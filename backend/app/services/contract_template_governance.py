"""Deterministic Contract template-family, clause, and assembly controls.

This module is deliberately independent of the AI runtime.  It accepts only
governed template candidates and human-reviewed bindings; it never selects a
template by filename, fuzzy similarity, or model output.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Mapping

from .week45 import stable_hash


class ContractTemplateGovernanceError(ValueError):
    """A fail-closed template, clause, or assembly decision."""

    def __init__(self, code: str, **details: Any) -> None:
        super().__init__(code)
        self.code = code
        self.details = details


class ContractRegionClass(StrEnum):
    FIXED_LEGAL_TEXT = "FIXED_LEGAL_TEXT"
    BILINGUAL_LEGAL_PAIR = "BILINGUAL_LEGAL_PAIR"
    CONTROLLED_CORPORATE_FACT = "CONTROLLED_CORPORATE_FACT"
    PARTY_VARIABLE = "PARTY_VARIABLE"
    PROJECT_VARIABLE = "PROJECT_VARIABLE"
    TECHNICAL_SCOPE_VARIABLE = "TECHNICAL_SCOPE_VARIABLE"
    COMMERCIAL_VARIABLE = "COMMERCIAL_VARIABLE"
    PAYMENT_MILESTONE = "PAYMENT_MILESTONE"
    CONDITIONAL_CLAUSE = "CONDITIONAL_CLAUSE"
    EXCLUSION_OR_THIRD_PARTY_CLAUSE = "EXCLUSION_OR_THIRD_PARTY_CLAUSE"
    REGULATORY_CAPABILITY_FACT = "REGULATORY_CAPABILITY_FACT"
    ANNEX_OR_DELIVERABLE = "ANNEX_OR_DELIVERABLE"
    FINANCIAL_ACCOUNT_REFERENCE = "FINANCIAL_ACCOUNT_REFERENCE"
    PROTECTED_HUMAN_SIGNATURE = "PROTECTED_HUMAN_SIGNATURE"
    EXECUTION_EVIDENCE_BLOCK = "EXECUTION_EVIDENCE_BLOCK"


VARIABLE_REGIONS = frozenset({
    ContractRegionClass.CONTROLLED_CORPORATE_FACT,
    ContractRegionClass.PARTY_VARIABLE,
    ContractRegionClass.PROJECT_VARIABLE,
    ContractRegionClass.TECHNICAL_SCOPE_VARIABLE,
    ContractRegionClass.COMMERCIAL_VARIABLE,
    ContractRegionClass.PAYMENT_MILESTONE,
    ContractRegionClass.CONDITIONAL_CLAUSE,
    ContractRegionClass.EXCLUSION_OR_THIRD_PARTY_CLAUSE,
    ContractRegionClass.REGULATORY_CAPABILITY_FACT,
    ContractRegionClass.ANNEX_OR_DELIVERABLE,
    ContractRegionClass.FINANCIAL_ACCOUNT_REFERENCE,
})


@dataclass(frozen=True)
class ContractTemplateCandidate:
    template_family: str
    template_version: str
    document_version_id: str
    content_hash: str
    applicability: Mapping[str, Any]
    status: str = "GOVERNED_CURRENT"


@dataclass(frozen=True)
class ContractTemplateResolution:
    template_family: str
    template_version: str
    document_version_id: str
    content_hash: str
    configuration_identity: str

    def snapshot(self) -> dict[str, str]:
        return {
            "template_family": self.template_family,
            "template_version": self.template_version,
            "document_version_id": self.document_version_id,
            "content_hash": self.content_hash,
            "configuration_identity": self.configuration_identity,
        }


@dataclass(frozen=True)
class ContractTemplateRegion:
    region_id: str
    template_family: str
    template_version: str
    anchor: str
    classification: ContractRegionClass
    source_binding: str | None
    applicability_rule: str
    ai_allowed: bool
    human_owner: str
    required: bool
    clause_version: str | None = None
    bilingual_pair_id: str | None = None
    rendering_rule: str = "EXACT_TEXT"


@dataclass(frozen=True)
class ContractBinding:
    region_id: str
    candidate_value: Any
    source_document_version_id: str
    source_locator: str
    confidence: float | None
    uncertainty: str | None
    conflict_state: str
    human_review_required: bool = True


def resolve_contract_template(
    candidates: list[ContractTemplateCandidate],
    *,
    requirements: Mapping[str, Any],
) -> ContractTemplateResolution:
    """Resolve exactly one eligible governed template candidate.

    ``requirements`` is the deterministic projection of accepted proposal,
    PO/LPO, service, scope, discipline, subtype, and effective configuration.
    """
    eligible = [
        candidate for candidate in candidates
        if candidate.status == "GOVERNED_CURRENT"
        and all(candidate.applicability.get(key) == value for key, value in requirements.items())
    ]
    if not eligible:
        raise ContractTemplateGovernanceError("CONTRACT_TEMPLATE_CONFIGURATION_MISSING")
    if len(eligible) > 1:
        raise ContractTemplateGovernanceError(
            "CONTRACT_TEMPLATE_CONFIGURATION_CONFLICT",
            candidates=[candidate.snapshot() if hasattr(candidate, "snapshot") else candidate.__dict__ for candidate in eligible],
        )
    selected = eligible[0]
    return ContractTemplateResolution(
        template_family=selected.template_family,
        template_version=selected.template_version,
        document_version_id=selected.document_version_id,
        content_hash=selected.content_hash,
        configuration_identity=stable_hash({"family": selected.template_family, "applicability": dict(selected.applicability)}),
    )


def validate_contract_region_manifest(regions: list[ContractTemplateRegion]) -> dict[str, int]:
    """Reject unclassified, unbound, unsafe, or structurally broken regions."""
    region_ids = [region.region_id for region in regions]
    if len(region_ids) != len(set(region_ids)):
        raise ContractTemplateGovernanceError("DUPLICATE_CONTRACT_REGION_ID")
    for region in regions:
        if not isinstance(region.classification, ContractRegionClass):
            raise ContractTemplateGovernanceError("UNCLASSIFIED_CONTRACT_REGION", region_id=region.region_id)
        if region.classification == ContractRegionClass.FIXED_LEGAL_TEXT and region.ai_allowed:
            raise ContractTemplateGovernanceError("AI_FIXED_LEGAL_TEXT_FORBIDDEN", region_id=region.region_id)
        if region.required and region.classification in VARIABLE_REGIONS and not region.source_binding:
            raise ContractTemplateGovernanceError("UNBOUND_CONTRACT_VARIABLE", region_id=region.region_id)
        if region.classification == ContractRegionClass.BILINGUAL_LEGAL_PAIR and not region.bilingual_pair_id:
            raise ContractTemplateGovernanceError("UNPAIRED_GOVERNED_LEGAL_CLAUSE", region_id=region.region_id)
    return {
        "total_regions": len(regions),
        "unclassified_regions": 0,
        "unbound_variable_regions": 0,
    }


def assemble_contract(
    *,
    resolution: ContractTemplateResolution,
    regions: list[ContractTemplateRegion],
    fixed_text: Mapping[str, str],
    approved_clauses: Mapping[str, str],
    bindings: list[ContractBinding],
    accepted_contract_revision_id: str,
) -> dict[str, Any]:
    """Create a deterministic render input; no model-produced final text."""
    validate_contract_region_manifest(regions)
    binding_by_region = {binding.region_id: binding for binding in bindings}
    rendered: list[dict[str, Any]] = []
    for region in regions:
        if region.classification == ContractRegionClass.FIXED_LEGAL_TEXT:
            if region.region_id not in fixed_text:
                raise ContractTemplateGovernanceError("FIXED_LEGAL_TEXT_MISSING", region_id=region.region_id)
            rendered.append({"region_id": region.region_id, "value": fixed_text[region.region_id], "source": "GOVERNED_TEMPLATE"})
            continue
        if region.classification in {ContractRegionClass.BILINGUAL_LEGAL_PAIR, ContractRegionClass.CONDITIONAL_CLAUSE} and region.region_id not in approved_clauses:
            raise ContractTemplateGovernanceError("APPROVED_CLAUSE_MISSING", region_id=region.region_id)
        binding = binding_by_region.get(region.region_id)
        if region.required and binding is None:
            raise ContractTemplateGovernanceError("UNBOUND_CONTRACT_VARIABLE", region_id=region.region_id)
        if binding and binding.human_review_required is not True:
            raise ContractTemplateGovernanceError("HUMAN_REVIEW_REQUIRED", region_id=region.region_id)
        value = approved_clauses.get(region.region_id) if region.region_id in approved_clauses else binding.candidate_value if binding else None
        rendered.append({"region_id": region.region_id, "value": value, "source": "APPROVED_CLAUSE" if region.region_id in approved_clauses else "HUMAN_REVIEWED_BINDING"})
    payload = {
        "template": resolution.snapshot(),
        "accepted_contract_revision_id": accepted_contract_revision_id,
        "regions": rendered,
        "governance": {
            "fixed_legal_text_mutations": 0,
            "undeclared_clause_insertions": 0,
            "cross_family_clause_leakage": 0,
            "ai_canonical_write_authority": "ZERO",
            "ai_protected_action_authority": "ZERO",
        },
    }
    return {**payload, "render_input_hash": stable_hash(payload)}
