"""Isolated Weeks 13–14 acceptance rehearsal runner.

This runner owns a TEST SQLite state, executes Golden Path v1/v2 in their
documented synthetic boundaries, exercises Week 13 operations, and emits a
machine-readable acceptance result. It never performs a government write.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

DB_PATH = Path("acceptance_rehearsal.db")
os.environ["APP_ENV"] = "TEST"
os.environ["SYNTHETIC_ONLY"] = "true"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.fixtures.canonical import fixture_metadata
from backend.app.main import app
from backend.app.models import *
from backend.app.seed.cli import seed
from backend.app.services.week7 import create_routed_finding
from backend.app.services.week45 import stable_hash


def require(response, label):
    if response.status_code >= 400:
        raise RuntimeError(f"{label}: {response.status_code} {response.text}")
    return response.json()


def command(label: str, args: list[str], env: dict[str, str], cwd: Path | None = None) -> dict[str, object]:
    result = subprocess.run(args, cwd=cwd or Path.cwd(), env=env, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"{label} failed: {result.stdout[-1000:]}\n{result.stderr[-1000:]}")
    return {"label": label, "status": "PASS", "stdout_tail": result.stdout[-500:]}


def create_recurrence_fixture() -> tuple[str, str]:
    with SessionLocal() as db:
        application = db.scalar(select(PermitApplication).where(PermitApplication.external_request_number == "GHCE-APP-0142"))
        project = db.get(Project, application.project_id)
        revision = db.scalar(select(PreparationRevision).where(PreparationRevision.application_id == application.id).order_by(PreparationRevision.sequence.desc()))
        if not revision:
            raise RuntimeError("Golden Path v1 did not create a revision")
        current = PreparationRevision(project_id=revision.project_id, application_id=revision.application_id, sequence=revision.sequence + 1, status="READY_FOR_ASSISTED_PREPARATION", scenario_version=revision.scenario_version, field_authority_version=revision.field_authority_version, requirement_config_version=revision.requirement_config_version, rendering_config_version=revision.rendering_config_version, package_id=revision.package_id, package_manifest_hash=revision.package_manifest_hash, created_by="preparer@amec.synthetic", configuration_bundle_id=revision.configuration_bundle_id)
        db.add(current); db.flush()
        cycle1 = SubmissionCycle(application_id=application.id, cycle_number=1, external_reference="SYN-W13-CYCLE-1", status="RETURNED", preparation_revision_id=revision.id, authority_repetition_number=1)
        cycle2 = SubmissionCycle(application_id=application.id, cycle_number=2, external_reference="SYN-W13-CYCLE-2", status="RETURNED", preparation_revision_id=current.id, authority_repetition_number=2)
        db.add_all([cycle1, cycle2]); db.flush()
        prior = create_routed_finding(db, project=project, application=application, source_type=FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT, source_channel="AUTHORITY_REVIEW", source_reference="SYN-W13-PRIOR-DRAWING", raw_text="Synthetic prior drawing comment.", title="Official drawing comment", finding_code="OFFICIAL_DRAWING_COMMENT", discipline="TECHNICAL", preparation_revision_id=revision.id, submission_cycle_id=cycle1.id, external_finding_id="SYN-W13-PRIOR-DRAWING", external_event_id="SYN-W13-PRIOR-DRAWING", affected_object_type="DRAWING", affected_object_id="DRAWING_SET", evidence_artifact_id="synthetic://w13/prior-comment", correlation_id="w13-recurrence-prior")
        prior_finding = prior["finding"]
        prior_finding.status = FindingStatus.CLOSED_VERIFIED
        resolution = FindingResolution(finding_id=prior_finding.id, resolution_version=1, disposition="CORRECTED", status="VERIFIED", correction_type="DRAWING_REVISION", correction_summary="Synthetic corrected drawing revision.", root_cause_category="DRAWING_REVISION_ERROR", required_evidence_policy="DRAWING_REVISION", closure_criteria_version="W10-CLOSURE-1.0", proposed_by="engineer@amec.synthetic", verified_by="engineer@amec.synthetic", verifier_role=Role.RESPONSIBLE_ENGINEER.value, verified_at=now_utc(), verification_result="PASS", correlation_id="w13-recurrence-prior")
        db.add(resolution); db.flush()
        db.add(FindingResolutionEvidence(finding_resolution_id=resolution.id, evidence_artifact_id="synthetic://w13/prior-closure", evidence_type="DRAWING_REVISION", added_by="engineer@amec.synthetic"))
        current_result = create_routed_finding(db, project=project, application=application, source_type=FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT, source_channel="AUTHORITY_REVIEW", source_reference="SYN-W13-RECURRED-DRAWING", raw_text="Synthetic repeated drawing comment after verified closure.", title="Official drawing comment", finding_code="OFFICIAL_DRAWING_COMMENT", discipline="TECHNICAL", preparation_revision_id=current.id, submission_cycle_id=cycle2.id, external_finding_id="SYN-W13-RECURRED-DRAWING", external_event_id="SYN-W13-RECURRED-DRAWING", affected_object_type="DRAWING", affected_object_id="DRAWING_SET", evidence_artifact_id="synthetic://w13/recurrence", correlation_id="w13-recurrence-current")
        create_routed_finding(db, project=project, application=application, source_type=FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT, source_channel="AUTHORITY_REVIEW", source_reference="SYN-W13-FIRST-DOCUMENT", raw_text="Synthetic first-occurrence document comment.", title="Official document comment", finding_code="OFFICIAL_DOCUMENT_COMMENT", discipline="ADMINISTRATIVE", preparation_revision_id=current.id, submission_cycle_id=cycle2.id, external_finding_id="SYN-W13-FIRST-DOCUMENT", external_event_id="SYN-W13-FIRST-DOCUMENT", affected_object_type="DOCUMENT", affected_object_id="DOCUMENT_SET", evidence_artifact_id="synthetic://w13/first-occurrence", correlation_id="w13-recurrence-first")
        db.commit()
        return application.id, current.id


def now_utc():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc)


def main():
    DB_PATH.unlink(missing_ok=True)
    env = os.environ.copy(); env["PYTHONPATH"] = "."
    v1 = command("golden_path_v1", [sys.executable, "backend/scripts/golden_path_v1.py"], env)
    canonical = command("canonical_fixture_check", [sys.executable, "backend/scripts/canonical_fixture_check.py"], env)
    v2 = command("golden_path_v2", [sys.executable, "backend/scripts/golden_path_v2.py"], env)
    browser = command("browser_e2e", ["npm", "run", "browser-e2e"], env, cwd=Path("frontend"))
    application_id, revision_id = create_recurrence_fixture()
    with TestClient(app) as client:
        policy = require(client.get("/api/monitoring/policies"), "policies")["policies"][0]
        first = require(client.post("/api/monitoring/run-due-synthetic", json={"policy_id": policy["id"]}), "monitor first")["runs"][0]
        second = require(client.post("/api/monitoring/run-due-synthetic", json={"policy_id": policy["id"]}), "monitor second")["runs"][0]
        drift = require(client.post("/api/monitoring/run-due-synthetic", json={"policy_id": policy["id"], "observed_state": {"contract": {"fingerprint": "DRIFT", "drift_type": "W13_REHEARSAL_DRIFT"}}}), "monitor drift")["runs"][0]
        drift_events = require(client.get("/api/portal-drift-events"), "drift events")["events"]
        if drift_events:
            contracts = require(client.get("/api/portal-contracts"), "portal contracts")["contracts"]
            require(client.post(f"/api/portal-contracts/{contracts[0]['id']}/validate", json={"reviewed_by": "maintainer@amec.synthetic"}), "contract validation")
            require(client.post(f"/api/portal-drift-events/{drift_events[0]['id']}/revalidate", json={}), "drift revalidation")
        recurrence = require(client.post("/api/recurrence/analyze", json={}), "recurrence")
        preventive = require(client.post(f"/api/preparation-revisions/{revision_id}/preventive-check", json={}), "preventive check")
        incident = require(client.post("/api/incidents/integrity", json={"application_id": application_id, "source_entity_type": "VerifiedAssertion", "source_entity_id": application_id, "created_by": "synthetic-operator"}), "incident")
        impact = require(client.post(f"/api/incidents/{incident['incident']['id']}/impact-assess", json={}), "impact")
        require(client.post(f"/api/workflow-safety-holds/{incident['hold']['id']}/release", json={"released_by": "engineer@amec.synthetic", "evidence": ["synthetic://w13/incident/reconciliation"]}), "hold release")
        restore = require(client.post("/api/recovery/test-restore", json={}), "restore")
        acceptance = require(client.post("/api/acceptance-rehearsal", json={"actor": "synthetic-acceptance-operator"}), "acceptance")
        evidence = require(client.get("/api/g10/evidence"), "g10 evidence")
        mode = require(client.get("/api/production-mode"), "production mode")
    result = {
        "status": "PASS" if acceptance["rehearsal"]["result"] == "PASS" and restore["rehearsal"]["result"] == "PASS" else "FAIL",
        "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE",
        "fixture": fixture_metadata(),
        "golden_path_v1": v1["status"], "canonical_fixture_check": canonical["status"], "golden_path_v2": v2["status"], "browser_e2e": browser["status"],
        "monitoring": {"first": first["result"], "second": second["result"], "drift": drift["result"]},
        "recurrence": recurrence["analysis"]["summary"], "preventive_checks": len(preventive["checks"]),
        "incident": {"severity": incident["incident"]["severity"], "hold_applied": incident["hold"]["blocks_automated_writes"], "impact_entities": len(impact["impact"]["affected_entities"])},
        "restore": restore["rehearsal"]["result"], "formal_g10_restore": False,
        "acceptance_run_id": acceptance["rehearsal"]["id"], "acceptance": acceptance["rehearsal"]["result"], "acceptance_checks": acceptance["checks"],
        "g10_evidence_items": len(evidence["items"]), "production_mode": mode["decision"]["mode"], "wave3_decision": mode["decision"]["decision"],
        "machine_final_submit": False, "live_ministry_write": False, "optional_automation_branch": "NOT_AUTHORIZED_NOT_BLOCKING", "client_workflow_approval": "BLOCKED_EXTERNAL",
    }
    artifact = Path("artifacts/week13-14-acceptance-result.json"); artifact.parent.mkdir(parents=True, exist_ok=True); artifact.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
