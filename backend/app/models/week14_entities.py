"""Week 14 acceptance rehearsal, pilot readiness, metrics, and G10 evidence."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class AcceptanceRehearsalRun(Base):
    __tablename__ = "acceptance_rehearsal_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    fixture_set: Mapped[str] = mapped_column(String(160), nullable=False)
    fixture_version: Mapped[str] = mapped_column(String(40), nullable=False)
    fixture_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    configuration_bundle_versions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    project_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    application_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    operator_identities: Mapped[list[dict[str, str]]] = mapped_column(JSON, default=list, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[str] = mapped_column(String(50), nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)
    operator_assistance_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    correlation_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    audit_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class AcceptanceMetric(Base):
    __tablename__ = "acceptance_metrics"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    rehearsal_run_id: Mapped[str] = mapped_column(ForeignKey("acceptance_rehearsal_runs.id"), nullable=False)
    metric: Mapped[str] = mapped_column(String(120), nullable=False)
    value: Mapped[float | None] = mapped_column(nullable=True)
    sample_size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)
    approved_threshold: Mapped[float | None] = mapped_column(nullable=True)
    threshold_status: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ShadowDefectDisposition(Base):
    __tablename__ = "shadow_defect_dispositions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    defect_id: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    affected_requirement: Mapped[str] = mapped_column(String(100), nullable=False)
    scenario_variant: Mapped[str] = mapped_column(String(100), nullable=False)
    root_cause: Mapped[str] = mapped_column(String(160), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    fix: Mapped[str] = mapped_column(Text, nullable=False)
    test_reference: Mapped[str] = mapped_column(String(300), nullable=False)
    acceptance_impact: Mapped[str] = mapped_column(String(100), nullable=False)
    g10_impact: Mapped[str] = mapped_column(String(100), nullable=False)


class PilotWorkflowApproval(Base):
    __tablename__ = "pilot_workflow_approvals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    scenario_variant: Mapped[str] = mapped_column(String(100), nullable=False)
    workflow_version: Mapped[str] = mapped_column(String(40), nullable=False)
    rehearsal_run_id: Mapped[str | None] = mapped_column(ForeignKey("acceptance_rehearsal_runs.id"))
    result: Mapped[str] = mapped_column(String(60), nullable=False)
    blockers: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    comments: Mapped[str] = mapped_column(Text, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)
    client_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class RoleReadinessMatrix(Base):
    __tablename__ = "role_readiness_matrix"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    training_material_exists: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    rehearsal_performed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    competency_evidence: Mapped[str] = mapped_column(Text, nullable=False)
    open_questions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    client_approved: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    g10_impact: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)


class G10EvidenceItem(Base):
    __tablename__ = "g10_evidence_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    criterion_id: Mapped[str] = mapped_column(String(100), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False)
    requirement: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_path: Mapped[str] = mapped_column(String(400), nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    blocker: Mapped[str | None] = mapped_column(Text)
    next_action: Mapped[str | None] = mapped_column(Text)


class ProductionModeDecision(Base):
    __tablename__ = "production_mode_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    mode: Mapped[str] = mapped_column(String(40), nullable=False)
    supported_operations: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    environment_assumptions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    capability_policy: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    observed_quality_performance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    defects: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    drift_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    mfa_session_behavior: Mapped[str] = mapped_column(Text, nullable=False)
    recovery_takeover: Mapped[str] = mapped_column(Text, nullable=False)
    residual_risks: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    g10_dependencies: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    decision: Mapped[str] = mapped_column(String(80), nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)

