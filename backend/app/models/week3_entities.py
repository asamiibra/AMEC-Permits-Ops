from datetime import date, datetime
from enum import Enum
from typing import Any
from uuid import uuid4
from sqlalchemy import JSON, Boolean, Date, DateTime, Enum as SAEnum, ForeignKey, Integer, Float, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base, utcnow


def enum_col(enum_type): return SAEnum(enum_type)


class Phase(str, Enum): PHASE_0 = "PHASE_0"; STAGE_2 = "STAGE_2"
class BaselineStatus(str, Enum): WORKING = "WORKING"; READY_FOR_REVIEW = "READY_FOR_REVIEW"; APPROVED = "APPROVED"; APPROVED_WITH_CONDITIONS = "APPROVED_WITH_CONDITIONS"; PAUSED = "PAUSED"; NO_GO = "NO_GO"; SUPERSEDED = "SUPERSEDED"
class AdjudicationStatus(str, Enum): PENDING = "PENDING"; IN_REVIEW = "IN_REVIEW"; DISPUTED = "DISPUTED"; ADJUDICATED = "ADJUDICATED"
class ThresholdCategory(str, Enum): SAFETY = "SAFETY"; QUALITY = "QUALITY"; EFFICIENCY = "EFFICIENCY"; OPERATIONS = "OPERATIONS"; ADOPTION = "ADOPTION"
class ThresholdStatus(str, Enum): MEASURED = "MEASURED"; PROPOSED = "PROPOSED"; NEEDS_MORE_EVIDENCE = "NEEDS_MORE_EVIDENCE"; APPROVED_STAGE_2 = "APPROVED_STAGE_2"; NOT_APPLICABLE = "NOT_APPLICABLE"
class AcceptanceCorpusStatus(str, Enum): DRAFT = "DRAFT"; READY_FOR_REVIEW = "READY_FOR_REVIEW"; APPROVED = "APPROVED"
class Tier1DecisionStatus(str, Enum): OPEN = "OPEN"; ESCALATED = "ESCALATED"; RESOLVED = "RESOLVED"; RESOLVED_WITH_FALLBACK = "RESOLVED_WITH_FALLBACK"; BLOCKER = "BLOCKER"
class Tier2Category(str, Enum): FIELD_MATRIX = "FIELD_MATRIX"; REQUIREMENT_MATRIX = "REQUIREMENT_MATRIX"; RENDERING = "RENDERING"; FINDING_TAXONOMY = "FINDING_TAXONOMY"; EDGE_CASE = "EDGE_CASE"; KPI = "KPI"; MUNICIPALITY_MAPPING = "MUNICIPALITY_MAPPING"; DOCUMENT = "DOCUMENT"
class Tier2Status(str, Enum): OPEN = "OPEN"; IN_PROGRESS = "IN_PROGRESS"; DONE = "DONE"; DEFERRED = "DEFERRED"
class DeliveryStatus(str, Enum): CANDIDATE = "CANDIDATE"; SELECTED_DEMO = "SELECTED_DEMO"; REJECTED = "REJECTED"
class SelectedMode(str, Enum): ASSISTED = "ASSISTED"; MOCK = "MOCK"; API = "API"; BROWSER = "BROWSER"; NOT_SUPPORTED = "NOT_SUPPORTED"
class DecisionStatus3(str, Enum): PASS = "PASS"; PASS_WITH_CONDITION = "PASS_WITH_CONDITION"; FAIL = "FAIL"; UNKNOWN = "UNKNOWN"
class Phase0DecisionType(str, Enum): GO = "GO"; GO_WITH_FALLBACK = "GO_WITH_FALLBACK"; GO_WITH_REDUCED_DEPTH = "GO_WITH_REDUCED_DEPTH"; PAUSE = "PAUSE"; NO_GO = "NO_GO"
class Stage2Status(str, Enum): DRAFT = "DRAFT"; READY_FOR_REVIEW = "READY_FOR_REVIEW"; APPROVED = "APPROVED"; APPROVED_WITH_CONDITIONS = "APPROVED_WITH_CONDITIONS"; REJECTED = "REJECTED"
class SignoffStatus(str, Enum): DRAFT = "DRAFT"; READY_FOR_COMMERCIAL_REVIEW = "READY_FOR_COMMERCIAL_REVIEW"; ISSUED = "ISSUED"; SIGNED = "SIGNED"; DECLINED = "DECLINED"
class PilotStatus(str, Enum): PROPOSED = "PROPOSED"; CONFIRMED = "CONFIRMED"


class PhaseBaseline(Base):
    __tablename__ = "phase_baselines"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    phase: Mapped[Phase] = mapped_column(enum_col(Phase), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[BaselineStatus] = mapped_column(enum_col(BaselineStatus), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str] = mapped_column(Text, nullable=False)


class AdjudicationCase(Base):
    __tablename__ = "adjudication_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    dataset_id: Mapped[str] = mapped_column(String(120), nullable=False)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, unique=True)
    status: Mapped[AdjudicationStatus] = mapped_column(enum_col(AdjudicationStatus), nullable=False)
    steward_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    responsible_engineer_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)
    expected_class: Mapped[str | None] = mapped_column(String(100))
    ambiguity: Mapped[str | None] = mapped_column(Text)


class AdjudicationHistory(Base):
    __tablename__ = "adjudication_histories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    case_id: Mapped[str] = mapped_column(ForeignKey("adjudication_cases.id"), nullable=False)
    action: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(200), nullable=False)
    before_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)


class ThresholdDefinition(Base):
    __tablename__ = "threshold_definitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    metric_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    metric_name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[ThresholdCategory] = mapped_column(enum_col(ThresholdCategory), nullable=False)
    observed_value: Mapped[float | None] = mapped_column(Float)
    sample_size: Mapped[int | None] = mapped_column(Integer)
    proposed_threshold: Mapped[float | None] = mapped_column(Float)
    comparison_operator: Mapped[str] = mapped_column(String(10), nullable=False)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    acceptance_effect: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[ThresholdStatus] = mapped_column(enum_col(ThresholdStatus), nullable=False)
    basis: Mapped[str] = mapped_column(Text, nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)


class AcceptanceCorpusDefinition(Base):
    __tablename__ = "acceptance_corpus_definitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[AcceptanceCorpusStatus] = mapped_column(enum_col(AcceptanceCorpusStatus), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    sampling_rule: Mapped[str] = mapped_column(Text, nullable=False)
    minimum_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    required_case_types_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    adjudication_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)


class Tier1Decision(Base):
    __tablename__ = "tier1_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    decision_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    topic: Mapped[str] = mapped_column(String(120), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    options_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[Tier1DecisionStatus] = mapped_column(enum_col(Tier1DecisionStatus), nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    impact_if_unresolved: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[str | None] = mapped_column(Text)
    fallback: Mapped[str | None] = mapped_column(Text)


class Tier2BacklogItem(Base):
    __tablename__ = "tier2_backlog_items"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    category: Mapped[Tier2Category] = mapped_column(enum_col(Tier2Category), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    priority: Mapped[str] = mapped_column(String(30), nullable=False)
    due_build_week: Mapped[int] = mapped_column(Integer, nullable=False)
    blocking_week6: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[Tier2Status] = mapped_column(enum_col(Tier2Status), nullable=False)
    dependency: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    scenario_expansion_warning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class BusinessBaseline(Base):
    __tablename__ = "business_baselines"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    applications_per_month: Mapped[float] = mapped_column(Float, nullable=False)
    applications_per_year: Mapped[float] = mapped_column(Float, nullable=False)
    manual_entry_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    upload_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    status_check_minutes: Mapped[float] = mapped_column(Float, nullable=False)
    return_rate: Mapped[float] = mapped_column(Float, nullable=False)
    average_submission_cycles: Mapped[float] = mapped_column(Float, nullable=False)
    rework_hours_per_return: Mapped[float] = mapped_column(Float, nullable=False)
    delay_days_per_return: Mapped[float] = mapped_column(Float, nullable=False)
    loaded_hourly_rate_qar: Mapped[float] = mapped_column(Float, nullable=False)
    optional_delay_value_per_day: Mapped[float | None] = mapped_column(Float)
    standing_classification_impact_status: Mapped[str] = mapped_column(String(50), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    measurement_period: Mapped[str] = mapped_column(String(100), nullable=False)
    confidence: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)


class BusinessKpiTarget(Base):
    __tablename__ = "business_kpi_targets"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    baseline: Mapped[float | None] = mapped_column(Float)
    target: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    owner: Mapped[str] = mapped_column(String(200), nullable=False)
    measurement_method: Mapped[str] = mapped_column(Text, nullable=False)


class DeliveryScenario(Base):
    __tablename__ = "delivery_scenarios"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scenario_code: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    delivery_location_model: Mapped[str] = mapped_column(String(200), nullable=False)
    real_data_location: Mapped[str] = mapped_column(String(300), nullable=False)
    remote_raw_access: Mapped[str] = mapped_column(String(80), nullable=False)
    external_ai_route: Mapped[str] = mapped_column(String(200), nullable=False)
    test_environment: Mapped[str] = mapped_column(String(200), nullable=False)
    commercial_range_min_qar: Mapped[float | None] = mapped_column(Float)
    commercial_range_max_qar: Mapped[float | None] = mapped_column(Float)
    schedule_weeks: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[DeliveryStatus] = mapped_column(enum_col(DeliveryStatus), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False)


class MunicipalityOperationDecision(Base):
    __tablename__ = "municipality_operation_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    operation: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    selected_mode: Mapped[SelectedMode] = mapped_column(enum_col(SelectedMode), nullable=False)
    authorization_status: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    fallback: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    decision_owner: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class PrecheckDecision(Base):
    __tablename__ = "precheck_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    trigger_method: Mapped[str] = mapped_column(String(200), nullable=False)
    capture_method: Mapped[str] = mapped_column(String(200), nullable=False)
    machine_readable: Mapped[bool] = mapped_column(Boolean, nullable=False)
    required_before_final_review: Mapped[bool] = mapped_column(Boolean, nullable=False)
    correction_loop_supported: Mapped[bool] = mapped_column(Boolean, nullable=False)
    fallback: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)


class PilotCohort(Base):
    __tablename__ = "pilot_cohorts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    super_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    preparer_user_ids_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    process_champion_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    requirement_steward_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    responsible_engineer_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    final_submitter_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    status: Mapped[PilotStatus] = mapped_column(enum_col(PilotStatus), nullable=False)


class Phase0Decision(Base):
    __tablename__ = "phase0_decisions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    decision: Mapped[Phase0DecisionType] = mapped_column(enum_col(Phase0DecisionType), nullable=False)
    decision_date: Mapped[date] = mapped_column(Date, nullable=False)
    recommended_by: Mapped[str] = mapped_column(String(200), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    conditions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    blockers_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    fallbacks_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    evidence_refs_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    commercial_effect: Mapped[str] = mapped_column(Text, nullable=False)
    next_action: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class Stage2Baseline(Base):
    __tablename__ = "stage2_baselines"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    status: Mapped[Stage2Status] = mapped_column(enum_col(Stage2Status), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scenario_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    tier1_snapshot_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    threshold_snapshot_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    municipality_mode_snapshot_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    data_delivery_snapshot_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    security_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    pilot_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    acceptance_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    tier2_backlog_snapshot_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    business_kpi_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    decision_log_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)


class Stage2ReviewAcknowledgement(Base):
    __tablename__ = "stage2_review_acknowledgements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    baseline_id: Mapped[str] = mapped_column(ForeignKey("stage2_baselines.id"), nullable=False)
    reviewer_role: Mapped[str] = mapped_column(String(100), nullable=False)
    reviewer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    acknowledgement: Mapped[str] = mapped_column(String(40), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class SignoffCProposal(Base):
    __tablename__ = "signoff_c_proposals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    stage2_baseline_id: Mapped[str] = mapped_column(ForeignKey("stage2_baselines.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[SignoffStatus] = mapped_column(enum_col(SignoffStatus), nullable=False)
    scope_summary: Mapped[str] = mapped_column(Text, nullable=False)
    capability_depth_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    delivery_scenario: Mapped[str] = mapped_column(String(100), nullable=False)
    schedule_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    fixed_price_qar: Mapped[float | None] = mapped_column(Float)
    payment_plan_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    holdback_percent: Mapped[float] = mapped_column(Float, nullable=False)
    client_staffing_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    technical_thresholds_json: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    remediation_commitment: Mapped[str] = mapped_column(Text, nullable=False)
    g10_conditions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    hypercare_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    operational_observation_days: Mapped[int] = mapped_column(Integer, nullable=False)
    support_terms: Mapped[str] = mapped_column(Text, nullable=False)
    warranty_terms: Mapped[str] = mapped_column(Text, nullable=False)
    maintenance_terms: Mapped[str] = mapped_column(Text, nullable=False)
    ip_terms: Mapped[str] = mapped_column(Text, nullable=False)
    data_exit_terms: Mapped[str] = mapped_column(Text, nullable=False)
    exclusions_json: Mapped[list[str]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class DeliveryAuthorityStatus(Base):
    __tablename__ = "delivery_authority_statuses"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    track: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    basis_artifact: Mapped[str] = mapped_column(String(300), nullable=False)
    basis_version: Mapped[str | None] = mapped_column(String(80))
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    evidence_reference: Mapped[str | None] = mapped_column(String(500))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
