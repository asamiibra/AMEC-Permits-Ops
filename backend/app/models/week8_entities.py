"""Week 8 relational lineage, material-change, validity, and shadow evidence."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class StalenessStatus:
    CURRENT = "CURRENT"
    STALE = "STALE"
    NEEDS_REVALIDATION = "NEEDS_REVALIDATION"
    SUPERSEDED = "SUPERSEDED"


class DocumentValidityStatus:
    VALID = "VALID"
    NOT_YET_EFFECTIVE = "NOT_YET_EFFECTIVE"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"
    SUPERSEDED = "SUPERSEDED"
    UNKNOWN_REVIEW_REQUIRED = "UNKNOWN_REVIEW_REQUIRED"


class MaterialChangeStatus:
    DETECTED = "DETECTED"
    NO_MATERIAL_CHANGE = "NO_MATERIAL_CHANGE"
    APPLIED = "APPLIED"


class ConfigurationArtifact(Base):
    __tablename__ = "configuration_artifacts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    stable_id: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(100), nullable=False)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    source_basis: Mapped[str] = mapped_column(String(300), nullable=False)
    semantic_payload_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ConfigurationBundle(Base):
    __tablename__ = "configuration_bundles"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    bundle_id: Mapped[str] = mapped_column(String(160), unique=True, nullable=False)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenario_configs.id"))
    bundle_version: Mapped[str] = mapped_column(String(80), nullable=False)
    artifact_ids_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    effective_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    source_basis: Mapped[str] = mapped_column(String(300), nullable=False)


class LineageEdge(Base):
    __tablename__ = "lineage_edges"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    upstream_type: Mapped[str] = mapped_column(String(100), nullable=False)
    upstream_id: Mapped[str] = mapped_column(String(160), nullable=False)
    upstream_version_or_hash: Mapped[str | None] = mapped_column(String(160))
    downstream_type: Mapped[str] = mapped_column(String(100), nullable=False)
    downstream_id: Mapped[str] = mapped_column(String(160), nullable=False)
    downstream_version_or_hash: Mapped[str | None] = mapped_column(String(160))
    dependency_kind: Mapped[str] = mapped_column(String(60), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)


class MaterialChangeEvent(Base):
    __tablename__ = "material_change_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_id: Mapped[str] = mapped_column(String(160), nullable=False)
    previous_version_or_hash: Mapped[str | None] = mapped_column(String(160))
    new_version_or_hash: Mapped[str | None] = mapped_column(String(160))
    change_type: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    actor_or_system: Mapped[str] = mapped_column(String(200), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    material: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class StaleReason(Base):
    __tablename__ = "stale_reasons"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(100), nullable=False)
    target_id: Mapped[str] = mapped_column(String(160), nullable=False)
    material_change_event_id: Mapped[str] = mapped_column(ForeignKey("material_change_events.id"), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(100), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cleared_by: Mapped[str | None] = mapped_column(String(200))
    replacement_target_id: Mapped[str | None] = mapped_column(String(160))


class DocumentValidity(Base):
    __tablename__ = "document_validities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), unique=True, nullable=False)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    superseded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    validity_status: Mapped[str] = mapped_column(String(50), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    rule_version: Mapped[str] = mapped_column(String(40), nullable=False)


class AuthorityApprovalValidity(Base):
    __tablename__ = "authority_approval_validities"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    approval_dependency_id: Mapped[str] = mapped_column(ForeignKey("approval_dependencies.id"), unique=True, nullable=False)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))


class ConfigurationChangeImpactPolicy(Base):
    __tablename__ = "configuration_change_impact_policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    config_type: Mapped[str] = mapped_column(String(80), nullable=False)
    change_severity: Mapped[str] = mapped_column(String(30), nullable=False)
    active_revision_policy: Mapped[str] = mapped_column(String(60), nullable=False)
    requires_re_evaluation: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    requires_new_revision: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    effective_from: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class CorpusRun(Base):
    __tablename__ = "corpus_runs"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    fixture_set: Mapped[str] = mapped_column(String(160), nullable=False)
    fixture_version: Mapped[str] = mapped_column(String(40), nullable=False)
    corpus_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class CorpusCase(Base):
    __tablename__ = "corpus_cases"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    corpus_run_id: Mapped[str] = mapped_column(ForeignKey("corpus_runs.id"), nullable=False)
    case_key: Mapped[str] = mapped_column(String(160), nullable=False)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    expected_class: Mapped[str | None] = mapped_column(String(100))
    expected_fields: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class CorpusCaseResult(Base):
    __tablename__ = "corpus_case_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    corpus_run_id: Mapped[str] = mapped_column(ForeignKey("corpus_runs.id"), nullable=False)
    corpus_case_id: Mapped[str] = mapped_column(ForeignKey("corpus_cases.id"), nullable=False)
    document_classification_agreement: Mapped[bool] = mapped_column(Boolean, nullable=False)
    critical_candidate_agreement: Mapped[bool] = mapped_column(Boolean, nullable=False)
    verified_final_agreement: Mapped[bool] = mapped_column(Boolean, nullable=False)
    false_accept: Mapped[bool] = mapped_column(Boolean, nullable=False)
    degraded_keyed_entry: Mapped[bool] = mapped_column(Boolean, nullable=False)
    human_correction: Mapped[bool] = mapped_column(Boolean, nullable=False)
    evidence_quality: Mapped[str] = mapped_column(String(40), nullable=False)
    timing_seconds: Mapped[float | None] = mapped_column(Integer)


class ShadowCorrection(Base):
    __tablename__ = "shadow_corrections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    application_id: Mapped[str | None] = mapped_column(ForeignKey("permit_applications.id"))
    preparation_revision_id: Mapped[str | None] = mapped_column(ForeignKey("preparation_revisions.id"))
    entity_type: Mapped[str] = mapped_column(String(100), nullable=False)
    field_or_category: Mapped[str] = mapped_column(String(160), nullable=False)
    proposed_value: Mapped[Any] = mapped_column(JSON)
    approved_human_value: Mapped[Any] = mapped_column(JSON)
    correction_type: Mapped[str] = mapped_column(String(80), nullable=False)
    root_cause_category: Mapped[str] = mapped_column(String(80), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evidence_artifact_id: Mapped[str | None] = mapped_column(String(300))
