"""Owner Administration Contract workspace records.

These tables are projections and immutable snapshots around the existing
Contract, ProposalAcceptedRevision, Project, and Dashboard master-content
records.  They do not create a second Client, Project, Proposal, or template
repository.
"""

from datetime import date, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class ContractReferenceSequence(Base):
    __tablename__ = "contract_reference_sequences"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    sequence_key: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    next_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)


class ContractTemplateSnapshot(Base):
    __tablename__ = "contract_template_snapshots"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False, index=True)
    master_content_id: Mapped[str] = mapped_column(ForeignKey("master_content_items.id"), nullable=False)
    master_content_ref: Mapped[str] = mapped_column(String(100), nullable=False)
    document_version_id: Mapped[str] = mapped_column(ForeignKey("document_versions.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    captured_by: Mapped[str] = mapped_column(String(200), nullable=False)


class ContractAdminInput(Base):
    __tablename__ = "contract_admin_inputs"
    __table_args__ = (UniqueConstraint("contract_id", "input_key", name="uq_contract_admin_input_key"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    input_key: Mapped[str] = mapped_column(String(120), nullable=False)
    value_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    entered_by: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ContractAdminEvidence(Base):
    __tablename__ = "contract_admin_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str | None] = mapped_column(ForeignKey("contract_revisions.id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(100), nullable=False)
    source_role: Mapped[str] = mapped_column(String(80), default="GENERAL", nullable=False)
    document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    source_reference: Mapped[str] = mapped_column(String(600), nullable=False)
    content_hash: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(40), default="RECORDED", nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(200), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)


class ProjectActivation(Base):
    __tablename__ = "project_activations"
    __table_args__ = (UniqueConstraint("contract_id", name="uq_project_activation_contract"), UniqueConstraint("project_id", name="uq_project_activation_project"), UniqueConstraint("idempotency_key", name="uq_project_activation_idempotency"))
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False)
    accepted_proposal_revision_id: Mapped[str | None] = mapped_column(ForeignKey("proposal_accepted_revisions.id"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    project_code: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    original_start_date: Mapped[date] = mapped_column(Date, nullable=False)
    activated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    activated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="ACTIVE", nullable=False)
    audit_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
