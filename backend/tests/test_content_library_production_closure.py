from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException
from starlette.requests import Request
from sqlalchemy import select

from backend.app.api.source18_routers import _actor
from backend.app.api import master_content_routers
from backend.app.api.dependencies import AuthenticatedPrincipal, current_user_role
from backend.app.db import SessionLocal
from backend.app.main import app
from backend.app.models import AuditEvent, DocumentVersion, Role
from backend.app.services import master_content
from backend.app.services import governed_retrieval
from backend.app.storage.azure_blob import AzureBlobBinaryStore
from backend.app.storage.port import StorageLocator, StorageStat
from backend.app.storage.errors import StorageError, StorageErrorCode


def test_upload_gate_rejects_pdf_signature_mismatch(monkeypatch):
    monkeypatch.setattr(master_content, "get_settings", lambda: SimpleNamespace(master_sor_allowed_extensions=".pdf", master_sor_max_file_size=1024))
    with pytest.raises(HTTPException) as caught:
        master_content._allowed_file("sample.pdf", b"not a pdf")
    assert caught.value.detail["code"] == "FILE_SIGNATURE_MISMATCH"


def test_create_upload_is_bounded_before_service_persistence(client, monkeypatch):
    settings = SimpleNamespace(master_sor_allowed_extensions=".txt", master_sor_max_file_size=4)
    monkeypatch.setattr(master_content, "get_settings", lambda: settings)
    monkeypatch.setattr(master_content_routers, "get_settings", lambda: settings)
    response = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": "BOUND-CREATE-TEST", "title": "Bounded create"},
        files={"file": ("bounded.txt", b"12345", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert response.status_code == 413
    assert response.json()["detail"]["code"] == "FILE_TOO_LARGE"


def test_upload_gate_rejects_dangerous_archive_member(monkeypatch):
    monkeypatch.setattr(master_content, "get_settings", lambda: SimpleNamespace(master_sor_allowed_extensions=".docx", master_sor_max_file_size=1024 * 1024))
    import io
    import zipfile
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("../escape.txt", "synthetic")
    with pytest.raises(HTTPException) as caught:
        master_content._allowed_file("sample.docx", output.getvalue())
    assert caught.value.detail["code"] == "DANGEROUS_ARCHIVE_MEMBER"


def test_entra_source18_actor_ignores_dev_header():
    request = Request({"type": "http", "headers": [(b"x-dev-actor", b"spoofed")], "method": "GET", "path": "/", "query_string": b"", "client": ("test", 1), "server": ("test", 80), "scheme": "http"})
    request.state.authenticated_principal = AuthenticatedPrincipal(auth_mode="ENTRA", role=Role.SYSTEM_ADMIN, user_id="entra-user-123", object_id="entra-object-123")
    assert _actor(request, Role.SYSTEM_ADMIN) == "entra-user-123"


def test_content_library_entra_actor_is_persisted_and_header_cannot_spoof(client):
    def entra_override(request: Request):
        request.state.authenticated_principal = AuthenticatedPrincipal(
            auth_mode="ENTRA", role=Role.SYSTEM_ADMIN, user_id="user-A", object_id="object-A"
        )
        return Role.SYSTEM_ADMIN

    app.dependency_overrides[current_user_role] = entra_override
    ref = f"TRUSTED-ACTOR-{uuid4().hex[:8].upper()}"
    try:
        response = client.post(
            "/api/master-content",
            data={"content_type": "FORM", "ref": ref, "title": "Trusted actor proof"},
            files={"file": ("trusted-actor.txt", b"synthetic", "text/plain")},
            headers={"X-Dev-Role": "SYSTEM_ADMIN", "X-Dev-Actor": "user-B"},
        )
        assert response.status_code == 200, response.text
        item_id = response.json()["id"]
        with SessionLocal() as db:
            event = db.scalar(select(AuditEvent).where(AuditEvent.event_type == "MASTER_CONTENT_CREATED", AuditEvent.entity_id == item_id))
            version = db.scalar(select(DocumentVersion).where(DocumentVersion.id == response.json()["current_version_id"]))
            assert event is not None and event.actor_id == "user-A"
            assert event.metadata_json["actor_role"] == "SYSTEM_ADMIN"
            assert version is not None and version.metadata_json["uploaded_by"] == "user-A"
    finally:
        app.dependency_overrides.pop(current_user_role, None)


def test_content_library_reconcile_audit_uses_trusted_entra_actor(client, monkeypatch):
    created = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": f"TRUSTED-RECONCILE-{uuid4().hex[:8].upper()}", "title": "Trusted reconcile actor"},
        files={"file": ("trusted-reconcile.txt", b"synthetic", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert created.status_code == 200, created.text
    item_id = created.json()["id"]
    with SessionLocal() as db:
        version = db.get(DocumentVersion, created.json()["current_version_id"])
        version.sha256 = "0" * 64
        db.commit()
    monkeypatch.setattr(
        master_content,
        "_adapter",
        lambda: SimpleNamespace(verify_artifact=lambda path, expected_sha256, expected_size: {"verified": False}),
    )

    def entra_override(request: Request):
        request.state.authenticated_principal = AuthenticatedPrincipal(
            auth_mode="ENTRA", role=Role.SYSTEM_ADMIN, user_id="reconcile-user-A", object_id="reconcile-object-A"
        )
        return Role.SYSTEM_ADMIN

    app.dependency_overrides[current_user_role] = entra_override
    try:
        response = client.post(
            f"/api/master-content/{item_id}/reconcile",
            headers={"X-Dev-Role": "SYSTEM_ADMIN", "X-Dev-Actor": "reconcile-user-B"},
        )
        assert response.status_code == 409, response.text
        with SessionLocal() as db:
            event = db.scalar(
                select(AuditEvent).where(
                    AuditEvent.event_type == "EXTERNAL_MUTATION_DETECTED",
                    AuditEvent.entity_id == item_id,
                ).order_by(AuditEvent.id.desc())
            )
            assert event is not None
            assert event.actor_id == "reconcile-user-A"
            assert event.metadata_json["actor_role"] == "SYSTEM_ADMIN"
    finally:
        app.dependency_overrides.pop(current_user_role, None)


def test_historical_binary_download_is_owner_only(client):
    ref = f"HISTORY-AUTHZ-{uuid4().hex[:8].upper()}"
    created = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": ref, "title": "History authorization", "used_in": '["BD"]'},
        files={"file": ("history-authz.txt", b"version-one", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert created.status_code == 200, created.text
    item_id = created.json()["id"]
    v1_id = created.json()["current_version_id"]
    revised = client.post(
        f"/api/master-content/{item_id}/versions",
        data={"expected_current_version": "1", "change_reason": "Synthetic history authorization"},
        files={"file": ("history-authz-v2.txt", b"version-two", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert revised.status_code == 200, revised.text
    denied = client.get(f"/api/master-content/{item_id}/versions/{v1_id}/download", headers={"X-Dev-Role": "PROCESS_CHAMPION"})
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "HISTORICAL_BINARY_ACCESS_FORBIDDEN"
    allowed = client.get(f"/api/master-content/{item_id}/versions/{v1_id}/download", headers={"X-Dev-Role": "OWNER_SPONSOR"})
    assert allowed.status_code == 200
    assert allowed.content == b"version-one"


def test_azure_blob_pending_scan_is_not_reusable(client):
    ref = f"SCAN-GATE-{uuid4().hex[:8].upper()}"
    created = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": ref, "title": "Scan gate", "used_in": '["BD"]'},
        files={"file": ("scan-gate.txt", b"synthetic", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert created.status_code == 200, created.text
    with SessionLocal() as db:
        version = db.get(DocumentVersion, created.json()["current_version_id"])
        version.metadata_json = {**version.metadata_json, "storage_provider": "azure-blob", "malware_scan_state": "SCAN_PENDING"}
        db.commit()
        result = master_content.evaluate_master_content_reuse_eligibility(db, item=db.get(master_content.MasterContentItem, created.json()["id"]), module="BD", usage_type="PROPOSAL_TEMPLATE", content_type="FORM", require_binding=False, enforce_governance_readiness=False)
        assert result["eligible"] is False
        assert "MALWARE_SCAN_NOT_CLEAN" in result["reasons"]


def test_azure_blob_malicious_scan_quarantines_download(client):
    ref = f"SCAN-MALICIOUS-{uuid4().hex[:8].upper()}"
    created = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": ref, "title": "Malicious quarantine", "used_in": '["BD"]'},
        files={"file": ("scan-malicious.txt", b"synthetic", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert created.status_code == 200, created.text
    with SessionLocal() as db:
        version = db.get(DocumentVersion, created.json()["current_version_id"])
        version.metadata_json = {
            **version.metadata_json,
            "storage_provider": "azure-blob",
            "malware_scan_state": "MALICIOUS",
        }
        db.commit()
    for role in ("PROCESS_CHAMPION", "OWNER_SPONSOR", "SYSTEM_ADMIN"):
        response = client.get(
            f"/api/master-content/{created.json()['id']}/versions/{created.json()['current_version_id']}/download",
            headers={"X-Dev-Role": role},
        )
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "MASTER_CONTENT_MALWARE_QUARANTINED"


class _FakeAzureBlobStore(AzureBlobBinaryStore):
    def __init__(self, tags, sha256):
        self.config = SimpleNamespace(container="managed-artifacts")
        self._tags = tags
        self._sha256 = sha256

    def scan_result(self, locator):
        return dict(self._tags)

    def stat(self, locator):
        return StorageStat(locator, size=9, sha256=self._sha256)


def _mark_azure_blob_version(created, *, scan_state="SCAN_PENDING", source_path="storage://azure-blob/managed-artifacts/test.bin"):
    with SessionLocal() as db:
        version = db.get(DocumentVersion, created.json()["current_version_id"])
        version.source_path_or_reference = source_path
        version.metadata_json = {
            **(version.metadata_json or {}),
            "storage_provider": "azure-blob",
            "malware_scan_state": scan_state,
        }
        db.commit()
        return version.id, version.sha256


@pytest.mark.parametrize(
    "claim",
    [
        {"scan_state": "CLEAN", "scanned_sha256": "0" * 64, "result_source": "DEFENDER_FOR_STORAGE_EVENT_GRID", "evidence_reference": "caller-clean"},
        {"scan_state": "CLEAN", "scanned_sha256": "a" * 64, "result_source": "DEFENDER_FOR_STORAGE_INDEX_TAG", "evidence_reference": "caller-matching-sha"},
        {"scan_state": "MALICIOUS", "scanned_sha256": None, "result_source": "DEFENDER_FOR_STORAGE_EVENT_GRID", "evidence_reference": "caller-malicious"},
    ],
)
def test_malware_endpoint_ignores_caller_scan_claims(client, monkeypatch, claim):
    created = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": f"SCAN-CLAIM-{uuid4().hex[:8].upper()}", "title": "Ignored scan claim"},
        files={"file": ("scan-claim.txt", b"synthetic", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert created.status_code == 200, created.text
    version_id, version_sha = _mark_azure_blob_version(created)
    monkeypatch.setattr(
        master_content_routers,
        "create_binary_store",
        lambda: _FakeAzureBlobStore({"Malware scanning scan result": "Malicious", "Malware scanning scan time": "synthetic"}, version_sha),
    )
    response = client.post(f"/api/master-content/{created.json()['id']}/malware-scan", json=claim, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        version = db.get(DocumentVersion, version_id)
        assert version.metadata_json["malware_scan_state"] == "MALICIOUS"
        assert version.metadata_json["malware_scan_result_source"] == "DEFENDER_FOR_STORAGE_INDEX_TAG"


@pytest.mark.parametrize(
    "tag_result,expected_state,stat_sha",
    [
        ("No threats found", "CLEAN", "MATCH"),
        ("No threats found", "SCAN_FAILED", "MISMATCH"),
        ("Malicious", "MALICIOUS", "MATCH"),
        ("Error", "SCAN_FAILED", "MATCH"),
        ("Not scanned", "SCAN_UNAVAILABLE", "MATCH"),
        (None, "SCAN_PENDING", "MATCH"),
    ],
)
def test_defender_reconciliation_is_the_only_scan_authority(client, monkeypatch, tag_result, expected_state, stat_sha):
    created = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": f"SCAN-RECON-{uuid4().hex[:8].upper()}", "title": "Defender reconciliation"},
        files={"file": ("scan-recon.txt", b"123456789", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert created.status_code == 200, created.text
    version_id, version_sha = _mark_azure_blob_version(created)
    tags = {"Malware scanning scan result": tag_result} if tag_result else {}
    actual_sha = version_sha if stat_sha == "MATCH" else "0" * 64
    monkeypatch.setattr(master_content_routers, "create_binary_store", lambda: _FakeAzureBlobStore(tags, actual_sha))
    response = client.post(
        f"/api/master-content/{created.json()['id']}/malware-scan/reconcile/{version_id}",
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        version = db.get(DocumentVersion, version_id)
        assert version.metadata_json["malware_scan_state"] == expected_state
        assert version.metadata_json["malware_scan_sha256"] == (version_sha if expected_state == "CLEAN" else None)


@pytest.mark.parametrize(
    "scan_state,expected_code",
    [
        ("SCAN_PENDING", "MASTER_CONTENT_MALWARE_SCAN_NOT_CLEAN"),
        ("MALICIOUS", "MASTER_CONTENT_MALWARE_QUARANTINED"),
        ("SCAN_FAILED", "MASTER_CONTENT_MALWARE_SCAN_NOT_CLEAN"),
        ("SCAN_UNAVAILABLE", "MASTER_CONTENT_MALWARE_SCAN_NOT_CLEAN"),
        (None, "MASTER_CONTENT_MALWARE_SCAN_NOT_CLEAN"),
        ("UNKNOWN", "MASTER_CONTENT_MALWARE_SCAN_NOT_CLEAN"),
    ],
)
def test_managed_binary_download_is_fail_closed_for_every_non_clean_state(client, scan_state, expected_code):
    created = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": f"DOWNLOAD-GATE-{uuid4().hex[:8].upper()}", "title": "Download gate"},
        files={"file": ("download-gate.txt", b"synthetic", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert created.status_code == 200, created.text
    _mark_azure_blob_version(created, scan_state=scan_state or "UNKNOWN")
    response = client.get(f"/api/master-content/{created.json()['id']}/download", headers={"X-Dev-Role": "OWNER_SPONSOR"})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == expected_code


def _retrieval_azure_item(client):
    created = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": f"RETRIEVAL-GATE-{uuid4().hex[:8].upper()}", "title": "Retrieval gate synthetic text"},
        files={"file": ("retrieval-gate.txt", b"retrieval bytes", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert created.status_code == 200, created.text
    version_id, version_sha = _mark_azure_blob_version(created)
    return created.json()["id"], version_id, version_sha


@pytest.mark.parametrize("scan_state", ["SCAN_PENDING", "MALICIOUS", "SCAN_FAILED", "SCAN_UNAVAILABLE", "UNKNOWN"])
def test_governed_retrieval_excludes_non_clean_managed_content(client, scan_state):
    item_id, version_id, _ = _retrieval_azure_item(client)
    with SessionLocal() as db:
        version = db.get(DocumentVersion, version_id)
        version.metadata_json = {**version.metadata_json, "malware_scan_state": scan_state}
        db.commit()
        access = governed_retrieval.access_context_for_role(Role.OWNER_SPONSOR, caller_id="synthetic-owner", purpose="READ")
        assert not governed_retrieval.governed_retrieve(db, governed_retrieval.RetrievalQuery(query="Retrieval gate", master_content_id=item_id), access)
        assert not governed_retrieval.governed_retrieve(db, governed_retrieval.RetrievalQuery(query="Retrieval gate", document_version_id=version_id), access)


def test_governed_retrieval_clean_and_storage_failure_never_uses_synthetic_text(client, monkeypatch):
    item_id, version_id, _ = _retrieval_azure_item(client)
    with SessionLocal() as db:
        version = db.get(DocumentVersion, version_id)
        version.metadata_json = {**version.metadata_json, "malware_scan_state": "CLEAN", "synthetic_text": "DO NOT USE FALLBACK"}
        db.commit()
        access = governed_retrieval.access_context_for_role(Role.OWNER_SPONSOR, caller_id="synthetic-owner", purpose="READ")
        monkeypatch.setattr(governed_retrieval, "read_master_content_bytes", lambda _db, _version: b"clean managed bytes")
        for query in (
            governed_retrieval.RetrievalQuery(query="Retrieval gate", master_content_id=item_id),
            governed_retrieval.RetrievalQuery(query="Retrieval gate", document_version_id=version_id),
        ):
            results = governed_retrieval.governed_retrieve(db, query, access)
            assert results and results[0].envelope.content == "clean managed bytes"
            answer = governed_retrieval.answer_from_retrieval("Retrieval gate", results)
            assert answer.answer == "clean managed bytes"
        monkeypatch.setattr(
            governed_retrieval,
            "read_master_content_bytes",
            lambda _db, _version: (_ for _ in ()).throw(StorageError(StorageErrorCode.UNAVAILABLE)),
        )
        with pytest.raises(StorageError):
            governed_retrieval.governed_retrieve(db, governed_retrieval.RetrievalQuery(query="Retrieval gate", master_content_id=item_id), access)


def test_source18_official_forms_are_read_only_typed_projections(client):
    response = client.get("/api/master-content/official-forms", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert response.status_code == 200, response.text
    assert response.json()["projection_type"] == "SOURCE18_OFFICIAL_FORM_READ_ONLY"
    assert response.json()["read_only"] is True
    assert response.json()["items"]
    item = response.json()["items"][0]
    assert item["authority_owner"] == "SOURCE18"
    assert item["reuse"]["allowed"] is True
    assert client.get("/api/master-content/official-forms/resolve", headers={"X-Dev-Role": "SYSTEM_ADMIN"}).status_code == 200


def test_dashboard_v2_direct_form_reads_enforce_persona_applicability(client):
    response = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": "V2-AUTHZ-DIRECT-TEST", "title": "Administration-only direct read", "used_in": '["ADMIN"]'},
        files={"file": ("v2-authz-direct.txt", b"synthetic", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert response.status_code == 200, response.text
    item_id = response.json()["id"]
    for suffix in ("applicability", "policy-lineage", "technical-lineage", "automation"):
        denied = client.get(f"/api/dashboard-v2/forms/{item_id}/{suffix}", headers={"X-Dev-Role": "PROCESS_CHAMPION"})
        assert denied.status_code == 403, (suffix, denied.text)
