"""Strict provider and local output contract for the D3 draft."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .errors import AIError


_CITATION_KEY = re.compile(r"^CIT-[0-9]{3}$")
MAX_VISIBLE_DRAFT_BYTES = 48 * 1024


class DraftSection(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    heading: str = Field(min_length=1, max_length=240)
    body: str = Field(min_length=1, max_length=12000)
    citation_keys: list[str] = Field(min_length=1, max_length=16)


class DraftAssumption(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    statement: str = Field(min_length=1, max_length=1000)
    basis: Literal["SOURCE_GROUNDED", "INFERENCE"]
    citation_keys: list[str] = Field(default_factory=list, max_length=16)


class TechnicalMethodologyDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    draft_title: str = Field(min_length=1, max_length=240)
    sections: list[DraftSection] = Field(min_length=2, max_length=8)
    assumptions: list[DraftAssumption] = Field(default_factory=list, max_length=10)
    open_questions: list[str] = Field(default_factory=list, max_length=20)
    limitations: list[str] = Field(default_factory=list, max_length=20)
    source_coverage_note: str = Field(min_length=1, max_length=1000)
    draft_only: Literal[True] = True

    @model_validator(mode="after")
    def validate_bounded_text(self) -> "TechnicalMethodologyDraft":
        if any(len(item) > 1000 for item in (*self.open_questions, *self.limitations)):
            raise ValueError("question or limitation exceeds bound")
        if any(not all(_CITATION_KEY.fullmatch(key) for key in section.citation_keys) for section in self.sections):
            raise ValueError("section contains malformed citation key")
        for assumption in self.assumptions:
            if not all(_CITATION_KEY.fullmatch(key) for key in assumption.citation_keys):
                raise ValueError("assumption contains malformed citation key")
            if assumption.basis == "SOURCE_GROUNDED" and not assumption.citation_keys:
                raise ValueError("source-grounded assumption needs a citation")
        encoded = json.dumps(self.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        if len(encoded) > MAX_VISIBLE_DRAFT_BYTES:
            raise ValueError("draft exceeds visible output bound")
        return self


class BillingSkillOutput(BaseModel):
    """Shared strict envelope for non-authoritative Billing analyses.

    The individual skill definitions constrain the semantic fields below with
    literals and dedicated schemas.  No amount, due date, invoice number, or
    payment status is accepted as an AI-authored canonical value.
    """

    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=4000)
    findings: list[str] = Field(default_factory=list, max_length=30)
    citations: list[str] = Field(min_length=1, max_length=20)
    open_questions: list[str] = Field(default_factory=list, max_length=30)
    human_review_required: Literal[True] = True
    canonical_state_mutated: Literal[False] = False


class BillingPaymentCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    invoice_id: str = Field(min_length=1, max_length=36)
    rank: int = Field(ge=1, le=20)
    rationale: str = Field(min_length=1, max_length=1200)
    evidence_strength: Literal["STRONG", "MODERATE", "WEAK"]
    suggested_allocation_amount: str | None = Field(default=None, max_length=40)


class BillingMilestoneProposal(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    label: str = Field(min_length=1, max_length=200)
    commercial_term_citation: str = Field(min_length=1, max_length=300)
    percentage_term: str | None = Field(default=None, max_length=40)
    fixed_amount_term: str | None = Field(default=None, max_length=40)
    trigger_candidate: str = Field(min_length=1, max_length=400)
    evidence_requirement: str = Field(min_length=1, max_length=600)


class BillingExtractedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    event_type: Literal["DELIVERY", "ACKNOWLEDGMENT"]
    channel: str | None = Field(default=None, max_length=80)
    recipient: str | None = Field(default=None, max_length=240)
    event_timestamp: str | None = Field(default=None, max_length=80)
    invoice_reference: str | None = Field(default=None, max_length=100)
    acknowledgment_reference: str | None = Field(default=None, max_length=200)
    evidence_locator: str | None = Field(default=None, max_length=300)


class BillingPaymentMatchOutput(BillingSkillOutput):
    ranked_candidates: list[BillingPaymentCandidate] = Field(default_factory=list, max_length=20)
    evidence_strength: Literal["STRONG", "MODERATE", "WEAK", "INSUFFICIENT"]
    anomalies: list[str] = Field(default_factory=list, max_length=20)


class BillingCollectionsOutput(BillingSkillOutput):
    priority: Literal["HIGH", "MEDIUM", "LOW", "NO_ACTION"]
    recommended_follow_up: str = Field(min_length=1, max_length=1200)
    account_summary: str = Field(min_length=1, max_length=2000)
    draft_communication: str = Field(min_length=1, max_length=4000)


class BillingPlanBuilderOutput(BillingSkillOutput):
    milestone_proposals: list[BillingMilestoneProposal] = Field(default_factory=list, max_length=20)
    commercial_ambiguities: list[str] = Field(default_factory=list, max_length=20)
    canonical_milestone_amount_calculations: Literal[0] = 0


class BillingReadinessOutput(BillingSkillOutput):
    assessment: Literal["LIKELY_READY", "NOT_READY", "REVIEW_REQUIRED"]
    missing_evidence: list[str] = Field(default_factory=list, max_length=30)
    conflicts: list[str] = Field(default_factory=list, max_length=30)


class BillingInvoiceReviewOutput(BillingSkillOutput):
    hard_control_failures: list[str] = Field(default_factory=list, max_length=30)
    semantic_warnings: list[str] = Field(default_factory=list, max_length=30)
    informational: list[str] = Field(default_factory=list, max_length=30)
    narrative_suggestion: str | None = Field(default=None, max_length=2000)


class BillingDeliveryAckOutput(BillingSkillOutput):
    extracted_events: list[BillingExtractedEvent] = Field(default_factory=list, max_length=20)
    extraction_status: Literal["EXTRACTED", "PARTIAL", "NOT_FOUND"]
    due_date_canonical_calculation_count: Literal[0] = 0


@dataclass(frozen=True)
class StructuredOutputDefinition:
    """Server-registered strict output behavior for one executable skill."""

    schema_name: str
    schema_version: str
    output_class: str
    provider_schema: dict[str, Any]
    validator: Callable[[object], BaseModel]
    citation_keys: Callable[[BaseModel], tuple[str, ...]]
    requires_grounding: bool = True


def _technical_citation_keys(value: BaseModel) -> tuple[str, ...]:
    draft = value
    keys: list[str] = []
    for section in draft.sections:
        keys.extend(section.citation_keys)
    for assumption in draft.assumptions:
        keys.extend(assumption.citation_keys)
    return tuple(keys)


PROVIDER_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "draft_title": {"type": "string"},
        "sections": {"type": "array", "items": {"type": "object", "properties": {"heading": {"type": "string"}, "body": {"type": "string"}, "citation_keys": {"type": "array", "items": {"type": "string"}}}, "required": ["heading", "body", "citation_keys"], "additionalProperties": False}},
        "assumptions": {"type": "array", "items": {"type": "object", "properties": {"statement": {"type": "string"}, "basis": {"type": "string", "enum": ["SOURCE_GROUNDED", "INFERENCE"]}, "citation_keys": {"type": "array", "items": {"type": "string"}}}, "required": ["statement", "basis", "citation_keys"], "additionalProperties": False}},
        "open_questions": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "source_coverage_note": {"type": "string"},
        "draft_only": {"type": "boolean"},
    },
    "required": ["draft_title", "sections", "assumptions", "open_questions", "limitations", "source_coverage_note", "draft_only"],
    "additionalProperties": False,
}


def validate_draft(payload: object) -> TechnicalMethodologyDraft:
    try:
        return TechnicalMethodologyDraft.model_validate(payload)
    except Exception as exc:
        raise AIError("AI_STRUCTURED_OUTPUT_VALIDATION_FAILED", status_code=502) from exc


def output_fingerprint(draft: TechnicalMethodologyDraft) -> str:
    canonical = json.dumps(draft.model_dump(mode="json"), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


# Bind the compatibility definition after the historical schema and validator
# exist.  This keeps the old public helpers stable while giving the registry a
# generic, server-owned output definition.
TECHNICAL_METHODOLOGY_OUTPUT = StructuredOutputDefinition(
    schema_name="technical_methodology_draft",
    schema_version="1",
    output_class="DRAFT",
    provider_schema=PROVIDER_JSON_SCHEMA,
    validator=validate_draft,
    citation_keys=_technical_citation_keys,
    requires_grounding=True,
)


def _billing_citation_keys(value: BaseModel) -> tuple[str, ...]:
    return tuple(value.citations)


def _billing_output(model: type[BillingSkillOutput], schema_name: str) -> StructuredOutputDefinition:
    schema = model.model_json_schema()
    schema["additionalProperties"] = False
    return StructuredOutputDefinition(
        schema_name=schema_name,
        schema_version="1",
        output_class="ANALYSIS",
        provider_schema=schema,
        validator=model.model_validate,
        citation_keys=_billing_citation_keys,
        requires_grounding=True,
    )


BILLING_PAYMENT_MATCH_OUTPUT = _billing_output(BillingPaymentMatchOutput, "billing_payment_match")
BILLING_COLLECTIONS_OUTPUT = _billing_output(BillingCollectionsOutput, "billing_collections_copilot")
BILLING_PLAN_BUILDER_OUTPUT = _billing_output(BillingPlanBuilderOutput, "billing_plan_builder")
BILLING_READINESS_OUTPUT = _billing_output(BillingReadinessOutput, "billing_readiness_assessment")
BILLING_INVOICE_REVIEW_OUTPUT = _billing_output(BillingInvoiceReviewOutput, "billing_invoice_review")
BILLING_DELIVERY_ACK_OUTPUT = _billing_output(BillingDeliveryAckOutput, "billing_delivery_ack_extraction")
