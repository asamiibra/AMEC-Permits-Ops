"""Contract skill metadata and the module-owned shared-runtime adapter."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config.settings import get_settings
from ..models import Contract, ContractAdminEvidence
from ..services.context_compiler import ContextSourceSpec
from .provider import AIProviderRequest, AIProviderResult, AIProviderUsage
from .skill_registry import CONTRACT_SKILLS, SkillDefinition, SKILL_REGISTRY


CONTRACT_SKILL_REGISTRY_VERSION = "CONTRACT-INTELLIGENCE-REGISTRY-2.0"

_SKILLS: tuple[dict[str, Any], ...] = (
    {"skill_id": "contract.document-understand", "name": "Understand document", "purpose": "Structure a Contract-related document for human review.", "required_context": ["current_revision"]},
    {"skill_id": "contract.compare-to-proposal", "name": "Compare to Proposal", "purpose": "Explain differences between the current Contract and accepted Proposal.", "required_context": ["current_revision", "accepted_proposal_revision"]},
    {"skill_id": "contract.compare-to-po-lpo", "name": "Compare to PO / LPO", "purpose": "Surface deterministic and semantic commercial differences.", "required_context": ["current_revision", "po_or_lpo_document"]},
    {"skill_id": "contract.revision-impact", "name": "Revision impact", "purpose": "Summarize changes between Contract revisions.", "required_context": ["at_least_two_revisions"]},
    {"skill_id": "contract.executed-copy-review", "name": "Review executed copy", "purpose": "Compare a returned executed copy with the accepted revision.", "required_context": ["accepted_revision", "executed_copy_candidate"]},
    {"skill_id": "contract.review-brief", "name": "Prepare review brief", "purpose": "Prepare a citation-backed brief for human Contract review.", "required_context": ["current_revision"]},
    {"skill_id": "contract.payment-terms-extract", "name": "Extract payment terms", "purpose": "Propose structured payment-term candidates.", "required_context": ["commercial_document"]},
    {"skill_id": "contract.deliverables-extract", "name": "Extract deliverables", "purpose": "Propose structured deliverable candidates.", "required_context": ["commercial_document"]},
    {"skill_id": "contract.client-inputs-extract", "name": "Extract client inputs", "purpose": "Propose missing client-input candidates.", "required_context": ["commercial_document"]},
    {"skill_id": "contract.communication-draft", "name": "Draft communication", "purpose": "Prepare a missing-document message for user review.", "required_context": ["missing_document_workflow"]},
    {"skill_id": "contract.operations-brief", "name": "Prepare Operations brief", "purpose": "Summarize timing, handoff, and advisory risks.", "required_context": ["operations_context"]},
)

_BY_ID = {skill.manifest.skill_id: skill for skill in CONTRACT_SKILLS}


def contract_context_specs(db: Session, contract: Contract) -> tuple[ContextSourceSpec, ...]:
    """Build source selectors from canonical Contract rows, never browser content."""
    if not contract.current_revision_id:
        return ()
    sources = [ContextSourceSpec(
        key="contract-current-revision",
        context_type="DOMAIN_ENTITY_REVISION",
        selector={"entity_type": "CONTRACT", "entity_id": contract.id},
        required=True,
    )]
    evidence = db.scalars(
        select(ContractAdminEvidence)
        .where(
            ContractAdminEvidence.contract_id == contract.id,
            ContractAdminEvidence.contract_revision_id == contract.current_revision_id,
            ContractAdminEvidence.document_version_id.is_not(None),
        )
        .order_by(ContractAdminEvidence.recorded_at.desc())
    ).all()
    seen: set[str] = set()
    for item in evidence:
        version_id = str(item.document_version_id)
        if version_id in seen:
            continue
        seen.add(version_id)
        sources.append(ContextSourceSpec(
            key=f"document-{str(item.source_role or 'GENERAL').lower()}-{version_id}",
            context_type="DOCUMENT_VERSION",
            selector={"id": version_id},
            required=False,
        ))
    return tuple(sources)


def contract_skill_definition(skill_id: str) -> SkillDefinition:
    try:
        return _BY_ID[skill_id]
    except KeyError as exc:
        raise ValueError("CONTRACT_SKILL_NOT_REGISTERED") from exc


def contract_skill_catalogue(*, contract_id: str, role: str, context: dict[str, bool] | None = None) -> dict[str, Any]:
    settings = get_settings()
    context = context or {}
    runtime_ready = bool(settings.ai_feature_enabled and settings.ai_external_inference_enabled and settings.ai_d4_commissioning_id.strip())
    skills: list[dict[str, Any]] = []
    for item in _SKILLS:
        definition = contract_skill_definition(item["skill_id"])
        context_ready = all(context.get(key, False) for key in item["required_context"])
        skills.append({
            "skill_id": definition.manifest.skill_id,
            "version": definition.manifest.version,
            "manifest_hash": definition.manifest.manifest_hash,
            "name": item["name"],
            "purpose": item["purpose"],
            "status": "AVAILABLE" if context_ready and runtime_ready else "CONTEXT_INELIGIBLE" if not context_ready else "RUNTIME_NOT_COMMISSIONED",
            "runtime_state": "EXECUTABLE_WHEN_ELIGIBLE",
            "eligibility_state": "EXECUTABLE_WHEN_ELIGIBLE" if context_ready else "CONTEXT_INELIGIBLE",
            "eligibility_reason": "Required Contract context is present." if context_ready else "Missing required context: " + ", ".join(key.replace("_", " ") for key in item["required_context"] if not context.get(key, False)),
            "runtime_ready": runtime_ready,
            "runtime_reason": "Shared D4 runtime is configured." if runtime_ready else "Shared D4 runtime is not commissioned in this environment.",
            "owning_module": "CONTRACT",
            "canonical_write_authority": "NONE",
            "protected_action_authority": "NONE",
            "canonical_or_protected_authority": "NONE",
            "human_review_required": True,
            "advisory_only": True,
            "required_context": item["required_context"],
            "allowed_reads": ["current ContractRevision", "accepted ProposalRevision", "authorized current DocumentVersion", "Contract operations projection"],
            "last_run": None,
            "requested_by_role": role,
        })
    return {
        "contract_id": contract_id,
        "architecture": {
            "registry_version": CONTRACT_SKILL_REGISTRY_VERSION,
            "citation_policy": "FACTUAL_DOCUMENT_ASSERTIONS_REQUIRE_CURRENT_DOCUMENT_VERSION_CITATION",
            "result_policy": "ADVISORY_CANDIDATE_REQUIRES_HUMAN_REVIEW",
        },
        "catalogue_state": "RELEASED",
        "execution_state": "EXECUTABLE_WHEN_ELIGIBLE",
        "eligibility_state": "EXECUTABLE_WHEN_ELIGIBLE" if all(skill["eligibility_state"] == "EXECUTABLE_WHEN_ELIGIBLE" for skill in skills) else "CONTEXT_INELIGIBLE",
        "runtime": {
            "feature_enabled": bool(settings.ai_feature_enabled),
            "external_inference_enabled": bool(settings.ai_external_inference_enabled),
            "real_content_allowed": bool(settings.ai_real_content_allowed),
            "state": "EXECUTABLE_WHEN_ELIGIBLE",
            "runtime_ready": runtime_ready,
            "catalogue_state": "RELEASED",
        },
        "skills": skills,
        "findings": [],
    }


class ContractDeterministicProvider:
    """Synthetic-only provider for local commissioning and unit tests."""

    def execute_structured(self, request: AIProviderRequest) -> AIProviderResult:
        import json

        input_payload = json.loads(request.provider_input)
        skill_id = str(input_payload.get("skill", {}).get("skill_id") or "contract.skill")
        payload = {
            "summary": f"Synthetic advisory result for {skill_id}.",
            "findings": [{
                "title": "Human review required",
                "detail": "This synthetic result is a candidate analysis. Confirm every claim against the cited current Contract evidence.",
                "disposition": "REVIEW_REQUIRED",
                "citation_keys": ["CIT-001"],
            }],
            "human_review_actions": ["Review the cited evidence before recording any canonical Contract decision."],
            "limitations": ["Synthetic commissioning result; not a Contract acceptance or protected action."],
            "citation_keys": ["CIT-001"],
            "advisory_only": True,
        }
        input_tokens = max(1, len(request.provider_input.encode("utf-8")) // 4)
        return AIProviderResult(str(uuid4()), payload, AIProviderUsage(input_tokens, 64, input_tokens + 64))
