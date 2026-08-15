"""Focused executable contract for the Proposal Intake Stage 1 seam."""

from backend.app.db import SessionLocal
from backend.app.models import WorkflowTask
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
