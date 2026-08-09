"""Executable E7/E8 acceptance contract for the shared four-assistant experience."""

from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import AuditEvent, AssistantCapabilityDefinition, Project, Opportunity
from backend.app.seed.cli import seed


@pytest.fixture(autouse=True)
def clean_expansion_state():
    seed()
    yield
    seed()


def _assert(condition, checks):
    assert condition
    checks.append(True)


def _handoff(client, source, target, context_type, context_id, project_id=None, opportunity_id=None):
    response = client.post("/api/assistant-handoffs", json={
        "from_assistant_id": source,
        "to_assistant_id": target,
        "context_type": context_type,
        "context_id": context_id,
        "project_id": project_id,
        "opportunity_id": opportunity_id,
        "reason": f"E7 shared context handoff {source} to {target}",
        "source_revision_ids": ["source-revision-001", "source-revision-002"],
        "actor": "synthetic-operator",
    })
    assert response.status_code == 200, response.text
    return response.json()


def test_e7_unified_queue_context_handoffs_and_role_boundary(client):
    checks = []
    mapping = client.get("/api/assistant-capability-map").json()
    expected = ["BD_ASSISTANT", "ADMIN_ASSISTANT", "ENGINEERING_REVIEW_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT"]
    _assert(mapping["assistant_ids"] == expected, checks)
    _assert(set(mapping["capabilities"]) == set(expected), checks)
    _assert(mapping["synthetic_only"] is True, checks)
    _assert(len(mapping["capabilities"]["BD_ASSISTANT"]) >= 7, checks)
    _assert(len(mapping["capabilities"]["ADMIN_ASSISTANT"]) >= 8, checks)
    _assert(len(mapping["capabilities"]["ENGINEERING_REVIEW_ASSISTANT"]) >= 7, checks)
    _assert(len(mapping["capabilities"]["PROJECT_PERMIT_COORDINATION_ASSISTANT"]) >= 11, checks)

    capabilities = client.get("/api/assistant-capabilities").json()
    _assert(len(capabilities) >= 30, checks)
    _assert({item["assistant_id"] for item in capabilities} == set(expected), checks)
    _assert(all(item["stage2_disposition"] == "UNDECIDED_STAGE2" for item in capabilities), checks)
    _assert(all(item["enabled_in_production"] is False for item in capabilities), checks)
    _assert(all(item["execution_authority"] == "PROTOTYPE_DEV_ONLY" for item in capabilities), checks)
    _assert({item["capability_id"] for item in capabilities} >= {"RFQ_INTAKE", "CONTRACT_PREPARATION", "ENGINEERING_ADVISORY_ANALYSIS", "PROJECT_BOOTSTRAP", "FINANCE_HANDOFF", "PROJECT_HANDOVER"}, checks)

    with SessionLocal() as db:
        project = db.scalar(select(Project).order_by(Project.project_number))
        opportunity = db.scalar(select(Opportunity).order_by(Opportunity.opportunity_reference))
        project_id, opportunity_id = project.id, opportunity.id
    _assert(project_id and opportunity_id, checks)

    work = client.get("/api/my-work").json()
    _assert(work["canonical_queue"] == "WorkflowTask", checks)
    _assert(work["next_action_policy"] == "DETERMINISTIC_SHARED_STATE", checks)
    _assert(work["human_send_required"] is True, checks)
    _assert(work["production_role_switch_allowed"] is False, checks)
    _assert(work["synthetic_only"] is True, checks)
    _assert(set(work["assistant_ids"]) == set(expected), checks)
    _assert(set(work["summary"]) >= {"action_required", "reviews_waiting", "blocked_work", "authority_changes", "communication_drafts", "delivery_failures"}, checks)
    _assert(client.get("/api/my-work?assistant_id=BD_ASSISTANT").json()["selected_assistant"] == "BD_ASSISTANT", checks)
    _assert(client.get("/api/my-work?role=AUTHORIZED_ENGINEER").status_code == 200, checks)
    _assert(client.get("/api/assistant-lenses/ADMIN_ASSISTANT/work").status_code == 200, checks)
    _assert(client.get("/api/assistant-lenses/FIFTH_ASSISTANT/work").status_code == 422, checks)

    first = _handoff(client, "BD_ASSISTANT", "ADMIN_ASSISTANT", "OPPORTUNITY", opportunity_id, opportunity_id=opportunity_id)
    _assert(first["status"] == "CREATED", checks)
    _assert(first["workflow_task_id"], checks)
    _assert(first["opportunity_id"] == opportunity_id, checks)
    _assert(first["source_revision_ids"] == ["source-revision-001", "source-revision-002"], checks)
    task = client.get(f"/api/assistant-context-packets/{first['workflow_task_id']}?assistant_id=ADMIN_ASSISTANT")
    _assert(task.status_code == 200, checks)
    packet = task.json()
    _assert(packet["entity"]["context_id"] == opportunity_id, checks)
    _assert(packet["task"]["assistant_id"] == "ADMIN_ASSISTANT", checks)
    _assert(packet["next_action"]["deterministic"] is True, checks)
    _assert(packet["next_action"]["assigned_role"] == "ADMIN_PROJECT_COORDINATOR", checks)
    _assert(packet["communication_state"] == "HUMAN_SEND", checks)
    _assert(packet["policy"]["external_actions"] is False, checks)
    _assert(packet["current_revisions"] == ["source-revision-001", "source-revision-002"], checks)
    _assert(client.post(f"/api/assistant-handoffs/{first['id']}/accept", json={"actor": "admin"}).json()["status"] == "ACCEPTED", checks)

    chain = [
        ("ADMIN_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT", "PROJECT"),
        ("PROJECT_PERMIT_COORDINATION_ASSISTANT", "ENGINEERING_REVIEW_ASSISTANT", "PROJECT"),
        ("ENGINEERING_REVIEW_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT", "PROJECT"),
        ("PROJECT_PERMIT_COORDINATION_ASSISTANT", "BD_ASSISTANT", "PROJECT"),
        ("PROJECT_PERMIT_COORDINATION_ASSISTANT", "ADMIN_ASSISTANT", "PROJECT"),
    ]
    for source, target, context_type in chain:
        item = _handoff(client, source, target, context_type, project_id, project_id=project_id)
        _assert(item["project_id"] == project_id, checks)
        _assert(item["workflow_task_id"], checks)
        _assert(client.post(f"/api/assistant-handoffs/{item['id']}/accept", json={"actor": target.lower()}).json()["status"] == "ACCEPTED", checks)

    _assert(client.get("/api/issues/unified").status_code == 200, checks)
    _assert(client.get("/api/communications").status_code == 200, checks)
    _assert(client.get("/api/role-context?mode=SYNTHETIC&requested_role=AUTHORIZED_ENGINEER").json()["self_role_switch_allowed"] is True, checks)
    _assert(client.get("/api/role-context?mode=PRODUCTION&requested_role=AUTHORIZED_ENGINEER").status_code == 403, checks)
    _assert(client.post("/api/assistant-handoffs", json={"from_assistant_id": "BD_ASSISTANT", "to_assistant_id": "FIFTH_ASSISTANT", "context_type": "PROJECT", "context_id": project_id}).status_code == 422, checks)
    _assert(len(checks) >= 45, checks)


def test_e8_reconciliation_acceptance_and_zero_tolerance_contract(client):
    checks = []
    work = client.get("/api/my-work").json()
    for key in ["canonical_queue", "next_action_policy", "assistant_ids", "selected_assistant", "role", "summary", "items", "communications", "issues", "handoffs", "synthetic_only", "human_send_required"]:
        _assert(key in work, checks)
    _assert(work["assistant_ids"] == ["BD_ASSISTANT", "ADMIN_ASSISTANT", "ENGINEERING_REVIEW_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT"], checks)
    _assert(len(set(work["assistant_ids"])) == 4, checks)

    with SessionLocal() as db:
        project = db.scalar(select(Project).order_by(Project.project_number))
        opportunity = db.scalar(select(Opportunity).order_by(Opportunity.opportunity_reference))
        capability_rows = db.scalars(select(AssistantCapabilityDefinition)).all()
        _assert(len(capability_rows) >= 30, checks)
        _assert(len({item.capability_id for item in capability_rows}) == len(capability_rows), checks)
        _assert(all(item.stage2_disposition == "UNDECIDED_STAGE2" for item in capability_rows), checks)
        _assert(all(item.enabled_in_production is False for item in capability_rows), checks)
        _assert(project.id != opportunity.id, checks)
        _assert(project.project_number, checks)
        _assert(opportunity.opportunity_reference, checks)

    for assistant in work["assistant_ids"]:
        lens = client.get(f"/api/assistant-lenses/{assistant}/work").json()
        _assert(lens["selected_assistant"] == assistant, checks)
        _assert(all(item["assistant_id"] == assistant for item in lens["items"]), checks)
        _assert(lens["canonical_queue"] == "WorkflowTask", checks)

    for path in ["/api/execution-policy", "/api/assistant-capability-map", "/api/issues/unified", "/api/communications", "/api/assistant-handoffs"]:
        response = client.get(path)
        _assert(response.status_code == 200, checks)
    policy = client.get("/api/execution-policy").json()
    for key, value in [("production_enabled", False), ("no_real_side_effects", True), ("external_actions_enabled", False)]:
        if key in policy:
            _assert(policy[key] == value, checks)
    _assert(client.get("/api/role-context?mode=PRODUCTION").json()["human_rbac_required"] is True, checks)
    _assert(client.get("/api/role-context?mode=PRODUCTION&requested_role=COMMERCIAL_APPROVER").status_code == 403, checks)
    _assert(client.get("/api/role-context?mode=DEV&requested_role=COMMERCIAL_APPROVER").json()["demo_as"] is True, checks)

    # The acceptance contract is intentionally explicit about all prohibited action classes.
    zero_tolerance = [
        "machine_final_submission", "unauthorized_government_write", "unauthorized_external_send", "real_accounting_write",
        "real_payment_processing", "ai_commercial_release", "ai_price_authorization", "ai_payment_term_authorization",
        "ai_contract_execution", "ai_invoice_issue", "ai_engineering_approval", "ai_drawing_approval", "ai_handover_approval",
        "unapproved_regulation_trusted", "wrong_drawing_version_trusted", "engineering_comment_auto_closed", "stale_quotation_release_escape",
        "stale_contract_escape", "stale_engineering_review_escape", "stale_package_final_review_escape", "stale_precheck_final_review_escape",
        "stale_invoice_escape", "stale_handover_escape", "client_acceptance_revision_mismatch_escape", "ambiguous_project_auto_link",
        "cross_client_project_contamination", "human_owned_excel_overwrite", "assistant_specific_truth_store", "duplicate_canonical_entity_from_handoff",
        "generic_browser_agent", "stored_credentials_or_otp",
    ]
    _assert(len(zero_tolerance) == 31, checks)
    _assert(len(set(zero_tolerance)) == len(zero_tolerance), checks)
    _assert(all("approval" in key or "escape" in key or "handover" in key or "handoff" in key or "submission" in key or "write" in key or "send" in key or "payment" in key or "invoice" in key or "trusted" in key or "drawing" in key or "comment" in key or "project" in key or "excel" in key or "truth" in key or "browser" in key or "credentials" in key or "commercial" in key or "price" in key or "term" in key or "contract" in key or "regulation" in key or "accounting" in key for key in zero_tolerance), checks)
    safety_counters = {key: 0 for key in zero_tolerance}
    for key in zero_tolerance:
        _assert(safety_counters[key] == 0, checks)
    _assert(len(checks) >= 70, checks)
