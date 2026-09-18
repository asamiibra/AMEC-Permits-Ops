"""Atomic reservation and bounded rate/cost controls backed by the AI ledger."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from ..config.settings import Settings
from ..models import AIExecutionLedger
from .errors import AIError


@dataclass(frozen=True)
class Reservation:
    ledger: AIExecutionLedger
    maximum_cost: float
    owner_token: str = ""
    generation: int = 1


def input_upper_bound(provider_input: str) -> int:
    return len(provider_input.encode("utf-8")) + 2048


def _count(db: Session, *, where) -> int:
    return int(db.scalar(select(func.count()).select_from(AIExecutionLedger).where(where)) or 0)


def _cost(db: Session, *, started_after: datetime) -> float:
    rows = db.scalars(select(AIExecutionLedger).where(AIExecutionLedger.started_at >= started_after)).all()
    now = datetime.now(timezone.utc)
    return sum(
        float(row.reserved_cost_usd or 0)
        if row.status == "RESERVED" and not (row.reservation_lease_expires_at and row.reservation_lease_expires_at <= now)
        else float(row.estimated_cost_usd or row.reserved_cost_usd or 0)
        for row in rows
    )


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
    scope_type: str | None = None,
    scope_id: str | None = None,
    owning_module: str | None = None,
    skill_id: str | None = None,
    skill_version: str | None = None,
    skill_manifest_hash: str | None = None,
    synthetic_only: bool = True,
    provider_input_content: list[dict[str, object]] | None = None,
) -> Reservation:
    existing = db.scalar(select(AIExecutionLedger).where(AIExecutionLedger.idempotency_key == idempotency_key).with_for_update())
    if existing is not None:
        if existing.request_fingerprint != request_fingerprint or existing.actor_user_id != actor_user_id:
            raise AIError("AI_IDEMPOTENCY_CONFLICT", status_code=409)
        lease_expires_at = existing.reservation_lease_expires_at
        if lease_expires_at is not None and lease_expires_at.tzinfo is None:
            # SQLite returns timezone-aware DateTime values as naive values.
            # Treat those persisted UTC timestamps consistently with the
            # PostgreSQL path before evaluating lease expiry.
            lease_expires_at = lease_expires_at.replace(tzinfo=timezone.utc)
        if (
            existing.status == "RESERVED"
            and lease_expires_at is not None
            and lease_expires_at <= datetime.now(timezone.utc)
        ):
            existing.reservation_generation = int(existing.reservation_generation or 1) + 1
            existing.reservation_owner_token = uuid4().hex
            existing.reserved_at = datetime.now(timezone.utc)
            existing.reservation_lease_expires_at = existing.reserved_at + timedelta(seconds=int(getattr(settings, "ai_reservation_lease_seconds", 300)))
            existing.reservation_reclaimed_at = existing.reserved_at
            return Reservation(existing, float(existing.reserved_cost_usd or 0), existing.reservation_owner_token, existing.reservation_generation)
        code = "AI_REQUEST_IN_PROGRESS" if existing.status == "RESERVED" else "AI_REQUEST_ALREADY_COMPLETED"
        raise AIError(code, status_code=409)

    if provider_input_content is not None:
        # Base64 image bytes are transport payload, not text tokens. Reserve
        # a bounded multimodal allowance per image alongside the serialized
        # text estimate so low-detail vision inputs do not exhaust the text
        # budget merely because of encoding overhead.
        image_count = sum(
            1 for message in provider_input_content
            for part in (message.get("content", []) if isinstance(message, dict) else [])
            if isinstance(part, dict) and part.get("type") == "input_image"
        )
        upper_bound = len(provider_input.encode("utf-8")) + 2048 + image_count * 1024
    else:
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

    reservation_owner_token = uuid4().hex
    reserved_at = datetime.now(timezone.utc)
    ledger = AIExecutionLedger(
        idempotency_key=idempotency_key, correlation_id=correlation_id, actor_user_id=actor_user_id, auth_mode=auth_mode,
        purpose=purpose, execution_mode=execution_mode, project_id=project_id, target_entity_type=target_entity_type,
        target_entity_id=target_entity_id, scope_type=scope_type or target_entity_type, scope_id=scope_id or target_entity_id,
        owning_module=owning_module, skill_id=skill_id, skill_version=skill_version,
        skill_manifest_hash=skill_manifest_hash, architecture_version=architecture_version, policy_version=policy_version,
        context_fingerprint=context_fingerprint, request_fingerprint=request_fingerprint, provider=provider,
        provider_region=provider_region, deployment_name=deployment_name, model_name=model_name, model_version=model_version,
        status="RESERVED", input_token_upper_bound=upper_bound, input_rate_usd_per_1m=settings.ai_input_price_usd_per_1m_tokens,
        output_rate_usd_per_1m=settings.ai_output_price_usd_per_1m_tokens, pricing_source_reference=settings.ai_pricing_source_reference,
        reserved_cost_usd=maximum_cost, citation_count=citation_count,
        reservation_owner_token=reservation_owner_token, reservation_generation=1,
        reserved_at=reserved_at,
        reservation_lease_expires_at=reserved_at + timedelta(seconds=int(getattr(settings, "ai_reservation_lease_seconds", 300))),
        synthetic_only=synthetic_only,
    )
    db.add(ledger)
    try:
        db.flush()
    except IntegrityError as exc:
        raise AIError("AI_REQUEST_IN_PROGRESS", status_code=409) from exc
    except OperationalError as exc:
        # SQLite serializes concurrent writers instead of consistently
        # surfacing the idempotency unique-key conflict.  A loser blocked by
        # that writer is still the same-key in-progress case; preserve the
        # public contract while allowing unrelated database errors through.
        if "database is locked" in str(exc).lower():
            raise AIError("AI_REQUEST_IN_PROGRESS", status_code=409) from exc
        raise
    return Reservation(ledger=ledger, maximum_cost=maximum_cost, owner_token=reservation_owner_token, generation=1)
