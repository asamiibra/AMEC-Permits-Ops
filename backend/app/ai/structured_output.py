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


class ProposalIntakeAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=4000)
    missing_information: list[str] = Field(default_factory=list, max_length=30)
    contradictions: list[str] = Field(default_factory=list, max_length=30)
    unresolved_candidate_facts: list[str] = Field(default_factory=list, max_length=30)
    source_currentness_issues: list[str] = Field(default_factory=list, max_length=30)
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
                node["additionalProperties"] = False
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
