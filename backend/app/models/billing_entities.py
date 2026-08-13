"""Canonical post-contract Billing, Invoice, financial-account, and receivable seams."""

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class BillingPlan(Base):
    __tablename__ = "billing_plans"
    __table_args__ = (UniqueConstraint("contract_id", "contract_revision_id", name="uq_billing_plan_contract_revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    client_account_id: Mapped[str] = mapped_column(ForeignKey("client_accounts.id"), nullable=False, index=True)
    currency: Mapped[str] = mapped_column(String(20), nullable=False)
    automation_mode: Mapped[str] = mapped_column(String(40), default="MANUAL", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", nullable=False, index=True)
    current_revision_id: Mapped[str | None] = mapped_column(String(36), index=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    activated_by: Mapped[str | None] = mapped_column(String(200))
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BillingPlanRevision(Base):
    __tablename__ = "billing_plan_revisions"
    __table_args__ = (UniqueConstraint("billing_plan_id", "revision_number", name="uq_billing_plan_revision_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    billing_plan_id: Mapped[str] = mapped_column(ForeignKey("billing_plans.id"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    client_account_id: Mapped[str] = mapped_column(ForeignKey("client_accounts.id"), nullable=False, index=True)
    contract_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(20), nullable=False)
    valuation_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    valuation_currency: Mapped[str | None] = mapped_column(String(20))
    valuation_status: Mapped[str] = mapped_column(String(50), default="UNKNOWN_NON_AUTHORITATIVE", nullable=False)
    contract_project_context_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", nullable=False, index=True)
    supersedes_revision_id: Mapped[str | None] = mapped_column(String(36))
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class BillingMilestone(Base):
    __tablename__ = "billing_milestones"
    __table_args__ = (UniqueConstraint("billing_plan_revision_id", "sequence", name="uq_billing_milestone_sequence"), Index("ix_billing_milestone_eligibility", "eligibility_state", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    billing_plan_revision_id: Mapped[str] = mapped_column(ForeignKey("billing_plan_revisions.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    source_contract_payment_term_id: Mapped[str | None] = mapped_column(ForeignKey("contract_payment_terms.id"), index=True)
    basis_type: Mapped[str] = mapped_column(String(50), nullable=False)
    basis_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    percentage: Mapped[float | None] = mapped_column(Numeric(12, 6))
    calculated_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str] = mapped_column(String(20), nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(80), nullable=False)
    trigger_description: Mapped[str | None] = mapped_column(Text)
    due_days: Mapped[int | None] = mapped_column(Integer)
    eligibility_state: Mapped[str] = mapped_column(String(40), default="WAITING_TRIGGER", nullable=False)
    invoiced_amount: Mapped[float] = mapped_column(Numeric(18, 2), default=0, nullable=False)
    remaining_invoiceable_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class BillingMilestoneEligibility(Base):
    __tablename__ = "billing_milestone_eligibilities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    billing_milestone_id: Mapped[str] = mapped_column(ForeignKey("billing_milestones.id"), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(40), nullable=False)
    evaluated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), default="BILLING_ELIGIBILITY_V1", nullable=False)


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"
    __table_args__ = (UniqueConstraint("invoice_revision_id", "sequence", name="uq_invoice_line_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    invoice_revision_id: Mapped[str] = mapped_column(ForeignKey("invoice_revisions.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    line_role: Mapped[str] = mapped_column(String(30), nullable=False)
    item_code: Mapped[str | None] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[float | None] = mapped_column(Numeric(18, 6))
    unit: Mapped[str | None] = mapped_column(String(40))
    unit_price: Mapped[float | None] = mapped_column(Numeric(18, 6))
    currency: Mapped[str] = mapped_column(String(20), nullable=False)
    calculated_line_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    billing_milestone_id: Mapped[str | None] = mapped_column(ForeignKey("billing_milestones.id"), index=True)
    affects_payable_total: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(300))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class InvoiceReference(Base):
    __tablename__ = "invoice_references"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    invoice_revision_id: Mapped[str] = mapped_column(ForeignKey("invoice_revisions.id"), nullable=False, index=True)
    reference_type: Mapped[str] = mapped_column(String(80), nullable=False)
    value: Mapped[str] = mapped_column(String(300), nullable=False)
    issuer_or_source: Mapped[str | None] = mapped_column(String(200))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="PENDING_VERIFICATION", nullable=False)
    verified_by: Mapped[str | None] = mapped_column(String(200))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class InvoiceApprovalRecord(Base):
    __tablename__ = "invoice_approval_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    invoice_revision_id: Mapped[str] = mapped_column(ForeignKey("invoice_revisions.id"), nullable=False, index=True)
    approval_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="PENDING", nullable=False)
    approval_reference: Mapped[str | None] = mapped_column(String(200))
    approving_party_or_body: Mapped[str | None] = mapped_column(String(200))
    decision_date: Mapped[date | None] = mapped_column(Date)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    verified_by: Mapped[str | None] = mapped_column(String(200))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class InvoiceAcceptRecord(Base):
    __tablename__ = "invoice_accept_records"
    __table_args__ = (UniqueConstraint("invoice_revision_id", name="uq_invoice_accept_revision"), UniqueConstraint("idempotency_key", name="uq_invoice_accept_idempotency"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    invoice_revision_id: Mapped[str] = mapped_column(ForeignKey("invoice_revisions.id"), nullable=False, index=True)
    accepted_by: Mapped[str] = mapped_column(String(200), nullable=False)
    accepted_role: Mapped[str] = mapped_column(String(80), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    precheck_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class InvoiceIssueEvent(Base):
    __tablename__ = "invoice_issue_events"
    __table_args__ = (UniqueConstraint("invoice_id", name="uq_invoice_issue_invoice"), UniqueConstraint("idempotency_key", name="uq_invoice_issue_idempotency"), UniqueConstraint("official_invoice_ref", name="uq_invoice_issue_reference"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    invoice_revision_id: Mapped[str] = mapped_column(ForeignKey("invoice_revisions.id"), nullable=False, index=True)
    official_invoice_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    issued_by: Mapped[str] = mapped_column(String(200), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    template_version_id: Mapped[str] = mapped_column(ForeignKey("template_versions.id"), nullable=False)
    financial_account_version_id: Mapped[str] = mapped_column(ForeignKey("financial_account_versions.id"), nullable=False)
    rendered_artifact_id: Mapped[str] = mapped_column(ForeignKey("rendered_artifacts.id"), nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class InvoiceDeliveryEvent(Base):
    __tablename__ = "invoice_delivery_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_invoice_delivery_idempotency"),
        Index("ix_invoice_delivery_invoice_time", "invoice_id", "delivered_at"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    issued_revision_id: Mapped[str] = mapped_column(ForeignKey("invoice_revisions.id"), nullable=False, index=True)
    issue_event_id: Mapped[str] = mapped_column(ForeignKey("invoice_issue_events.id"), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    recipient_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    delivered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    delivery_reference: Mapped[str | None] = mapped_column(String(200))
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="RECORDED", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)


class InvoiceAcknowledgment(Base):
    __tablename__ = "invoice_acknowledgments"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_invoice_acknowledgment_idempotency"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    issued_revision_id: Mapped[str] = mapped_column(ForeignKey("invoice_revisions.id"), nullable=False, index=True)
    acknowledgment_reference: Mapped[str | None] = mapped_column(String(200))
    acknowledged_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="RECORDED", nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)


class InvoiceNumberingPolicy(Base):
    __tablename__ = "invoice_numbering_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    policy_key: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    prefix: Mapped[str] = mapped_column(String(60), nullable=False)
    padding: Mapped[int] = mapped_column(Integer, default=6, nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    version: Mapped[str] = mapped_column(String(40), default="V1", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE", nullable=False)
    no_reuse: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    updated_by: Mapped[str | None] = mapped_column(String(200))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class FinancialAccountMaster(Base):
    __tablename__ = "financial_account_masters"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    legal_entity_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), index=True)
    legal_entity_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FinancialAccountVersion(Base):
    __tablename__ = "financial_account_versions"
    __table_args__ = (UniqueConstraint("financial_account_master_id", "version_number", name="uq_financial_account_version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    financial_account_master_id: Mapped[str] = mapped_column(ForeignKey("financial_account_masters.id"), nullable=False, index=True)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    bank_name: Mapped[str] = mapped_column(String(160), nullable=False)
    account_name: Mapped[str] = mapped_column(String(200), nullable=False)
    account_reference: Mapped[str] = mapped_column(String(200), nullable=False)
    currency: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default="DRAFT", nullable=False)
    payment_instruction_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PaymentReceipt(Base):
    __tablename__ = "payment_receipts"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_payment_receipt_idempotency"), Index("ix_payment_receipt_scope", "contract_id", "project_id", "verification_status"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    client_account_id: Mapped[str] = mapped_column(ForeignKey("client_accounts.id"), nullable=False, index=True)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    received_date: Mapped[date] = mapped_column(Date, nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(20), nullable=False)
    reference: Mapped[str] = mapped_column(String(200), nullable=False)
    payment_method: Mapped[str | None] = mapped_column(String(80))
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    verification_status: Mapped[str] = mapped_column(String(40), default="OBSERVED", nullable=False, index=True)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    verified_by: Mapped[str | None] = mapped_column(String(200))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)


class InvoicePaymentAllocation(Base):
    __tablename__ = "invoice_payment_allocations"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_invoice_payment_allocation_idempotency"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    payment_receipt_id: Mapped[str] = mapped_column(ForeignKey("payment_receipts.id"), nullable=False, index=True)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    allocated_amount: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(20), nullable=False)
    allocated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    allocated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="ALLOCATED", nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)


class ReceivableFollowUp(Base):
    __tablename__ = "receivable_follow_ups"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    follow_up_date: Mapped[date] = mapped_column(Date, nullable=False)
    channel: Mapped[str] = mapped_column(String(60), nullable=False)
    contact_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), index=True)
    note: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str | None] = mapped_column(String(120))
    next_follow_up_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
