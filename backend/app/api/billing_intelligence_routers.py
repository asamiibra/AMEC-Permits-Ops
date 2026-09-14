"""Billing Intelligence routes; all work is draft/recommendation only."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from backend.app.api.dependencies import AuthenticatedPrincipal, trusted_current_principal
from backend.app.ai.billing_skill_pack import BILLING_SKILLS_BY_ID
from backend.app.config.settings import get_settings
from backend.app.db import get_db
from backend.app.services.billing_intelligence import execute_billing_intelligence
from backend.app.services.context_compiler import ContextSourceSpec


router = APIRouter(prefix="/api/billing/intelligence", tags=["billing-intelligence"])


class BillingIntelligenceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    sources: list[ContextSourceSpec] = Field(min_length=1, max_length=20)
    idempotency_key: str = Field(default_factory=lambda: str(uuid4()), min_length=1, max_length=200)


@router.get("/skills")
def list_billing_intelligence_skills(
    principal: Annotated[AuthenticatedPrincipal, Depends(trusted_current_principal)],
) -> dict[str, object]:
    return {
        "feature": "Billing Intelligence",
        "skills": [
            {
                "skill_id": item.manifest.skill_id,
                "version": item.manifest.version,
                "manifest_hash": item.manifest.manifest_hash,
                "output_class": item.manifest.output_class,
                "review_trigger": item.manifest.review_trigger,
                "canonical_write_authority": item.manifest.canonical_write_authority,
                "protected_action_authority": item.manifest.protected_action_authority,
            }
            for item in BILLING_SKILLS_BY_ID.values()
        ],
        "cash_forecasting": "DEFERRED_PENDING_SUFFICIENT_HISTORY_AND_VALIDATED_NUMERIC_MODEL",
    }


@router.post("/{skill_name}")
def run_billing_intelligence(
    skill_name: str,
    payload: BillingIntelligenceRequest,
    principal: Annotated[AuthenticatedPrincipal, Depends(trusted_current_principal)],
    db: Session = Depends(get_db),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
) -> dict[str, object]:
    skill_id = f"billing.{skill_name}"
    if skill_id not in BILLING_SKILLS_BY_ID:
        raise HTTPException(status_code=404, detail={"code": "BILLING_INTELLIGENCE_SKILL_NOT_FOUND"})
    return execute_billing_intelligence(
        db,
        skill_id=skill_id,
        project_id=str(payload.project_id),
        principal=principal,
        sources=[item.model_dump(mode="json") for item in payload.sources],
        idempotency_key=payload.idempotency_key,
        correlation_id=correlation_id or str(uuid4()),
        settings=get_settings(),
    )

