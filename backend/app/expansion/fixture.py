"""Controlled successor metadata for the Stage 1 v2.6 synthetic fixture."""
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
EXPANDED_FIXTURE_ID = "PermitOps_Synthetic_MVP_Dataset_v1"
EXPANDED_FIXTURE_VERSION = "1.2.0"
EXPANDED_FIXTURE_PREDECESSOR = {"name": "PermitOps_Synthetic_MVP_Dataset_v1", "version": "1.1.1", "manifest_hash": "b3a5fbee1a968e3740801b0b696b31a39a3a907437f2377fcdfdfad3bb3546cb"}
EXPANDED_RESOURCE_PATH = "synthetic-data/fixtures/expansion/stage1_v2_6_fixture.json"
SOURCE_FAMILIES = ["BD_COMMERCIAL", "CONTRACT_ADMIN", "PROJECT_REFERENCE", "ENGINEERING", "FINANCE", "HANDOVER", "COMMUNICATION", "PERMIT_CORE"]
SCENARIOS = ["EXPANSION_A_HAPPY_UPSTREAM_HANDOFF", "EXPANSION_B_MISSING_EXPIRED_DOCUMENT", "EXPANSION_C_ENGINEERING_REVIEW_FOUNDATION"]


def _manifest() -> dict[str, Any]:
    resources = [
        ("rfq_email.txt", "BD_COMMERCIAL", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("tender_document.txt", "BD_COMMERCIAL", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("client_master.txt", "BD_COMMERCIAL", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("quotation_template.txt", "BD_COMMERCIAL", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("quotation_revision.txt", "BD_COMMERCIAL", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("quotation_approval_evidence.txt", "BD_COMMERCIAL", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("client_acceptance_evidence.txt", "BD_COMMERCIAL", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("contract_template.txt", "CONTRACT_ADMIN", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("contract_revision.txt", "CONTRACT_ADMIN", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("contract_attachment.txt", "CONTRACT_ADMIN", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("contract_milestone.txt", "CONTRACT_ADMIN", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("client_checklist.txt", "CONTRACT_ADMIN", "EXPANSION_B_MISSING_EXPIRED_DOCUMENT"),
        ("missing_document_case.txt", "CONTRACT_ADMIN", "EXPANSION_B_MISSING_EXPIRED_DOCUMENT"),
        ("expired_document_case.txt", "CONTRACT_ADMIN", "EXPANSION_B_MISSING_EXPIRED_DOCUMENT"),
        ("missing_document_draft.txt", "COMMUNICATION", "EXPANSION_B_MISSING_EXPIRED_DOCUMENT"),
        ("reference_number_record.txt", "PROJECT_REFERENCE", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("project_status_representation.txt", "PROJECT_REFERENCE", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("engineering_drawing_v1.txt", "ENGINEERING", "EXPANSION_C_ENGINEERING_REVIEW_FOUNDATION"),
        ("synthetic_regulation_placeholder.txt", "ENGINEERING", "EXPANSION_C_ENGINEERING_REVIEW_FOUNDATION"),
        ("engineer_comment_sheet.txt", "ENGINEERING", "EXPANSION_C_ENGINEERING_REVIEW_FOUNDATION"),
        ("drawing_review_cycle.txt", "ENGINEERING", "EXPANSION_C_ENGINEERING_REVIEW_FOUNDATION"),
        ("invoice_draft.txt", "FINANCE", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("finance_handoff.txt", "FINANCE", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("handover_output.txt", "HANDOVER", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("handover_approval_placeholder.txt", "HANDOVER", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("rfq_followup_draft.txt", "COMMUNICATION", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("reference_number_draft.txt", "COMMUNICATION", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("invoice_draft_email.txt", "COMMUNICATION", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("approval_response_draft.txt", "COMMUNICATION", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
        ("handover_draft.txt", "COMMUNICATION", "EXPANSION_A_HAPPY_UPSTREAM_HANDOFF"),
    ]
    return {
        "fixture_set": EXPANDED_FIXTURE_ID,
        "version": EXPANDED_FIXTURE_VERSION,
        "predecessor": EXPANDED_FIXTURE_PREDECESSOR,
        "created_at": "2026-08-08T00:00:00Z",
        "reason": "Stage 1 v2.6 owner-session expansion foundation; historical permit fixture remains unchanged.",
        "source_family_count": len(SOURCE_FAMILIES),
        "scenario_count": len(SCENARIOS),
        "source_families": SOURCE_FAMILIES,
        "scenarios": SCENARIOS,
        "synthetic_only": True,
        "owner_session_expansion": True,
        "resources": [{"path": f"synthetic-data/fixtures/expansion/{name}", "type": "SYNTHETIC_TEXT_RESOURCE", "source_family": family, "scenario": scenario, "synthetic_label": "SYNTHETIC / NOT CLIENT APPROVED / NOT PRODUCTION"} for name, family, scenario in resources],
        "safety": {"real_credentials": False, "real_personal_identifiers": False, "authoritative_regulation_text": False, "external_actions": False},
    }


EXPANDED_FIXTURE_MANIFEST = _manifest()
EXPANDED_FIXTURE_MANIFEST_HASH = hashlib.sha256(json.dumps(EXPANDED_FIXTURE_MANIFEST, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def expanded_fixture_metadata() -> dict[str, Any]:
    return {"fixture_set": EXPANDED_FIXTURE_ID, "fixture_version": EXPANDED_FIXTURE_VERSION, "fixture_manifest_hash": EXPANDED_FIXTURE_MANIFEST_HASH, "predecessor": EXPANDED_FIXTURE_PREDECESSOR}
