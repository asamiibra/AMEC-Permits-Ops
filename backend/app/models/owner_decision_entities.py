"""Canonical Owner decision register and immutable decision history."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class OwnerDecision(Base):
    __tablename__ = "owner_decisions"
    __table_args__ = (UniqueConstraint("decision_key", name="uq_owner_decision_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    decision_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    group_name: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    why: Mapped[str] = mapped_column(Text, nullable=False)
    decision_type: Mapped[str] = mapped_column(String(60), nullable=False)
    blocking_level: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    proposed_default_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    effective_value_json: Mapped[Any | None] = mapped_column(JSON)
    options_json: Mapped[list[Any]] = mapped_column(JSON, default=list, nullable=False)
    affected_modules_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    owner_notes: Mapped[str | None] = mapped_column(Text)
    confirmed_by: Mapped[str | None] = mapped_column(String(200))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    effective_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    supersedes_decision_id: Mapped[str | None] = mapped_column(String(36), index=True)
    system_fact_source: Mapped[str | None] = mapped_column(String(300))
    current_system_state_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    runtime_value_json: Mapped[Any | None] = mapped_column(JSON)
    apply_state: Mapped[str] = mapped_column(String(40), default="NOT_APPLIED", nullable=False)
    runtime_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    legacy_keys_json: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)


class OwnerDecisionHistory(Base):
    __tablename__ = "owner_decision_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    decision_id: Mapped[str] = mapped_column(ForeignKey("owner_decisions.id"), nullable=False, index=True)
    decision_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    before_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    after_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    actor_id: Mapped[str | None] = mapped_column(String(200))
    actor_role: Mapped[str | None] = mapped_column(String(80))
    note: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class OwnerDecisionAlias(Base):
    __tablename__ = "owner_decision_aliases"
    __table_args__ = (UniqueConstraint("legacy_key", name="uq_owner_decision_legacy_key"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    legacy_key: Mapped[str] = mapped_column(String(160), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    source_module: Mapped[str] = mapped_column(String(100), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text)
    migrated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
