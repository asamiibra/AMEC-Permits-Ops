"""Governed Contract Intelligence skill catalogue.

This is a registry and eligibility seam, not an autonomous Contract agent.
Every skill is advisory, citation-backed when it runs, and has zero authority
to write canonical records or perform protected actions.
"""

from __future__ import annotations

from typing import Any

from ..config.settings import get_settings

CONTRACT_SKILL_REGISTRY_VERSION = "CONTRACT-INTELLIGENCE-REGISTRY-1.0"

_SKILLS: tuple[dict[str, Any], ...] = (
    {"skill_id": "contract.document-understand", "name": "Understand document", "purpose": "Structure a Contract-related document for human review.", "reads": ["authorized DocumentVersion"], "effect": "candidate only", "required_context": ["current_revision"]},
    {"skill_id": "contract.compare-to-proposal", "name": "Compare to Proposal", "purpose": "Explain differences between the current Contract and accepted Proposal.", "reads": ["current ContractRevision", "accepted ProposalRevision"], "effect": "advisory comparison", "required_context": ["current_revision", "accepted_proposal_revision"]},
    {"skill_id": "contract.compare-to-po-lpo", "name": "Compare to PO / LPO", "purpose": "Surface deterministic and semantic commercial differences.", "reads": ["current ContractRevision", "authorized PO/LPO DocumentVersion"], "effect": "advisory comparison", "required_context": ["current_revision", "po_or_lpo_document"]},
    {"skill_id": "contract.revision-impact", "name": "Revision impact", "purpose": "Summarize changes between Contract revisions.", "reads": ["current and historical ContractRevision"], "effect": "advisory summary", "required_context": ["at_least_two_revisions"]},
    {"skill_id": "contract.executed-copy-review", "name": "Review executed copy", "purpose": "Compare a returned executed copy with the accepted revision.", "reads": ["accepted ContractRevision", "candidate executed DocumentVersion"], "effect": "candidate differences", "required_context": ["accepted_revision", "executed_copy_candidate"]},
    {"skill_id": "contract.review-brief", "name": "Prepare review brief", "purpose": "Prepare a citation-backed brief for human Contract review.", "reads": ["authorized Contract evidence"], "effect": "draft only", "required_context": ["current_revision"]},
    {"skill_id": "contract.payment-terms-extract", "name": "Extract payment terms", "purpose": "Propose structured payment-term candidates.", "reads": ["authorized commercial DocumentVersion"], "effect": "candidate only", "required_context": ["commercial_document"]},
    {"skill_id": "contract.deliverables-extract", "name": "Extract deliverables", "purpose": "Propose structured deliverable candidates.", "reads": ["authorized commercial DocumentVersion"], "effect": "candidate only", "required_context": ["commercial_document"]},
    {"skill_id": "contract.client-inputs-extract", "name": "Extract client inputs", "purpose": "Propose missing client-input candidates.", "reads": ["authorized commercial DocumentVersion"], "effect": "candidate only", "required_context": ["commercial_document"]},
    {"skill_id": "contract.communication-draft", "name": "Draft communication", "purpose": "Prepare a missing-document message for user review.", "reads": ["authorized Contract readiness"], "effect": "draft only; never send", "required_context": ["missing_document_workflow"]},
    {"skill_id": "contract.operations-brief", "name": "Prepare Operations brief", "purpose": "Summarize timing, handoff, and advisory risks.", "reads": ["Contract operations projection"], "effect": "advisory summary", "required_context": ["operations_context"]},
)

_COMMON_POLICY = {
    "release_state": "RELEASED_FOR_CATALOGUE_ONLY",
    "owning_module": "CONTRACT",
    "applicable_entity_types": ["Contract", "ContractRevision"],
    "allowed_context": ["authenticated principal", "Contract scope", "current Contract read model", "authorized current DocumentVersion", "verified module evidence"],
    "input_trust_floor": "CURRENT_AUTHORIZED_CANONICAL_CONTEXT_OR_VERIFIED_EVIDENCE",
    "allowed_tools": [],
    "tool_policy": "NO_TOOLS_WHILE_RUNTIME_NOT_INTEGRATED",
    "model_policy": "NO_MODEL_INVOCATION_WHILE_DISABLED_BY_POLICY",
    "citation_policy": "FACTUAL_DOCUMENT_ASSERTIONS_REQUIRE_CURRENT_DOCUMENT_VERSION_CITATION",
    "evaluation_suite_version": "CONTRACT-INTELLIGENCE-EVAL-1.0",
    "eval_pack": {"name": "CONTRACT-INTELLIGENCE-EVAL", "version": "1.0"},
    "input_schema": {"contract_id": "string", "document_version_ids": "string[] (authorized by server)"},
    "output_schema": {"findings": "array of advisory candidates", "citations": "array of current DocumentVersion citations"},
    "review_trigger_policy": "MODULE_CONTRACT_HUMAN_REVIEW_REQUIRED",
    "suggested_review_role": "CONTRACT_REVIEW_AUTHORITY",
    "dependency_capture_policy": "CAPTURE_CURRENT_DOCUMENT_AND_CANONICAL_REVISION_DEPENDENCIES_ON_EXECUTION",
    "invalidation_policy": "STALE_ON_SOURCE_SUPERSESSION_OR_CANONICAL_CONTEXT_CHANGE",
    "output_class": "CANDIDATE_ANALYSIS_DRAFT_RECOMMENDATION_ONLY",
    "canonical_write_authority": "ZERO",
    "protected_action_authority": "ZERO",
}


def contract_skill_catalogue(*, contract_id: str, role: str, context: dict[str, bool] | None = None) -> dict[str, Any]:
    settings = get_settings()
    # The shared Contract skill runtime has not been integrated yet. Global AI
    # flags are configuration facts only and must never make these catalogue
    # entries appear executable.
    execution_enabled = False
    runtime_state = "RUNTIME_NOT_INTEGRATED"
    context = context or {}
    return {
        "contract_id": contract_id,
        "architecture": {
            "registry_version": CONTRACT_SKILL_REGISTRY_VERSION,
            "citation_policy": "FACTUAL_DOCUMENT_ASSERTIONS_REQUIRE_CURRENT_DOCUMENT_VERSION_CITATION",
            "result_policy": "ADVISORY_CANDIDATE_REQUIRES_HUMAN_REVIEW",
        },
        "catalogue_state": "RELEASED",
        "execution_state": runtime_state,
        "eligibility_state": "CATALOGUE_ONLY",
        "runtime": {
            "feature_enabled": bool(settings.ai_feature_enabled),
            "external_inference_enabled": bool(settings.ai_external_inference_enabled),
            "real_content_allowed": bool(settings.ai_real_content_allowed),
            "state": runtime_state,
            "catalogue_state": "RELEASED",
            "execution_state": runtime_state,
        },
        "skills": [
            {
                "skill_id": item["skill_id"],
                "version": "1.0.0",
                "name": item["name"],
                "purpose": item["purpose"],
                "status": "AVAILABLE" if execution_enabled else "DISABLED_BY_POLICY",
                "eligibility_state": "ELIGIBLE_FOR_FUTURE_EXECUTION" if all(context.get(key, False) for key in item["required_context"]) else "MISSING_REQUIRED_CONTEXT",
                "eligibility_reason": ("Required context is present; execution remains disabled until the shared Contract runtime is integrated." if all(context.get(key, False) for key in item["required_context"]) else "Missing required context: " + ", ".join(key.replace("_", " ") for key in item["required_context"] if not context.get(key, False))),
                **_COMMON_POLICY,
                "applicable_document_classes": ["CONTRACT", "CONTRACT_AMENDMENT", "PO", "LPO", "CLIENT_DOCUMENT", "EXECUTED_CONTRACT"],
                "required_capabilities": ["CONTRACT_READ"],
                "required_context": item["required_context"],
                "allowed_reads": item["reads"],
                "allowed_effects": [item["effect"]],
                "human_review_required": True,
                "last_run": None,
                "requested_by_role": role,
            }
            for item in _SKILLS
        ],
        "findings": [],
    }
