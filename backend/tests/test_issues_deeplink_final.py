from urllib.parse import parse_qs, urlparse


def _issues(client, persona, headers=None):
    response = client.get("/api/issues", params={"persona": persona}, headers=headers or {})
    assert response.status_code == 200, response.text
    return response.json()["issues"]


def test_issue_rows_use_existing_context_routes_with_focus_query(client):
    rows = _issues(client, "OWNER", {"X-Dev-Role": "SYSTEM_ADMIN"})
    assert len(rows) >= 7
    assert all("issue" in parse_qs(urlparse(row["deep_link"]).query) for row in rows)
    assert all(not urlparse(row["deep_link"]).path.startswith("/issues/") for row in rows)
    assert {urlparse(row["deep_link"]).path.split("/")[1] for row in rows} >= {"proposals", "contracts", "proposals-contracts"}


def test_persona_routes_preserve_actionability_and_context_only_targets(client):
    bd = _issues(client, "BUSINESS_DEVELOPMENT", {"X-Dev-Role": "COMMERCIAL_APPROVER"})
    engineering = _issues(client, "ENGINEERING", {"X-Dev-Role": "RESPONSIBLE_ENGINEER"})
    bd_technical = next(item for item in bd if item["domain"] == "PROPOSAL_TECHNICAL")
    bd_commercial = next(item for item in bd if item["domain"] == "PROPOSAL_COMMERCIAL")
    engineering_technical = next(item for item in engineering if item["domain"] == "PROPOSAL_TECHNICAL")
    assert bd_technical["actionability"] == "CONTEXT_ONLY"
    assert urlparse(bd_technical["deep_link"]).path.count("/") == 2
    assert bd_commercial["actionability"] == "ACTIONABLE"
    assert urlparse(bd_commercial["deep_link"]).path.count("/") == 2
    assert engineering_technical["actionability"] == "ACTIONABLE"
    assert urlparse(engineering_technical["deep_link"]).path.endswith("/preparation")


def test_issue_backed_work_and_target_api_reject_cross_entity_focus(client):
    work = client.get("/api/work", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert work.status_code == 200
    issue_items = [item for item in work.json()["items"] if item.get("issue_id")]
    assert issue_items
    assert all("issue=" in item["deep_link"] and not item["deep_link"].startswith("/issues/") for item in issue_items)
    rows = _issues(client, "OWNER", {"X-Dev-Role": "SYSTEM_ADMIN"})
    permit = next(item for item in rows if item["domain"] == "PERMIT_TECHNICAL")
    unrelated = next(item for item in rows if item["domain"] == "PROPOSAL_TECHNICAL")
    project_id = urlparse(permit["deep_link"]).path.split("/")[2]
    response = client.get(f"/api/projects/{project_id}", params={"issue": unrelated["id"]})
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ISSUE_PROJECT_MISMATCH"


def test_context_only_persona_cannot_mutate_engineering_or_permit_state(client):
    register = client.get("/api/proposals-main", params={"persona": "SYSTEM_ADMIN"}).json()
    preparation = next(row for row in register["rows"] if row["proposal_status"] == "PROPOSAL_PREPARATION")
    ready = client.post(f"/api/proposals-main/proposals/{preparation['id']}/engineering-ready", headers={"X-Dev-Role": "COMMERCIAL_APPROVER"})
    assert ready.status_code == 403
    project = next(item for item in client.get("/api/projects").json() if item["project_number"] == "GHCE-2026-0142")
    confirm = client.post(f"/api/projects/{project['id']}/confirm-project-sources", headers={"X-Dev-Role": "COMMERCIAL_APPROVER"}, json={"project_reference": project["project_number"]})
    assert confirm.status_code == 403
