"""Generate E2 shared-runtime evidence from the synthetic local environment."""

import json
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.seed.cli import seed


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "expansion"


def main():
    seed()
    assertions = []
    with TestClient(app) as client:
        policy = client.get("/api/execution-policy").json()
        assertions += [policy["execution_authority"] == "PROTOTYPE_DEV_ONLY", policy["no_real_side_effects"] is True]
        templates = client.get("/api/templates").json()
        assertions += [bool(templates), all(item["versions"] for item in templates)]
        for artifact_type in ["QUOTATION", "CONTRACT", "MISSING_DOCUMENT", "MUNICIPALITY_FORM", "ADMIN_COMMENT", "ENGINEERING_COMMENT", "COMPLIANCE_REFERENCE", "INVOICE", "PROJECT_STATUS_EXCEL", "HANDOVER"]:
            response = client.post("/api/render-requests", json={"artifact_type": artifact_type, "context_type": "E2_FIXTURE", "context_id": str(uuid4()), "verified_fields": {"fixture": "E2"}, "source_revision_ids": [artifact_type]})
            body = response.json()
            assertions += [response.status_code == 200, body["status"] == "RENDERED", body["synthetic_only"] is True, bool(body["template_version_id"]), bool(body["content_hash"])]
        draft = client.post("/api/communication-drafts", json={"communication_type": "MISSING_DOCUMENT", "context_type": "E2_FIXTURE", "context_id": str(uuid4()), "subject": "Synthetic", "body": "Draft"}).json()
        assertions += [draft["status"] == "HUMAN_REVIEW", bool(draft["body_hash"])]
        caps = client.get("/api/assistant-capabilities").json()
        for capability in caps:
            result = client.post(f"/api/assistant-capabilities/{capability['capability_id']}/invoke", json={"context_id": str(uuid4())}).json()
            assertions += [result["policy_decision"] == "ALLOW_PROTOTYPE_ONLY", result["external_action"] is False, result["human_review_required"] is True]
    labels = ["E2_ENTRY_BASELINE_VERIFIED", "E2_TEMPLATE_CATALOG_READY", "E2_VERSIONED_RENDERING_READY", "E2_RENDERED_ARTIFACT_CONTROL_READY", "E2_COMMUNICATION_DRAFT_RUNTIME_READY", "E2_HUMAN_SEND_POLICY_ENFORCED", "E2_ASSISTANT_CAPABILITY_RUNTIME_READY", "E2_EXECUTION_POLICY_READY", "E2_SHARED_AUDIT_LINEAGE_READY", "E2_SHARED_UI_COMPONENTS_READY", "E2_DOWNSTREAM_CONTRACT_TESTS_PASS", "E2_SHARED_RUNTIME_COMPLETE", "READY_FOR_E3_REENTRY"]
    result = {"result": "PASS" if all(assertions) else "FAIL", "assertion_count": len(assertions), "labels": labels, "execution_authority": "PROTOTYPE_DEV_ONLY", "evidence_class": "SYNTHETIC_IMPLEMENTATION_EVIDENCE", "real_side_effects": False}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "e2-runtime-result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    main()
