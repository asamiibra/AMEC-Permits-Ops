from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import Finding


def test_issue_detail_inventory_is_business_classified_and_evidence_backed(client):
    rows = client.get("/api/issues", params={"persona": "OWNER"}).json()["issues"]
    assert rows
    assert {row["display_domain"] for row in rows} >= {"PROPOSAL", "CONTRACT", "PERMIT", "SYSTEM / DATA"}
    assert all(row["issue_detail_link"] == f"/issues/{row['id']}" or row["id"] in row["issue_detail_link"] for row in rows)
    assert not any(row["display_domain"] == "PERMIT" for row in rows if row["domain"] in {"PROPOSAL_COMMERCIAL", "CONTRACT"})
    for row in rows:
        if not row["issue_detail_link"].startswith("/issues/"):
            continue
        response = client.get(f"/api{row['issue_detail_link']}", params={"persona": "OWNER"})
        assert response.status_code == 200
        payload = response.json()
        assert payload["issue"]["title"] == row["title"]
        assert payload["issue"]["what_is_wrong"]
        assert payload["issue"]["why_it_matters"]
        assert payload["issue"]["what_needs_to_happen"]
        assert payload["affected_entity"]["type"] == row["display_domain"]
        assert payload["evidence"]
        assert "history" in payload and "activity" in payload


def test_issue_detail_direct_route_and_work_correlation(client):
    with SessionLocal() as db:
        finding_ids = {row.id for row in db.scalars(select(Finding)).all()}
    work = client.get("/api/work").json()["items"]
    issue_work = [item for item in work if item.get("issue_id")]
    assert issue_work
    assert {item["issue_id"] for item in issue_work} <= finding_ids
    assert all(item["issue_id"] in item["deep_link"] or item["deep_link"] == f"/issues/{item['issue_id']}" for item in issue_work)
    assert client.get("/api/issues/not-a-real-issue").status_code == 404


def test_issue_detail_server_capabilities_and_entity_binding(client):
    rows = client.get("/api/issues", params={"persona": "OWNER"}).json()["issues"]
    commercial = next(row for row in rows if row["domain"] == "PROPOSAL_COMMERCIAL")
    technical = next(row for row in rows if row["domain"] == "PROPOSAL_TECHNICAL")
    permit = next(row for row in rows if row["domain"] in {"PERMIT_TECHNICAL", "AUTHORITY"})
    payload = {"disposition": "CORRECTED", "correction_type": "REVIEW", "correction_summary": "role boundary test", "root_cause_category": "UNKNOWN_REVIEW_REQUIRED"}
    for row, role in [(commercial, "RESPONSIBLE_ENGINEER"), (permit, "COMMERCIAL_APPROVER")]:
        response = client.post(f"/api/findings/{row['id']}/resolutions", headers={"X-Dev-Role": role}, json=payload)
        assert response.status_code == 403
        assert response.json()["detail"]["code"] == "CAPABILITY_DENIED"
    mismatch = client.post(f"/api/findings/{technical['id']}/resolutions", json={**payload, "affected_entity_id": "wrong-entity"})
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["code"] == "ISSUE_ENTITY_MISMATCH"
    cross_project = client.post(f"/api/findings/{technical['id']}/resolutions", json={**payload, "project_id": "wrong-project"})
    assert cross_project.status_code == 409
    assert cross_project.json()["detail"]["code"] == "ISSUE_ENTITY_MISMATCH"
