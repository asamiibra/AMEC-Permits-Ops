"""Revision-scoped Contract commercial and billing-readiness records.

These records describe Contract commitments only.  They are deliberately not
Invoice, Payment, or BillingMilestone records; downstream billing remains a
separate workstream.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class ContractPaymentTerm(Base):
    __tablename__ = "contract_payment_terms"
    __table_args__ = (UniqueConstraint("contract_revision_id", "sequence", name="uq_contract_payment_term_revision_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str] = mapped_column(String(160), nullable=False)
    term_text: Mapped[str] = mapped_column(Text, nullable=False)
    basis_type: Mapped[str | None] = mapped_column(String(60))
    percentage: Mapped[float | None] = mapped_column(Numeric(12, 6))
    fixed_amount: Mapped[float | None] = mapped_column(Numeric(18, 2))
    currency: Mapped[str | None] = mapped_column(String(20))
    trigger_type: Mapped[str | None] = mapped_column(String(80))
    trigger_description: Mapped[str | None] = mapped_column(Text)
    due_days: Mapped[int | None] = mapped_column(Integer)
    source_clause: Mapped[str | None] = mapped_column(String(200))
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="NEEDS_REVIEW", nullable=False)
    candidate_source: Mapped[str] = mapped_column(String(40), default="HUMAN_ENTERED", nullable=False)
    human_verified_by: Mapped[str | None] = mapped_column(String(200))
    human_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ContractDeliverableCommitment(Base):
    __tablename__ = "contract_deliverable_commitments"
    __table_args__ = (UniqueConstraint("contract_revision_id", "sequence", name="uq_contract_deliverable_revision_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    commitment_ref: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    due_trigger_description: Mapped[str | None] = mapped_column(Text)
    source_scope_item_id: Mapped[str | None] = mapped_column(String(36), index=True)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="COMMITTED", nullable=False)
    human_verified_by: Mapped[str | None] = mapped_column(String(200))
    human_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class ContractClientInputRequirement(Base):
    __tablename__ = "contract_client_input_requirements"
    __table_args__ = (UniqueConstraint("contract_revision_id", "sequence", name="uq_contract_client_input_revision_sequence"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    contract_id: Mapped[str] = mapped_column(ForeignKey("contracts.id"), nullable=False, index=True)
    contract_revision_id: Mapped[str] = mapped_column(ForeignKey("contract_revisions.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    input_code: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(40), default="OPEN", nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(80))
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"), index=True)
    human_verified_by: Mapped[str | None] = mapped_column(String(200))
    human_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
