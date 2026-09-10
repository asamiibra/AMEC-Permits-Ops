"""Durable Source18 state owned by the canonical Authority/Administration domain."""

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, utcnow


def _id() -> str:
    return str(uuid4())


class RegulatoryStateVersion(Base, TimestampMixin):
    """Accepted/pending regulatory facts with immutable supersession lineage."""

    __tablename__ = "regulatory_state_versions"
    __table_args__ = (
        Index("ix_regulatory_state_subject", "subject_type", "subject_id", "state_type"),
        Index("ix_regulatory_state_case", "authority_case_id", "state_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str | None] = mapped_column(ForeignKey("authority_cases.id"), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    subject_type: Mapped[str] = mapped_column(String(80), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    state_type: Mapped[str] = mapped_column(String(100), nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING")
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    source_reference: Mapped[str | None] = mapped_column(String(500))
    state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    supersedes_id: Mapped[str | None] = mapped_column(String(36), index=True)
    accepted_by: Mapped[str | None] = mapped_column(String(200))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    synthetic_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class CommitteePacketRevision(Base, TimestampMixin):
    """Immutable packet revisions; release, signed return and submission stay separate."""

    __tablename__ = "committee_packet_revisions"
    __table_args__ = (UniqueConstraint("authority_case_id", "revision_number", name="uq_committee_packet_revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    supersedes_id: Mapped[str | None] = mapped_column(ForeignKey("committee_packet_revisions.id"), index=True)
    official_form_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    form_binding_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    field_values_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    authority_only_fields_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    validation_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    owner_release_by: Mapped[str | None] = mapped_column(String(200))
    owner_release_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    signed_return_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    signed_return_verified_by: Mapped[str | None] = mapped_column(String(200))
    signed_return_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    submission_cycle_id: Mapped[str | None] = mapped_column(ForeignKey("authority_submission_cycles.id"), index=True)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class PhysicalOriginalCustodyEvent(Base):
    """Evidence-backed custody history; a checkbox cannot create custody."""

    __tablename__ = "physical_original_custody_events"
    __table_args__ = (Index("ix_physical_original_case_document", "authority_case_id", "document_version_id", "event_at"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    authority_case_id: Mapped[str] = mapped_column(ForeignKey("authority_cases.id"), nullable=False, index=True)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    custodian: Mapped[str] = mapped_column(String(200), nullable=False)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    evidence_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    evidence_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
