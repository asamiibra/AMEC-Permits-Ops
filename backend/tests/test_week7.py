"""Week 7 finding/task/notification acceptance scenarios."""

from datetime import datetime, timezone

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import (
    AuthorityPrecheckItem, AuthorityPrecheckRun, Finding, FindingSourceType,
    PreparationRevision, WorkflowTask,
)


def canonical_revision():
    with SessionLocal() as db:
        return db.scalar(select(PreparationRevision).order_by(PreparationRevision.created_at.desc()))


def canonical_application(client):
    return next(item for item in client.get("/api/applications").json() if item["external_request_number"] == "GHCE-APP-0142")


def test_official_comment_preserves_source_arabic_and_failure_retry(client):
    application = next(item for item in client.get("/api/applications").json() if item["external_request_number"] == "GHCE-APP-0187")
    comment = client.post("/api/findings/manual-official-comment", json={
        "application_id": application["id"],
        "raw_text": "الرسم غير مطابق للإصدار المعتمد",
        "title": "Official drawing comment",
        "finding_code": "OFFICIAL_DRAWING_COMMENT",
        "language": "ar",
        "evidence_artifact_id": "synthetic://official-comment/w7-1",
        "external_event_id": "W7-OFFICIAL-001",
        "channel": "MOCK_TEAMS",
    })
    assert comment.status_code == 200
    result = comment.json()["result"]
    finding = result["finding"]
    assert finding["source_type"] == FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT
    assert finding["authority_precheck_run_id"] is None
    assert finding["submission_cycle_id"]
    assert finding["raw_text"] == "الرسم غير مطابق للإصدار المعتمد"
    assert finding["language"] == "ar"
    assert result["task"]["owner_role"] == "RESPONSIBLE_ENGINEER"
    assert result["notification"]["status"] == "DELIVERED"

    failed = client.post("/api/findings/manual", json={
        "application_id": application["id"],
        "source_type": "MANUAL_OPERATOR_CAPTURE",
        "source_reference": "failure-demo-001",
        "raw_text": "Synthetic notification failure",
        "title": "Notification failure demo",
        "finding_code": "ATTACHMENT_MISSING",
        "force_notification_failure": True,
        "external_event_id": "W7-FAILURE-001",
    })
    assert failed.status_code == 200
    failed_result = failed.json()["result"]
    assert failed_result["finding"]["status"] in {"OPEN", "ASSIGNED"}
    assert failed_result["task"]["status"] == "OPEN"
    assert failed_result["notification"]["status"] == "FAILED"
    retry = client.post(f"/api/notifications/{failed_result['notification']['id']}/retry")
    assert retry.status_code == 200
    assert retry.json()["notification"]["status"] == "DELIVERED"


def test_precheck_conversion_revision_linkage_and_duplicate_channel(client):
    revision = canonical_revision()
    assert revision is not None
    with SessionLocal() as db:
        run = AuthorityPrecheckRun(application_id=revision.application_id, preparation_revision_id=revision.id, run_reference="W7-PRECHECK-001", source="SYNTHETIC_AUTHORITY_AI", status="FINDINGS", raw_evidence_artifact_id=f"synthetic://precheck/{revision.id}/w7", result_hash="a" * 64, run_at=datetime.now(timezone.utc))
        db.add(run); db.flush()
        db.add(AuthorityPrecheckItem(precheck_run_id=run.id, source_type="AUTHORITY_PRECHECK", code="SYN-DRAWING-001", message="Synthetic technical To-Do: drawing revision requires review.", severity="BLOCKING", status="OPEN"))
        db.commit(); run_id = run.id
    ingested = client.post(f"/api/findings/from-precheck/{run_id}", json={"captured_by": "synthetic-precheck"})
    assert ingested.status_code == 200
    item = ingested.json()["results"][0]
    finding = item["finding"]
    assert finding["source_type"] == "AUTHORITY_PRECHECK"
    assert finding["authority_precheck_run_id"] == run_id
    assert finding["preparation_revision_id"] == revision.id
    assert finding["finding_code"]["code"] == "DRAWING_REVISION_MISMATCH"
    assert item["task"]["owner_role"] == "RESPONSIBLE_ENGINEER"
    assert item["notification"]["status"] == "DELIVERED"
    gate = client.get(f"/api/preparation-revisions/{revision.id}/open-blocking-findings")
    assert gate.status_code == 200
    assert gate.json()["has_open_blocking_findings"] is True
    assert gate.json()["precheck_clear"] is False

    duplicate = client.post(f"/api/findings/from-precheck/{run_id}")
    assert duplicate.status_code == 200
    assert duplicate.json()["results"][0]["dedupe_result"] == "DUPLICATE_EVENT_LINKED"
    with SessionLocal() as db:
        assert db.scalar(select(WorkflowTask).where(WorkflowTask.finding_id == finding["id"])) is not None
        assert len(list(db.scalars(select(WorkflowTask).where(WorkflowTask.finding_id == finding["id"])).all())) == 1


def test_portal_validation_and_task_completion_do_not_close_finding(client):
    revision = canonical_revision()
    assert revision is not None
    response = client.post(f"/api/findings/from-portal-validation/{revision.id}", json={
        "validation_code": "ATTACHMENT_MISSING",
        "message": "Required title deed attachment is missing.",
        "raw_text": "Required title deed attachment is missing.",
        "external_event_id": "W7-PORTAL-001",
    })
    assert response.status_code == 200
    result = response.json()["result"]
    assert result["finding"]["source_type"] == "PORTAL_VALIDATION"
    assert result["finding"]["preparation_revision_id"] == revision.id
    assert result["task"]["owner_role"] == "PERMIT_PREPARER"
    task_id = result["task"]["id"]
    completed = client.post(f"/api/tasks/{task_id}/complete")
    assert completed.status_code == 200
    detail = client.get(f"/api/findings/{result['finding']['id']}").json()
    assert detail["task"]["status"] == "COMPLETED"
    assert detail["status"] != "CLOSED"
    assert "/api/findings/{finding_id}/close" not in client.get("/openapi.json").json()["paths"]


def test_atomic_failure_leaves_no_orphan_chain(client):
    application = canonical_application(client)
    before = client.get("/api/findings", params={"application_id": application["id"]}).json()["count"]
    failed = client.post("/api/findings/manual", json={
        "application_id": application["id"],
        "source_reference": "rollback-demo-001",
        "raw_text": "Synthetic rollback",
        "title": "Rollback test",
        "finding_code": "ATTACHMENT_MISSING",
        "simulate_failure_at": "before_notification",
        "external_event_id": "W7-ROLLBACK-001",
    })
    assert failed.status_code == 500
    after = client.get("/api/findings", params={"application_id": application["id"]}).json()["count"]
    assert after == before


def test_week7_report_and_ignored_portal_noise(client):
    revision = canonical_revision()
    ignored = client.post(f"/api/findings/from-portal-validation/{revision.id}", json={"validation_code": "TRANSIENT_HELPER_MESSAGE", "message": "Not a durable issue"})
    assert ignored.status_code == 200
    assert ignored.json()["created"] is False
    report = client.get("/api/week7/report")
    assert report.status_code == 200
    body = report.json()
    assert body["label"] == "DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED"
    assert "AUTHORITY_PRECHECK" in body["findings_by_source"]
    assert "OFFICIAL_MUNICIPALITY_COMMENT" in body["findings_by_source"]
