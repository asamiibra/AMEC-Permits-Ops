"""Week 11 read-only monitoring, contract drift, and operator observability."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class MonitoringPolicy(Base):
    __tablename__ = "monitoring_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenario_configs.id"))
    application_id: Mapped[str | None] = mapped_column(ForeignKey("permit_applications.id"))
    environment: Mapped[str] = mapped_column(String(40), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(60), nullable=False)
    operations_allowed: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    cadence_mode: Mapped[str] = mapped_column(String(40), nullable=False)
    cadence_value: Mapped[int | None] = mapped_column(Integer)
    business_hours_policy: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    jitter_policy: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    max_failures_before_pause: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    adapter_id: Mapped[str] = mapped_column(String(100), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    portal_contract_version: Mapped[str] = mapped_column(String(50), nullable=False)
    fallback_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    notification_policy_id: Mapped[str | None] = mapped_column(String(100))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    version: Mapped[str] = mapped_column(String(40), default="W11-1.0", nullable=False)


class MonitoringExecutionDecision(Base):
    __tablename__ = "monitoring_execution_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    monitoring_policy_id: Mapped[str] = mapped_column(ForeignKey("monitoring_policies.id"), nullable=False)
    run_id: Mapped[str | None] = mapped_column(ForeignKey("monitoring_runs.id"))
    operation: Mapped[str] = mapped_column(String(60), nullable=False)
    decision: Mapped[str] = mapped_column(String(40), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(40), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class MonitoringRun(Base):
    __tablename__ = "monitoring_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    submission_cycle_id: Mapped[str | None] = mapped_column(ForeignKey("submission_cycles.id"))
    monitoring_policy_id: Mapped[str] = mapped_column(ForeignKey("monitoring_policies.id"), nullable=False)
    scheduled_for: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    environment: Mapped[str] = mapped_column(String(40), nullable=False)
    adapter_id: Mapped[str] = mapped_column(String(100), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    portal_contract_version: Mapped[str] = mapped_column(String(50), nullable=False)
    prior_snapshot_id: Mapped[str | None] = mapped_column(String(36))
    new_snapshot_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[str | None] = mapped_column(String(50))
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    retry_class: Mapped[str | None] = mapped_column(String(60))
    duration_ms: Mapped[int | None] = mapped_column(Integer)


class MonitoringCheck(Base):
    __tablename__ = "monitoring_checks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    monitoring_run_id: Mapped[str] = mapped_column(ForeignKey("monitoring_runs.id"), nullable=False)
    operation: Mapped[str] = mapped_column(String(60), nullable=False)
    prior_fingerprint: Mapped[str | None] = mapped_column(String(64))
    current_fingerprint: Mapped[str | None] = mapped_column(String(64))
    comparison_result: Mapped[str] = mapped_column(String(50), nullable=False)
    checked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evidence_artifact_id: Mapped[str | None] = mapped_column(String(300))
    status_code: Mapped[str | None] = mapped_column(String(50))
    repetition_number: Mapped[int | None] = mapped_column(Integer)
    comment_count: Mapped[int | None] = mapped_column(Integer)
    normalized_state_hash: Mapped[str | None] = mapped_column(String(64))


class MonitoringStateSnapshot(Base):
    __tablename__ = "monitoring_state_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    monitoring_run_id: Mapped[str] = mapped_column(ForeignKey("monitoring_runs.id"), nullable=False)
    capture_method: Mapped[str] = mapped_column(String(50), nullable=False)
    trusted: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    application_identity: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    state: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    raw_evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    contract_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PortalReadContract(Base):
    __tablename__ = "portal_read_contracts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    adapter_id: Mapped[str] = mapped_column(String(100), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(50), nullable=False)
    operation: Mapped[str] = mapped_column(String(60), nullable=False)
    expected_route_or_section: Mapped[str] = mapped_column(String(200), nullable=False)
    expected_field_keys: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    expected_status_semantics: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    expected_comment_structure: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    expected_identity_assertions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    expected_structural_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)


class PortalDriftEvent(Base):
    __tablename__ = "portal_drift_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    monitoring_run_id: Mapped[str | None] = mapped_column(ForeignKey("monitoring_runs.id"))
    adapter_id: Mapped[str] = mapped_column(String(100), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    operation: Mapped[str] = mapped_column(String(60), nullable=False)
    drift_type: Mapped[str] = mapped_column(String(60), nullable=False)
    expected_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_artifact_id: Mapped[str | None] = mapped_column(String(300))
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    revalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revalidated_by: Mapped[str | None] = mapped_column(String(200))


class PortalContractValidationRun(Base):
    __tablename__ = "portal_contract_validation_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    adapter_id: Mapped[str] = mapped_column(String(100), nullable=False)
    adapter_version: Mapped[str] = mapped_column(String(50), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(50), nullable=False)
    environment: Mapped[str] = mapped_column(String(40), nullable=False)
    test_fixture_version: Mapped[str] = mapped_column(String(80), nullable=False)
    operations_tested: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    pass_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fail_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AuthorityStatusObservation(Base):
    __tablename__ = "authority_status_observations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    submission_cycle_id: Mapped[str | None] = mapped_column(ForeignKey("submission_cycles.id"))
    monitoring_run_id: Mapped[str] = mapped_column(ForeignKey("monitoring_runs.id"), nullable=False)
    raw_status: Mapped[str] = mapped_column(String(80), nullable=False)
    normalized_status: Mapped[str] = mapped_column(String(80), nullable=False)
    authority_reference: Mapped[str | None] = mapped_column(String(160))
    repetition_number: Mapped[int | None] = mapped_column(Integer)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evidence_artifact_id: Mapped[str | None] = mapped_column(String(300))
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class AuthorityCommentObservation(Base):
    __tablename__ = "authority_comment_observations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    submission_cycle_id: Mapped[str | None] = mapped_column(ForeignKey("submission_cycles.id"))
    monitoring_run_id: Mapped[str] = mapped_column(ForeignKey("monitoring_runs.id"), nullable=False)
    external_comment_id: Mapped[str | None] = mapped_column(String(160))
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(30), nullable=False)
    authority_reference: Mapped[str | None] = mapped_column(String(160))
    section_object_reference: Mapped[str | None] = mapped_column(String(200))
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evidence_artifact_id: Mapped[str | None] = mapped_column(String(300))
    source_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized_key: Mapped[str | None] = mapped_column(String(240))


class AuthorityStateComparison(Base):
    __tablename__ = "authority_state_comparisons"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    monitoring_run_id: Mapped[str] = mapped_column(ForeignKey("monitoring_runs.id"), nullable=False)
    prior_snapshot_id: Mapped[str | None] = mapped_column(String(36))
    current_snapshot_id: Mapped[str | None] = mapped_column(String(36))
    status_changed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    prior_status: Mapped[str | None] = mapped_column(String(80))
    current_status: Mapped[str | None] = mapped_column(String(80))
    repetition_changed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    prior_repetition: Mapped[int | None] = mapped_column(Integer)
    current_repetition: Mapped[int | None] = mapped_column(Integer)
    new_comment_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    removed_comment_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    changed_comment_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    materiality: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    reasons: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class HumanMonitoringCapture(Base):
    __tablename__ = "human_monitoring_captures"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    submission_cycle_id: Mapped[str | None] = mapped_column(ForeignKey("submission_cycles.id"))
    captured_by: Mapped[str] = mapped_column(String(200), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(80), nullable=False)
    repetition_number: Mapped[int | None] = mapped_column(Integer)
    comments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evidence_artifact_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    verification_mode: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(60), nullable=False)


class ExternalMutationObservation(Base):
    __tablename__ = "external_mutation_observations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    monitoring_run_id: Mapped[str] = mapped_column(ForeignKey("monitoring_runs.id"), nullable=False)
    prior_snapshot_id: Mapped[str | None] = mapped_column(String(36))
    current_snapshot_id: Mapped[str | None] = mapped_column(String(36))
    changed_paths: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    prior_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    observed_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    impact: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_artifact_id: Mapped[str | None] = mapped_column(String(300))
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    authorship: Mapped[str] = mapped_column(String(60), default="EXTERNAL_HUMAN_OR_AUTHORITY", nullable=False)


class NotificationDeliveryAttempt(Base):
    __tablename__ = "notification_delivery_attempts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    notification_event_id: Mapped[str] = mapped_column(ForeignKey("notification_events.id"), nullable=False)
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    attempted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    failure_code: Mapped[str | None] = mapped_column(String(100))
    external_reference: Mapped[str | None] = mapped_column(String(200))


class OperatorTaskTiming(Base):
    __tablename__ = "operator_task_timings"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    user_role: Mapped[str] = mapped_column(String(80), nullable=False)
    scenario_variant: Mapped[str] = mapped_column(String(100), nullable=False)
    task_type: Mapped[str] = mapped_column(String(100), nullable=False)
    preparation_revision_id: Mapped[str | None] = mapped_column(ForeignKey("preparation_revisions.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    correction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    navigation_count: Mapped[int | None] = mapped_column(Integer)
    evidence_views: Mapped[int | None] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(60), nullable=False)
