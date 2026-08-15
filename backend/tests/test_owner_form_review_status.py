"""Focused contract for the compact Owner Form status overlay."""

from uuid import uuid4


OWNER = {"X-Dev-Role": "SYSTEM_ADMIN"}


def test_owner_status_is_simple_and_needs_review_is_not_resolved_downstream(client):
    ref = f"F-REVIEW-{uuid4().hex[:8]}"
    created = client.post(
        "/api/master-content",
        data={
            "content_type": "FORM",
            "ref": ref,
            "title": "Needs review synthetic Form",
            "description": "Synthetic review fixture",
            "used_in": '["PERMIT"]',
            "needs_review": "true",
            "review_note": "Confirm this source is the intended current Form.",
        },
        files={"file": ("review.txt", b"review-source", "text/plain")},
        headers=OWNER,
    )
    assert created.status_code == 200, created.text
    item = created.json()
    assert item["owner_status"] == "Needs Review"
    assert item["review_note"].startswith("Confirm")

    listed = client.get("/api/master-content", params={"content_type": "FORM", "owner_status": "NEEDS_REVIEW"}, headers=OWNER)
    assert any(row["id"] == item["id"] for row in listed.json())

    bound = client.put(
        f"/api/master-content/{item['id']}/module-bindings",
        json=[{"module": "PERMIT", "usage_type": "AVAILABLE"}],
        headers=OWNER,
    )
    assert bound.status_code == 200
    unresolved = client.get("/api/master-content/resolvers/PERMIT/AVAILABLE", headers=OWNER)
    assert item["id"] not in {row["id"] for row in unresolved.json()["candidates"]}

    cleared = client.patch(
        f"/api/master-content/{item['id']}/metadata",
        json={"needs_review": False, "change_reason": "Owner approved synthetic fixture"},
        headers=OWNER,
    )
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["owner_status"] == "Current"
    assert cleared.json()["review_note"] is None


def test_exact_document_versions_remain_readable_after_review_and_inactive(client):
    ref = f"F-HISTORY-{uuid4().hex[:8]}"
    created = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": ref, "title": "Historical version fixture", "description": "Synthetic history fixture"},
        files={"file": ("history-v1.txt", b"history-v1", "text/plain")},
        headers=OWNER,
    )
    assert created.status_code == 200, created.text
    item = created.json()
    v1 = item["versions"][0]["id"]
    revised = client.post(
        f"/api/master-content/{item['id']}/versions",
        data={"expected_current_version": "1", "change_reason": "Create exact history fixture", "needs_review": "true", "review_note": "Review source"},
        files={"file": ("history-v2.txt", b"history-v2", "text/plain")},
        headers=OWNER,
    )
    assert revised.status_code == 200, revised.text
    v2 = revised.json()["versions"][0]["id"]
    assert revised.json()["owner_status"] == "Needs Review"
    assert client.get(f"/api/master-content/{item['id']}/versions/{v1}/download", headers=OWNER).content == b"history-v1"
    assert client.get(f"/api/master-content/{item['id']}/versions/{v2}/download", headers=OWNER).content == b"history-v2"

    archived = client.post(f"/api/master-content/{item['id']}/archive", headers=OWNER)
    assert archived.status_code == 200, archived.text
    assert archived.json()["owner_status"] == "Inactive"
    assert archived.json()["current_version_id"] == v2
    assert client.get(f"/api/master-content/{item['id']}/versions/{v1}/download", headers=OWNER).content == b"history-v1"
    assert client.get(f"/api/master-content/{item['id']}/versions/{v2}/download", headers=OWNER).content == b"history-v2"


def test_dashboard_and_administration_project_the_same_owner_form_state(client):
    ref = f"F-PARITY-{uuid4().hex[:8]}"
    created = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": ref, "title": "Parity fixture", "description": "Synthetic parity fixture", "needs_review": "true", "review_note": "Same note on both surfaces", "used_in": '["PERMIT"]'},
        files={"file": ("parity.txt", b"parity", "text/plain")},
        headers={**OWNER, "X-Source-Surface": "DASHBOARD"},
    )
    assert created.status_code == 200, created.text
    item_id = created.json()["id"]
    dashboard = client.get("/api/master-content", params={"content_type": "FORM", "q": ref}, headers={**OWNER, "X-Source-Surface": "DASHBOARD"}).json()
    administration = client.get("/api/master-content", params={"content_type": "FORM", "q": ref}, headers={**OWNER, "X-Source-Surface": "ADMINISTRATION"}).json()
    dashboard_row = next(row for row in dashboard if row["id"] == item_id)
    administration_row = next(row for row in administration if row["id"] == item_id)
    keys = ("owner_status", "needs_review", "review_note", "current_version_id", "version", "versions")
    assert {key: dashboard_row.get(key) for key in keys[:-1]} == {key: administration_row.get(key) for key in keys[:-1]}
    detail = client.get(f"/api/master-content/{item_id}", headers=OWNER).json()
    assert detail["owner_status"] == "Needs Review"
    assert detail["review_note"] == "Same note on both surfaces"
