"""Atomic reservation and bounded rate/cost controls backed by the AI ledger."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config.settings import Settings
from ..models import AIExecutionLedger
from .errors import AIError


@dataclass(frozen=True)
class Reservation:
    ledger: AIExecutionLedger
    maximum_cost: float


def input_upper_bound(provider_input: str) -> int:
    return len(provider_input.encode("utf-8")) + 2048


def _count(db: Session, *, where) -> int:
    return int(db.scalar(select(func.count()).select_from(AIExecutionLedger).where(where)) or 0)


def _cost(db: Session, *, started_after: datetime) -> float:
    rows = db.scalars(select(AIExecutionLedger).where(AIExecutionLedger.started_at >= started_after)).all()
    return sum(float(row.reserved_cost_usd or 0) if row.status == "RESERVED" else float(row.estimated_cost_usd or row.reserved_cost_usd or 0) for row in rows)


def reserve_execution(
    db: Session,
    *,
    settings: Settings,
    idempotency_key: str,
    correlation_id: str,
    actor_user_id: str | None,
    auth_mode: str,
    purpose: str,
    execution_mode: str,
    project_id: str,
    target_entity_type: str,
    target_entity_id: str,
    architecture_version: str,
    policy_version: str,
    context_fingerprint: str,
    request_fingerprint: str,
    provider: str,
    provider_region: str,
    deployment_name: str,
    model_name: str,
    model_version: str,
    citation_count: int,
    provider_input: str,
) -> Reservation:
    existing = db.scalar(select(AIExecutionLedger).where(AIExecutionLedger.idempotency_key == idempotency_key).with_for_update())
    if existing is not None:
        code = "AI_REQUEST_IN_PROGRESS" if existing.status == "RESERVED" else "AI_REQUEST_ALREADY_COMPLETED"
        raise AIError(code, status_code=409)

    upper_bound = input_upper_bound(provider_input)
    if upper_bound > settings.ai_max_input_token_upper_bound:
        raise AIError("AI_INPUT_TOKEN_BUDGET_EXCEEDED", status_code=429)
    maximum_cost = (upper_bound * settings.ai_input_price_usd_per_1m_tokens / 1_000_000) + (settings.ai_max_output_tokens * settings.ai_output_price_usd_per_1m_tokens / 1_000_000)
    if maximum_cost > settings.ai_max_estimated_cost_usd_per_request:
        raise AIError("AI_COST_BUDGET_EXCEEDED", status_code=429)

    now = datetime.now(timezone.utc)
    minute = now - timedelta(minutes=1)
    hour = now - timedelta(hours=1)
    day = now - timedelta(days=1)
    actor_filter = AIExecutionLedger.actor_user_id == actor_user_id
    if _count(db, where=actor_filter & (AIExecutionLedger.started_at >= minute)) >= settings.ai_max_requests_per_user_per_minute:
        raise AIError("AI_RATE_LIMIT_USER_MINUTE", status_code=429)
    if _count(db, where=actor_filter & (AIExecutionLedger.started_at >= hour)) >= settings.ai_max_requests_per_user_per_hour:
        raise AIError("AI_RATE_LIMIT_USER_HOUR", status_code=429)
    if _count(db, where=(AIExecutionLedger.project_id == project_id) & (AIExecutionLedger.started_at >= hour)) >= settings.ai_max_requests_per_project_per_hour:
        raise AIError("AI_RATE_LIMIT_PROJECT_HOUR", status_code=429)
    if _count(db, where=AIExecutionLedger.started_at >= hour) >= settings.ai_max_requests_global_per_hour:
        raise AIError("AI_RATE_LIMIT_GLOBAL_HOUR", status_code=429)
    if _cost(db, started_after=day) + maximum_cost > settings.ai_max_estimated_cost_usd_per_day:
        raise AIError("AI_COST_BUDGET_EXCEEDED", status_code=429)

    ledger = AIExecutionLedger(
        idempotency_key=idempotency_key, correlation_id=correlation_id, actor_user_id=actor_user_id, auth_mode=auth_mode,
        purpose=purpose, execution_mode=execution_mode, project_id=project_id, target_entity_type=target_entity_type,
        target_entity_id=target_entity_id, architecture_version=architecture_version, policy_version=policy_version,
        context_fingerprint=context_fingerprint, request_fingerprint=request_fingerprint, provider=provider,
        provider_region=provider_region, deployment_name=deployment_name, model_name=model_name, model_version=model_version,
        status="RESERVED", input_token_upper_bound=upper_bound, input_rate_usd_per_1m=settings.ai_input_price_usd_per_1m_tokens,
        output_rate_usd_per_1m=settings.ai_output_price_usd_per_1m_tokens, pricing_source_reference=settings.ai_pricing_source_reference,
        reserved_cost_usd=maximum_cost, citation_count=citation_count, synthetic_only=True,
    )
    db.add(ledger)
    try:
        db.flush()
    except IntegrityError as exc:
        raise AIError("AI_REQUEST_IN_PROGRESS", status_code=409) from exc
    return Reservation(ledger=ledger, maximum_cost=maximum_cost)
