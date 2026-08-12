"""BD Proposal owner-session records.

These tables extend the existing Opportunity/Proposal model with transactional
evidence and immutable acceptance lineage.  They deliberately do not copy
Dashboard master-content bytes.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, utcnow


def _id() -> str:
    return str(uuid4())


class ProposalSourceEvidence(Base, TimestampMixin):
    __tablename__ = "proposal_source_evidence"
    __table_args__ = (UniqueConstraint("proposal_id", "source_type", "content_hash", name="uq_proposal_source_hash"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    source_filename: Mapped[str] = mapped_column(String(300), nullable=False)
    source_reference: Mapped[str] = mapped_column(String(600), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    source_revision: Mapped[str | None] = mapped_column(String(80))
    provenance: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    conflict_key: Mapped[str | None] = mapped_column(String(120), index=True)
    status: Mapped[str] = mapped_column(String(40), default="CURRENT", nullable=False)
    verification_state: Mapped[str] = mapped_column(String(40), default="READ_BACK_VERIFIED", nullable=False)
    supersedes_id: Mapped[str | None] = mapped_column(String(36))
    created_by: Mapped[str] = mapped_column(String(200), nullable=False)


class ProposalAcceptedRevision(Base):
    __tablename__ = "proposal_accepted_revisions"
    __table_args__ = (UniqueConstraint("proposal_id", "revision_number", name="uq_proposal_accepted_revision"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    revision_number: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    validation_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    template_ref: Mapped[str | None] = mapped_column(String(100))
    template_version_id: Mapped[str | None] = mapped_column(String(36))
    template_version: Mapped[str | None] = mapped_column(String(40))
    template_hash: Mapped[str | None] = mapped_column(String(64))
    checklist_ref: Mapped[str | None] = mapped_column(String(100))
    checklist_version_id: Mapped[str | None] = mapped_column(String(36))
    checklist_version: Mapped[str | None] = mapped_column(String(40))
    checklist_hash: Mapped[str | None] = mapped_column(String(64))
    definition_refs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    accepted_by: Mapped[str] = mapped_column(String(200), nullable=False)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="ACCEPTED", nullable=False)
    supersedes_revision_id: Mapped[str | None] = mapped_column(String(36))


class ProposalOutputArtifact(Base):
    __tablename__ = "proposal_output_artifacts"
    __table_args__ = (UniqueConstraint("revision_id", "artifact_type", name="uq_proposal_output_type"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    revision_id: Mapped[str] = mapped_column(ForeignKey("proposal_accepted_revisions.id"), nullable=False, index=True)
    proposal_id: Mapped[str] = mapped_column(ForeignKey("opportunities.id"), nullable=False, index=True)
    artifact_type: Mapped[str] = mapped_column(String(40), nullable=False)
    filename: Mapped[str] = mapped_column(String(300), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    storage_reference: Mapped[str] = mapped_column(String(600), nullable=False)
    lineage: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    synthetic_only: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class ProposalOwnerSetting(Base, TimestampMixin):
    __tablename__ = "proposal_owner_settings"
    __table_args__ = (UniqueConstraint("setting_key", name="uq_proposal_owner_setting_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    setting_key: Mapped[str] = mapped_column(String(120), nullable=False)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="SAFE_DEFAULT", nullable=False)
    updated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
