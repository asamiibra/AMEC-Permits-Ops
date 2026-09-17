"""Contract-owned orchestration over the shared governed SkillRuntime."""

from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from ..ai.contract_skills import CONTRACT_CONTEXT_VERSION, CONTRACT_POLICY_VERSION, CONTRACT_SKILLS_BY_ID
from ..ai.provider import AIProviderRequest, AIProviderResult, AIProviderUsage
from ..ai.skill_runtime import RuntimeDependencies, SkillExecutionRequest, SkillRuntime
from ..api.dependencies import AuthenticatedPrincipal
from ..config.settings import Settings
from ..models import AIWorkProduct, Contract, ContractAdminEvidence, ContextDependency, ContractRevision, WorkflowTask
from .backend_realignment import require_capability
from .intelligence_contracts import IntelligenceContractError
from .intelligence_foundation import record_module_review_decision
from ..ai.skill_registry import SKILL_REGISTRY


class ContractDeterministicProvider:
    """Synthetic provider for local/hosted portability lanes only."""

    def execute_structured(self, request: AIProviderRequest) -> AIProviderResult:
        context = json.loads(request.provider_input).get("context", [])
        citations = [item.get("citation_key") for item in context if item.get("citation_key")] or ["CIT-001"]
        return AIProviderResult(
            f"synthetic-contract-{request.schema_name}",
            {
                "summary": "Synthetic governed Contract Intelligence analysis for human review.",
                "findings": ["Contract canonical state remains authoritative; this result is advisory."],
                "citations": citations[:20],
                "open_questions": [],
                "currentness_notes": ["Inputs were bound to the current Contract revision and current evidence versions."],
                "candidate_actions": ["Review the finding in the Contract workspace."],
                "human_review_required": True,
                "canonical_state_mutated": False,
                "protected_action_count": 0,
            },
            AIProviderUsage(1, 1, 2),
        )


def _runtime_settings(settings: Settings, provider: Any | None) -> Settings:
    if not isinstance(provider, ContractDeterministicProvider):
        return settings
    return settings.model_copy(update={
        "ai_feature_enabled": True,
        "ai_external_inference_enabled": True,
        "ai_d4_commissioning_id": "CONTRACT-SYNTHETIC-D4",
        "ai_azure_openai_endpoint": "https://contract-synthetic.openai.azure.com",
        "ai_uami_client_id": "00000000-0000-0000-0000-000000000001",
        "ai_uami_principal_id": "00000000-0000-0000-0000-000000000002",
        "ai_azure_tenant_id": "00000000-0000-0000-0000-000000000003",
        "ai_max_input_token_upper_bound": 8192,
        "ai_max_output_tokens": 512,
        "ai_max_requests_per_user_per_minute": 100,
        "ai_max_requests_per_user_per_hour": 1000,
        "ai_max_requests_per_project_per_hour": 1000,
        "ai_max_requests_global_per_hour": 10000,
        "ai_max_estimated_cost_usd_per_request": 1.0,
        "ai_max_estimated_cost_usd_per_day": 100.0,
        "ai_input_price_usd_per_1m_tokens": 1.0,
        "ai_output_price_usd_per_1m_tokens": 1.0,
        "ai_pricing_source_reference": "CONTRACT-SYNTHETIC-PRICING",
    })


def _contract_sources(db: Session, contract: Contract) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = [{
        "key": "contract-current-revision",
        "context_type": "DOMAIN_ENTITY_REVISION",
        "selector": {"entity_type": "CONTRACT", "entity_id": contract.id},
        "required": True,
    }]
    seen: set[str] = set()
    evidence = db.scalars(
        select(ContractAdminEvidence)
        .where(ContractAdminEvidence.contract_id == contract.id, ContractAdminEvidence.document_version_id.is_not(None))
        .order_by(ContractAdminEvidence.recorded_at.desc())
    ).all()
    for item in evidence:
        version_id = item.document_version_id
        if not version_id or version_id in seen:
            continue
        seen.add(version_id)
        sources.append({
            "key": f"document-{version_id}",
            "context_type": "DOCUMENT_VERSION",
            "selector": {"document_version_id": version_id},
            "required": False,
        })
    return sources


def _ensure_review_task(db: Session, contract: Contract, work_product: AIWorkProduct, correlation_id: str) -> WorkflowTask:
    tasks = db.scalars(select(WorkflowTask).where(
        WorkflowTask.task_type == "CONTRACT_INTELLIGENCE_REVIEW",
        WorkflowTask.context_type == "CONTRACT",
        WorkflowTask.context_id == contract.id,
    )).all()
    for task in tasks:
        if isinstance(task.evidence_summary, dict) and task.evidence_summary.get("work_product_id") == work_product.id:
            return task
    task = WorkflowTask(
        project_id=contract.project_id,
        task_type="CONTRACT_INTELLIGENCE_REVIEW",
        title="Review Contract Intelligence result",
        description="Review the citation-backed Contract candidate; this does not approve, accept, sign, activate, invoice, or mutate Contract state.",
        owner_role="OWNER",
        status="OPEN",
        priority="NORMAL",
        correlation_id=correlation_id,
        task_family="CONTRACT_INTELLIGENCE",
        context_type="CONTRACT",
        context_id=contract.id,
        blocking=False,
        next_action_code="REVIEW_CONTRACT_INTELLIGENCE",
        deep_link=f"/contract-mobilization/contracts/{contract.id}",
        evidence_summary={"work_product_id": work_product.id, "human_review_required": True, "canonical_state_mutated": False},
    )
    db.add(task)
    db.flush()
    return task


def execute_contract_intelligence(
    db: Session,
    *,
    contract_id: str,
    skill_id: str,
    principal: AuthenticatedPrincipal,
    idempotency_key: str,
    correlation_id: str,
    settings: Settings,
    provider: Any | None = None,
) -> dict[str, Any]:
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise IntelligenceContractError("CONTRACT_NOT_FOUND")
    skill = CONTRACT_SKILLS_BY_ID.get(skill_id)
    if skill is None:
        raise IntelligenceContractError("CONTRACT_INTELLIGENCE_SKILL_NOT_FOUND")
    if not principal.user_id:
        raise IntelligenceContractError("CONTRACT_INTELLIGENCE_ACTOR_REQUIRED")
    require_capability(principal.role, "CONTRACT_READ")
    request = SkillExecutionRequest(
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        skill_id=skill.manifest.skill_id,
        skill_version=skill.manifest.version,
        skill_manifest_hash=skill.manifest.manifest_hash,
        purpose=skill.manifest.purpose,
        execution_mode="INTERACTIVE",
        scope_type="CONTRACT",
        scope_id=contract.id,
        project_id=contract.project_id,
        target_entity_type="CONTRACT",
        target_entity_id=contract.id,
        context_schema_version=CONTRACT_CONTEXT_VERSION,
        policy_version=CONTRACT_POLICY_VERSION,
        sources=tuple(_contract_sources(db, contract)),
    )
    runtime_session = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    result = SkillRuntime(
        registry=SKILL_REGISTRY,
        dependencies=RuntimeDependencies(session_factory=runtime_session),
    ).execute(db, principal, request, settings=_runtime_settings(settings, provider), provider=provider)
    work_product = db.get(AIWorkProduct, result["work_product_id"])
    if work_product is None:
        raise IntelligenceContractError("CONTRACT_INTELLIGENCE_WORK_PRODUCT_NOT_FOUND")
    task = _ensure_review_task(db, contract, work_product, correlation_id)
    db.commit()
    result.update({
        "current_actionable": str(work_product.state) == "CURRENT",
        "review_required": True,
        "review_task_id": task.id,
        "review_capability": "CONTRACT_REVIEW_AUTHORITY",
        "canonical_state_mutated": False,
        "protected_action_count": 0,
    })
    return result


def contract_intelligence_reviews(db: Session, contract_id: str) -> list[dict[str, Any]]:
    tasks = db.scalars(select(WorkflowTask).where(
        WorkflowTask.task_type == "CONTRACT_INTELLIGENCE_REVIEW",
        WorkflowTask.context_type == "CONTRACT",
        WorkflowTask.context_id == contract_id,
    ).order_by(WorkflowTask.created_at.desc())).all()
    return [{
        "task_id": task.id,
        "status": task.status,
        "next_action_code": task.next_action_code,
        "work_product_id": (task.evidence_summary or {}).get("work_product_id"),
        "human_review_required": True,
        "canonical_state_mutated": False,
    } for task in tasks]


def submit_contract_intelligence_review(
    db: Session,
    *,
    contract_id: str,
    work_product_id: str,
    decision: str,
    idempotency_key: str,
    principal: AuthenticatedPrincipal,
    correlation_id: str,
    reason: str,
) -> dict[str, Any]:
    contract = db.get(Contract, contract_id)
    product = db.get(AIWorkProduct, work_product_id)
    if contract is None or product is None or product.scope_id != contract.id or product.owning_module.upper() != "CONTRACT":
        raise IntelligenceContractError("CONTRACT_INTELLIGENCE_REVIEW_SCOPE_MISMATCH")
    require_capability(principal.role, "CONTRACT_REVIEW_AUTHORITY")
    dependency = db.scalar(select(ContextDependency).where(
        ContextDependency.context_snapshot_id == product.context_snapshot_id,
        ContextDependency.dependency_type == "DOMAIN_ENTITY_REVISION",
        ContextDependency.dependency_id == contract.id,
    ))
    if dependency is None:
        raise IntelligenceContractError("CONTRACT_INTELLIGENCE_REVIEW_DEPENDENCY_MISSING")
    review = record_module_review_decision(
        db, principal=principal, owning_module="CONTRACT",
        review_subject_type="WORK_PRODUCT", review_subject_id=product.id,
        decision=decision.upper(), idempotency_key=idempotency_key,
        correlation_id=correlation_id, authorizing_capability="CONTRACT_REVIEW_AUTHORITY",
        precondition_version=dependency.dependency_version_or_hash,
        work_product_id=product.id, context_snapshot_id=product.context_snapshot_id,
        source_currentness_identity={"contract_id": contract.id, "work_product_state": product.state},
        reason=reason,
    )
    task = next((item for item in db.scalars(select(WorkflowTask).where(
        WorkflowTask.task_type == "CONTRACT_INTELLIGENCE_REVIEW",
        WorkflowTask.context_id == contract.id,
    )).all() if (item.evidence_summary or {}).get("work_product_id") == product.id), None)
    if task and decision.upper() in {"ACCEPT", "CORRECT", "REJECT"}:
        task.status = "COMPLETED"
        task.next_action_code = "CONTRACT_INTELLIGENCE_REVIEW_RECORDED"
    db.commit()
    return {"decision_id": review.id, "decision": review.decision, "work_product_id": product.id, "canonical_state_mutated": False, "protected_action_count": 0}
