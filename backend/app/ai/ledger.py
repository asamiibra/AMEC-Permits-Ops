from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import AIExecutionLedger
from .errors import AIError
from .provider import AIProviderUsage


def reserve_audit(db: Session, *, ledger: AIExecutionLedger, actor_type: str) -> None:
    audit(db, correlation_id=ledger.correlation_id, event_type="AI_INTERACTIVE_REQUEST_RESERVED", entity_type="AIExecutionLedger", entity_id=ledger.id, actor_id=ledger.actor_user_id, actor_type=actor_type, metadata={"ledger_id": ledger.id, "purpose": ledger.purpose, "project_id": ledger.project_id, "target_entity_type": ledger.target_entity_type, "target_entity_id": ledger.target_entity_id, "context_fingerprint": ledger.context_fingerprint, "request_fingerprint": ledger.request_fingerprint, "provider": ledger.provider, "deployment": ledger.deployment_name, "model": ledger.model_name, "version": ledger.model_version})


def finalize_success(db: Session, *, ledger_id: str, correlation_id: str, actor_id: str | None, actor_type: str, usage: AIProviderUsage, estimated_cost: float, output_fingerprint: str, citation_count: int, provider_response_id: str) -> None:
    ledger = db.get(AIExecutionLedger, ledger_id)
    if ledger is None or ledger.status != "RESERVED":
        raise AIError("AI_LEDGER_FINALIZATION_FAILED", status_code=500)
    ledger.status = "SUCCEEDED"
    ledger.input_tokens = usage.input_tokens
    ledger.output_tokens = usage.output_tokens
    ledger.total_tokens = usage.total_tokens
    ledger.estimated_cost_usd = estimated_cost
    ledger.output_fingerprint = output_fingerprint
    ledger.citation_count = citation_count
    ledger.provider_response_id = provider_response_id
    ledger.completed_at = datetime.now(timezone.utc)
    audit(db, correlation_id=correlation_id, event_type="AI_INTERACTIVE_REQUEST_SUCCEEDED", entity_type="AIExecutionLedger", entity_id=ledger.id, actor_id=actor_id, actor_type=actor_type, metadata={"ledger_id": ledger.id, "input_tokens": usage.input_tokens, "output_tokens": usage.output_tokens, "total_tokens": usage.total_tokens, "estimated_cost_usd": estimated_cost, "citation_count": citation_count, "output_fingerprint": output_fingerprint})


def finalize_failure(db: Session, *, ledger_id: str, correlation_id: str, actor_id: str | None, actor_type: str, code: str) -> None:
    ledger = db.get(AIExecutionLedger, ledger_id)
    if ledger is None or ledger.status != "RESERVED":
        raise AIError("AI_LEDGER_FINALIZATION_FAILED", status_code=500)
    ledger.status = "FAILED"
    ledger.error_code = code
    ledger.estimated_cost_usd = ledger.reserved_cost_usd
    ledger.completed_at = datetime.now(timezone.utc)
    audit(db, correlation_id=correlation_id, event_type="AI_INTERACTIVE_REQUEST_FAILED", entity_type="AIExecutionLedger", entity_id=ledger.id, actor_id=actor_id, actor_type=actor_type, metadata={"ledger_id": ledger.id, "error_code": code})
