"""Week 10 closure, resubmission, control-catalogue, and current-state-loop records."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class FindingResolution(Base):
    __tablename__ = "finding_resolutions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), nullable=False)
    resolution_version: Mapped[int] = mapped_column(Integer, nullable=False)
    disposition: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    correction_type: Mapped[str] = mapped_column(String(100), nullable=False)
    correction_summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause_category: Mapped[str] = mapped_column(String(100), nullable=False)
    corrected_entity_type: Mapped[str | None] = mapped_column(String(100))
    corrected_entity_id: Mapped[str | None] = mapped_column(String(160))
    corrected_version_or_hash: Mapped[str | None] = mapped_column(String(160))
    required_evidence_policy: Mapped[str] = mapped_column(String(100), nullable=False)
    closure_criteria_version: Mapped[str] = mapped_column(String(40), nullable=False)
    proposed_by: Mapped[str] = mapped_column(String(200), nullable=False)
    proposed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    verified_by: Mapped[str | None] = mapped_column(String(200))
    verifier_role: Mapped[str | None] = mapped_column(String(100))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verification_result: Mapped[str | None] = mapped_column(String(50))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    prior_resolution_id: Mapped[str | None] = mapped_column(ForeignKey("finding_resolutions.id"))
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)


class FindingResolutionEvidence(Base):
    __tablename__ = "finding_resolution_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    finding_resolution_id: Mapped[str] = mapped_column(ForeignKey("finding_resolutions.id"), nullable=False)
    evidence_artifact_id: Mapped[str] = mapped_column(String(300), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_entity_type: Mapped[str | None] = mapped_column(String(100))
    source_entity_id: Mapped[str | None] = mapped_column(String(160))
    source_version_or_hash: Mapped[str | None] = mapped_column(String(160))
    added_by: Mapped[str] = mapped_column(String(200), nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FindingClosureEvaluation(Base):
    __tablename__ = "finding_closure_evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), nullable=False)
    resolution_id: Mapped[str] = mapped_column(ForeignKey("finding_resolutions.id"), nullable=False)
    finding_code_version: Mapped[str] = mapped_column(String(40), nullable=False)
    required_evidence: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    provided_evidence: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    required_verifier_role: Mapped[str] = mapped_column(String(100), nullable=False)
    verifier: Mapped[str | None] = mapped_column(String(200))
    result: Mapped[str] = mapped_column(String(60), nullable=False)
    blockers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FindingDispute(Base):
    __tablename__ = "finding_disputes"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), nullable=False)
    raised_by: Mapped[str] = mapped_column(String(200), nullable=False)
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_artifact_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(200))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decision: Mapped[str | None] = mapped_column(String(80))
    resubmission_effect: Mapped[str] = mapped_column(String(50), nullable=False)


class FindingReopenEvent(Base):
    __tablename__ = "finding_reopen_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), nullable=False)
    prior_resolution_id: Mapped[str | None] = mapped_column(ForeignKey("finding_resolutions.id"))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    source_authority_event_id: Mapped[str | None] = mapped_column(ForeignKey("authority_events.id"))
    reopened_by: Mapped[str] = mapped_column(String(200), nullable=False)
    reopened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FindingHistoryLink(Base):
    __tablename__ = "finding_history_links"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    current_finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), nullable=False)
    prior_finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), nullable=False)
    relationship_type: Mapped[str] = mapped_column(String(60), nullable=False)
    finding_code: Mapped[str] = mapped_column(String(120), nullable=False)
    affected_object_key: Mapped[str | None] = mapped_column(String(200))
    submission_cycle_id: Mapped[str | None] = mapped_column(ForeignKey("submission_cycles.id"))
    preparation_revision_id: Mapped[str | None] = mapped_column(ForeignKey("preparation_revisions.id"))
    linked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    linked_by: Mapped[str] = mapped_column(String(200), nullable=False)
    confidence_mode: Mapped[str] = mapped_column(String(60), nullable=False)


class PrecheckClearanceEvaluation(Base):
    __tablename__ = "precheck_clearance_evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    precheck_run_id: Mapped[str] = mapped_column(ForeignKey("authority_precheck_runs.id"), nullable=False)
    blocking_finding_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    unresolved_blocking_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stale_input: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    result: Mapped[str] = mapped_column(String(60), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evaluation_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class SubmittedSnapshot(Base):
    __tablename__ = "submitted_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    submission_cycle_id: Mapped[str] = mapped_column(ForeignKey("submission_cycles.id"), nullable=False)
    preparation_revision_id: Mapped[str] = mapped_column(ForeignKey("preparation_revisions.id"), nullable=False)
    package_id: Mapped[str] = mapped_column(ForeignKey("packages.id"), nullable=False)
    package_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    portal_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("portal_snapshots.id"))
    submitted_values: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    submitted_grids: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    submitted_attachments: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    authority_status: Mapped[str] = mapped_column(String(50), nullable=False)
    submission_reference: Mapped[str] = mapped_column(String(160), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    capture_method: Mapped[str] = mapped_column(String(60), nullable=False)
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class ApprovalApplicabilityEvaluation(Base):
    __tablename__ = "approval_applicability_evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    approval_id: Mapped[str] = mapped_column(ForeignKey("approvals.id"), nullable=False)
    prior_entity_id: Mapped[str] = mapped_column(String(160), nullable=False)
    current_entity_id: Mapped[str] = mapped_column(String(160), nullable=False)
    same_hash_or_scope: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    material_change: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    result: Mapped[str] = mapped_column(String(60), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ResubmissionReadinessEvaluation(Base):
    __tablename__ = "resubmission_readiness_evaluations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    submission_cycle_id: Mapped[str | None] = mapped_column(ForeignKey("submission_cycles.id"))
    preparation_revision_id: Mapped[str | None] = mapped_column(ForeignKey("preparation_revisions.id"))
    package_id: Mapped[str | None] = mapped_column(ForeignKey("packages.id"))
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    overall_status: Mapped[str] = mapped_column(String(60), nullable=False)
    blocking_finding_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    allowed_dispute_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    package_status: Mapped[str | None] = mapped_column(String(50))
    precheck_status: Mapped[str | None] = mapped_column(String(60))
    dependency_validity_status: Mapped[str | None] = mapped_column(String(60))
    approval_status: Mapped[str | None] = mapped_column(String(60))
    portal_reconciliation_status: Mapped[str | None] = mapped_column(String(60))
    reasons: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evaluation_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class ControlDefinition(Base):
    __tablename__ = "control_definitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    control_code: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_fields: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    blocking: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    finding_code_on_fail: Mapped[str | None] = mapped_column(String(120))
    verifier_role: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)


class ControlRun(Base):
    __tablename__ = "control_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    control_definition_id: Mapped[str] = mapped_column(ForeignKey("control_definitions.id"), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    package_id: Mapped[str | None] = mapped_column(ForeignKey("packages.id"))
    preparation_revision_id: Mapped[str | None] = mapped_column(ForeignKey("preparation_revisions.id"))
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)


class RuleCandidate(Base):
    __tablename__ = "rule_candidates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    source_finding_id: Mapped[str] = mapped_column(ForeignKey("findings.id"), nullable=False)
    proposed_control_area: Mapped[str] = mapped_column(String(120), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class RequirementMatrixCoverage(Base):
    __tablename__ = "requirement_matrix_coverage"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scenario_id: Mapped[str] = mapped_column(String(120), nullable=False)
    scenario_version: Mapped[str] = mapped_column(String(80), nullable=False)
    total_requirements: Mapped[int] = mapped_column(Integer, nullable=False)
    complete: Mapped[int] = mapped_column(Integer, nullable=False)
    incomplete: Mapped[int] = mapped_column(Integer, nullable=False)
    blocked_external: Mapped[int] = mapped_column(Integer, nullable=False)
    not_applicable: Mapped[int] = mapped_column(Integer, nullable=False)
    unknown: Mapped[int] = mapped_column(Integer, nullable=False)
    coverage_percent: Mapped[int] = mapped_column(Integer, nullable=False)
    missing_attributes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class FieldMatrixCoverage(Base):
    __tablename__ = "field_matrix_coverage"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scenario_id: Mapped[str] = mapped_column(String(120), nullable=False)
    field_set_version: Mapped[str] = mapped_column(String(80), nullable=False)
    total_fields: Mapped[int] = mapped_column(Integer, nullable=False)
    critical_fields: Mapped[int] = mapped_column(Integer, nullable=False)
    complete_fields: Mapped[int] = mapped_column(Integer, nullable=False)
    incomplete_fields: Mapped[int] = mapped_column(Integer, nullable=False)
    blocked_external: Mapped[int] = mapped_column(Integer, nullable=False)
    unknown: Mapped[int] = mapped_column(Integer, nullable=False)
    target_coverage: Mapped[dict[str, int]] = mapped_column(JSON, default=dict, nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
