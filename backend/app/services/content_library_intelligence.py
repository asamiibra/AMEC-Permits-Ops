"""Content Library adapter over the shared Intelligence runtime."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.ai.content_library_skill_pack import (
    CONTENT_LIBRARY_CONTEXT_VERSION,
    CONTENT_LIBRARY_POLICY_VERSION,
    CONTENT_LIBRARY_SKILLS_BY_ID,
)
from backend.app.ai.provider import AIProviderRequest, AIProviderResult, AIProviderUsage
from backend.app.ai.skill_registry import SKILL_REGISTRY
from backend.app.ai.skill_runtime import RuntimeDependencies, SkillExecutionRequest, SkillRuntime
from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.config.settings import Settings
from backend.app.models import AIWorkProduct, MasterContentItem, WorkflowTask
from backend.app.services.backend_realignment import require_capability
from backend.app.services.intelligence_contracts import IntelligenceContractError


class ContentLibraryDeterministicProvider:
    """Synthetic provider for local acceptance; production uses the shared gateway."""

    def execute_structured(self, request: AIProviderRequest) -> AIProviderResult:
        context = json.loads(request.provider_input).get("context", [])
        citations = [item.get("citation_key") for item in context if item.get("citation_key")] or ["CIT-001"]
        common = {
            "summary": "Synthetic governed Content Library analysis for Owner review.",
            "findings": ["Master Content and current DocumentVersion remain authoritative."],
            "citations": citations[:20],
            "open_questions": [],
            "human_review_required": True,
            "canonical_state_mutated": False,
        }
        if request.schema_name == "content_library_intake_governance_analysis":
            payload = {**common, "candidate_metadata": {}, "review_flags": []}
        elif request.schema_name == "content_library_reuse_applicability_analysis":
            payload = {**common, "recommendations": [], "blockers": [], "confidence": "INSUFFICIENT"}
        elif request.schema_name == "content_library_description_draft":
            payload = {**common, "title": None, "description": "Human review is required before saving a description.", "keywords": [], "draft_only": True}
        else:
            payload = {**common, "analysis_kind": request.schema_name, "impacts": [], "blockers": []}
        return AIProviderResult("synthetic-content-library-intelligence", payload, AIProviderUsage(1, 1, 2))


def _runtime_settings(settings: Settings, provider: Any | None) -> Settings:
    if not isinstance(provider, ContentLibraryDeterministicProvider):
        return settings
    return settings.model_copy(update={
        "ai_feature_enabled": True,
        "ai_external_inference_enabled": True,
        "ai_d4_commissioning_id": "CONTENT-LIBRARY-SYNTHETIC-D4",
        "ai_azure_openai_endpoint": "https://content-library-synthetic.openai.azure.com",
        "ai_uami_client_id": "00000000-0000-0000-0000-000000000001",
        "ai_uami_principal_id": "00000000-0000-0000-0000-000000000002",
        "ai_azure_tenant_id": "00000000-0000-0000-0000-000000000003",
        "ai_max_input_token_upper_bound": 24000,
        "ai_max_output_tokens": 512,
        "ai_max_requests_per_user_per_minute": 100,
        "ai_max_requests_per_user_per_hour": 1000,
        "ai_max_requests_per_project_per_hour": 1000,
        "ai_max_requests_global_per_hour": 10000,
        "ai_max_estimated_cost_usd_per_request": 1.0,
        "ai_max_estimated_cost_usd_per_day": 100.0,
        "ai_input_price_usd_per_1m_tokens": 1.0,
        "ai_output_price_usd_per_1m_tokens": 1.0,
        "ai_pricing_source_reference": "CONTENT-LIBRARY-SYNTHETIC-PRICING",
    })


def _sources(item: MasterContentItem) -> list[dict[str, Any]]:
    if not item.current_document_version_id:
        raise IntelligenceContractError("MASTER_CONTENT_CURRENT_VERSION_REQUIRED")
    return [{
        "key": "master-content-current",
        "context_type": "MASTER_CONTENT",
        "selector": {
            "master_content_item_id": item.id,
            "document_version_id": item.current_document_version_id,
            "content_type": item.content_type,
        },
        "required": True,
    }]


def execute_content_library_intelligence(
    db: Session,
    *,
    item_id: str,
    skill_id: str,
    principal: AuthenticatedPrincipal,
    idempotency_key: str,
    correlation_id: str,
    settings: Settings,
    provider: Any | None = None,
) -> dict[str, Any]:
    item = db.get(MasterContentItem, item_id)
    if item is None:
        raise IntelligenceContractError("MASTER_CONTENT_NOT_FOUND")
    skill = CONTENT_LIBRARY_SKILLS_BY_ID.get(skill_id)
    if skill is None:
        raise IntelligenceContractError("MASTER_CONTENT_INTELLIGENCE_SKILL_NOT_FOUND")
    require_capability(principal.role, "READ_ALL")
    request = SkillExecutionRequest(
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        skill_id=skill.manifest.skill_id,
        skill_version=skill.manifest.version,
        skill_manifest_hash=skill.manifest.manifest_hash,
        purpose="MASTER_CONTENT_INTELLIGENCE",
        execution_mode="INTERACTIVE",
        scope_type="MASTER_CONTENT_ITEM",
        scope_id=item.id,
        target_entity_type="MASTER_CONTENT_ITEM",
        target_entity_id=item.id,
        context_schema_version=CONTENT_LIBRARY_CONTEXT_VERSION,
        policy_version=CONTENT_LIBRARY_POLICY_VERSION,
        sources=tuple(_sources(item)),
    )
    runtime_session = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    result = SkillRuntime(
        registry=SKILL_REGISTRY,
        dependencies=RuntimeDependencies(session_factory=runtime_session),
    ).execute(db, principal, request, settings=_runtime_settings(settings, provider), provider=provider)
    product = db.get(AIWorkProduct, result["work_product_id"])
    if product is None:
        raise IntelligenceContractError("MASTER_CONTENT_INTELLIGENCE_WORK_PRODUCT_NOT_FOUND")
    task = next((row for row in db.scalars(select(WorkflowTask).where(
        WorkflowTask.task_type == "MASTER_CONTENT_INTELLIGENCE_REVIEW",
        WorkflowTask.context_type == "MASTER_CONTENT",
        WorkflowTask.context_id == item.id,
    )).all() if (row.evidence_summary or {}).get("work_product_id") == product.id), None)
    if task is None:
        task = WorkflowTask(
            task_type="MASTER_CONTENT_INTELLIGENCE_REVIEW",
            title=f"Review Content Library Intelligence for {item.ref}",
            description="Review this citation-backed advisory result before taking an ordinary human Content Library action.",
            owner_role="OWNER",
            status="OPEN",
            priority="NORMAL",
            correlation_id=correlation_id,
            task_family="MASTER_CONTENT_INTELLIGENCE",
            context_type="MASTER_CONTENT",
            context_id=item.id,
            blocking=False,
            next_action_code="REVIEW_MASTER_CONTENT_INTELLIGENCE",
            deep_link=f"/dashboard?content={item.id}",
            evidence_summary={"work_product_id": product.id, "human_review_required": True, "canonical_state_mutated": False},
        )
        db.add(task)
        db.commit()
    result.update({
        "review_required": True,
        "review_task_id": task.id,
        "canonical_state_mutated": False,
        "protected_action_count": 0,
    })
    return result


def content_library_intelligence_reviews(db: Session, item_id: str) -> list[dict[str, Any]]:
    rows = db.scalars(select(WorkflowTask).where(
        WorkflowTask.task_type == "MASTER_CONTENT_INTELLIGENCE_REVIEW",
        WorkflowTask.context_type == "MASTER_CONTENT",
        WorkflowTask.context_id == item_id,
    ).order_by(WorkflowTask.created_at.desc())).all()
    return [{
        "task_id": row.id,
        "status": row.status,
        "work_product_id": (row.evidence_summary or {}).get("work_product_id"),
        "human_review_required": True,
        "canonical_state_mutated": False,
    } for row in rows]
