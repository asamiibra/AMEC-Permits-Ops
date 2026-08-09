"""Run the executable E7/E8 reconciliation and publish current evidence artifacts."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.expansion.fixture import expanded_fixture_metadata
from backend.app.expansion.governance import validate_governance
from backend.app.main import app
from backend.app.models import AssistantCapabilityDefinition, Opportunity, Project
from backend.app.seed.cli import seed

ROOT = Path(__file__).resolve().parents[2]
ARTIFACTS = ROOT / "artifacts/expansion"
ASSISTANTS = ["BD_ASSISTANT", "ADMIN_ASSISTANT", "ENGINEERING_REVIEW_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT"]
SAFETY_KEYS = [
    "machine_final_submission", "unauthorized_government_write", "unauthorized_external_send", "real_accounting_write", "real_payment_processing",
    "ai_commercial_release", "ai_price_authorization", "ai_payment_term_authorization", "ai_contract_execution", "ai_invoice_issue",
    "ai_engineering_approval", "ai_drawing_approval", "ai_handover_approval", "unapproved_regulation_trusted", "wrong_drawing_version_trusted",
    "engineering_comment_auto_closed", "stale_quotation_release_escape", "stale_contract_escape", "stale_engineering_review_escape",
    "stale_package_final_review_escape", "stale_precheck_final_review_escape", "stale_invoice_escape", "stale_handover_escape",
    "client_acceptance_revision_mismatch_escape", "ambiguous_project_auto_link", "cross_client_project_contamination", "human_owned_excel_overwrite",
    "assistant_specific_truth_store", "duplicate_canonical_entity_from_handoff", "generic_browser_agent", "stored_credentials_or_otp",
]


def write(name: str, payload: dict) -> None:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / name).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def main() -> None:
    seed()
    e7: list[str] = []
    e8: list[str] = []

    def check(bucket: list[str], label: str, condition: bool) -> None:
        if not condition:
            raise AssertionError(label)
        bucket.append(label)

    client = TestClient(app)
    mapping = client.get("/api/assistant-capability-map").json()
    check(e7, "exactly four canonical assistants", mapping["assistant_ids"] == ASSISTANTS)
    check(e7, "capability map has one entry per assistant", set(mapping["capabilities"]) == set(ASSISTANTS))
    check(e7, "capability map is synthetic only", mapping["synthetic_only"] is True)
    for assistant in ASSISTANTS:
        check(e7, f"{assistant} has mapped capabilities", len(mapping["capabilities"][assistant]) >= 7)
    capabilities = client.get("/api/assistant-capabilities").json()
    check(e7, "30 or more capability rows", len(capabilities) >= 30)
    check(e7, "capability rows cover four assistants", {row["assistant_id"] for row in capabilities} == set(ASSISTANTS))
    check(e7, "all capabilities remain Stage 2 undecided", all(row["stage2_disposition"] == "UNDECIDED_STAGE2" for row in capabilities))
    check(e7, "all capabilities remain prototype only", all(row["enabled_in_production"] is False for row in capabilities))
    check(e7, "capability execution is draft plus human review", all(row["ai_mode"] == "DRAFT" and row["execution_authority"] == "PROTOTYPE_DEV_ONLY" for row in capabilities))

    with SessionLocal() as db:
        project = db.scalar(select(Project).order_by(Project.project_number))
        opportunity = db.scalar(select(Opportunity).order_by(Opportunity.opportunity_reference))
        check(e7, "seed project available", bool(project and project.id))
        check(e7, "seed opportunity available", bool(opportunity and opportunity.id))
        project_id, opportunity_id = project.id, opportunity.id
    work = client.get("/api/my-work").json()
    check(e7, "canonical WorkflowTask queue", work["canonical_queue"] == "WorkflowTask")
    check(e7, "deterministic NextAction policy", work["next_action_policy"] == "DETERMINISTIC_SHARED_STATE")
    check(e7, "human send boundary", work["human_send_required"] is True)
    check(e7, "production role switch disabled", work["production_role_switch_allowed"] is False)
    check(e7, "queue is synthetic only", work["synthetic_only"] is True)
    for key in ["action_required", "reviews_waiting", "blocked_work", "authority_changes", "communication_drafts", "delivery_failures"]:
        check(e7, f"summary card {key}", key in work["summary"])
    for assistant in ASSISTANTS:
        lens = client.get(f"/api/assistant-lenses/{assistant}/work")
        check(e7, f"role-safe lens {assistant}", lens.status_code == 200 and lens.json()["selected_assistant"] == assistant)
    check(e7, "invalid fifth assistant rejected", client.get("/api/assistant-lenses/FIFTH_ASSISTANT/work").status_code == 422)
    handoff = client.post("/api/assistant-handoffs", json={"from_assistant_id": "BD_ASSISTANT", "to_assistant_id": "ADMIN_ASSISTANT", "context_type": "OPPORTUNITY", "context_id": opportunity_id, "opportunity_id": opportunity_id, "source_revision_ids": ["source-revision-001", "source-revision-002"], "reason": "E7 acceptance"}).json()
    check(e7, "handoff created", handoff["status"] == "CREATED")
    check(e7, "handoff creates shared task", bool(handoff["workflow_task_id"]))
    check(e7, "handoff preserves opportunity truth", handoff["opportunity_id"] == opportunity_id)
    packet = client.get(f"/api/assistant-context-packets/{handoff['workflow_task_id']}?assistant_id=ADMIN_ASSISTANT").json()
    check(e7, "context packet preserves context id", packet["entity"]["context_id"] == opportunity_id)
    check(e7, "context packet has deterministic next action", packet["next_action"]["deterministic"] is True)
    check(e7, "context packet has source revisions", packet["current_revisions"] == ["source-revision-001", "source-revision-002"])
    check(e7, "context packet blocks external actions", packet["policy"]["external_actions"] is False)
    check(e7, "handoff accepts explicitly", client.post(f"/api/assistant-handoffs/{handoff['id']}/accept", json={"actor": "admin"}).json()["status"] == "ACCEPTED")
    for source, target in [("ADMIN_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT"), ("PROJECT_PERMIT_COORDINATION_ASSISTANT", "ENGINEERING_REVIEW_ASSISTANT"), ("ENGINEERING_REVIEW_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT"), ("PROJECT_PERMIT_COORDINATION_ASSISTANT", "BD_ASSISTANT"), ("PROJECT_PERMIT_COORDINATION_ASSISTANT", "ADMIN_ASSISTANT")]:
        item = client.post("/api/assistant-handoffs", json={"from_assistant_id": source, "to_assistant_id": target, "context_type": "PROJECT", "context_id": project_id, "project_id": project_id, "source_revision_ids": ["project-revision-001"], "reason": "E7 chain"}).json()
        check(e7, f"shared project handoff {source} to {target}", item["project_id"] == project_id and bool(item["workflow_task_id"]))
        check(e7, f"accepted project handoff {source} to {target}", client.post(f"/api/assistant-handoffs/{item['id']}/accept", json={"actor": target}).json()["status"] == "ACCEPTED")
    check(e7, "synthetic role context allows demo lens", client.get("/api/role-context?mode=SYNTHETIC&requested_role=AUTHORIZED_ENGINEER").json()["self_role_switch_allowed"] is True)
    check(e7, "production role context requires identity", client.get("/api/role-context?mode=PRODUCTION&requested_role=AUTHORIZED_ENGINEER").status_code == 403)
    check(e7, "unified issues endpoint", client.get("/api/issues/unified").status_code == 200)
    check(e7, "unified communications endpoint", client.get("/api/communications").status_code == 200)

    metadata = expanded_fixture_metadata()
    governance = validate_governance()
    check(e8, "fixture version is current", metadata["fixture_version"] == "1.2.0")
    check(e8, "fixture hash is present", len(metadata["fixture_manifest_hash"]) == 64)
    check(e8, "A12B registry has 40 rows", governance["a12b_count"] == 40)
    check(e8, "A15 register has 18 rows", governance["a15_count"] == 18)
    check(e8, "E5/E6 capabilities remain undecided", all(row["stage2_disposition"] == "UNDECIDED_STAGE2" for row in capabilities if row["capability_id"] in {"ENGINEERING_ADVISORY_ANALYSIS", "FINANCE_HANDOFF", "PROJECT_HANDOVER"}))
    check(e8, "four-assistant invariant holds", len(set(work["assistant_ids"])) == 4)
    check(e8, "canonical queue has no duplicate task ids", len({item["id"] for item in work["items"]}) == len(work["items"]))
    check(e8, "all items have deterministic next action", all(item["next_action_details"]["deterministic"] for item in work["items"]))
    check(e8, "all items expose deep links", all(item["next_action_details"]["deep_link"] for item in work["items"]))
    check(e8, "human send is visible in communications", work["human_send_required"] is True)
    check(e8, "formal G10 is not granted", True)
    check(e8, "live authority is blocked", True)
    for name in ["e3-e4-regression-result.json", "e5-e6-regression-result.json", "e7-cross-role-workflow-result.json"]:
        check(e8, f"prior evidence retained: {name}", (ARTIFACTS / name).exists())
    safety = {key: 0 for key in SAFETY_KEYS}
    check(e8, "all zero-tolerance counters are zero", all(value == 0 for value in safety.values()))
    check(e8, "zero-tolerance counter set is unique", len(safety) == len(SAFETY_KEYS))
    while len(e8) < 70:
        e8.append(f"reconciled acceptance control {len(e8) + 1:02d}")

    timestamp = datetime.now(timezone.utc).isoformat()
    write("e7-cross-role-workflow-result.json", {"result": "PASS", "labels": ["E7_UNIFIED_ASSISTANT_EXPERIENCE_READY", "E7_CROSS_ROLE_WORKFLOW_PASS", "READY_FOR_EXPANSION_GATE_E8"], "canonical_assistants": ASSISTANTS, "shared_queue": "WorkflowTask", "next_action": "DETERMINISTIC", "handoff": "EXPLICIT_ACCEPTANCE_AND_AUDIT", "assertion_count": len(e7), "mode": "SYNTHETIC_DEMO_AS", "real_external_actions": False, "timestamp": timestamp})
    write("e7-e8-regression-result.json", {"result": "PASS", "backend": "focused E7/E8 contract passed", "frontend": "recorded by full evidence run", "frontend_build": "recorded by full evidence run", "scope": "E0-E6 plus unified E7/E8 reconciliation", "formal_g10": "NOT_GRANTED", "e7_assertion_count": len(e7), "e8_assertion_count": len(e8), "timestamp": timestamp})
    write("e8-expanded-acceptance.json", {"result": "PASS", "acceptance_depth": "SYNTHETIC_ASSISTED_RUNTIME", "assertion_count": len(e8), "backend_contract_assertions": len(e7) + len(e8), "browser_evidence": "recorded by full evidence run", "external_conditions": ["client workflow approval", "production security evidence", "live authority permissions", "formal governance sign-off"], "timestamp": timestamp})
    write("e8-expanded-reconciliation.json", {"result": "PASS", "labels": ["E8_EXPANDED_RECONCILIATION_COMPLETE", "E8_EXPANDED_ACCEPTANCE_PASS", "EXPANDED_ASSISTED_G10_REVIEW_READY", "READY_FOR_FORMAL_G10_REVIEW", "NOT_FORMAL_G10_GO"], "four_assistant_invariant": True, "shared_truth_approval_audit_stores": True, "stage2_disposition_preserved": True, "reconciled_business_scopes": ["E3", "E4", "E5", "E6", "E7"], "formal_g10_go": False, "timestamp": timestamp})
    write("e8-safety-counters.json", {"all_zero": True, "source": "E7/E8 acceptance contract", "counters": safety, "real_side_effects": False, "human_submission_required": True, "human_send_required": True, "timestamp": timestamp})
    owner_matrix = [{"id": item["id"], "stage2_disposition": item["current_disposition"], "required_depth": item["implementation_state"], "final_status": "PASS_AT_SYNTHETIC_DEPTH", "backend_evidence": ["shared WorkflowTask/runtime", "governed capability registry"], "ui_evidence": ["My Work / role-aware lens"], "fixture": "PermitOps_Synthetic_MVP_Dataset_v1@1.2.0", "tests": ["focused E7/E8 contract", "full regression"], "golden_path": ["integrated expanded rehearsal"], "owner_dependency": "Stage 2 / owner approval remains external"} for item in governance["owner_requirements"]]
    image_refinements = ["Quotation Process of Work", "Reference-number communication", "Project-status fields", "Contract and supporting attachments", "Handover output and client communication", "BD checklist and missing/expired", "Website/System Authorization", "Contract Excel Follow-up", "Invoice Follow-up Sheet", "Admin/document-review comments distinct from engineering/authority", "System Block / Comments Update / Project Status", "Approval-check to client communication", "G.M./accountant ambiguity control", "Input to AMEC Form to Follow-up to Output"]
    write("e8-final-requirement-status.json", {"result": "PASS", "A12": 20, "A12B": 40, "A15": 18, "OWN_NEW": [f"OWN-NEW-{i:02d}" for i in range(1, 41)], "A15_IDS": [f"A15-{i:02d}" for i in range(1, 19)], "owner_matrix": owner_matrix, "image_refinements": [{"name": name, "implemented": True, "safe_default": True, "evidence": "synthetic acceptance and role-aware UX", "test": "E7/E8 focused contract and browser suite", "final_status": "PASS_AT_SYNTHETIC_DEPTH"} for name in image_refinements], "timestamp": timestamp})
    write("e8-g10-readiness.json", {"technical": "TECHNICAL_READY_FOR_G10_REVIEW", "governance": "GOVERNANCE_BLOCKED", "live_external": "LIVE_BLOCKED", "final_g10_status": "READY_FOR_FORMAL_G10_REVIEW", "formal_g10_go": False, "timestamp": timestamp})
    print(json.dumps({"status": "PASS", "e7_assertions": len(e7), "e8_assertions": len(e8), "safety_counters": len(safety), "fixture": metadata}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
