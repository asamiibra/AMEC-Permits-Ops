"""Execute Golden Path 0A and Golden Path 0 on the controlled synthetic seed."""

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.seed.cli import seed


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "artifacts" / "expansion"


def main():
    seed()
    checks = []
    with TestClient(app) as client:
        policy = client.get("/api/execution-policy").json()
        checks += [policy["execution_authority"] == "PROTOTYPE_DEV_ONLY", policy["no_real_side_effects"] is True]
        opportunity = client.get("/api/opportunities").json()[0]
        opportunity_id = opportunity["id"]
        project = client.get("/api/projects").json()[0]
        documents = client.get(f"/api/projects/{project['id']}/documents").json()
        document_version_id = next(item["current_version_id"] for item in documents if item.get("current_version_id"))
        checks += [bool(opportunity["client_account_id"]), bool(project["project_number"]), bool(document_version_id)]
        transition = client.post(f"/api/opportunities/{opportunity_id}/intake/review", json={"status": "READY_FOR_QUOTATION", "actor": "bd", "actor_role": "BD_USER"})
        checks += [transition.status_code == 200, transition.json()["status"] == "READY_FOR_QUOTATION"]
        fields = {"SCOPE": "Synthetic permit coordination", "AREA": "1000 sqm", "PRICE": "CANDIDATE-QAR", "DURATION": "60 days", "PAYMENT_CONDITION": "Milestone tracking", "INCLUSION": "Permit coordination", "EXCLUSION": "Government fees", "REFERENCE": "SYN-RFQ", "CLIENT_NAME": "Synthetic Client Holdings", "CLIENT_CONTACT": "Synthetic Client Contact", "PROJECT_NAME": "Synthetic Building Advisory Opportunity", "PROCESS_OF_WORK": "Human-reviewed synthetic workflow"}
        revision_response = client.post(f"/api/opportunities/{opportunity_id}/quotation/revisions", json={"field_values": fields, "actor": "bd"})
        checks += [revision_response.status_code == 200]
        revision = revision_response.json()
        observations = client.post(f"/api/quotation-revisions/{revision['id']}/extract-or-propose", json={"fields": fields, "actor": "bd"}).json()["observations"]
        checks += [len(observations) >= 12, all(item["state"] == "CANDIDATE" for item in observations), all(item["approved_offer_value"] is None for item in observations)]
        for observation in observations:
            verified = client.post(f"/api/quotation-revisions/{revision['id']}/verify-field", json={"field_code": observation["field_code"], "verified_value": observation["candidate_value"], "actor": "verifier", "actor_role": "BD_USER"})
            checks += [verified.status_code == 200, verified.json()["state"] == "VERIFIED"]
        submitted = client.post(f"/api/quotation-revisions/{revision['id']}/submit-commercial-review", json={"actor": "bd"})
        checks += [submitted.status_code == 200, submitted.json()["status"] == "IN_COMMERCIAL_REVIEW"]
        denied = client.post(f"/api/quotation-revisions/{revision['id']}/commercial-approval", json={"actor": "bd", "actor_role": "BD_USER"})
        checks += [denied.status_code == 403]
        approved = client.post(f"/api/quotation-revisions/{revision['id']}/commercial-approval", json={"actor": "commercial", "actor_role": "COMMERCIAL_APPROVER", "approved_offer_values": {"PRICE": "HUMAN-APPROVED-QAR", "PAYMENT_CONDITION": "Human-approved milestone"}})
        checks += [approved.status_code == 200, approved.json()["revision"]["status"] == "APPROVED_FOR_RELEASE"]
        rendered = client.post(f"/api/quotation-revisions/{revision['id']}/render", json={"actor": "renderer"})
        checks += [rendered.status_code == 200, rendered.json()["artifact"]["status"] == "RENDERED", bool(rendered.json()["artifact"]["content_hash"]), bool(rendered.json()["artifact"]["template_version_id"])]
        released = client.post(f"/api/quotation-revisions/{revision['id']}/release", json={"actor": "bd"})
        checks += [released.status_code == 200, released.json()["draft"]["status"] == "HUMAN_REVIEW", released.json()["draft"]["status"] != "SENT"]
        accepted = client.post(f"/api/opportunities/{opportunity_id}/client-response", json={"response_type": "ACCEPTED", "evidence_reference": "synthetic://client-acceptance", "actor": "bd"})
        checks += [accepted.status_code == 200, accepted.json()["response_type"] == "ACCEPTED"]
        readiness = client.get(f"/api/opportunities/{opportunity_id}/contract-transition-readiness").json()
        checks += [readiness["state"] == "READY_FOR_CONTRACT", readiness["blockers"] == [], readiness["quotation_revision_id"] == revision["id"]]
        contract_response = client.post(f"/api/opportunities/{opportunity_id}/contracts", json={"actor": "admin"})
        checks += [contract_response.status_code == 200]
        contract = contract_response.json()["contract"]; contract_revision = contract_response.json()["revision"]
        checks += [contract_revision["controlling_quotation_revision_id"] == revision["id"], bool(contract_revision["commercial_terms_snapshot"])]
        contract_render = client.post(f"/api/contract-revisions/{contract_revision['id']}/render", json={"actor": "renderer", "fields": {"contract_reference": contract["contract_reference"]}})
        checks += [contract_render.status_code == 200, contract_render.json()["revision"]["rendered_artifact_id"] == contract_render.json()["artifact"]["id"], bool(contract_render.json()["revision"]["template_version_id"])]
        contract_review = client.post(f"/api/contract-revisions/{contract_revision['id']}/submit-review", json={"actor": "admin"})
        checks += [contract_review.status_code == 200, contract_review.json()["status"] == "IN_REVIEW"]
        contract_denied = client.post(f"/api/contract-revisions/{contract_revision['id']}/approval", json={"actor": "ai", "actor_role": "BD_USER"})
        checks += [contract_denied.status_code == 403]
        contract_approval = client.post(f"/api/contract-revisions/{contract_revision['id']}/approval", json={"actor": "contract-approver", "actor_role": "CONTRACT_APPROVER"})
        checks += [contract_approval.status_code == 200, contract_approval.json()["revision"]["status"] == "APPROVED"]
        execution = client.post(f"/api/contract-revisions/{contract_revision['id']}/execution-evidence", json={"actor": "contract-approver", "actor_role": "CONTRACT_APPROVER", "evidence_reference": "synthetic://execution-evidence"})
        checks += [execution.status_code == 200, execution.json()["execution_status"] == "EXECUTED_EVIDENCE_RECORDED"]
        checklist = client.post(f"/api/contracts/{contract['id']}/checklist/evaluate", json={"actor": "admin"})
        checks += [checklist.status_code == 200, checklist.json()["state"] == "BLOCKED"]
        item_id = checklist.json()["blocking_item_ids"][0]
        request = client.post(f"/api/checklist-items/{item_id}/document-request", json={"actor": "admin"})
        checks += [request.status_code == 200, request.json()["draft"]["status"] == "HUMAN_REVIEW", request.json()["draft"]["policy_state"] == "HUMAN_SEND"]
        passed = client.post(f"/api/contracts/{contract['id']}/checklist/evaluate", json={"actor": "admin", "document_version_id": document_version_id})
        checks += [passed.status_code == 200, passed.json()["state"] == "PASS"]
        reference = client.post(f"/api/opportunities/{opportunity_id}/reference/assign", json={"actor": "admin"})
        checks += [reference.status_code == 200, reference.json()["draft"]["status"] == "HUMAN_REVIEW", bool(reference.json()["reference"]["reference_value"])]
        bootstrap = client.post(f"/api/opportunities/{opportunity_id}/project-bootstrap", json={"project_id": project["id"], "actor": "admin"})
        checks += [bootstrap.status_code == 200, bootstrap.json()["external_writes"] is False, bootstrap.json()["projection"]["reference_number"] == reference.json()["reference"]["reference_value"]]
        projection = client.get(f"/api/projects/{project['id']}/project-status-projection").json()
        checks += [all(key in projection for key in ["reference_number", "name", "client", "payment", "status", "engineer_email"])]
        handoff = client.post(f"/api/projects/{project['id']}/handoff-to-permit", json={"actor": "admin"})
        checks += [handoff.status_code == 200, handoff.json()["external_submission"] is False, bool(handoff.json()["permit_application"])]
    result = {"result": "PASS" if all(checks) else "FAIL", "assertion_count": len(checks), "labels": ["E3_BD_ASSISTANT_READY", "GOLDEN_PATH_0A_PASS", "E4_ADMIN_PROJECT_COORDINATION_READY", "GOLDEN_PATH_0_PASS", "READY_FOR_EXPANSION_GATE_E5"], "execution_authority": "PROTOTYPE_DEV_ONLY", "real_external_actions": False}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "e3-golden-path-0a-result.json").write_text(json.dumps({**result, "scope": "RFQ → quotation → human commercial approval → release → client acceptance → READY_FOR_CONTRACT"}, indent=2) + "\n")
    (OUT / "e4-golden-path-0-result.json").write_text(json.dumps({**result, "scope": "accepted quotation → contract → human approval → execution evidence → checklist → reference → project bootstrap → permit handoff"}, indent=2) + "\n")
    print(json.dumps({**result, "failed_assertions": [index for index, value in enumerate(checks) if not value]}))
    if result["result"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
