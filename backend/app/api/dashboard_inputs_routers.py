"""Dashboard Master Content Inputs & Go-Live API."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..models import DashboardInputItem, Role
from ..services.dashboard_inputs import CONFIRMED_STATUSES, CONTEXT_KEY, GOVERNANCE_CONTEXT_KEY, dashboard_inputs_payload, default_status
from ..services.owner_decisions import LEGACY_ALIASES, apply_action, get_decision, sync_legacy_projection

router = APIRouter(prefix="/api/dashboard-inputs", tags=["dashboard-inputs"])


class DashboardInputUpdate(BaseModel):
    action: str | None = Field(default=None, max_length=40)
    status: str | None = Field(default=None, max_length=40)
    notes: str | None = Field(default=None, max_length=2000)


def owner_only(role: Role) -> None:
    if role not in {Role.SYSTEM_ADMIN, Role.OWNER_SPONSOR}:
        raise HTTPException(status_code=403, detail={"code": "DASHBOARD_INPUT_OWNER_ONLY", "message": "Only Owner can change Dashboard setup inputs."})


@router.get("")
def dashboard_inputs(include_governance: bool = Query(default=False), db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    payload = dashboard_inputs_payload(db, include_governance=include_governance)
    db.commit()
    return payload


@router.patch("/{input_key}")
def update_dashboard_input(input_key: str, payload: DashboardInputUpdate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    owner_only(role)
    item = db.scalar(select(DashboardInputItem).where(DashboardInputItem.context_key.in_((CONTEXT_KEY, GOVERNANCE_CONTEXT_KEY)), DashboardInputItem.input_key == input_key))
    if not item:
        # The GET path is idempotent and also establishes the registry.
        dashboard_inputs_payload(db)
        item = db.scalar(select(DashboardInputItem).where(DashboardInputItem.context_key.in_((CONTEXT_KEY, GOVERNANCE_CONTEXT_KEY)), DashboardInputItem.input_key == input_key))
    if not item:
        raise HTTPException(status_code=404, detail={"code": "DASHBOARD_INPUT_NOT_FOUND"})
    action = (payload.action or "").lower()
    alias = LEGACY_ALIASES.get(input_key)
    if alias:
        canonical = get_decision(db, alias[0])
        if canonical and action in {"confirm", "complete", "reopen", "not_applicable"}:
            canonical_action = "confirm_default" if action in {"confirm", "complete"} else action
            try:
                result = apply_action(db, canonical, action=canonical_action, value=None, notes=payload.notes, actor=role.value, role=role, correlation_id=getattr(request.state, "correlation_id", "dashboard-input"))
                sync_legacy_projection(db, canonical)
                db.commit()
                return next(item for item in dashboard_inputs_payload(db)["items"] if item["key"] == input_key)
            except ValueError as exc:
                db.rollback()
                raise HTTPException(status_code=409, detail={"code": str(exc)}) from exc
    if input_key == "DASHBOARD_SYNOLOGY_CONNECTION" and action in {"confirm", "complete"}:
        raise HTTPException(status_code=409, detail={"code": "REAL_SYNOLOGY_VERIFICATION_REQUIRED", "message": "Synology cannot be manually confirmed; complete the real health check first."})
    before = {"status": item.status, "notes": item.notes, "confirmed_by": item.confirmed_by}
    if action == "confirm":
        item.status = "COMPLETE" if item.blocking_level in {"CONTENT", "EXTERNAL_TECHNICAL"} else "CONFIRMED"
        item.confirmed_by = role.value
        item.confirmed_at = datetime.now(timezone.utc)
    elif action == "reopen":
        item.status = default_status(item.input_key)
        item.confirmed_by = None
        item.confirmed_at = None
    elif action == "not_applicable":
        if item.blocking_level != "OPTIONAL":
            raise HTTPException(status_code=422, detail={"code": "DASHBOARD_INPUT_NOT_OPTIONAL"})
        item.status = "NOT_APPLICABLE"
    elif payload.status:
        allowed = set(CONFIRMED_STATUSES) | {"NEEDS_CONFIRMATION", "PROPOSED_DEFAULT", "NEEDS_DECISION", "NEEDS_CONTENT", "IN_PROGRESS", "WAITING_ON_AMEC_IT", "OPTIONAL"}
        if payload.status not in allowed or (input_key == "DASHBOARD_SYNOLOGY_CONNECTION" and payload.status in {"CONFIRMED", "COMPLETE"}):
            raise HTTPException(status_code=422, detail={"code": "DASHBOARD_INPUT_STATUS_NOT_ALLOWED"})
        item.status = payload.status
        if payload.status not in {"CONFIRMED", "COMPLETE"}:
            item.confirmed_by = None
            item.confirmed_at = None
    elif action != "note":
        raise HTTPException(status_code=422, detail={"code": "DASHBOARD_INPUT_ACTION_REQUIRED"})
    if payload.notes is not None:
        item.notes = payload.notes.strip() or None
    after = {"status": item.status, "notes": item.notes, "confirmed_by": item.confirmed_by}
    audit(db, correlation_id=getattr(request.state, "correlation_id", "dashboard-input"), event_type="DASHBOARD_INPUT_STATUS_CHANGED", entity_type="DashboardInputItem", entity_id=item.id, actor_id=role.value, before=before, after=after, metadata={"input_key": input_key, "action": action or "status", "note": payload.notes})
    db.commit()
    return next(item for item in dashboard_inputs_payload(db)["items"] if item["key"] == input_key)
