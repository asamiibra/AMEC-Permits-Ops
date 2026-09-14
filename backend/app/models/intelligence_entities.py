"""Shared ProposalOps Intelligence v1 persistence contracts.

These records carry typed metadata and candidate/output envelopes.  They do
not grant authority, promote assertions, or contain source bytes/prompts.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, text
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
        Index(
            "uq_candidate_assertion_current_family",
            "candidate_family_key",
            unique=True,
            mssql_where=text("candidate_family_key IS NOT NULL AND status = 'CURRENT'"),
            sqlite_where=text("status = 'CURRENT'"),
            postgresql_where=text("status = 'CURRENT'"),
        ),
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
    candidate_family_key: Mapped[str | None] = mapped_column(String(300), index=True)
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
    policy_id: Mapped[str | None] = mapped_column(String(160), index=True)
    policy_hash: Mapped[str | None] = mapped_column(String(64))
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
    lineage_hash: Mapped[str | None] = mapped_column(String(64), index=True)
    invalidation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


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


class AIWorkProductDependency(Base):
    """Immutable causal edge from a durable work product to one exact dependency."""

    __tablename__ = "ai_work_product_dependencies"
    __table_args__ = (
        UniqueConstraint(
            "work_product_id", "dependency_type", "dependency_id", "dependency_version_or_hash",
            name="uq_ai_work_product_dependency_identity",
        ),
        Index("ix_ai_work_product_dependency_lookup", "dependency_type", "dependency_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    work_product_id: Mapped[str] = mapped_column(ForeignKey("ai_work_products.id"), nullable=False, index=True)
    dependency_type: Mapped[str] = mapped_column(String(80), nullable=False)
    dependency_id: Mapped[str] = mapped_column(String(200), nullable=False)
    dependency_version_or_hash: Mapped[str] = mapped_column(String(200), nullable=False)
    dependency_metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class IntelligenceInvalidation(Base):
    """Append-only causal invalidation record; never overwrites prior output."""

    __tablename__ = "intelligence_invalidations"
    __table_args__ = (
        UniqueConstraint("work_product_id", "source_event_id", name="uq_intelligence_invalidation_event"),
        Index("ix_intelligence_invalidation_dependency", "dependency_type", "dependency_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    work_product_id: Mapped[str] = mapped_column(ForeignKey("ai_work_products.id"), nullable=False, index=True)
    prior_state: Mapped[str] = mapped_column(String(20), nullable=False)
    resulting_state: Mapped[str] = mapped_column(String(20), nullable=False)
    dependency_type: Mapped[str] = mapped_column(String(80), nullable=False)
    dependency_id: Mapped[str] = mapped_column(String(200), nullable=False)
    prior_dependency_version_or_hash: Mapped[str | None] = mapped_column(String(200))
    superseding_dependency_version_or_hash: Mapped[str | None] = mapped_column(String(200))
    source_event_id: Mapped[str] = mapped_column(String(200), nullable=False)
    reason_code: Mapped[str] = mapped_column(String(120), nullable=False)
    invalidated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)


class IntelligencePolicy(Base):
    """Server-owned immutable policy/ruleset identity."""

    __tablename__ = "intelligence_policies"
    __table_args__ = (UniqueConstraint("policy_code", "version", name="uq_intelligence_policy_identity"),)

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    policy_code: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    declared_scope: Mapped[str] = mapped_column(String(120), nullable=False, default="SHARED_INTELLIGENCE")
    policy_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class IntelligenceEvalPack(Base):
    """Small server-owned evaluation-pack registry for future module packs."""

    __tablename__ = "intelligence_eval_packs"
    __table_args__ = (UniqueConstraint("eval_pack_id", "version", name="uq_intelligence_eval_pack_identity"),)

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    eval_pack_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    owning_module: Mapped[str] = mapped_column(String(120), nullable=False)
    critical_case_policy: Mapped[str] = mapped_column(String(120), nullable=False)
    acceptance_threshold_policy: Mapped[str] = mapped_column(String(200), nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class IntelligenceReviewDecision(Base):
    """Shared immutable ledger primitive; it owns no queue or module lifecycle."""

    __tablename__ = "intelligence_review_decisions"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_intelligence_review_decision_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    owning_module: Mapped[str] = mapped_column(String(120), nullable=False)
    review_subject_type: Mapped[str] = mapped_column(String(80), nullable=False)
    review_subject_id: Mapped[str] = mapped_column(String(160), nullable=False)
    candidate_assertion_id: Mapped[str | None] = mapped_column(ForeignKey("candidate_assertions.id"))
    work_product_id: Mapped[str | None] = mapped_column(ForeignKey("ai_work_products.id"))
    source_currentness_identity: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    context_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("context_snapshots.id"))
    reviewer_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    reviewer_persona: Mapped[str] = mapped_column(String(120), nullable=False)
    authorizing_capability: Mapped[str] = mapped_column(String(160), nullable=False)
    decision: Mapped[str] = mapped_column(String(30), nullable=False)
    correction_payload: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    reason: Mapped[str | None] = mapped_column(Text)
    precondition_version: Mapped[str] = mapped_column(String(200), nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    decision_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class IntelligenceToolDefinition(Base):
    """Server-owned read-only tool contract; no model-selected execution."""

    __tablename__ = "intelligence_tool_definitions"
    __table_args__ = (UniqueConstraint("tool_id", "version", name="uq_intelligence_tool_identity"),)

    id: Mapped[str] = mapped_column(String(160), primary_key=True)
    tool_id: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(80), nullable=False)
    immutable_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    input_schema_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    output_schema_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    allowed_modules: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    allowed_skills: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    required_capability: Mapped[str | None] = mapped_column(String(160))
    data_classification_ceiling: Mapped[str] = mapped_column(String(50), nullable=False, default="INTERNAL")
    timeout_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    budget_units: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    read_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)


class IntelligenceToolInvocation(Base):
    __tablename__ = "intelligence_tool_invocations"
    __table_args__ = (UniqueConstraint("idempotency_key", name="uq_intelligence_tool_invocation_idempotency"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    idempotency_key: Mapped[str] = mapped_column(String(200), nullable=False)
    tool_id: Mapped[str] = mapped_column(String(120), nullable=False)
    tool_version: Mapped[str] = mapped_column(String(80), nullable=False)
    tool_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    owning_module: Mapped[str] = mapped_column(String(120), nullable=False)
    skill_id: Mapped[str] = mapped_column(String(160), nullable=False)
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False)
    context_snapshot_id: Mapped[str | None] = mapped_column(ForeignKey("context_snapshots.id"))
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    outcome: Mapped[str] = mapped_column(String(40), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(120))
    output_hash: Mapped[str | None] = mapped_column(String(64))
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
