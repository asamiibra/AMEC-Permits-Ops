"""Case-specific Preparation + Submission Loop runtime companions.

These records deliberately sit beside, and reference, the canonical
Regulatory, Requirement, Form, Document, and Engineering domains. They are
immutable at the workflow boundaries that become evidence.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, utcnow


def _id() -> str:
    return str(uuid4())


class AuthorityCaseCreateRequest(Base):
    __tablename__ = "authority_case_create_requests"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_authority_case_create_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False, unique=True)
    requested_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuthorityCasePolicyBinding(Base, TimestampMixin):
    __tablename__ = "authority_case_policy_bindings"
    __table_args__ = (UniqueConstraint("authority_case_id", name="uq_authority_case_policy_binding_case"), Index("ix_authority_case_policy_binding_policy", "policy_version_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False)
    policy_version_id: Mapped[str] = mapped_column(ForeignKey("requirement_policy_versions.id"), nullable=False)
    resolution_state: Mapped[str] = mapped_column(String(30), nullable=False, default="RESOLVED")
    resolved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_by: Mapped[str] = mapped_column(String(200), nullable=False)
    resolution_facts: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class RequirementInstance(Base, TimestampMixin):
    __tablename__ = "requirement_instances"
    __table_args__ = (
        UniqueConstraint("authority_case_id", "policy_item_id", name="uq_requirement_instance_case_policy_item"),
        Index("ix_requirement_instance_case_status", "authority_case_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False)
    policy_version_id: Mapped[str] = mapped_column(ForeignKey("requirement_policy_versions.id"), nullable=False)
    policy_item_id: Mapped[str] = mapped_column(ForeignKey("requirement_policy_items.id"), nullable=False)
    requirement_definition_id: Mapped[str] = mapped_column(ForeignKey("requirement_definitions.id"), nullable=False)
    group_id: Mapped[str | None] = mapped_column(ForeignKey("requirement_groups.id"), index=True)
    lifecycle_phase_id: Mapped[str | None] = mapped_column(ForeignKey("regulatory_lifecycle_phases.id"), index=True)
    purpose: Mapped[str] = mapped_column(String(50), nullable=False, default="AUTHORITY_SUBMISSION")
    applicability: Mapped[str] = mapped_column(String(30), nullable=False, default="APPLICABILITY_UNKNOWN")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="MISSING")
    dependency_state: Mapped[str] = mapped_column(String(30), nullable=False, default="NOT_DUE")
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="Not yet evaluated")
    source_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evaluated_by: Mapped[str | None] = mapped_column(String(200))


class CaseEvidenceSelection(Base, TimestampMixin):
    __tablename__ = "case_evidence_selections"
    __table_args__ = (Index("ix_case_evidence_selection_instance", "requirement_instance_id", "status"), Index("ix_case_evidence_selection_case", "authority_case_id", "document_version_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False)
    requirement_instance_id: Mapped[str] = mapped_column(ForeignKey("requirement_instances.id"), nullable=False)
    document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    form_instance_id: Mapped[str | None] = mapped_column(ForeignKey("form_instances.id"), index=True)
    approved_design_baseline_id: Mapped[str | None] = mapped_column(ForeignKey("approved_design_baselines.id"), index=True)
    evidence_kind: Mapped[str] = mapped_column(String(50), nullable=False, default="DOCUMENT")
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="SELECTED")
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    details_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    selected_by: Mapped[str] = mapped_column(String(200), nullable=False)
    selected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PhysicalEvidenceItem(Base, TimestampMixin):
    __tablename__ = "physical_evidence_items"
    __table_args__ = (Index("ix_physical_evidence_case_status", "authority_case_id", "status"), Index("ix_physical_evidence_requirement", "requirement_instance_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False)
    requirement_instance_id: Mapped[str | None] = mapped_column(ForeignKey("requirement_instances.id"), index=True)
    item_type: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="EXPECTED")
    location: Mapped[str | None] = mapped_column(String(240))
    custodian: Mapped[str | None] = mapped_column(String(200))
    verified_by: Mapped[str | None] = mapped_column(String(200))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)


class SubmissionPackage(Base, TimestampMixin):
    __tablename__ = "submission_packages"
    __table_args__ = (UniqueConstraint("preparation_revision_id", name="uq_submission_package_preparation"), Index("ix_submission_package_case_state", "authority_case_id", "state"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    manifest_hash: Mapped[str | None] = mapped_column(String(64))
    manifest_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class SubmissionPackageItem(Base):
    __tablename__ = "submission_package_items"
    __table_args__ = (UniqueConstraint("package_id", "display_order", name="uq_submission_package_item_order"), Index("ix_submission_package_item_package", "package_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    package_id: Mapped[str] = mapped_column(ForeignKey("submission_packages.id"), nullable=False)
    item_type: Mapped[str] = mapped_column(String(50), nullable=False)
    requirement_instance_id: Mapped[str | None] = mapped_column(ForeignKey("requirement_instances.id"), index=True)
    evidence_selection_id: Mapped[str | None] = mapped_column(ForeignKey("case_evidence_selections.id"), index=True)
    document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    form_instance_id: Mapped[str | None] = mapped_column(ForeignKey("form_instances.id"), index=True)
    baseline_id: Mapped[str | None] = mapped_column(ForeignKey("approved_design_baselines.id"), index=True)
    baseline_member_id: Mapped[str | None] = mapped_column(ForeignKey("approved_design_baseline_members.id"), index=True)
    physical_evidence_item_id: Mapped[str | None] = mapped_column(ForeignKey("physical_evidence_items.id"), index=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    section: Mapped[str | None] = mapped_column(String(120))
    submission_filename: Mapped[str | None] = mapped_column(String(300))
    label: Mapped[str | None] = mapped_column(String(300))


class SubmissionPrecheckRun(Base, TimestampMixin):
    __tablename__ = "submission_precheck_runs"
    __table_args__ = (Index("ix_submission_precheck_case_result", "authority_case_id", "result"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    submission_package_id: Mapped[str] = mapped_column(ForeignKey("submission_packages.id"), nullable=False)
    policy_version_id: Mapped[str | None] = mapped_column(ForeignKey("requirement_policy_versions.id"), index=True)
    package_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    digital_readiness: Mapped[str] = mapped_column(String(30), nullable=False)
    physical_readiness: Mapped[str] = mapped_column(String(30), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evaluated_by: Mapped[str] = mapped_column(String(200), nullable=False)


class SubmissionPrecheckCheck(Base):
    __tablename__ = "submission_precheck_checks"
    __table_args__ = (Index("ix_submission_precheck_check_run", "precheck_run_id", "blocking", "result"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    precheck_run_id: Mapped[str] = mapped_column(ForeignKey("submission_precheck_runs.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    source_type: Mapped[str | None] = mapped_column(String(80))
    source_id: Mapped[str | None] = mapped_column(String(36))


class SubmissionAttempt(Base, TimestampMixin):
    __tablename__ = "submission_attempts"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_submission_attempt_idempotency"), Index("ix_submission_attempt_case_state", "authority_case_id", "state"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    submission_package_id: Mapped[str] = mapped_column(ForeignKey("submission_packages.id"), nullable=False)
    precheck_run_id: Mapped[str] = mapped_column(ForeignKey("submission_precheck_runs.id"), nullable=False)
    channel_code: Mapped[str] = mapped_column(String(60), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING_EXTERNAL_CONFIRMATION")
    authorized_by: Mapped[str] = mapped_column(String(200), nullable=False)
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ExternalSubmissionSnapshot(Base, TimestampMixin):
    __tablename__ = "external_submission_snapshots"
    __table_args__ = (UniqueConstraint("submission_attempt_id", name="uq_external_snapshot_attempt"), Index("ix_external_snapshot_case", "authority_case_id", "external_status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    submission_attempt_id: Mapped[str] = mapped_column(ForeignKey("submission_attempts.id"), nullable=False)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False)
    channel_code: Mapped[str] = mapped_column(String(60), nullable=False)
    package_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(240))
    external_status: Mapped[str] = mapped_column(String(40), nullable=False, default="RECEIVED")
    external_submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmation_source: Mapped[str] = mapped_column(String(40), nullable=False, default="MANUAL_CONFIRMED")
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    confirmed_by: Mapped[str] = mapped_column(String(200), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class AuthoritySubmissionCycle(Base, TimestampMixin):
    __tablename__ = "authority_submission_cycles"
    __table_args__ = (UniqueConstraint("authority_case_id", "cycle_number", name="uq_authority_submission_cycle_number"), Index("ix_authority_submission_cycle_case_status", "authority_case_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False)
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    submission_package_id: Mapped[str] = mapped_column(ForeignKey("submission_packages.id"), nullable=False)
    external_submission_snapshot_id: Mapped[str] = mapped_column(ForeignKey("external_submission_snapshots.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="SUBMITTED_CONFIRMED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AuthorityCaseFinding(Base, TimestampMixin):
    __tablename__ = "authority_case_findings"
    __table_args__ = (Index("ix_authority_case_finding_case_status", "authority_case_id", "status"), Index("ix_authority_case_finding_cycle", "submission_cycle_id"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False)
    submission_cycle_id: Mapped[str | None] = mapped_column(ForeignKey("authority_submission_cycles.id"), index=True)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    external_finding_id: Mapped[str | None] = mapped_column(String(160))
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="OPEN")
    severity: Mapped[str] = mapped_column(String(30), nullable=False, default="UNSPECIFIED")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    captured_by: Mapped[str] = mapped_column(String(200), nullable=False)
    engineering_impact: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN")
    affected_requirement_instance_id: Mapped[str | None] = mapped_column(ForeignKey("requirement_instances.id"), index=True)


class AuthorityFindingResponse(Base, TimestampMixin):
    __tablename__ = "authority_finding_responses"
    __table_args__ = (Index("ix_authority_finding_response_finding", "finding_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    finding_id: Mapped[str] = mapped_column(ForeignKey("authority_case_findings.id"), nullable=False)
    response_text: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    affected_requirement_instance_id: Mapped[str | None] = mapped_column(ForeignKey("requirement_instances.id"))
    affected_baseline_id: Mapped[str | None] = mapped_column(ForeignKey("approved_design_baselines.id"))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PREPARED")
    prepared_by: Mapped[str] = mapped_column(String(200), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthorityCaseOutcome(Base, TimestampMixin):
    __tablename__ = "authority_case_outcomes"
    __table_args__ = (Index("ix_authority_case_outcome_case", "authority_case_id", "outcome_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False)
    submission_cycle_id: Mapped[str | None] = mapped_column(ForeignKey("authority_submission_cycles.id"))
    outcome_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="VERIFIED")
    external_identifier: Mapped[str | None] = mapped_column(String(240))
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    evidence_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[str] = mapped_column(String(200), nullable=False)
    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
