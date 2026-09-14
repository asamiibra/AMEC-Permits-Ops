"""Proposal-owned P08 Intelligence API; no generic browser AI runtime."""

from __future__ import annotations

from typing import Any, Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..api.dependencies import AuthenticatedPrincipal, trusted_current_principal
from ..config.settings import get_settings
from ..db import get_db
from ..services.proposal_intelligence import ProposalDeterministicProvider, apply_section_draft, create_candidate_review, execute_proposal_intelligence, proposal_reviews, submit_proposal_review

router = APIRouter(prefix="/api/bd/proposals", tags=["bd-proposal-intelligence"])


class ProposalIntelligenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    operation: str = Field(min_length=1, max_length=80)
    idempotency_key: str = Field(min_length=1, max_length=200)


class ProposalReviewDecisionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    decision: str = Field(min_length=1, max_length=30)
    idempotency_key: str = Field(min_length=1, max_length=200)
    precondition_version: str = Field(min_length=1, max_length=200)
    correction_payload: dict[str, Any] | None = None
    reason: str | None = Field(default=None, max_length=2000)


class ProposalSectionDraftApplyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    work_product_id: str = Field(min_length=1, max_length=36)
    working_revision_id: str = Field(min_length=1, max_length=36)
    working_revision_hash: str = Field(min_length=64, max_length=64)
    section_type: str = Field(min_length=1, max_length=80)
    edited_content: str = Field(min_length=1, max_length=100000)


@router.post("/{proposal_id}/intelligence")
def execute_proposal_intelligence_route(
    proposal_id: str, payload: ProposalIntelligenceRequest, request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(trusted_current_principal)],
    db: Session = Depends(get_db), correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
):
    correlation = correlation_id or str(uuid4())
    settings = get_settings()
    synthetic_local = settings.synthetic_only and settings.app_env.upper() in {"TEST", "DEV"}
    provider = ProposalDeterministicProvider() if synthetic_local else None
    return execute_proposal_intelligence(db, proposal_id=proposal_id, operation=payload.operation, principal=principal, idempotency_key=payload.idempotency_key, correlation_id=correlation, settings=settings, provider=provider)


@router.get("/{proposal_id}/intelligence/reviews")
def proposal_intelligence_reviews(
    proposal_id: str, principal: Annotated[AuthenticatedPrincipal, Depends(trusted_current_principal)], db: Session = Depends(get_db),
):
    return {"items": proposal_reviews(db, proposal_id)}


@router.post("/{proposal_id}/intelligence/candidates/{candidate_id}/review")
def proposal_candidate_review(
    proposal_id: str, candidate_id: str, request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(trusted_current_principal)], db: Session = Depends(get_db),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
):
    binding = create_candidate_review(db, proposal_id=proposal_id, candidate_id=candidate_id, principal=principal, correlation_id=correlation_id or str(uuid4()))
    db.commit()
    return {"binding_id": binding.id, "workflow_task_id": binding.workflow_task_id, "precondition_version": binding.precondition_version, "required_capability": binding.required_capability}


@router.post("/{proposal_id}/intelligence/reviews/{binding_id}/decision")
def proposal_intelligence_review_decision(
    proposal_id: str, binding_id: str, payload: ProposalReviewDecisionRequest, request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(trusted_current_principal)], db: Session = Depends(get_db),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
):
    return submit_proposal_review(db, proposal_id=proposal_id, binding_id=binding_id, decision=payload.decision, idempotency_key=payload.idempotency_key, principal=principal, correlation_id=correlation_id or str(uuid4()), precondition_version=payload.precondition_version, correction_payload=payload.correction_payload, reason=payload.reason)


@router.post("/{proposal_id}/intelligence/section-draft/apply")
def apply_proposal_section_draft(
    proposal_id: str, payload: ProposalSectionDraftApplyRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(trusted_current_principal)],
    db: Session = Depends(get_db), correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
):
    result = apply_section_draft(
        db,
        proposal_id=proposal_id,
        work_product_id=payload.work_product_id,
        working_revision_id=payload.working_revision_id,
        working_revision_hash=payload.working_revision_hash,
        section_type=payload.section_type,
        edited_content=payload.edited_content,
        principal=principal,
        correlation_id=correlation_id or str(uuid4()),
    )
    db.commit()
    return result
