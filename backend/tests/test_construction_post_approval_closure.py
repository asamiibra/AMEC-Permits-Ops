from uuid import uuid4


OWNER = {"X-Dev-Role": "OWNER_SPONSOR"}


def _project_and_execution(client, prefix: str):
    suffix = uuid4().hex[:10]
    project = client.post(
        "/api/projects",
        headers=OWNER,
        json={"project_number": f"{prefix}-P-{suffix}", "project_name": "Synthetic construction closure project", "municipality": "Doha", "permit_type": "Building"},
    )
    assert project.status_code == 200, project.text
    project_body = project.json()
    execution = client.post(
        "/api/construction/executions",
        headers=OWNER,
        json={"project_id": project_body["id"], "execution_ref": f"{prefix}-E-{suffix}", "title": "Synthetic post-approval execution", "scope_description": "Closure verification scope"},
    )
    assert execution.status_code == 200, execution.text
    return project_body, execution.json()


def test_construction_start_boundary_and_completion_context_are_explicit(client):
    project, execution = _project_and_execution(client, "CLOSE-GATE")
    execution_id = execution["id"]

    readiness = client.post(f"/api/construction/executions/{execution_id}/readiness", headers=OWNER, json={})
    assert readiness.status_code == 200
    assert readiness.json()["result"] == "NOT_READY"

    unauthorized_start = client.post(f"/api/construction/executions/{execution_id}/work-events", headers=OWNER, json={"event_type": "START", "idempotency_key": "closure-unauthorized-start-1"})
    assert unauthorized_start.status_code == 409
    assert "ConstructionStartAuthorization" in unauthorized_start.json()["detail"]

    invalid_stop = client.post(f"/api/construction/executions/{execution_id}/work-events", headers=OWNER, json={"event_type": "STOP", "idempotency_key": "closure-invalid-stop-1"})
    assert invalid_stop.status_code == 409
    assert invalid_stop.json()["detail"]["code"] == "INVALID_WORK_STATE_TRANSITION"

    context = client.get(f"/api/construction/executions/{execution_id}/completion-context")
    assert context.status_code == 200
    assert context.json()["completion_scope_deferred"] is True
    assert context.json()["as_built_scope"] == "DEFERRED"
    assert context.json()["handover_scope"] == "DEFERRED"
    assert context.json()["financial_settlement_scope"] == "DEFERRED"
    assert context.json()["construction_execution"]["project_id"] == project["id"]


def test_construction_notifications_correspondence_inspections_and_issue_are_distinct(client):
    _, execution = _project_and_execution(client, "CLOSE-EVIDENCE")
    execution_id = execution["id"]

    notification_payload = {"notification_type": "START_NOTICE", "recipient_snapshot": {"party": "synthetic"}, "payload_snapshot": {"synthetic": True}, "idempotency_key": "closure-notification-1"}
    prepared = client.post(f"/api/construction/executions/{execution_id}/notifications", headers=OWNER, json=notification_payload)
    retry = client.post(f"/api/construction/executions/{execution_id}/notifications", headers=OWNER, json=notification_payload)
    assert prepared.status_code == retry.status_code == 200
    assert prepared.json()["id"] == retry.json()["id"]
    assert prepared.json()["status"] == "PREPARED"
    sent = client.post(f"/api/construction/notifications/{prepared.json()['id']}/send", headers=OWNER, json={"external_reference": "SYNTHETIC-NOT-SENT-1"})
    assert sent.status_code == 200
    assert sent.json()["status"] == "SENT"
    assert sent.json()["external_reference"] == "SYNTHETIC-NOT-SENT-1"

    correspondence = client.post(f"/api/construction/executions/{execution_id}/correspondence", headers=OWNER, json={"direction": "OUTBOUND", "subject": "Synthetic construction correspondence", "status": "PREPARED"})
    assert correspondence.status_code == 200
    assert correspondence.json()["construction_execution_id"] == execution_id

    internal = client.post(f"/api/construction/executions/{execution_id}/inspections", headers=OWNER, json={"inspection_kind": "INTERNAL_SITE", "idempotency_key": "closure-internal-inspection-1"})
    internal_retry = client.post(f"/api/construction/executions/{execution_id}/inspections", headers=OWNER, json={"inspection_kind": "INTERNAL_SITE", "idempotency_key": "closure-internal-inspection-1"})
    authority = client.post(f"/api/construction/executions/{execution_id}/inspections", headers=OWNER, json={"inspection_kind": "AUTHORITY", "idempotency_key": "closure-authority-inspection-1"})
    assert internal.status_code == authority.status_code == 200
    assert internal_retry.json()["id"] == internal.json()["id"]
    assert {internal.json()["inspection_kind"], authority.json()["inspection_kind"]} == {"INTERNAL_SITE", "AUTHORITY"}
    recorded = client.post(f"/api/construction/inspections/{internal.json()['id']}/record", headers=OWNER, json={"outcome": "PASS", "status": "COMPLETED"})
    assert recorded.status_code == 200
    assert recorded.json()["inspection_kind"] == "INTERNAL_SITE"

    issue = client.post(f"/api/construction/executions/{execution_id}/issues", headers=OWNER, json={"issue_ref": "CLOSE-ISSUE-1", "category": "SITE", "severity": "MINOR", "description": "Synthetic construction issue"})
    assert issue.status_code == 200
    assert issue.json()["construction_execution_id"] == execution_id
    assert issue.json()["authority_case_finding_id"] is None


def test_construction_execution_list_is_project_scoped(client):
    first_project, first_execution = _project_and_execution(client, "CLOSE-SCOPE-A")
    second_project, second_execution = _project_and_execution(client, "CLOSE-SCOPE-B")
    first_rows = client.get("/api/construction", params={"project_id": first_project["id"]})
    second_rows = client.get("/api/construction", params={"project_id": second_project["id"]})
    assert first_rows.status_code == second_rows.status_code == 200
    assert {row["id"] for row in first_rows.json()} == {first_execution["id"]}
    assert {row["id"] for row in second_rows.json()} == {second_execution["id"]}
