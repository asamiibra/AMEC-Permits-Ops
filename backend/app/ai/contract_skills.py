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
    {"skill_id": "contract.document-understand", "name": "Understand document", "purpose": "Structure a Contract-related document for human review.", "reads": ["authorized DocumentVersion"], "effect": "candidate only"},
    {"skill_id": "contract.compare-to-proposal", "name": "Compare to Proposal", "purpose": "Explain differences between the current Contract and accepted Proposal.", "reads": ["current ContractRevision", "accepted ProposalRevision"], "effect": "advisory comparison"},
    {"skill_id": "contract.compare-to-po-lpo", "name": "Compare to PO / LPO", "purpose": "Surface deterministic and semantic commercial differences.", "reads": ["current ContractRevision", "authorized PO/LPO DocumentVersion"], "effect": "advisory comparison"},
    {"skill_id": "contract.revision-impact", "name": "Revision impact", "purpose": "Summarize changes between Contract revisions.", "reads": ["current and historical ContractRevision"], "effect": "advisory summary"},
    {"skill_id": "contract.executed-copy-review", "name": "Review executed copy", "purpose": "Compare a returned executed copy with the accepted revision.", "reads": ["accepted ContractRevision", "candidate executed DocumentVersion"], "effect": "candidate differences"},
    {"skill_id": "contract.review-brief", "name": "Prepare review brief", "purpose": "Prepare a citation-backed brief for human Contract review.", "reads": ["authorized Contract evidence"], "effect": "draft only"},
    {"skill_id": "contract.payment-terms-extract", "name": "Extract payment terms", "purpose": "Propose structured payment-term candidates.", "reads": ["authorized commercial DocumentVersion"], "effect": "candidate only"},
    {"skill_id": "contract.deliverables-extract", "name": "Extract deliverables", "purpose": "Propose structured deliverable candidates.", "reads": ["authorized commercial DocumentVersion"], "effect": "candidate only"},
    {"skill_id": "contract.client-inputs-extract", "name": "Extract client inputs", "purpose": "Propose missing client-input candidates.", "reads": ["authorized commercial DocumentVersion"], "effect": "candidate only"},
    {"skill_id": "contract.communication-draft", "name": "Draft communication", "purpose": "Prepare a missing-document message for user review.", "reads": ["authorized Contract readiness"], "effect": "draft only; never send"},
    {"skill_id": "contract.operations-brief", "name": "Prepare Operations brief", "purpose": "Summarize timing, handoff, and advisory risks.", "reads": ["Contract operations projection"], "effect": "advisory summary"},
)

_COMMON_POLICY = {
    "release_state": "RELEASED_FOR_CATALOGUE_ONLY",
    "applicable_entity_types": ["Contract", "ContractRevision"],
    "context_requirements": ["authenticated principal", "Contract scope", "current Contract read model"],
    "allowed_tools": [],
    "model_policy": "NO_MODEL_INVOCATION_WHILE_DISABLED_BY_POLICY",
    "citation_policy": "FACTUAL_DOCUMENT_ASSERTIONS_REQUIRE_CURRENT_DOCUMENT_VERSION_CITATION",
    "evaluation_suite_version": "CONTRACT-INTELLIGENCE-EVAL-1.0",
    "input_schema": {"contract_id": "string", "document_version_ids": "string[] (authorized by server)"},
    "output_schema": {"findings": "array of advisory candidates", "citations": "array of current DocumentVersion citations"},
}


def contract_skill_catalogue(*, contract_id: str, role: str) -> dict[str, Any]:
    settings = get_settings()
    execution_enabled = bool(settings.ai_feature_enabled and settings.ai_external_inference_enabled and settings.ai_real_content_allowed)
    runtime_state = "ENABLED" if execution_enabled else "DISABLED_BY_POLICY"
    return {
        "contract_id": contract_id,
        "architecture": {
            "registry_version": CONTRACT_SKILL_REGISTRY_VERSION,
            "citation_policy": "FACTUAL_DOCUMENT_ASSERTIONS_REQUIRE_CURRENT_DOCUMENT_VERSION_CITATION",
            "result_policy": "ADVISORY_CANDIDATE_REQUIRES_HUMAN_REVIEW",
        },
        "runtime": {
            "feature_enabled": bool(settings.ai_feature_enabled),
            "external_inference_enabled": bool(settings.ai_external_inference_enabled),
            "real_content_allowed": bool(settings.ai_real_content_allowed),
            "state": runtime_state,
        },
        "skills": [
            {
                "skill_id": item["skill_id"],
                "version": "1.0.0",
                "name": item["name"],
                "purpose": item["purpose"],
                "status": "AVAILABLE" if execution_enabled else "DISABLED_BY_POLICY",
                "eligibility_reason": "Eligible for authenticated Contract context; execution is disabled by current AI runtime policy." if not execution_enabled else "Eligible for this authenticated Contract context.",
                **_COMMON_POLICY,
                "applicable_document_classes": ["CONTRACT", "CONTRACT_AMENDMENT", "PO", "LPO", "CLIENT_DOCUMENT", "EXECUTED_CONTRACT"],
                "required_capabilities": ["CONTRACT_READ"],
                "allowed_reads": item["reads"],
                "allowed_effects": [item["effect"]],
                "canonical_write_authority": "ZERO",
                "protected_action_authority": "ZERO",
                "human_review_required": True,
                "last_run": None,
                "requested_by_role": role,
            }
            for item in _SKILLS
        ],
        "findings": [],
    }
