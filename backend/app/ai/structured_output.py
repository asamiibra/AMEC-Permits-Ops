"""Strict provider and local output contract for the D3 draft."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Callable, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

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
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=4000)
    findings: list[str] = Field(default_factory=list, max_length=30)
    citations: list[str] = Field(min_length=1, max_length=20)
    open_questions: list[str] = Field(default_factory=list, max_length=30)
    human_review_required: Literal[True] = True
    canonical_state_mutated: Literal[False] = False

    @field_validator("citations")
    @classmethod
    def validate_citations(cls, value: list[str]) -> list[str]:
        if any(not _CITATION_KEY.fullmatch(item) for item in value):
            raise ValueError("malformed citation key")
        return value


class BillingPaymentCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    invoice_id: str = Field(min_length=1, max_length=36)
    rank: int = Field(ge=1, le=20)
    rationale: str = Field(min_length=1, max_length=1200)
    evidence_strength: Literal["STRONG", "MODERATE", "WEAK"]
    suggested_allocation_amount: str | None = Field(default=None, max_length=40)

    @field_validator("suggested_allocation_amount")
    @classmethod
    def validate_amount(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            amount = Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError("malformed allocation amount") from exc
        if not amount.is_finite() or amount < 0 or amount.as_tuple().exponent < -2:
            raise ValueError("malformed allocation amount")
        return value


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


class ContractSkillOutput(BaseModel):
    """Strict advisory envelope shared by the Contract skill catalogue."""

    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=4000)
    findings: list[str] = Field(default_factory=list, max_length=30)
    citations: list[str] = Field(min_length=1, max_length=20)
    open_questions: list[str] = Field(default_factory=list, max_length=30)
    currentness_notes: list[str] = Field(default_factory=list, max_length=20)
    candidate_actions: list[str] = Field(default_factory=list, max_length=20)
    human_review_required: Literal[True] = True
    canonical_state_mutated: Literal[False] = False
    protected_action_count: Literal[0] = 0

    @field_validator("citations")
    @classmethod
    def validate_contract_citations(cls, value: list[str]) -> list[str]:
        if any(not _CITATION_KEY.fullmatch(item) for item in value):
            raise ValueError("malformed citation key")
        return value


class ContentLibrarySkillOutput(BaseModel):
    """Strict advisory envelope for the governed Content Library pack."""

    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=4000)
    findings: list[str] = Field(default_factory=list, max_length=30)
    citations: list[str] = Field(min_length=1, max_length=20)
    open_questions: list[str] = Field(default_factory=list, max_length=30)
    human_review_required: Literal[True] = True
    canonical_state_mutated: Literal[False] = False

    @field_validator("citations")
    @classmethod
    def validate_content_citations(cls, value: list[str]) -> list[str]:
        if any(not _CITATION_KEY.fullmatch(item) for item in value):
            raise ValueError("malformed citation key")
        return value


class ContentLibraryCandidateOutput(ContentLibrarySkillOutput):
    candidate_metadata: dict[str, Any] = Field(default_factory=dict)
    review_flags: list[str] = Field(default_factory=list, max_length=30)


class ContentLibraryAnalysisOutput(ContentLibrarySkillOutput):
    analysis_kind: str = Field(min_length=1, max_length=120)
    impacts: list[str] = Field(default_factory=list, max_length=30)
    blockers: list[str] = Field(default_factory=list, max_length=30)


class ContentLibraryRecommendationOutput(ContentLibrarySkillOutput):
    recommendations: list[str] = Field(default_factory=list, max_length=30)
    blockers: list[str] = Field(default_factory=list, max_length=30)
    confidence: Literal["HIGH", "MEDIUM", "LOW", "INSUFFICIENT"]


class ContentLibraryDescriptionDraftOutput(ContentLibrarySkillOutput):
    title: str | None = Field(default=None, max_length=240)
    description: str = Field(min_length=1, max_length=2000)
    keywords: list[str] = Field(default_factory=list, max_length=30)
    draft_only: Literal[True] = True


class ProposalIntakeAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=4000)
    missing_information: list[str] = Field(default_factory=list, max_length=30)
    contradictions: list[str] = Field(default_factory=list, max_length=30)
    unresolved_candidate_facts: list[str] = Field(default_factory=list, max_length=30)
    source_currentness_issues: list[str] = Field(default_factory=list, max_length=30)
    citation_keys: list[str] = Field(min_length=1, max_length=30)


class ProposalRequirementCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    requirement: str = Field(min_length=1, max_length=2000)
    proposal_section: str = Field(min_length=1, max_length=240)
    supporting_facts: list[str] = Field(default_factory=list, max_length=20)
    evidence_candidates: list[str] = Field(default_factory=list, max_length=20)
    conflicting_evidence: list[str] = Field(default_factory=list, max_length=20)
    missing_evidence: list[str] = Field(default_factory=list, max_length=20)
    explanation: str = Field(min_length=1, max_length=2000)
    confidence: float = Field(ge=0, le=1)
    citation_keys: list[str] = Field(min_length=1, max_length=16)


class ProposalRequirementEvidenceAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=4000)
    requirement_candidates: list[ProposalRequirementCandidate] = Field(default_factory=list, max_length=50)
    open_questions: list[str] = Field(default_factory=list, max_length=30)
    citation_keys: list[str] = Field(min_length=1, max_length=30)


class ProposalSectionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    section_type: str = Field(min_length=1, max_length=120)
    draft_content: str = Field(min_length=1, max_length=16000)
    approved_content_used: list[str] = Field(default_factory=list, max_length=30)
    canonical_facts_used: list[str] = Field(default_factory=list, max_length=30)
    open_questions: list[str] = Field(default_factory=list, max_length=30)
    assumptions: list[str] = Field(default_factory=list, max_length=30)
    unsupported_claims: list[str] = Field(default_factory=list, max_length=30)
    citation_keys: list[str] = Field(min_length=1, max_length=30)
    draft_only: Literal[True] = True


class ProposalCommercialVariance(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    field: str = Field(min_length=1, max_length=160)
    proposal_value: str = Field(max_length=1000)
    source_value: str = Field(max_length=1000)
    candidate_classification: Literal["POSSIBLE_MATERIAL_VARIANCE"] = "POSSIBLE_MATERIAL_VARIANCE"
    citation_keys: list[str] = Field(min_length=1, max_length=16)


class ProposalCommercialConsistencyReview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=4000)
    variances: list[ProposalCommercialVariance] = Field(default_factory=list, max_length=50)
    open_questions: list[str] = Field(default_factory=list, max_length=30)
    citation_keys: list[str] = Field(min_length=1, max_length=30)


class ProposalHandoffPreflight(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=4000)
    deterministic_state: Literal["READY", "BLOCKED", "UNKNOWN"]
    deterministic_blockers: list[str] = Field(default_factory=list, max_length=50)
    candidate_issues: list[str] = Field(default_factory=list, max_length=30)
    next_permissible_human_actions: list[str] = Field(default_factory=list, max_length=30)
    citation_keys: list[str] = Field(min_length=1, max_length=30)


class ProposalScopeTechnicalAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=4000)
    assumptions: list[str] = Field(default_factory=list, max_length=30)
    exclusions: list[str] = Field(default_factory=list, max_length=30)
    unresolved_technical_questions: list[str] = Field(default_factory=list, max_length=30)
    eligibility_dependencies: list[str] = Field(default_factory=list, max_length=30)
    recommendation_notes: list[str] = Field(default_factory=list, max_length=30)
    citation_keys: list[str] = Field(min_length=1, max_length=30)


class ProposalLpoDifference(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    field: str = Field(min_length=1, max_length=160)
    proposal_value: str = Field(max_length=1000)
    lpo_value: str = Field(max_length=1000)
    evidence_key: str = Field(min_length=1, max_length=30)


class ProposalLpoVarianceAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=4000)
    accepted_revision_id: str = Field(min_length=1, max_length=36)
    lpo_evidence_id: str | None = Field(default=None, min_length=1, max_length=36)
    differences: list[ProposalLpoDifference] = Field(default_factory=list, max_length=50)
    citation_keys: list[str] = Field(min_length=1, max_length=30)


class ProposalReadinessExplanation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    explanation: str = Field(min_length=1, max_length=4000)
    blockers: list[str] = Field(default_factory=list, max_length=30)
    stale_dependencies: list[str] = Field(default_factory=list, max_length=30)
    missing_information: list[str] = Field(default_factory=list, max_length=30)
    next_permissible_human_actions: list[str] = Field(default_factory=list, max_length=30)
    citation_keys: list[str] = Field(min_length=1, max_length=30)


def _proposal_citation_keys(value: BaseModel) -> tuple[str, ...]:
    return tuple(value.citation_keys)


def _validate_proposal(model: type[BaseModel], value: object) -> BaseModel:
    try:
        return model.model_validate(value)
    except Exception as exc:
        raise AIError("AI_STRUCTURED_OUTPUT_VALIDATION_FAILED", status_code=502) from exc


def _strict_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    def close(node: Any) -> Any:
        if isinstance(node, dict):
            if node.get("type") == "object":
                # Azure OpenAI strict structured outputs require every object
                # property to be present in `required`, including fields that
                # have a Pydantic default.  An unconstrained dict is also
                # represented as an object without properties; close it as an
                # intentionally empty object so it cannot become an escape
                # hatch for provider output.
                properties = node.setdefault("properties", {})
                node["additionalProperties"] = False
                node["required"] = list(properties)
            for value in node.values():
                close(value)
        elif isinstance(node, list):
            for value in node:
                close(value)
        return node
    return close(schema)


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

PROPOSAL_INTAKE_ANALYSIS_OUTPUT = StructuredOutputDefinition(
    schema_name="proposal_intake_analysis", schema_version="1", output_class="ANALYSIS",
    provider_schema=_strict_schema(ProposalIntakeAnalysis), validator=lambda value: _validate_proposal(ProposalIntakeAnalysis, value),
    citation_keys=_proposal_citation_keys, requires_grounding=True,
)
PROPOSAL_SCOPE_TECHNICAL_ANALYSIS_OUTPUT = StructuredOutputDefinition(
    schema_name="proposal_scope_technical_analysis", schema_version="1", output_class="RECOMMENDATION",
    provider_schema=_strict_schema(ProposalScopeTechnicalAnalysis), validator=lambda value: _validate_proposal(ProposalScopeTechnicalAnalysis, value),
    citation_keys=_proposal_citation_keys, requires_grounding=True,
)
PROPOSAL_LPO_VARIANCE_ANALYSIS_OUTPUT = StructuredOutputDefinition(
    schema_name="proposal_lpo_variance_analysis", schema_version="1", output_class="ANALYSIS",
    provider_schema=_strict_schema(ProposalLpoVarianceAnalysis), validator=lambda value: _validate_proposal(ProposalLpoVarianceAnalysis, value),
    citation_keys=_proposal_citation_keys, requires_grounding=True,
)
PROPOSAL_READINESS_EXPLANATION_OUTPUT = StructuredOutputDefinition(
    schema_name="proposal_readiness_explanation", schema_version="1", output_class="ANALYSIS",
    provider_schema=_strict_schema(ProposalReadinessExplanation), validator=lambda value: _validate_proposal(ProposalReadinessExplanation, value),
    citation_keys=_proposal_citation_keys, requires_grounding=True,
)

PROPOSAL_TENDER_INTAKE_ANALYSIS_OUTPUT = StructuredOutputDefinition(
    schema_name="proposal_tender_intake_analysis", schema_version="1", output_class="ANALYSIS",
    provider_schema=_strict_schema(ProposalIntakeAnalysis), validator=lambda value: _validate_proposal(ProposalIntakeAnalysis, value),
    citation_keys=_proposal_citation_keys, requires_grounding=True,
)
PROPOSAL_REQUIREMENT_EVIDENCE_ANALYSIS_OUTPUT = StructuredOutputDefinition(
    schema_name="proposal_requirement_evidence_analysis", schema_version="1", output_class="ANALYSIS",
    provider_schema=_strict_schema(ProposalRequirementEvidenceAnalysis), validator=lambda value: _validate_proposal(ProposalRequirementEvidenceAnalysis, value),
    citation_keys=_proposal_citation_keys, requires_grounding=True,
)
PROPOSAL_SECTION_DRAFT_OUTPUT = StructuredOutputDefinition(
    schema_name="proposal_section_draft", schema_version="1", output_class="DRAFT",
    provider_schema=_strict_schema(ProposalSectionDraft), validator=lambda value: _validate_proposal(ProposalSectionDraft, value),
    citation_keys=_proposal_citation_keys, requires_grounding=True,
)
PROPOSAL_COMMERCIAL_CONSISTENCY_REVIEW_OUTPUT = StructuredOutputDefinition(
    schema_name="proposal_commercial_consistency_review", schema_version="1", output_class="ANALYSIS",
    provider_schema=_strict_schema(ProposalCommercialConsistencyReview), validator=lambda value: _validate_proposal(ProposalCommercialConsistencyReview, value),
    citation_keys=_proposal_citation_keys, requires_grounding=True,
)
PROPOSAL_HANDOFF_PREFLIGHT_OUTPUT = StructuredOutputDefinition(
    schema_name="proposal_handoff_preflight", schema_version="1", output_class="ANALYSIS",
    provider_schema=_strict_schema(ProposalHandoffPreflight), validator=lambda value: _validate_proposal(ProposalHandoffPreflight, value),
    citation_keys=_proposal_citation_keys, requires_grounding=True,
)


def _billing_citation_keys(value: BaseModel) -> tuple[str, ...]:
    return tuple(value.citations)


def _billing_output(model: type[BillingSkillOutput], schema_name: str) -> StructuredOutputDefinition:
    return StructuredOutputDefinition(
        schema_name=schema_name, schema_version="1", output_class="ANALYSIS",
        provider_schema=_strict_schema(model), validator=model.model_validate,
        citation_keys=_billing_citation_keys, requires_grounding=True,
    )


BILLING_PAYMENT_MATCH_OUTPUT = _billing_output(BillingPaymentMatchOutput, "billing_payment_match")
BILLING_COLLECTIONS_OUTPUT = _billing_output(BillingCollectionsOutput, "billing_collections_copilot")
BILLING_PLAN_BUILDER_OUTPUT = _billing_output(BillingPlanBuilderOutput, "billing_plan_builder")
BILLING_READINESS_OUTPUT = _billing_output(BillingReadinessOutput, "billing_readiness_assessment")
BILLING_INVOICE_REVIEW_OUTPUT = _billing_output(BillingInvoiceReviewOutput, "billing_invoice_review")
BILLING_DELIVERY_ACK_OUTPUT = _billing_output(BillingDeliveryAckOutput, "billing_delivery_ack_extraction")


CONTRACT_INTELLIGENCE_OUTPUT = StructuredOutputDefinition(
    schema_name="contract_intelligence_candidate", schema_version="1", output_class="ANALYSIS",
    provider_schema=_strict_schema(ContractSkillOutput), validator=ContractSkillOutput.model_validate,
    citation_keys=lambda value: tuple(value.citations), requires_grounding=True,
)


def _content_library_citation_keys(value: BaseModel) -> tuple[str, ...]:
    return tuple(value.citations)


def _content_library_output(model: type[ContentLibrarySkillOutput], schema_name: str, output_class: str) -> StructuredOutputDefinition:
    return StructuredOutputDefinition(
        schema_name=schema_name,
        schema_version="1",
        output_class=output_class,
        provider_schema=_strict_schema(model),
        validator=model.model_validate,
        citation_keys=_content_library_citation_keys,
        requires_grounding=True,
    )


CONTENT_LIBRARY_INTAKE_GOVERNANCE_OUTPUT = _content_library_output(ContentLibraryCandidateOutput, "content_library_intake_governance_analysis", "CANDIDATE")
CONTENT_LIBRARY_QUALITY_GAP_OUTPUT = _content_library_output(ContentLibraryAnalysisOutput, "content_library_quality_gap_analysis", "ANALYSIS")
CONTENT_LIBRARY_VERSION_CHANGE_OUTPUT = _content_library_output(ContentLibraryAnalysisOutput, "content_library_version_change_analysis", "ANALYSIS")
CONTENT_LIBRARY_DEPENDENCY_IMPACT_OUTPUT = _content_library_output(ContentLibraryAnalysisOutput, "content_library_dependency_impact_analysis", "ANALYSIS")
CONTENT_LIBRARY_REUSE_APPLICABILITY_OUTPUT = _content_library_output(ContentLibraryRecommendationOutput, "content_library_reuse_applicability_analysis", "RECOMMENDATION")
CONTENT_LIBRARY_DESCRIPTION_DRAFT_OUTPUT = _content_library_output(ContentLibraryDescriptionDraftOutput, "content_library_description_draft", "DRAFT")
CONTENT_LIBRARY_SOURCE_GROUNDED_ASSIST_OUTPUT = _content_library_output(ContentLibraryAnalysisOutput, "content_library_source_grounded_assist", "ANALYSIS")
