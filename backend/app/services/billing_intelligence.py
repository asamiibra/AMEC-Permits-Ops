"""Billing-owned orchestration on the shared Intelligence runtime."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session, sessionmaker

from backend.app.ai.provider import AIProviderRequest, AIProviderResult, AIProviderUsage
from backend.app.ai.billing_skill_pack import BILLING_CONTEXT_VERSION, BILLING_POLICY_VERSION, BILLING_SKILLS_BY_ID
from backend.app.ai.skill_runtime import RuntimeDependencies, SkillExecutionRequest, SkillRuntime
from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.config.settings import Settings


class BillingDeterministicProvider:
    """Synthetic provider for local acceptance; never used by production routes."""

    def execute_structured(self, request: AIProviderRequest) -> AIProviderResult:
        context = json.loads(request.provider_input).get("context", [])
        citation = ["CIT-001"] if context else []
        common = {
            "summary": "Synthetic governed Billing Intelligence analysis for human review.",
            "findings": ["Canonical Billing state remains authoritative."],
            "citations": citation,
            "open_questions": [],
            "human_review_required": True,
            "canonical_state_mutated": False,
        }
        payloads = {
            "billing_payment_match": {**common, "ranked_candidates": [], "evidence_strength": "INSUFFICIENT", "anomalies": []},
            "billing_collections_copilot": {**common, "priority": "NO_ACTION", "recommended_follow_up": "Review the receivable with the Billing owner.", "account_summary": "Synthetic account summary.", "draft_communication": "Draft only; human editing and sending remain separate."},
            "billing_plan_builder": {**common, "milestone_proposals": [], "commercial_ambiguities": [], "canonical_milestone_amount_calculations": 0},
            "billing_readiness_assessment": {**common, "assessment": "REVIEW_REQUIRED", "missing_evidence": [], "conflicts": []},
            "billing_invoice_review": {**common, "hard_control_failures": [], "semantic_warnings": [], "informational": [], "narrative_suggestion": None},
            "billing_delivery_ack_extraction": {**common, "extracted_events": [], "extraction_status": "NOT_FOUND", "due_date_canonical_calculation_count": 0},
        }
        return AIProviderResult("synthetic-billing-intelligence", payloads[request.schema_name], AIProviderUsage(1, 1, 2))


def execute_billing_intelligence(
    db: Session,
    *,
    skill_id: str,
    project_id: str,
    principal: AuthenticatedPrincipal,
    sources: list[dict[str, Any]],
    idempotency_key: str,
    correlation_id: str,
    settings: Settings,
    provider: Any | None = None,
) -> dict[str, Any]:
    skill = BILLING_SKILLS_BY_ID[skill_id]
    request = SkillExecutionRequest(
        idempotency_key=idempotency_key,
        correlation_id=correlation_id,
        skill_id=skill.manifest.skill_id,
        skill_version=skill.manifest.version,
        skill_manifest_hash=skill.manifest.manifest_hash,
        purpose="BILLING_INTELLIGENCE",
        execution_mode="INTERACTIVE",
        scope_type="PROJECT",
        scope_id=project_id,
        project_id=project_id,
        target_entity_type="PROJECT",
        target_entity_id=project_id,
        context_schema_version=BILLING_CONTEXT_VERSION,
        policy_version=BILLING_POLICY_VERSION,
        sources=tuple(sources),
    )
    runtime_session = sessionmaker(bind=db.get_bind(), expire_on_commit=False)
    runtime_settings = settings
    if isinstance(provider, BillingDeterministicProvider):
        runtime_settings = settings.model_copy(update={
            "ai_feature_enabled": True,
            "ai_external_inference_enabled": True,
            "ai_d4_commissioning_id": "BILLING-SYNTHETIC-D4",
            "ai_azure_openai_endpoint": "https://billing-synthetic.openai.azure.com",
            "ai_uami_client_id": "00000000-0000-0000-0000-000000000001",
            "ai_uami_principal_id": "00000000-0000-0000-0000-000000000002",
            "ai_azure_tenant_id": "00000000-0000-0000-0000-000000000003",
            "ai_max_output_tokens": 512,
        })
    return SkillRuntime(dependencies=RuntimeDependencies(session_factory=runtime_session)).execute(
        db, principal, request, settings=runtime_settings, provider=provider,
    )

