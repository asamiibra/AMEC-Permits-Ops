"""Canonical Source-18 engineering acceptance and regulatory workflow state.

These records extend the existing AuthorityCase, document, form, identity,
and audit primitives.  They do not create a second case or document system.
The tables are deliberately versioned and append-only at submission
boundaries so a later review can reproduce the exact decision context.
"""

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, utcnow


def _id() -> str:
    return str(uuid4())


class Source18PolicyVersion(Base, TimestampMixin):
    __tablename__ = "source18_policy_versions"
    __table_args__ = (UniqueConstraint("policy_code", "version", name="uq_source18_policy_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    policy_code: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    source_class: Mapped[str] = mapped_column(String(50), nullable=False, default="REGULATORY_SOURCE_REQUIRED")
    source_reference: Mapped[str | None] = mapped_column(String(500))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    rules_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class OfficeRegistration(Base, TimestampMixin):
    __tablename__ = "source18_office_registrations"
    __table_args__ = (UniqueConstraint("office_id", "registration_number", name="uq_source18_office_registration"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    office_id: Mapped[str] = mapped_column(ForeignKey("consultancy_offices.id"), nullable=False, index=True)
    registration_number: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    currentness_state: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    source_policy_version_id: Mapped[str | None] = mapped_column(ForeignKey("source18_policy_versions.id"), index=True)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Source18OfficeCertificate(Base, TimestampMixin):
    __tablename__ = "source18_office_certificates"
    __table_args__ = (UniqueConstraint("office_registration_id", "version_number", name="uq_source18_certificate_version"), Index("ix_source18_certificate_current", "office_registration_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    office_registration_id: Mapped[str] = mapped_column(ForeignKey("source18_office_registrations.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    certificate_number: Mapped[str | None] = mapped_column(String(120))
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    custody_state: Mapped[str] = mapped_column(String(50), nullable=False, default="DIGITAL_SCAN")
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("source18_office_certificates.id"), index=True)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Source18OfficeDocument(Base, TimestampMixin):
    __tablename__ = "source18_office_documents"
    __table_args__ = (UniqueConstraint("office_registration_id", "document_type", "version_number", name="uq_source18_office_document_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    office_registration_id: Mapped[str] = mapped_column(ForeignKey("source18_office_registrations.id"), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    custody_state: Mapped[str] = mapped_column(String(50), nullable=False, default="DIGITAL_SCAN")
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("source18_office_documents.id"), index=True)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Source18EngineerProfile(Base, TimestampMixin):
    __tablename__ = "source18_engineer_profiles"
    __table_args__ = (UniqueConstraint("office_id", "engineer_ref", name="uq_source18_engineer_profile"), Index("ix_source18_engineer_profile_status", "office_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    office_id: Mapped[str] = mapped_column(ForeignKey("consultancy_offices.id"), nullable=False, index=True)
    engineer_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    discipline: Mapped[str] = mapped_column(String(120), nullable=False)
    grade_category: Mapped[str | None] = mapped_column(String(120))
    registration_number: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ACTIVE")
    regulatory_profile_state: Mapped[str] = mapped_column(String(40), nullable=False, default="UNKNOWN")
    raw_pii_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    current_evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    current_policy_version_id: Mapped[str | None] = mapped_column(ForeignKey("source18_policy_versions.id"), index=True)
    evidence_currentness: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)


class Source18RosterMembership(Base, TimestampMixin):
    __tablename__ = "source18_roster_memberships"
    __table_args__ = (Index("ix_source18_roster_membership_office", "office_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    office_id: Mapped[str] = mapped_column(ForeignKey("consultancy_offices.id"), nullable=False, index=True)
    engineer_profile_id: Mapped[str] = mapped_column(ForeignKey("source18_engineer_profiles.id"), nullable=False, index=True)
    discipline: Mapped[str] = mapped_column(String(120), nullable=False)
    regulator_counted_state: Mapped[str] = mapped_column(String(40), nullable=False, default="UNKNOWN")
    classified_engineer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    inside_qatar: Mapped[bool | None] = mapped_column(Boolean)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="ACTIVE")
    source_policy_version_id: Mapped[str | None] = mapped_column(ForeignKey("source18_policy_versions.id"), index=True)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    source_order: Mapped[int | None] = mapped_column(Integer)


class Source18OfficialFormVersion(Base, TimestampMixin):
    __tablename__ = "source18_official_form_versions"
    __table_args__ = (UniqueConstraint("form_code", "version", name="uq_source18_official_form_version"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    form_code: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    currentness_state: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    provenance_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class Source18WorkflowTransaction(Base, TimestampMixin):
    __tablename__ = "source18_workflow_transactions"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_source18_transaction_idempotency"), Index("ix_source18_transaction_case", "authority_case_id", "transaction_type", "state"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False, index=True)
    office_id: Mapped[str] = mapped_column(ForeignKey("consultancy_offices.id"), nullable=False, index=True)
    transaction_type: Mapped[str] = mapped_column(String(60), nullable=False)
    processing_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    state: Mapped[str] = mapped_column(String(60), nullable=False)
    engineer_profile_id: Mapped[str | None] = mapped_column(ForeignKey("source18_engineer_profiles.id"), index=True)
    current_policy_version_id: Mapped[str | None] = mapped_column(ForeignKey("source18_policy_versions.id"), index=True)
    official_form_version_id: Mapped[str | None] = mapped_column(ForeignKey("source18_official_form_versions.id"), index=True)
    requirement_version_id: Mapped[str | None] = mapped_column(ForeignKey("requirement_policy_versions.id"), index=True)
    currentness_state: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    remediation_exception: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requested_disciplines_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    current_disciplines_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    actor_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    source_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    last_transition_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Source18PacketRevision(Base):
    __tablename__ = "source18_packet_revisions"
    __table_args__ = (UniqueConstraint("transaction_id", "revision_number", name="uq_source18_packet_revision"), Index("ix_source18_packet_transaction", "transaction_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("source18_workflow_transactions.id"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    packet_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    required_signers_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    signature_state: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_STARTED")
    stamp_state: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_STARTED")
    custody_state: Mapped[str] = mapped_column(String(50), nullable=False, default="DIGITAL_SCAN")
    internal_release_state: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_RELEASED")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("source18_packet_revisions.id"), index=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class Source18SubmissionCycle(Base, TimestampMixin):
    __tablename__ = "source18_submission_cycles"
    __table_args__ = (UniqueConstraint("transaction_id", "cycle_number", name="uq_source18_submission_cycle"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("source18_workflow_transactions.id"), nullable=False, index=True)
    packet_revision_id: Mapped[str] = mapped_column(ForeignKey("source18_packet_revisions.id"), nullable=False)
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="SUBMITTED")
    external_reference: Mapped[str | None] = mapped_column(String(200))
    external_outcome_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)


class Source18ExternalComment(Base, TimestampMixin):
    __tablename__ = "source18_external_comments"
    __table_args__ = (Index("ix_source18_comment_cycle", "submission_cycle_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    submission_cycle_id: Mapped[str] = mapped_column(ForeignKey("source18_submission_cycles.id"), nullable=False)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)


class Source18LaborRosterSnapshot(Base):
    __tablename__ = "source18_labor_roster_snapshots"
    __table_args__ = (UniqueConstraint("office_id", "snapshot_hash", name="uq_source18_roster_snapshot_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    office_id: Mapped[str] = mapped_column(ForeignKey("consultancy_offices.id"), nullable=False, index=True)
    snapshot_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    source_version: Mapped[str] = mapped_column(String(100), nullable=False)
    source_ordering_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    departed_reconciliation_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    rows_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    captured_by: Mapped[str] = mapped_column(String(200), nullable=False)
