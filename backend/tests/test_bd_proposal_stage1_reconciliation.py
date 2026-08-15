"""Focused executable contract for the Proposal Intake Stage 1 seam."""

from backend.app.db import SessionLocal
from backend.app.models import Opportunity, WorkflowTask
from sqlalchemy import select


BD = {"X-Dev-Role": "COMMERCIAL_APPROVER"}


def test_stage1_notes_site_photo_readiness_and_proceed_are_proposal_first(client):
    created = client.post("/api/bd/proposals", headers=BD, json={"proposal_description": "Stage 1 reconciliation sample", "client_name": "Synthetic Stage 1 Client"})
    assert created.status_code == 200, created.text
    proposal_id = created.json()["id"]

    blocked = client.post(f"/api/bd/proposals/{proposal_id}/proceed", headers=BD)
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "PROPOSAL_INTAKE_BLOCKED"

    source = client.post(f"/api/bd/proposals/{proposal_id}/sources", headers=BD, data={"source_type": "TENDER_EMAIL"}, files={"file": ("tender.eml", b"From: client@example.invalid\n\nPlease advise", "message/rfc822")})
    assert source.status_code == 200, source.text
    note = client.post(f"/api/bd/proposals/{proposal_id}/notes", headers=BD, json={"note_type": "CALL_NOTE", "content": "Client requested a six-month completion window."})
    assert note.status_code == 200, note.text
    site_photo = client.post(f"/api/bd/proposals/{proposal_id}/site-photos", headers=BD, files={"file": ("site.jpg", b"synthetic-site-photo", "image/jpeg")})
    assert site_photo.status_code == 200, site_photo.text
    assert site_photo.json()["site_photos"][0]["source_type"] == "SITE_PHOTO"

    ready = client.get(f"/api/bd/proposals/{proposal_id}/intake-readiness", headers=BD)
    assert ready.status_code == 200
    assert ready.json()["ready"] is True

    proceeded = client.post(f"/api/bd/proposals/{proposal_id}/proceed", headers=BD)
    assert proceeded.status_code == 200, proceeded.text
    assert proceeded.json()["proposal"]["stage"] == "PROPOSAL_PREPARATION"
    retry = client.post(f"/api/bd/proposals/{proposal_id}/proceed", headers=BD)
    assert retry.status_code == 200
    assert retry.json()["result"] == "IDEMPOTENT"
    with SessionLocal() as db:
        tasks = list(db.scalars(select(WorkflowTask).where(WorkflowTask.context_id == proposal_id, WorkflowTask.task_type == "PROPOSAL_PREPARATION")).all())
        assert len(tasks) == 1


def test_stage_gate_projection_exposes_golden_fixture_and_legacy_reconciliation_state(client):
    rows = client.get("/api/bd/proposals", headers=BD).json()["items"]
    golden = next(row for row in rows if row["proposal_reference"] == "SYN-OPP-0002")
    detail = client.get(f"/api/bd/proposals/{golden['id']}", headers=BD)
    assert detail.status_code == 200, detail.text
    payload = detail.json()
    assert payload["stage"] == "PROPOSAL_PREPARATION"
    assert payload["stage_gate"]["intake"]["state"] == "COMPLETED"
    assert any(item["event_type"] == "BD_PROPOSAL_PROCEEDED_TO_ENGINEERING" for item in payload["stage_history"])
    assert payload["sources"]
    assert "Complete intake before Engineering" not in str(payload)

    created = client.post("/api/bd/proposals", headers=BD, json={"proposal_description": "Legacy reconciliation fixture", "client_name": "Synthetic Legacy Client"})
    assert created.status_code == 200, created.text
    proposal_id = created.json()["id"]
    with SessionLocal() as db:
        item = db.get(Opportunity, proposal_id)
        assert item
        item.status = "PROPOSAL_PREPARATION"
        db.commit()
    legacy = client.get(f"/api/bd/proposals/{proposal_id}", headers=BD)
    assert legacy.status_code == 200, legacy.text
    legacy_payload = legacy.json()
    assert legacy_payload["stage_gate"]["intake"]["state"] == "RECONCILIATION_REQUIRED"
    assert legacy_payload["stage_gate"]["intake"]["message"] == "Upstream Intake reconciliation required"


def test_future_commands_are_stage_gated_until_their_owner_stage(client):
    created = client.post("/api/bd/proposals", headers=BD, json={"proposal_description": "Stage command gate sample", "client_name": "Synthetic Gate Client"})
    assert created.status_code == 200, created.text
    proposal_id = created.json()["id"]
    response = client.post(f"/api/bd/proposals/{proposal_id}/client-responses", headers=BD, json={"response_type": "ACCEPTED"})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "CLIENT_RESPONSE_STAGE_BLOCKED"
    outcome = client.post(f"/api/bd/proposals/{proposal_id}/commercial-outcome", headers=BD, json={"outcome": "WON"})
    assert outcome.status_code == 409
    assert outcome.json()["detail"]["code"] == "COMMERCIAL_OUTCOME_STAGE_BLOCKED"
    accepted = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=BD)
    assert accepted.status_code == 409
    assert accepted.json()["detail"]["code"] == "PROPOSAL_ACCEPT_STAGE_BLOCKED"
