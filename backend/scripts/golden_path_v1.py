"""Retroactive Week 6 Golden Path v1 runner.

This is a synthetic simulator run. It never calls an official authority and
does not expose a final-submit operation.
"""

import json
from pathlib import Path

from sqlalchemy import select
from fastapi.testclient import TestClient

from backend.app.db import SessionLocal
from backend.app.fixtures.canonical import CANONICAL_APPLICATION_IDS, CANONICAL_FIXTURE_ID, CANONICAL_FIXTURE_MANIFEST_HASH, CANONICAL_FIXTURE_VERSION, CANONICAL_PROJECT_IDS
from backend.app.main import app
from backend.app.models import AuditEvent, Document, DocumentVersion, FieldObservation, Project, VerifiedAssertion
from backend.app.seed.cli import seed


def require(response, expected=200):
    assert response.status_code == expected, f"{response.request.method} {response.request.url}: {response.status_code} {response.text}"
    return response.json()


def run() -> dict:
    # The command owns an isolated seeded test state through the configured
    # DATABASE_URL. The seed is synthetic and deterministic.
    seed()
    with TestClient(app) as client:
        projects = require(client.get("/api/projects"))
        project = next(item for item in projects if item["project_number"] == CANONICAL_PROJECT_IDS[0])
        pid = project["id"]
        application = next(item for item in require(client.get("/api/applications")) if item["external_request_number"] == CANONICAL_APPLICATION_IDS[0])
        initial = require(client.post(f"/api/projects/{pid}/readiness/evaluate"))
        documents = require(client.get(f"/api/projects/{pid}/documents"))
        for document in documents:
            if document["document_type"] in {"TITLE_DEED", "OWNER_QID", "DRAWING_SET"}:
                require(client.patch(f"/api/document-versions/{document['current_version_id']}/approval-state", json={"approval_state": "APPROVED", "actor_id": "synthetic-reviewer"}))
        title = next(item for item in documents if item["document_type"] == "TITLE_DEED")
        keyed = require(client.post(f"/api/projects/{pid}/manual-observations", json={"document_version_id": title["current_version_id"], "field_code": "PROPERTY.PLOT_NUMBER", "raw_value": "001234", "source_region_text": "Degraded OCR fallback — keyed by human reviewer"}))
        require(client.post(f"/api/observations/{keyed['id']}/verify", json={"method": "MANUAL_KEYED_VERIFIED", "actor_id": "synthetic-reviewer"}))
        drawing = next(item for item in documents if item["document_type"] == "DRAWING_SET")
        for observation in require(client.get(f"/api/document-versions/{drawing['current_version_id']}/observations")):
            if observation["field_code"] == "DRAWING.REVISION":
                require(client.post(f"/api/observations/{observation['id']}/verify", json={"method": "HUMAN_VERIFIED", "actor_id": "synthetic-reviewer"}))
        ready = require(client.post(f"/api/projects/{pid}/readiness/evaluate"))
        package_response = require(client.post(f"/api/projects/{pid}/package"))
        package = package_response["package"]
        require(client.post(f"/api/projects/{pid}/forms/OWNER_UNDERTAKING/render"))
        require(client.post(f"/api/projects/{pid}/approvals", json={"approval_type": "DATA_VERIFICATION_COMPLETE", "role_at_decision": "REQUIREMENT_STEWARD", "decided_by": "synthetic-steward"}))
        require(client.post(f"/api/projects/{pid}/approvals", json={"approval_type": "TECHNICAL_REVIEW_COMPLETE", "role_at_decision": "RESPONSIBLE_ENGINEER", "decided_by": "synthetic-engineer"}))
        approved = require(client.post(f"/api/packages/{package['id']}/approve", json={"approved_by": "synthetic-steward"}))
        revision_response = require(client.post(f"/api/projects/{pid}/preparation-revisions", json={"package_id": package["id"], "created_by": "synthetic-preparer"}))
        revision = revision_response["revision"]
        rid = revision["id"]
        grids = require(client.get(f"/api/preparation-revisions/{rid}/municipality/grids"))["rows"]
        attachments = require(client.get(f"/api/preparation-revisions/{rid}/municipality/attachments"))["attachments"]
        require(client.post(f"/api/preparation-revisions/{rid}/intended-state", json={"application_identity": {"application_id": application["id"], "external_request_number": application["external_request_number"]}, "fields": {"plot_number": "001234", "owner_name": "Yousef Ahmed Ali"}, "repeating_rows": grids, "attachments": attachments}))
        require(client.put(f"/mock-authority/applications/{application['id']}/draft", json={"state_json": {"plot_number": "001234", "owner_name": "Yousef Ahmed Ali", "buildings": grids}}))
        snapshot = require(client.post(f"/api/preparation-revisions/{rid}/portal-snapshots", json={"snapshot_type": "REOPENED", "capture_method": "SIMULATOR_READ", "grid_state": grids, "attachment_state": attachments}))
        reconciliation = require(client.post(f"/api/preparation-revisions/{rid}/reconcile", json={"portal_snapshot_id": snapshot["id"]}))
        precheck = require(client.post(f"/api/preparation-revisions/{rid}/precheck/capture"))
        require(client.post(f"/api/preparation-revisions/{rid}/session/attendance", json={"human_attendance_confirmed": True}))
        handoff = require(client.post(f"/api/preparation-revisions/{rid}/handoff", json={}))
    with SessionLocal() as db:
        versions = db.scalars(select(DocumentVersion).join(Document).where(Document.project_id == pid)).all()
        assertions = db.scalars(select(VerifiedAssertion).where(VerifiedAssertion.project_id == pid)).all()
        events = db.scalars(select(AuditEvent).where(AuditEvent.correlation_id.like("%"))).all()
        correlations = sorted({item.correlation_id for item in events if item.correlation_id})
        bootstrap_events = [item.id for item in events if item.correlation_id == "seed-canonical-fixture" and item.event_type in {"PROJECT_INITIATED", "PROJECT_NUMBER_RESERVED", "PROJECT_CREATED", "SYNOLOGY_PROJECT_ROOT_CREATED", "PROJECT_TEMPLATE_APPLIED", "EXCEL_PROJECT_ROW_LINKED"}]
    result = {
        "status": "PASS" if reconciliation["revision"]["status"] == "VERIFIED_DRAFT" and handoff["statement"] == "HUMAN SUBMISSION REQUIRED" else "FAIL",
        "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE",
        "fixture": {"name": CANONICAL_FIXTURE_ID, "version": CANONICAL_FIXTURE_VERSION, "manifest_hash": CANONICAL_FIXTURE_MANIFEST_HASH},
        "project_id": project["project_number"],
        "application_id": application["external_request_number"],
        "project_bootstrap_event_ids": bootstrap_events,
        "document_version_ids": [item.id for item in versions],
        "verified_assertion_ids": [item.id for item in assertions],
        "package_id": package["id"],
        "package_hash": package["manifest_hash"],
        "approval_actor": approved["package"]["approved_by"],
        "preparation_revision_id": rid,
        "portal_snapshot_ids": [snapshot["id"]],
        "reconciliation": reconciliation["revision"]["status"],
        "precheck_run_id": precheck["run"]["id"] if precheck.get("run") else None,
        "handoff_id": handoff["handoff"]["id"],
        "audit_correlation_ids": correlations,
        "initial_readiness": initial["evaluation"]["overall_status"],
        "ready_readiness": ready["evaluation"]["overall_status"],
        "machine_final_submit": False,
    }
    Path("artifacts").mkdir(parents=True, exist_ok=True)
    Path("artifacts/golden-path-v1-result.json").write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
