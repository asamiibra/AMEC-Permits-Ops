from datetime import date, datetime, timezone
from uuid import uuid4

from backend.app.db import SessionLocal
from backend.app.models import (
    ApprovedDesignBaseline, ApprovedDesignBaselineMember, ConsultancyOffice, Document, DocumentApprovalState,
    DocumentType, DocumentVersion, EngineeringDeliverable, EngineeringDeliverableRevision,
    EngineeringRendition, EngineeringWorkPackage, ExternalBody, Jurisdiction,
    Project, RequirementDefinition, RequirementPolicyItem, RequirementPolicyVersion,
    ServiceType,
)


def _headers(role="SYSTEM_ADMIN", actor="loop-owner"):
    return {"X-Dev-Role": role, "X-Dev-Actor": actor}


def test_authority_case_preparation_submission_and_confirmation_loop(client):
    suffix = uuid4().hex[:10].upper()
    with SessionLocal() as db:
        office = db.query(ConsultancyOffice).first()
        project = Project(project_number=f"LOOP-{suffix}", project_name="Synthetic Loop Project", office_id=office.id, workstream="REGULATORY", status="ACTIVE", municipality="Synthetic Municipality", permit_type="Building", activated_at=datetime.now(timezone.utc), activated_by="loop-owner")
        body = ExternalBody(code=f"LOOP-BODY-{suffix}", name_en="Synthetic Authority", body_type="AUTHORITY", status="ACTIVE", verification_state="VERIFIED", created_by="loop-owner")
        jurisdiction = Jurisdiction(code=f"LOOP-JUR-{suffix}", country_code="QA", name_en="Synthetic Jurisdiction", level="LOCALITY", status="ACTIVE")
        service = ServiceType(code=f"LOOP-SERVICE-{suffix}", name_en="Synthetic Building Service", status="ACTIVE")
        definition = RequirementDefinition(code=f"LOOP-REQ-{suffix}", name_en="Approved evidence", kind="DOCUMENT", status="ACTIVE")
        policy = RequirementPolicyVersion(service_type_id=service.id, jurisdiction_id=jurisdiction.id, external_body_id=body.id, version="RP1", status="ACTIVE", effective_from=date.today(), purpose="AUTHORITY_SUBMISSION", approved_by="loop-owner", approved_at=datetime.now(timezone.utc))
        db.add_all([project, body, jurisdiction, service, definition]); db.flush()
        policy.service_type_id = service.id; policy.jurisdiction_id = jurisdiction.id; policy.external_body_id = body.id
        db.add(policy); db.flush()
        policy_item = RequirementPolicyItem(policy_version_id=policy.id, requirement_definition_id=definition.id, status="ACTIVE", order_index=1)
        document = Document(project_id=project.id, document_type=DocumentType.OTHER, logical_name="loop-evidence.pdf", language="EN", source_system="SYNTHETIC")
        db.add_all([policy_item, document]); db.flush()
        version = DocumentVersion(document_id=document.id, version_number=1, source_filename="loop-evidence.pdf", source_path_or_reference="synthetic://loop-evidence", sha256="a" * 64, mime_type="application/pdf", file_size=10, language="EN", approval_state=DocumentApprovalState.APPROVED, source_system="SYNTHETIC", valid_until=date.today())
        document.current_version_id = version.id
        wp = EngineeringWorkPackage(project_id=project.id, package_ref=f"WP-{suffix}", title="Loop package", owner_actor="loop-owner")
        db.add_all([version, wp]); db.flush()
        deliverable = EngineeringDeliverable(project_id=project.id, work_package_id=wp.id, deliverable_ref=f"D-{suffix}", title="Approved drawing", created_by="loop-owner", status="APPROVED")
        db.add(deliverable); db.flush()
        revision = EngineeringDeliverableRevision(project_id=project.id, deliverable_id=deliverable.id, revision_code="R1", sequence=1, title="Approved drawing R1", approval_status="PROFESSIONALLY_APPROVED", status="APPROVED", prepared_by="loop-engineer", immutable_at=datetime.now(timezone.utc))
        db.add(revision); db.flush()
        rendition = EngineeringRendition(project_id=project.id, revision_id=revision.id, document_version_id=version.id, rendition_kind="PUBLISHED", content_hash="b" * 64, created_by="loop-engineer")
        db.add(rendition); db.flush()
        baseline = ApprovedDesignBaseline(project_id=project.id, baseline_ref=f"B1-{suffix}", purpose="AMEC_APPROVED_DESIGN", status="APPROVED", manifest_hash="c" * 64, manifest_json={"members": [rendition.id]}, validation_json={"valid": True}, approved_by="loop-professional", approval_credential_reference="SYNTHETIC-CREDENTIAL", approved_at=datetime.now(timezone.utc), created_by="loop-owner")
        db.add(baseline); db.flush()
        member = ApprovedDesignBaselineMember(baseline_id=baseline.id, project_id=project.id, revision_id=revision.id, rendition_id=rendition.id, member_role="APPROVED_DESIGN_INPUT", pinned_hash="d" * 64)
        db.add(member); db.commit()
        ids = {"project": project.id, "body": body.id, "jurisdiction": jurisdiction.id, "service": service.id, "policy": policy.id, "version": version.id, "baseline": baseline.id}

    denied = client.post("/api/authority-cases", headers=_headers("RESPONSIBLE_ENGINEER", "engineer"), json={"project_id": ids["project"], "external_body_id": ids["body"], "jurisdiction_id": ids["jurisdiction"], "service_type_id": ids["service"], "idempotency_key": f"case-denied-{suffix}"})
    assert denied.status_code == 403
    created = client.post("/api/authority-cases", headers=_headers(), json={"project_id": ids["project"], "external_body_id": ids["body"], "jurisdiction_id": ids["jurisdiction"], "service_type_id": ids["service"], "case_reference": f"CASE-{suffix}", "idempotency_key": f"case-{suffix}"})
    assert created.status_code == 200, created.text
    case_id = created.json()["case"]["id"]
    replayed = client.post("/api/authority-cases", headers=_headers(), json={"project_id": ids["project"], "external_body_id": ids["body"], "jurisdiction_id": ids["jurisdiction"], "service_type_id": ids["service"], "idempotency_key": f"case-{suffix}"})
    assert replayed.status_code == 200
    assert replayed.json()["case"]["id"] == case_id
    initialized = client.post(f"/api/authority-cases/{case_id}/requirements/initialize", headers=_headers(), json={})
    assert initialized.status_code == 200, initialized.text
    instance = initialized.json()["items"][0]
    assert instance["applicability"] == "APPLICABILITY_UNKNOWN"
    assert client.post(f"/api/authority-cases/{case_id}/requirements/{instance['id']}/decision", headers=_headers(), json={"decision": "APPLICABLE", "reason": "Synthetic service requires approved evidence"}).status_code == 200
    evidence = client.post(f"/api/authority-cases/{case_id}/requirements/{instance['id']}/evidence", headers=_headers(), json={"document_version_id": ids["version"]})
    assert evidence.status_code == 200, evidence.text
    prep = client.post(f"/api/authority-cases/{case_id}/preparations", headers=_headers(), json={"approved_design_baseline_id": ids["baseline"]})
    assert prep.status_code == 200, prep.text
    prep_id = prep.json()["id"]
    locked_prep = client.post(f"/api/authority-cases/{case_id}/preparations/{prep_id}/lock", headers=_headers(), json={})
    assert locked_prep.status_code == 200, locked_prep.text
    assert locked_prep.json()["authority_state"] == "LOCKED"
    package = client.post(f"/api/authority-cases/{case_id}/packages", headers=_headers(), json={"preparation_revision_id": prep_id}).json()
    package_id = package["id"]
    added = client.post(f"/api/authority-cases/{case_id}/packages/{package_id}/items", headers=_headers(), json={"item_type": "DOCUMENT", "requirement_instance_id": instance["id"], "document_version_id": ids["version"], "label": "Approved evidence"})
    assert added.status_code == 200, added.text
    locked_package = client.post(f"/api/authority-cases/{case_id}/packages/{package_id}/lock", headers=_headers(), json={})
    assert locked_package.status_code == 200, locked_package.text
    precheck = client.post(f"/api/authority-cases/{case_id}/precheck", headers=_headers(), json={"submission_package_id": package_id})
    assert precheck.status_code == 200, precheck.text
    assert precheck.json()["run"]["result"] == "PASS", precheck.text
    precheck_id = precheck.json()["run"]["id"]
    unauthorized = client.post(f"/api/authority-cases/{case_id}/submit/authorize", headers=_headers("PROCESS_CHAMPION", "bd"), json={"submission_package_id": package_id, "precheck_run_id": precheck_id, "idempotency_key": f"attempt-denied-{suffix}"})
    assert unauthorized.status_code == 403
    attempt = client.post(f"/api/authority-cases/{case_id}/submit/authorize", headers=_headers(), json={"submission_package_id": package_id, "precheck_run_id": precheck_id, "channel_code": "MANUAL_PORTAL", "idempotency_key": f"attempt-{suffix}"})
    assert attempt.status_code == 200, attempt.text
    assert attempt.json()["state"] == "PENDING_EXTERNAL_CONFIRMATION"
    attempt_id = attempt.json()["id"]
    attempt_replay = client.post(f"/api/authority-cases/{case_id}/submit/authorize", headers=_headers(), json={"submission_package_id": package_id, "precheck_run_id": precheck_id, "channel_code": "MANUAL_PORTAL", "idempotency_key": f"attempt-{suffix}"})
    assert attempt_replay.status_code == 200
    assert attempt_replay.json()["id"] == attempt_id
    confirmed = client.post(f"/api/authority-cases/{case_id}/submit/confirm", headers=_headers(), json={"submission_attempt_id": attempt_id, "confirmation_source": "MANUAL_CONFIRMED", "external_reference": f"EXT-{suffix}", "identifier_type": "APPLICATION_NUMBER", "identifier_value": f"APP-{suffix}"})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["cycle"]["status"] == "SUBMITTED_CONFIRMED"
    confirmation_replay = client.post(f"/api/authority-cases/{case_id}/submit/confirm", headers=_headers(), json={"submission_attempt_id": attempt_id, "confirmation_source": "MANUAL_CONFIRMED"})
    assert confirmation_replay.status_code == 200
    assert confirmation_replay.json()["cycle"]["id"] == confirmed.json()["cycle"]["id"]
    assert client.post(f"/api/authority-cases/{case_id}/packages/{package_id}/items", headers=_headers(), json={"item_type": "OTHER"}).status_code == 409
    finding = client.post(f"/api/authority-cases/{case_id}/findings", headers=_headers(), json={"submission_cycle_id": confirmed.json()["cycle"]["id"], "category": "ENGINEERING", "title": "Synthetic authority comment", "raw_text": "Revise the drawing note.", "engineering_impact": "POTENTIAL"})
    assert finding.status_code == 200, finding.text
    response = client.post(f"/api/authority-cases/{case_id}/findings/{finding.json()['id']}/responses", headers=_headers(), json={"response_text": "Response prepared; external closure remains pending."})
    assert response.status_code == 200
    outcome = client.post(f"/api/authority-cases/{case_id}/outcomes", headers=_headers(), json={"submission_cycle_id": confirmed.json()["cycle"]["id"], "outcome_type": "APPROVED", "external_submission_snapshot_id": confirmed.json()["snapshot"]["id"]})
    assert outcome.status_code == 200, outcome.text
    assert outcome.json()["status"] == "VERIFIED"
    workspace = client.get(f"/api/authority-cases/{case_id}", headers=_headers())
    assert workspace.status_code == 200
    assert workspace.json()["state_separation"]["external"] == "SUBMITTED_CONFIRMED"
