from datetime import date
from concurrent.futures import ThreadPoolExecutor
from time import monotonic
from uuid import uuid4

from backend.app.db import SessionLocal
from backend.app.models import (
    BuildingAsset,
    Document,
    DocumentApprovalState,
    DocumentType,
    DocumentVersion,
    ExternalBody,
    Jurisdiction,
    RequirementDefinition,
    RequirementPolicyItem,
    RequirementPolicyVersion,
    ServiceType,
    ConstructionExecution,
)


OWNER = {"X-Dev-Role": "OWNER_SPONSOR"}
ENGINEERING = {"X-Dev-Role": "RESPONSIBLE_ENGINEER"}


def _project_execution(client, prefix: str):
    suffix = uuid4().hex[:8]
    project = client.post("/api/projects", headers=OWNER, json={"project_number": f"{prefix}-P-{suffix}", "project_name": "Synthetic Completion Project", "municipality": "Doha", "permit_type": "Building"})
    assert project.status_code == 200, project.text
    body = project.json()
    execution = client.post("/api/construction/executions", headers=OWNER, json={"project_id": body["id"], "execution_ref": f"{prefix}-E-{suffix}", "title": "Synthetic completed construction", "scope_description": "Completion handoff"})
    assert execution.status_code == 200, execution.text
    with SessionLocal() as db:
        row = db.get(ConstructionExecution, execution.json()["id"])
        row.work_state = "COMPLETED"
        db.commit()
    return body, execution.json()


def _completion_config():
    suffix = uuid4().hex[:8]
    with SessionLocal() as db:
        service = ServiceType(code=f"BUILDING_COMPLETION_{suffix}", name_en="Synthetic Building Completion", status="ACTIVE")
        body = ExternalBody(code=f"QATAR_MUNICIPALITY_{suffix}", name_en="Synthetic Municipality", body_type="AUTHORITY", status="ACTIVE", verification_state="SYNTHETIC_VERIFIED")
        jurisdiction = Jurisdiction(code=f"QATAR_{suffix}", country_code="QA", name_en="Synthetic Qatar", status="ACTIVE")
        db.add_all([service, body, jurisdiction]); db.flush()
        policy = RequirementPolicyVersion(service_type_id=service.id, jurisdiction_id=jurisdiction.id, external_body_id=body.id, version="SYN-COMPLETION-1", status="ACTIVE", purpose="COMPLETION_CLOSEOUT", effective_from=date(2020, 1, 1), provenance_json={"synthetic": True})
        db.add(policy); db.flush()
        definitions = []
        for code in ["SITE_CLEANLINESS_CERTIFICATE", "GENERAL_COMPLETION_DOCUMENT"]:
            definition = RequirementDefinition(code=f"{code}_{suffix}", name_en=code.replace("_", " "), kind="DOCUMENT", status="ACTIVE")
            db.add(definition); db.flush()
            definitions.append(definition)
            db.add(RequirementPolicyItem(policy_version_id=policy.id, requirement_definition_id=definition.id, order_index=len(definitions), status="ACTIVE", applicability_expression={}))
        document = Document(project_id=None, document_type=DocumentType.OTHER, logical_name=f"completion-evidence-{suffix}", language="EN", source_system="SYNTHETIC", current_version_id=None)
        db.add(document); db.flush()
        version = DocumentVersion(document_id=document.id, version_number=1, source_filename="synthetic-completion-evidence.pdf", source_path_or_reference="synthetic://completion/evidence", sha256=("a" * 64), mime_type="application/pdf", file_size=10, language="EN", approval_state=DocumentApprovalState.APPROVED, source_system="SYNTHETIC", metadata_json={"synthetic": True})
        db.add(version); db.flush(); document.current_version_id = version.id
        db.commit()
        return {"service_type_id": service.id, "external_body_id": body.id, "jurisdiction_id": jurisdiction.id, "policy_id": policy.id, "document_version_id": version.id, "definitions": [x.id for x in definitions]}


def _start(client, project, execution, config, subject_type="Project", subject_id=None):
    response = client.post("/api/completion/start", headers=OWNER, json={"project_id": project["id"], "construction_execution_id": execution["id"], "subject_type": subject_type, "subject_id": subject_id, "service_type_id": config["service_type_id"], "external_body_id": config["external_body_id"], "jurisdiction_id": config["jurisdiction_id"], "idempotency_key": f"completion-start-{uuid4().hex}"})
    assert response.status_code == 200, response.text
    return response.json()


def test_completion_is_explicit_and_reuses_regulatory_case(client):
    project, execution = _project_execution(client, "COMP-START")
    config = _completion_config()
    assert client.get("/api/completion", headers=OWNER).json() == []
    workspace = _start(client, project, execution, config)
    assert workspace["case"]["status"] == "PREPARING"
    assert workspace["link"]["construction_completion_context_id"]
    assert client.get("/api/completion", headers=OWNER).json()[0]["id"] == workspace["case"]["id"]
    retry = client.post("/api/completion/start", headers=OWNER, json={"project_id": project["id"], "construction_execution_id": execution["id"], "service_type_id": config["service_type_id"], "external_body_id": config["external_body_id"], "jurisdiction_id": config["jurisdiction_id"], "idempotency_key": workspace["link"]["idempotency_key"]})
    assert retry.status_code == 200
    assert retry.json()["case"]["id"] == workspace["case"]["id"]


def test_asbuilt_baseline_snapshot_comparison_and_variance_are_separate(client):
    project, execution = _project_execution(client, "COMP-ASBUILT")
    config = _completion_config()
    workspace = _start(client, project, execution, config)
    case_id = workspace["case"]["id"]
    asset = client.post(f"/api/completion/{case_id}/building-assets", headers=ENGINEERING, json={"asset_ref": "B1", "name": "Synthetic Building One", "building_type": "VILLA"}).json()
    approved_snapshot = client.post(f"/api/completion/{case_id}/building-snapshots", headers=ENGINEERING, json={"building_asset_id": asset["id"], "snapshot_type": "AUTHORITY_APPROVED", "values_json": {"area": 100, "floors": 2, "use": "RESIDENTIAL"}})
    assert approved_snapshot.status_code == 200, approved_snapshot.text
    as_built_snapshot = client.post(f"/api/completion/{case_id}/building-snapshots", headers=ENGINEERING, json={"building_asset_id": asset["id"], "snapshot_type": "AS_BUILT", "values_json": {"area": 112, "floors": 2, "use": "RESIDENTIAL"}, "verified_by": "synthetic-professional"})
    assert as_built_snapshot.status_code == 200, as_built_snapshot.text
    revision = client.post(f"/api/completion/{case_id}/as-built/revisions", headers=ENGINEERING, json={"title": "Synthetic As-Built Drawing", "discipline": "ARCHITECTURAL", "revision_code": "AB-1", "document_version_id": config["document_version_id"]})
    assert revision.status_code == 200, revision.text
    revision_id = revision.json()["revision"]["id"]
    review = client.post(f"/api/completion/{case_id}/as-built/revisions/{revision_id}/review", headers=ENGINEERING, json={"status": "APPROVED", "credential_reference": "SYNTH-CRED-1"})
    assert review.status_code == 200, review.text
    rendition_id = revision.json()["rendition"]["id"]
    baseline = client.post(f"/api/completion/{case_id}/as-built/baselines", headers=ENGINEERING, json={"baseline_ref": "AB-1", "members":[{"engineering_revision_id": revision_id, "rendition_id": rendition_id, "document_version_id": config["document_version_id"], "building_snapshot_id": as_built_snapshot.json()["id"]}]})
    assert baseline.status_code == 200, baseline.text
    baseline_id = baseline.json()["baseline"]["id"]
    approved = client.post(f"/api/completion/{case_id}/as-built/baselines/{baseline_id}/approve", headers=OWNER, json={})
    assert approved.status_code == 200 and approved.json()["status"] == "APPROVED"
    comparison = client.post(f"/api/completion/{case_id}/comparisons", headers=ENGINEERING, json={"baseline_id": baseline_id, "approved_snapshot_id": approved_snapshot.json()["id"], "as_built_snapshot_id": as_built_snapshot.json()["id"]})
    assert comparison.status_code == 200 and comparison.json()["run"]["result"] == "DIFFERENCE_DETECTED"
    variance = comparison.json()["variances"][0]
    disposition = client.patch(f"/api/completion/{case_id}/variances/{variance['id']}/disposition", headers=ENGINEERING, json={"disposition":"ACCEPTABLE_NO_ACTION", "reason":"Synthetic professional disposition"})
    assert disposition.status_code == 200 and disposition.json()["status"] == "DISPOSITIONED"
    assert client.get(f"/api/completion/{case_id}/readiness", headers=OWNER).json()["stage"] == "COMPLETION_REQUIREMENTS"
    assert approved.json()["id"] == baseline_id


def test_completion_requirements_evidence_forms_and_submission_loop(client):
    project, execution = _project_execution(client, "COMP-SUBMIT")
    config = _completion_config()
    workspace = _start(client, project, execution, config)
    case_id = workspace["case"]["id"]
    requirement_init = client.post(f"/api/completion/{case_id}/requirements/initialize", headers=ENGINEERING, json={})
    assert requirement_init.status_code == 200, requirement_init.text
    items = requirement_init.json()["items"]
    assert all(x["purpose"] == "COMPLETION_CLOSEOUT" for x in items)
    for item in items:
        decision = client.post(f"/api/authority-cases/{case_id}/requirements/{item['id']}/decision", headers=ENGINEERING, json={"decision":"APPLICABLE", "reason":"Synthetic policy applies"})
        assert decision.status_code == 200, decision.text
        evidence_kind = "INTERNAL_DECLARATION" if "SITE_CLEANLINESS" in item["source_snapshot"].get("policy_item_id", "") else "DOCUMENT"
        evidence = client.post(f"/api/completion/{case_id}/requirements/{item['id']}/evidence", headers=ENGINEERING, json={"evidence_kind": evidence_kind, "document_version_id": config["document_version_id"], "status":"VERIFIED"})
        assert evidence.status_code == 200, evidence.text
    # No form source was supplied, so the generic precheck cannot claim PASS.
    prep = client.post(f"/api/completion/{case_id}/preparations", headers=ENGINEERING, json={})
    assert prep.status_code == 409


def test_completion_finding_cycle_outcome_and_handover_seam(client):
    project, execution = _project_execution(client, "COMP-OUTCOME")
    config = _completion_config()
    workspace = _start(client, project, execution, config)
    case_id = workspace["case"]["id"]
    with SessionLocal() as db:
        link = db.scalar(__import__("sqlalchemy", fromlist=["select"]).select(__import__("backend.app.models", fromlist=["CompletionCaseLink"]).CompletionCaseLink).where(__import__("backend.app.models", fromlist=["CompletionCaseLink"]).CompletionCaseLink.authority_case_id == case_id))
        assert link.project_id == project["id"]
    assert client.get(f"/api/completion/{case_id}/outcome-context", headers=OWNER).json()["handover_created"] is False


def test_completion_full_precheck_submission_finding_and_verified_outcome(client):
    project, execution = _project_execution(client, "COMP-FULL")
    config = _completion_config()
    workspace = _start(client, project, execution, config)
    case_id = workspace["case"]["id"]

    asset = client.post(
        f"/api/completion/{case_id}/building-assets",
        headers=ENGINEERING,
        json={"asset_ref": "B1", "name": "Synthetic Building One", "building_type": "VILLA"},
    ).json()
    approved_snapshot = client.post(
        f"/api/completion/{case_id}/building-snapshots",
        headers=ENGINEERING,
        json={"building_asset_id": asset["id"], "snapshot_type": "AUTHORITY_APPROVED", "values_json": {"area": 100, "floors": 2}},
    ).json()
    as_built_snapshot = client.post(
        f"/api/completion/{case_id}/building-snapshots",
        headers=ENGINEERING,
        json={"building_asset_id": asset["id"], "snapshot_type": "AS_BUILT", "values_json": {"area": 100, "floors": 2}, "verified_by": "synthetic-professional"},
    ).json()
    revision_response = client.post(
        f"/api/completion/{case_id}/as-built/revisions",
        headers=ENGINEERING,
        json={"title": "Synthetic As-Built Drawing", "discipline": "ARCHITECTURAL", "revision_code": "AB-1", "document_version_id": config["document_version_id"]},
    )
    assert revision_response.status_code == 200, revision_response.text
    revision = revision_response.json()
    review = client.post(
        f"/api/completion/{case_id}/as-built/revisions/{revision['revision']['id']}/review",
        headers=ENGINEERING,
        json={"status": "APPROVED", "credential_reference": "SYNTH-CRED-FULL"},
    )
    assert review.status_code == 200, review.text
    baseline_response = client.post(
        f"/api/completion/{case_id}/as-built/baselines",
        headers=ENGINEERING,
        json={"baseline_ref": "AB-1", "members": [{"engineering_revision_id": revision["revision"]["id"], "rendition_id": revision["rendition"]["id"], "document_version_id": config["document_version_id"], "building_snapshot_id": as_built_snapshot["id"]}]},
    )
    assert baseline_response.status_code == 200, baseline_response.text
    baseline_id = baseline_response.json()["baseline"]["id"]
    assert client.post(f"/api/completion/{case_id}/as-built/baselines/{baseline_id}/approve", headers=OWNER, json={}).status_code == 200
    comparison = client.post(
        f"/api/completion/{case_id}/comparisons",
        headers=ENGINEERING,
        json={"baseline_id": baseline_id, "approved_snapshot_id": approved_snapshot["id"], "as_built_snapshot_id": as_built_snapshot["id"]},
    )
    assert comparison.status_code == 200 and comparison.json()["run"]["result"] == "MATCH"

    requirement_init = client.post(f"/api/completion/{case_id}/requirements/initialize", headers=ENGINEERING, json={})
    assert requirement_init.status_code == 200, requirement_init.text
    items = requirement_init.json()["items"]
    for item in items:
        assert client.post(f"/api/authority-cases/{case_id}/requirements/{item['id']}/decision", headers=ENGINEERING, json={"decision": "APPLICABLE", "reason": "Synthetic governed applicability"}).status_code == 200
        evidence = client.post(f"/api/completion/{case_id}/requirements/{item['id']}/evidence", headers=ENGINEERING, json={"evidence_kind": "AUTHORITY_CERTIFICATE", "document_version_id": config["document_version_id"], "status": "VERIFIED"})
        assert evidence.status_code == 200, evidence.text

    preparation = client.post(f"/api/completion/{case_id}/preparations", headers=ENGINEERING, json={})
    assert preparation.status_code == 200, preparation.text
    preparation = preparation.json()
    assert client.post(f"/api/completion/{case_id}/preparations/{preparation['id']}/lock", headers=OWNER, json={}).status_code == 200
    package = client.post(f"/api/completion/{case_id}/packages?preparation_revision_id={preparation['id']}", headers=ENGINEERING)
    assert package.status_code == 200, package.text
    package = package.json()
    item = client.post(f"/api/completion/{case_id}/packages/{package['id']}/items", headers=ENGINEERING, json={"item_type": "AS_BUILT_BASELINE", "as_built_baseline_id": baseline_id})
    assert item.status_code == 200, item.text
    assert client.post(f"/api/completion/{case_id}/packages/{package['id']}/lock", headers=OWNER, json={}).status_code == 200
    precheck = client.post(f"/api/completion/{case_id}/precheck?preparation_revision_id={preparation['id']}&submission_package_id={package['id']}", headers=ENGINEERING)
    assert precheck.status_code == 200 and precheck.json()["run"]["result"] == "PASS", precheck.text

    attempt = client.post(
        f"/api/completion/{case_id}/submit-authorization",
        headers=OWNER,
        json={"preparation_revision_id": preparation["id"], "submission_package_id": package["id"], "precheck_run_id": precheck.json()["run"]["id"], "idempotency_key": f"full-submit-{uuid4().hex}"},
    )
    assert attempt.status_code == 200 and attempt.json()["state"] == "PENDING_EXTERNAL_CONFIRMATION"
    confirmation = client.post(f"/api/completion/{case_id}/submission-attempts/{attempt.json()['id']}/external-confirmation", headers=OWNER, json={"external_reference": "SYNTH-COMP-RECEIPT-1"})
    assert confirmation.status_code == 200, confirmation.text
    cycle_id = confirmation.json()["cycle"]["id"]
    finding = client.post(f"/api/completion/{case_id}/findings", headers=ENGINEERING, json={"submission_cycle_id": cycle_id, "category": "DOCUMENT", "title": "Synthetic completion clarification", "raw_text": "Provide the final verified certificate reference.", "severity": "MAJOR", "engineering_impact": "NONE"})
    assert finding.status_code == 200, finding.text
    response = client.post(f"/api/completion/{case_id}/findings/{finding.json()['id']}/responses", headers=ENGINEERING, json={"response_text": "Certificate reference verified in the controlled evidence set."})
    assert response.status_code == 200 and response.json()["status"] == "PREPARED"
    outcome = client.post(f"/api/completion/{case_id}/outcomes", headers=OWNER, json={"submission_cycle_id": cycle_id, "external_identifier": "SYNTH-COMPLETION-CERT-1"})
    assert outcome.status_code == 200 and outcome.json()["handover_created"] is False
    context = client.get(f"/api/completion/{case_id}/outcome-context", headers=OWNER)
    assert context.status_code == 200 and context.json()["handover_ready"] is True and context.json()["handover_created"] is False


def test_completion_start_idempotency_is_concurrent_safe(client):
    project, execution = _project_execution(client, "COMP-CONCURRENT")
    config = _completion_config()
    payload = {"project_id": project["id"], "construction_execution_id": execution["id"], "subject_type": "Project", "subject_id": project["id"], "service_type_id": config["service_type_id"], "external_body_id": config["external_body_id"], "jurisdiction_id": config["jurisdiction_id"], "idempotency_key": f"completion-concurrent-{uuid4().hex}"}
    def start_once():
        return client.post("/api/completion/start", headers=OWNER, json=payload)
    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(lambda _index: start_once(), range(4)))
    assert all(response.status_code == 200 for response in responses), [response.text for response in responses]
    assert len({response.json()["case"]["id"] for response in responses}) == 1


def test_completion_workspace_scales_to_one_thousand_building_assets(client):
    project, execution = _project_execution(client, "COMP-SCALE")
    config = _completion_config()
    workspace = _start(client, project, execution, config)
    with SessionLocal() as db:
        db.bulk_save_objects([BuildingAsset(project_id=project["id"], asset_ref=f"B-{index:04d}", name=f"Synthetic Building {index:04d}", building_type="VILLA", created_by="synthetic-scale") for index in range(1000)])
        db.commit()
    started = monotonic()
    response = client.get(f"/api/completion/{workspace['case']['id']}", headers=OWNER)
    elapsed = monotonic() - started
    assert response.status_code == 200, response.text
    assert len(response.json()["building_assets"]) == 1000
    assert elapsed < 1.5
