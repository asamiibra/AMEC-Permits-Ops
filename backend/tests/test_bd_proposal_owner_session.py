"""BD Proposal owner-session vertical acceptance tests."""

import hashlib
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import AuditEvent, DocumentVersion, Opportunity, ProposalIntakeArtifact, ProposalSourceEvidence, ProposalSourceLink
from backend.app.services.proposals_sor import intake_sor_root, read_proposal_source_bytes


def _headers(role: str) -> dict[str, str]:
    return {"X-Dev-Role": role}


def _ensure_dashboard_proposal_templates(client):
    for ref, title, usage in (("F-0003", "Regression Proposal Template", "PROPOSAL_TEMPLATE"), ("F-0004", "Regression Proposal Checklist", "PROPOSAL_CHECKLIST")):
        rows = client.get("/api/master-content", params={"q": ref}, headers=_headers("SYSTEM_ADMIN")).json()
        item = next((row for row in rows if row["ref"] == ref), None)
        if not item:
            created = client.post("/api/master-content", data={"content_type": "FORM", "ref": ref, "title": title, "description": title, "used_in": '["BD"]'}, files={"file": (f"{ref}.txt", b"synthetic regression canonical content", "text/plain")}, headers=_headers("SYSTEM_ADMIN"))
            assert created.status_code == 200, created.text
            item = created.json()
        bound = client.put(f"/api/master-content/{item['id']}/module-bindings", json=[{"module": "BD", "usage_type": usage}], headers=_headers("SYSTEM_ADMIN"))
        assert bound.status_code == 200, bound.text


def _advance_to_engineering_handoff(client, proposal_id: str):
    proceeded = client.post(f"/api/bd/proposals/{proposal_id}/proceed", headers=_headers("COMMERCIAL_APPROVER"))
    assert proceeded.status_code == 200, proceeded.text
    ready = client.post(f"/api/proposals-main/proposals/{proposal_id}/engineering-ready", headers=_headers("RESPONSIBLE_ENGINEER"))
    assert ready.status_code == 200, ready.text


def _create_source_for_readback(client, *, title: str = "Source readback regression", content: bytes = b"synthetic source readback\n"):
    created = client.post("/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json={"proposal_description": title, "client_name": "Synthetic Readback Client"})
    assert created.status_code == 200, created.text
    proposal_id = created.json()["id"]
    uploaded = client.post(
        f"/api/bd/proposals/{proposal_id}/sources",
        headers=_headers("COMMERCIAL_APPROVER"),
        data={"source_type": "TENDER_DOCUMENT", "source_revision": "RB1"},
        files={"file": ("readback.txt", content, "text/plain")},
    )
    assert uploaded.status_code == 200, uploaded.text
    source_id = uploaded.json()["proposal"]["sources"][0]["id"]
    return proposal_id, source_id, content


def _source_persisted_snapshot(proposal_id: str, source_id: str):
    with SessionLocal() as db:
        proposal = db.get(Opportunity, proposal_id)
        evidence = db.get(ProposalSourceEvidence, source_id)
        link = db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal_id, ProposalSourceLink.source_evidence_id == source_id))
        version = db.get(DocumentVersion, link.document_version_id) if link else None
        artifact = db.get(ProposalIntakeArtifact, (evidence.provenance or {}).get("source_artifact_id")) if evidence else None
        return {
            "proposal": (proposal.status, proposal.updated_at),
            "evidence": (evidence.id, evidence.proposal_id, evidence.source_filename, evidence.source_reference, evidence.content_hash, evidence.content_type, evidence.status, evidence.verification_state, evidence.provenance),
            "link": (link.id, link.proposal_id, link.source_evidence_id, link.document_id, link.document_version_id, link.source_role, link.added_by, link.active) if link else None,
            "version": (version.id, version.document_id, version.version_number, version.source_filename, version.source_path_or_reference, version.sha256, version.file_size, version.mime_type, version.approval_state, version.source_system) if version else None,
            "artifact": (artifact.id, artifact.opportunity_id, artifact.source_filename, artifact.stored_filename, artifact.sor_path, artifact.content_hash, artifact.file_size, artifact.content_type, artifact.status, artifact.verification_state) if artifact else None,
            "audit_count": db.query(AuditEvent).filter(AuditEvent.entity_id == proposal_id).count(),
        }


def test_bd_proposal_source_content_is_exact_and_survives_handoff_without_writes(client):
    proposal_id, source_id, content = _create_source_for_readback(client)
    expected_sha = hashlib.sha256(content).hexdigest()
    before = _source_persisted_snapshot(proposal_id, source_id)

    response = client.get(f"/api/bd/proposals/{proposal_id}/sources/{source_id}/content", headers=_headers("SYSTEM_ADMIN"))
    assert response.status_code == 200, response.text
    assert response.content == content
    assert response.headers["content-type"] == "text/plain; charset=utf-8"
    assert response.headers["x-content-sha256"] == expected_sha
    assert response.headers["x-proposal-source-evidence-id"] == source_id
    assert response.headers["x-proposal-source-link-id"]
    assert response.headers["x-document-version-id"]
    assert response.headers["x-proposal-intake-artifact-id"]
    assert _source_persisted_snapshot(proposal_id, source_id) == before

    _advance_to_engineering_handoff(client, proposal_id)
    after_handoff = client.get(f"/api/bd/proposals/{proposal_id}/sources/{source_id}/content", headers=_headers("SYSTEM_ADMIN"))
    assert after_handoff.status_code == 200
    assert after_handoff.content == content

    with SessionLocal() as db:
        proposal = db.get(Opportunity, proposal_id)
        assert proposal.status == "PROPOSAL_HANDOVER"
        assert before["proposal"][0] == "IN_REVIEW"
        evidence = db.get(ProposalSourceEvidence, source_id)
        link = db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal_id, ProposalSourceLink.source_evidence_id == source_id))
        version = db.get(DocumentVersion, link.document_version_id)
        artifact = db.get(ProposalIntakeArtifact, (evidence.provenance or {})["source_artifact_id"])
        assert evidence.content_hash == version.sha256 == artifact.content_hash == expected_sha
        assert version.file_size == artifact.file_size == len(content)


def test_bd_proposal_source_content_requires_read_capability_and_exact_proposal(client, monkeypatch):
    proposal_id, source_id, _ = _create_source_for_readback(client, title="Readback authorization regression")
    denied_matrix = set(__import__("backend.app.services.backend_realignment", fromlist=["CAPABILITY_MATRIX"]).CAPABILITY_MATRIX["ENGINEERING"])
    from backend.app.services import backend_realignment
    monkeypatch.setitem(backend_realignment.CAPABILITY_MATRIX, "ENGINEERING", denied_matrix - {"BD_PROPOSAL_READ"})
    denied = client.get(f"/api/bd/proposals/{proposal_id}/sources/{source_id}/content", headers=_headers("RESPONSIBLE_ENGINEER"))
    assert denied.status_code == 403
    monkeypatch.setitem(backend_realignment.CAPABILITY_MATRIX, "ENGINEERING", denied_matrix)

    other = client.post("/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json={"proposal_description": "Other Proposal", "client_name": "Other Client"})
    assert other.status_code == 200
    assert client.get(f"/api/bd/proposals/{other.json()['id']}/sources/{source_id}/content", headers=_headers("SYSTEM_ADMIN")).status_code == 404
    assert client.get(f"/api/bd/proposals/{proposal_id}/sources/missing-source/content", headers=_headers("SYSTEM_ADMIN")).status_code == 404


def test_bd_proposal_source_content_fails_closed_on_typed_linkage_mismatch(client):
    proposal_id, source_id, _ = _create_source_for_readback(client, title="Linkage mismatch regression")
    with SessionLocal() as db:
        link = db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal_id, ProposalSourceLink.source_evidence_id == source_id))
        original = link.document_version_id
        link.document_version_id = "missing-document-version"
        db.commit()
    try:
        response = client.get(f"/api/bd/proposals/{proposal_id}/sources/{source_id}/content", headers=_headers("SYSTEM_ADMIN"))
        assert response.status_code == 409
    finally:
        with SessionLocal() as db:
            link = db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal_id, ProposalSourceLink.source_evidence_id == source_id))
            link.document_version_id = original
            db.commit()


def test_bd_proposal_source_content_fails_closed_when_source_link_is_missing(client):
    proposal_id, source_id, _ = _create_source_for_readback(client, title="Missing link regression")
    with SessionLocal() as db:
        link = db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal_id, ProposalSourceLink.source_evidence_id == source_id))
        link_row = {name: getattr(link, name) for name in ("id", "proposal_id", "source_evidence_id", "document_id", "document_version_id", "source_role", "added_by", "active", "note")}
        db.delete(link)
        db.commit()
    try:
        response = client.get(f"/api/bd/proposals/{proposal_id}/sources/{source_id}/content", headers=_headers("SYSTEM_ADMIN"))
        assert response.status_code == 409
    finally:
        with SessionLocal() as db:
            db.add(ProposalSourceLink(**link_row))
            db.commit()


def test_bd_proposal_source_content_fails_closed_on_document_and_intake_hash_disagreement(client):
    proposal_id, source_id, _ = _create_source_for_readback(client, title="Typed hash regression")
    with SessionLocal() as db:
        evidence = db.get(ProposalSourceEvidence, source_id)
        link = db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal_id, ProposalSourceLink.source_evidence_id == source_id))
        version = db.get(DocumentVersion, link.document_version_id)
        artifact = db.get(ProposalIntakeArtifact, (evidence.provenance or {})["source_artifact_id"])
        version_sha = version.sha256
        artifact_sha = artifact.content_hash
        version.sha256 = "1" * 64
        db.commit()
    try:
        assert client.get(f"/api/bd/proposals/{proposal_id}/sources/{source_id}/content", headers=_headers("SYSTEM_ADMIN")).status_code == 409
    finally:
        with SessionLocal() as db:
            db.get(DocumentVersion, version.id).sha256 = version_sha
            db.commit()

    with SessionLocal() as db:
        artifact = db.get(ProposalIntakeArtifact, artifact.id)
        artifact.content_hash = "2" * 64
        db.commit()
    try:
        assert client.get(f"/api/bd/proposals/{proposal_id}/sources/{source_id}/content", headers=_headers("SYSTEM_ADMIN")).status_code == 409
    finally:
        with SessionLocal() as db:
            db.get(ProposalIntakeArtifact, artifact.id).content_hash = artifact_sha
            db.commit()


def test_bd_proposal_source_content_fails_closed_on_actual_bytes_and_missing_file(client, tmp_path):
    proposal_id, source_id, content = _create_source_for_readback(client, title="Physical file regression")
    with SessionLocal() as db:
        evidence = db.get(ProposalSourceEvidence, source_id)
        artifact = db.get(ProposalIntakeArtifact, (evidence.provenance or {})["source_artifact_id"])
        stored_path = Path(artifact.sor_path)
        reference = db.get(Opportunity, proposal_id).opportunity_reference
        expected_sha = artifact.content_hash
        expected_size = artifact.file_size
    stored_path.write_bytes(b"tampered persisted bytes")
    try:
        assert client.get(f"/api/bd/proposals/{proposal_id}/sources/{source_id}/content", headers=_headers("SYSTEM_ADMIN")).status_code == 409
    finally:
        stored_path.write_bytes(content)

    backup = stored_path.with_name(f"{stored_path.name}.missing-test")
    stored_path.rename(backup)
    try:
        assert client.get(f"/api/bd/proposals/{proposal_id}/sources/{source_id}/content", headers=_headers("SYSTEM_ADMIN")).status_code == 409
    finally:
        backup.rename(stored_path)

    with pytest.raises(HTTPException) as size_mismatch:
        read_proposal_source_bytes(opportunity_reference=reference, sor_path=str(stored_path), expected_sha256=expected_sha, expected_file_size=expected_size + 1)
    assert size_mismatch.value.status_code == 409


def test_bd_proposal_source_content_rejects_file_and_proposal_root_symlink_escape(client, tmp_path):
    proposal_id, source_id, content = _create_source_for_readback(client, title="Symlink confinement regression")
    with SessionLocal() as db:
        proposal = db.get(Opportunity, proposal_id)
        evidence = db.get(ProposalSourceEvidence, source_id)
        artifact = db.get(ProposalIntakeArtifact, (evidence.provenance or {})["source_artifact_id"])
        stored_path = Path(artifact.sor_path)
        proposal_root = intake_sor_root() / proposal.opportunity_reference
        expected_sha = artifact.content_hash
        expected_size = artifact.file_size

    outside_file = tmp_path / "outside-source.txt"
    outside_file.write_bytes(b"outside source")
    file_backup = stored_path.with_name(f"{stored_path.name}.symlink-test")
    stored_path.rename(file_backup)
    stored_path.symlink_to(outside_file)
    try:
        assert client.get(f"/api/bd/proposals/{proposal_id}/sources/{source_id}/content", headers=_headers("SYSTEM_ADMIN")).status_code == 409
    finally:
        stored_path.unlink()
        file_backup.rename(stored_path)
        stored_path.write_bytes(content)

    outside_root = tmp_path / "outside-proposal-root"
    outside_root.mkdir()
    (outside_root / stored_path.name).write_bytes(content)
    root_backup = proposal_root.with_name(f"{proposal_root.name}.symlink-test")
    proposal_root.rename(root_backup)
    proposal_root.symlink_to(outside_root, target_is_directory=True)
    try:
        with pytest.raises(HTTPException) as escaped_root:
            read_proposal_source_bytes(opportunity_reference=proposal.opportunity_reference, sor_path=str(stored_path), expected_sha256=expected_sha, expected_file_size=expected_size)
        assert escaped_root.value.status_code == 409
    finally:
        proposal_root.unlink()
        root_backup.rename(proposal_root)


def test_bd_proposal_source_content_does_not_accept_a_client_path_parameter(client, tmp_path):
    proposal_id, source_id, content = _create_source_for_readback(client, title="Client path parameter regression")
    response = client.get(
        f"/api/bd/proposals/{proposal_id}/sources/{source_id}/content",
        params={"sor_path": str(tmp_path / "arbitrary-client-path"), "path": str(tmp_path / "another-client-path")},
        headers=_headers("SYSTEM_ADMIN"),
    )
    assert response.status_code == 200
    assert response.content == content


def test_bd_proposal_source_content_fails_closed_on_hash_and_size_mismatch(client):
    proposal_id, source_id, content = _create_source_for_readback(client, title="Hash mismatch regression")
    with SessionLocal() as db:
        evidence = db.get(ProposalSourceEvidence, source_id)
        link = db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal_id, ProposalSourceLink.source_evidence_id == source_id))
        version = db.get(DocumentVersion, link.document_version_id)
        artifact = db.get(ProposalIntakeArtifact, (evidence.provenance or {})["source_artifact_id"])
        original = (evidence.content_hash, version.sha256, artifact.content_hash, artifact.file_size)
        evidence.content_hash = "0" * 64
        db.commit()
    try:
        assert client.get(f"/api/bd/proposals/{proposal_id}/sources/{source_id}/content", headers=_headers("SYSTEM_ADMIN")).status_code == 409
    finally:
        with SessionLocal() as db:
            evidence = db.get(ProposalSourceEvidence, source_id)
            link = db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal_id, ProposalSourceLink.source_evidence_id == source_id))
            version = db.get(DocumentVersion, link.document_version_id)
            artifact = db.get(ProposalIntakeArtifact, (evidence.provenance or {})["source_artifact_id"])
            evidence.content_hash, version.sha256, artifact.content_hash, artifact.file_size = original
            db.commit()

    with SessionLocal() as db:
        evidence = db.get(ProposalSourceEvidence, source_id)
        link = db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal_id, ProposalSourceLink.source_evidence_id == source_id))
        version = db.get(DocumentVersion, link.document_version_id)
        artifact = db.get(ProposalIntakeArtifact, (evidence.provenance or {})["source_artifact_id"])
        original_size = artifact.file_size
        artifact.file_size = original_size + 1
        db.commit()
    try:
        assert client.get(f"/api/bd/proposals/{proposal_id}/sources/{source_id}/content", headers=_headers("SYSTEM_ADMIN")).status_code == 409
    finally:
        with SessionLocal() as db:
            artifact = db.get(ProposalIntakeArtifact, (db.get(ProposalSourceEvidence, source_id).provenance or {})["source_artifact_id"])
            artifact.file_size = original_size
            db.commit()


def test_read_proposal_source_bytes_rejects_escape_and_missing_file(client):
    proposal_id, source_id, content = _create_source_for_readback(client, title="Path safety regression")
    with SessionLocal() as db:
        proposal = db.get(Opportunity, proposal_id)
        evidence = db.get(ProposalSourceEvidence, source_id)
        artifact = db.get(ProposalIntakeArtifact, (evidence.provenance or {})["source_artifact_id"])
        root_path = artifact.sor_path
        reference = proposal.opportunity_reference
        expected_sha = artifact.content_hash
        expected_size = artifact.file_size
    with pytest.raises(HTTPException) as escaped:
        read_proposal_source_bytes(opportunity_reference=reference, sor_path=f"{Path(root_path).parent}/../escape.txt", expected_sha256=expected_sha, expected_file_size=expected_size)
    assert escaped.value.status_code == 409
    with pytest.raises(HTTPException) as missing:
        read_proposal_source_bytes(opportunity_reference=reference, sor_path=f"{Path(root_path).parent}/missing.txt", expected_sha256=expected_sha, expected_file_size=expected_size)
    assert missing.value.status_code == 409


def test_bd_proposal_full_owner_session_flow(client):
    owner = _headers("SYSTEM_ADMIN")
    _ensure_dashboard_proposal_templates(client)

    created = client.post("/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json={
        "proposal_description": "BD owner-session regression proposal",
        "project_reference": "GHCE-2026-0187",
        "client_name": "Synthetic BD Regression Client",
    })
    assert created.status_code == 200
    proposal_id = created.json()["id"]

    initial = client.get(f"/api/bd/proposals/{proposal_id}/validation", headers=owner).json()
    assert initial["ready"] is False
    assert {"SOURCE_EVIDENCE_REQUIRED", "SCOPE_OF_WORK_REQUIRED"} <= {item["code"] for item in initial["blockers"]}

    for source_type in ("TENDER_DOCUMENT", "TENDER_EMAIL", "TENDER_PHOTO", "CLIENT_DATA"):
        response = client.post(
            f"/api/bd/proposals/{proposal_id}/sources",
            headers=_headers("COMMERCIAL_APPROVER"),
            data={"source_type": source_type, "source_revision": "S1"},
            files={"file": (f"{source_type.lower()}.txt", f"synthetic {source_type}".encode(), "text/plain")},
        )
        assert response.status_code == 200
        assert response.json()["source"]["verification_state"] == "READ_BACK_VERIFIED"

    updated = client.patch(f"/api/bd/proposals/{proposal_id}", headers=_headers("COMMERCIAL_APPROVER"), json={
        "fields": {
            "client_name": "Synthetic BD Regression Client",
            "scope_of_work": "AMEC design and permitting scope",
            "client_scope_of_work": "Client tender scope",
            "process_of_work": "Review, prepare, verify, hand off",
            "price": "QAR 10000",
            "duration": "30 days",
            "inclusions": ["Drawings"],
            "exclusions": ["Authority fees"],
            "additional_information": "Regression proof",
            "definition_terms": ["Project Reference"],
            "provenance": {"scope_of_work": "manual", "client_scope_of_work": "source", "price": "manual"},
        },
        "amec_input": {"review_note": "Human AMEC review recorded."},
    })
    assert updated.status_code == 200
    ready = client.get(f"/api/bd/proposals/{proposal_id}/validation", headers=owner).json()
    assert ready["ready"] is True
    assert ready["ai_assist"]["enabled"] is False

    _advance_to_engineering_handoff(client, proposal_id)

    engineering_accept = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=_headers("RESPONSIBLE_ENGINEER"))
    assert engineering_accept.status_code == 403
    accepted = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=_headers("COMMERCIAL_APPROVER"))
    assert accepted.status_code == 200
    accepted_payload = accepted.json()
    revision = accepted_payload["current_revision"]
    assert revision["revision_number"] == 1
    assert revision["template"]["ref"] == "F-0003"
    assert revision["checklist"]["ref"] == "F-0004"

    outputs = client.get(f"/api/bd/proposals/{proposal_id}/outputs", headers=owner)
    assert outputs.status_code == 200
    assert {item["artifact_type"] for item in outputs.json()["items"]} == {"PROPOSAL", "CHECKLIST"}
    download = client.get(f"/api/bd/proposals/{proposal_id}/outputs/proposal", headers=owner)
    assert download.status_code == 200
    assert download.headers["x-artifact-hash"]

    handoff = client.post(f"/api/bd/proposals/{proposal_id}/handoff/contract", headers=_headers("COMMERCIAL_APPROVER"))
    assert handoff.status_code == 200
    assert handoff.json()["accepted_revision_id"] == revision["id"]
    assert handoff.json()["proposal_reference"] == accepted_payload["proposal_reference"]
    assert handoff.json()["client"] == "Synthetic BD Regression Client"
    assert handoff.json()["project_reference"] == "GHCE-2026-0187"
    assert handoff.json()["proposal_artifact"]["content_hash"]
    assert handoff.json()["checklist_artifact"]["content_hash"]
    assert handoff.json()["machine_legal_contract"] is False


def test_bd_proposal_dashboard_seams_and_engineering_read_only(client):
    owner = _headers("SYSTEM_ADMIN")
    _ensure_dashboard_proposal_templates(client)
    resolved = client.get("/api/bd/proposals/master-content", headers=_headers("COMMERCIAL_APPROVER"))
    assert resolved.status_code == 200
    assert resolved.json()["proposal_template"]["status"] == "RESOLVED"
    assert resolved.json()["proposal_checklist"]["status"] == "RESOLVED"
    assert resolved.json()["definitions"]["truth"] == "DASHBOARD_DEFINITIONS"

    denied = client.post("/api/bd/proposals", headers=_headers("RESPONSIBLE_ENGINEER"), json={"proposal_description": "Denied", "client_name": "Denied"})
    assert denied.status_code == 403

    settings = client.get("/api/bd/proposals/settings/go-live", headers=owner)
    assert settings.status_code == 200
    assert settings.json()["safe_default"] is True


def test_bd_proposal_source_replacement_preserves_history_without_permanent_conflict(client):
    _ensure_dashboard_proposal_templates(client)
    created = client.post("/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json={"proposal_description": "Source history regression", "client_name": "Synthetic Source History Client"})
    assert created.status_code == 200
    proposal_id = created.json()["id"]
    first = client.post(f"/api/bd/proposals/{proposal_id}/sources", headers=_headers("COMMERCIAL_APPROVER"), data={"source_type": "TENDER_DOCUMENT", "source_revision": "v1"}, files={"file": ("tender-v1.txt", b"original tender", "text/plain")})
    second = client.post(f"/api/bd/proposals/{proposal_id}/sources", headers=_headers("COMMERCIAL_APPROVER"), data={"source_type": "TENDER_DOCUMENT", "source_revision": "v2"}, files={"file": ("tender-v2.txt", b"revised tender", "text/plain")})
    assert first.status_code == second.status_code == 200
    sources = second.json()["proposal"]["sources"]
    assert len(sources) == 2
    assert {item["status"] for item in sources} == {"CURRENT", "CONFLICT"}
    validation = second.json()["proposal"]["validation"]
    assert "SOURCE_CONFLICTS_UNRESOLVED" not in {item["code"] for item in validation["blockers"]}
    assert "SOURCE_CONFLICT_HISTORY" in {item["code"] for item in validation["warnings"]}


def test_bd_proposal_acceptance_pins_template_and_checklist_history(client):
    _ensure_dashboard_proposal_templates(client)
    created = client.post("/api/bd/proposals", headers=_headers("COMMERCIAL_APPROVER"), json={"proposal_description": "Template history regression", "client_name": "Synthetic Template History Client"})
    assert created.status_code == 200
    proposal_id = created.json()["id"]
    for source_type in ("TENDER_DOCUMENT", "TENDER_EMAIL", "TENDER_PHOTO", "CLIENT_DATA"):
        response = client.post(f"/api/bd/proposals/{proposal_id}/sources", headers=_headers("COMMERCIAL_APPROVER"), data={"source_type": source_type, "source_revision": "H1"}, files={"file": (f"{source_type.lower()}-h1.txt", b"history source", "text/plain")})
        assert response.status_code == 200
    fields = {"scope_of_work": "AMEC scope", "client_scope_of_work": "Client scope", "process_of_work": "Review", "price": "QAR 100", "duration": "1 day"}
    assert client.patch(f"/api/bd/proposals/{proposal_id}", headers=_headers("COMMERCIAL_APPROVER"), json={"fields": fields}).status_code == 200
    _advance_to_engineering_handoff(client, proposal_id)
    first = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=_headers("COMMERCIAL_APPROVER")).json()["current_revision"]
    template_id = first["template"]["ref"]
    checklist_id = first["checklist"]["ref"]
    for ref, label in ((template_id, "template v2"), (checklist_id, "checklist v2")):
        item = next(row for row in client.get("/api/master-content", params={"q": ref}, headers=_headers("SYSTEM_ADMIN")).json() if row["ref"] == ref)
        versioned = client.post(f"/api/master-content/{item['id']}/versions", headers=_headers("SYSTEM_ADMIN"), data={"expected_current_version": "1", "change_reason": label}, files={"file": (f"{ref}-v2.txt", label.encode(), "text/plain")})
        assert versioned.status_code == 200, versioned.text
    assert client.patch(f"/api/bd/proposals/{proposal_id}", headers=_headers("COMMERCIAL_APPROVER"), json={"fields": {"proposal_details": "Updated after master revision"}}).status_code == 200
    created_revision = client.post(f"/api/bd/proposals/{proposal_id}/revisions", headers=_headers("COMMERCIAL_APPROVER"), json={"reason": "Dashboard master revision"})
    assert created_revision.status_code == 200, created_revision.text
    second = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=_headers("COMMERCIAL_APPROVER")).json()
    history = {row["revision_number"]: row for row in second["revision_history"]}
    assert history[1]["revision_number"] == 1
    assert second["current_revision"]["revision_number"] == 2
    assert second["current_revision"]["template"]["version"] == "2"
    assert second["current_revision"]["checklist"]["version"] == "2"
    assert history[1]["content_hash"] != second["current_revision"]["content_hash"]


def test_bd_proposal_owner_lanes_search_and_projection_contract(client):
    _ensure_dashboard_proposal_templates(client)
    bd = _headers("COMMERCIAL_APPROVER")

    need = client.post("/api/bd/proposals", headers=bd, json={"proposal_description": "Lane blocker activity", "client_name": "Lane Need Client"}).json()
    need_id = need["id"]
    need_rows = client.get("/api/bd/proposals", params={"lane": "NEED_ACTION"}, headers=bd).json()
    assert need_id in {row["id"] for row in need_rows["items"]}
    assert need_rows["lane_counts"]["NEED_ACTION"] == need_rows["count"]

    searchable = client.post("/api/bd/proposals", headers=bd, json={"proposal_description": "Harbor design activity", "project_reference": "PROJ-WEST-01", "client_name": "Lane Search Company"}).json()
    search_id = searchable["id"]
    assert client.patch(f"/api/bd/proposals/{search_id}", headers=bd, json={"fields": {"project_description": "Harbor design activity", "client_scope_of_work": "West Bay fit-out"}}).status_code == 200
    assert client.put(f"/api/bd/proposals/{search_id}/site-context", headers=bd, json={"location_text": "West Bay", "status": "UNRESOLVED"}).status_code == 200
    for params in ({"client": "Lane Search Company"}, {"activity": "Harbor design"}, {"location": "West Bay"}, {"q": "PROJ-WEST-01"}):
        result = client.get("/api/bd/proposals", params=params, headers=bd).json()
        assert search_id in {row["id"] for row in result["items"]}

    complete = client.post("/api/bd/proposals", headers=bd, json={"proposal_description": "Authority review activity", "project_reference": "PROJ-AUTH-01", "client_name": "Authority Review Client"}).json()
    authority_id = complete["id"]
    for source_type in ("TENDER_DOCUMENT", "TENDER_EMAIL", "TENDER_PHOTO", "CLIENT_DATA"):
        response = client.post(f"/api/bd/proposals/{authority_id}/sources", headers=bd, data={"source_type": source_type}, files={"file": (f"{source_type}.txt", b"authority fixture", "text/plain")})
        assert response.status_code == 200
    assert client.patch(f"/api/bd/proposals/{authority_id}", headers=bd, json={"fields": {"scope_of_work": "AMEC scope", "client_scope_of_work": "Client scope", "price": "QAR 200", "duration": "20 days", "inclusions": ["Design"], "exclusions": ["Authority fees"]}, "amec_input": {"assumption": "Human review"}}).status_code == 200
    with SessionLocal() as db:
        row = db.get(Opportunity, authority_id)
        row.status = "PROPOSAL_HANDOVER"
        db.commit()
    authority_rows = client.get("/api/bd/proposals", params={"lane": "AUTHORITY_REVIEW"}, headers=bd).json()
    assert authority_id in {row["id"] for row in authority_rows["items"]}
    detail = client.get(f"/api/bd/proposals/{authority_id}", headers=bd).json()
    assert detail["authority"]["status"] == "REVIEW_REQUIRED"
    assert detail["authority"]["government_authority"] is False
    assert detail["proposal_breakdown"]["commercial_summary"]["price"] == "QAR 200"
    assert detail["amec_input"]["assumption"] == "Human review"
