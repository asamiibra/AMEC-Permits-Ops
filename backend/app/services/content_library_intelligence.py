"""Content Library adapter over the shared Intelligence runtime."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..ai.content_library_skill_pack import (
    CONTENT_LIBRARY_CONTEXT_VERSION,
    CONTENT_LIBRARY_POLICY_VERSION,
    CONTENT_LIBRARY_SKILLS_BY_ID,
)
from ..ai.provider import AIProviderRequest, AIProviderResult, AIProviderUsage
from ..ai.skill_registry import SKILL_REGISTRY
from ..ai.skill_runtime import RuntimeDependencies, SkillExecutionRequest, SkillRuntime
from ..api.dependencies import AuthenticatedPrincipal
from ..config.settings import Settings
from ..models import (
    AIWorkProduct,
    AIWorkProductDependency,
    ContentCategory,
    DefinitionEntry,
    IntelligenceCitation,
    IntelligenceReviewDecision,
    MasterContentItem,
    WorkflowTask,
)
from .backend_realignment import require_capability
from .intelligence_foundation import record_module_review_decision
from .intelligence_contracts import IntelligenceContractError


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
        source = next((item.get("projection", {}) for item in context if item.get("projection")), {})
        is_definition = bool(source.get("term"))
        title = source.get("title") or (source.get("term") if is_definition else "Content Library form")
        candidate_metadata = {
            "title": title,
            "category_id": source.get("category_id"),
            "category_label": source.get("category_label") or source.get("category"),
            "source_type_code": source.get("source_type"),
        }
        if source.get("term"):
            candidate_metadata = {"term": source["term"], "category": source.get("category")}
        if request.schema_name == "content_library_intake_governance_analysis":
            payload = {
                **common,
                "candidate_metadata": candidate_metadata,
                "review_flags": ["Confirm category and owner-controlled metadata before saving."],
            }
        elif request.schema_name == "content_library_reuse_applicability_analysis":
            payload = {**common, "recommendations": [], "blockers": [], "confidence": "INSUFFICIENT"}
        elif request.schema_name == "content_library_description_draft":
            payload = {
                **common,
                "title": title,
                "description": f"Governed definition source for {title}. Review and edit this draft before saving." if is_definition else f"Governed form source for {title}. Review and edit this draft before saving.",
                "keywords": ["governed", "definition", "source"] if is_definition else ["governed", "form", "source"],
                "draft_only": True,
            }
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


def _definition_sources(definition: DefinitionEntry) -> list[dict[str, Any]]:
    if not definition.current_revision_id:
        raise IntelligenceContractError("DEFINITION_CURRENT_REVISION_REQUIRED")
    return [{
        "key": "definition-current",
        "context_type": "DEFINITION_REVISION",
        "selector": {"definition_revision_id": definition.current_revision_id},
        "required": True,
    }]


CONTENT_LIBRARY_DRAFT_FIELDS = {"title", "description", "category_id"}


def _review_dependency(db: Session, product: AIWorkProduct, item: MasterContentItem) -> AIWorkProductDependency:
    """Return the exact current source edge required for a human review."""

    if product.state != "CURRENT" or not item.current_document_version_id:
        raise IntelligenceContractError("MASTER_CONTENT_INTELLIGENCE_REVIEW_STALE")
    dependency = db.scalar(select(AIWorkProductDependency).where(
        AIWorkProductDependency.work_product_id == product.id,
        AIWorkProductDependency.dependency_type == "MASTER_CONTENT_VERSION",
        AIWorkProductDependency.dependency_id == item.current_document_version_id,
    ))
    if dependency is None:
        raise IntelligenceContractError("MASTER_CONTENT_INTELLIGENCE_REVIEW_DEPENDENCY_MISSING")
    return dependency


def _definition_review_dependency(db: Session, product: AIWorkProduct, definition: DefinitionEntry) -> AIWorkProductDependency:
    if product.state != "CURRENT" or not definition.current_revision_id:
        raise IntelligenceContractError("DEFINITION_INTELLIGENCE_REVIEW_STALE")
    dependency = db.scalar(select(AIWorkProductDependency).where(
        AIWorkProductDependency.work_product_id == product.id,
        AIWorkProductDependency.dependency_type == "DEFINITION_REVISION",
        AIWorkProductDependency.dependency_id == definition.current_revision_id,
    ))
    if dependency is None:
        raise IntelligenceContractError("DEFINITION_INTELLIGENCE_REVIEW_DEPENDENCY_MISSING")
    return dependency


def _draft_fields(db: Session, item: MasterContentItem, output: dict[str, Any]) -> dict[str, Any]:
    """Derive only server-governed editor fields from a structured work product."""

    fields: dict[str, Any] = {}
    if isinstance(output.get("title"), str) and output["title"].strip():
        fields["title"] = output["title"].strip()
    if isinstance(output.get("description"), str) and output["description"].strip():
        fields["description"] = output["description"].strip()
    metadata = output.get("candidate_metadata")
    if isinstance(metadata, dict):
        category_id = metadata.get("category_id")
        if isinstance(category_id, str) and db.get(ContentCategory, category_id) is not None:
            fields["category_id"] = category_id
        for key in CONTENT_LIBRARY_DRAFT_FIELDS - {"title", "description", "category_id"}:
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                fields[key] = value.strip()
    return fields


def _definition_draft_fields(definition: DefinitionEntry, output: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {}
    if isinstance(output.get("description"), str) and output["description"].strip():
        fields["description"] = output["description"].strip()
    metadata = output.get("candidate_metadata")
    if isinstance(metadata, dict):
        if isinstance(metadata.get("term"), str) and metadata["term"].strip():
            fields["term"] = metadata["term"].strip()
        if isinstance(metadata.get("category"), str) and metadata["category"].strip():
            fields["category"] = metadata["category"].strip()
    return fields


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
        "review_precondition_version": _review_dependency(db, product, item).dependency_version_or_hash,
        "draft_fields": _draft_fields(db, item, result.get("output") or {}),
    })
    return result


def submit_content_library_intelligence_review(
    db: Session,
    *,
    item_id: str,
    work_product_id: str,
    decision: str,
    idempotency_key: str,
    precondition_version: str,
    accepted_fields: dict[str, Any],
    principal: AuthenticatedPrincipal,
    correlation_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    item = db.get(MasterContentItem, item_id)
    product = db.get(AIWorkProduct, work_product_id)
    if item is None or product is None or product.scope_id != item_id or product.owning_module.upper() != "MASTER_CONTENT":
        raise IntelligenceContractError("MASTER_CONTENT_INTELLIGENCE_REVIEW_SCOPE_MISMATCH")
    dependency = _review_dependency(db, product, item)
    if dependency.dependency_version_or_hash != precondition_version:
        raise IntelligenceContractError("MASTER_CONTENT_INTELLIGENCE_REVIEW_STALE")
    require_capability(principal.role, "MASTER_CONTENT_BINDING_WRITE")
    normalized_decision = decision.upper()
    if normalized_decision in {"ACCEPT", "CORRECT"}:
        safe_fields = _draft_fields(db, item, product.structured_output_json or {})
        if set(accepted_fields) - CONTENT_LIBRARY_DRAFT_FIELDS or any(safe_fields.get(key) != value for key, value in accepted_fields.items()):
            raise IntelligenceContractError("MASTER_CONTENT_INTELLIGENCE_REVIEW_FIELD_NOT_OFFERED")
    else:
        accepted_fields = {}
    review = record_module_review_decision(
        db,
        principal=principal,
        owning_module="MASTER_CONTENT",
        review_subject_type="WORK_PRODUCT",
        review_subject_id=product.id,
        decision=normalized_decision,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        authorizing_capability="MASTER_CONTENT_BINDING_WRITE",
        precondition_version=dependency.dependency_version_or_hash,
        work_product_id=product.id,
        context_snapshot_id=product.context_snapshot_id,
        source_currentness_identity={
            "master_content_id": item.id,
            "current_document_version_id": item.current_document_version_id,
            "work_product_state": product.state,
        },
        correction_payload=accepted_fields or None,
        reason=reason,
    )
    task = next((row for row in db.scalars(select(WorkflowTask).where(
        WorkflowTask.task_type == "MASTER_CONTENT_INTELLIGENCE_REVIEW",
        WorkflowTask.context_type == "MASTER_CONTENT",
        WorkflowTask.context_id == item.id,
    )).all() if (row.evidence_summary or {}).get("work_product_id") == product.id), None)
    if task and normalized_decision in {"ACCEPT", "CORRECT", "REJECT"}:
        task.status = "COMPLETED"
        task.next_action_code = "MASTER_CONTENT_INTELLIGENCE_REVIEW_RECORDED"
        task.evidence_summary = {
            **(task.evidence_summary or {}),
            "review_decision_id": review.id,
            "decision": normalized_decision,
            "accepted_fields": accepted_fields,
            "canonical_state_mutated": False,
        }
    db.commit()
    return {
        "decision_id": review.id,
        "decision": review.decision,
        "work_product_id": product.id,
        "accepted_fields": accepted_fields,
        "canonical_state_mutated": False,
        "protected_action_count": 0,
    }


def execute_definition_intelligence(
    db: Session,
    *,
    definition_id: str,
    skill_id: str,
    principal: AuthenticatedPrincipal,
    idempotency_key: str,
    correlation_id: str,
    settings: Settings,
    provider: Any | None = None,
) -> dict[str, Any]:
    definition = db.get(DefinitionEntry, definition_id)
    if definition is None:
        raise IntelligenceContractError("DEFINITION_NOT_FOUND")
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
        scope_type="DEFINITION_ENTRY",
        scope_id=definition.id,
        target_entity_type="DEFINITION_ENTRY",
        target_entity_id=definition.id,
        context_schema_version=CONTENT_LIBRARY_CONTEXT_VERSION,
        policy_version=CONTENT_LIBRARY_POLICY_VERSION,
        sources=tuple(_definition_sources(definition)),
    )
    runtime_session = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    result = SkillRuntime(
        registry=SKILL_REGISTRY,
        dependencies=RuntimeDependencies(session_factory=runtime_session),
    ).execute(db, principal, request, settings=_runtime_settings(settings, provider), provider=provider)
    product = db.get(AIWorkProduct, result["work_product_id"])
    if product is None:
        raise IntelligenceContractError("DEFINITION_INTELLIGENCE_WORK_PRODUCT_NOT_FOUND")
    task = next((row for row in db.scalars(select(WorkflowTask).where(
        WorkflowTask.task_type == "MASTER_CONTENT_INTELLIGENCE_REVIEW",
        WorkflowTask.context_type == "DEFINITION_ENTRY",
        WorkflowTask.context_id == definition.id,
    )).all() if (row.evidence_summary or {}).get("work_product_id") == product.id), None)
    if task is None:
        task = WorkflowTask(
            task_type="MASTER_CONTENT_INTELLIGENCE_REVIEW",
            title=f"Review Content Library Intelligence for {definition.term}",
            description="Review this citation-backed advisory result before taking an ordinary human Definition action.",
            owner_role="OWNER",
            status="OPEN",
            priority="NORMAL",
            correlation_id=correlation_id,
            task_family="MASTER_CONTENT_INTELLIGENCE",
            context_type="DEFINITION_ENTRY",
            context_id=definition.id,
            blocking=False,
            next_action_code="REVIEW_MASTER_CONTENT_INTELLIGENCE",
            deep_link=f"/dashboard?definition={definition.id}",
            evidence_summary={"work_product_id": product.id, "human_review_required": True, "canonical_state_mutated": False},
        )
        db.add(task)
        db.commit()
    result.update({
        "review_required": True,
        "review_task_id": task.id,
        "canonical_state_mutated": False,
        "protected_action_count": 0,
        "review_precondition_version": _definition_review_dependency(db, product, definition).dependency_version_or_hash,
        "draft_fields": _definition_draft_fields(definition, result.get("output") or {}),
    })
    return result


def submit_definition_intelligence_review(
    db: Session,
    *,
    definition_id: str,
    work_product_id: str,
    decision: str,
    idempotency_key: str,
    precondition_version: str,
    accepted_fields: dict[str, Any],
    principal: AuthenticatedPrincipal,
    correlation_id: str,
    reason: str | None = None,
) -> dict[str, Any]:
    definition = db.get(DefinitionEntry, definition_id)
    product = db.get(AIWorkProduct, work_product_id)
    if definition is None or product is None or product.scope_id != definition_id or product.owning_module.upper() != "MASTER_CONTENT":
        raise IntelligenceContractError("DEFINITION_INTELLIGENCE_REVIEW_SCOPE_MISMATCH")
    dependency = _definition_review_dependency(db, product, definition)
    if dependency.dependency_version_or_hash != precondition_version:
        raise IntelligenceContractError("DEFINITION_INTELLIGENCE_REVIEW_STALE")
    require_capability(principal.role, "MASTER_CONTENT_BINDING_WRITE")
    normalized_decision = decision.upper()
    if normalized_decision in {"ACCEPT", "CORRECT"}:
        safe_fields = _definition_draft_fields(definition, product.structured_output_json or {})
        if set(accepted_fields) - {"term", "description", "category"} or any(safe_fields.get(key) != value for key, value in accepted_fields.items()):
            raise IntelligenceContractError("DEFINITION_INTELLIGENCE_REVIEW_FIELD_NOT_OFFERED")
    else:
        accepted_fields = {}
    review = record_module_review_decision(
        db,
        principal=principal,
        owning_module="MASTER_CONTENT",
        review_subject_type="WORK_PRODUCT",
        review_subject_id=product.id,
        decision=normalized_decision,
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        authorizing_capability="MASTER_CONTENT_BINDING_WRITE",
        precondition_version=dependency.dependency_version_or_hash,
        work_product_id=product.id,
        context_snapshot_id=product.context_snapshot_id,
        source_currentness_identity={"definition_id": definition.id, "current_revision_id": definition.current_revision_id, "work_product_state": product.state},
        correction_payload=accepted_fields or None,
        reason=reason,
    )
    task = next((row for row in db.scalars(select(WorkflowTask).where(
        WorkflowTask.task_type == "MASTER_CONTENT_INTELLIGENCE_REVIEW",
        WorkflowTask.context_type == "DEFINITION_ENTRY",
        WorkflowTask.context_id == definition.id,
    )).all() if (row.evidence_summary or {}).get("work_product_id") == product.id), None)
    if task and normalized_decision in {"ACCEPT", "CORRECT", "REJECT"}:
        task.status = "COMPLETED"
        task.next_action_code = "MASTER_CONTENT_INTELLIGENCE_REVIEW_RECORDED"
        task.evidence_summary = {**(task.evidence_summary or {}), "review_decision_id": review.id, "decision": normalized_decision, "accepted_fields": accepted_fields, "canonical_state_mutated": False}
    db.commit()
    return {"decision_id": review.id, "decision": review.decision, "work_product_id": product.id, "accepted_fields": accepted_fields, "canonical_state_mutated": False, "protected_action_count": 0}


def content_library_intelligence_reviews(db: Session, item_id: str, *, context_type: str = "MASTER_CONTENT") -> list[dict[str, Any]]:
    rows = db.scalars(select(WorkflowTask).where(
        WorkflowTask.task_type == "MASTER_CONTENT_INTELLIGENCE_REVIEW",
        WorkflowTask.context_type == context_type,
        WorkflowTask.context_id == item_id,
    ).order_by(WorkflowTask.created_at.desc())).all()
    decisions = {
        row.work_product_id: row
        for row in db.scalars(select(IntelligenceReviewDecision).where(
            IntelligenceReviewDecision.work_product_id.in_([
                (task.evidence_summary or {}).get("work_product_id") for task in rows if (task.evidence_summary or {}).get("work_product_id")
            ])
        )).all()
    }
    return [{
        "task_id": row.id,
        "status": row.status,
        "work_product_id": (row.evidence_summary or {}).get("work_product_id"),
        "human_review_required": True,
        "canonical_state_mutated": False,
        "decision": decisions.get((row.evidence_summary or {}).get("work_product_id")).decision if decisions.get((row.evidence_summary or {}).get("work_product_id")) else None,
    } for row in rows]


def _persisted_product_payload(db: Session, product: AIWorkProduct, *, context_type: str, entity: MasterContentItem | DefinitionEntry) -> dict[str, Any]:
    """Expose a reload-safe, reviewable work product without granting authority."""

    citations = db.scalars(select(IntelligenceCitation).where(
        IntelligenceCitation.work_product_id == product.id,
    ).order_by(IntelligenceCitation.ordinal)).all()
    dependency_type = "DEFINITION_REVISION" if context_type == "DEFINITION_ENTRY" else "MASTER_CONTENT_VERSION"
    dependency = db.scalar(select(AIWorkProductDependency).where(
        AIWorkProductDependency.work_product_id == product.id,
        AIWorkProductDependency.dependency_type == dependency_type,
    ))
    decision = db.scalar(select(IntelligenceReviewDecision).where(
        IntelligenceReviewDecision.work_product_id == product.id,
    ).order_by(IntelligenceReviewDecision.decided_at.desc()))
    output = product.structured_output_json or {}
    draft_fields = (
        _definition_draft_fields(entity, output)
        if context_type == "DEFINITION_ENTRY"
        else _draft_fields(db, entity, output)
    )
    return {
        "work_product_id": product.id,
        "skill_id": product.skill_id,
        "skill_version": product.skill_version,
        "skill_manifest_hash": product.skill_manifest_hash,
        "status": "SUCCEEDED",
        "state": product.state,
        "currentness": product.state,
        "stale_reason": product.stale_reason,
        "created_at": product.created_at.isoformat(),
        "output_class": product.output_class,
        "output": output,
        "output_hash": product.output_hash,
        "citations": [{
            "ordinal": citation.ordinal,
            "source_type": citation.source_type,
            "source_id": citation.source_id,
            "source_version_or_hash": citation.source_version_or_hash,
            "locator_json": citation.locator_json,
        } for citation in citations],
        "citation_count": product.citation_count,
        "review_required": True,
        "review_precondition_version": dependency.dependency_version_or_hash if dependency else None,
        "draft_fields": draft_fields,
        "decision": decision.decision if decision else None,
        "canonical_state_mutated": False,
        "protected_action_count": 0,
    }


def content_library_intelligence_products(db: Session, item_id: str, *, context_type: str = "MASTER_CONTENT") -> list[dict[str, Any]]:
    """Return persisted Content Library intelligence, including stale history."""

    if context_type == "DEFINITION_ENTRY":
        entity = db.get(DefinitionEntry, item_id)
        scope_type = "DEFINITION_ENTRY"
    else:
        entity = db.get(MasterContentItem, item_id)
        scope_type = "MASTER_CONTENT_ITEM"
    if entity is None:
        return []
    products = db.scalars(select(AIWorkProduct).where(
        AIWorkProduct.scope_type == scope_type,
        AIWorkProduct.scope_id == item_id,
        AIWorkProduct.owning_module.in_(["master_content", "MASTER_CONTENT"]),
    ).order_by(AIWorkProduct.created_at.desc()).limit(50)).all()
    return [_persisted_product_payload(db, product, context_type=context_type, entity=entity) for product in products]
