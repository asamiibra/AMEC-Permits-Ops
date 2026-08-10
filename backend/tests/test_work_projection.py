import pytest


KPI_KEYS = {
    "needs_action": "needs_action",
    "waiting_review": "waiting_review",
    "blocked": "blocked",
    "overdue": "overdue",
}


@pytest.mark.parametrize("role", ["SYSTEM_ADMIN", "COMMERCIAL_APPROVER", "RESPONSIBLE_ENGINEER"])
def test_work_kpi_counts_equal_the_matching_filtered_list(client, role):
    headers = {"X-Dev-Role": role}
    base = client.get("/api/work", headers=headers)
    assert base.status_code == 200
    base_body = base.json()

    for kpi, summary_key in KPI_KEYS.items():
        filtered = client.get("/api/work", params={"kpi": kpi}, headers=headers)
        assert filtered.status_code == 200
        body = filtered.json()
        assert body["projection"] == "AMEC Work"
        assert body["summary"][summary_key] == len(body["items"])

        summary = client.get("/api/work/summary", headers=headers)
        assert summary.status_code == 200
        assert summary.json()["summary"] == base_body["summary"]


def test_owner_is_union_of_business_development_and_engineering_work(client):
    owner = client.get("/api/work", headers={"X-Dev-Role": "SYSTEM_ADMIN"}).json()
    bd = client.get("/api/work", headers={"X-Dev-Role": "COMMERCIAL_APPROVER"}).json()
    engineering = client.get("/api/work", headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER"}).json()

    owner_ids = {item["id"] for item in owner["items"]}
    scoped_ids = {item["id"] for item in bd["items"]} | {item["id"] for item in engineering["items"]}
    assert scoped_ids <= owner_ids
    assert owner["persona"] == "OWNER"
    assert bd["persona"] == "BUSINESS_DEVELOPMENT"
    assert engineering["persona"] == "ENGINEERING"


def test_passive_notifications_are_recent_changes_not_work_items(client):
    body = client.get("/api/work", headers={"X-Dev-Role": "SYSTEM_ADMIN"}).json()
    assert all(item["source_type"] != "NOTIFICATION_EVENT" for item in body["items"])
    assert "recent_changes" in body


def test_communication_review_is_human_readable_work(client):
    body = client.get("/api/work", headers={"X-Dev-Role": "SYSTEM_ADMIN"}).json()
    drafts = [item for item in body["items"] if item["source_type"] == "COMMUNICATION_DRAFT"]
    assert drafts
    assert all("email" in item["title"].lower() or "communication" in item["title"].lower() for item in drafts)
    assert all(item["deep_link"].startswith("/notifications") for item in drafts)


def test_work_items_have_business_context_and_deep_links(client):
    body = client.get("/api/work", headers={"X-Dev-Role": "SYSTEM_ADMIN"}).json()
    assert body["items"]
    assert all(item["business_context"] and item["deep_link"] for item in body["items"])


def test_work_domain_precedence_and_action_deduplication_are_canonical(client):
    body = client.get("/api/work", headers={"X-Dev-Role": "SYSTEM_ADMIN"}).json()
    items = body["items"]
    assert len({item["canonical_action_key"] for item in items}) == len(items)
    assert all(item["domain"] in {"PROPOSAL", "CONTRACT", "PERMIT", "SYSTEM"} for item in items)
    assert any(item["domain"] == "PROPOSAL" and "Proposal" in item["title"] for item in items)
    assert any(item["domain"] == "CONTRACT" and "Contract" in item["title"] for item in items)
    assert any(item["domain"] == "PERMIT" for item in items)
    owner_text = " ".join(f"{item['title']} {item['business_context']} {item['stage'] or ''}" for item in items)
    assert "quotation" not in owner_text.lower()
    assert "review_issue" not in owner_text.lower()
    assert all(item["cta_label"] not in {"Open work", "Open issue"} for item in items)


def test_engineering_sees_proposal_and_permit_work_but_not_commercial_work(client):
    body = client.get("/api/work", headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER"}).json()
    assert any(item["domain"] == "PROPOSAL" for item in body["items"])
    assert any(item["domain"] == "PERMIT" for item in body["items"])
    assert not any(item["domain"] == "CONTRACT" for item in body["items"])


def test_recent_changes_are_persona_relevant_business_events(client):
    owner = client.get("/api/work", headers={"X-Dev-Role": "SYSTEM_ADMIN"}).json()["recent_changes"]
    bd = client.get("/api/work", headers={"X-Dev-Role": "COMMERCIAL_APPROVER"}).json()["recent_changes"]
    engineering = client.get("/api/work", headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER"}).json()["recent_changes"]
    assert owner and bd and engineering
    assert any("clarification" in item["title"].lower() or "proposal" in item["title"].lower() for item in bd)
    assert any("authority" in item["title"].lower() or "proposal" in item["title"].lower() for item in engineering)
    assert all("workflow change was recorded" not in item["detail"].lower() for item in owner)


def test_stage_one_completion_reprojects_the_next_action(client):
    project = next(item for item in client.get("/api/projects").json() if item["project_number"] == "GHCE-2026-0142")
    before = client.get("/api/work", headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER"}).json()
    before_titles = {item["title"] for item in before["items"] if item.get("project_id") == project["id"]}
    if "Confirm project & sources" in before_titles:
        response = client.post(
            f"/api/projects/{project['id']}/confirm-project-sources",
            json={"project_reference": project["project_number"]},
            headers={"X-Dev-Role": "SYSTEM_ADMIN"},
        )
        assert response.status_code == 200
    after = client.get("/api/work", headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER"}).json()
    after_titles = {item["title"] for item in after["items"] if item.get("project_id") == project["id"]}
    assert "Confirm project & sources" not in after_titles
    assert "Verify project data" in after_titles
