"""Focused contract tests for the final BD Proposal Forms-v2 hardening seams."""

from backend.app.db import SessionLocal
from backend.app.models import MasterContentReferenceSequence


BD = {"X-Dev-Role": "COMMERCIAL_APPROVER"}
OWNER = {"X-Dev-Role": "SYSTEM_ADMIN"}


def _ensure_templates(client):
    for ref, title, usage in (("F-0003", "Final hardening Proposal Template", "PROPOSAL_TEMPLATE"), ("F-0004", "Final hardening Proposal Checklist", "PROPOSAL_CHECKLIST")):
        rows = client.get("/api/master-content", params={"q": ref}, headers=OWNER).json()
        item = next((row for row in rows if row["ref"] == ref), None)
        if not item:
            created = client.post("/api/master-content", data={"content_type": "FORM", "ref": ref, "title": title, "description": title, "used_in": '["BD"]'}, files={"file": (f"{ref}.txt", b"synthetic final hardening content", "text/plain")}, headers=OWNER)
            assert created.status_code == 200, created.text
            item = created.json()
        bound = client.put(f"/api/master-content/{item['id']}/module-bindings", json=[{"module": "BD", "usage_type": usage}], headers=OWNER)
        assert bound.status_code == 200, bound.text


def _cleanup(client, proposal_id):
    response = client.post("/api/bd/proposals/test-support/cleanup", json=[proposal_id], headers=OWNER)
    assert response.status_code == 200, response.text


def _sources(client, proposal_id, suffix="S1"):
    for source_type in ("TENDER_DOCUMENT", "TENDER_EMAIL", "TENDER_PHOTO", "CLIENT_DATA"):
        response = client.post(
            f"/api/bd/proposals/{proposal_id}/sources",
            data={"source_type": source_type, "source_revision": suffix},
            files={"file": (f"{source_type.lower()}-{suffix}.txt", f"{source_type} {suffix}".encode(), "text/plain")},
            headers=BD,
        )
        assert response.status_code == 200, response.text


def _ready_fields():
    return {
        "scope_of_work": "AMEC structured design and permitting scope",
        "client_scope_of_work": "Client tender scope",
        "process_of_work": "Review, prepare, verify, and hand off",
        "price": "QAR 100000",
        "currency": "QAR",
        "duration": "30 days",
        "inclusions": ["Design coordination"],
        "exclusions": ["Authority fees"],
    }


def _advance_to_engineering_handoff(client, proposal_id: str):
    proceeded = client.post(f"/api/bd/proposals/{proposal_id}/proceed", headers=BD)
    assert proceeded.status_code == 200, proceeded.text
    ready = client.post(f"/api/proposals-main/proposals/{proposal_id}/engineering-ready", headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER"})
    assert ready.status_code == 200, ready.text


def test_bd_proposal_final_hardening_preserves_risk_history_and_revision_boundaries(client):
    _ensure_templates(client)
    created = client.post("/api/bd/proposals", json={"proposal_description": "Final Proposal hardening contract", "project_reference": "FINAL-HARDENING-01", "client_name": "Synthetic Final Hardening Client"}, headers=BD)
    assert created.status_code == 200, created.text
    proposal_id = created.json()["id"]
    try:
        first_reference = created.json()["proposal_reference"]
        assert first_reference.startswith("AMEC-SYN-PROP-")
        initial = client.get(f"/api/bd/proposals/{proposal_id}", headers=BD).json()
        stale_save = client.patch(f"/api/bd/proposals/{proposal_id}", json={"fields": {"project_description": "first save"}, "expected_updated_at": initial["updated_at"]}, headers=BD)
        assert stale_save.status_code == 200, stale_save.text
        rejected = client.patch(f"/api/bd/proposals/{proposal_id}", json={"fields": {"project_description": "stale overwrite"}, "expected_updated_at": initial["updated_at"]}, headers=BD)
        assert rejected.status_code == 409, rejected.text
        assert rejected.json()["detail"]["code"] == "PROPOSAL_DRAFT_CHANGED"

        _sources(client, proposal_id)
        current = client.get(f"/api/bd/proposals/{proposal_id}", headers=BD).json()
        patched = client.patch(f"/api/bd/proposals/{proposal_id}", json={"fields": _ready_fields(), "expected_updated_at": current["updated_at"]}, headers=BD)
        assert patched.status_code == 200, patched.text
        _advance_to_engineering_handoff(client, proposal_id)

        unknown = client.post(f"/api/bd/proposals/{proposal_id}/unknowns", json={"category": "CLIENT_INPUT", "statement": "Final occupancy count remains unknown", "materiality": "MATERIAL"}, headers=BD)
        assert unknown.status_code == 200, unknown.text
        unknown_id = unknown.json()["hardening"]["unknowns"][0]["id"]
        blocked = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=BD)
        assert blocked.status_code == 409, blocked.text
        assert "MATERIAL_UNKNOWN_REQUIRES_ACKNOWLEDGMENT" in {item["code"] for item in blocked.json()["detail"]["blockers"]}
        acknowledged = client.post(f"/api/bd/proposals/{proposal_id}/acknowledgments", json={"target_type": "PROPOSAL_UNKNOWN", "target_id": unknown_id, "note": "Owner reviewed the commercial risk."}, headers=BD)
        assert acknowledged.status_code == 200, acknowledged.text
        assert acknowledged.json()["hardening"]["boundaries"]["acknowledged_is_not_resolved"] is True

        conflict = client.post(f"/api/bd/proposals/{proposal_id}/conflicts", json={"field_code": "site.area", "source_a": "Tender Document", "value_a": "500 m2", "source_b": "Client Email", "value_b": "750 m2", "materiality": "MATERIAL"}, headers=BD)
        assert conflict.status_code == 200, conflict.text
        conflict_id = conflict.json()["hardening"]["conflicts"][0]["id"]
        blocked_again = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=BD)
        assert blocked_again.status_code == 409, blocked_again.text
        assert "MATERIAL_CONFLICT_REQUIRES_ACKNOWLEDGMENT" in {item["code"] for item in blocked_again.json()["detail"]["blockers"]}
        assert client.post(f"/api/bd/proposals/{proposal_id}/acknowledgments", json={"target_type": "PROPOSAL_CONFLICT", "target_id": conflict_id}, headers=BD).status_code == 200

        accepted = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=BD)
        assert accepted.status_code == 200, accepted.text
        accepted_payload = accepted.json()
        assert accepted_payload["current_revision"]["revision_number"] == 1
        assert accepted_payload["hardening"]["current_information_changed"] is False
        assert accepted_payload["current_revision"]["id"]

        replaced = client.post(f"/api/bd/proposals/{proposal_id}/sources", data={"source_type": "TENDER_DOCUMENT", "source_revision": "S2"}, files={"file": ("tender-document-S2.txt", b"changed tender document", "text/plain")}, headers=BD)
        assert replaced.status_code == 200, replaced.text
        changed = replaced.json()["proposal"]["hardening"]
        assert changed["active_staleness"]
        assert changed["current_information_changed"] is True
        revision = client.post(f"/api/bd/proposals/{proposal_id}/revisions", json={"reason": "Client requested revised tender basis"}, headers=BD)
        assert revision.status_code == 200, revision.text
        assert revision.json()["revision"]["status"] == "DRAFT"
        assert revision.json()["revision"]["base_accepted_revision_id"] == accepted_payload["current_revision"]["id"]
        reviewed = client.post(f"/api/bd/proposals/{proposal_id}/staleness/review", headers=BD)
        assert reviewed.status_code == 200, reviewed.text
        assert not reviewed.json()["hardening"]["active_staleness"]

        second = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=BD)
        assert second.status_code == 200, second.text
        assert second.json()["current_revision"]["revision_number"] == 2
        response = client.post(f"/api/bd/proposals/{proposal_id}/client-responses", json={"response_type": "CHANGE_REQUESTED", "idempotency_key": "final-response-1", "notes": "Please revise the tender basis."}, headers=BD)
        assert response.status_code == 200, response.text
        duplicate = client.post(f"/api/bd/proposals/{proposal_id}/client-responses", json={"response_type": "CHANGE_REQUESTED", "idempotency_key": "final-response-1"}, headers=BD)
        assert duplicate.status_code == 200
        assert duplicate.json()["result"] == "IDEMPOTENT"
        outcome = client.post(f"/api/bd/proposals/{proposal_id}/commercial-outcome", json={"outcome": "LOST", "reason": "Client selected another provider", "evidence_reference": "email://synthetic/client-response"}, headers=BD)
        assert outcome.status_code == 200, outcome.text
        final = outcome.json()["proposal"]
        assert final["stage"] == "CLOSED"
        assert final["hardening"]["boundaries"]["client_response_is_not_amec_accept"] is True
        assert final["hardening"]["boundaries"]["ready_close_is_not_outcome"] is True
        assert final["authority"]["government_authority"] is False
        assert client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=BD).status_code == 409

        with SessionLocal() as db:
            sequence = db.query(MasterContentReferenceSequence).filter(MasterContentReferenceSequence.content_type == "PROPOSAL_REFERENCE").one()
            assert sequence.current_value >= int(first_reference.rsplit("-", 1)[1])
    finally:
        _cleanup(client, proposal_id)
