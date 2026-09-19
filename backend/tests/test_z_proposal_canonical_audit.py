from backend.app.db import SessionLocal
from backend.app.models import Opportunity, ProposalRevision


def test_canonical_audit_reads_persisted_revision_and_document_lineage(client):
    headers = {"X-Dev-Role": "SYSTEM_ADMIN"}
    created = client.post("/api/proposals/sources/2026/projects/520/create-proposal", headers=headers)
    assert created.status_code == 200, created.text
    proposal_id = created.json()["proposal_id"]

    response = client.get(
        "/api/proposals/sources/canonical-audit",
        params={"references": created.json()["proposal_reference"]},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    row = response.json()["rows"][0]
    assert row["proposal_id"] == proposal_id
    assert row["classification"] in {"CURRENT_CANONICAL_AI_GENERATED", "SOURCE_MANIFEST_STALE"}, row
    assert row["template_id"] == "AMEC-PROPOSAL-V1-TECHNICAL-REPORT"
    assert row["template_version"] == "1.0.0"
    assert row["baseline_selection_method"] == "GOVERNED_MASTER_CONTENT_TEMPLATE"
    assert row["baseline_document_version_id"]
    assert row["editor_document_version_id"]
    assert row["editor_document_version_id"] == row["rendered_and_downloaded_document_version_id"]
    assert row["editor_document_sha256"] == row["rendered_and_downloaded_document_sha256"]
    assert row["ai_provenance"]["generated_from_ai"] is True
    assert row["generation_summary"]["full_document_generation"] == "COMPLETE"


def test_canonical_audit_apply_preserves_old_revision_and_creates_new_one(client):
    headers = {"X-Dev-Role": "SYSTEM_ADMIN"}
    created = client.post("/api/proposals/sources/2026/projects/520/create-proposal", headers=headers)
    assert created.status_code == 200, created.text
    proposal_id = created.json()["proposal_id"]
    reference = created.json()["proposal_reference"]
    with SessionLocal() as db:
        revision = db.query(ProposalRevision).filter_by(proposal_id=proposal_id, status="DRAFT").order_by(ProposalRevision.revision_number.desc()).first()
        assert revision is not None
        snapshot = dict(revision.snapshot)
        snapshot["ai_provenance"] = {**(snapshot.get("ai_provenance") or {}), "generated_from_ai": False}
        revision.snapshot = snapshot
        db.commit()

    dry = client.post(
        "/api/proposals/sources/canonical-audit/regenerate",
        headers=headers,
        json={"references": [reference], "apply": False},
    )
    assert dry.status_code == 200, dry.text
    assert dry.json()["before"]["rows"][0]["classification"] == "OLD_REVISION_NEEDS_REGENERATION"

    applied = client.post(
        "/api/proposals/sources/canonical-audit/regenerate",
        headers=headers,
        json={"references": [reference], "apply": True},
    )
    assert applied.status_code == 200, applied.text
    payload = applied.json()
    assert payload["operations"][0]["result"] in {"REGENERATED", "GENERATION_REVIEW_REQUIRED", "GENERATION_FAILED_RETRYABLE"}
    with SessionLocal() as db:
        rows = db.query(ProposalRevision).filter_by(proposal_id=proposal_id).order_by(ProposalRevision.revision_number).all()
        assert len(rows) >= 2
        assert rows[0].status == "SUPERSEDED"
        assert rows[-1].id != rows[0].id
