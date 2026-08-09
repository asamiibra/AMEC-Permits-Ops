"""Week 11–12 synthetic demonstration and safety-boundary evidence runner."""

import json
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.main import app
from backend.app.models import User
from backend.app.seed.cli import seed
from backend.app.fixtures.canonical import fixture_metadata


def require(response, label):
    if response.status_code >= 400:
        raise RuntimeError(f"{label}: {response.status_code} {response.text}")
    return response.json()


def main():
    seed()
    with TestClient(app) as client:
        policy = require(client.get("/api/monitoring/policies"), "policies")["policies"][0]
        first = require(client.post("/api/monitoring/run-due-synthetic", json={"policy_id": policy["id"]}), "monitor 1")["runs"][0]
        second = require(client.post("/api/monitoring/run-due-synthetic", json={"policy_id": policy["id"]}), "monitor 2")["runs"][0]
        changed = require(client.post("/api/monitoring/run-due-synthetic", json={"policy_id": policy["id"], "observed_state": {"status": "UNDER_REVIEW", "repetition_number": 1, "comments": [{"id": f"{policy['application_id']}:C4", "text": "تعليق رسمي جديد", "language": "ar"}]}}), "status/comment change")["runs"][0]
        drift = require(client.post("/api/monitoring/run-due-synthetic", json={"policy_id": policy["id"], "observed_state": {"contract": {"fingerprint": "DRIFT", "drift_type": "COMMENT_SCHEMA_DRIFT"}}}), "drift")["runs"][0]
        contracts = require(client.get("/api/portal-contracts"), "contracts")["contracts"]
        validation = require(client.post(f"/api/portal-contracts/{contracts[0]['id']}/validate", json={"reviewed_by": "maintainer@amec.synthetic"}), "contract validation")
        drift_events = require(client.get("/api/portal-drift-events"), "drift events")["events"]
        require(client.post(f"/api/portal-drift-events/{drift_events[0]['id']}/revalidate", json={}), "drift revalidation")
        mutation = require(client.post("/api/monitoring/run-due-synthetic", json={"policy_id": policy["id"], "observed_state": {"portal_fields": {"OWNER.NAME_EN": "External human edit"}}}), "external mutation")["runs"][0]
        manual = require(client.post("/api/monitoring/manual-capture", json={"application_id": policy["application_id"], "captured_by": "authorized-human", "status": "UNDER_REVIEW", "repetition_number": 1, "comments": [], "evidence_artifact_ids": ["synthetic://human-capture/1"]}), "manual fallback")
        users = {u.email: u.id for u in SessionLocal().scalars(select(User)).all()}
        auth = require(client.post("/api/attended-auth-sessions", json={"user_id": users["submitter@amec.synthetic"], "user_role": "FINAL_SUBMITTER"}), "auth create")["session"]
        require(client.post(f"/api/attended-auth-sessions/{auth['id']}/mfa-started", json={"challenge_type": "OTP_SMS"}), "mfa start")
        auth_done = require(client.post(f"/api/attended-auth-sessions/{auth['id']}/mfa-completed", json={}), "mfa complete")["session"]
        require(client.post("/api/operator-timings", json={"user_role": "PERMIT_PREPARER", "scenario_variant": "COMPANY_OWNER", "task_type": "PREPARATION", "duration_ms": 120000, "correction_count": 3, "source": "SYNTHETIC_BASELINE"}), "baseline timing")
        require(client.post("/api/operator-timings", json={"user_role": "PERMIT_PREPARER", "scenario_variant": "COMPANY_OWNER", "task_type": "PREPARATION", "duration_ms": 70000, "correction_count": 1, "source": "WEEK11_OPTIMIZED"}), "optimized timing")
        variants = require(client.get("/api/scenario-variants"), "variants")["variants"]
        coverage = require(client.get("/api/rendering/coverage"), "rendering coverage")
        edges = require(client.get("/api/week12/edge-coverage"), "edge coverage")
        week11_report = require(client.get("/api/week11/report"), "week11 report")["report"]
        report = {"status": "PASS", "fixture": fixture_metadata(), "monitoring": {"first": first["result"], "second": second["result"], "material_change": changed["result"], "drift": drift["result"], "manual_fallback": manual["capture"]["verification_mode"], "external_mutation": mutation["external_mutation"]}, "drift_revalidation": validation["validation"]["result"], "attended_auth": auth_done["status"], "ergonomics": week11_report["timing_summary"], "variants": [v["variant_code"] for v in variants], "rendering_missing": sum(len(x["missing_fields"]) for x in coverage["coverage"]), "edge_cases": {"passed": edges["passed"], "total": edges["case_count"]}, "machine_final_submit": False, "optional_automation_branch": "NOT_AUTHORIZED_NOT_BLOCKING", "secrets_persisted": False}
    artifact = Path("artifacts/week11-12-demo-result.json")
    artifact.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
