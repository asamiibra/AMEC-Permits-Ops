"""Latest owner model: separate registers and controlled Permit transition."""

from pathlib import Path

from backend.app.db import SessionLocal
from backend.app.fixtures.canonical import canonical_sor_root
from backend.app.models import Contract, PermitApplication, Project, ProjectArtifactRecord, SynologyProjectBootstrap
from backend.app.services.proposals_sor import EXPECTED_PROJECT_FOLDERS


def test_register_views_are_separate_and_share_the_six_kpis(client):
    proposals = client.get("/api/proposals-main?persona=SYSTEM_ADMIN&view=proposals")
    contracts = client.get("/api/proposals-main?persona=SYSTEM_ADMIN&view=contracts")
    assert proposals.status_code == contracts.status_code == 200
    proposal_body, contract_body = proposals.json(), contracts.json()
    assert proposal_body["view"] == "proposals"
    assert contract_body["view"] == "contracts"
    assert set(proposal_body["kpis"]) == set(contract_body["kpis"])
    assert proposal_body["rows"] == proposal_body["proposals"]
    assert contract_body["rows"] == contract_body["contracts"]
    assert {"related_contract_id", "contract_action_eligible"} <= set(proposal_body["rows"][0])
    assert {"related_proposal_id", "contract_reference", "permit_action_eligible"} <= set(contract_body["rows"][0])


def test_permit_transition_requires_manual_source_and_preserves_same_project_lineage(client):
    generated_root = None
    generated_bootstrap = None
    with SessionLocal() as db:
        contract = db.query(Contract).order_by(Contract.contract_reference).first()
        project = db.get(Project, contract.project_id)
        application = db.query(PermitApplication).filter(PermitApplication.controlling_contract_id == contract.id).first()
        assert contract and project and application
        project_id, reference, contract_id = project.id, project.project_number, contract.id
        bootstrap = db.query(SynologyProjectBootstrap).filter(SynologyProjectBootstrap.project_id == project_id).first()
        if not bootstrap:
            root_path = f"2026/TEST-{contract_id}"
            generated_root = canonical_sor_root() / root_path
            for folder in EXPECTED_PROJECT_FOLDERS:
                (generated_root / folder).mkdir(parents=True, exist_ok=True)
            bootstrap = SynologyProjectBootstrap(project_id=project_id, root_path=root_path, subfolders_json=EXPECTED_PROJECT_FOLDERS, template_applied=True, template_manifest_json=[], status="CREATED")
            db.add(bootstrap)
            generated_bootstrap = bootstrap
            db.commit()

    missing_file = client.post("/api/proposals-main/intake", data={"action": "PERMIT_INITIATION", "project_id": project_id, "contract_id": contract_id, "actor_role": "SYSTEM_ADMIN"})
    assert missing_file.status_code == 422
    filename = "owner-model-permit-initiation.txt"
    response = client.post("/api/proposals-main/intake", data={"action": "PERMIT_INITIATION", "project_id": project_id, "project_reference": reference, "contract_id": contract_id, "actor": "owner@amec.synthetic", "actor_role": "SYSTEM_ADMIN", "idempotency_key": "owner-model-permit-initiation-v1"}, files={"file": (filename, b"controlled permit initiation source", "text/plain")})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["semantic_class"] == "PERMIT_SOURCE"
    assert body["verification_state"] == "READ_BACK_VERIFIED"
    with SessionLocal() as db:
        record = db.query(ProjectArtifactRecord).filter(ProjectArtifactRecord.id == body["id"]).one()
        linked = db.get(PermitApplication, body["workflow"]["permit_application_id"])
        assert record.project_id == project_id
        assert record.contract_id == contract_id
        assert linked.project_id == project_id
        assert linked.controlling_contract_id == contract_id
        sor_file = canonical_sor_root() / record.sor_path
        db.delete(record)
        db.commit()
    if sor_file.exists():
        sor_file.unlink()
    if generated_bootstrap:
        with SessionLocal() as db:
            db.delete(db.merge(generated_bootstrap))
            db.commit()
    if generated_root and generated_root.exists():
        for child in sorted(generated_root.glob("*"), reverse=True):
            if child.is_dir(): child.rmdir()
        generated_root.rmdir()
