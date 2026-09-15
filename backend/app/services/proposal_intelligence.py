"""Proposal-owned P08 Intelligence orchestration and review boundary."""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from typing import Any
from uuid import uuid4

from sqlalchemy import select, true
from sqlalchemy.orm import Session, sessionmaker

from backend.app.ai.provider import AIProviderRequest, AIProviderResult, AIProviderUsage
from backend.app.ai.skill_registry import PROPOSAL_SKILLS, SkillDefinition
from backend.app.ai.skill_runtime import RuntimeDependencies, SkillExecutionRequest, SkillRuntime
from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.config.settings import Settings
from backend.app.models import (
    AIWorkProduct, CandidateAssertion, ContextDependency, ContextSnapshot,
    IntelligenceReviewDecision, Opportunity, ProposalAcceptedRevision,
    ProposalIntelligenceReviewBinding, User, WorkflowTask, WorkflowTaskStatus,
)
from backend.app.services.backend_realignment import persona_for_role, require_capability
from backend.app.services.intelligence_contracts import IntelligenceContractError, stable_hash
from backend.app.services.intelligence_foundation import (
    dependency_current, promote_verified_assertion_from_decision,
    register_eval_pack, record_module_review_decision, revalidate_snapshot, invalidate_dependency,
)


P08_POLICY_VERSION = "PROPOSAL_INTELLIGENCE-1.0"
P08_REVIEW_CAPABILITY = "BD_PROPOSAL_INTELLIGENCE_REVIEW"
P08_EVAL_PACK_ID = "proposal-intelligence-v1"
P08_EVAL_PACK_VERSION = "1.0.0"
P08_CRITICAL_CASES = (
    "cross-project", "wrong-persona", "missing-capability", "stale-revision", "stale-document",
    "stale-verified-assertion", "stale-master-content", "stale-policy", "source-mismatch",
    "citation-mismatch", "malformed-output", "trust-floor", "sensitivity", "protected-action",
    "policy-spoof", "skill-spoof", "provider-spoof", "prompt-injection", "provider-failure",
    "context-race", "stale-review", "duplicate-review", "conflicting-review", "corrected-candidate",
    "analysis-not-truth", "unrelated-dependency-current",
)
P08_EVAL_PACK_HASH = stable_hash({"eval_pack_id": P08_EVAL_PACK_ID, "version": P08_EVAL_PACK_VERSION, "owning_module": "proposal", "critical_case_policy": "ALL_SECURITY_CURRENTNESS_AUTHORITY_CRITICAL", "acceptance_threshold_policy": "CRITICAL_100_PERCENT_NO_SKIPS"})
OPERATION_TO_SKILL = {
    "intake-analysis": "proposal.intake-analysis",
    "scope-technical-analysis": "proposal.scope-technical-analysis",
    "lpo-variance-analysis": "proposal.lpo-variance-analysis",
    "readiness-explanation": "proposal.readiness-explanation",
}
_SKILLS = {item.manifest.skill_id: item for item in PROPOSAL_SKILLS}
_REVIEW_PERSONA_BY_SKILL = {
    "proposal.intake-analysis": "BUSINESS_DEVELOPMENT",
    "proposal.scope-technical-analysis": "ENGINEERING",
    "proposal.lpo-variance-analysis": "BUSINESS_DEVELOPMENT",
    "proposal.readiness-explanation": "BUSINESS_DEVELOPMENT",
}


def _review_persona_for_work_product(work_product: AIWorkProduct) -> str:
    """Return the accountable module reviewer for this analysis skill."""
    return _REVIEW_PERSONA_BY_SKILL.get(work_product.skill_id, "BUSINESS_DEVELOPMENT")


def _allowed_review_personas(binding: ProposalIntelligenceReviewBinding) -> set[str]:
    """Keep Owner override explicit while preserving module reviewer routing."""
    return {"OWNER", "SYSTEM_ADMIN", binding.required_persona}


def _runtime_settings(settings: Settings, provider: Any | None) -> Settings:
    if not isinstance(provider, ProposalDeterministicProvider):
        return settings
    # Synthetic API/browser acceptance still traverses the shared D4 gateway,
    # but never contacts Azure. These fixed binding values make that boundary
    # explicit without weakening production settings validation.
    return settings.model_copy(update={
        "ai_feature_enabled": True,
        "ai_external_inference_enabled": True,
        "ai_d4_commissioning_id": "P08-SYNTHETIC-D4",
        "ai_azure_openai_endpoint": "https://p08-synthetic.openai.azure.com",
        "ai_uami_client_id": "00000000-0000-0000-0000-000000000001",
        "ai_uami_principal_id": "00000000-0000-0000-0000-000000000002",
        "ai_azure_tenant_id": "00000000-0000-0000-0000-000000000003",
        "ai_d3_project_ids": ("synthetic-proposal",),
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
        "ai_pricing_source_reference": "P08-SYNTHETIC-PRICING",
    })


def _accepted(db: Session, proposal_id: str) -> ProposalAcceptedRevision:
    rows = db.scalars(select(ProposalAcceptedRevision).where(
        ProposalAcceptedRevision.proposal_id == proposal_id,
        ProposalAcceptedRevision.status == "ACCEPTED",
    ).order_by(ProposalAcceptedRevision.revision_number.desc())).all()
    if len(rows) != 1:
        raise IntelligenceContractError("PROPOSAL_ACCEPTED_REVISION_CURRENTNESS_UNRESOLVED")
    return rows[0]


def _revision_dependency(proposal: Opportunity, revision: ProposalAcceptedRevision) -> dict[str, Any]:
    return {
        "domain_entity": "PROPOSAL",
        "accepted_revision_id": revision.id,
        "accepted_revision_number": revision.revision_number,
        "accepted_revision_hash": revision.content_hash,
    }


def _principal(db: Session, principal: AuthenticatedPrincipal) -> AuthenticatedPrincipal:
    if not principal.user_id:
        user = db.scalar(select(User).where(User.active == true(), User.role == principal.role).order_by(User.id))
        if user is not None:
            return replace(principal, user_id=user.id, office_id=user.office_id)
    if not principal.user_id:
        raise IntelligenceContractError("INTELLIGENCE_REVIEW_AUTHENTICATED_PRINCIPAL_REQUIRED")
    return principal


def _skill(operation: str) -> SkillDefinition:
    try:
        return _SKILLS[OPERATION_TO_SKILL[operation]]
    except KeyError as exc:
        raise IntelligenceContractError("PROPOSAL_INTELLIGENCE_OPERATION_UNSUPPORTED") from exc


class ProposalDeterministicProvider:
    """Synthetic provider used only by the P08 test/runtime environment."""

    def execute_structured(self, request: AIProviderRequest) -> AIProviderResult:
        context = json.loads(request.provider_input).get("context", [])
        item = context[0] if context else {}
        projection = item.get("projection", {})
        citation = ["CIT-001"]
        name = request.schema_name
        if name == "proposal_intake_analysis":
            payload = {"summary": "Synthetic governed Proposal intake analysis.", "missing_information": [], "contradictions": [], "unresolved_candidate_facts": [], "source_currentness_issues": [], "citation_keys": citation}
        elif name == "proposal_scope_technical_analysis":
            payload = {"summary": "Synthetic governed technical scope recommendation.", "assumptions": [], "exclusions": [], "unresolved_technical_questions": [], "eligibility_dependencies": [], "recommendation_notes": ["Human BD / Engineering review remains required."], "citation_keys": citation}
        elif name == "proposal_lpo_variance_analysis":
            payload = {"summary": "Synthetic typed LPO comparison; no adjudication performed.", "accepted_revision_id": projection.get("accepted_revision_id", "unresolved"), "lpo_evidence_id": projection.get("lpo_evidence_id"), "differences": [], "citation_keys": citation}
        else:
            payload = {"explanation": "Synthetic governed Proposal readiness explanation.", "blockers": [], "stale_dependencies": [], "missing_information": [], "next_permissible_human_actions": ["Review the analysis inside the Proposal workspace."], "citation_keys": citation}
        return AIProviderResult(f"synthetic-proposal-{name}", payload, AIProviderUsage(1, 1, 2))


@dataclass(frozen=True)
class ProposalContext:
    proposal: Opportunity
    accepted_revision: ProposalAcceptedRevision
    skill: SkillDefinition


def build_proposal_context(db: Session, *, proposal_id: str, operation: str, principal: AuthenticatedPrincipal) -> ProposalContext:
    principal = _principal(db, principal)
    proposal = db.get(Opportunity, proposal_id)
    if proposal is None:
        raise IntelligenceContractError("PROPOSAL_NOT_FOUND")
    accepted = _accepted(db, proposal.id)
    return ProposalContext(proposal=proposal, accepted_revision=accepted, skill=_skill(operation))


def execute_proposal_intelligence(
    db: Session, *, proposal_id: str, operation: str, principal: AuthenticatedPrincipal,
    idempotency_key: str, correlation_id: str, settings: Settings, provider: Any | None = None,
) -> dict[str, Any]:
    principal = _principal(db, principal)
    context = build_proposal_context(db, proposal_id=proposal_id, operation=operation, principal=principal)
    register_eval_pack(
        db, eval_pack_id=P08_EVAL_PACK_ID, version=P08_EVAL_PACK_VERSION, owning_module="proposal",
        critical_case_policy="ALL_SECURITY_CURRENTNESS_AUTHORITY_CRITICAL",
        acceptance_threshold_policy="CRITICAL_100_PERCENT_NO_SKIPS",
    )
    proposal = context.proposal
    request = SkillExecutionRequest(
        idempotency_key=idempotency_key, correlation_id=correlation_id,
        skill_id=context.skill.manifest.skill_id, skill_version=context.skill.manifest.version,
        skill_manifest_hash=context.skill.manifest.manifest_hash, purpose="PROPOSAL_INTELLIGENCE",
        execution_mode="INTERACTIVE", scope_type="PROPOSAL", scope_id=proposal.id,
        project_id=proposal.project_id, target_entity_type="PROPOSAL", target_entity_id=proposal.id,
        context_schema_version="proposal-context-v1", policy_version=P08_POLICY_VERSION,
        sources=({"key": "proposal-accepted-revision", "context_type": "DOMAIN_ENTITY_REVISION", "selector": {"entity_type": "PROPOSAL", "entity_id": proposal.id}},),
    )
    # Proposal API execution uses the request transaction's configured
    # database. The shared runtime remains the sole execution path, while a
    # short-lived sibling session keeps reservation/finalization independent
    # without falling back to the process-default database.
    runtime_session = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    result = SkillRuntime(dependencies=RuntimeDependencies(session_factory=runtime_session)).execute(db, principal, request, settings=_runtime_settings(settings, provider), provider=provider)
    work_product = db.get(AIWorkProduct, result["work_product_id"])
    if work_product is None:
        raise IntelligenceContractError("PROPOSAL_INTELLIGENCE_WORK_PRODUCT_NOT_FOUND")
    _create_work_review(db, proposal=proposal, revision=context.accepted_revision, work_product=work_product, correlation_id=correlation_id)
    db.commit()
    result["current_actionable"] = str(work_product.state) == "CURRENT"
    result["review_actionable"] = True
    result["review_required_capability"] = P08_REVIEW_CAPABILITY
    return result


def _create_work_review(db: Session, *, proposal: Opportunity, revision: ProposalAcceptedRevision, work_product: AIWorkProduct, correlation_id: str) -> ProposalIntelligenceReviewBinding:
    existing = db.scalar(select(ProposalIntelligenceReviewBinding).where(ProposalIntelligenceReviewBinding.work_product_id == work_product.id))
    if existing:
        return existing
    task = WorkflowTask(
        task_type="PROPOSAL_INTELLIGENCE_REVIEW", title="Review Proposal Intelligence result",
        description="Review the structured Proposal analysis; this does not authorize a protected Proposal action.",
        owner_role=_review_persona_for_work_product(work_product), status=WorkflowTaskStatus.OPEN, priority="NORMAL",
        correlation_id=correlation_id, task_family="PROPOSAL_INTELLIGENCE", context_type="PROPOSAL",
        context_id=proposal.id, blocking=False, next_action_code="REVIEW_PROPOSAL_INTELLIGENCE",
        deep_link=f"/proposals/{proposal.id}", evidence_summary={"work_product_id": work_product.id},
    )
    db.add(task)
    db.flush()
    dependency = db.scalar(select(ContextDependency).where(
        ContextDependency.context_snapshot_id == work_product.context_snapshot_id,
        ContextDependency.dependency_type == "DOMAIN_ENTITY_REVISION",
        ContextDependency.dependency_id == proposal.id,
    ))
    if dependency is None:
        raise IntelligenceContractError("PROPOSAL_INTELLIGENCE_REVISION_DEPENDENCY_MISSING")
    binding = ProposalIntelligenceReviewBinding(
        workflow_task_id=task.id, proposal_id=proposal.id, review_subject_type="WORK_PRODUCT",
        review_subject_id=work_product.id, work_product_id=work_product.id,
        context_snapshot_id=work_product.context_snapshot_id, dependency_type=dependency.dependency_type,
        dependency_id=dependency.dependency_id, dependency_version_or_hash=dependency.dependency_version_or_hash,
        required_persona=_review_persona_for_work_product(work_product), required_capability=P08_REVIEW_CAPABILITY,
        correlation_id=correlation_id, idempotency_key=f"proposal-review:{work_product.id}",
        precondition_version=dependency.dependency_version_or_hash, actionable=True,
    )
    db.add(binding)
    db.flush()
    return binding


def create_candidate_review(
    db: Session, *, proposal_id: str, candidate_id: str, principal: AuthenticatedPrincipal,
    correlation_id: str,
) -> ProposalIntelligenceReviewBinding:
    principal = _principal(db, principal)
    proposal = db.get(Opportunity, proposal_id)
    candidate = db.get(CandidateAssertion, candidate_id)
    if proposal is None or candidate is None or candidate.scope_id != proposal.id or (candidate.target_module and candidate.target_module.lower() != "proposal"):
        raise IntelligenceContractError("PROPOSAL_REVIEW_SCOPE_MISMATCH")
    existing = db.scalar(select(ProposalIntelligenceReviewBinding).where(ProposalIntelligenceReviewBinding.candidate_assertion_id == candidate.id))
    if existing:
        return existing
    task = WorkflowTask(
        task_type="PROPOSAL_INTELLIGENCE_CANDIDATE_REVIEW", title="Review Proposal candidate fact",
        description="Review the candidate fact; Accept/Correct creates a shared VerifiedAssertion only through the human decision command.",
        owner_role="BUSINESS_DEVELOPMENT", status=WorkflowTaskStatus.OPEN, priority="NORMAL",
        correlation_id=correlation_id, task_family="PROPOSAL_INTELLIGENCE", context_type="PROPOSAL",
        context_id=proposal.id, blocking=False, next_action_code="REVIEW_PROPOSAL_CANDIDATE",
        deep_link=f"/proposals/{proposal.id}", evidence_summary={"candidate_assertion_id": candidate.id},
    )
    db.add(task)
    db.flush()
    binding = ProposalIntelligenceReviewBinding(
        workflow_task_id=task.id, proposal_id=proposal.id, review_subject_type="CANDIDATE_ASSERTION",
        review_subject_id=candidate.id, candidate_assertion_id=candidate.id,
        dependency_type="CANDIDATE_ASSERTION", dependency_id=candidate.id,
        dependency_version_or_hash=candidate.value_hash, required_persona="BUSINESS_DEVELOPMENT",
        required_capability=P08_REVIEW_CAPABILITY, correlation_id=correlation_id,
        idempotency_key=f"proposal-candidate-review:{candidate.id}", precondition_version=candidate.value_hash,
        actionable=True,
    )
    db.add(binding)
    db.flush()
    return binding


def refresh_review_currentness(db: Session, binding: ProposalIntelligenceReviewBinding) -> bool:
    if not binding.actionable:
        return False
    dependency = ContextDependency(
        context_snapshot_id=binding.context_snapshot_id or "", dependency_type=binding.dependency_type,
        dependency_id=binding.dependency_id, dependency_version_or_hash=binding.dependency_version_or_hash,
        required=True, trust_state="CANONICAL", currentness_state_at_capture="CURRENT", metadata_json={"domain_entity": "PROPOSAL"},
    )
    current = dependency_current(db, dependency)
    if current and binding.context_snapshot_id:
        current = not bool(revalidate_snapshot(db, binding.context_snapshot_id))
    if not current:
        binding.actionable = False
        binding.stale_reason = "PROPOSAL_INTELLIGENCE_DEPENDENCY_STALE"
        invalidate_dependency(
            db, dependency_type=binding.dependency_type, dependency_id=binding.dependency_id,
            superseding_version_or_hash=None,
            source_event_id=f"proposal-review-currentness:{binding.id}",
            reason_code="PROPOSAL_INTELLIGENCE_DEPENDENCY_STALE",
        ) if binding.work_product_id else None
        if binding.work_product_id:
            work_product = db.get(AIWorkProduct, binding.work_product_id)
            if work_product and str(work_product.state) == "CURRENT":
                work_product.state = "STALE"
                work_product.stale_reason = binding.stale_reason
        task = db.get(WorkflowTask, binding.workflow_task_id)
        if task:
            task.status = WorkflowTaskStatus.BLOCKED
            task.next_action_code = "RERUN_PROPOSAL_INTELLIGENCE"
        db.flush()
    return current


def proposal_reviews(db: Session, proposal_id: str) -> list[dict[str, Any]]:
    rows = db.scalars(select(ProposalIntelligenceReviewBinding).where(ProposalIntelligenceReviewBinding.proposal_id == proposal_id).order_by(ProposalIntelligenceReviewBinding.created_at)).all()
    result = []
    for row in rows:
        refresh_review_currentness(db, row)
        wp = db.get(AIWorkProduct, row.work_product_id) if row.work_product_id else None
        task = db.get(WorkflowTask, row.workflow_task_id)
        result.append({"binding_id": row.id, "workflow_task_id": row.workflow_task_id, "proposal_id": row.proposal_id, "review_subject_type": row.review_subject_type, "review_subject_id": row.review_subject_id, "work_product_id": row.work_product_id, "context_snapshot_id": row.context_snapshot_id, "required_persona": row.required_persona, "required_capability": row.required_capability, "correlation_id": row.correlation_id, "precondition_version": row.precondition_version, "actionable": row.actionable and bool(wp and str(wp.state) == "CURRENT"), "stale_reason": row.stale_reason, "task_status": task.status if task else None, "output": wp.structured_output_json if wp and str(wp.state) == "CURRENT" else (wp.structured_output_json if wp else None), "work_product_state": str(wp.state) if wp else None, "skill_id": wp.skill_id if wp else None, "skill_version": wp.skill_version if wp else None})
    db.commit()
    return result


def submit_proposal_review(
    db: Session, *, proposal_id: str, binding_id: str, decision: str, idempotency_key: str,
    principal: AuthenticatedPrincipal, correlation_id: str, precondition_version: str,
    correction_payload: dict[str, Any] | None = None, reason: str | None = None,
) -> dict[str, Any]:
    principal = _principal(db, principal)
    proposal = db.get(Opportunity, proposal_id)
    binding = db.get(ProposalIntelligenceReviewBinding, binding_id)
    if proposal is None or binding is None or binding.proposal_id != proposal_id:
        raise IntelligenceContractError("PROPOSAL_REVIEW_NOT_FOUND")
    existing_decision = db.scalar(select(IntelligenceReviewDecision).where(IntelligenceReviewDecision.idempotency_key == idempotency_key))
    if existing_decision is not None:
        if existing_decision.review_subject_id != binding.review_subject_id or existing_decision.decision != decision or existing_decision.precondition_version != precondition_version or existing_decision.reviewer_user_id != principal.user_id:
            raise IntelligenceContractError("INTELLIGENCE_IDEMPOTENCY_KEY_REUSE_MISMATCH")
        return {"decision_id": existing_decision.id, "decision": existing_decision.decision, "work_product_id": existing_decision.work_product_id, "verified_assertion_created": False, "protected_action_executed": False}
    if not refresh_review_currentness(db, binding) or not binding.actionable:
        raise IntelligenceContractError("PROPOSAL_REVIEW_STALE")
    if precondition_version != binding.precondition_version:
        raise IntelligenceContractError("PROPOSAL_REVIEW_PRECONDITION_FAILED")
    require_capability(principal.role, P08_REVIEW_CAPABILITY)
    if principal.role.value != "SYSTEM_ADMIN" and persona_for_role(principal.role) not in _allowed_review_personas(binding):
        raise IntelligenceContractError("PROPOSAL_REVIEW_PERSONA_DENIED")
    if binding.candidate_assertion_id:
        candidate = db.get(CandidateAssertion, binding.candidate_assertion_id)
        if candidate is None or candidate.status != "CURRENT" or candidate.value_hash != binding.dependency_version_or_hash:
            raise IntelligenceContractError("PROPOSAL_REVIEW_STALE")
        decision_row = record_module_review_decision(
            db, principal=principal, owning_module="proposal", review_subject_type="CANDIDATE_ASSERTION",
            review_subject_id=candidate.id, decision=decision, idempotency_key=idempotency_key,
            correlation_id=correlation_id, authorizing_capability=P08_REVIEW_CAPABILITY,
            precondition_version=precondition_version, candidate_assertion_id=candidate.id,
            source_currentness_identity={"proposal_id": proposal.id, "candidate_value_hash": candidate.value_hash},
            correction_payload=correction_payload, reason=reason,
        )
        verified_id = None
        if decision in {"ACCEPT", "CORRECT"}:
            verified_id = promote_verified_assertion_from_decision(db, principal=principal, decision_id=decision_row.id, correction_payload=correction_payload).id
        binding.actionable = False
        task = db.get(WorkflowTask, binding.workflow_task_id)
        if task:
            task.status = WorkflowTaskStatus.COMPLETED
        db.commit()
        return {"decision_id": decision_row.id, "decision": decision_row.decision, "verified_assertion_id": verified_id, "protected_action_executed": False}
    revision = _accepted(db, proposal.id)
    current_revision_hash = f"{revision.id}:{revision.revision_number}:{revision.content_hash}"
    if current_revision_hash != binding.dependency_version_or_hash:
        raise IntelligenceContractError("PROPOSAL_REVIEW_STALE")
    wp = db.get(AIWorkProduct, binding.work_product_id) if binding.work_product_id else None
    if wp is None or str(wp.state) != "CURRENT":
        raise IntelligenceContractError("PROPOSAL_REVIEW_STALE")
    decision_row = record_module_review_decision(
        db, principal=principal, owning_module="proposal", review_subject_type=binding.review_subject_type,
        review_subject_id=binding.review_subject_id, decision=decision, idempotency_key=idempotency_key,
        correlation_id=correlation_id, authorizing_capability=P08_REVIEW_CAPABILITY,
        precondition_version=precondition_version, work_product_id=wp.id,
        context_snapshot_id=binding.context_snapshot_id,
        source_currentness_identity={"proposal_id": proposal.id, "accepted_revision_id": revision.id, "accepted_revision_hash": revision.content_hash},
        correction_payload=correction_payload, reason=reason,
    )
    binding.actionable = False
    task = db.get(WorkflowTask, binding.workflow_task_id)
    if task:
        task.status = WorkflowTaskStatus.COMPLETED
    db.commit()
    return {"decision_id": decision_row.id, "decision": decision_row.decision, "work_product_id": wp.id, "verified_assertion_created": False, "protected_action_executed": False}


def submit_candidate_review(
    db: Session, *, proposal_id: str, candidate_id: str, decision: str, idempotency_key: str,
    principal: AuthenticatedPrincipal, correlation_id: str, precondition_version: str,
    correction_payload: dict[str, Any] | None = None, reason: str | None = None,
) -> dict[str, Any]:
    principal = _principal(db, principal)
    proposal = db.get(Opportunity, proposal_id)
    candidate = db.get(CandidateAssertion, candidate_id)
    if proposal is None or candidate is None or candidate.scope_id != proposal.id or candidate.target_module and candidate.target_module.lower() != "proposal":
        raise IntelligenceContractError("PROPOSAL_REVIEW_SCOPE_MISMATCH")
    require_capability(principal.role, P08_REVIEW_CAPABILITY)
    if candidate.status != "CURRENT" or candidate.value_hash != precondition_version:
        raise IntelligenceContractError("PROPOSAL_REVIEW_STALE")
    row = record_module_review_decision(
        db, principal=principal, owning_module="proposal", review_subject_type="CANDIDATE_ASSERTION", review_subject_id=candidate.id,
        decision=decision, idempotency_key=idempotency_key, correlation_id=correlation_id,
        authorizing_capability=P08_REVIEW_CAPABILITY, precondition_version=precondition_version,
        candidate_assertion_id=candidate.id, source_currentness_identity={"proposal_id": proposal.id, "candidate_value_hash": candidate.value_hash}, correction_payload=correction_payload, reason=reason,
    )
    verified_id = None
    if decision in {"ACCEPT", "CORRECT"}:
        verified = promote_verified_assertion_from_decision(db, principal=principal, decision_id=row.id, correction_payload=correction_payload)
        verified_id = verified.id
    db.commit()
    return {"decision_id": row.id, "decision": row.decision, "verified_assertion_id": verified_id, "protected_action_executed": False}
