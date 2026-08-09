"""Week 7 finding, task, SLA, authority-event, and notification entities.

Week 7 intentionally uses controlled string values instead of database enums so
configuration can evolve without silently changing the meaning of historical
records. All records are synthetic/dev-safe and preserve raw source evidence.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class FindingSourceType:
    INTERNAL_PREFLIGHT = "INTERNAL_PREFLIGHT"
    PORTAL_VALIDATION = "PORTAL_VALIDATION"
    AUTHORITY_PRECHECK = "AUTHORITY_PRECHECK"
    OFFICIAL_MUNICIPALITY_COMMENT = "OFFICIAL_MUNICIPALITY_COMMENT"
    EMAIL_NOTICE = "EMAIL_NOTICE"
    MANUAL_OPERATOR_CAPTURE = "MANUAL_OPERATOR_CAPTURE"


class FindingCodeStatus:
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    RETIRED = "RETIRED"


class FindingSeverity:
    BLOCKING = "BLOCKING"
    MAJOR = "MAJOR"
    ADVISORY = "ADVISORY"


class FindingStatus:
    OPEN = "OPEN"
    ASSIGNED = "ASSIGNED"
    IN_PROGRESS = "IN_PROGRESS"
    DISPUTED = "DISPUTED"
    DEFERRED = "DEFERRED"
    CORRECTION_MADE = "CORRECTION_MADE"
    EVIDENCE_ATTACHED = "EVIDENCE_ATTACHED"
    VERIFIED = "VERIFIED"
    CLOSED = "CLOSED"
    CLOSED_VERIFIED = "CLOSED_VERIFIED"
    REOPENED = "REOPENED"


class WorkflowTaskStatus:
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    IN_PROGRESS = "IN_PROGRESS"
    BLOCKED = "BLOCKED"
    DISPUTED = "DISPUTED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class NotificationStatus:
    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED = "FAILED"
    SUPPRESSED = "SUPPRESSED"


class FindingCode(Base):
    __tablename__ = "finding_codes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    title_en: Mapped[str] = mapped_column(String(240), nullable=False)
    title_ar: Mapped[str] = mapped_column(String(240), nullable=False)
    description_en: Mapped[str] = mapped_column(Text, nullable=False)
    description_ar: Mapped[str] = mapped_column(Text, nullable=False)
    source_classes_allowed: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    discipline: Mapped[str] = mapped_column(String(80), nullable=False)
    default_severity: Mapped[str] = mapped_column(String(30), nullable=False)
    blocking_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    required_owner_role: Mapped[str] = mapped_column(String(80), nullable=False)
    default_sla_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    closure_evidence_policy: Mapped[str] = mapped_column(String(60), nullable=False)
    internal_preflight_control_code: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checksum: Mapped[str | None] = mapped_column(String(64))
    finding_class: Mapped[str] = mapped_column(String(60), default="DATA_INTEGRITY", nullable=False)
    typical_root_cause_category: Mapped[str] = mapped_column(String(100), default="UNKNOWN_REVIEW_REQUIRED", nullable=False)
    closure_verifier_role: Mapped[str] = mapped_column(String(100), default="REQUIREMENT_STEWARD", nullable=False)
    allowed_dispositions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    resubmission_gate_effect: Mapped[str] = mapped_column(String(60), default="STILL_BLOCKS", nullable=False)
    precheck_gate_effect: Mapped[str] = mapped_column(String(60), default="BLOCKS_PRECHECK", nullable=False)
    recurrence_key_strategy: Mapped[str] = mapped_column(String(100), default="CODE_OBJECT", nullable=False)


class AuthorityEvent(Base):
    __tablename__ = "authority_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    source_channel: Mapped[str] = mapped_column(String(60), nullable=False)
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(300))
    external_event_id: Mapped[str | None] = mapped_column(String(160))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    raw_evidence_artifact_id: Mapped[str | None] = mapped_column(String(300))
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_key: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    linked_authority_event_id: Mapped[str | None] = mapped_column(String(36))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class SubmissionCycle(Base):
    """Minimum typed seam for an official returned-application review context."""

    __tablename__ = "submission_cycles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False)
    external_reference: Mapped[str | None] = mapped_column(String(160))
    source_reference: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    preparation_revision_id: Mapped[str | None] = mapped_column(ForeignKey("preparation_revisions.id"))
    submitted_snapshot_id: Mapped[str | None] = mapped_column(String(36))
    submission_confirmation_id: Mapped[str | None] = mapped_column(String(36))
    authority_repetition_number: Mapped[int | None] = mapped_column(Integer)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    preparation_revision_id: Mapped[str | None] = mapped_column(ForeignKey("preparation_revisions.id"))
    authority_precheck_run_id: Mapped[str | None] = mapped_column(ForeignKey("authority_precheck_runs.id"))
    submission_cycle_id: Mapped[str | None] = mapped_column(ForeignKey("submission_cycles.id"))
    authority_event_id: Mapped[str | None] = mapped_column(ForeignKey("authority_events.id"))
    finding_code_id: Mapped[str | None] = mapped_column(ForeignKey("finding_codes.id"))
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(300), nullable=False)
    external_finding_id: Mapped[str | None] = mapped_column(String(160))
    source_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    captured_by: Mapped[str] = mapped_column(String(200), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_summary: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(30), nullable=False)
    translated_summary: Mapped[str | None] = mapped_column(Text)
    discipline: Mapped[str] = mapped_column(String(80), nullable=False)
    affected_object_type: Mapped[str | None] = mapped_column(String(80))
    affected_object_id: Mapped[str | None] = mapped_column(String(160))
    requirement_code: Mapped[str | None] = mapped_column(String(120))
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    assignee_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    assignee_role: Mapped[str | None] = mapped_column(String(80))
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_artifact_id: Mapped[str | None] = mapped_column(String(300))
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    finding_code_version: Mapped[str | None] = mapped_column(String(40))
    finding_code_checksum: Mapped[str | None] = mapped_column(String(64))


class WorkflowTask(Base):
    __tablename__ = "workflow_tasks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    application_id: Mapped[str | None] = mapped_column(ForeignKey("permit_applications.id"))
    finding_id: Mapped[str | None] = mapped_column(ForeignKey("findings.id"))
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    owner_role: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    priority: Mapped[str] = mapped_column(String(30), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    escalation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    assistant_id: Mapped[str | None] = mapped_column(String(80), index=True)
    task_family: Mapped[str | None] = mapped_column(String(50), index=True)
    context_type: Mapped[str | None] = mapped_column(String(80))
    context_id: Mapped[str | None] = mapped_column(String(36), index=True)
    blocking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    next_action_code: Mapped[str | None] = mapped_column(String(100))
    deep_link: Mapped[str | None] = mapped_column(String(300))
    evidence_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class FindingRoutingRule(Base):
    __tablename__ = "finding_routing_rules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scenario_id: Mapped[str] = mapped_column(String(100), nullable=False)
    finding_code_id: Mapped[str | None] = mapped_column(ForeignKey("finding_codes.id"))
    discipline: Mapped[str | None] = mapped_column(String(80))
    source_type: Mapped[str | None] = mapped_column(String(60))
    severity: Mapped[str | None] = mapped_column(String(30))
    owner_role: Mapped[str] = mapped_column(String(80), nullable=False)
    preferred_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    escalation_role: Mapped[str] = mapped_column(String(80), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)


class FindingSlaPolicy(Base):
    __tablename__ = "finding_sla_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scenario_id: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(60))
    acknowledgment_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    assignment_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    target_action_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    escalation_hours: Mapped[int] = mapped_column(Integer, nullable=False)
    business_calendar_mode: Mapped[str] = mapped_column(String(60), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    policy_label: Mapped[str] = mapped_column(String(80), nullable=False)


class NotificationEvent(Base):
    __tablename__ = "notification_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), nullable=False)
    workflow_task_id: Mapped[str] = mapped_column(ForeignKey("workflow_tasks.id"), nullable=False)
    recipient_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    recipient_role: Mapped[str] = mapped_column(String(80), nullable=False)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    event_type: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    subject: Mapped[str] = mapped_column(String(300), nullable=False)
    body_preview: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    attempted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_code: Mapped[str | None] = mapped_column(String(100))
    external_message_reference: Mapped[str | None] = mapped_column(String(200))
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)


class PortalValidationFindingRule(Base):
    __tablename__ = "portal_validation_finding_rules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    validation_code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    create_finding: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    finding_code_id: Mapped[str | None] = mapped_column(ForeignKey("finding_codes.id"))
    owner_role: Mapped[str] = mapped_column(String(80), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
