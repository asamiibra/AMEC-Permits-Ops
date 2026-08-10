"""Focused end-to-end proof for the owner Dashboard master-content contract."""

from pathlib import Path
from uuid import uuid4

from backend.app.adapters.synology.adapter import MockSynologyAdapter
from backend.app.services import master_content


def _master(client, content_type, ref, title, body=b"v1", role="SYSTEM_ADMIN", surface="DASHBOARD"):
    return client.post(
        "/api/master-content",
        data={"content_type": content_type, "ref": ref, "title": title, "description": "Synthetic controlled fixture"},
        files={"file": ("fixture.txt", body, "text/plain")},
        headers={"X-Dev-Role": role, "Idempotency-Key": str(uuid4()), "X-Source-Surface": surface},
    )


def test_owner_dashboard_master_content_golden_path(client):
    categories = client.get("/api/master-content/categories", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert categories.status_code == 200
    category_id = categories.json()[0]["id"]

    created = _master(client, "FORM", f"F-{uuid4().hex[:6]}", "Synthetic Consultant Form")
    assert created.status_code == 200, created.text
    item = created.json()
    item_id = item["id"]
    assert item["version"] == 1
    assert item["storage_status"] == "Storage verified"

    retry = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": item["ref"], "title": item["title"]},
        files={"file": ("fixture.txt", b"v1", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN", "Idempotency-Key": "stable-owner-dashboard-retry"},
    )
    retry_again = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": item["ref"], "title": item["title"]},
        files={"file": ("fixture.txt", b"v1", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN", "Idempotency-Key": "stable-owner-dashboard-retry"},
    )
    assert retry.status_code == 409  # the key was intentionally not used for the first create
    assert retry_again.status_code == 409

    version = client.post(
        f"/api/master-content/{item_id}/versions",
        data={"expected_current_version": "1", "change_reason": "Synthetic owner revision", "category_id": category_id},
        files={"file": ("fixture-v2.txt", b"v2", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN", "Idempotency-Key": str(uuid4())},
    )
    assert version.status_code == 200, version.text
    current = version.json()
    assert current["version"] == 2
    assert [v["status"] for v in current["versions"]] == ["CURRENT", "SUPERSEDED"]

    conflict = client.post(
        f"/api/master-content/{item_id}/versions",
        data={"expected_current_version": "1", "change_reason": "Stale client"},
        files={"file": ("fixture-v3.txt", b"v3", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN", "Idempotency-Key": str(uuid4())},
    )
    assert conflict.status_code == 409
    assert conflict.json()["detail"]["code"] == "VERSION_CONFLICT"

    historical = client.get(f"/api/master-content/{item_id}/versions/{current['versions'][1]['id']}/download", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert historical.status_code == 200
    assert historical.content == b"v1"

    for content_type, ref, title in [("REPORT", f"R-{uuid4().hex[:6]}", "Synthetic Report"), ("ENGINEERING_WORK", f"D-{uuid4().hex[:6]}", "Synthetic QCS Reference")]:
        response = _master(client, content_type, ref, title)
        assert response.status_code == 200, response.text

    forbidden = _master(client, "REPORT", f"R-{uuid4().hex[:6]}", "Denied Report", role="COMMERCIAL_APPROVER")
    assert forbidden.status_code == 403
    assert forbidden.json()["detail"]["code"] == "CAPABILITY_DENIED"


def test_definitions_are_structured_and_revisioned(client):
    term = f"Client ID {uuid4().hex[:5]}"
    created = client.post("/api/definitions", json={"term": term, "description": "Synthetic client identifier"}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert created.status_code == 200, created.text
    definition = created.json()
    revised = client.post(f"/api/definitions/{definition['id']}/revisions", json={"term": definition["term"], "description": "Updated synthetic identifier", "change_reason": "Owner clarification", "expected_revision": 1}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert revised.status_code == 200, revised.text
    assert revised.json()["revision"] == 2
    assert [row["status"] for row in revised.json()["revisions"]] == ["CURRENT", "SUPERSEDED"]
    notifications = client.get("/api/notifications", params={"persona": "OWNER", "domain": "MASTER_CONTENT"}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert notifications.status_code == 200
    assert any(row["event_type"] == "DEFINITION_REVISION_PROMOTED" and term in row["subject"] for row in notifications.json()["notifications"])


def test_report_dependency_revalidation_uses_shared_propagation_contract(client):
    project_id = client.get("/api/projects").json()[0]["id"]
    created = _master(client, "REPORT", f"RP-{uuid4().hex[:6]}", "Synthetic Report Definition")
    assert created.status_code == 200, created.text
    item = created.json()
    dependency = client.post(
        f"/api/master-content/{item['id']}/dependencies",
        json={"downstream_type": "GeneratedReport", "downstream_id": f"report-{uuid4().hex[:8]}", "project_id": project_id},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert dependency.status_code == 200, dependency.text
    revised = client.post(
        f"/api/master-content/{item['id']}/versions",
        data={"expected_current_version": "1", "change_reason": "Report logic revision"},
        files={"file": ("report-v2.txt", b"report-v2", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN", "Idempotency-Key": str(uuid4())},
    )
    assert revised.status_code == 200, revised.text
    propagation = client.get(f"/api/master-content/{item['id']}/propagation")
    assert propagation.status_code == 200
    assert propagation.json()["dependencies"][0]["status"] == "NEEDS_REVALIDATION"
    assert propagation.json()["dependencies"][0]["downstream_type"] == "GeneratedReport"


def test_administration_forms_use_canonical_parity_and_do_not_spuriously_notify(client):
    ref = f"ADMIN-F-{uuid4().hex[:6]}"
    created = _master(client, "FORM", ref, "Administration parity form", body=b"form-v1", surface="DASHBOARD")
    assert created.status_code == 200, created.text
    item = created.json()
    dashboard = client.get("/api/master-content", params={"content_type": "FORM"}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    administration = client.get("/api/master-content", params={"content_type": "FORM"}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    dashboard_row = next(row for row in dashboard.json() if row["id"] == item["id"])
    administration_row = next(row for row in administration.json() if row["id"] == item["id"])
    assert {key: dashboard_row[key] for key in ("ref", "category", "description", "status", "version", "current_version_id")} == {key: administration_row[key] for key in ("ref", "category", "description", "status", "version", "current_version_id")}

    revised = client.post(
        f"/api/master-content/{item['id']}/versions",
        data={"expected_current_version": "1", "change_reason": "Administration version update"},
        files={"file": ("admin-v2.txt", b"form-v2", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN", "X-Source-Surface": "ADMINISTRATION", "Idempotency-Key": str(uuid4())},
    )
    assert revised.status_code == 200, revised.text
    history = revised.json()["versions"]
    assert [row["version"] for row in history] == [2, 1]
    assert [row["status"] for row in history] == ["CURRENT", "SUPERSEDED"]
    assert client.get(f"/api/master-content/{item['id']}/versions/{history[1]['id']}/download").content == b"form-v1"
    assert client.get(f"/api/master-content/{item['id']}/versions/{history[0]['id']}/download").content == b"form-v2"
    propagation = client.get(f"/api/master-content/{item['id']}/propagation").json()
    latest_event = next(event for event in propagation["events"] if event["new_version_id"] == history[0]["id"])
    assert latest_event["metadata"]["source_surface"] == "ADMINISTRATION"
    assert propagation["events"][0]["metadata"].get("propagation", {}).get("notifications", 0) == 0

    denied = _master(client, "FORM", f"DENY-F-{uuid4().hex[:6]}", "Denied Administration form", role="COMMERCIAL_APPROVER", surface="ADMINISTRATION")
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "CAPABILITY_DENIED"


def test_sor_failure_does_not_return_success(client, monkeypatch):
    original = master_content._adapter
    monkeypatch.setattr(master_content, "_adapter", lambda: MockSynologyAdapter("/path/that/is/not/the/sor"))
    response = _master(client, "FORM", f"F-{uuid4().hex[:6]}", "SOR Failure Fixture")
    assert response.status_code in {502, 503}
    assert response.json()["detail"]["code"] in {"SOR_UNAVAILABLE", "SOR_WRITE_FAILED"}
    monkeypatch.setattr(master_content, "_adapter", original)


def test_material_master_change_propagates_to_issues_work_notifications_and_lineage(client):
    projects = client.get("/api/projects")
    assert projects.status_code == 200
    project_id = projects.json()[0]["id"]

    created = _master(client, "ENGINEERING_WORK", f"EW-{uuid4().hex[:6]}", "Synthetic Engineering Source")
    assert created.status_code == 200, created.text
    item = created.json()
    version_one = item["current_version_id"]

    dependency = client.post(
        f"/api/master-content/{item['id']}/dependencies",
        json={"downstream_type": "EngineeringReview", "downstream_id": f"review-{uuid4().hex[:8]}", "project_id": project_id},
        headers={"X-Dev-Role": "SYSTEM_ADMIN"},
    )
    assert dependency.status_code == 200, dependency.text
    dependency_id = dependency.json()["id"]

    revised = client.post(
        f"/api/master-content/{item['id']}/versions",
        data={"expected_current_version": "1", "change_reason": "Synthetic engineering revalidation"},
        files={"file": ("fixture-v2.txt", b"engineering-v2", "text/plain")},
        headers={"X-Dev-Role": "SYSTEM_ADMIN", "Idempotency-Key": str(uuid4())},
    )
    assert revised.status_code == 200, revised.text
    version_two = revised.json()["current_version_id"]
    assert version_two != version_one

    propagation = client.get(f"/api/master-content/{item['id']}/propagation")
    assert propagation.status_code == 200
    current_dependency = next(row for row in propagation.json()["dependencies"] if row["id"] == dependency_id)
    assert current_dependency["status"] == "NEEDS_REVALIDATION"
    assert current_dependency["expected_current_version_id"] == version_two
    assert current_dependency["bound_version_id"] == version_one
    assert any(row["materiality"] == "MATERIAL" and row["new_version_id"] == version_two for row in propagation.json()["events"])

    issues = client.get("/api/issues", params={"persona": "ENGINEERING"}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert issues.status_code == 200
    assert any(row["title"].startswith(item["ref"]) for row in issues.json()["issues"])
    work = client.get("/api/work", params={"team": "ENGINEERING"}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert work.status_code == 200
    assert any(row.get("source_type") == "WORKFLOW_TASK" and row.get("title", "").startswith("Revalidate") for row in work.json()["items"])
    notifications = client.get("/api/notifications", params={"persona": "ENGINEERING", "domain": "MASTER_CONTENT"}, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert notifications.status_code == 200
    assert any(row["event_type"] == "MASTER_CONTENT_VERSION_PROMOTED" for row in notifications.json()["notifications"])

    eligible = client.get("/api/master-content/eligible", params={"use": "ENGINEERING_AI"})
    assert eligible.status_code == 200
    eligible_row = next(row for row in eligible.json() if row["master_content_id"] == item["id"])
    assert eligible_row["document_version_id"] == version_two
    assert eligible_row["eligibility"] == "CURRENT_VERIFIED"

    revalidated = client.post(f"/api/master-content/dependencies/{dependency_id}/revalidate", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert revalidated.status_code == 200
    assert revalidated.json()["status"] == "CURRENT"
    assert revalidated.json()["bound_version_id"] == version_two

    duplicate_reconcile = client.get(f"/api/master-content/{item['id']}/propagation")
    assert duplicate_reconcile.status_code == 200
    assert sum(row["event_type"] == "MASTER_CONTENT_VERSION_PROMOTED" for row in duplicate_reconcile.json()["events"]) == 1
