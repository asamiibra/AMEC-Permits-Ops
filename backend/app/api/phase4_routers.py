from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Phase4ClassificationEnvelope, Phase4ProjectionReceipt, Role
from ..api.dependencies import current_user_role
from ..schemas.phase4 import (
    ClassificationEnvelopeIn,
    EvidenceEnvelopeIn,
    ProjectionRequest,
    PromotionIn,
    ReviewDecisionIn,
    SourceChangeEventIn,
)
from ..services.phase4 import (
    create_classification_envelope,
    execute_projection,
    ingest_evidence_envelope,
    plan_projection,
    promote_verified_assertion,
    record_review_decision,
    record_source_event,
    review_queue,
    serialize,
)


router = APIRouter(prefix="/api/phase4", tags=["phase4-corpus"])


@router.get("/health")
def phase4_health(role: Role = Depends(current_user_role)):
    return {"status": "ready", "contract": "AMEC_CORPUS_APP_INTEGRATION_CONTRACT_V1", "capability_persona": role.value}


@router.post("/source-events")
def source_event(payload: SourceChangeEventIn, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = record_source_event(db, payload, role)
    db.commit()
    return serialize(item)


@router.post("/evidence-envelopes")
def evidence_envelope(payload: EvidenceEnvelopeIn, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = ingest_evidence_envelope(db, payload, role)
    db.commit()
    return serialize(item)


@router.post("/classification-envelopes")
def classification_envelope(payload: ClassificationEnvelopeIn, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = create_classification_envelope(db, payload, role)
    db.commit()
    return serialize(item)


@router.get("/review-queue")
def get_review_queue(scope_type: str | None = None, scope_id: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return {"items": review_queue(db, role, scope_type=scope_type, scope_id=scope_id)}


@router.get("/review/{envelope_id}")
def get_review(envelope_id: str, scope_type: str | None = None, scope_id: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    scoped = review_queue(db, role, scope_type=scope_type, scope_id=scope_id)
    if not any(item["id"] == envelope_id for item in scoped):
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "CLASSIFICATION_ENVELOPE_NOT_FOUND"})
    item = db.get(Phase4ClassificationEnvelope, envelope_id)
    if item is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "CLASSIFICATION_ENVELOPE_NOT_FOUND"})
    return serialize(item)


@router.post("/review-decisions")
def review_decision(payload: ReviewDecisionIn, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = record_review_decision(db, payload, role)
    db.commit()
    return serialize(item)


@router.post("/verified-assertions/{verified_assertion_id}/promote")
def promote(verified_assertion_id: str, payload: PromotionIn, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    if payload.verified_assertion_id != verified_assertion_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail={"code": "ASSERTION_PATH_ID_MISMATCH"})
    item = promote_verified_assertion(db, payload, role)
    db.commit()
    return serialize(item)


@router.post("/projection-plans")
def projection_plan(payload: ProjectionRequest, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = plan_projection(db, payload, role)
    db.commit()
    return serialize(item)


@router.post("/projections")
def projection(payload: ProjectionRequest, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    item = execute_projection(db, payload, role)
    db.commit()
    return serialize(item)


@router.get("/projection-receipts/{projection_id}")
def projection_receipt(projection_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    from ..services.backend_realignment import require_capability
    require_capability(role, "PHASE4_TYPED_PROJECTION")
    item = db.scalar(select(Phase4ProjectionReceipt).where(Phase4ProjectionReceipt.projection_id == projection_id))
    if item is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail={"code": "PROJECTION_RECEIPT_NOT_FOUND"})
    return serialize(item)
