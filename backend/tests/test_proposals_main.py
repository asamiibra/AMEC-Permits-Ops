"""Owner-directed Proposals & Contracts main-page contract coverage."""

from pathlib import Path
from fastapi.testclient import TestClient

from backend.app.db import SessionLocal
from backend.app.models import ConsultancyOffice, Contract, Document, DocumentVersion, EvidenceArtifact, LineageEdge, Opportunity, PermitApplication, Project, ProjectArtifactRecord, ProposalIntakeArtifact, Quotation
from backend.app.api import proposals_main_routers
from backend.app.main import app
from backend.app.fixtures.canonical import canonical_sor_root


def _project():
    with SessionLocal() as db:
        project = db.query(Project).order_by(Project.project_number).first()
        return project.id, project.project_number


def test_main_page_kpis_are_derived_and_manual_intake_is_verified(client):
    project_id, project_reference = _project()
    main = client.get("/api/proposals-main?persona=SYSTEM_ADMIN")
    assert main.status_code == 200
    payload = main.json()
    assert {"OPEN_PROPOSALS", "OPEN_CONTRACTS", "PROPOSAL_HANDOVER", "CONTRACT_HANDOVER", "PROPOSALS_IN_PROCESS", "CONTRACTS_IN_PROCESS"} <= set(payload["kpis"])
    assert payload["kpis"]["OPEN_PROPOSALS"]["count"] == sum(1 for row in payload["rows"] if row["proposal_status"] in payload["kpis"]["OPEN_PROPOSALS"]["states"])
    assert payload["persona"]["amount_visible"] is True

    filename = "proposal-main-contract-test.txt"
    sor_file = canonical_sor_root() / "2026/GHCE-2026-0142_Al-Noor-Villa/01_Client" / filename
    form = {"action": "CLIENT_LIST", "project_id": project_id, "project_reference": project_reference, "actor": "owner@amec.synthetic", "actor_role": "SYSTEM_ADMIN", "idempotency_key": "proposal-main-contract-test-v1"}
    try:
        first = client.post("/api/proposals-main/intake", data=form, files={"file": (filename, b"client list source", "text/plain")})
        assert first.status_code == 200
        body = first.json()
        assert body["semantic_class"] == "CLIENT_SOURCE"
        assert body["verification_state"] == "READ_BACK_VERIFIED"
        assert body["folder_template_version"] == "SYN-AMEC-PROJECT-FOLDERS-1.0"
        retry = client.post("/api/proposals-main/intake", data=form, files={"file": (filename, b"client list source", "text/plain")})
        assert retry.status_code == 200
        assert retry.json()["reused"] is True
        version = client.post("/api/proposals-main/intake", data={**form, "idempotency_key": "proposal-main-contract-test-v2"}, files={"file": (filename, b"client list revised source", "text/plain")})
        assert version.status_code == 200
        assert version.json()["version"] == 2
        assert version.json()["supersedes_record_id"] == body["id"]
        mismatch = client.post("/api/proposals-main/intake", data={**form, "project_reference": "GHCE-2026-9999", "idempotency_key": "proposal-main-contract-test-mismatch"}, files={"file": (filename, b"wrong project", "text/plain")})
        assert mismatch.status_code == 409
        unavailable = client.post("/api/proposals-main/intake", headers={"X-Synthetic-SOR": "UNAVAILABLE"}, data={**form, "idempotency_key": "proposal-main-contract-test-unavailable"}, files={"file": (filename, b"unavailable", "text/plain")})
        assert unavailable.status_code == 503
    finally:
        for candidate in sor_file.parent.glob("proposal-main-contract-test*"):
            candidate.unlink()
        with SessionLocal() as db:
            records = db.query(ProjectArtifactRecord).filter(ProjectArtifactRecord.source_filename == filename).all()
            version_ids = [item.document_version_id for item in records if item.document_version_id]
            evidence_ids = [item.evidence_artifact_id for item in records if item.evidence_artifact_id]
            record_ids = [item.id for item in records]
            db.query(LineageEdge).filter((LineageEdge.upstream_id.in_(record_ids)) | (LineageEdge.downstream_id.in_(version_ids + evidence_ids))).delete(synchronize_session=False)
            for item in records:
                db.delete(item)
            db.flush()
            for version_id in version_ids:
                version = db.get(DocumentVersion, version_id)
                if version:
                    document = db.get(Document, version.document_id)
                    db.delete(version)
                    if document:
                        db.delete(document)
            for evidence_id in evidence_ids:
                evidence = db.get(EvidenceArtifact, evidence_id)
                if evidence:
                    db.delete(evidence)
            db.commit()


def test_main_page_response_declares_complete_typed_contract(client):
    response = client.get("/api/proposals-main?persona=SYSTEM_ADMIN&view=proposals")
    assert response.status_code == 200
    payload = response.json()
    assert payload["view"] == "proposals"
    assert payload["rows"] == payload["proposals"]
    assert set(payload["kpis"]) == {"OPEN_PROPOSALS", "OPEN_CONTRACTS", "PROPOSAL_HANDOVER", "CONTRACT_HANDOVER", "PROPOSALS_IN_PROCESS", "CONTRACTS_IN_PROCESS"}
    for key, kpi in payload["kpis"].items():
        assert isinstance(kpi["label"], str)
        assert isinstance(kpi["count"], int) and kpi["count"] >= 0
        assert isinstance(kpi["states"], list)
        assert kpi["entity"] in {"proposal", "contract"}
    openapi = client.get("/openapi.json").json()
    schema = openapi["paths"]["/api/proposals-main"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("/ProposalMainResponse")


def test_incomplete_main_projection_is_a_controlled_server_error(client, monkeypatch):
    monkeypatch.setattr(proposals_main_routers, "_rows", lambda _db: [{"record_type": "PROPOSAL_WORKSPACE"}])
    with TestClient(app, raise_server_exceptions=False) as safe_client:
        response = safe_client.get("/api/proposals-main?persona=SYSTEM_ADMIN&view=proposals")
    assert response.status_code == 500
    assert response.json()["detail"] == "Internal server error"


def test_persona_action_boundaries_are_explicit(client):
    owner = client.get("/api/proposals-main?persona=SYSTEM_ADMIN").json()["persona"]
    bd = client.get("/api/proposals-main?persona=COMMERCIAL_APPROVER").json()["persona"]
    engineering = client.get("/api/proposals-main?persona=RESPONSIBLE_ENGINEER").json()["persona"]
    assert owner["allowed_actions"] == ["CLIENT_LIST", "PROPOSAL_FORM", "CONTRACT_FORM", "NEW_PROPOSAL", "PERMIT_INITIATION"]
    assert bd["allowed_actions"] == ["CLIENT_LIST", "CONTRACT_FORM", "NEW_PROPOSAL", "PERMIT_INITIATION"]
    assert engineering["allowed_actions"] == ["PROPOSAL_FORM"]
    assert engineering["amount_visible"] is False


def test_provisional_sources_promote_to_canonical_sor_idempotently(client):
    project_id, project_reference = _project()
    second_project_id = None
    with SessionLocal() as db:
        second_project_id = db.query(Project).order_by(Project.project_number).offset(1).first().id

    source_root = canonical_sor_root() / "proposal-intake"
    first = client.post("/api/proposals-main/intake", data={"action": "TENDER_DOCUMENT", "proposal_description": "G11 promotion proof", "actor": "owner@amec.synthetic", "actor_role": "SYSTEM_ADMIN", "idempotency_key": "g11-promotion-tender-v1"}, files={"file": ("g11-promotion.txt", b"tender evidence", "text/plain")})
    assert first.status_code == 200
    opportunity_id = first.json()["opportunity_id"]
    second = client.post("/api/proposals-main/intake", data={"action": "PROPOSAL_FORM", "opportunity_id": opportunity_id, "proposal_description": "G11 promotion proof", "actor": "engineering@amec.synthetic", "actor_role": "RESPONSIBLE_ENGINEER", "idempotency_key": "g11-promotion-form-v1"}, files={"file": ("g11-proposal-form.txt", b"proposal form evidence", "text/plain")})
    assert second.status_code == 200

    promoted = client.post(f"/api/proposals-main/proposals/{opportunity_id}/promote/{project_id}", data={"actor": "owner@amec.synthetic"})
    assert promoted.status_code == 200
    payload = promoted.json()
    assert payload["promotion_state"] == "CANONICAL_VERIFIED"
    assert payload["policy"] == "COPY_VERIFY_AND_ARCHIVE_SOURCE"
    assert payload["cross_project_artifact_writes"] == 0
    assert {item["content_hash"] for item in payload["promoted"]} == {
        first.json()["content_hash"],
        second.json()["content_hash"],
    }

    retry = client.post(f"/api/proposals-main/proposals/{opportunity_id}/promote/{project_id}", data={"actor": "owner@amec.synthetic"})
    assert retry.status_code == 200
    assert all(item["reused"] is True for item in retry.json()["promoted"])
    with SessionLocal() as db:
        source_rows = db.query(ProposalIntakeArtifact).filter(ProposalIntakeArtifact.opportunity_id == opportunity_id).all()
        canonical_rows = db.query(ProjectArtifactRecord).filter(ProjectArtifactRecord.opportunity_id == opportunity_id, ProjectArtifactRecord.project_id == project_id).all()
        promotion_edges = db.query(LineageEdge).filter(LineageEdge.upstream_type == "ProposalIntakeArtifact", LineageEdge.dependency_kind == "PROVISIONAL_TO_CANONICAL_SOR_PROMOTION").all()
        assert len(source_rows) == 2
        assert all(row.status == "HISTORICAL" and row.metadata_json["promotion_state"] == "CANONICAL_VERIFIED" for row in source_rows)
        assert len(canonical_rows) == 2
        assert len([edge for edge in promotion_edges if edge.upstream_id in {row.id for row in source_rows}]) == 2
        assert all(row.project_id == project_id for row in canonical_rows)
        assert all((canonical_sor_root() / row.sor_path).read_bytes() for row in canonical_rows)

    cross_project = client.post(f"/api/proposals-main/proposals/{opportunity_id}/promote/{second_project_id}", data={"actor": "owner@amec.synthetic"})
    assert cross_project.status_code == 409
    assert cross_project.json()["detail"] == "CROSS_PROJECT_PROMOTION_BLOCKED"
    import shutil
    for path in source_root.glob("AMEC-SYN-OPP-*"):
        if path.is_dir() and any(candidate.name.startswith("g11-") for candidate in path.rglob("*")):
            shutil.rmtree(path)
    for filename in ("g11-promotion.txt", "g11-proposal-form.txt"):
        candidate = canonical_sor_root() / "2026/GHCE-2026-0142_Al-Noor-Villa/03_Design" / filename
        if candidate.exists():
            candidate.unlink()


def test_canonical_backend_contracts_kpis_detail_and_server_rbac(client):
    with SessionLocal() as db:
        opportunity = db.query(Opportunity).filter(Opportunity.opportunity_reference == "SYN-OPP-0001").one()
        contract = db.query(Contract).filter(Contract.contract_reference == "SYN-CTR-0001").one()
        projects = db.query(Project).order_by(Project.project_number).all()
        application = db.query(PermitApplication).order_by(PermitApplication.external_request_number).first()

    summary = client.get("/api/proposals-contracts/summary")
    assert summary.status_code == 200
    summary_payload = summary.json()
    proposal_list = client.get("/api/proposals-contracts/proposals?filter=open").json()
    contract_list = client.get("/api/proposals-contracts/contracts?filter=open").json()
    assert summary_payload["open_proposals"] == len(proposal_list["items"])
    assert summary_payload["open_contracts"] == len(contract_list["items"])

    proposal_detail = client.get(f"/api/proposals/{opportunity.id}")
    preparation = client.get(f"/api/proposals/{opportunity.id}/preparation", headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER"})
    contract_detail = client.get(f"/api/contracts/{contract.id}")
    permit_detail = client.get(f"/api/permits/{application.id}")
    assert proposal_detail.status_code == preparation.status_code == contract_detail.status_code == permit_detail.status_code == 200
    assert proposal_detail.json()["entity_type"] == "Proposal"
    assert contract_detail.json()["related_proposal_id"] == opportunity.id
    assert permit_detail.json()["controlling_contract_id"] == contract.id

    bd = {"X-Dev-Role": "PROCESS_CHAMPION"}
    engineering = {"X-Dev-Role": "RESPONSIBLE_ENGINEER"}
    assert client.post(f"/api/proposals/{opportunity.id}/contract?project_id={projects[1].id}", headers=bd).status_code == 409
    assert client.post(f"/api/proposals/{opportunity.id}/contract", headers=engineering).status_code == 403
    assert client.post(f"/api/contracts/{contract.id}/permit?project_id={projects[1].id}", headers=bd).status_code == 409
    assert client.post("/api/proposals-main/intake", headers=engineering, data={"action": "CLIENT_LIST", "project_id": projects[0].id}, files={"file": ("rbac.txt", b"x", "text/plain")}).status_code == 403


def test_contract_permit_handoff_starts_downstream_permit_when_project_is_canonical(client):
    with SessionLocal() as db:
        contract = db.query(Contract).order_by(Contract.contract_reference).first()
        quotation = db.get(Quotation, contract.quotation_id) if contract else None
        opportunity = db.get(Opportunity, quotation.opportunity_id) if quotation else None
        projects = db.query(Project).order_by(Project.project_number).all()
        target = next((item for item in projects if not db.query(PermitApplication).filter(PermitApplication.project_id == item.id).first()), None)
        if target is None:
            office = db.query(ConsultancyOffice).first()
            target = Project(project_number="GHCE-2026-999", project_name="Synthetic Contract Permit Handoff", office_id=office.id, workstream="QEC-DOHA / BUILDING_PERMIT", status="ACTIVE", municipality="Demo Municipality A", permit_type="Building Permit")
            db.add(target)
            db.flush()
        assert contract and opportunity and target
        opportunity.project_id = target.id
        contract.project_id = target.id
        db.commit()
        contract_id = contract.id
        project_id = target.id
    response = client.post(f"/api/contracts/{contract_id}/permit?project_id={project_id}", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert response.status_code == 200, response.text
    assert response.json()["project_id"] == project_id
    with SessionLocal() as db:
        assert db.query(PermitApplication).filter(PermitApplication.project_id == project_id, PermitApplication.controlling_contract_id == contract_id).count() == 1


def test_primary_demo_source_provenance_lifecycle_and_lineage_reconcile(client):
    with SessionLocal() as db:
        opportunity = db.query(Opportunity).filter(Opportunity.opportunity_reference == "SYN-OPP-0001").one()
        contract = db.query(Contract).filter(Contract.contract_reference == "SYN-CTR-0001").one()

    register = client.get("/api/proposals-main?persona=SYSTEM_ADMIN")
    assert register.status_code == 200
    row = next(item for item in register.json()["rows"] if item["id"] == opportunity.id)
    assert row["source_count"] == 3
    assert row["current_stage"] != "Contract form"
    assert row["next_action"]["code"] == "VIEW_CONTRACT"
    assert row["related_contract_id"] == contract.id

    detail = client.get(f"/api/proposals/{opportunity.id}")
    assert detail.status_code == 200
    body = detail.json()
    assert len(body["sources"]) == row["source_count"]
    assert all(source["verification_status"] == "READ_BACK_VERIFIED" for source in body["sources"])
    assert all(source["sor_binding"] == "CANONICAL_PROJECT_SOR" for source in body["sources"])
    assert body["related_contracts"][0]["related_proposal_id"] == opportunity.id

    contract_detail = client.get(f"/api/contracts/{contract.id}")
    assert contract_detail.status_code == 200
    contract_body = contract_detail.json()
    assert contract_body["reference"] == "SYN-CTR-0001"
    assert contract_body["project"]["reference"] != contract_body["reference"]
    assert contract_body["related_proposal"]["id"] == opportunity.id
    assert contract_body["next_action"]["code"] == "OPEN_PERMIT"


def test_contextual_sources_do_not_create_orphan_proposal_and_missing_context_blocks(client):
    with SessionLocal() as db:
        project = db.query(Project).order_by(Project.project_number).offset(1).first()
        before = db.query(Opportunity).count()
    source = client.post(
        "/api/proposals-main/intake",
        data={"action": "CLIENT_LIST", "project_id": project.id, "project_reference": project.project_number, "actor": "owner@amec.synthetic", "actor_role": "SYSTEM_ADMIN", "idempotency_key": "client-list-contextual-v1"},
        files={"file": ("client-list-contextual.txt", b"SYNTHETIC CLIENT LIST", "text/plain")},
    )
    assert source.status_code == 200, source.text
    with SessionLocal() as db:
        assert db.query(Opportunity).count() == before
        record = db.query(ProjectArtifactRecord).filter(ProjectArtifactRecord.id == source.json()["id"]).one()
        assert record.opportunity_id is None
        db.delete(record)
        db.commit()
    no_proposal = client.post("/api/proposals-main/intake", data={"action": "PROPOSAL_FORM", "actor_role": "SYSTEM_ADMIN"}, files={"file": ("form.txt", b"form", "text/plain")})
    assert no_proposal.status_code == 409
    assert no_proposal.json()["detail"]["code"] == "CANONICAL_PROPOSAL_CONTEXT_REQUIRED"


def test_commercial_and_engineering_intake_actions_are_server_denied(client):
    engineering = {"X-Dev-Role": "RESPONSIBLE_ENGINEER"}
    bd = {"X-Dev-Role": "PROCESS_CHAMPION"}
    assert client.post("/api/proposals-main/intake", headers=engineering, data={"action": "NEW_PROPOSAL"}, files={"file": ("new.txt", b"x", "text/plain")}).status_code == 403
    assert client.post("/api/proposals-main/intake", headers=engineering, data={"action": "CONTRACT_FORM"}, files={"file": ("contract.txt", b"x", "text/plain")}).status_code == 403
    assert client.post("/api/proposals-main/intake", headers=bd, data={"action": "PROPOSAL_FORM"}, files={"file": ("proposal.txt", b"x", "text/plain")}).status_code == 403


def test_new_proposal_route_creation_is_source_verified_idempotent_and_reference_aware(client):
    project_id, project_reference = _project()
    bd = {"X-Dev-Role": "PROCESS_CHAMPION"}
    page = client.get("/api/proposals-main?persona=COMMERCIAL_APPROVER")
    client_id = page.json()["clients"][0]["id"]
    provisional_form = {
        "action": "TENDER_DOCUMENT",
        "proposal_description": "BD source-driven New Proposal audit proof",
        "client_account_id": client_id,
        "price": "QAR 125,000",
        "period": "30-day proposal validity",
        "sow": "Initial tender scope",
        "exclusions": "Authority fees",
        "create_new_proposal": "true",
        "actor": "bd@amec.synthetic",
        "actor_role": "COMMERCIAL_APPROVER",
        "idempotency_key": "new-proposal-route-audit-tender-v1",
    }
    first = client.post("/api/proposals-main/intake", headers=bd, data=provisional_form, files={"file": ("new-proposal-route-audit.txt", b"tender source evidence", "text/plain")})
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["reference_state"] == "PROVISIONAL"
    assert first_body["semantic_class"] == "TENDER_DOCUMENT_SOURCE"
    assert first_body["verification_state"] == "READ_BACK_VERIFIED"
    opportunity_id = first_body["opportunity_id"]
    with SessionLocal() as db:
        opportunity_count = db.query(Opportunity).count()
    retry = client.post("/api/proposals-main/intake", headers=bd, data=provisional_form, files={"file": ("new-proposal-route-audit.txt", b"tender source evidence", "text/plain")})
    assert retry.status_code == 200, retry.text
    assert retry.json()["reused"] is True
    assert retry.json()["opportunity_id"] == opportunity_id
    with SessionLocal() as db:
        assert db.query(Opportunity).count() == opportunity_count

    second = client.post("/api/proposals-main/intake", headers=bd, data={**provisional_form, "action": "CLIENT_INFORMATION", "opportunity_id": opportunity_id, "idempotency_key": "new-proposal-route-audit-client-v1"}, files={"file": ("new-proposal-client.txt", b"client information evidence", "text/plain")})
    assert second.status_code == 200, second.text
    assert second.json()["semantic_class"] == "CLIENT_SOURCE"
    detail = client.get(f"/api/proposals-main/proposals/{opportunity_id}")
    assert detail.status_code == 200
    assert detail.json()["proposal"]["source_count"] == 2
    assert all(source["verification_status"] == "READ_BACK_VERIFIED" for source in detail.json()["sources"])

    canonical = client.post("/api/proposals-main/intake", headers=bd, data={**provisional_form, "proposal_description": "Canonical New Proposal audit proof", "project_id": project_id, "project_reference": project_reference, "idempotency_key": "new-proposal-route-audit-canonical-v1"}, files={"file": ("new-proposal-canonical.txt", b"canonical tender evidence", "text/plain")})
    assert canonical.status_code == 200, canonical.text
    canonical_id = canonical.json()["opportunity_id"]
    with SessionLocal() as db:
        canonical_opportunity = db.get(Opportunity, canonical_id)
        assert canonical_opportunity.reference_state == "CANONICAL"
        assert canonical_opportunity.project_id == project_id

    mismatch = client.post("/api/proposals-main/intake", headers=bd, data={**provisional_form, "project_id": project_id, "project_reference": "AMEC-NOT-THE-PROJECT", "idempotency_key": "new-proposal-route-audit-mismatch-v1"}, files={"file": ("new-proposal-mismatch.txt", b"mismatch evidence", "text/plain")})
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["code"] == "PROJECT_REFERENCE_MISMATCH"
