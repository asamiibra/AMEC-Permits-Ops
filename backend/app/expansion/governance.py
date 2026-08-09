from pathlib import Path
from typing import Any
import yaml

ROOT = Path(__file__).resolve().parents[3]
OWNER_REGISTRY_PATH = ROOT / "config/stage1_v2_6_owner_session_requirements.yaml"
CLARIFICATION_REGISTRY_PATH = ROOT / "config/stage1_v2_6_owner_clarifications.yaml"

OWNER_IDS = [f"OWN-NEW-{i:02d}" for i in range(1, 41)]
CLARIFICATION_IDS = [f"A15-{i:02d}" for i in range(1, 19)]
ALLOWED_DISPOSITIONS = {"IN", "IN_REDUCED_DEPTH", "ROADMAP", "EXCLUDED", "UNDECIDED_STAGE2"}
ALLOWED_CLARIFICATION_STATUSES = {"OPEN_SAFE_DEFAULT_ACTIVE", "RESOLVED", "EXCLUDED_BY_SCOPE", "SUPERSEDED_BY_SIGNED_DECISION"}
REQUIREMENT_FAMILIES = {"BD_COMMERCIAL", "CONTRACT_ADMIN", "PROJECT_REFERENCE", "PERMIT", "ENGINEERING", "FINANCE", "HANDOVER", "COMMUNICATION", "ASSISTANT_CROSS_CUTTING", "GOVERNANCE"}
IMPLEMENTATION_STATES = {"REQUIREMENT_EXISTS", "CAPABILITY_DESIGNED", "CAPABILITY_IMPLEMENTED", "CAPABILITY_TESTED", "CAPABILITY_APPROVED_FOR_BUILD", "CAPABILITY_APPROVED_FOR_PRODUCTION", "GOVERNANCE_CONTROLLED"}
ASSISTANT_IDS = ["BD_ASSISTANT", "ADMIN_ASSISTANT", "ENGINEERING_REVIEW_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT"]
CAPABILITY_STATES = ["REQUIREMENT_EXISTS", "CAPABILITY_DESIGNED", "CAPABILITY_IMPLEMENTED", "CAPABILITY_TESTED", "CAPABILITY_APPROVED_FOR_BUILD", "CAPABILITY_APPROVED_FOR_PRODUCTION"]
APPROVAL_PURPOSES = ["COMMERCIAL_QUOTATION_RELEASE", "CONTRACT_APPROVAL", "COMMUNICATION_RELEASE", "FINANCE_INVOICE_APPROVAL", "ENGINEERING_DISPOSITION", "HANDOVER_RELEASE"]
EXPANSION_ROLES = ["BD_USER", "COMMERCIAL_APPROVER", "ADMIN_PROJECT_COORDINATOR", "CONTRACT_APPROVER", "AUTHORIZED_ENGINEER", "FINANCE_ACCOUNTANT", "COMMUNICATION_APPROVER", "PERMIT_PREPARER", "DATA_VERIFIER", "RESPONSIBLE_ENGINEER", "PACKAGE_APPROVER", "FINAL_SUBMITTER", "SYSTEM_ADMINISTRATOR", "AUDITOR"]


def load_owner_requirements() -> list[dict[str, Any]]:
    return yaml.safe_load(OWNER_REGISTRY_PATH.read_text(encoding="utf-8"))["requirements"]


def load_clarifications() -> list[dict[str, Any]]:
    return yaml.safe_load(CLARIFICATION_REGISTRY_PATH.read_text(encoding="utf-8"))["clarifications"]


def validate_governance() -> dict[str, Any]:
    requirements = load_owner_requirements()
    clarifications = load_clarifications()
    requirement_ids = [item["id"] for item in requirements]
    clarification_ids = [item["id"] for item in clarifications]
    assert requirement_ids == OWNER_IDS, "A12B must contain OWN-NEW-01 through OWN-NEW-40 exactly once"
    assert len(set(requirement_ids)) == 40
    assert all(item["family"] in REQUIREMENT_FAMILIES for item in requirements)
    assert all(item["current_disposition"] in ALLOWED_DISPOSITIONS for item in requirements)
    assert all(item["implementation_state"] in IMPLEMENTATION_STATES for item in requirements)
    assert all(item["current_disposition"] != "IN" or item.get("owner_decision_required") is False for item in requirements if item["current_disposition"] == "IN")
    assert clarification_ids == CLARIFICATION_IDS, "A15 must contain A15-01 through A15-18 exactly once"
    assert len(set(clarification_ids)) == 18
    assert all(item["status"] in ALLOWED_CLARIFICATION_STATUSES for item in clarifications)
    assert all(item.get("required_resolution_gate") and item.get("safe_default") for item in clarifications)
    return {"a12b_count": 40, "a15_count": 18, "assistant_ids": ASSISTANT_IDS, "owner_requirements": requirements, "clarifications": clarifications}
