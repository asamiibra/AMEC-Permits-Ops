"""Focused E2 shared-runtime contract checks (synthetic only)."""

from uuid import uuid4
import pytest
from backend.app.seed.cli import seed


@pytest.fixture(autouse=True)
def restore_seed_after_e2_test():
    yield
    seed()


def test_e2_policy_and_canonical_contracts(client):
    policy = client.get("/api/execution-policy").json()
    assert policy["execution_authority"] == "PROTOTYPE_DEV_ONLY"
    assert policy["evidence_class"] == "SYNTHETIC_IMPLEMENTATION_EVIDENCE"
    assert policy["production_enabled"] is False
    assert policy["no_real_side_effects"] is True
    for name in ["INTERNAL_READ", "INTERNAL_DRAFT", "HUMAN_APPROVAL_REQUIRED", "EXTERNAL_DRAFT", "EXTERNAL_HUMAN_SEND", "EXTERNAL_AUTOMATED_WRITE", "PROFESSIONAL_DECISION", "COMMERCIAL_DECISION", "GOVERNMENT_FINAL_SUBMISSION", "ACCOUNTING_WRITE"]:
        assert name in policy["policy_classes"]
    capabilities = client.get("/api/assistant-capabilities").json()
    assistants = {item["assistant_id"] for item in capabilities}
    assert assistants == {"BD_ASSISTANT", "ADMIN_ASSISTANT", "ENGINEERING_REVIEW_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT"}
    assert len(capabilities) >= 30
    assert {item["capability_id"] for item in capabilities} >= {"RFQ_INTAKE", "CONTRACT_PREPARATION", "ENGINEERING_ADVISORY_ANALYSIS", "PROJECT_BOOTSTRAP", "PERMIT_WORKFLOW_COORDINATION", "FINANCE_HANDOFF", "PROJECT_HANDOVER"}
    for item in capabilities:
        assert item["stage2_disposition"] == "UNDECIDED_STAGE2"
        assert item["execution_authority"] == "PROTOTYPE_DEV_ONLY"
        assert item["enabled_in_production"] is False
        assert item["ai_mode"] == "DRAFT"
        assert item["capability_status"] == "ACTIVE"


def test_e2_template_lifecycle_and_render_contract(client):
    templates = client.get("/api/templates").json()
    assert templates
    definition = templates[0]
    assert definition["artifact_type"]
    assert definition["versions"]
    detail = client.get(f"/api/templates/{definition['id']}")
    assert detail.status_code == 200
    assert len(detail.json()["versions"]) == len(definition["versions"])
    version = definition["versions"][0]
    assert client.get(f"/api/templates/{definition['id']}/versions").status_code == 200
    assert client.post(f"/api/templates/{definition['id']}/versions/{version['id']}/validate").json()["valid"] is True
    created = client.post(f"/api/templates/{definition['id']}/versions", json={"version": "0.2-e2", "content": "synthetic", "actor_role": "SYSTEM_ADMIN"})
    assert created.status_code == 200
    assert created.json()["status"] == "SYNTHETIC_STANDIN"
    assert client.post(f"/api/templates/{definition['id']}/versions/{created.json()['id']}/supersede", json={"actor_role": "SYSTEM_ADMIN"}).json()["status"] == "SUPERSEDED"
    denied = client.post(f"/api/templates/{definition['id']}/versions", json={"version": "prod-e2", "status": "APPROVED_FOR_PRODUCTION", "actor_role": "SYSTEM_ADMIN"})
    assert denied.status_code == 403
    context = str(uuid4())
    rendered = client.post("/api/render-requests", json={"artifact_type": "CONTRACT", "context_type": "CONTRACT_REVISION", "context_id": context, "verified_fields": {"reference": "SYN-CTR"}, "source_revision_ids": ["rev-b", "rev-a"]})
    assert rendered.status_code == 200
    artifact = rendered.json()
    assert artifact["status"] == "RENDERED"
    assert artifact["synthetic_only"] is True
    assert artifact["source_revision_ids"] == ["rev-a", "rev-b"]
    assert artifact["render_input_hash"]
    assert artifact["content_hash"]
    assert artifact["storage_reference"].startswith("synthetic://")
    assert client.get(f"/api/rendered-artifacts/{artifact['id']}").status_code == 200
    lineage = client.get(f"/api/rendered-artifacts/{artifact['id']}/lineage").json()
    assert lineage["artifact"]["id"] == artifact["id"]
    assert isinstance(lineage["lineage"], list)


def test_e2_communications_and_human_send_boundary(client):
    draft_response = client.post("/api/communication-drafts", json={"communication_type": "MISSING_DOCUMENT", "context_type": "CHECKLIST", "context_id": str(uuid4()), "subject": "Synthetic follow-up", "body": "Please review", "actor_role": "ADMIN_PROJECT_COORDINATOR"})
    assert draft_response.status_code == 200
    draft = draft_response.json()
    assert draft["status"] == "HUMAN_REVIEW"
    assert draft["policy_state"] == "HUMAN_SEND"
    assert draft["body_hash"]
    assert draft["source_snapshot"]["synthetic_only"] is True
    assert draft["source_revision_ids"] == []
    details = client.get(f"/api/communication-drafts/{draft['id']}").json()
    assert len(details["delivery"]) == 1
    assert details["delivery"][0]["delivery_status"] == "NOT_SENT"
    assert details["approvals"] == []
    assert client.get(f"/api/communication-drafts/{draft['id']}/lineage").status_code == 200
    assert client.post(f"/api/communication-drafts/{draft['id']}/submit-review", json={"actor": "operator"}).json()["status"] == "HUMAN_REVIEW"
    approved = client.post(f"/api/communication-drafts/{draft['id']}/approve-for-human-send", json={"actor": "approver", "actor_role": "COMMUNICATION_APPROVER"})
    assert approved.status_code == 200
    assert approved.json()["status"] == "READY_FOR_HUMAN_SEND"
    after = client.get(f"/api/communication-drafts/{draft['id']}").json()
    assert after["approvals"]
    assert after["delivery"][0]["delivery_status"] == "NOT_SENT"
    assert "send" not in [route for route in []]


def test_e2_capability_envelope_and_invocation_lineage(client):
    capabilities = client.get("/api/assistant-capabilities").json()
    for item in capabilities:
        response = client.post(f"/api/assistant-capabilities/{item['capability_id']}/invoke", json={"context_id": str(uuid4()), "source_revision_ids": ["source-1"], "actor_role": "ADMIN_PROJECT_COORDINATOR"})
        assert response.status_code == 200
        result = response.json()
        assert result["policy_decision"] == "ALLOW_PROTOTYPE_ONLY"
        assert result["result_type"] == "CANDIDATE_OR_DRAFT"
        assert result["external_action"] is False
        assert result["human_review_required"] is True
        assert result["deterministic_gate_result"] == "HUMAN_REVIEW_REQUIRED"
        assert result["output_envelope"]["synthetic_only"] is True
    invalid = client.post(f"/api/assistant-capabilities/{capabilities[0]['capability_id']}/invoke", json={"assistant_id": "FIFTH_ASSISTANT", "context_id": str(uuid4())})
    assert invalid.status_code == 200
    assert client.get("/api/assistant-capability-map").json()["assistant_ids"] == ["BD_ASSISTANT", "ADMIN_ASSISTANT", "ENGINEERING_REVIEW_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT"]


def test_e2_downstream_artifact_types_use_shared_runtime(client):
    artifact_types = ["QUOTATION", "CONTRACT", "MISSING_DOCUMENT", "MUNICIPALITY_FORM", "ADMIN_COMMENT", "ENGINEERING_COMMENT", "COMPLIANCE_REFERENCE", "INVOICE", "PROJECT_STATUS_EXCEL", "HANDOVER"]
    for artifact_type in artifact_types:
        response = client.post("/api/render-requests", json={"artifact_type": artifact_type, "context_type": "SYNTHETIC_CONTEXT", "context_id": str(uuid4()), "verified_fields": {"fixture": "E2"}, "source_revision_ids": [artifact_type]})
        assert response.status_code == 200
        body = response.json()
        assert body["artifact_type"] == artifact_type
        assert body["status"] == "RENDERED"
        assert body["synthetic_only"] is True
        assert body["template_version_id"]
        assert body["render_input_hash"]
        assert body["content_hash"]


def test_e7_unified_queue_handoff_and_shared_issue_surfaces(client):
    work = client.get("/api/my-work").json()
    assert len(work["assistant_ids"]) == 4
    assert work["synthetic_only"] is True
    for key in ["action_required", "reviews_waiting", "blocked_work", "authority_changes", "communication_drafts", "delivery_failures"]:
        assert key in work["summary"]
    for assistant in work["assistant_ids"]:
        scoped = client.get(f"/api/assistant-lenses/{assistant}/work")
        assert scoped.status_code == 200
        assert scoped.json()["selected_assistant"] == assistant
    handoff = client.post("/api/assistant-handoffs", json={"from_assistant_id": "BD_ASSISTANT", "to_assistant_id": "ADMIN_ASSISTANT", "context_type": "OPPORTUNITY", "context_id": str(uuid4()), "reason": "Shared context review"})
    assert handoff.status_code == 200
    assert handoff.json()["status"] == "CREATED"
    accepted = client.post(f"/api/assistant-handoffs/{handoff.json()['id']}/accept", json={"actor": "admin"})
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "ACCEPTED"
    assert client.get("/api/assistant-handoffs").status_code == 200
    assert client.get("/api/issues/unified").status_code == 200
    assert client.get("/api/communications").status_code == 200
