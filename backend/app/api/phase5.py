from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..db import get_db
from ..models import Role
from ..schemas.classifier_v2 import (
    ClassifierV2Request,
    Phase5ProjectionIn,
    Phase5PromotionIn,
    Phase5ReviewDecisionIn,
)
from ..schemas.phase4 import ProjectionRequest, PromotionIn, ReviewDecisionIn
from ..services.classifier_v2 import classify_and_persist
from ..services.phase4 import (
    execute_projection,
    plan_projection,
    promote_verified_assertion,
    record_review_decision,
    review_queue,
    serialize,
)


router = APIRouter(prefix="/api/phase5", tags=["phase5-classifier-v2"])


@router.get("/health")
def phase5_health(role: Role = Depends(current_user_role)):
    return {
        "status": "ready",
        "classifier_version": "classifier-v2-rules-only-1.0.0",
        "learned_classifier_mode": "NOT_PROMOTED_DATA_INSUFFICIENT",
        "llm_real_content_mode": "DISABLED",
        "llm_external_call_count": 0,
        "shadow_state": "REVIEW_COMPARE_ONLY",
        "capability_persona": role.value,
    }


@router.post("/classify")
def classify(payload: ClassifierV2Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = classify_and_persist(db, payload, role)
    db.commit()
    return item


@router.post("/shadow-replay")
def shadow_replay(payload: ClassifierV2Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = classify_and_persist(db, payload, role)
    db.commit()
    return {**item, "shadow_state": "REVIEW_COMPARE_ONLY", "promotion_attempted": False, "projection_attempted": False}


@router.get("/review-queue")
def get_review_queue(scope_type: str | None = None, scope_id: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return {"items": review_queue(db, role, scope_type=scope_type, scope_id=scope_id)}


@router.post("/review-decisions")
def review_decision(payload: Phase5ReviewDecisionIn, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    phase4_payload = ReviewDecisionIn(**payload.model_dump())
    item = record_review_decision(db, phase4_payload, role)
    db.commit()
    return {**serialize(item), "history_policy": "APPEND_ONLY"}


@router.post("/verified-assertions/{verified_assertion_id}/promote")
def promote(verified_assertion_id: str, payload: Phase5PromotionIn, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    phase4_payload = PromotionIn(**payload.model_dump())
    if phase4_payload.verified_assertion_id != verified_assertion_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail={"code": "ASSERTION_PATH_ID_MISMATCH"})
    item = promote_verified_assertion(db, phase4_payload, role)
    db.commit()
    return {**serialize(item), "promotion_boundary": "EXPLICIT_HUMAN_REVIEW_ONLY"}


@router.post("/projection-plans")
def projection_plan(payload: Phase5ProjectionIn, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = plan_projection(db, ProjectionRequest(**payload.model_dump()), role)
    db.commit()
    return {**serialize(item), "classifier_only_projection": False}


@router.post("/projections")
def projection(payload: Phase5ProjectionIn, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = execute_projection(db, ProjectionRequest(**payload.model_dump()), role)
    db.commit()
    return {**serialize(item), "classifier_only_projection": False}
