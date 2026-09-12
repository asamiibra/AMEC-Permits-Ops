"""Operational AI execution metadata.

This table deliberately contains no prompt, source text, model output, token,
or person-identifying content.  It is an execution ledger, not business truth.
"""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, Index, Integer, JSON, Numeric, String, Boolean, event
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


class AIExecutionLedger(Base):
    __tablename__ = "ai_execution_ledger"
    __table_args__ = (
        Index("ix_ai_ledger_actor_started", "actor_user_id", "started_at"),
        Index("ix_ai_ledger_project_started", "project_id", "started_at"),
        Index("ix_ai_ledger_scope_started", "scope_type", "scope_id", "started_at"),
        Index("ix_ai_ledger_status_started", "status", "started_at"),
        Index("ix_ai_ledger_started", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    idempotency_key: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_user_id: Mapped[str | None] = mapped_column(String(36))
    auth_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    purpose: Mapped[str] = mapped_column(String(100), nullable=False)
    execution_mode: Mapped[str] = mapped_column(String(30), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    scope_id: Mapped[str] = mapped_column(String(160), nullable=False, index=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    owning_module: Mapped[str | None] = mapped_column(String(120))
    skill_id: Mapped[str | None] = mapped_column(String(160))
    skill_version: Mapped[str | None] = mapped_column(String(80))
    skill_manifest_hash: Mapped[str | None] = mapped_column(String(64))
    target_entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_entity_id: Mapped[str] = mapped_column(String(100), nullable=False)
    architecture_version: Mapped[str] = mapped_column(String(80), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(80), nullable=False)
    context_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_region: Mapped[str] = mapped_column(String(40), nullable=False)
    deployment_name: Mapped[str] = mapped_column(String(120), nullable=False)
    model_name: Mapped[str] = mapped_column(String(80), nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    input_token_upper_bound: Mapped[int] = mapped_column(Integer, nullable=False)
    input_tokens: Mapped[int | None] = mapped_column(Integer)
    output_tokens: Mapped[int | None] = mapped_column(Integer)
    total_tokens: Mapped[int | None] = mapped_column(Integer)
    input_rate_usd_per_1m: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    output_rate_usd_per_1m: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    pricing_source_reference: Mapped[str] = mapped_column(String(500), nullable=False)
    reserved_cost_usd: Mapped[float] = mapped_column(Numeric(18, 8), nullable=False)
    estimated_cost_usd: Mapped[float | None] = mapped_column(Numeric(18, 8))
    citation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    provider_response_id: Mapped[str | None] = mapped_column(String(200))
    output_fingerprint: Mapped[str | None] = mapped_column(String(64))
    error_code: Mapped[str | None] = mapped_column(String(120))
    synthetic_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


@event.listens_for(AIExecutionLedger, "before_insert")
def _backfill_legacy_ledger_scope(_mapper, _connection, target: AIExecutionLedger) -> None:
    """Preserve existing project reservation writers during the additive migration."""

    if target.project_id and not target.scope_type:
        target.scope_type = "PROJECT"
    if target.project_id and not target.scope_id:
        target.scope_id = target.project_id
