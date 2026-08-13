"""Wave A governance records attached to canonical master content.

These tables deliberately complement, rather than replace, the existing
MasterContentItem -> Document -> DocumentVersion lineage.
"""

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, utcnow


def _id() -> str:
    return str(uuid4())


class MasterContentGovernanceProfile(Base, TimestampMixin):
    __tablename__ = "master_content_governance_profiles"
    __table_args__ = (UniqueConstraint("master_content_item_id", name="uq_master_content_governance_item"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    master_content_item_id: Mapped[str] = mapped_column(ForeignKey("master_content_items.id"), nullable=False, index=True)
    content_ownership_class: Mapped[str] = mapped_column(String(40), nullable=False, default="NEEDS_REVIEW", index=True)
    artifact_kind: Mapped[str] = mapped_column(String(60), nullable=False, default="UNKNOWN", index=True)
    publisher_name: Mapped[str | None] = mapped_column(String(240))
    publisher_unit: Mapped[str | None] = mapped_column(String(240))
    jurisdiction_text: Mapped[str | None] = mapped_column(String(240))
    official_form_no: Mapped[str | None] = mapped_column(String(120), index=True)
    official_issue_no: Mapped[str | None] = mapped_column(String(80))
    official_issue_date: Mapped[date | None] = mapped_column(Date)
    language_profile: Mapped[str] = mapped_column(String(30), nullable=False, default="OTHER")
    sensitivity_class: Mapped[str] = mapped_column(String(40), nullable=False, default="NONE")
    contains_pii: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_signature: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_stamp: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_financial_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    contains_project_specific_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    restricted_reference_sample: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    currentness_status: Mapped[str] = mapped_column(String(40), nullable=False, default="UNVERIFIED", index=True)
    currentness_verified_by: Mapped[str | None] = mapped_column(String(200))
    currentness_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    currentness_verification_note: Mapped[str | None] = mapped_column(Text)


class MasterContentSourceProvenance(Base):
    __tablename__ = "master_content_source_provenance"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    obtained_from: Mapped[str] = mapped_column(String(240), nullable=False)
    obtained_by: Mapped[str] = mapped_column(String(200), nullable=False)
    obtained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    source_reference: Mapped[str | None] = mapped_column(String(500))
    ingest_batch: Mapped[str | None] = mapped_column(String(160))
    provenance_note: Mapped[str | None] = mapped_column(Text)
    evidence_reference: Mapped[str | None] = mapped_column(String(500))


class MasterContentQualityFlag(Base):
    __tablename__ = "master_content_quality_flags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    master_content_item_id: Mapped[str] = mapped_column(ForeignKey("master_content_items.id"), nullable=False, index=True)
    document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    code: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(20), nullable=False, default="WARNING", index=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN", index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_note: Mapped[str | None] = mapped_column(Text)
    recommended_next_action: Mapped[str | None] = mapped_column(Text)
    raised_by: Mapped[str] = mapped_column(String(200), nullable=False)
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    resolved_by: Mapped[str | None] = mapped_column(String(200))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    resolution: Mapped[str | None] = mapped_column(Text)


class MasterContentSourceSection(Base):
    __tablename__ = "master_content_source_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    master_content_item_id: Mapped[str] = mapped_column(ForeignKey("master_content_items.id"), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    section_key: Mapped[str] = mapped_column(String(120), nullable=False)
    label: Mapped[str] = mapped_column(String(240), nullable=False)
    locator_type: Mapped[str] = mapped_column(String(40), nullable=False, default="PAGE_RANGE")
    page_start: Mapped[int | None] = mapped_column()
    page_end: Mapped[int | None] = mapped_column()
    locator_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE", index=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class MasterContentReadinessAssessment(Base):
    __tablename__ = "master_content_readiness_assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    master_content_item_id: Mapped[str] = mapped_column(ForeignKey("master_content_items.id"), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    evaluator_version: Mapped[str] = mapped_column(String(30), nullable=False, default="WAVE_A_1")
    state: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    blocking_reasons: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    warnings: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    dimensions: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
