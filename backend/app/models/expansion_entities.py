"""Shared AMEC Stage 1 v2.6 semantic foundation.

These entities deliberately compose with the existing PermitOps evidence,
approval, task, audit, validity, rendering, and lineage primitives. They do
not authorize downstream business actions.
"""

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, utcnow


def _id() -> str:
    return str(uuid4())


class EvidenceArtifact(Base):
    """Shared evidence pointer used by expanded domains; bytes remain external to the DB."""
    __tablename__ = "evidence_artifacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(300), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    synthetic_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    label: Mapped[str] = mapped_column(String(150), default="SYNTHETIC / NOT CLIENT APPROVED", nullable=False)


class ProjectArtifactRecord(Base, TimestampMixin):
    """Workflow/index record for bytes written to the configured project SOR.

    This record intentionally stores metadata and lineage pointers only. The
    project-folder repository remains the durable system of record for file
    bytes.
    """
    __tablename__ = "project_artifact_records"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_project_artifact_idempotency"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    opportunity_id: Mapped[str | None] = mapped_column(ForeignKey("opportunities.id"), index=True)
    contract_id: Mapped[str | None] = mapped_column(ForeignKey("contracts.id"), index=True)
    artifact_type: Mapped[str] = mapped_column(String(50), nullable=False)
    semantic_class: Mapped[str] = mapped_column(String(50), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    sor_path: Mapped[str] = mapped_column(String(600), nullable=False)
    source_revision: Mapped[str | None] = mapped_column(String(80))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    folder_template_version: Mapped[str] = mapped_column(String(60), nullable=False)
    document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    evidence_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_artifacts.id"), index=True)
    supersedes_record_id: Mapped[str | None] = mapped_column(String(36))
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    verification_state: Mapped[str] = mapped_column(String(40), nullable=False, default="REGISTERED")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="REGISTERED")
    audit_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Opportunity(Base, TimestampMixin):
    __tablename__ = "opportunities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    office_id: Mapped[str] = mapped_column(ForeignKey("consultancy_offices.id"), nullable=False, index=True)
    client_account_id: Mapped[str | None] = mapped_column(ForeignKey("client_accounts.id"), index=True)
    opportunity_reference: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    current_owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), index=True)
    stage2_capability_scope: Mapped[str] = mapped_column(String(100), default="UNDECIDED_STAGE2", nullable=False)
    # Proposal-facing terminology is canonical; the internal Opportunity name
    # remains stable for migration compatibility.
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    reference_state: Mapped[str] = mapped_column(String(30), default="PROVISIONAL", nullable=False)
    proposal_fields_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    provisional_reference: Mapped[str | None] = mapped_column(String(100), index=True)
    canonical_project_reference: Mapped[str | None] = mapped_column(String(100), index=True)
    canonicalized_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canonicalized_by: Mapped[str | None] = mapped_column(String(200))


class ClientAccount(Base, TimestampMixin):
    __tablename__ = "client_accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    client_reference: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    legal_name: Mapped[str] = mapped_column(String(250), nullable=False)
    display_name: Mapped[str] = mapped_column(String(250), nullable=False)
    client_type: Mapped[str] = mapped_column(String(50), nullable=False)
    canonical_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), index=True)
    commercial_registration_number: Mapped[str | None] = mapped_column(String(100))
    data_classification: Mapped[str] = mapped_column(String(40), default="SYNTHETIC", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE", nullable=False)


class ClientContact(Base, TimestampMixin):
    __tablename__ = "client_contacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    client_account_id: Mapped[str] = mapped_column(ForeignKey("client_accounts.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    email: Mapped[str] = mapped_column(String(200), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(80))
    role_title: Mapped[str | None] = mapped_column(String(120))
    language_preference: Mapped[str | None] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE", nullable=False)


class RFQ(Base):
    __tablename__ = "rfqs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    source_document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    sender_reference: Mapped[str | None] = mapped_column(String(200))
    source_reference: Mapped[str | None] = mapped_column(String(200))
    language: Mapped[str] = mapped_column(String(10), default="EN", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="RECEIVED", nullable=False)


class TenderDocument(Base):
    __tablename__ = "tender_documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    document_role: Mapped[str] = mapped_column(String(80), default="TENDER", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="RECEIVED", nullable=False)


class Quotation(Base, TimestampMixin):
    __tablename__ = "quotations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    quotation_reference: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)
    current_revision_id: Mapped[str | None] = mapped_column(String(36))
    client_account_id: Mapped[str] = mapped_column(ForeignKey("client_accounts.id"), nullable=False, index=True)


class QuotationRevision(Base):
    __tablename__ = "quotation_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    quotation_id: Mapped[str] = mapped_column(ForeignKey("quotations.id"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    template_version_id: Mapped[str | None] = mapped_column(ForeignKey("template_versions.id"))
    rendered_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("rendered_artifacts.id"))
    render_input_hash: Mapped[str | None] = mapped_column(String(64))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    semantic_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", nullable=False)
    supersedes_revision_id: Mapped[str | None] = mapped_column(String(36))
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("quotation_id", "revision_number", name="uq_quotation_revision_number"),)


class CommercialTerm(Base):
    __tablename__ = "commercial_terms"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    quotation_revision_id: Mapped[str] = mapped_column(ForeignKey("quotation_revisions.id"), nullable=False, index=True)
    term_type: Mapped[str] = mapped_column(String(40), nullable=False)
    value_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    evidence_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_artifacts.id"))
    status: Mapped[str] = mapped_column(String(40), default="PROPOSED", nullable=False)


class QuotationApproval(Base):
    __tablename__ = "quotation_approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    quotation_revision_id: Mapped[str] = mapped_column(ForeignKey("quotation_revisions.id"), nullable=False, index=True)
    approval_id: Mapped[str] = mapped_column(ForeignKey("approvals.id"), nullable=False, unique=True)
    approval_type: Mapped[str] = mapped_column(String(80), default="COMMERCIAL_QUOTATION_RELEASE", nullable=False)


class Contract(Base, TimestampMixin):
    __tablename__ = "contracts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    client_account_id: Mapped[str] = mapped_column(ForeignKey("client_accounts.id"), nullable=False, index=True)
    quotation_id: Mapped[str] = mapped_column(ForeignKey("quotations.id"), nullable=False, index=True)
    contract_reference: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)
    current_revision_id: Mapped[str | None] = mapped_column(String(36))
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    end_date: Mapped[date | None] = mapped_column(Date)
    contract_name: Mapped[str | None] = mapped_column(String(250))
    proposal_id: Mapped[str | None] = mapped_column(ForeignKey("opportunities.id"), index=True)
    accepted_proposal_revision_id: Mapped[str | None] = mapped_column(ForeignKey("proposal_accepted_revisions.id"), index=True)
    project_opportunity_ref: Mapped[str | None] = mapped_column(String(120), index=True)
    stage: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False, index=True)
    amount_value: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str | None] = mapped_column(String(20))
    duration: Mapped[str | None] = mapped_column(String(120))
    expected_close_date: Mapped[date | None] = mapped_column(Date)
    actual_close_date: Mapped[date | None] = mapped_column(Date)
    close_date_meaning: Mapped[str | None] = mapped_column(String(120))
    authority_state: Mapped[str] = mapped_column(String(50), default="NOT_REVIEWED", nullable=False)
    last_activity_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    field_provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ContractRevision(Base):
    __tablename__ = "contract_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    controlling_quotation_revision_id: Mapped[str] = mapped_column(ForeignKey("quotation_revisions.id"), nullable=False, index=True)
    rendered_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("rendered_artifacts.id"))
    template_version_id: Mapped[str | None] = mapped_column(ForeignKey("template_versions.id"))
    render_input_hash: Mapped[str | None] = mapped_column(String(64))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    commercial_terms_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", nullable=False)
    supersedes_revision_id: Mapped[str | None] = mapped_column(String(36))
    accepted_proposal_revision_id: Mapped[str | None] = mapped_column(ForeignKey("proposal_accepted_revisions.id"), index=True)
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    contract_name: Mapped[str | None] = mapped_column(String(250))
    stage: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)
    amount_value: Mapped[str | None] = mapped_column(String(100))
    currency: Mapped[str | None] = mapped_column(String(20))
    duration: Mapped[str | None] = mapped_column(String(120))
    expected_close_date: Mapped[date | None] = mapped_column(Date)
    actual_close_date: Mapped[date | None] = mapped_column(Date)
    admin_input_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("contract_id", "revision_number", name="uq_contract_revision_number"),)


class ContractMilestone(Base):
    __tablename__ = "contract_milestones"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False, index=True)
    milestone_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    payment_condition: Mapped[str | None] = mapped_column(Text)
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    amount_value: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), default="PLANNED", nullable=False)


class ContractApproval(Base):
    __tablename__ = "contract_approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False, index=True)
    approval_id: Mapped[str] = mapped_column(ForeignKey("approvals.id"), nullable=False, unique=True)
    approval_type: Mapped[str] = mapped_column(String(80), default="CONTRACT_APPROVAL", nullable=False)


class ChecklistItem(Base):
    __tablename__ = "checklist_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    context_type: Mapped[str] = mapped_column(String(80), nullable=False)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    requirement_code: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    required_condition: Mapped[str] = mapped_column(Text, nullable=False)
    required_document_type: Mapped[str | None] = mapped_column(String(100))
    validity_policy_ref: Mapped[str | None] = mapped_column(String(100))
    current_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    applicability: Mapped[str] = mapped_column(String(50), default="APPLICABLE", nullable=False)
    validity_status: Mapped[str] = mapped_column(String(50), default="UNKNOWN_REVIEW_REQUIRED", nullable=False)
    owner_role: Mapped[str] = mapped_column(String(100), default="ADMIN_PROJECT_COORDINATOR", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="OPEN", nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class DocumentRequest(Base):
    __tablename__ = "document_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    checklist_item_id: Mapped[str] = mapped_column(ForeignKey("checklist_items.id"), nullable=False, index=True)
    client_account_id: Mapped[str] = mapped_column(ForeignKey("client_accounts.id"), nullable=False, index=True)
    requested_from_contact_id: Mapped[str | None] = mapped_column(ForeignKey("client_contacts.id"))
    status: Mapped[str] = mapped_column(String(50), default="OPEN", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    communication_draft_id: Mapped[str | None] = mapped_column(String(36))


class ReferenceNumber(Base):
    __tablename__ = "reference_numbers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    reference_value: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    reference_type: Mapped[str] = mapped_column(String(50), nullable=False)
    opportunity_id: Mapped[str | None] = mapped_column(ForeignKey("opportunities.id"))
    quotation_id: Mapped[str | None] = mapped_column(ForeignKey("quotations.id"))
    contract_id: Mapped[str | None] = mapped_column(ForeignKey("contracts.id"))
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    permit_application_id: Mapped[str | None] = mapped_column(ForeignKey("permit_applications.id"))
    status: Mapped[str] = mapped_column(String(40), default="RESERVED", nullable=False)
    reserved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectAdministrationRecord(Base, TimestampMixin):
    __tablename__ = "project_administration_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, unique=True)
    reference_number_id: Mapped[str] = mapped_column(ForeignKey("reference_numbers.id"), nullable=False)
    client_account_id: Mapped[str] = mapped_column(ForeignKey("client_accounts.id"), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(50), default="NOT_CONFIGURED", nullable=False)
    payment_followup_state: Mapped[str] = mapped_column(String(50), default="TRACK_ONLY", nullable=False)
    project_status: Mapped[str] = mapped_column(String(50), default="ACTIVE", nullable=False)
    engineer_contact_id: Mapped[str | None] = mapped_column(ForeignKey("client_contacts.id"))
    engineer_email_projection: Mapped[str | None] = mapped_column(String(200))
    synology_linkage_reference: Mapped[str | None] = mapped_column(String(300))
    excel_linkage_reference: Mapped[str | None] = mapped_column(String(300))
    last_governed_update_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CommunicationDraft(Base, TimestampMixin):
    __tablename__ = "communication_drafts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    communication_type: Mapped[str] = mapped_column(String(80), nullable=False)
    context_type: Mapped[str] = mapped_column(String(80), nullable=False)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    recipient_contact_id: Mapped[str | None] = mapped_column(ForeignKey("client_contacts.id"))
    template_version_id: Mapped[str | None] = mapped_column(ForeignKey("template_versions.id"))
    subject: Mapped[str] = mapped_column(String(250), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)
    policy_state: Mapped[str] = mapped_column(String(50), default="HUMAN_SEND", nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_revision_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    body_hash: Mapped[str | None] = mapped_column(String(64))
    stale_reason: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class CommunicationApproval(Base):
    __tablename__ = "communication_approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    communication_draft_id: Mapped[str] = mapped_column(ForeignKey("communication_drafts.id"), nullable=False, index=True)
    approval_id: Mapped[str] = mapped_column(ForeignKey("approvals.id"), nullable=False, unique=True)
    approval_type: Mapped[str] = mapped_column(String(80), default="COMMUNICATION_RELEASE", nullable=False)


class CommunicationDelivery(Base):
    __tablename__ = "communication_deliveries"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    communication_draft_id: Mapped[str] = mapped_column(ForeignKey("communication_drafts.id"), nullable=False, index=True)
    delivery_channel: Mapped[str] = mapped_column(String(50), nullable=False)
    delivery_status: Mapped[str] = mapped_column(String(50), default="NOT_SENT", nullable=False)
    external_message_id: Mapped[str | None] = mapped_column(String(200))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_artifacts.id"))


class Invoice(Base, TimestampMixin):
    __tablename__ = "invoices"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    invoice_reference: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)
    current_revision_id: Mapped[str | None] = mapped_column(String(36))
    requirement_decision_id: Mapped[str | None] = mapped_column(ForeignKey("invoice_requirement_decisions.id"))


class InvoiceRevision(Base):
    __tablename__ = "invoice_revisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    controlling_contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False)
    controlling_milestone_id: Mapped[str | None] = mapped_column(ForeignKey("contract_milestones.id"))
    status: Mapped[str] = mapped_column(String(40), default="DRAFT", nullable=False)
    supersedes_revision_id: Mapped[str | None] = mapped_column(String(36))
    template_version_id: Mapped[str | None] = mapped_column(ForeignKey("template_versions.id"))
    rendered_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("rendered_artifacts.id"))
    render_input_hash: Mapped[str | None] = mapped_column(String(64))
    content_hash: Mapped[str | None] = mapped_column(String(64))
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    stale_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    __table_args__ = (UniqueConstraint("invoice_id", "revision_number", name="uq_invoice_revision_number"),)


class InvoiceMilestone(Base):
    __tablename__ = "invoice_milestones"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    contract_milestone_id: Mapped[str] = mapped_column(ForeignKey("contract_milestones.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="TRACK_ONLY", nullable=False)


class InvoiceApproval(Base):
    __tablename__ = "invoice_approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    invoice_revision_id: Mapped[str] = mapped_column(ForeignKey("invoice_revisions.id"), nullable=False, index=True)
    approval_id: Mapped[str] = mapped_column(ForeignKey("approvals.id"), nullable=False, unique=True)
    approval_type: Mapped[str] = mapped_column(String(80), default="FINANCE_INVOICE_APPROVAL", nullable=False)


class AccountingHandoff(Base):
    __tablename__ = "accounting_handoffs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    assigned_role: Mapped[str] = mapped_column(String(80), default="GENERIC_FINANCE_HANDOFF", nullable=False)
    assigned_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(40), default="TRACK_ONLY", nullable=False)
    workflow_task_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_tasks.id"))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProjectHandover(Base):
    __tablename__ = "project_handovers"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="NOT_READY", nullable=False)
    readiness_state: Mapped[str] = mapped_column(String(50), default="NOT_READY", nullable=False)
    rendered_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("rendered_artifacts.id"))
    approval_id: Mapped[str | None] = mapped_column(ForeignKey("approvals.id"))
    communication_draft_id: Mapped[str | None] = mapped_column(ForeignKey("communication_drafts.id"))
    readiness_checks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    selected_deliverables: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    approval_state: Mapped[str] = mapped_column(String(50), default="HANDOVER_DRAFT_READY", nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_role: Mapped[str | None] = mapped_column(String(100))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    release_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    release_evidence_status: Mapped[str] = mapped_column(String(60), default="NOT_RECORDED", nullable=False)
    stale_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class InvoiceRequirementDecision(Base):
    __tablename__ = "invoice_requirement_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False, index=True)
    milestone_id: Mapped[str | None] = mapped_column(ForeignKey("contract_milestones.id"))
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    decision_source: Mapped[str] = mapped_column(String(50), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by: Mapped[str | None] = mapped_column(String(200))
    rule_id: Mapped[str | None] = mapped_column(String(120))
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FinanceEvidence(Base):
    __tablename__ = "finance_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    invoice_id: Mapped[str] = mapped_column(ForeignKey("invoices.id"), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False)
    source: Mapped[str] = mapped_column(String(60), default="SYNTHETIC_EXTERNAL_EVENT", nullable=False)
    evidence_reference: Mapped[str] = mapped_column(String(300), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RegulationSource(Base):
    __tablename__ = "regulation_sources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    source_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(250), nullable=False)
    jurisdiction: Mapped[str] = mapped_column(String(100), nullable=False)
    authority_name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    publication_state: Mapped[str] = mapped_column(String(60), default="SYNTHETIC_PLACEHOLDER", nullable=False)


class RegulationVersion(Base):
    __tablename__ = "regulation_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    regulation_source_id: Mapped[str] = mapped_column(ForeignKey("regulation_sources.id"), nullable=False, index=True)
    edition: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(100), nullable=False)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    source_uri_or_reference: Mapped[str | None] = mapped_column(String(300))
    content_status: Mapped[str] = mapped_column(String(60), default="SYNTHETIC_PLACEHOLDER", nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64))


class RegulationApplicability(Base):
    __tablename__ = "regulation_applicabilities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    regulation_version_id: Mapped[str] = mapped_column(ForeignKey("regulation_versions.id"), nullable=False, index=True)
    context_type: Mapped[str] = mapped_column(String(80), nullable=False)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    discipline: Mapped[str] = mapped_column(String(100), nullable=False)
    applicability_status: Mapped[str] = mapped_column(String(60), default="NOT_CONFIGURED", nullable=False)
    approved_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    approval_id: Mapped[str | None] = mapped_column(ForeignKey("approvals.id"))
    effective_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_scope_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_review_scopes.id"), index=True)
    basis_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class EngineeringReview(Base):
    __tablename__ = "engineering_reviews"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    discipline: Mapped[str] = mapped_column(String(100), nullable=False)
    drawing_document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="SYNTHETIC_DEMO_DISCIPLINE", nullable=False)
    authorized_engineer_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    current_scope_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_review_scopes.id"))
    current_drawing_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EngineeringReviewScope(Base):
    __tablename__ = "engineering_review_scopes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    engineering_review_id: Mapped[str] = mapped_column(ForeignKey("engineering_reviews.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    scope_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    discipline: Mapped[str] = mapped_column(String(100), nullable=False)
    supported_drawing_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    selected_regulation_version_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    applicability_basis: Mapped[str] = mapped_column(Text, nullable=False)
    review_objectives: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    excluded_topics: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    authorized_engineer_role: Mapped[str] = mapped_column(String(100), default="AUTHORIZED_ENGINEER", nullable=False)
    stage2_disposition: Mapped[str] = mapped_column(String(40), default="UNDECIDED_STAGE2", nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(100), default="SYNTHETIC_IMPLEMENTATION_EVIDENCE", nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="CONFIGURED", nullable=False)
    synthetic_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class EngineeringReviewRun(Base):
    __tablename__ = "engineering_review_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    engineering_review_id: Mapped[str] = mapped_column(ForeignKey("engineering_reviews.id"), nullable=False, index=True)
    drawing_document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    review_scope_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_review_scopes.id"), index=True)
    regulation_applicability_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    pinned_drawing_hash: Mapped[str | None] = mapped_column(String(64))
    pinned_revision_label: Mapped[str | None] = mapped_column(String(50))
    model_config_version: Mapped[str | None] = mapped_column(String(80))
    prompt_bundle_version: Mapped[str | None] = mapped_column(String(80))
    evidence_recipe: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="HUMAN_REVIEW_REQUIRED", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class EngineeringComment(Base):
    __tablename__ = "engineering_comments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    engineering_review_run_id: Mapped[str] = mapped_column(ForeignKey("engineering_review_runs.id"), nullable=False, index=True)
    drawing_document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    comment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    stable_comment_number: Mapped[str | None] = mapped_column(String(60), index=True)
    source_type: Mapped[str] = mapped_column(String(50), default="SYNTHETIC_PROPOSED", nullable=False)
    proposed_text: Mapped[str] = mapped_column(Text, nullable=False)
    location_reference: Mapped[str | None] = mapped_column(String(200))
    issue_text: Mapped[str | None] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text)
    regulation_version_id: Mapped[str | None] = mapped_column(ForeignKey("regulation_versions.id"))
    regulation_evidence_reference: Mapped[str | None] = mapped_column(String(300))
    severity: Mapped[str] = mapped_column(String(30), default="ADVISORY", nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    uncertainty_state: Mapped[str] = mapped_column(String(50), default="SUPPORTED_EVIDENCE", nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(50), default="PROPOSED", nullable=False)
    engineer_disposition: Mapped[str] = mapped_column(String(60), default="NOT_DISPOSED", nullable=False)
    engineer_notes: Mapped[str | None] = mapped_column(Text)
    closure_state: Mapped[str] = mapped_column(String(50), default="OPEN", nullable=False)
    required_action: Mapped[str | None] = mapped_column(Text)
    supersedes_comment_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_comments.id"))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correction_received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    re_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class DrawingReviewCycle(Base):
    __tablename__ = "drawing_review_cycles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    discipline: Mapped[str] = mapped_column(String(100), nullable=False)
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    input_drawing_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    review_run_id: Mapped[str] = mapped_column(ForeignKey("engineering_review_runs.id"), nullable=False)
    output_drawing_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    status: Mapped[str] = mapped_column(String(50), default="OPEN", nullable=False)
    material_change_reason: Mapped[str | None] = mapped_column(Text)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TemplateDefinition(Base):
    __tablename__ = "template_definitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    template_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="EN", nullable=False)
    owner_role: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(60), default="SYNTHETIC_STANDIN", nullable=False)


class TemplateVersion(Base):
    __tablename__ = "template_versions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    template_definition_id: Mapped[str] = mapped_column(ForeignKey("template_definitions.id"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(60), default="SYNTHETIC_STANDIN", nullable=False)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_id: Mapped[str | None] = mapped_column(String(36))
    __table_args__ = (UniqueConstraint("template_definition_id", "version", name="uq_template_version"),)


class RenderedArtifact(Base):
    __tablename__ = "rendered_artifacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    template_version_id: Mapped[str] = mapped_column(ForeignKey("template_versions.id"), nullable=False, index=True)
    context_type: Mapped[str] = mapped_column(String(80), nullable=False)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(80), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_reference: Mapped[str] = mapped_column(String(300), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="DRAFT", nullable=False)
    render_input_hash: Mapped[str | None] = mapped_column(String(64))
    source_revision_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    rendered_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="EN", nullable=False)
    synthetic_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AssistantCapabilityDefinition(Base, TimestampMixin):
    __tablename__ = "assistant_capability_definitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    assistant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    capability_id: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    input_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    output_types: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    required_human_authority: Mapped[str] = mapped_column(String(120), nullable=False)
    external_action_policy: Mapped[str] = mapped_column(String(100), default="NONE", nullable=False)
    stage2_disposition: Mapped[str] = mapped_column(String(40), default="UNDECIDED_STAGE2", nullable=False)
    execution_authority: Mapped[str] = mapped_column(String(50), default="PROTOTYPE_DEV_ONLY", nullable=False)
    enabled_in_prototype: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enabled_in_production: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allowed_source_classes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    ai_mode: Mapped[str] = mapped_column(String(40), default="DRAFT", nullable=False)
    capability_version: Mapped[str] = mapped_column(String(40), default="E2-1.0", nullable=False)
    capability_status: Mapped[str] = mapped_column(String(40), default="ACTIVE", nullable=False)
    enabled_in_dev: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enabled_in_test: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ExpansionFixtureResource(Base):
    __tablename__ = "expansion_fixture_resources"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    fixture_version: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    resource_path: Mapped[str] = mapped_column(String(300), nullable=False)
    source_family: Mapped[str] = mapped_column(String(80), nullable=False)
    scenario: Mapped[str] = mapped_column(String(100), nullable=False)
    synthetic_label: Mapped[str] = mapped_column(String(150), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class ExecutionAuthorityConfig(Base, TimestampMixin):
    __tablename__ = "execution_authority_configs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority: Mapped[str] = mapped_column(String(50), nullable=False, unique=True)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)
    production_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    external_actions_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)


class QuotationFieldObservation(Base):
    __tablename__ = "quotation_field_observations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    quotation_revision_id: Mapped[str] = mapped_column(ForeignKey("quotation_revisions.id"), nullable=False, index=True)
    field_code: Mapped[str] = mapped_column(String(80), nullable=False)
    candidate_value: Mapped[str | None] = mapped_column(Text)
    verified_value: Mapped[str | None] = mapped_column(Text)
    proposed_offer_value: Mapped[str | None] = mapped_column(Text)
    approved_offer_value: Mapped[str | None] = mapped_column(Text)
    authority_mode: Mapped[str] = mapped_column(String(50), default="HUMAN_APPROVED", nullable=False)
    state: Mapped[str] = mapped_column(String(40), default="CANDIDATE", nullable=False)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    evidence_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_artifacts.id"))
    material: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ClientResponse(Base):
    __tablename__ = "client_responses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    quotation_revision_id: Mapped[str] = mapped_column(ForeignKey("quotation_revisions.id"), nullable=False, index=True)
    response_type: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_artifacts.id"))
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ContractExecutionEvidence(Base):
    __tablename__ = "contract_execution_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False, index=True)
    evidence_artifact_id: Mapped[str] = mapped_column(ForeignKey("evidence_artifacts.id"), nullable=False)
    execution_status: Mapped[str] = mapped_column(String(50), default="EXECUTION_EVIDENCE_PENDING", nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class SystemBlock(Base):
    __tablename__ = "system_blocks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    context_type: Mapped[str] = mapped_column(String(80), nullable=False)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    control_code: Mapped[str] = mapped_column(String(100), nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    owner_role: Mapped[str] = mapped_column(String(100), nullable=False)
    required_action: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_condition: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AdminDocumentComment(Base):
    __tablename__ = "admin_document_comments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    comment_number: Mapped[str] = mapped_column(String(50), nullable=False)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    reviewed_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("rendered_artifacts.id"))
    source_type: Mapped[str] = mapped_column(String(60), default="ADMIN_DOCUMENT_REVIEW", nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), default="MEDIUM", nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    owner_role: Mapped[str] = mapped_column(String(100), default="ADMIN_PROJECT_COORDINATOR", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="OPEN", nullable=False)
    resolution_evidence: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ProjectStatusProjection(Base):
    __tablename__ = "project_status_projections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, unique=True)
    reference_number: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    client: Mapped[str] = mapped_column(String(250), nullable=False)
    payment: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    engineer_email: Mapped[str | None] = mapped_column(String(200))
    workbook_reference: Mapped[str] = mapped_column(String(200), default="SYNTHETIC_LOCAL_EXCEL", nullable=False)
    human_owned_cells_protected: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    projected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class QuotationRelease(Base):
    __tablename__ = "quotation_releases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    quotation_revision_id: Mapped[str] = mapped_column(ForeignKey("quotation_revisions.id"), nullable=False, unique=True)
    rendered_artifact_id: Mapped[str] = mapped_column(ForeignKey("rendered_artifacts.id"), nullable=False)
    approval_id: Mapped[str] = mapped_column(ForeignKey("approvals.id"), nullable=False)
    released_by: Mapped[str] = mapped_column(String(200), nullable=False)
    released_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    release_channel_intent: Mapped[str] = mapped_column(String(80), default="HUMAN_SEND", nullable=False)


class CapabilityInvocationRecord(Base, TimestampMixin):
    __tablename__ = "capability_invocation_records"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    assistant_id: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    capability_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    caller: Mapped[str] = mapped_column(String(200), nullable=False)
    caller_role: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_decision: Mapped[str] = mapped_column(String(60), nullable=False)
    result_type: Mapped[str] = mapped_column(String(60), nullable=False)
    output_envelope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    source_revision_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    deterministic_gate_result: Mapped[str] = mapped_column(String(60), default="HUMAN_REVIEW_REQUIRED", nullable=False)


class AssistantHandoff(Base, TimestampMixin):
    __tablename__ = "assistant_handoffs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    from_assistant_id: Mapped[str] = mapped_column(String(80), nullable=False)
    to_assistant_id: Mapped[str] = mapped_column(String(80), nullable=False)
    context_type: Mapped[str] = mapped_column(String(80), nullable=False)
    context_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    opportunity_id: Mapped[str | None] = mapped_column(ForeignKey("opportunities.id"), index=True)
    source_revision_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    workflow_task_id: Mapped[str | None] = mapped_column(ForeignKey("workflow_tasks.id"))
    status: Mapped[str] = mapped_column(String(40), default="CREATED", nullable=False)
    accepted_by: Mapped[str | None] = mapped_column(String(200))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text, nullable=False)


class ProposalIntakeArtifact(Base, TimestampMixin):
    """Durable pre-project intake evidence rooted by the provisional reference."""

    __tablename__ = "proposal_intake_artifacts"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_proposal_intake_idempotency"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    opportunity_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    opportunity_reference: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(80), nullable=False)
    semantic_class: Mapped[str] = mapped_column(String(80), nullable=False)
    source_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    stored_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    sor_path: Mapped[str] = mapped_column(String(600), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    source_revision: Mapped[str | None] = mapped_column(String(80))
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    verification_state: Mapped[str] = mapped_column(String(40), default="READ_BACK_VERIFIED", nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="REGISTERED", nullable=False)
    evidence_artifact_id: Mapped[str | None] = mapped_column(ForeignKey("evidence_artifacts.id"), index=True)
    supersedes_artifact_id: Mapped[str | None] = mapped_column(String(36))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
