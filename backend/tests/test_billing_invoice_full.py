"""Contract-driven Billing / Invoice lifecycle acceptance coverage."""

from decimal import Decimal

import pytest

from backend.app.db import SessionLocal
from backend.app.models import Contract, InvoiceRevision, Project
from backend.tests.test_admin_contract_owner_session import clean_owner_fixture, ensure_contract_template, headers, make_accepted_proposal


@pytest.fixture(scope="module", autouse=True)
def restore_seed_after_billing_module():
    """Prevent billing fixtures from contaminating later cross-module tests."""
    yield
    cleanup = clean_owner_fixture.__wrapped__()
    next(cleanup)
    try:
        next(cleanup)
    except StopIteration:
        pass


def _activated_contract(client, name: str = "Billing Lifecycle Fixture"):
    ensure_contract_template(client)
    proposal_id, _accepted_revision = make_accepted_proposal(client, name)
    created = client.post("/api/admin/contracts/from-proposal/%s" % proposal_id, headers=headers("OWNER_SPONSOR"), json={})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]
    checked = client.post(f"/api/admin/contracts/{contract_id}/checker", headers={**headers("OWNER_SPONSOR"), "X-Dev-Actor": "billing-contract-checker"}, json={"reason": "Synthetic billing fixture independent check"})
    assert checked.status_code == 200, checked.text
    authority = client.post(f"/api/admin/contracts/{contract_id}/authority", headers=headers("OWNER_SPONSOR"), json={"decision": "APPROVE", "reason": "Billing fixture authority"})
    assert authority.status_code == 200, authority.text
    accepted = client.post(f"/api/admin/contracts/{contract_id}/accept", headers=headers("OWNER_SPONSOR"), json={"idempotency_key": f"accept-billing-contract:{contract_id}"})
    assert accepted.status_code == 200, accepted.text
    uploaded = client.post(f"/api/admin/contracts/{contract_id}/documents", headers={**headers("OWNER_SPONSOR"), "X-Dev-Actor": "billing-contract-authority"}, json={"source_role": "EXECUTED_CONTRACT", "source_filename": "billing-executed-contract.txt", "content": f"synthetic executed billing copy for {contract_id}", "reason": "Billing activation prerequisite"})
    assert uploaded.status_code == 200, uploaded.text
    executed = client.post(f"/api/admin/contracts/{contract_id}/executed-evidence", headers={**headers("OWNER_SPONSOR"), "X-Dev-Actor": "billing-contract-authority"}, json={"document_version_id": uploaded.json()["document_version_id"], "evidence_reference": f"synthetic://billing-executed/{contract_id}", "reason": "Billing activation prerequisite"})
    assert executed.status_code == 200, executed.text
    activated = client.post(
        f"/api/admin/contracts/{contract_id}/activate-project",
        headers=headers("OWNER_SPONSOR"),
        json={"project_code": f"AMEC-BILLING-{contract_id[:8].upper()}", "start_date": "2026-08-13", "idempotency_key": f"activate-{contract_id}"},
    )
    assert activated.status_code == 200, activated.text
    return contract_id


def test_billing_invoice_accept_issue_receivable_payment_and_separation(client):
    contract_id = _activated_contract(client, "Skyline Factory Industrial")
    before = client.get("/api/billing/invoices", headers=headers("OWNER_SPONSOR")).json()["total"]

    plan_response = client.post("/api/billing/plans", headers=headers("COMMERCIAL_APPROVER"), json={"contract_id": contract_id})
    assert plan_response.status_code == 200, plan_response.text
    plan = plan_response.json()["plan"]
    plan_revision = plan_response.json()["revision"]

    first = client.post(
        f"/api/billing/plan-revisions/{plan_revision['id']}/milestones",
        headers=headers("COMMERCIAL_APPROVER"),
        json={"name": "Mobilization", "basis_type": "FIXED_AMOUNT", "basis_amount": "125000", "trigger_type": "MANUAL_EVIDENCE", "due_days": 30},
    )
    second = client.post(
        f"/api/billing/plan-revisions/{plan_revision['id']}/milestones",
        headers=headers("COMMERCIAL_APPROVER"),
        json={"name": "Completion", "basis_type": "FIXED_AMOUNT", "basis_amount": "125000", "trigger_type": "HANDOVER_ACCEPTED", "due_days": 30},
    )
    assert first.status_code == second.status_code == 200, (first.text, second.text)
    first_id = first.json()["id"]
    second_id = second.json()["id"]
    assert client.get("/api/billing/invoices", headers=headers("OWNER_SPONSOR")).json()["total"] == before

    assert client.post(f"/api/billing/milestones/{first_id}/eligibility", headers=headers("OWNER_SPONSOR"), json={"decision": "ELIGIBLE", "trigger_evidence": {"basis": "owner-reviewed"}}).status_code == 200
    assert client.post(f"/api/billing/plans/{plan['id']}/activate", headers=headers("OWNER_SPONSOR"), json={}).status_code == 200
    blocked = client.post("/api/billing/invoices", headers=headers("COMMERCIAL_APPROVER"), json={"milestone_ids": [second_id]})
    assert blocked.status_code == 409 and blocked.json()["detail"]["code"] == "ELIGIBLE_MILESTONES_REQUIRED"

    created = client.post(
        "/api/billing/invoices",
        headers=headers("COMMERCIAL_APPROVER"),
        json={"milestone_ids": [first_id], "due_date_basis": "DELIVERY_DATE", "due_days": 30, "planned_collection_date": "2026-08-20", "service_period": "2026-08", "informational_lines": [{"description": "Full Contract Amount (display only)", "calculated_line_amount": "250000"}]},
    )
    assert created.status_code == 200, created.text
    invoice = created.json()["invoice"]
    revision = created.json()["revision"]
    assert Decimal(str(revision["gross_charge_total"])) == Decimal("125000.00")
    assert Decimal(str(revision["payable_total"])) == Decimal("125000.00")
    assert invoice["invoice_ref_status"] == "NOT_ALLOCATED"

    assert client.post(f"/api/billing/invoice-revisions/{revision['id']}/references", headers=headers("COMMERCIAL_APPROVER"), json={"reference_type": "APPROVAL_REF", "value": "SYN-APP-001", "status": "VERIFIED"}).status_code == 200
    assert client.post(f"/api/billing/invoice-revisions/{revision['id']}/approvals", headers=headers("OWNER_SPONSOR"), json={"approval_type": "CLIENT_REFERENCE", "approval_reference": "SYN-APP-001", "status": "VERIFIED"}).status_code == 200
    assert client.post(f"/api/billing/invoice-revisions/{revision['id']}/accept", headers=headers("COMMERCIAL_APPROVER"), json={"idempotency_key": "accept-denied"}).status_code == 403
    accepted = client.post(f"/api/billing/invoice-revisions/{revision['id']}/accept", headers=headers("OWNER_SPONSOR"), json={"idempotency_key": "accept-billing-001"})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["invoice"]["status"] == "ACCEPTED_INTERNAL"

    account = client.post("/api/billing/financial-accounts", headers=headers("OWNER_SPONSOR"), json={"legal_entity_ref": "AMEC-SYNTHETIC-ENTITY", "account_name": "Synthetic Receipts"})
    assert account.status_code == 200, account.text
    version = client.post(f"/api/billing/financial-accounts/{account.json()['id']}/versions", headers=headers("OWNER_SPONSOR"), json={"bank_name": "Synthetic Bank", "account_name": "Synthetic Receipts", "account_reference": "SYNTHETIC-ACCOUNT-001", "currency": "QAR", "effective_from": "2026-01-01"})
    assert version.status_code == 200, version.text
    version_id = version.json()["id"]
    assert "SYNTHETIC-ACCOUNT-001" not in version.text
    assert client.post(f"/api/billing/financial-account-versions/{version_id}/approve", headers=headers("OWNER_SPONSOR"), json={}).status_code == 200

    issued = client.post(f"/api/billing/invoice-revisions/{revision['id']}/issue", headers=headers("OWNER_SPONSOR"), json={"idempotency_key": "issue-billing-001", "financial_account_version_id": version_id})
    assert issued.status_code == 200, issued.text
    issue = issued.json()["issue"]
    assert issued.json()["invoice"]["status"] == "ISSUED"
    assert issue["official_invoice_ref"].startswith("INV-AMEC-")
    assert issued.json()["financial_account"]["account_reference"].startswith("••••")

    receivable = client.get(f"/api/billing/invoices/{invoice['id']}/receivable", headers=headers("OWNER_SPONSOR")).json()
    assert receivable["state"] == "AWAITING_DUE_EVENT"
    missing_delivery_proof = client.post(f"/api/billing/invoice-revisions/{revision['id']}/deliveries", headers=headers("OWNER_SPONSOR"), json={"channel": "EMAIL", "idempotency_key": "delivery-billing-missing-proof"})
    assert missing_delivery_proof.status_code == 409
    assert missing_delivery_proof.json()["detail"]["code"] == "DELIVERY_EVIDENCE_REQUIRED"
    delivery = client.post(f"/api/billing/invoice-revisions/{revision['id']}/deliveries", headers=headers("OWNER_SPONSOR"), json={"channel": "EMAIL", "recipient_snapshot": {"party_ref": "SYN-CLIENT"}, "delivered_at": "2026-08-14T10:00:00+00:00", "delivery_reference": "SYN-DELIVERY-001", "idempotency_key": "delivery-billing-001"})
    assert delivery.status_code == 200, delivery.text
    assert delivery.json()["revision"]["due_date"] == "2026-09-13"
    duplicate_delivery = client.post(f"/api/billing/invoice-revisions/{revision['id']}/deliveries", headers=headers("OWNER_SPONSOR"), json={"channel": "EMAIL", "idempotency_key": "delivery-billing-001"})
    assert duplicate_delivery.status_code == 200
    assert duplicate_delivery.json()["delivery"]["id"] == delivery.json()["delivery"]["id"]
    communications = client.get(f"/api/billing/invoices/{invoice['id']}/communications", headers=headers("OWNER_SPONSOR")).json()
    assert communications["communication_state"] == "DELIVERED" and len(communications["deliveries"]) == 1
    acknowledgment = client.post(f"/api/billing/invoices/{invoice['id']}/acknowledgments", headers=headers("OWNER_SPONSOR"), json={"acknowledgment_reference": "SYN-ACK-001", "acknowledged_at": "2026-08-15T10:00:00+00:00", "idempotency_key": "ack-billing-001"})
    assert acknowledgment.status_code == 200, acknowledgment.text
    assert acknowledgment.json()["receivable"]["communication_state"] == "ACKNOWLEDGED"
    observed_without_evidence = client.post("/api/billing/payments", headers=headers("COMMERCIAL_APPROVER"), json={"invoice_id": invoice["id"], "amount": "1000", "currency": "QAR", "reference": "SYN-PAY-MISSING-EVIDENCE", "idempotency_key": "payment-billing-missing-evidence"})
    assert observed_without_evidence.status_code == 200, observed_without_evidence.text
    blocked_verification = client.post(f"/api/billing/payments/{observed_without_evidence.json()['id']}/verify", headers=headers("OWNER_SPONSOR"), json={})
    assert blocked_verification.status_code == 409
    assert blocked_verification.json()["detail"]["code"] == "PAYMENT_METHOD_REQUIRED"
    payment = client.post("/api/billing/payments", headers=headers("COMMERCIAL_APPROVER"), json={"invoice_id": invoice["id"], "amount": "50000", "currency": "QAR", "reference": "SYN-PAY-001", "payment_method": "BANK_TRANSFER", "evidence_reference": "synthetic://bank-transfer-proof-001", "idempotency_key": "payment-billing-001"})
    assert payment.status_code == 200, payment.text
    payment_id = payment.json()["id"]
    assert client.get(f"/api/billing/invoices/{invoice['id']}/receivable", headers=headers("OWNER_SPONSOR")).json()["verified_paid_amount"] == "0.00"
    assert client.post(f"/api/billing/payments/{payment_id}/verify", headers=headers("OWNER_SPONSOR"), json={}).status_code == 200
    allocated = client.post(f"/api/billing/payments/{payment_id}/allocate", headers=headers("OWNER_SPONSOR"), json={"invoice_id": invoice["id"], "allocated_amount": "50000", "idempotency_key": "allocation-billing-001"})
    assert allocated.status_code == 200, allocated.text
    assert allocated.json()["receivable"]["state"] == "PARTIALLY_PAID"
    follow_up = client.post(f"/api/billing/invoices/{invoice['id']}/follow-ups", headers=headers("COMMERCIAL_APPROVER"), json={"note": "Synthetic follow-up only", "channel": "INTERNAL_NOTE"})
    assert follow_up.status_code == 200, follow_up.text
    assert client.get(f"/api/billing/invoices/{invoice['id']}/receivable", headers=headers("OWNER_SPONSOR")).json()["state"] == "PARTIALLY_PAID"
    reversed_payment = client.post(f"/api/billing/payments/{payment_id}/reverse", headers=headers("OWNER_SPONSOR"), json={"reason": "Synthetic bank confirmation withdrawn", "evidence_reference": "synthetic://reversal-proof-001", "idempotency_key": "reversal-billing-001"})
    assert reversed_payment.status_code == 200, reversed_payment.text
    assert reversed_payment.json()["payment"]["verification_status"] == "REVERSED"
    assert client.get(f"/api/billing/invoices/{invoice['id']}/receivable", headers=headers("OWNER_SPONSOR")).json()["verified_paid_amount"] == "0.00"
    resolved = client.post(f"/api/billing/invoices/{invoice['id']}/resolutions", headers=headers("OWNER_SPONSOR"), json={"resolution_type": "WRITTEN_OFF", "amount": "125000", "currency": "QAR", "reason": "Synthetic non-cash closure", "approval_reference": "SYN-RESOLUTION-001", "idempotency_key": "resolution-billing-001"})
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["receivable"]["state"] == "RESOLVED_NON_CASH"
    assert resolved.json()["receivable"]["outstanding_amount"] == "0.00"
    with SessionLocal() as db:
        persisted_revision = db.get(InvoiceRevision, revision["id"])
        assert persisted_revision.actual_collection_date is not None
        assert persisted_revision.actual_collection_date_source == "NON_CASH_RECEIVABLE_RESOLUTION"
        assert persisted_revision.planned_collection_date.isoformat() == "2026-08-20"
        assert persisted_revision.service_period == "2026-08"
        project = db.get(Project, invoice["project_id"])
        office_id = project.office_id
    project_projection = client.get(f"/api/billing/projects/{invoice['project_id']}/financial-projection", headers=headers("OWNER_SPONSOR"))
    assert project_projection.status_code == 200, project_projection.text
    assert project_projection.json()["non_cash_resolved_amount"] == "125000.00"
    assert project_projection.json()["outstanding_amount"] == "0.00"
    assert project_projection.json()["billing_completion_state"] == "COMPLETE"
    assert project_projection.json()["financial_completion_state"] == "COMPLETE"
    assert project_projection.json()["billing_complete"] is True
    assert project_projection.json()["financial_complete"] is True
    register = client.get(f"/api/billing/offices/{office_id}/invoice-register", headers=headers("OWNER_SPONSOR"))
    assert register.status_code == 200 and register.json()["total"] >= 1
    open_receivables = client.get(f"/api/billing/offices/{office_id}/open-receivables", headers=headers("OWNER_SPONSOR"))
    assert open_receivables.status_code == 200
    assert all(item["outstanding_amount"] != "0.00" for item in open_receivables.json()["items"])
    assert client.get(f"/api/billing/invoices/{invoice['id']}/download", headers=headers("COMMERCIAL_APPROVER")).status_code == 200


def test_client_prepayment_is_recorded_verified_and_kept_as_unallocated_credit(client):
    contract_id = _activated_contract(client, "Client Prepayment Fixture")
    recorded = client.post(
        "/api/billing/payments",
        headers=headers("COMMERCIAL_APPROVER"),
        json={
            "contract_id": contract_id,
            "project_id": None,
            "amount": "5000",
            "currency": "QAR",
            "reference": "SYN-PREPAY-001",
            "payment_method": "BANK_TRANSFER",
            "evidence_reference": "synthetic://prepayment-proof-001",
            "idempotency_key": "prepayment-001",
        },
    )
    assert recorded.status_code == 200, recorded.text
    payment_id = recorded.json()["id"]
    assert recorded.json()["credit"]["state"] == "CLIENT_PREPAYMENT_RECORDED"
    assert recorded.json()["credit"]["unallocated_balance"] == "0.00"

    verified = client.post(f"/api/billing/payments/{payment_id}/verify", headers=headers("OWNER_SPONSOR"), json={})
    assert verified.status_code == 200, verified.text
    credit = client.get(f"/api/billing/payments/{payment_id}/unallocated-credit", headers=headers("OWNER_SPONSOR"))
    assert credit.status_code == 200, credit.text
    assert credit.json()["state"] == "UNALLOCATED_CLIENT_CREDIT"
    assert credit.json()["unallocated_balance"] == "5000.00"
    assert credit.json()["project_id"] is None

    custody_payment = client.post(
        "/api/billing/payments",
        headers=headers("COMMERCIAL_APPROVER"),
        json={
            "contract_id": contract_id,
            "project_id": None,
            "amount": "1250",
            "currency": "QAR",
            "reference": "SYN-CUSTODY-001",
            "payment_method": "ALTERNATE_RECIPIENT",
            "evidence_reference": "synthetic://custody-proof-001",
            "custodian_context_json": {
                "payment_destination": "Synthetic alternate recipient",
                "received_by": "synthetic-receiver",
                "custodian": "synthetic-custodian",
                "recipient_name": "Synthetic alternate recipient",
                "actual_recipient_context": "Synthetic approved alternate recipient",
                "custody_reference": "SYN-CUSTODY-REF-001",
            },
            "idempotency_key": "custody-payment-001",
        },
    )
    assert custody_payment.status_code == 200, custody_payment.text
    assert custody_payment.json()["custodian_context_json"]["custody_reference"] == "SYN-CUSTODY-REF-001"
    custody_verified = client.post(f"/api/billing/payments/{custody_payment.json()['id']}/verify", headers=headers("OWNER_SPONSOR"), json={})
    assert custody_verified.status_code == 200, custody_verified.text


def test_billing_rejects_manual_invoice_and_cross_role_issue(client):
    assert client.post("/api/billing/invoices", headers=headers("OWNER_SPONSOR"), json={"contract_id": "not-a-contract", "amount": "1"}).status_code == 409
    assert client.post("/api/billing/plans", headers=headers("RESPONSIBLE_ENGINEER"), json={"contract_id": "not-a-contract"}).status_code == 403


def test_external_agreement_type_is_not_amec_billing_authority(client):
    ensure_contract_template(client)
    proposal_id, _accepted_revision = make_accepted_proposal(client, "External Construction Agreement Boundary")
    created = client.post(f"/api/admin/contracts/from-proposal/{proposal_id}", headers=headers("OWNER_SPONSOR"), json={})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]
    checked = client.post(f"/api/admin/contracts/{contract_id}/checker", headers={**headers("OWNER_SPONSOR"), "X-Dev-Actor": "external-boundary-checker"}, json={"reason": "Synthetic external-agreement boundary check"})
    assert checked.status_code == 200, checked.text
    authority = client.post(f"/api/admin/contracts/{contract_id}/authority", headers=headers("OWNER_SPONSOR"), json={"decision": "APPROVE", "reason": "Boundary fixture authority"})
    assert authority.status_code == 200, authority.text
    accepted = client.post(f"/api/admin/contracts/{contract_id}/accept", headers=headers("OWNER_SPONSOR"), json={"idempotency_key": f"accept-boundary:{contract_id}"})
    assert accepted.status_code == 200, accepted.text
    with SessionLocal() as db:
        contract = db.get(Contract, contract_id)
        contract.agreement_type = "EXTERNAL_CONSTRUCTION_AGREEMENT"
        db.commit()
    rejected = client.post("/api/billing/plans", headers=headers("OWNER_SPONSOR"), json={"contract_id": contract_id})
    assert rejected.status_code == 409
    assert rejected.json()["detail"]["code"] == "CONTRACT_NOT_ELIGIBLE_FOR_AMEC_BILLING"
