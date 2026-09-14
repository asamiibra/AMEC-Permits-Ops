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
