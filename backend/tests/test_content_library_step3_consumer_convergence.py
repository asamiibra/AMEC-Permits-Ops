"""Step 3 proofs for shared deterministic consumer selection and binding."""

from __future__ import annotations

import json
from uuid import uuid4

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import (
    DocumentVersion,
    Finding,
    MasterContentChangeEvent,
    MasterContentItem,
    NotificationEvent,
    Opportunity,
    WorkflowTask,
)
from backend.app.services.master_content import canonical_master_content_candidates
from backend.app.services.proposal_workspace import engineering_references_for_proposal


OWNER = {"X-Dev-Role": "SYSTEM_ADMIN"}
BD = {"X-Dev-Role": "PROCESS_CHAMPION"}


def _engineering(client, *, needs_review: bool = False):
    ref = f"STEP3-E-{uuid4().hex[:8]}"
    response = client.post(
        "/api/master-content",
        data={
            "content_type": "ENGINEERING_WORK",
            "ref": ref,
            "title": f"Step 3 engineering source {ref}",
            "description": "Synthetic Step 3 consumer source",
            "used_in": json.dumps(["ENGINEERING"]),
            "source_type_code": "QCS",
            "engineering_metadata": json.dumps({"discipline": "STRUCTURAL"}),
            "needs_review": str(needs_review).lower(),
        },
        files={"file": (f"{ref}.txt", b"step 3 engineering source", "text/plain")},
        headers=OWNER,
    )
    assert response.status_code == 200, response.text
    item = response.json()
    governed = client.patch(
        f"/api/master-content/{item['id']}/governance",
        json={"content_ownership_class": "AMEC_OWNED", "artifact_kind": "TECHNICAL_WORKSHEET", "language_profile": "EN"},
        headers=OWNER,
    )
    assert governed.status_code == 200, governed.text
    provenance = client.post(
        f"/api/master-content/{item['id']}/provenance",
        json={"obtained_from": "Synthetic Step 3 fixture"},
        headers=OWNER,
    )
    assert provenance.status_code == 200, provenance.text
    return item


def test_engineering_proposal_consumer_uses_shared_exact_current_resolver(client):
    item = _engineering(client)
    with SessionLocal() as db:
        candidates = canonical_master_content_candidates(db, module="ENGINEERING", usage_type="AVAILABLE", content_type="ENGINEERING_WORK")
        candidate = next(row for row in candidates if row["id"] == item["id"])
        projection = engineering_references_for_proposal(db, Opportunity(status="PROPOSAL_PREPARATION"))
    reference = next(row for row in projection["items"] if row["id"] == item["id"])
    assert reference["version_id"] == candidate["version_id"] == item["current_version_id"]
    assert reference["hash"] == candidate["hash"]
    assert reference["source_type"] == "QCS"
    assert reference["discipline"] == "STRUCTURAL"


def test_shared_resolver_excludes_review_inactive_superseded_and_ambiguous_sources(client):
    needs_review = _engineering(client, needs_review=True)
    inactive = _engineering(client)
    assert client.post(f"/api/master-content/{inactive['id']}/archive", headers=OWNER).status_code == 200
    pending = _engineering(client)
    with SessionLocal() as db:
        version = db.get(DocumentVersion, pending["current_version_id"])
        version.metadata_json = {**version.metadata_json, "master_status": "SUPERSEDED"}
        version.approval_state = "SUPERSEDED"
        db.commit()
        candidates = canonical_master_content_candidates(db, module="ENGINEERING", usage_type="AVAILABLE", content_type="ENGINEERING_WORK")
    ids = {row["id"] for row in candidates}
    assert needs_review["id"] not in ids
    assert inactive["id"] not in ids
    assert pending["id"] not in ids

    first = _engineering(client)
    second = _engineering(client)
    resolved = client.get("/api/master-content/resolvers/ENGINEERING/AVAILABLE", headers=OWNER)
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "AMBIGUOUS"
    assert {first["id"], second["id"]}.issubset({row["id"] for row in resolved.json()["candidates"]})


def test_master_content_consumer_authorization_and_exact_form_binding_fail_closed(client):
    denied = client.get("/api/master-content/resolvers/ENGINEERING/AVAILABLE", headers=BD)
    assert denied.status_code == 403

    wrong_type = client.post(
        "/api/master-content",
        data={"content_type": "REPORT", "ref": f"STEP3-R-{uuid4().hex[:8]}", "title": "Step 3 wrong purpose type", "used_in": '["BD"]'},
        files={"file": ("report.txt", b"report", "text/plain")},
        headers=OWNER,
    )
    assert wrong_type.status_code == 200, wrong_type.text
    invalid_binding = client.put(
        f"/api/master-content/{wrong_type.json()['id']}/module-bindings",
        json=[{"module": "BD", "usage_type": "PROPOSAL_TEMPLATE"}],
        headers=OWNER,
    )
    assert invalid_binding.status_code == 422
    assert invalid_binding.json()["detail"]["code"] == "PURPOSE_CONTENT_TYPE_MISMATCH"
    proposal_resolution = client.get("/api/master-content/resolvers/BD/PROPOSAL_TEMPLATE", headers=OWNER)
    assert proposal_resolution.status_code == 200
    assert wrong_type.json()["id"] not in {row["id"] for row in proposal_resolution.json()["candidates"]}

    form_one = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": f"STEP3-F-{uuid4().hex[:8]}", "title": "Step 3 form one", "used_in": '["BD"]'},
        files={"file": ("form-one.txt", b"form one", "text/plain")},
        headers=OWNER,
    )
    form_two = client.post(
        "/api/master-content",
        data={"content_type": "FORM", "ref": f"STEP3-F-{uuid4().hex[:8]}", "title": "Step 3 form two", "used_in": '["BD"]'},
        files={"file": ("form-two.txt", b"form two", "text/plain")},
        headers=OWNER,
    )
    assert form_one.status_code == form_two.status_code == 200
    one, two = form_one.json(), form_two.json()
    profile = client.post(
        "/api/form-automation/profiles",
        json={"master_content_item_id": one["id"], "source_document_version_id": one["current_version_id"], "renderer_type": "SYNTHETIC_JSON"},
        headers=OWNER,
    )
    assert profile.status_code == 200, profile.text
    mismatch = client.post(
        "/api/form-automation/instances",
        json={"profile_id": profile.json()["id"], "master_content_item_id": two["id"], "source_document_version_id": one["current_version_id"], "context_type": "SYNTHETIC", "context_id": str(uuid4())},
        headers=OWNER,
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["code"] == "FORM_INSTANCE_MASTER_CONTENT_MISMATCH"


def test_consumer_resolution_matrix_covers_all_downstream_classes_and_cardinality(client):
    expected = {
        "BD": {"SINGLETON_REQUIRED"},
        "ADMIN": {"SINGLETON_REQUIRED"},
        "ENGINEERING": {"COLLECTION"},
        "PERMIT": {"COLLECTION"},
        "REPORTS": {"COLLECTION"},
        "DEFINITIONS": {"SINGLETON_REQUIRED"},
    }
    for consumer, cardinalities in expected.items():
        response = client.get(f"/api/master-content/consumer-resolvers/{consumer}", headers=OWNER)
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["consumer"] == consumer
        assert payload["selection_rule"].startswith("SINGLETON_REQUIRED")
        assert payload["resolvers"]
        assert {row["selection_cardinality"] for row in payload["resolvers"]} == cardinalities
        for row in payload["resolvers"]:
            assert row["exact_version_binding"] is True
            assert row["canonical_resolver"].startswith("/api/")
            assert "resolution" in row

    assert client.get("/api/master-content/consumer-resolvers/PROPOSAL", headers=OWNER).json()["consumer"] == "BD"
    assert client.get("/api/master-content/consumer-resolvers/REPORT", headers=OWNER).json()["consumer"] == "REPORTS"
    assert client.get("/api/master-content/consumer-resolvers/DEFINITION", headers=OWNER).json()["consumer"] == "DEFINITIONS"


def test_consumer_matrix_respects_persona_scope_without_mutating_state(client):
    business_development = client.get("/api/master-content/consumer-resolvers/ENGINEERING", headers=BD)
    engineering = client.get("/api/master-content/consumer-resolvers/BD", headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER"})
    assert business_development.status_code == engineering.status_code == 200
    assert business_development.json()["consumer"] == "BD"
    assert engineering.json()["consumer"] == "ENGINEERING"
    assert all(row["module"] == "BD" for row in business_development.json()["resolvers"])
    assert all(row["module"] == "ENGINEERING" for row in engineering.json()["resolvers"])


def test_propagated_revalidation_keeps_canonical_content_library_links(client):
    """Finding, task, and notification projections must converge on the CL item."""
    item = _engineering(client)
    project = next(row for row in client.get("/api/projects").json() if row["project_number"] == "GHCE-2026-0142")
    dependency = client.post(
        f"/api/master-content/{item['id']}/dependencies",
        json={
            "downstream_type": "PermitApplication",
            "downstream_id": f"step3-permit-{uuid4().hex}",
            "project_id": project["id"],
            "dependency_kind": "MASTER_CONTENT_CURRENT_VERSION",
        },
        headers=OWNER,
    )
    assert dependency.status_code == 200, dependency.text

    version = client.post(
        f"/api/master-content/{item['id']}/versions",
        data={"expected_current_version": "1", "change_reason": "Step 3 link projection regression proof"},
        files={"file": ("updated-source.txt", b"updated source", "text/plain")},
        headers=OWNER,
    )
    assert version.status_code == 200, version.text
    current_version_id = version.json()["current_version_id"]
    canonical_link = f"/content-library?content={item['id']}"

    with SessionLocal() as db:
        event = db.scalar(select(MasterContentChangeEvent).where(MasterContentChangeEvent.new_version_id == current_version_id))
        assert event is not None
        finding = db.scalar(select(Finding).where(Finding.source_type == "MASTER_CONTENT", Finding.correlation_id == event.correlation_id))
        task = db.scalar(select(WorkflowTask).where(WorkflowTask.context_type == "MASTER_CONTENT_DEPENDENCY", WorkflowTask.correlation_id == event.correlation_id))
        notifications = db.scalars(select(NotificationEvent).where(NotificationEvent.correlation_id == event.correlation_id)).all()

    assert finding is not None
    assert task is not None
    assert finding.deep_link == task.deep_link == canonical_link
    assert task.finding_id == finding.id
    assert len(notifications) == 2
    assert all(notification.deep_link == canonical_link for notification in notifications)
    assert all(notification.finding_id == finding.id for notification in notifications)
    assert all(notification.workflow_task_id == task.id for notification in notifications)
    assert all("/dashboard?content=" not in (notification.deep_link or "") for notification in notifications)

    issues = client.get("/api/issues", params={"persona": "ENGINEERING"}, headers=OWNER)
    assert issues.status_code == 200, issues.text
    projected_issue = next(row for row in issues.json()["issues"] if row["id"] == finding.id)
    assert projected_issue["deep_link"] == canonical_link
    assert projected_issue["issue_detail_link"] == canonical_link

    work = client.get("/api/work", params={"team": "ENGINEERING"}, headers=OWNER)
    assert work.status_code == 200, work.text
    projected_task = next(row for row in work.json()["items"] if row.get("source_type") == "WORKFLOW_TASK" and row.get("source_id") == task.id)
    assert projected_task["deep_link"] == canonical_link
