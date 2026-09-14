from __future__ import annotations

import pytest

from backend.app.ai.billing_skill_pack import BILLING_SKILLS
from backend.app.ai.skill_registry import SKILL_REGISTRY
from backend.app.ai.structured_output import (
    BillingDeliveryAckOutput,
    BillingInvoiceReviewOutput,
    BillingPaymentMatchOutput,
)
from backend.app.services.billing_intelligence import BillingDeterministicProvider
from backend.app.ai.provider import AIProviderRequest


def test_billing_pack_is_registered_strict_and_non_authoritative():
    assert {item.manifest.skill_id for item in BILLING_SKILLS} == {
        "billing.payment-match",
        "billing.collections-copilot",
        "billing.plan-builder",
        "billing.readiness-assessment",
        "billing.invoice-review",
        "billing.delivery-ack-extraction",
    }
    for item in BILLING_SKILLS:
        resolved = SKILL_REGISTRY.resolve(item.manifest.skill_id, item.manifest.version, item.manifest.manifest_hash)
        assert resolved.manifest.owning_module == "billing"
        assert resolved.manifest.review_trigger == "ALWAYS"
        assert resolved.manifest.allowed_tools == []
        assert resolved.manifest.canonical_write_authority == "NONE"
        assert resolved.manifest.protected_action_authority == "NONE"
        assert resolved.output.provider_schema["additionalProperties"] is False


def test_billing_outputs_reject_authority_fields_and_accept_zero_guards():
    base = {
        "summary": "bounded",
        "findings": [],
        "citations": ["CIT-001"],
        "open_questions": [],
        "human_review_required": True,
        "canonical_state_mutated": False,
    }
    BillingInvoiceReviewOutput.model_validate({**base, "hard_control_failures": [], "semantic_warnings": [], "informational": [], "narrative_suggestion": None})
    BillingDeliveryAckOutput.model_validate({**base, "extracted_events": [], "extraction_status": "NOT_FOUND", "due_date_canonical_calculation_count": 0})
    with pytest.raises(Exception):
        BillingPaymentMatchOutput.model_validate({**base, "ranked_candidates": [], "evidence_strength": "WEAK", "anomalies": [], "approved": True})
    with pytest.raises(Exception):
        BillingPaymentMatchOutput.model_validate({**base, "citations": ["CIT-1"], "ranked_candidates": [], "evidence_strength": "WEAK", "anomalies": []})


def test_synthetic_provider_returns_each_registered_schema():
    provider = BillingDeterministicProvider()
    for skill in BILLING_SKILLS:
        result = provider.execute_structured(AIProviderRequest('{"context":[{"projection":{}}]}', 512, skill.output.provider_schema, skill.output.schema_name))
        output = skill.output.validator(result.payload)
        assert output.canonical_state_mutated is False
        assert output.human_review_required is True
