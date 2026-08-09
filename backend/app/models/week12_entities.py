"""Week 12 in-scope variant, rendering, handoff, and attended-auth records."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, utcnow


def _id() -> str:
    return str(uuid4())


class ScenarioVariant(Base):
    __tablename__ = "scenario_variants"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    variant_code: Mapped[str] = mapped_column(String(100), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    applicability: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    canonical_fixture_project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.id"))
    included: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    signed_scope_basis: Mapped[str] = mapped_column(String(300), nullable=False)
    rule_set_version: Mapped[str] = mapped_column(String(50), nullable=False)
    field_set_version: Mapped[str] = mapped_column(String(50), nullable=False)
    rendering_set_version: Mapped[str] = mapped_column(String(50), nullable=False)
    attachment_rule_set_version: Mapped[str] = mapped_column(String(50), nullable=False)
    grid_rule_set_version: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False)


class VariantCompatibilityResult(Base):
    __tablename__ = "variant_compatibility_results"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    base_variant: Mapped[str] = mapped_column(String(100), nullable=False)
    second_variant: Mapped[str] = mapped_column(String(100), nullable=False)
    domain_schema_change_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    new_semantic_fields: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    new_rendering_rules: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    new_requirement_rules: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    new_attachment_rules: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    new_grid_rules: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    new_human_decisions: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    core_code_fork_required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    result: Mapped[str] = mapped_column(String(40), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class TargetRenderingCoverage(Base):
    __tablename__ = "target_rendering_coverages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenario_configs.id"), nullable=False)
    variant_id: Mapped[str] = mapped_column(ForeignKey("scenario_variants.id"), nullable=False)
    target_type: Mapped[str] = mapped_column(String(60), nullable=False)
    supported_fields: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    mapped_fields: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    missing_fields: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    blocked_external: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    not_applicable: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    coverage_percent: Mapped[float] = mapped_column(Float, nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)


class AttendedAuthSession(Base):
    __tablename__ = "attended_auth_sessions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str | None] = mapped_column(ForeignKey("permit_applications.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    user_role: Mapped[str] = mapped_column(String(80), nullable=False)
    environment: Mapped[str] = mapped_column(String(40), nullable=False)
    adapter_id: Mapped[str | None] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    auth_mode: Mapped[str] = mapped_column(String(60), nullable=False)
    mfa_mode: Mapped[str] = mapped_column(String(60), nullable=False)
    mfa_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    challenge_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    challenge_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    session_reference_hash: Mapped[str | None] = mapped_column(String(64))
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)


class MfaChallengeEvent(Base):
    __tablename__ = "mfa_challenge_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    auth_session_id: Mapped[str] = mapped_column(ForeignKey("attended_auth_sessions.id"), nullable=False)
    challenge_type: Mapped[str] = mapped_column(String(60), nullable=False)
    initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_by_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    result: Mapped[str] = mapped_column(String(30), nullable=False)
    external_reference_hash: Mapped[str | None] = mapped_column(String(64))


class HumanTakeoverEvent(Base):
    __tablename__ = "human_takeover_events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_id)
    application_id: Mapped[str] = mapped_column(ForeignKey("permit_applications.id"), nullable=False)
    session_reference: Mapped[str | None] = mapped_column(String(100))
    initiated_by: Mapped[str] = mapped_column(String(200), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    prior_state_hash: Mapped[str | None] = mapped_column(String(64))
    reread_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    reconciliation_result: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    correlation_id: Mapped[str] = mapped_column(String(100), nullable=False)
