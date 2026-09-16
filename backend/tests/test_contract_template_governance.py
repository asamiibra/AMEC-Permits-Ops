import pytest

from backend.app.services.contract_template_governance import (
    ContractBinding,
    ContractRegionClass,
    ContractTemplateCandidate,
    ContractTemplateGovernanceError,
    ContractTemplateRegion,
    assemble_contract,
    resolve_contract_template,
    validate_contract_region_manifest,
)


def candidate(version: str, applicability: dict[str, object]) -> ContractTemplateCandidate:
    return ContractTemplateCandidate("AMEC-SERVICE", version, f"doc-{version}", f"hash-{version}", applicability)


def test_template_resolution_is_exact_and_fail_closed():
    requirements = {"service": "PERMIT", "language": "AR_EN"}
    resolved = resolve_contract_template([candidate("2", requirements)], requirements=requirements)
    assert resolved.snapshot() == {
        "template_family": "AMEC-SERVICE",
        "template_version": "2",
        "document_version_id": "doc-2",
        "content_hash": "hash-2",
        "configuration_identity": resolved.configuration_identity,
    }
    with pytest.raises(ContractTemplateGovernanceError, match="CONFIGURATION_MISSING"):
        resolve_contract_template([], requirements=requirements)
    with pytest.raises(ContractTemplateGovernanceError, match="CONFIGURATION_CONFLICT"):
        resolve_contract_template([candidate("2", requirements), candidate("3", requirements)], requirements=requirements)


def test_region_manifest_rejects_unbound_or_ai_mutable_legal_regions():
    with pytest.raises(ContractTemplateGovernanceError, match="AI_FIXED_LEGAL_TEXT_FORBIDDEN"):
        validate_contract_region_manifest([ContractTemplateRegion("r1", "F", "1", "a", ContractRegionClass.FIXED_LEGAL_TEXT, None, "always", True, "OWNER", True)])
    with pytest.raises(ContractTemplateGovernanceError, match="UNBOUND_CONTRACT_VARIABLE"):
        validate_contract_region_manifest([ContractTemplateRegion("r2", "F", "1", "a", ContractRegionClass.COMMERCIAL_VARIABLE, None, "always", False, "OWNER", True)])
    with pytest.raises(ContractTemplateGovernanceError, match="UNPAIRED_GOVERNED_LEGAL_CLAUSE"):
        validate_contract_region_manifest([ContractTemplateRegion("r3", "F", "1", "a", ContractRegionClass.BILINGUAL_LEGAL_PAIR, "clause", "always", False, "OWNER", True)])


def test_assembly_is_deterministic_and_advisory_only():
    resolution = resolve_contract_template([candidate("1", {"service": "PERMIT"})], requirements={"service": "PERMIT"})
    regions = [
        ContractTemplateRegion("legal", "AMEC-SERVICE", "1", "a", ContractRegionClass.FIXED_LEGAL_TEXT, "fixed", "always", False, "OWNER", True),
        ContractTemplateRegion("client", "AMEC-SERVICE", "1", "b", ContractRegionClass.PARTY_VARIABLE, "client.name", "always", False, "OWNER", True),
    ]
    result = assemble_contract(
        resolution=resolution,
        regions=regions,
        fixed_text={"legal": "Approved clause"},
        approved_clauses={},
        bindings=[ContractBinding("client", "AMEC", "doc-source", "party.name", 0.99, None, "NONE")],
        accepted_contract_revision_id="revision-1",
    )
    assert result["governance"]["fixed_legal_text_mutations"] == 0
    assert result["governance"]["ai_canonical_write_authority"] == "ZERO"
    assert result["render_input_hash"]
