from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import AuditEvent, NotificationEvent, NotificationReadState, WorkflowTask


def test_engineering_and_bd_issue_visibility_reconciles(client):
    engineering = client.get("/api/issues", params={"persona": "ENGINEERING"}).json()
    bd = client.get("/api/issues", params={"persona": "BUSINESS_DEVELOPMENT"}).json()
    owner = client.get("/api/issues", params={"persona": "OWNER"}).json()
    assert any(item["domain"] == "PROPOSAL_TECHNICAL" and item["actionability"] == "ACTIONABLE" for item in engineering["issues"])
    assert any(item["domain"] == "PROPOSAL_COMMERCIAL" and item["actionability"] == "ACTIONABLE" for item in bd["issues"])
    assert set(item["domain"] for item in owner["issues"]) >= {"PROPOSAL_COMMERCIAL", "PROPOSAL_TECHNICAL", "CONTRACT", "PERMIT_TECHNICAL", "AUTHORITY", "SYSTEM_INTEGRITY"}
    for persona, payload in [("ENGINEERING", engineering), ("BUSINESS_DEVELOPMENT", bd), ("OWNER", owner)]:
        summary = client.get("/api/issues/summary", params={"persona": persona}).json()["summary"]
        assert summary["open_issues"] == len(payload["issues"])


def test_one_event_projects_persona_specific_notification_messages(client):
    responses = [client.get("/api/notifications", params={"persona": persona}).json() for persona in ("OWNER", "BUSINESS_DEVELOPMENT", "ENGINEERING")]
    event_ids = {next(item for item in response["notifications"] if item["event_type"] == "ENGINEERING_PROPOSAL_READY")["source_event_id"] for response in responses}
    messages = {next(item for item in response["notifications"] if item["event_type"] == "ENGINEERING_PROPOSAL_READY")["message"] for response in responses}
    assert len(event_ids) == 1
    assert len(messages) == 3
    for persona, response in zip(("OWNER", "BUSINESS_DEVELOPMENT", "ENGINEERING"), responses):
        summary = client.get("/api/notifications/summary", params={"persona": persona}).json()["summary"]
        assert summary["unread"] == sum(item["unread"] for item in response["notifications"])


def test_notification_acknowledgement_does_not_complete_amec_work_task(client):
    with SessionLocal() as db:
        event = db.scalar(select(NotificationEvent).where(NotificationEvent.event_type == "AUTHORITY_COMMENT_CAPTURED"))
        task = db.get(WorkflowTask, event.workflow_task_id)
        task_status = task.status
    response = client.post(f"/api/notifications/{event.id}/acknowledge")
    assert response.status_code == 200
    assert response.json()["task_unchanged"] is True
    with SessionLocal() as db:
        assert db.get(WorkflowTask, event.workflow_task_id).status == task_status


def test_notification_read_state_is_persona_scoped_and_idempotent(client):
    event = client.get("/api/notifications", params={"persona": "OWNER"}).json()["notifications"]
    sources = next(item for item in event if item["event_type"] == "PROJECT_SOURCES_CONFIRMED")
    owner_headers = {"X-Dev-Role": "SYSTEM_ADMIN", "X-Dev-User": "demo:owner"}
    engineering_headers = {"X-Dev-Role": "RESPONSIBLE_ENGINEER", "X-Dev-User": "demo:engineering"}
    owner_before = client.get("/api/notifications/summary", params={"persona": "OWNER"}, headers=owner_headers).json()["summary"]["unread"]
    engineering_before = client.get("/api/notifications/summary", params={"persona": "ENGINEERING"}, headers=engineering_headers).json()["summary"]["unread"]
    with SessionLocal() as db:
        audit_before = db.query(AuditEvent).filter(AuditEvent.event_type == "NOTIFICATION_ACKNOWLEDGED").count()
    first = client.post(f"/api/notifications/{sources['id']}/acknowledge?persona=OWNER", headers=owner_headers)
    second = client.post(f"/api/notifications/{sources['id']}/acknowledge?persona=OWNER", headers=owner_headers)
    assert first.status_code == 200 and first.json()["changed"] is True
    assert second.status_code == 200 and second.json()["changed"] is False
    owner_after = client.get("/api/notifications/summary", params={"persona": "OWNER"}, headers=owner_headers).json()["summary"]["unread"]
    engineering_after = client.get("/api/notifications/summary", params={"persona": "ENGINEERING"}, headers=engineering_headers).json()["summary"]["unread"]
    assert owner_after == owner_before - 1
    assert engineering_after == engineering_before
    with SessionLocal() as db:
        assert db.query(NotificationReadState).filter(NotificationReadState.notification_event_id == sources["id"], NotificationReadState.persona == "OWNER").count() == 1
        assert db.query(AuditEvent).filter(AuditEvent.event_type == "NOTIFICATION_ACKNOWLEDGED").count() == audit_before


def test_notification_mapping_and_context_are_canonical(client):
    sources = next(item for item in client.get("/api/notifications", params={"persona": "OWNER"}).json()["notifications"] if item["event_type"] == "PROJECT_SOURCES_CONFIRMED")
    assert sources["display_domain"] == "Permit · Sources"
    assert sources["cta_label"] == "Open Permit"
    assert sources["deep_link"].endswith("/verify-data")
    detail = client.get(f"/api/notifications/{sources['id']}", params={"persona": "OWNER"})
    assert detail.status_code == 200
    assert detail.json()["notification"]["id"] == sources["id"]


def test_unknown_persona_is_typed_error_not_fake_empty(client):
    response = client.get("/api/issues", params={"persona": "NOT_A_PERSONA"})
    assert response.status_code == 422
    assert "UNKNOWN_PERSONA" in response.json()["detail"]


def test_controlled_demo_role_is_authoritative_when_present(client):
    response = client.get("/api/issues", params={"persona": "ENGINEERING"}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert response.status_code == 200
    assert response.json()["persona"] == "OWNER"


def test_issue_deep_links_cover_proposal_contract_and_permit_contexts(client):
    rows = client.get("/api/issues", params={"persona": "OWNER"}).json()["issues"]
    links = {item["domain"]: item["deep_link"] for item in rows}
    assert links["PROPOSAL_COMMERCIAL"].startswith("/proposals/")
    assert links["CONTRACT"].startswith("/contracts/")
    assert links["PERMIT_TECHNICAL"].startswith("/proposals-contracts/")
