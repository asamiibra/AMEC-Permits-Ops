"""AI-D1 context seam plus the single D3 interactive draft endpoint.

There is intentionally no generation, chat, completion, agent, invoke-model,
provider, task enqueue, or persistence endpoint in this tranche.
"""

from __future__ import annotations

from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from ..ai.context import build_context_manifest
from ..ai.contracts import AIContextManifest
from ..api.dependencies import AuthenticatedPrincipal, trusted_current_principal
from ..db import get_db
from ..services.governed_retrieval import RetrievalQuery
from ..ai.orchestration import execute_technical_methodology
from ..config.settings import get_settings


router = APIRouter(prefix="/api/ai", tags=["ai-context"])


class TechnicalMethodologyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project_id: UUID
    client_request_id: UUID


@router.get("/runtime-status")
def runtime_status(
    principal: Annotated[
        AuthenticatedPrincipal, Depends(trusted_current_principal)
    ],
) -> dict[str, object]:
    settings = get_settings()
    return {
        "feature_present": True,
        "feature_enabled": bool(settings.ai_feature_enabled),
        "external_inference_enabled": bool(settings.ai_external_inference_enabled),
        "commissioning_state": "COMMISSIONED" if settings.ai_external_inference_enabled else "COMMISSIONING_PENDING",
        "synthetic_only": settings.synthetic_only,
        "real_data_allowed": settings.real_data_allowed,
        "ai_real_content_allowed": settings.ai_real_content_allowed,
        "authenticated_actor": principal.auth_mode,
    }


class AIContextRetrievalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str | None = Field(default=None, max_length=500)
    master_content_id: str | None = None
    document_version_id: str | None = None
    definition_entry_id: str | None = None
    project_id: str | None = None
    limit: int = Field(default=20, ge=1, le=50)

    def to_retrieval_query(self) -> RetrievalQuery:
        return RetrievalQuery(**self.model_dump())


class AIContextManifestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    purpose: str = Field(min_length=1, max_length=100)
    execution_mode: str = Field(min_length=1, max_length=30)
    target_entity_type: str = Field(min_length=1, max_length=50)
    target_entity_id: str = Field(min_length=1, max_length=100)
    retrieval: AIContextRetrievalRequest = Field(
        default_factory=AIContextRetrievalRequest
    )


@router.post("/context/manifest", response_model=AIContextManifest)
def context_manifest(
    payload: AIContextManifestRequest,
    request: Request,
    principal: Annotated[
        AuthenticatedPrincipal, Depends(trusted_current_principal)
    ],
    db: Session = Depends(get_db),
) -> AIContextManifest:
    manifest = build_context_manifest(
        db,
        principal,
        purpose=payload.purpose,
        execution_mode=payload.execution_mode,
        target_entity_type=payload.target_entity_type,
        target_entity_id=payload.target_entity_id,
        query=payload.retrieval.to_retrieval_query(),
    )
    # Only safe contract metadata is observable here.  Full evidence content
    # is never written to logs, and no audit/business event is created.
    request.state.ai_context_observability = {
        "purpose": manifest.purpose.value,
        "execution_mode": manifest.execution_mode.value,
        "target_entity_type": manifest.scope.target_entity_type.value,
        "authorized": True,
        "decision_code": "AI_CONTEXT_AUTHORIZED",
        "item_count": len(manifest.items),
        "total_context_bytes": sum(
            len(item.content.encode("utf-8")) for item in manifest.items
        ),
        "manifest_fingerprint": manifest.manifest_fingerprint,
    }
    return manifest


@router.post("/interactive/technical-methodology")
def interactive_technical_methodology(
    payload: TechnicalMethodologyRequest,
    request: Request,
    principal: Annotated[AuthenticatedPrincipal, Depends(trusted_current_principal)],
    db: Session = Depends(get_db),
    correlation_id: str | None = Header(default=None, alias="X-Correlation-ID"),
) -> dict[str, object]:
    request_id = str(payload.client_request_id)
    correlation = correlation_id or str(uuid4())
    if len(correlation) > 100:
        correlation = correlation[:100]
    return execute_technical_methodology(
        db,
        principal,
        settings=get_settings(),
        project_id=str(payload.project_id),
        client_request_id=request_id,
        correlation_id=correlation,
    )
