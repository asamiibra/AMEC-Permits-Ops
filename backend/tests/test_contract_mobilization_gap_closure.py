from uuid import uuid4

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import AuditEvent, Contract, ContractAdminEvidence, ContractRevision, Project, ProjectActivation, ServiceEngagement
from backend.tests.test_admin_contract_owner_session import ensure_contract_template, make_accepted_proposal, record_checker


def headers(role: str, actor: str | None = None) -> dict[str, str]:
    value = {"X-Dev-Role": role}
    if actor:
        value["X-Dev-Actor"] = actor
    return value


def test_executed_evidence_service_gate_operations_and_persistence(client):
    suffix = uuid4().hex[:8]
    ensure_contract_template(client)
    proposal_id, _ = make_accepted_proposal(client, f"Contract Mobilization Gap Closure {suffix}")
    created = client.post("/api/admin/contracts", headers=headers("OWNER_SPONSOR", "contract-maker"), json={"proposal_id": proposal_id})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]
    revision_id = created.json()["current_revision"]["id"]
    record_checker(client, contract_id, actor="contract-checker")
    accepted = client.post(f"/api/admin/contracts/{contract_id}/accept", headers=headers("OWNER_SPONSOR", "contract-authority"), json={"idempotency_key": f"gap-accept:{suffix}"})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["contract"]["current_revision"]["accepted"] is True

    before_evidence = client.get(f"/api/admin/contracts/{contract_id}", headers=headers("OWNER_SPONSOR"))
    assert before_evidence.json()["executed_evidence"] == []
    uploaded = client.post(f"/api/admin/contracts/{contract_id}/documents", headers=headers("OWNER_SPONSOR", "contract-authority"), json={"source_role": "EXECUTED_CONTRACT", "source_filename": "executed-contract.txt", "content": f"Synthetic executed Contract {suffix}", "reason": "Synthetic executed-copy upload"})
    assert uploaded.status_code == 200, uploaded.text
    document_version_id = uploaded.json()["document_version_id"]
    evidence = client.post(f"/api/admin/contracts/{contract_id}/executed-evidence", headers=headers("OWNER_SPONSOR", "contract-authority"), json={"document_version_id": document_version_id, "evidence_reference": f"synthetic://executed-contract/{suffix}", "reason": "Synthetic human executed-evidence record"})
    assert evidence.status_code == 200, evidence.text
    assert evidence.json()["decision"] == "RECORDED"
    assert evidence.json()["evidence"]["contract_revision_id"] == revision_id
    assert evidence.json()["evidence"]["document_version_id"] == document_version_id
    assert evidence.json()["evidence"]["metadata"]["signature_policy"] == "HUMAN_CONTROLLED"
    assert evidence.json()["evidence"]["metadata"]["forms_completion"] == "NOT_INFERRED"
    repeat = client.post(f"/api/admin/contracts/{contract_id}/executed-evidence", headers=headers("OWNER_SPONSOR", "different-authority"), json={"document_version_id": document_version_id, "evidence_reference": f"synthetic://executed-contract/{suffix}"})
    assert repeat.status_code == 200
    assert repeat.json()["decision"] == "ALREADY_RECORDED"

    not_yet_activated = client.post("/api/handover/service-engagements", headers=headers("OWNER_SPONSOR", "service-owner"), json={"project_id": "not-activated", "contract_id": contract_id, "contract_revision_id": revision_id, "service_ref": f"DESIGN-{suffix}", "service_offering_code": "DESIGN", "description": "Should be rejected"})
    assert not_yet_activated.status_code == 404
    with SessionLocal() as db:
        contract = db.get(Contract, contract_id)
        assert contract and contract.current_revision_id == revision_id
        project = db.get(Project, contract.project_id) if contract.project_id else db.scalar(select(Project).order_by(Project.project_number))
        assert project
        contract.project_id = project.id
        db.commit()
        assert db.scalar(select(ServiceEngagement).where(ServiceEngagement.contract_id == contract_id)) is None
        assert db.scalar(select(ContractRevision).where(ContractRevision.id == revision_id)).status == "EXECUTED_EVIDENCE_RECORDED"
        assert db.scalar(select(ContractAdminEvidence).where(ContractAdminEvidence.contract_id == contract_id, ContractAdminEvidence.source_role == "EXECUTED_CONTRACT"))
        assert db.scalar(select(AuditEvent).where(AuditEvent.event_type == "ADMIN_CONTRACT_EXECUTED_EVIDENCE_RECORDED", AuditEvent.entity_id == contract_id))
        project_id = project.id

    blocked = client.post("/api/handover/service-engagements", headers=headers("OWNER_SPONSOR", "service-owner"), json={"project_id": project_id, "contract_id": contract_id, "contract_revision_id": revision_id, "service_ref": f"DESIGN-{suffix}", "service_offering_code": "DESIGN", "description": "Blocked before Project Activation"})
    assert blocked.status_code == 409
    assert blocked.json()["detail"]["code"] == "PROJECT_ACTIVATION_REQUIRED"
    unauthorized = client.post("/api/handover/service-engagements", headers=headers("COMMERCIAL_APPROVER", "unauthorized"), json={"project_id": project_id, "contract_id": contract_id, "contract_revision_id": revision_id, "service_ref": f"DESIGN-{suffix}", "service_offering_code": "DESIGN", "description": "Unauthorized"})
    assert unauthorized.status_code == 403

    activation = client.post(f"/api/admin/contracts/{contract_id}/activate-project", headers=headers("OWNER_SPONSOR", "project-owner"), json={"project_code": f"AMEC-2026-{int(suffix[:3], 16) % 900 + 100:03d}", "start_date": "2026-09-11", "idempotency_key": f"gap-activation:{suffix}"})
    assert activation.status_code == 200, activation.text
    activated_project_id = activation.json()["activation"]["project_id"]
    service_payload = {"project_id": activated_project_id, "contract_id": contract_id, "contract_revision_id": revision_id, "service_ref": f"DESIGN-{suffix}", "service_offering_code": "DESIGN", "description": "Synthetic gated Design service"}
    service = client.post("/api/handover/service-engagements", headers=headers("OWNER_SPONSOR", "service-owner"), json=service_payload)
    assert service.status_code == 200, service.text
    assert service.json()["service_engagement"]["contract_revision_id"] == revision_id
    duplicate = client.post("/api/handover/service-engagements", headers=headers("OWNER_SPONSOR", "service-owner"), json=service_payload)
    assert duplicate.status_code == 200
    assert duplicate.json()["idempotent"] is True
    with SessionLocal() as db:
        assert db.scalar(select(ServiceEngagement).where(ServiceEngagement.contract_id == contract_id, ServiceEngagement.service_ref == f"DESIGN-{suffix}"))
        assert db.scalar(select(ProjectActivation).where(ProjectActivation.contract_id == contract_id, ProjectActivation.project_id == activated_project_id))

    operations = client.get(f"/api/admin/contracts/{contract_id}/operations", headers=headers("OWNER_SPONSOR"))
    assert operations.status_code == 200, operations.text
    body = operations.json()
    assert body["source_of_record"] == "CANONICAL_CONTRACT_PROJECT_MOBILIZATION_READ_MODEL"
    assert body["mobilization"]["project_activation"] == "ACTIVE"
    assert body["mobilization"]["service_engagement_count"] == 1
    assert body["contract"]["current_revision_id"] == revision_id
    assert body["executed_evidence"][0]["document_version_id"] == document_version_id
    assert body["external_send"] == "HUMAN_CONTROLLED"
