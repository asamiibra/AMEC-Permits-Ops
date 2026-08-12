"""Owner Decision Center API and truthful go-live computation."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..db import get_db
from ..models import OwnerDecision, OwnerDecisionHistory, Role
from ..services.owner_decisions import DECISION_BY_KEY, OWNER_ROLES, apply_action, get_decision, register_payload, sync_legacy_projection


router = APIRouter(prefix="/api/owner-decisions", tags=["owner-decisions"])


class DecisionAction(BaseModel):
    action: str = Field(min_length=1, max_length=40)
    value: Any | None = None
    notes: str | None = Field(default=None, max_length=4000)


def owner_only(role: Role = Depends(current_user_role)) -> Role:
    if role not in OWNER_ROLES:
        raise HTTPException(status_code=403, detail={"code": "UNAUTHORIZED_OWNER_DECISION_CHANGE", "message": "Only an authorized Owner may change global decisions."})
    return role


@router.get("")
def list_owner_decisions(db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return register_payload(db)


@router.post("/{decision_key}/actions")
def owner_decision_action(decision_key: str, payload: DecisionAction, request: Request, db: Session = Depends(get_db), role: Role = Depends(owner_only), x_test_force_apply_failure: str | None = Header(default=None)):
    item = get_decision(db, decision_key)
    if not item:
        raise HTTPException(status_code=404, detail={"code": "OWNER_DECISION_NOT_FOUND", "key": decision_key})
    action = payload.action.lower().strip()
    allowed = {"confirm_default", "choose", "not_applicable", "approve_safe_default", "reopen", "supersede"}
    if action not in allowed:
        raise HTTPException(status_code=422, detail={"code": "OWNER_DECISION_ACTION_INVALID", "allowed": sorted(allowed)})
    actor = role.value
    try:
        result = apply_action(db, item, action=action, value=payload.value, notes=payload.notes, actor=actor, role=role, correlation_id=request.state.correlation_id, force_apply_failure=x_test_force_apply_failure == "true")
        sync_legacy_projection(db, item)
        db.commit()
        return result
    except ValueError as exc:
        db.rollback()
        code = str(exc)
        status = 409 if code in {"SYNOLOGY_MANUAL_VERIFICATION_ZERO", "OWNER_DECISION_SELECTION_REQUIRED"} else 422
        raise HTTPException(status_code=status, detail={"code": code}) from exc


@router.post("/{decision_key}/technical-verify")
def technical_verify(decision_key: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(owner_only)):
    # The endpoint deliberately has no request field that can promote a fact.
    # A future adapter verification may call the service with machine evidence.
    item = get_decision(db, decision_key)
    if not item or item.decision_type != "TECHNICAL_FACT":
        raise HTTPException(status_code=404, detail={"code": "OWNER_DECISION_TECHNICAL_FACT_NOT_FOUND"})
    raise HTTPException(status_code=409, detail={"code": "REAL_SYNOLOGY_VERIFICATION_REQUIRED", "message": "Technical verification must come from the real adapter health check; Owner acknowledgement cannot set VERIFIED."})


@router.get("/readiness/summary")
def owner_decision_readiness(db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    payload = register_payload(db)
    return {"go_live": payload["go_live"], "summary": payload["summary"], "truth_tokens": payload["truth_tokens"]}


@router.post("/test-support/cleanup")
def owner_decision_test_cleanup(db: Session = Depends(get_db), role: Role = Depends(owner_only)):
    from ..services.owner_decisions import ensure_register
    if role != Role.SYSTEM_ADMIN:
        raise HTTPException(status_code=403, detail={"code": "TEST_CLEANUP_SYSTEM_ADMIN_ONLY"})
    ensure_register(db)
    history_removed = db.query(OwnerDecisionHistory).delete(synchronize_session=False)
    for item in db.query(OwnerDecision).all():
        spec = DECISION_BY_KEY[item.decision_key]
        item.status = "EXTERNAL_TECHNICAL_BLOCK" if spec["blocking"] == "EXTERNAL_TECHNICAL" else "UNANSWERED" if spec["blocking"] == "P0_GO_LIVE_BLOCKER" else "PROPOSED_DEFAULT"
        item.effective_value_json = None
        item.runtime_value_json = None
        item.owner_notes = None
        item.confirmed_by = None
        item.confirmed_at = None
        item.effective_from = None
        item.apply_state = "NOT_APPLIED"
        item.runtime_checked_at = None
    db.commit()
    return {"status": "CLEANED", "history_removed": history_removed, "decisions_reset": db.query(OwnerDecision).count()}


@router.get("/{decision_key}")
def owner_decision_detail(decision_key: str, db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    item = get_decision(db, decision_key)
    if not item:
        raise HTTPException(status_code=404, detail={"code": "OWNER_DECISION_NOT_FOUND", "key": decision_key})
    from ..services.owner_decisions import _decision_payload
    return _decision_payload(db, item)
