"""Administration Contract owner-session acceptance coverage."""

import pytest

from backend.app.db import SessionLocal
from backend.app.models import (
    AuditEvent, ClientAccount, Contract, ContractAdminEvidence, ContractAdminInput,
    ContractRevision, ContractTemplateSnapshot, LineageEdge, NotificationEvent,
    Opportunity, Project, ProjectActivation, ProposalAcceptedRevision,
    ProposalIntakeArtifact, ProposalOutputArtifact, ProposalSourceEvidence,
    Quotation, QuotationRevision, WorkflowTask,
)


def headers(role: str) -> dict[str, str]:
    return {"X-Dev-Role": role}


@pytest.fixture(autouse=True)
def clean_owner_fixture():
    yield
    with SessionLocal() as db:
        proposals = db.query(Opportunity).filter(Opportunity.title.in_(["Skyline Factory Industrial", "Project Activation Fixture"])).all()
        proposal_ids = [item.id for item in proposals]
        contracts = db.query(Contract).filter(Contract.proposal_id.in_(proposal_ids)).all() if proposal_ids else []
        contract_ids = [item.id for item in contracts]
        project_ids = [item.project_id for item in contracts if item.project_id]
        if contract_ids:
            db.query(ProjectActivation).filter(ProjectActivation.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(ContractTemplateSnapshot).filter(ContractTemplateSnapshot.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(ContractAdminEvidence).filter(ContractAdminEvidence.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(ContractAdminInput).filter(ContractAdminInput.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(WorkflowTask).filter(WorkflowTask.context_type == "CONTRACT", WorkflowTask.context_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(NotificationEvent).filter(NotificationEvent.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(LineageEdge).filter(LineageEdge.project_id.in_(project_ids)).delete(synchronize_session=False) if project_ids else None
            db.query(AuditEvent).filter(AuditEvent.entity_id.in_(contract_ids + project_ids)).delete(synchronize_session=False)
            db.query(ContractRevision).filter(ContractRevision.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(Contract).filter(Contract.id.in_(contract_ids)).delete(synchronize_session=False)
            quotation_ids = [item.quotation_id for item in contracts]
            db.query(QuotationRevision).filter(QuotationRevision.quotation_id.in_(quotation_ids)).delete(synchronize_session=False)
            db.query(Quotation).filter(Quotation.id.in_(quotation_ids)).delete(synchronize_session=False)
        if proposal_ids:
            db.query(ProposalOutputArtifact).filter(ProposalOutputArtifact.proposal_id.in_(proposal_ids)).delete(synchronize_session=False)
            db.query(ProposalAcceptedRevision).filter(ProposalAcceptedRevision.proposal_id.in_(proposal_ids)).delete(synchronize_session=False)
            db.query(ProposalSourceEvidence).filter(ProposalSourceEvidence.proposal_id.in_(proposal_ids)).delete(synchronize_session=False)
            db.query(ProposalIntakeArtifact).filter(ProposalIntakeArtifact.opportunity_id.in_(proposal_ids)).delete(synchronize_session=False)
            db.query(AuditEvent).filter(AuditEvent.entity_id.in_(proposal_ids)).delete(synchronize_session=False)
            client_ids = [item.client_account_id for item in proposals if item.client_account_id]
            db.query(Opportunity).filter(Opportunity.id.in_(proposal_ids)).delete(synchronize_session=False)
            if client_ids:
                db.query(ClientAccount).filter(ClientAccount.id.in_(client_ids), ~ClientAccount.id.in_(db.query(Opportunity.client_account_id))).delete(synchronize_session=False)
        if project_ids:
            db.query(Project).filter(Project.id.in_(project_ids)).delete(synchronize_session=False)
        db.commit()


def ensure_contract_template(client):
    rows = client.get("/api/master-content", params={"q": "CT-TEST-001"}, headers=headers("SYSTEM_ADMIN"))
    item = next((row for row in rows.json() if row["ref"] == "CT-TEST-001"), None)
    if not item:
        response = client.post("/api/master-content", data={"content_type": "FORM", "ref": "CT-TEST-001", "title": "Resolver Contract Template", "description": "Canonical synthetic Contract Template", "used_in": '["ADMIN"]'}, files={"file": ("CT-TEST-001.txt", b"canonical contract template", "text/plain")}, headers=headers("SYSTEM_ADMIN"))
        assert response.status_code == 200, response.text
        item = response.json()
    binding = client.put(f"/api/master-content/{item['id']}/module-bindings", json=[{"module": "ADMIN", "usage_type": "CONTRACT_TEMPLATE"}], headers=headers("SYSTEM_ADMIN"))
    assert binding.status_code == 200, binding.text


def make_accepted_proposal(client, name="Skyline Factory Industrial"):
    for ref, title, usage in (("F-0003", "Test Proposal Template", "PROPOSAL_TEMPLATE"), ("F-0004", "Test Proposal Checklist", "PROPOSAL_CHECKLIST")):
        rows = client.get("/api/master-content", params={"q": ref}, headers=headers("SYSTEM_ADMIN"))
        item = next((row for row in rows.json() if row["ref"] == ref), None)
        if not item:
            created = client.post("/api/master-content", data={"content_type": "FORM", "ref": ref, "title": title, "description": title, "used_in": '["BD"]'}, files={"file": (f"{ref}.txt", b"proposal content", "text/plain")}, headers=headers("SYSTEM_ADMIN"))
            assert created.status_code == 200, created.text
            item = created.json()
        assert client.put(f"/api/master-content/{item['id']}/module-bindings", json=[{"module": "BD", "usage_type": usage}], headers=headers("SYSTEM_ADMIN")).status_code == 200
    created = client.post("/api/bd/proposals", headers=headers("COMMERCIAL_APPROVER"), json={"proposal_description": name, "project_reference": "PRJ-DEMO-001", "client_name": "Skyline Synthetic Client"})
    assert created.status_code == 200, created.text
    proposal_id = created.json()["id"]
    for source_type in ("TENDER_DOCUMENT", "TENDER_EMAIL", "TENDER_PHOTO", "CLIENT_DATA"):
        response = client.post(f"/api/bd/proposals/{proposal_id}/sources", headers=headers("COMMERCIAL_APPROVER"), data={"source_type": source_type}, files={"file": (f"{source_type}.txt", b"synthetic source", "text/plain")})
        assert response.status_code == 200, response.text
    response = client.patch(f"/api/bd/proposals/{proposal_id}", headers=headers("COMMERCIAL_APPROVER"), json={"fields": {"scope_of_work": "Industrial permitting scope", "client_scope_of_work": "Factory development", "price": "QAR 250000", "currency": "QAR", "duration": "90 days"}})
    assert response.status_code == 200, response.text
    accepted = client.post(f"/api/bd/proposals/{proposal_id}/accept", headers=headers("COMMERCIAL_APPROVER"))
    assert accepted.status_code == 200, accepted.text
    return proposal_id, accepted.json()["current_revision"]


def test_contract_owner_session_pins_exact_accepted_revision_and_template(client):
    ensure_contract_template(client)
    proposal_id, accepted_revision = make_accepted_proposal(client)
    created = client.post("/api/admin/contracts", headers=headers("OWNER_SPONSOR"), json={"proposal_id": proposal_id})
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["contract"]["reference"].startswith("C-DEMO-")
    assert body["origin"]["accepted_revision_id"] == accepted_revision["id"]
    assert body["origin"]["content_hash"] == accepted_revision["content_hash"]
    assert body["template"]["ref"] == "CT-TEST-001"
    assert body["template"]["version"]
    assert body["contract"]["stage"] == "DRAFT"
    rows = client.get("/api/admin/contracts", headers=headers("OWNER_SPONSOR")).json()
    row = next(item for item in rows["items"] if item["id"] == body["id"])
    assert {"contract", "contract_ref", "stage", "amount", "close_date", "open"} <= set(row)

    changed = client.patch(f"/api/bd/proposals/{proposal_id}", headers=headers("COMMERCIAL_APPROVER"), json={"fields": {"price": "QAR 999999"}})
    assert changed.status_code == 200
    reread = client.get(f"/api/admin/contracts/{body['id']}", headers=headers("OWNER_SPONSOR")).json()
    assert reread["origin"]["accepted_revision_id"] == accepted_revision["id"]
    assert reread["origin"]["content_hash"] == accepted_revision["content_hash"]
    assert reread["contract"]["amount"] == "QAR 250000"
    assert client.get(f"/api/admin/contracts/{body['id']}/history", headers=headers("OWNER_SPONSOR")).json()["rewrite_policy"] == "APPEND_ONLY"


def test_contract_manual_policy_permissions_and_explicit_project_activation(client):
    ensure_contract_template(client)
    proposal_id, _ = make_accepted_proposal(client, "Project Activation Fixture")
    created = client.post(f"/api/admin/contracts/from-proposal/{proposal_id}", headers=headers("OWNER_SPONSOR"), json={})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]
    assert client.post("/api/admin/contracts", headers=headers("OWNER_SPONSOR"), json={}).json()["detail"]["code"] == "MANUAL_CONTRACT_POLICY_REQUIRES_ACCEPTED_PROPOSAL"
    assert client.post(f"/api/admin/contracts/{contract_id}/activate-project", headers=headers("COMMERCIAL_APPROVER"), json={"project_code": "AMEC-DEMO-001", "start_date": "2026-08-12", "idempotency_key": "activation-denied"}).status_code == 403
    assert client.post(f"/api/admin/contracts/{contract_id}/activate-project", headers=headers("RESPONSIBLE_ENGINEER"), json={"project_code": "AMEC-DEMO-001", "start_date": "2026-08-12", "idempotency_key": "activation-denied-engineering"}).status_code == 403
    assert client.patch(f"/api/admin/contracts/{contract_id}", headers=headers("RESPONSIBLE_ENGINEER"), json={"amount": "QAR 1", "reason": "not authorized"}).status_code == 403
    activation = client.post(f"/api/admin/contracts/{contract_id}/activate-project", headers=headers("OWNER_SPONSOR"), json={"project_code": "AMEC-DEMO-001", "start_date": "2026-08-12", "idempotency_key": "activation-skyline-v1"})
    assert activation.status_code == 200, activation.text
    first = activation.json()
    assert first["created"] is True
    assert first["activation"]["project_code"] == "AMEC-DEMO-001"
    assert first["activation"]["start_date"] == "2026-08-12"
    assert first["contract"]["project"]["reference"] == "PRJ-DEMO-001"
    assert first["contract"]["project"]["code"] == "AMEC-DEMO-001"
    repeat = client.post(f"/api/admin/contracts/{contract_id}/activate-project", headers=headers("OWNER_SPONSOR"), json={"project_code": "AMEC-DEMO-001", "start_date": "2026-08-12", "idempotency_key": "activation-skyline-v1-repeat"})
    assert repeat.status_code == 200, repeat.text
    assert repeat.json()["created"] is False
    assert repeat.json()["activation"]["project_id"] == first["activation"]["project_id"]
    go_live = client.get("/api/admin/contracts/inputs/go-live", headers=headers("OWNER_SPONSOR"))
    assert go_live.status_code == 200
    assert len(go_live.json()["items"]) >= 22
