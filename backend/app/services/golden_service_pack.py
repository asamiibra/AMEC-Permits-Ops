"""Technical Golden Service Pack contract.

This is an assembly/validation contract over existing shared-domain records,
not a new business module or an authority-policy source. It deliberately keeps
official service selection and source approval outside the codebase.
"""

from __future__ import annotations

from typing import Any


REQUIRED_COMPONENTS = (
    "external_body",
    "jurisdiction",
    "service_type",
    "regulatory_journey",
    "authority_case",
    "case_party_snapshot",
    "requirement_policy_version",
    "requirement_applicability",
    "forms",
    "form_automation_profile",
    "mapping_release",
    "writer_ownership",
    "technical_rule_set_version",
    "outputs",
    "human_gates",
    "submission_boundary",
    "closeout_axes",
    "source_currentness",
    "logical_storage_destinations",
)

OWNER_DEPENDENT_FIELDS = (
    "official_external_body",
    "official_jurisdiction",
    "official_service_type",
    "official_authority_policy_source",
    "official_form_files_and_versions",
    "named_initial_users",
    "production_storage_binding",
)


def candidate_golden_service_pack() -> dict[str, Any]:
    """Return a complete synthetic candidate without selecting official policy."""

    return {
        "pack_id": "CANDIDATE-GOLDEN-SERVICE-SYNTHETIC-BUILDING-PERMIT",
        "status": "READY_FOR_OWNER_SELECTION",
        "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE",
        "selected": False,
        "production_approved": False,
        "selection_basis": "Existing synthetic shared-domain and authority-case test coverage",
        "components": {
            "external_body": {"code": "SYNTHETIC-AUTHORITY", "source": "synthetic fixture only"},
            "jurisdiction": {"code": "SYNTHETIC-DOHA", "source": "synthetic fixture only"},
            "service_type": {"code": "SYNTHETIC-BUILDING-PERMIT", "source": "synthetic test service only"},
            "regulatory_journey": {"versioned": True, "owner_selection_required": True},
            "authority_case": {"scoped_by": ["project", "external_body", "jurisdiction", "service_type"]},
            "case_party_snapshot": {"immutable": True},
            "requirement_policy_version": {"versioned": True, "source_currentness_required": True},
            "requirement_applicability": {"context_bound": True, "unknown_is_blocking": True},
            "forms": {"versioned": True, "official_files_required": True},
            "form_automation_profile": {"renderer_and_contract_versioned": True},
            "mapping_release": {"versioned": True, "qa_gate_required": True},
            "writer_ownership": {"system_writable_fields": True, "human_authority_fields": False},
            "technical_rule_set_version": {"versioned": True, "source_lineage_required": True},
            "outputs": {"lineage_required": True, "generated_distinct_from_sent": True},
            "human_gates": ["PROPOSAL_ACCEPT", "CONTRACT_AUTHORITY", "PROJECT_ACTIVATION", "PROFESSIONAL_APPROVAL", "HUMAN_SUBMIT_AUTHORIZATION", "HANDOVER_ACCEPTANCE"],
            "submission_boundary": {"machine_submit": False, "external_confirmation_required": True},
            "closeout_axes": ["service_scope", "contract_admin", "regulatory", "financial", "archive"],
            "source_currentness": {"hash_and_version_lineage": True, "official_source_confirmation_required": True},
            "logical_storage_destinations": {"source": "AMEC_SYNOLOGY_LOGICAL_SOR", "synthetic_binding": "SYNTHETIC_SOR"},
        },
        "owner_dependent_fields": list(OWNER_DEPENDENT_FIELDS),
        "hard_coded_authority_policy": False,
    }


def validate_candidate_pack(pack: dict[str, Any]) -> dict[str, Any]:
    components = pack.get("components") or {}
    missing = sorted(set(REQUIRED_COMPONENTS) - set(components))
    owner_fields = sorted(set(OWNER_DEPENDENT_FIELDS) - set(pack.get("owner_dependent_fields") or []))
    invalid_approval = pack.get("production_approved") is True and pack.get("selected") is not True
    checks = {
        "required_components_present": not missing,
        "owner_dependent_fields_isolated": not owner_fields,
        "hard_coded_authority_policy_zero": pack.get("hard_coded_authority_policy") is False,
        "production_approval_not_inferred": not invalid_approval,
        "machine_submit_disabled": components.get("submission_boundary", {}).get("machine_submit") is False,
    }
    return {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "missing_components": missing,
        "unisolated_owner_fields": owner_fields,
    }
