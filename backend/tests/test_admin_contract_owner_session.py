"""Administration Contract owner-session acceptance coverage."""

import pytest

from backend.app.db import SessionLocal
from backend.app.models import (
    AssistantHandoff, AuditEvent, ClientAccount, Contract, ContractAdminEvidence, ContractAdminInput,
    ContractRevision, ContractTemplateSnapshot, LineageEdge, NotificationEvent,
    ContractClientInputRequirement, ContractDeliverableCommitment, ContractPaymentTerm,
    Opportunity, Project, ProjectActivation, ProposalAcceptedRevision,
    ProposalIntakeArtifact, ProposalOutputArtifact, ProposalSourceEvidence, ProposalSourceLink,
    Quotation, QuotationRevision, WorkflowTask,
    DocumentVersion,
    BillingPlan, BillingPlanRevision, BillingMilestone, BillingMilestoneEligibility,
    Invoice, InvoiceRevision, InvoiceMilestone, InvoiceApproval, InvoiceRequirementDecision,
    InvoiceLineItem, InvoiceReference, InvoiceApprovalRecord, InvoiceAcceptRecord,
    InvoiceIssueEvent, InvoiceDeliveryEvent, InvoiceAcknowledgment,
    PaymentReceipt, InvoicePaymentAllocation, ReceivableFollowUp, AccountingHandoff, FinanceEvidence,
)


def headers(role: str) -> dict[str, str]:
    return {"X-Dev-Role": role}


@pytest.fixture(autouse=True)
def clean_owner_fixture():
    yield
    with SessionLocal() as db:
        proposals = db.query(Opportunity).filter(Opportunity.title.in_(["Skyline Factory Industrial", "Project Activation Fixture", "Contract Reconciliation Fixture", "Contract Page Owner Sketch Delta Fixture", "External Construction Agreement Boundary"])).all()
        proposal_ids = [item.id for item in proposals]
        contracts = db.query(Contract).filter(Contract.proposal_id.in_(proposal_ids)).all() if proposal_ids else []
        contract_ids = [item.id for item in contracts]
        activation_project_ids = [item.project_id for item in db.query(ProjectActivation).filter(ProjectActivation.contract_id.in_(contract_ids)).all()] if contract_ids else []
        project_ids = list({item.project_id for item in contracts if item.project_id} | set(activation_project_ids))
        if contract_ids:
            # Billing/invoice rows are deliberately part of this shared owner
            # fixture cleanup.  PostgreSQL correctly rejects deleting a
            # ContractRevision while a BillingPlan or InvoiceRevision still
            # points at it; SQLite had previously hidden this contamination.
            billing_plan_ids = [item.id for item in db.query(BillingPlan).filter(BillingPlan.contract_id.in_(contract_ids)).all()]
            billing_plan_revision_ids = [item.id for item in db.query(BillingPlanRevision).filter(BillingPlanRevision.contract_id.in_(contract_ids)).all()]
            billing_milestone_ids = [item.id for item in db.query(BillingMilestone).filter(BillingMilestone.billing_plan_revision_id.in_(billing_plan_revision_ids)).all()] if billing_plan_revision_ids else []
            invoice_ids = [item.id for item in db.query(Invoice).filter(Invoice.contract_id.in_(contract_ids)).all()]
            invoice_revision_ids = [item.id for item in db.query(InvoiceRevision).filter(InvoiceRevision.invoice_id.in_(invoice_ids)).all()] if invoice_ids else []
            issue_event_ids = [item.id for item in db.query(InvoiceIssueEvent).filter(InvoiceIssueEvent.invoice_id.in_(invoice_ids)).all()] if invoice_ids else []
            payment_ids = [item.id for item in db.query(PaymentReceipt).filter(PaymentReceipt.contract_id.in_(contract_ids)).all()]
            if invoice_revision_ids:
                db.query(InvoiceLineItem).filter(InvoiceLineItem.invoice_revision_id.in_(invoice_revision_ids)).delete(synchronize_session=False)
                db.query(InvoiceReference).filter(InvoiceReference.invoice_revision_id.in_(invoice_revision_ids)).delete(synchronize_session=False)
                db.query(InvoiceApprovalRecord).filter(InvoiceApprovalRecord.invoice_revision_id.in_(invoice_revision_ids)).delete(synchronize_session=False)
                db.query(InvoiceAcceptRecord).filter(InvoiceAcceptRecord.invoice_revision_id.in_(invoice_revision_ids)).delete(synchronize_session=False)
                db.query(InvoiceApproval).filter(InvoiceApproval.invoice_revision_id.in_(invoice_revision_ids)).delete(synchronize_session=False)
                db.query(InvoiceAcknowledgment).filter(InvoiceAcknowledgment.issued_revision_id.in_(invoice_revision_ids)).delete(synchronize_session=False)
                db.query(InvoiceDeliveryEvent).filter(InvoiceDeliveryEvent.issued_revision_id.in_(invoice_revision_ids)).delete(synchronize_session=False)
                db.query(InvoiceIssueEvent).filter(InvoiceIssueEvent.invoice_revision_id.in_(invoice_revision_ids)).delete(synchronize_session=False)
            if issue_event_ids:
                db.query(InvoiceDeliveryEvent).filter(InvoiceDeliveryEvent.issue_event_id.in_(issue_event_ids)).delete(synchronize_session=False)
            if invoice_ids:
                db.query(InvoiceDeliveryEvent).filter(InvoiceDeliveryEvent.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
                db.query(InvoiceAcknowledgment).filter(InvoiceAcknowledgment.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
                db.query(InvoiceIssueEvent).filter(InvoiceIssueEvent.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
                db.query(InvoiceMilestone).filter(InvoiceMilestone.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
                db.query(InvoicePaymentAllocation).filter(InvoicePaymentAllocation.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
                db.query(ReceivableFollowUp).filter(ReceivableFollowUp.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
                db.query(AccountingHandoff).filter(AccountingHandoff.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
                db.query(FinanceEvidence).filter(FinanceEvidence.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
                db.query(InvoiceRevision).filter(InvoiceRevision.invoice_id.in_(invoice_ids)).delete(synchronize_session=False)
                db.query(Invoice).filter(Invoice.id.in_(invoice_ids)).delete(synchronize_session=False)
            if payment_ids:
                db.query(InvoicePaymentAllocation).filter(InvoicePaymentAllocation.payment_receipt_id.in_(payment_ids)).delete(synchronize_session=False)
                db.query(PaymentReceipt).filter(PaymentReceipt.id.in_(payment_ids)).delete(synchronize_session=False)
            if billing_milestone_ids:
                db.query(BillingMilestoneEligibility).filter(BillingMilestoneEligibility.billing_milestone_id.in_(billing_milestone_ids)).delete(synchronize_session=False)
                db.query(InvoiceLineItem).filter(InvoiceLineItem.billing_milestone_id.in_(billing_milestone_ids)).delete(synchronize_session=False)
                db.query(BillingMilestone).filter(BillingMilestone.id.in_(billing_milestone_ids)).delete(synchronize_session=False)
            if billing_plan_revision_ids:
                db.query(BillingPlanRevision).filter(BillingPlanRevision.id.in_(billing_plan_revision_ids)).delete(synchronize_session=False)
            if billing_plan_ids:
                db.query(BillingPlan).filter(BillingPlan.id.in_(billing_plan_ids)).delete(synchronize_session=False)
            db.query(InvoiceRequirementDecision).filter(InvoiceRequirementDecision.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(ProjectActivation).filter(ProjectActivation.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(ContractTemplateSnapshot).filter(ContractTemplateSnapshot.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(ContractAdminEvidence).filter(ContractAdminEvidence.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(ContractPaymentTerm).filter(ContractPaymentTerm.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(ContractDeliverableCommitment).filter(ContractDeliverableCommitment.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(ContractClientInputRequirement).filter(ContractClientInputRequirement.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            db.query(ContractAdminInput).filter(ContractAdminInput.contract_id.in_(contract_ids)).delete(synchronize_session=False)
            task_ids = [item.id for item in db.query(WorkflowTask).filter(WorkflowTask.context_type == "CONTRACT", WorkflowTask.context_id.in_(contract_ids)).all()]
            if task_ids:
                db.query(NotificationEvent).filter(NotificationEvent.workflow_task_id.in_(task_ids)).delete(synchronize_session=False)
                db.query(AssistantHandoff).filter(AssistantHandoff.workflow_task_id.in_(task_ids)).delete(synchronize_session=False)
                db.query(WorkflowTask).filter(WorkflowTask.id.in_(task_ids)).delete(synchronize_session=False)
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
            db.query(ProposalSourceLink).filter(ProposalSourceLink.proposal_id.in_(proposal_ids)).delete(synchronize_session=False)
            db.query(ProposalSourceEvidence).filter(ProposalSourceEvidence.proposal_id.in_(proposal_ids)).delete(synchronize_session=False)
            db.query(ProposalIntakeArtifact).filter(ProposalIntakeArtifact.opportunity_id.in_(proposal_ids)).delete(synchronize_session=False)
            db.query(AuditEvent).filter(AuditEvent.entity_id.in_(proposal_ids)).delete(synchronize_session=False)
            client_ids = [item.client_account_id for item in proposals if item.client_account_id]
            db.query(Opportunity).filter(Opportunity.id.in_(proposal_ids)).delete(synchronize_session=False)
            if client_ids:
                db.query(ClientAccount).filter(ClientAccount.id.in_(client_ids), ~ClientAccount.id.in_(db.query(Opportunity.client_account_id))).delete(synchronize_session=False)
        if project_ids:
            # PostgreSQL enforces the shared LineageEdge project FK; the
            # canonical fixture project may have lineage from an earlier test
            # even when it is not attached to the disposable contract set.
            db.query(LineageEdge).filter(LineageEdge.project_id.in_(project_ids)).delete(synchronize_session=False)
            db.query(Project).filter(Project.id.in_(project_ids)).delete(synchronize_session=False)
        canonical_project = db.query(Project).filter(Project.project_number == "PRJ-DEMO-001").first()
        if canonical_project:
            canonical_contracts = db.query(Contract).filter(Contract.project_id == canonical_project.id).all()
            # Preserve the durable seed chain used by the Proposal/Permit
            # cross-module regression. Owner-session fixtures may temporarily
            # attach disposable contracts to the same canonical project, but
            # cleanup must never remove SYN-CTR-0001 or its Project.
            if any(item.contract_reference == "SYN-CTR-0001" for item in canonical_contracts):
                canonical_contracts = [item for item in canonical_contracts if item.contract_reference != "SYN-CTR-0001"]
            canonical_contract_ids = [item.id for item in canonical_contracts]
            if canonical_contract_ids:
                canonical_plan_ids = [item.id for item in db.query(BillingPlan).filter(BillingPlan.contract_id.in_(canonical_contract_ids)).all()]
                canonical_plan_revision_ids = [item.id for item in db.query(BillingPlanRevision).filter(BillingPlanRevision.contract_id.in_(canonical_contract_ids)).all()]
                canonical_milestone_ids = [item.id for item in db.query(BillingMilestone).filter(BillingMilestone.billing_plan_revision_id.in_(canonical_plan_revision_ids)).all()] if canonical_plan_revision_ids else []
                canonical_invoice_ids = [item.id for item in db.query(Invoice).filter(Invoice.contract_id.in_(canonical_contract_ids)).all()]
                canonical_invoice_revision_ids = [item.id for item in db.query(InvoiceRevision).filter(InvoiceRevision.invoice_id.in_(canonical_invoice_ids)).all()] if canonical_invoice_ids else []
                canonical_issue_ids = [item.id for item in db.query(InvoiceIssueEvent).filter(InvoiceIssueEvent.invoice_id.in_(canonical_invoice_ids)).all()] if canonical_invoice_ids else []
                if canonical_invoice_revision_ids:
                    db.query(InvoiceLineItem).filter(InvoiceLineItem.invoice_revision_id.in_(canonical_invoice_revision_ids)).delete(synchronize_session=False)
                    db.query(InvoiceReference).filter(InvoiceReference.invoice_revision_id.in_(canonical_invoice_revision_ids)).delete(synchronize_session=False)
                    db.query(InvoiceApprovalRecord).filter(InvoiceApprovalRecord.invoice_revision_id.in_(canonical_invoice_revision_ids)).delete(synchronize_session=False)
                    db.query(InvoiceAcceptRecord).filter(InvoiceAcceptRecord.invoice_revision_id.in_(canonical_invoice_revision_ids)).delete(synchronize_session=False)
                    db.query(InvoiceApproval).filter(InvoiceApproval.invoice_revision_id.in_(canonical_invoice_revision_ids)).delete(synchronize_session=False)
                if canonical_issue_ids:
                    db.query(InvoiceDeliveryEvent).filter(InvoiceDeliveryEvent.issue_event_id.in_(canonical_issue_ids)).delete(synchronize_session=False)
                if canonical_invoice_ids:
                    db.query(InvoiceDeliveryEvent).filter(InvoiceDeliveryEvent.invoice_id.in_(canonical_invoice_ids)).delete(synchronize_session=False)
                    db.query(InvoiceAcknowledgment).filter(InvoiceAcknowledgment.invoice_id.in_(canonical_invoice_ids)).delete(synchronize_session=False)
                    db.query(InvoiceIssueEvent).filter(InvoiceIssueEvent.invoice_id.in_(canonical_invoice_ids)).delete(synchronize_session=False)
                    db.query(InvoiceMilestone).filter(InvoiceMilestone.invoice_id.in_(canonical_invoice_ids)).delete(synchronize_session=False)
                    db.query(InvoicePaymentAllocation).filter(InvoicePaymentAllocation.invoice_id.in_(canonical_invoice_ids)).delete(synchronize_session=False)
                    db.query(ReceivableFollowUp).filter(ReceivableFollowUp.invoice_id.in_(canonical_invoice_ids)).delete(synchronize_session=False)
                    db.query(AccountingHandoff).filter(AccountingHandoff.invoice_id.in_(canonical_invoice_ids)).delete(synchronize_session=False)
                    db.query(FinanceEvidence).filter(FinanceEvidence.invoice_id.in_(canonical_invoice_ids)).delete(synchronize_session=False)
                    db.query(InvoiceRevision).filter(InvoiceRevision.invoice_id.in_(canonical_invoice_ids)).delete(synchronize_session=False)
                    db.query(Invoice).filter(Invoice.id.in_(canonical_invoice_ids)).delete(synchronize_session=False)
                if canonical_milestone_ids:
                    db.query(BillingMilestoneEligibility).filter(BillingMilestoneEligibility.billing_milestone_id.in_(canonical_milestone_ids)).delete(synchronize_session=False)
                    db.query(InvoiceLineItem).filter(InvoiceLineItem.billing_milestone_id.in_(canonical_milestone_ids)).delete(synchronize_session=False)
                    db.query(BillingMilestone).filter(BillingMilestone.id.in_(canonical_milestone_ids)).delete(synchronize_session=False)
                if canonical_plan_revision_ids:
                    db.query(BillingPlanRevision).filter(BillingPlanRevision.id.in_(canonical_plan_revision_ids)).delete(synchronize_session=False)
                if canonical_plan_ids:
                    db.query(BillingPlan).filter(BillingPlan.id.in_(canonical_plan_ids)).delete(synchronize_session=False)
                db.query(InvoiceRequirementDecision).filter(InvoiceRequirementDecision.contract_id.in_(canonical_contract_ids)).delete(synchronize_session=False)
                db.query(ProjectActivation).filter(ProjectActivation.contract_id.in_(canonical_contract_ids)).delete(synchronize_session=False)
                db.query(ContractTemplateSnapshot).filter(ContractTemplateSnapshot.contract_id.in_(canonical_contract_ids)).delete(synchronize_session=False)
                db.query(ContractAdminEvidence).filter(ContractAdminEvidence.contract_id.in_(canonical_contract_ids)).delete(synchronize_session=False)
                db.query(ContractPaymentTerm).filter(ContractPaymentTerm.contract_id.in_(canonical_contract_ids)).delete(synchronize_session=False)
                db.query(ContractDeliverableCommitment).filter(ContractDeliverableCommitment.contract_id.in_(canonical_contract_ids)).delete(synchronize_session=False)
                db.query(ContractClientInputRequirement).filter(ContractClientInputRequirement.contract_id.in_(canonical_contract_ids)).delete(synchronize_session=False)
                db.query(ContractAdminInput).filter(ContractAdminInput.contract_id.in_(canonical_contract_ids)).delete(synchronize_session=False)
                db.query(NotificationEvent).filter(NotificationEvent.contract_id.in_(canonical_contract_ids)).delete(synchronize_session=False)
                task_ids = [item.id for item in db.query(WorkflowTask).filter(WorkflowTask.context_type == "CONTRACT", WorkflowTask.context_id.in_(canonical_contract_ids)).all()]
                if task_ids:
                    db.query(NotificationEvent).filter(NotificationEvent.workflow_task_id.in_(task_ids)).delete(synchronize_session=False)
                    db.query(AssistantHandoff).filter(AssistantHandoff.workflow_task_id.in_(task_ids)).delete(synchronize_session=False)
                    db.query(WorkflowTask).filter(WorkflowTask.id.in_(task_ids)).delete(synchronize_session=False)
                db.query(AuditEvent).filter(AuditEvent.entity_id.in_(canonical_contract_ids)).delete(synchronize_session=False)
                db.query(ContractRevision).filter(ContractRevision.contract_id.in_(canonical_contract_ids)).delete(synchronize_session=False)
                db.query(Contract).filter(Contract.id.in_(canonical_contract_ids)).delete(synchronize_session=False)
            if not db.query(Contract).filter(Contract.project_id == canonical_project.id, Contract.contract_reference == "SYN-CTR-0001").first():
                db.query(LineageEdge).filter(LineageEdge.project_id == canonical_project.id).delete(synchronize_session=False)
                db.query(Project).filter(Project.id == canonical_project.id).delete(synchronize_session=False)
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


def test_contract_reconciliation_read_model_and_billing_seam(client):
    ensure_contract_template(client)
    proposal_id, _ = make_accepted_proposal(client, "Contract Reconciliation Fixture")
    created = client.post("/api/admin/contracts", headers=headers("OWNER_SPONSOR"), json={"proposal_id": proposal_id})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]
    patched = client.patch(f"/api/admin/contracts/{contract_id}", headers=headers("OWNER_SPONSOR"), json={"payment_condition_text": "30% advance; 70% on approved deliverable", "contracted_scope_text": "Detailed permit design and authority coordination", "reason": "Owner recorded Contract commercial terms"})
    assert patched.status_code == 200, patched.text
    term = client.post(f"/api/admin/contracts/{contract_id}/commercial-terms", headers=headers("OWNER_SPONSOR"), json={"sequence": 1, "label": "Advance", "term_text": "30% advance", "percentage": "30", "currency": "QAR", "human_verified": True})
    assert term.status_code == 200, term.text
    assert term.json()["payment_terms"][0]["status"] == "VERIFIED"
    deliverable = client.post(f"/api/admin/contracts/{contract_id}/deliverables", headers=headers("OWNER_SPONSOR"), json={"sequence": 1, "name": "Permit design package", "description": "Detailed works package"})
    assert deliverable.status_code == 200, deliverable.text
    client_input = client.post(f"/api/admin/contracts/{contract_id}/client-inputs", headers=headers("OWNER_SPONSOR"), json={"sequence": 1, "title": "Signed LPO", "source_type": "CLIENT_DOCUMENT"})
    assert client_input.status_code == 200, client_input.text
    missing_exact = client.post(f"/api/admin/contracts/{contract_id}/evidence", headers=headers("OWNER_SPONSOR"), json={"evidence_type": "LPO", "source_role": "LPO", "source_reference": "lpo.pdf"})
    assert missing_exact.status_code == 422
    detail = client.get(f"/api/admin/contracts/{contract_id}", headers=headers("OWNER_SPONSOR"))
    assert detail.status_code == 200
    body = detail.json()
    assert body["contract"]["payment_condition_text"] == "30% advance; 70% on approved deliverable"
    assert body["deliverables"][0]["name"] == "Permit design package"
    assert body["client_inputs"][0]["title"] == "Signed LPO"
    before = client.get(f"/api/admin/contracts/{contract_id}/billing-context", headers=headers("OWNER_SPONSOR")).json()
    assert before["status"] == "NEEDS_CONTRACT_AUTHORITY"
    authority = client.post(f"/api/admin/contracts/{contract_id}/authority", headers=headers("OWNER_SPONSOR"), json={"decision": "APPROVE", "reason": "Owner authority review complete"})
    assert authority.status_code == 200, authority.text
    activation = client.post(f"/api/admin/contracts/{contract_id}/activate-project", headers=headers("OWNER_SPONSOR"), json={"project_code": "AMEC-RECON-001", "start_date": "2026-08-13", "idempotency_key": "reconciliation-activation-v1"})
    assert activation.status_code == 200, activation.text
    billing = client.get(f"/api/admin/contracts/{contract_id}/billing-context", headers=headers("OWNER_SPONSOR")).json()
    assert billing["status"] == "READY_FOR_BILLING_SETUP"
    assert billing["invoice_created"] is False
    assert billing["billing_milestone_created"] is False
    assert billing["project_activation_status"] == "ACTIVE"
    assert billing["project_required_policy"] == "REQUIRED"
    assert billing["revision_selection"]["exact_revision_pinned"] is True
    assert billing["contract_project_context_snapshot"]["canonical_project_created"] is True
    assert billing["external_agreement_consumption"] == "AMEC_PROFESSIONAL_SERVICES_CONTRACT_ONLY"
    immutable = client.patch(f"/api/admin/contracts/{contract_id}", headers=headers("OWNER_SPONSOR"), json={"amount": "QAR 999", "reason": "Should be blocked after approval"})
    assert immutable.status_code == 409


def test_contract_page_owner_sketch_delta_documents_fields_sources_and_acceptance(client):
    ensure_contract_template(client)
    proposal_id, accepted_revision = make_accepted_proposal(client, "Contract Page Owner Sketch Delta Fixture")
    created = client.post("/api/admin/contracts", headers=headers("OWNER_SPONSOR"), json={"proposal_id": proposal_id})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]

    initial = client.get(f"/api/admin/contracts/{contract_id}", headers=headers("OWNER_SPONSOR"))
    assert initial.status_code == 200, initial.text
    body = initial.json()
    assert {"client_fields", "field_lineage", "client_document", "lpo", "documents_needed", "deliverable_commitments", "source_panel"} <= set(body)
    assert body["client_fields"]["pin_number"]["display_value"] == "Not configured"
    assert body["client_fields"]["pin_number"]["source"] == "OWNER_DEFINITION_REQUIRED"
    assert {item["label"] for item in body["source_panel"]} == {"Contract", "Document List", "Accepted Proposal", "LPO", "Client Document", "Contract Template"}

    client_document = client.post(f"/api/admin/contracts/{contract_id}/documents", headers=headers("OWNER_SPONSOR"), json={"source_role": "CLIENT_DOCUMENT", "source_filename": "client-document-v1.txt", "content": "client document version one"})
    assert client_document.status_code == 200, client_document.text
    client_v1 = client_document.json()
    assert client_v1["version_number"] == 1
    client_v2 = client.post(f"/api/admin/contracts/{contract_id}/documents", headers=headers("OWNER_SPONSOR"), json={"source_role": "CLIENT_DOCUMENT", "source_filename": "client-document-v2.txt", "content": "client document version two"})
    assert client_v2.status_code == 200, client_v2.text
    assert client_v2.json()["version_number"] == 2
    lpo = client.post(f"/api/admin/contracts/{contract_id}/documents", headers=headers("OWNER_SPONSOR"), json={"source_role": "LPO", "source_filename": "lpo.txt", "content": "purchase order"})
    assert lpo.status_code == 200, lpo.text
    downloaded = client.get(f"/api/admin/contracts/{contract_id}/documents/{client_v2.json()['document_version_id']}/download", headers=headers("OWNER_SPONSOR"))
    assert downloaded.status_code == 200
    assert downloaded.content == b"client document version two"
    with SessionLocal() as db:
        assert db.query(DocumentVersion).filter(DocumentVersion.document_id == client_v1["document_id"]).count() == 2

    changed_fields = client.patch(f"/api/admin/contracts/{contract_id}/client-fields", headers=headers("OWNER_SPONSOR"), json={"client_name": "Contract-side Client", "client_company": "Contract-side Company", "cr_number": "CR-DELTA", "mobile": "+974 5555 0101", "client_email": "owner@example.test", "reason": "Owner confirmed Contract party fields"})
    assert changed_fields.status_code == 200, changed_fields.text
    changed = changed_fields.json()
    assert changed["current_revision"]["revision_number"] == 2
    assert changed["client_fields"]["client_name"]["value"] == "Contract-side Client"
    assert changed["client_fields"]["client_name"]["source"] == "CONTRACT_REVISION"
    assert changed["origin"]["accepted_revision_id"] == accepted_revision["id"]

    accepted = client.post(f"/api/admin/contracts/{contract_id}/accept", headers=headers("OWNER_SPONSOR"), json={"idempotency_key": f"accept:{contract_id}"})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["decision"] == "ACCEPTED"
    assert accepted.json()["contract"]["current_revision"]["status"] == "FINALIZED"
    assert accepted.json()["contract"]["activation"] is None
    repeat = client.post(f"/api/admin/contracts/{contract_id}/accept", headers=headers("OWNER_SPONSOR"), json={"idempotency_key": f"accept:{contract_id}"})
    assert repeat.status_code == 200
    assert repeat.json()["decision"] == "ALREADY_ACCEPTED"
    assert client.post(f"/api/admin/contracts/{contract_id}/accept", headers=headers("RESPONSIBLE_ENGINEER"), json={}).status_code == 403
    assert client.patch(f"/api/admin/contracts/{contract_id}/client-fields", headers=headers("OWNER_SPONSOR"), json={"client_name": "Blocked after accept", "reason": "Expected immutable finalized revision"}).status_code == 409
