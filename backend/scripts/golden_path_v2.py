"""Repeatable Week 10 Golden Path v2 synthetic runner.

The only submission step here is an explicitly marked external-human test
harness event. It is not mounted as a PermitOps product route.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

os.environ["APP_ENV"] = "TEST"
os.environ["SYNTHETIC_ONLY"] = "true"
os.environ["DATABASE_URL"] = "sqlite:///./golden_path_v2.db"

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.main import app
from backend.app.db import SessionLocal
from backend.app.models import *
from backend.app.seed.cli import seed
from backend.app.fixtures.canonical import fixture_metadata


def call(client, method: str, path: str, payload: dict | None = None) -> dict:
    response = getattr(client, method)(path, json=payload) if payload is not None else getattr(client, method)(path)
    if response.status_code >= 400:
        raise RuntimeError(f"{method.upper()} {path} -> {response.status_code}: {response.text}")
    return response.json()


def prepare_project(client, project_id: str) -> None:
    call(client, "post", f"/api/projects/{project_id}/readiness/evaluate")
    documents = call(client, "get", f"/api/projects/{project_id}/documents")
    for document in documents:
        if document["document_type"] in {"TITLE_DEED", "OWNER_QID", "DRAWING_SET"} and document.get("current_version_id"):
            call(client, "patch", f"/api/document-versions/{document['current_version_id']}/approval-state", {"approval_state": "APPROVED"})
    title = next(x for x in documents if x["document_type"] == "TITLE_DEED")
    keyed = call(client, "post", f"/api/projects/{project_id}/manual-observations", {"document_version_id": title["current_version_id"], "field_code": "PROPERTY.PLOT_NUMBER", "raw_value": "001234", "source_region_text": "Synthetic Golden Path v2 evidence"})
    call(client, "post", f"/api/observations/{keyed['id']}/verify", {"method": "HUMAN_VERIFIED"})
    drawing = next(x for x in documents if x["document_type"] == "DRAWING_SET")
    for observation in call(client, "get", f"/api/document-versions/{drawing['current_version_id']}/observations"):
        if observation.get("field_code") == "DRAWING.REVISION":
            call(client, "post", f"/api/observations/{observation['id']}/verify", {"method": "HUMAN_VERIFIED"})
    ready = call(client, "post", f"/api/projects/{project_id}/readiness/evaluate")
    if ready["evaluation"]["overall_status"] not in {"READY", "READY_WITH_NONBLOCKING_WARNINGS"}:
        raise RuntimeError(f"Golden Path bootstrap did not reach package readiness: {ready}")


def make_run(revision_id: str, status: str, code: str | None = None) -> str:
    with SessionLocal() as db:
        revision = db.get(PreparationRevision, revision_id)
        run = AuthorityPrecheckRun(application_id=revision.application_id, preparation_revision_id=revision.id, run_reference=f"W10-{revision.sequence}", source="SYNTHETIC_AUTHORITY_AI", status=status, raw_evidence_artifact_id=f"synthetic://golden-path-v2/precheck/{revision.sequence}", result_hash=("b" if status == "CLEAR" else "a") * 64, configuration_bundle_id=revision.configuration_bundle_id, run_at=datetime.now(timezone.utc))
        db.add(run); db.flush()
        if code:
            db.add(AuthorityPrecheckItem(precheck_run_id=run.id, source_type="AUTHORITY_PRECHECK", code=code, message="Synthetic blocking technical action for correction loop.", severity="BLOCKING", status="OPEN"))
        db.commit()
        return run.id


def main() -> None:
    db_path = Path("golden_path_v2.db")
    if db_path.exists():
        db_path.unlink()
    seed()
    with TestClient(app) as client:
        project = next(x for x in call(client, "get", "/api/projects") if x["project_number"] == "GHCE-2026-0142")
        prepare_project(client, project["id"])
        package1 = call(client, "post", f"/api/projects/{project['id']}/package")["package"]
        call(client, "post", f"/api/projects/{project['id']}/approvals", {"approval_type": "DATA_VERIFICATION_COMPLETE", "role_at_decision": "REQUIREMENT_STEWARD", "entity_type": "Project"})
        call(client, "post", f"/api/projects/{project['id']}/approvals", {"approval_type": "TECHNICAL_REVIEW_COMPLETE", "role_at_decision": "RESPONSIBLE_ENGINEER", "entity_type": "Project"})
        call(client, "post", f"/api/packages/{package1['id']}/approve", {"approved_by": "steward@amec.synthetic"})
        revision1 = call(client, "post", f"/api/projects/{project['id']}/preparation-revisions", {"package_id": package1["id"], "created_by": "preparer@amec.synthetic"})["revision"]
        run1_id = make_run(revision1["id"], "FINDINGS", "TECHNICAL_TODO")
        precheck1 = call(client, "post", f"/api/findings/from-precheck/{run1_id}", {"captured_by": "synthetic-precheck"})
        f1 = precheck1["results"][0]["finding"]
        clearance1 = call(client, "post", f"/api/precheck-runs/{run1_id}/clearance/evaluate")["evaluation"]

        correction = call(client, "post", f"/api/preparation-revisions/{revision1['id']}/create-correction-revision", {"material_change": True, "source_type": "VerifiedAssertion", "source_id": revision1["id"], "change_type": "DRAWING_REVISION_CORRECTION", "new_version_or_hash": "synthetic-corrected-R02", "created_by": "engineer@amec.synthetic"})
        package2 = correction["package"]
        revision2 = correction["revision"]
        call(client, "post", f"/api/projects/{project['id']}/approvals", {"approval_type": "DATA_VERIFICATION_COMPLETE", "role_at_decision": "REQUIREMENT_STEWARD", "entity_type": "Package", "entity_id": package2["id"]})
        call(client, "post", f"/api/projects/{project['id']}/approvals", {"approval_type": "TECHNICAL_REVIEW_COMPLETE", "role_at_decision": "RESPONSIBLE_ENGINEER", "entity_type": "Package", "entity_id": package2["id"]})
        call(client, "post", f"/api/packages/{package2['id']}/approve", {"approved_by": "steward@amec.synthetic"})
        call(client, "post", f"/api/preparation-revisions/{revision2['id']}/human-portal-verifications", {"verifier": "preparer@amec.synthetic", "verifier_role": "PERMIT_PREPARER", "evidence_artifact_id": "synthetic://golden-path-v2/portal-verification", "result": "VERIFIED"})
        run2_id = make_run(revision2["id"], "CLEAR")
        clearance2 = call(client, "post", f"/api/precheck-runs/{run2_id}/clearance/evaluate")["evaluation"]
        resolution = call(client, "post", f"/api/findings/{f1['id']}/resolutions", {"correction_summary": "Corrected drawing revision and rechecked authority precheck.", "correction_type": "DRAWING_REVISION", "root_cause_category": "DRAWING_REVISION_ERROR", "proposed_by": "engineer@amec.synthetic"})["resolution"]
        call(client, "post", f"/api/finding-resolutions/{resolution['id']}/evidence", {"evidence_artifact_id": run2_id, "evidence_type": "AUTHORITY_RECHECK", "source_entity_type": "AuthorityPrecheckRun", "source_entity_id": run2_id})
        call(client, "post", f"/api/finding-resolutions/{resolution['id']}/verify", {"verifier": "engineer@amec.synthetic"})

        application_id = revision2["application_id"]
        cycle = call(client, "post", "/api/submission-cycles/synthetic-capture", {"application_id": application_id, "preparation_revision_id": revision2["id"], "package_id": package2["id"], "status": "SUBMITTED", "external_human_action": True, "submission_reference": "SYN-HUMAN-SUBMIT-W10", "submitted_values": {"plot_number": "001234"}})
        cycle_id = cycle["cycle"]["id"]
        returned = call(client, "post", "/api/submission-cycles/synthetic-capture", {"application_id": application_id, "preparation_revision_id": revision2["id"], "submission_cycle_id": cycle_id, "status": "RETURNED", "comments": [{"finding_code": "OFFICIAL_DOCUMENT_COMMENT", "raw_text": "Synthetic missing document comment.", "title": "Official document comment", "blocking": True, "external_event_id": "W10-OFFICIAL-DOC"}, {"finding_code": "OFFICIAL_DRAWING_COMMENT", "raw_text": "Synthetic drawing revision comment.", "title": "Official drawing comment", "blocking": True, "external_event_id": "W10-OFFICIAL-DRAWING"}]})
        official = returned["official_findings"]
        f2, f3 = official[0]["finding"], official[1]["finding"]
        r2 = call(client, "post", f"/api/findings/{f2['id']}/resolutions", {"correction_summary": "Added corrected document evidence.", "root_cause_category": "ATTACHMENT_MISSING", "proposed_by": "preparer@amec.synthetic"})["resolution"]
        call(client, "post", f"/api/finding-resolutions/{r2['id']}/evidence", {"evidence_artifact_id": "synthetic://w10/document-correction", "evidence_type": "DOCUMENT_EVIDENCE"})
        call(client, "post", f"/api/finding-resolutions/{r2['id']}/verify", {"verifier": "steward@amec.synthetic"})
        blocked_gate = call(client, "post", f"/api/applications/{application_id}/resubmission-readiness/evaluate")["evaluation"]
        r3 = call(client, "post", f"/api/findings/{f3['id']}/resolutions", {"correction_summary": "Corrected drawing revision with engineer evidence.", "root_cause_category": "DRAWING_REVISION_ERROR", "proposed_by": "engineer@amec.synthetic"})["resolution"]
        for evidence_type in ["DRAWING_REVISION", "AUTHORITY_RESPONSE"]:
            call(client, "post", f"/api/finding-resolutions/{r3['id']}/evidence", {"evidence_artifact_id": f"synthetic://w10/{evidence_type.lower()}", "evidence_type": evidence_type})
        call(client, "post", f"/api/finding-resolutions/{r3['id']}/verify", {"verifier": "engineer@amec.synthetic"})
        ready = call(client, "post", f"/api/applications/{application_id}/resubmission-readiness/evaluate")["evaluation"]
        if blocked_gate["overall_status"] != "RESUBMISSION_BLOCKED":
            raise AssertionError("G9 negative assertion failed: open official blocker did not block")
        if ready["overall_status"] != "RESUBMISSION_READY":
            raise AssertionError(f"G9 final assertion failed: {ready['overall_status']}")
        import json
        with SessionLocal() as db:
            audit_correlations = sorted({x.correlation_id for x in db.scalars(select(AuditEvent).order_by(AuditEvent.occurred_at)).all()})
        report = {"fixture": fixture_metadata(), "project": project["project_number"], "application": application_id, "submission_cycles": [cycle["cycle"], returned["cycle"]], "preparation_revisions": [revision1, revision2], "packages": [package1, package2], "precheck_runs": [run1_id, run2_id], "clearances": [clearance1, clearance2], "findings": [f1, f2, f3], "resolutions": [resolution, r2, r3], "audit_correlation_ids": audit_correlations, "negative_resubmission": blocked_gate, "resubmission": ready, "machine_submit_operation": False, "live_ministry_write": False}
        artifact = Path("artifacts/golden-path-v2-result.json")
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
        print(json.dumps(report, indent=2, default=str))


if __name__ == "__main__":
    main()
