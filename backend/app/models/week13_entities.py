"""Week 13 recurrence, operations, incident, and recovery evidence records."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class FindingRecurrenceAnalysisRun(Base):
    __tablename__ = "finding_recurrence_analysis_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenario_configs.id"))
    fixture_evidence_set_version: Mapped[str] = mapped_column(String(100), nullable=False)
    from_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    to_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finding_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    closed_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recurring_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recurrence_after_closure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    possible_recurrence_review_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class FindingRecurrenceAnalysisItem(Base):
    __tablename__ = "finding_recurrence_analysis_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    run_id: Mapped[str] = mapped_column(ForeignKey("finding_recurrence_analysis_runs.id"), nullable=False)
    finding_code: Mapped[str] = mapped_column(String(120), nullable=False)
    recurrence_key: Mapped[str] = mapped_column(String(300), nullable=False)
    root_cause_category: Mapped[str] = mapped_column(String(100), nullable=False)
    discipline: Mapped[str] = mapped_column(String(80), nullable=False)
    affected_object_key: Mapped[str | None] = mapped_column(String(200))
    occurrence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    submission_cycle_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    preparation_revision_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    prior_approval_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recurrence_after_closure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    first_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    related_finding_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    classification: Mapped[str] = mapped_column(String(60), nullable=False)
    result: Mapped[str] = mapped_column(String(60), nullable=False)


class PriorFindingPreventiveCheck(Base):
    __tablename__ = "prior_finding_preventive_checks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    preparation_revision_id: Mapped[str | None] = mapped_column(ForeignKey("preparation_revisions.id"))
    finding_code: Mapped[str] = mapped_column(String(120), nullable=False)
    prior_finding_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    current_affected_object: Mapped[str | None] = mapped_column(String(200))
    relevance_result: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class FindingPreventionControl(Base):
    __tablename__ = "finding_prevention_controls"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    finding_code_id: Mapped[str] = mapped_column(ForeignKey("finding_codes.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    control_code: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_requirement: Mapped[str | None] = mapped_column(String(120))
    owner_role: Mapped[str] = mapped_column(String(80), nullable=False)
    required_before_gate: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), nullable=False)


class SupportCase(Base):
    __tablename__ = "support_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    application_id: Mapped[str | None] = mapped_column(ForeignKey("permit_applications.id"))
    finding_id: Mapped[str | None] = mapped_column(ForeignKey("findings.id"))
    monitoring_run_id: Mapped[str | None] = mapped_column(ForeignKey("monitoring_runs.id"))
    opened_by: Mapped[str] = mapped_column(String(200), nullable=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    current_level: Mapped[str] = mapped_column(String(20), nullable=False)
    assigned_to: Mapped[str | None] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    external_dependency: Mapped[str | None] = mapped_column(String(200))
    resolution_summary: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)


class IntegrityIncident(Base):
    __tablename__ = "integrity_incidents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)
    incident_type: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    application_id: Mapped[str | None] = mapped_column(ForeignKey("permit_applications.id"))
    source_entity_type: Mapped[str | None] = mapped_column(String(100))
    source_entity_id: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evidence_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    notifications: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    root_cause_category: Mapped[str | None] = mapped_column(String(120))
    corrective_action: Mapped[str | None] = mapped_column(Text)
    residual_risk: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)


class WorkflowSafetyHold(Base):
    __tablename__ = "workflow_safety_holds"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scope_type: Mapped[str] = mapped_column(String(80), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(160), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    incident_id: Mapped[str] = mapped_column(ForeignKey("integrity_incidents.id"), nullable=False)
    blocks_automated_writes: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    blocks_final_review_readiness: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    blocks_resubmission_readiness: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    released_by: Mapped[str | None] = mapped_column(String(200))
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    release_evidence: Mapped[list[str] | None] = mapped_column(JSON)


class IncidentImpactAssessment(Base):
    __tablename__ = "incident_impact_assessments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    incident_id: Mapped[str] = mapped_column(ForeignKey("integrity_incidents.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(160), nullable=False)
    affected_entities: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    lineage_edge_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    assessed_by: Mapped[str] = mapped_column(String(200), nullable=False)
    assessed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class RecoveryManifest(Base):
    __tablename__ = "recovery_manifests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    environment: Mapped[str] = mapped_column(String(40), nullable=False)
    backup_set_id: Mapped[str] = mapped_column(String(160), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    database_backup_ref: Mapped[str] = mapped_column(String(300), nullable=False)
    evidence_store_backup_ref: Mapped[str | None] = mapped_column(String(300))
    config_snapshot_ref: Mapped[str] = mapped_column(String(300), nullable=False)
    schema_migration_head: Mapped[str] = mapped_column(String(80), nullable=False)
    fixture_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    config_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    encryption_handling_status: Mapped[str] = mapped_column(String(100), nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)


class RestoreRehearsal(Base):
    __tablename__ = "restore_rehearsals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    recovery_manifest_id: Mapped[str] = mapped_column(ForeignKey("recovery_manifests.id"), nullable=False)
    rehearsal_type: Mapped[str] = mapped_column(String(60), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    checks: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)
    not_formal_g10: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class KillSwitchReadiness(Base):
    __tablename__ = "kill_switch_readiness"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    environment: Mapped[str] = mapped_column(String(40), nullable=False)
    mode: Mapped[str] = mapped_column(String(40), nullable=False)
    write_kill_switch: Mapped[str] = mapped_column(String(60), nullable=False)
    tested: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    retained_capabilities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    disabled_capabilities: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)
    result_hash: Mapped[str] = mapped_column(String(64), nullable=False)


class RoleTrainingChecklist(Base):
    __tablename__ = "role_training_checklists"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    checklist_version: Mapped[str] = mapped_column(String(40), nullable=False)
    boundaries: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    evidence_requirements: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    stop_conditions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    escalation_route: Mapped[str] = mapped_column(String(200), nullable=False)
    evidence_class: Mapped[str] = mapped_column(String(80), nullable=False)

