"""Construction and post-approval execution records.

Construction owns execution state and evidence links, while the upstream
permit, contract, party, document, and engineering domains remain canonical.
The snapshot records intentionally denormalize the exact inputs used by a
human gate so later edits cannot silently change historical authorization.
"""

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class ConstructionExecution(Base):
    __tablename__ = "construction_executions"
    __table_args__ = (
        UniqueConstraint("project_id", "execution_ref", name="uq_construction_execution_ref"),
        Index("ix_construction_execution_project_status", "project_id", "status", "work_state"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    contract_id: Mapped[str | None] = mapped_column(ForeignKey("contracts.id"), index=True)
    contract_revision_id: Mapped[str | None] = mapped_column(ForeignKey("contract_revisions.id"), index=True)
    authority_case_id: Mapped[str | None] = mapped_column(ForeignKey("authority_cases.id"), index=True)
    execution_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    scope_description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PLANNED")
    work_state: Mapped[str] = mapped_column(String(40), nullable=False, default="NOT_STARTED")
    current_authority_snapshot_id: Mapped[str | None] = mapped_column(String(36), index=True)
    current_design_snapshot_id: Mapped[str | None] = mapped_column(String(36), index=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class AuthorityApprovedDesignSnapshot(Base):
    __tablename__ = "authority_approved_design_snapshots"
    __table_args__ = (Index("ix_authority_approved_snapshot_execution", "construction_execution_id", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    authority_case_id: Mapped[str | None] = mapped_column(ForeignKey("authority_cases.id"), index=True)
    authority_outcome_id: Mapped[str | None] = mapped_column(ForeignKey("authority_outcomes.id"), index=True)
    submission_cycle_id: Mapped[str | None] = mapped_column(ForeignKey("authority_submission_cycles.id"), index=True)
    external_submission_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("external_submission_snapshots.id"), index=True)
    submission_package_id: Mapped[str | None] = mapped_column(ForeignKey("submission_packages.id"), index=True)
    preparation_revision_id: Mapped[str | None] = mapped_column(ForeignKey("preparation_revisions.id"), index=True)
    approved_design_baseline_id: Mapped[str] = mapped_column(ForeignKey("approved_design_baselines.id"), nullable=False, index=True)
    authority_decision_reference: Mapped[str | None] = mapped_column(String(240))
    external_approval_reference: Mapped[str | None] = mapped_column(String(240))
    authority_state: Mapped[str] = mapped_column(String(40), nullable=False, default="APPROVED")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CURRENT")
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_until: Mapped[date | None] = mapped_column(Date)
    source_document_version_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    baseline_member_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    source_lineage_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    captured_by: Mapped[str] = mapped_column(String(200), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ConstructionDesignSnapshot(Base):
    __tablename__ = "construction_design_snapshots"
    __table_args__ = (
        UniqueConstraint("construction_execution_id", "version_number", name="uq_construction_design_snapshot_version"),
        Index("ix_construction_design_snapshot_execution", "construction_execution_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    authority_approved_design_snapshot_id: Mapped[str] = mapped_column(ForeignKey("authority_approved_design_snapshots.id"), nullable=False)
    approved_design_baseline_id: Mapped[str] = mapped_column(ForeignKey("approved_design_baselines.id"), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CURRENT")
    member_revision_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    member_rendition_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    document_version_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("construction_design_snapshots.id"))
    promoted_by: Mapped[str] = mapped_column(String(200), nullable=False)
    promoted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ConstructionStartReadiness(Base):
    __tablename__ = "construction_start_readiness"
    __table_args__ = (Index("ix_construction_start_readiness_execution", "construction_execution_id", "evaluated_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    blockers_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    checks_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evaluation_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    evaluated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ConstructionStartAuthorization(Base):
    __tablename__ = "construction_start_authorizations"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_construction_start_authorization_idempotency"),
        Index("ix_construction_start_authorization_execution", "construction_execution_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    project_activation_id: Mapped[str] = mapped_column(ForeignKey("project_activations.id"), nullable=False)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False)
    authority_approved_design_snapshot_id: Mapped[str] = mapped_column(ForeignKey("authority_approved_design_snapshots.id"), nullable=False)
    construction_design_snapshot_id: Mapped[str] = mapped_column(ForeignKey("construction_design_snapshots.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="START_AUTHORIZED")
    intended_start_date: Mapped[date | None] = mapped_column(Date)
    readiness_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    party_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    authorization_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    authorized_by: Mapped[str] = mapped_column(String(200), nullable=False)
    authorized_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ConstructionPartyAssignment(Base):
    __tablename__ = "construction_party_assignments"
    __table_args__ = (Index("ix_construction_party_assignment_execution", "construction_execution_id", "role_code", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    authority_case_id: Mapped[str | None] = mapped_column(ForeignKey("authority_cases.id"), index=True)
    party_role_assignment_id: Mapped[str | None] = mapped_column(ForeignKey("party_role_assignments.id"), index=True)
    professional_credential_id: Mapped[str | None] = mapped_column(ForeignKey("professional_credentials.id"), index=True)
    role_code: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    credential_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    assigned_by: Mapped[str] = mapped_column(String(200), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ConstructionObligationDefinition(Base):
    __tablename__ = "construction_obligation_definitions"
    __table_args__ = (UniqueConstraint("project_id", "code", "version", name="uq_construction_obligation_definition"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    authority_case_id: Mapped[str | None] = mapped_column(ForeignKey("authority_cases.id"), index=True)
    requirement_definition_id: Mapped[str | None] = mapped_column(ForeignKey("requirement_definitions.id"), index=True)
    policy_version_id: Mapped[str | None] = mapped_column(ForeignKey("requirement_policy_versions.id"), index=True)
    code: Mapped[str] = mapped_column(String(120), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_type: Mapped[str] = mapped_column(String(60), nullable=False, default="MANUAL")
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    required_role_codes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    due_rule_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ConstructionObligationInstance(Base):
    __tablename__ = "construction_obligation_instances"
    __table_args__ = (Index("ix_construction_obligation_instance_execution", "construction_execution_id", "status", "due_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    definition_id: Mapped[str] = mapped_column(ForeignKey("construction_obligation_definitions.id"), nullable=False)
    authority_case_id: Mapped[str | None] = mapped_column(ForeignKey("authority_cases.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="WAITING_TRIGGER")
    trigger_event_type: Mapped[str | None] = mapped_column(String(60))
    trigger_event_id: Mapped[str | None] = mapped_column(String(36))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completion_evidence_document_version_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    instance_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ConstructionObligationParticipant(Base):
    __tablename__ = "construction_obligation_participants"
    __table_args__ = (UniqueConstraint("obligation_instance_id", "party_id", "role_code", name="uq_construction_obligation_participant"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    obligation_instance_id: Mapped[str] = mapped_column(ForeignKey("construction_obligation_instances.id"), nullable=False, index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    role_code: Mapped[str] = mapped_column(String(80), nullable=False)
    responsibility: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    assigned_by: Mapped[str] = mapped_column(String(200), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ConstructionWorkControlEvent(Base):
    __tablename__ = "construction_work_control_events"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_construction_work_control_event_idempotency"),
        Index("ix_construction_work_control_event_execution", "construction_execution_id", "event_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    start_authorization_id: Mapped[str | None] = mapped_column(ForeignKey("construction_start_authorizations.id"), index=True)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    prior_state: Mapped[str] = mapped_column(String(40), nullable=False)
    new_state: Mapped[str] = mapped_column(String(40), nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False, default="HUMAN_COMMAND")
    source_id: Mapped[str | None] = mapped_column(String(160))
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    notes: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)


class AuthorityNotification(Base):
    __tablename__ = "construction_authority_notifications"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_construction_authority_notification_idempotency"), Index("ix_construction_authority_notification_execution", "construction_execution_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    authority_case_id: Mapped[str | None] = mapped_column(ForeignKey("authority_cases.id"), index=True)
    obligation_instance_id: Mapped[str | None] = mapped_column(ForeignKey("construction_obligation_instances.id"), index=True)
    work_control_event_id: Mapped[str | None] = mapped_column(ForeignKey("construction_work_control_events.id"), index=True)
    notification_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PREPARED")
    channel_code: Mapped[str] = mapped_column(String(60), nullable=False, default="MANUAL_PORTAL")
    recipient_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    payload_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(240))
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    prepared_by: Mapped[str] = mapped_column(String(200), nullable=False)
    prepared_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    sent_by: Mapped[str | None] = mapped_column(String(200))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)


class ProjectCorrespondence(Base):
    __tablename__ = "construction_correspondence"
    __table_args__ = (Index("ix_construction_correspondence_execution", "construction_execution_id", "status", "occurred_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    authority_case_id: Mapped[str | None] = mapped_column(ForeignKey("authority_cases.id"), index=True)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PREPARED")
    sender_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"))
    recipient_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"))
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    reference: Mapped[str | None] = mapped_column(String(160))
    document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    external_reference: Mapped[str | None] = mapped_column(String(240))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ConstructionInspection(Base):
    __tablename__ = "construction_inspections"
    __table_args__ = (Index("ix_construction_inspection_execution", "construction_execution_id", "inspection_kind", "status"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    authority_case_id: Mapped[str | None] = mapped_column(ForeignKey("authority_cases.id"), index=True)
    inspection_kind: Mapped[str] = mapped_column(String(30), nullable=False)  # INTERNAL_SITE or AUTHORITY
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="REQUESTED")
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    inspector_party_id: Mapped[str | None] = mapped_column(ForeignKey("parties.id"), index=True)
    authority_reference: Mapped[str | None] = mapped_column(String(240))
    outcome: Mapped[str | None] = mapped_column(String(40))
    findings_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evidence_document_version_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ConstructionIssue(Base):
    __tablename__ = "construction_issues"
    __table_args__ = (Index("ix_construction_issue_execution", "construction_execution_id", "status", "severity"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    issue_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False, default="MAJOR")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_scope: Mapped[str | None] = mapped_column(String(240))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    observed_by: Mapped[str] = mapped_column(String(200), nullable=False)
    authority_case_finding_id: Mapped[str | None] = mapped_column(ForeignKey("authority_case_findings.id"), index=True)
    design_change_request_id: Mapped[str | None] = mapped_column(ForeignKey("design_change_requests.id"), index=True)
    requirement_instance_id: Mapped[str | None] = mapped_column(ForeignKey("requirement_instances.id"), index=True)
    evidence_document_version_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    resolution_notes: Mapped[str | None] = mapped_column(Text)
    resolved_by: Mapped[str | None] = mapped_column(String(200))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ConstructionEvidenceLink(Base):
    __tablename__ = "construction_evidence_links"
    __table_args__ = (Index("ix_construction_evidence_link_execution", "construction_execution_id", "evidence_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(60), nullable=False)
    document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    physical_evidence_item_id: Mapped[str | None] = mapped_column(ForeignKey("physical_evidence_items.id"), index=True)
    material_test_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_material_tests.id"), index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    captured_by: Mapped[str] = mapped_column(String(200), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
