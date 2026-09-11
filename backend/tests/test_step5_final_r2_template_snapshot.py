"""Focused R2 coverage for the bounded pre-finalization template capture."""

from backend.app.db import SessionLocal
from backend.app.models import ContractTemplateSnapshot

from backend.tests.test_admin_contract_owner_session import ensure_contract_template, headers, make_accepted_proposal, record_checker


def test_owner_capture_is_exactly_once_and_non_owner_denied(client):
    ensure_contract_template(client)
    proposal_id, _ = make_accepted_proposal(client, "Step5 Final R2 Snapshot Fixture")
    created = client.post("/api/admin/contracts/from-proposal/" + proposal_id, headers=headers("OWNER_SPONSOR"), json={})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]

    with SessionLocal() as db:
        db.query(ContractTemplateSnapshot).filter(ContractTemplateSnapshot.contract_id == contract_id).delete(synchronize_session=False)
        db.commit()

    before = client.get("/api/admin/contracts/" + contract_id, headers=headers("OWNER_SPONSOR"))
    assert before.status_code == 200, before.text
    assert before.json()["template"] is None
    assert any(item["code"] == "CONTRACT_TEMPLATE_REQUIRED" for item in before.json()["readiness"]["blockers"])

    payload = {"reason": "Owner captured the current canonical Contract Template", "idempotency_key": "r2-capture:" + contract_id}
    captured = client.post("/api/admin/contracts/" + contract_id + "/template-snapshot", headers=headers("OWNER_SPONSOR"), json=payload)
    assert captured.status_code == 200, captured.text
    assert captured.json()["decision"] == "CAPTURED"
    assert captured.json()["captured"] is True
    assert captured.json()["snapshot"]["master_content_id"]
    assert captured.json()["snapshot"]["document_version_id"]
    assert captured.json()["snapshot"]["hash"]

    replay = client.post("/api/admin/contracts/" + contract_id + "/template-snapshot", headers=headers("OWNER_SPONSOR"), json=payload)
    assert replay.status_code == 200, replay.text
    assert replay.json()["decision"] == "ALREADY_CAPTURED"
    with SessionLocal() as db:
        assert db.query(ContractTemplateSnapshot).filter(ContractTemplateSnapshot.contract_id == contract_id).count() == 1

    for role in ("COMMERCIAL_APPROVER", "RESPONSIBLE_ENGINEER"):
        denied = client.post("/api/admin/contracts/" + contract_id + "/template-snapshot", headers=headers(role), json=payload)
        assert denied.status_code == 403


def test_finalized_contract_cannot_be_backfilled(client):
    ensure_contract_template(client)
    proposal_id, _ = make_accepted_proposal(client, "Step5 Final R2 Finalized Fixture")
    created = client.post("/api/admin/contracts/from-proposal/" + proposal_id, headers=headers("OWNER_SPONSOR"), json={})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]
    client.post("/api/admin/contracts/" + contract_id + "/template-snapshot", headers=headers("OWNER_SPONSOR"), json={"reason": "Owner captured the current canonical Contract Template", "idempotency_key": "r2-finalized-capture:" + contract_id})
    record_checker(client, contract_id)
    accepted = client.post("/api/admin/contracts/" + contract_id + "/accept", headers=headers("OWNER_SPONSOR"), json={"idempotency_key": "r2-finalized-accept:" + contract_id})
    assert accepted.status_code == 200, accepted.text
    blocked = client.post("/api/admin/contracts/" + contract_id + "/template-snapshot", headers=headers("OWNER_SPONSOR"), json={"reason": "Owner attempted a prohibited finalized backfill", "idempotency_key": "r2-finalized-replay:" + contract_id})
    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["detail"]["code"] == "FINALIZED_CONTRACT_SNAPSHOT_BACKFILL_FORBIDDEN"
