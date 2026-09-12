"""Shared ProposalOps Intelligence v1 persistence contracts.

These records carry typed metadata and candidate/output envelopes.  They do
not grant authority, promote assertions, or contain source bytes/prompts.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class CandidateAssertion(Base):
    __tablename__ = "candidate_assertions"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_candidate_assertion_idempotency"),
        Index("ix_candidate_assertion_scope", "scope_type", "scope_id"),
        Index("ix_candidate_assertion_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(160), nullable=False)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    target_module: Mapped[str | None] = mapped_column(String(120))
    subject_type: Mapped[str] = mapped_column(String(50), nullable=False)
    subject_id: Mapped[str] = mapped_column(String(160), nullable=False)
    assertion_code: Mapped[str] = mapped_column(String(160), nullable=False)
    field_definition_id: Mapped[str | None] = mapped_column(ForeignKey("field_definitions.id"))
    value_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    display_value: Mapped[str | None] = mapped_column(Text)
    value_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    producer_kind: Mapped[str] = mapped_column(String(80), nullable=False)
    producer_version: Mapped[str] = mapped_column(String(80), nullable=False)
    producer_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_document_version_id: Mapped[str | None] = mapped_column(ForeignKey("document_versions.id"))
    source_observation_id: Mapped[str | None] = mapped_column(ForeignKey("field_observations.id"))
    evidence_envelope_id: Mapped[str | None] = mapped_column(String(160))
    data_classification: Mapped[str] = mapped_column(String(50), nullable=False)
    contains_sensitive_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CURRENT")
    promoted_verified_assertion_id: Mapped[str | None] = mapped_column(ForeignKey("verified_assertions.id"))
    supersedes_candidate_assertion_id: Mapped[str | None] = mapped_column(ForeignKey("candidate_assertions.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ContextSnapshot(Base):
    __tablename__ = "context_snapshots"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_context_snapshot_idempotency"),
        Index("ix_context_snapshot_scope", "scope_type", "scope_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    owning_module: Mapped[str] = mapped_column(String(120), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(160), nullable=False)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(String(36))
    actor_persona: Mapped[str] = mapped_column(String(120), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(160), nullable=False)
    skill_version: Mapped[str] = mapped_column(String(80), nullable=False)
    skill_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    context_schema_version: Mapped[str] = mapped_column(String(80), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    authorization_context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    context_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    dependency_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    synthetic_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class ContextDependency(Base):
    __tablename__ = "context_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "context_snapshot_id", "dependency_type", "dependency_id", "dependency_version_or_hash",
            name="uq_context_dependency_identity",
        ),
        Index("ix_context_dependency_type_id", "dependency_type", "dependency_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    context_snapshot_id: Mapped[str] = mapped_column(ForeignKey("context_snapshots.id"), nullable=False, index=True)
    dependency_type: Mapped[str] = mapped_column(String(80), nullable=False)
    dependency_id: Mapped[str] = mapped_column(String(200), nullable=False)
    dependency_version_or_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    trust_state: Mapped[str] = mapped_column(String(50), nullable=False)
    currentness_state_at_capture: Mapped[str] = mapped_column(String(50), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class AIWorkProduct(Base):
    __tablename__ = "ai_work_products"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_ai_work_product_idempotency"),
        Index("ix_ai_work_product_scope", "scope_type", "scope_id"),
        Index("ix_ai_work_product_state", "state"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    execution_ledger_id: Mapped[str] = mapped_column(ForeignKey("ai_execution_ledger.id"), nullable=False)
    context_snapshot_id: Mapped[str] = mapped_column(ForeignKey("context_snapshots.id"), nullable=False)
    owning_module: Mapped[str] = mapped_column(String(120), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(160), nullable=False)
    skill_version: Mapped[str] = mapped_column(String(80), nullable=False)
    skill_manifest_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False)
    scope_id: Mapped[str] = mapped_column(String(160), nullable=False)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"), index=True)
    target_entity_type: Mapped[str] = mapped_column(String(80), nullable=False)
    target_entity_id: Mapped[str] = mapped_column(String(160), nullable=False)
    output_class: Mapped[str] = mapped_column(String(30), nullable=False)
    structured_output_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    output_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    data_classification: Mapped[str] = mapped_column(String(50), nullable=False)
    contains_sensitive_data: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="CURRENT")
    citation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    stale_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    stale_reason: Mapped[str | None] = mapped_column(Text)


class IntelligenceCitation(Base):
    __tablename__ = "intelligence_citations"
    __table_args__ = (
        UniqueConstraint("work_product_id", "ordinal", name="uq_intelligence_citation_ordinal"),
        Index("ix_intelligence_citation_source", "source_type", "source_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    work_product_id: Mapped[str] = mapped_column(ForeignKey("ai_work_products.id"), nullable=False, index=True)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(String(80), nullable=False)
    source_id: Mapped[str] = mapped_column(String(200), nullable=False)
    source_version_or_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    locator_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    citation_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
