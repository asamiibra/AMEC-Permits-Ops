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
