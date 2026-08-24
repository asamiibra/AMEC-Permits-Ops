"""Completion / As-Built canonical technical and handoff records.

The regulatory, requirement, form, preparation, submission, finding, party,
document, and authority-outcome truths remain in their existing shared tables.
These records only add the missing scoped technical state and immutable
cross-domain pins needed to carry Construction into Completion safely.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class BuildingAsset(Base):
    __tablename__ = "building_assets"
    __table_args__ = (
        UniqueConstraint("project_id", "asset_ref", name="uq_building_asset_ref"),
        Index("ix_building_asset_project_status", "project_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    property_id: Mapped[str | None] = mapped_column(ForeignKey("properties.id"), index=True)
    asset_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    name: Mapped[str] = mapped_column(String(240), nullable=False)
    building_type: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class BuildingSnapshot(Base):
    __tablename__ = "building_snapshots"
    __table_args__ = (
        UniqueConstraint("building_asset_id", "snapshot_type", "version_number", name="uq_building_snapshot_version"),
        Index("ix_building_snapshot_project_type", "project_id", "snapshot_type", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    building_asset_id: Mapped[str] = mapped_column(ForeignKey("building_assets.id"), nullable=False, index=True)
    snapshot_type: Mapped[str] = mapped_column(String(30), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    values_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    verified_assertion_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    source_document_version_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="IMMUTABLE")
    snapshot_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("building_snapshots.id"))
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ConstructionCompletionContext(Base):
    __tablename__ = "construction_completion_contexts"
    __table_args__ = (UniqueConstraint("construction_execution_id", name="uq_completion_context_execution"), Index("ix_completion_context_project", "project_id", "status"))

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    authority_approved_design_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("authority_approved_design_snapshots.id"), index=True)
    construction_design_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("construction_design_snapshots.id"), index=True)
    work_state: Mapped[str] = mapped_column(String(40), nullable=False)
    open_issue_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    open_obligation_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    inspection_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    material_test_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    physical_evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    party_snapshot: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    source_snapshot_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="CURRENT")
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class CompletionCaseLink(Base):
    __tablename__ = "completion_case_links"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_completion_case_link_idempotency"),
        UniqueConstraint("authority_case_id", name="uq_completion_case_link_case"),
        Index("ix_completion_case_link_project", "project_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    construction_completion_context_id: Mapped[str] = mapped_column(ForeignKey("construction_completion_contexts.id"), nullable=False, index=True)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False, index=True)
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="IN_PROGRESS")
    started_by: Mapped[str] = mapped_column(String(200), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AsBuiltBaseline(Base):
    __tablename__ = "as_built_baselines"
    __table_args__ = (
        UniqueConstraint("project_id", "construction_execution_id", "baseline_ref", name="uq_as_built_baseline_ref"),
        UniqueConstraint("project_id", "construction_execution_id", "version_number", name="uq_as_built_baseline_version"),
        Index("ix_as_built_baseline_scope", "project_id", "construction_execution_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    construction_execution_id: Mapped[str] = mapped_column(ForeignKey("construction_executions.id"), nullable=False, index=True)
    authority_case_id: Mapped[str | None] = mapped_column(ForeignKey("authority_cases.id"), index=True)
    source_construction_design_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("construction_design_snapshots.id"), index=True)
    baseline_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    scope_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(200))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_baseline_id: Mapped[str | None] = mapped_column(ForeignKey("as_built_baselines.id"), index=True)
    immutable_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AsBuiltBaselineMember(Base):
    __tablename__ = "as_built_baseline_members"
    __table_args__ = (
        Index("uq_as_built_baseline_member", "baseline_id", "engineering_revision_id", "rendition_id", "building_snapshot_id", unique=True, mssql_where=text("engineering_revision_id IS NOT NULL AND rendition_id IS NOT NULL AND building_snapshot_id IS NOT NULL")),
        Index("ix_as_built_baseline_member_baseline", "baseline_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    baseline_id: Mapped[str] = mapped_column(ForeignKey("as_built_baselines.id", ondelete="CASCADE"), nullable=False)
    engineering_revision_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"), index=True)
    rendition_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_renditions.id"), index=True)
    document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    building_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("building_snapshots.id"), index=True)
    member_role: Mapped[str] = mapped_column(String(80), nullable=False, default="AS_BUILT_ENGINEERING")
    pinned_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AsBuiltComparisonRun(Base):
    __tablename__ = "as_built_comparison_runs"
    __table_args__ = (
        UniqueConstraint("baseline_id", "reference_fingerprint", "rule_version", name="uq_as_built_comparison_run"),
        Index("ix_as_built_comparison_project", "project_id", "result"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    baseline_id: Mapped[str] = mapped_column(ForeignKey("as_built_baselines.id"), nullable=False, index=True)
    construction_design_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("construction_design_snapshots.id"), index=True)
    authority_approved_building_snapshot_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    as_built_building_snapshot_ids: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    reference_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_version: Mapped[str] = mapped_column(String(40), nullable=False)
    result: Mapped[str] = mapped_column(String(30), nullable=False, default="MATCH")
    difference_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AsBuiltVariance(Base):
    __tablename__ = "as_built_variances"
    __table_args__ = (
        Index("uq_as_built_variance_field", "comparison_run_id", "building_asset_id", "field_key", unique=True, mssql_where=text("building_asset_id IS NOT NULL")),
        Index("ix_as_built_variance_project_status", "project_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    comparison_run_id: Mapped[str] = mapped_column(ForeignKey("as_built_comparison_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    building_asset_id: Mapped[str | None] = mapped_column(ForeignKey("building_assets.id"), index=True)
    engineering_revision_id: Mapped[str | None] = mapped_column(ForeignKey("engineering_deliverable_revisions.id"), index=True)
    field_key: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="STRUCTURED_FIELD")
    approved_value_json: Mapped[Any] = mapped_column(JSON, nullable=True)
    as_built_value_json: Mapped[Any] = mapped_column(JSON, nullable=True)
    delta_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="OPEN")
    professional_disposition: Mapped[str | None] = mapped_column(String(60))
    requires_design_change: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_authority_modification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    design_change_request_id: Mapped[str | None] = mapped_column(ForeignKey("design_change_requests.id"), index=True)
    disposition_reason: Mapped[str | None] = mapped_column(Text)
    dispositioned_by: Mapped[str | None] = mapped_column(String(200))
    dispositioned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
