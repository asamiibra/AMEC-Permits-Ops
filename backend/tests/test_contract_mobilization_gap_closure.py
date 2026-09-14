from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select

from backend.app.db import SessionLocal
from backend.app.models import AuditEvent, Contract, ContractAdminEvidence, ContractClientInputRequirement, ContractRevision, NotificationEvent, Project, ProjectActivation, ServiceEngagement, WorkflowTask
from backend.app import worker
from backend.app.models.base import utcnow
from backend.tests.test_admin_contract_owner_session import ensure_contract_template, make_accepted_proposal, record_authority, record_checker


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
    record_authority(client, contract_id, actor="contract-authority")
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
    for role in ("EXISTING_DRAWINGS", "PROJECT_SKETCH", "TITLE_DEED", "OWNER_CLIENT_ID"):
        dossier = client.post(f"/api/admin/contracts/{contract_id}/documents", headers=headers("OWNER_SPONSOR", "dossier-owner"), json={"source_role": role, "source_filename": f"{role.lower()}.txt", "content": f"Synthetic {role} for {contract_id}", "reason": "Synthetic Design-entry dossier"})
        assert dossier.status_code == 200, dossier.text
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


def test_authority_review_snapshot_survives_acceptance_execution_and_cannot_be_downgraded(client):
    suffix = uuid4().hex[:8]
    ensure_contract_template(client)
    proposal_id, _ = make_accepted_proposal(client, f"Durable authority review {suffix}")
    created = client.post("/api/admin/contracts", headers=headers("OWNER_SPONSOR", "durable-maker"), json={"proposal_id": proposal_id})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]
    record_checker(client, contract_id, actor="durable-checker")
    approved = record_authority(client, contract_id, actor="durable-authority")
    revision_id = approved.json()["revision_id"]
    accepted = client.post(f"/api/admin/contracts/{contract_id}/accept", headers=headers("OWNER_SPONSOR", "durable-authority"), json={"idempotency_key": f"durable-accept:{suffix}"})
    assert accepted.status_code == 200, accepted.text
    repeat = client.post(f"/api/admin/contracts/{contract_id}/authority", headers=headers("OWNER_SPONSOR", "different-authority"), json={"decision": "APPROVE", "reason": "Repeat exact authority review"})
    assert repeat.status_code == 200 and repeat.json()["decision"] == "ALREADY_AUTHORITY_REVIEWED"
    assert repeat.json()["contract"]["current_revision"]["status"] == "FINALIZED"
    uploaded = client.post(f"/api/admin/contracts/{contract_id}/documents", headers=headers("OWNER_SPONSOR", "durable-authority"), json={"source_role": "EXECUTED_CONTRACT", "source_filename": f"durable-executed-{suffix}.txt", "content": "synthetic executed copy", "reason": "Record exact executed copy"})
    assert uploaded.status_code == 200, uploaded.text
    executed = client.post(f"/api/admin/contracts/{contract_id}/executed-evidence", headers=headers("OWNER_SPONSOR", "durable-authority"), json={"document_version_id": uploaded.json()["document_version_id"], "evidence_reference": f"synthetic://durable-executed/{suffix}", "reason": "Record exact executed evidence"})
    assert executed.status_code == 200, executed.text
    after_execution = client.post(f"/api/admin/contracts/{contract_id}/authority", headers=headers("OWNER_SPONSOR", "different-authority"), json={"decision": "APPROVE", "reason": "Repeat after execution"})
    assert after_execution.status_code == 200 and after_execution.json()["decision"] == "ALREADY_AUTHORITY_REVIEWED"
    assert after_execution.json()["contract"]["current_revision"]["status"] == "EXECUTED_EVIDENCE_RECORDED"
    returned = client.post(f"/api/admin/contracts/{contract_id}/authority", headers=headers("OWNER_SPONSOR", "different-authority"), json={"decision": "RETURN", "reason": "Attempt forbidden downgrade"})
    assert returned.status_code == 409, returned.text
    assert returned.json()["detail"]["code"] == "CONTRACT_AUTHORITY_REVIEW_IMMUTABLE"
    with SessionLocal() as db:
        revision = db.get(ContractRevision, revision_id)
        assert revision and revision.status == "EXECUTED_EVIDENCE_RECORDED"
        from backend.app.services.contract_workspace import contract_revision_is_authority_reviewed
        assert contract_revision_is_authority_reviewed(revision) is True


def test_start_prerequisite_facts_are_independent_and_pure_permit_is_not_design(client):
    suffix = uuid4().hex[:8]
    ensure_contract_template(client)
    proposal_id, _ = make_accepted_proposal(client, f"Independent prerequisite facts {suffix}")
    created = client.post("/api/admin/contracts", headers=headers("OWNER_SPONSOR", "facts-maker"), json={"proposal_id": proposal_id})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]

    facts = client.get(f"/api/admin/contracts/{contract_id}/start-prerequisites", headers=headers("OWNER_SPONSOR"))
    assert facts.status_code == 200, facts.text
    fact_map = {item["fact"]: item for item in facts.json()["facts"]}
    assert {"CONTRACT_EXECUTED", "CLIENT_COPY_DISTRIBUTED", "OPERATIONS_HANDOFF", "ADVANCE_PAYMENT_RECEIVED", "ADVANCE_PAYMENT_VERIFIED", "ADVANCE_PAYMENT_ALLOCATED", "CLIENT_ARCHITECTURE_APPROVED", "CONTRACT_DURATION_START", "PROJECT_ACTIVATION", "MUNICIPALITY_WORK_START"} <= set(fact_map)
    assert fact_map["CLIENT_ARCHITECTURE_APPROVED"]["state"] == "NOT_APPLICABLE"
    assert fact_map["MUNICIPALITY_WORK_START"]["state"] == "NOT_APPLICABLE"

    from backend.app.services.contract_workspace import design_start_readiness
    with SessionLocal() as db:
        contract = db.get(Contract, contract_id)
        assert contract
        assert design_start_readiness(db, contract, "PERMIT")["result"] == "NOT_APPLICABLE"


def test_timing_facts_require_exact_timing_clause_and_typed_action(client):
    suffix = uuid4().hex[:8]
    ensure_contract_template(client)
    proposal_id, _ = make_accepted_proposal(client, f"Typed timing facts {suffix}")
    created = client.post("/api/admin/contracts", headers=headers("OWNER_SPONSOR", "timing-maker"), json={"proposal_id": proposal_id})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]
    generic = client.post(f"/api/admin/contracts/{contract_id}/evidence", headers=headers("OWNER_SPONSOR", "timing-owner"), json={"evidence_type": "CLIENT_ARCHITECTURE_APPROVED", "source_role": "CLIENT_ARCHITECTURE_APPROVED", "source_reference": "synthetic://generic"})
    assert generic.status_code == 409 and generic.json()["detail"]["code"] == "USE_TYPED_TIMING_FACT_ACTION"
    no_requirement = client.get(f"/api/admin/contracts/{contract_id}/start-prerequisites", headers=headers("OWNER_SPONSOR"))
    facts = {item["fact"]: item for item in no_requirement.json()["facts"]}
    assert facts["CLIENT_ARCHITECTURE_APPROVED"]["state"] == "NOT_APPLICABLE"
    assert facts["MUNICIPALITY_WORK_START"]["state"] == "NOT_APPLICABLE"
    uploaded = client.post(f"/api/admin/contracts/{contract_id}/documents", headers=headers("OWNER_SPONSOR", "timing-owner"), json={"source_role": "ARCHITECTURE", "source_filename": f"architecture-clause-{suffix}.txt", "content": "Clause: client architecture approval is required before contract duration start.", "reason": "Upload exact timing clause"})
    assert uploaded.status_code == 200, uploaded.text
    source_id = uploaded.json()["document_version_id"]
    invalid_gate = client.post(f"/api/admin/contracts/{contract_id}/timing-requirements", headers=headers("OWNER_SPONSOR", "timing-owner"), json={"fact": "CLIENT_ARCHITECTURE_APPROVED", "applicable": True, "required_for": ["DESIGN_START"], "source_clause": "CLAUSE-ARCH-1", "source_document_version_id": source_id, "policy_version": "TIMING_POLICY_V1", "reason": "Record clause applicability"})
    assert invalid_gate.status_code == 422 and invalid_gate.json()["detail"]["code"] == "ARCHITECTURE_CANNOT_GATE_DESIGN_START"
    requirement = client.post(f"/api/admin/contracts/{contract_id}/timing-requirements", headers=headers("OWNER_SPONSOR", "timing-owner"), json={"fact": "CLIENT_ARCHITECTURE_APPROVED", "applicable": True, "required_for": ["CONTRACT_DURATION_START"], "source_clause": "CLAUSE-ARCH-1", "source_document_version_id": source_id, "policy_version": "TIMING_POLICY_V1", "reason": "Record exact clause applicability"})
    assert requirement.status_code == 200, requirement.text
    record_checker(client, contract_id, actor="timing-checker")
    record_authority(client, contract_id, actor="timing-authority")
    accepted = client.post(f"/api/admin/contracts/{contract_id}/accept", headers=headers("OWNER_SPONSOR", "timing-authority"), json={"idempotency_key": f"timing-accept:{suffix}"})
    assert accepted.status_code == 200, accepted.text
    executed_upload = client.post(f"/api/admin/contracts/{contract_id}/documents", headers=headers("OWNER_SPONSOR", "timing-authority"), json={"source_role": "EXECUTED_CONTRACT", "source_filename": f"executed-timing-{suffix}.txt", "content": "Synthetic executed timing contract", "reason": "Record executed timing contract"})
    assert executed_upload.status_code == 200, executed_upload.text
    executed = client.post(f"/api/admin/contracts/{contract_id}/executed-evidence", headers=headers("OWNER_SPONSOR", "timing-authority"), json={"document_version_id": executed_upload.json()["document_version_id"], "evidence_reference": f"synthetic://executed-timing/{suffix}", "reason": "Pin executed timing contract"})
    assert executed.status_code == 200, executed.text
    requirement_after_finalize = client.post(f"/api/admin/contracts/{contract_id}/timing-requirements", headers=headers("OWNER_SPONSOR", "timing-owner"), json={"fact": "CLIENT_ARCHITECTURE_APPROVED", "applicable": True, "required_for": ["CONTRACT_DURATION_START"], "source_clause": "CLAUSE-ARCH-1", "source_document_version_id": source_id, "policy_version": "TIMING_POLICY_V1", "reason": "Attempt to mutate finalized requirement"})
    assert requirement_after_finalize.status_code == 409 and requirement_after_finalize.json()["detail"]["code"] == "CONTRACT_FINALIZED_REVISION_IMMUTABLE"
    wrong = client.post(f"/api/admin/contracts/{contract_id}/timing-facts/CLIENT_ARCHITECTURE_APPROVED", headers=headers("OWNER_SPONSOR", "timing-owner"), json={"contract_revision_id": created.json()["current_revision"]["id"], "effective_date": "2026-09-14", "trigger_type": "CLIENT_APPROVAL", "source_clause": "WRONG-CLAUSE", "source_reference": "synthetic://architecture-approval", "source_document_version_id": source_id, "approval_evidence": "Owner recorded exact approval", "policy_version": "TIMING_POLICY_V1", "reason": "Record architecture approval"})
    assert wrong.status_code == 409 and wrong.json()["detail"]["code"] == "TIMING_FACT_AUTHORITY_MISMATCH"
    recorded = client.post(f"/api/admin/contracts/{contract_id}/timing-facts/CLIENT_ARCHITECTURE_APPROVED", headers=headers("OWNER_SPONSOR", "timing-owner"), json={"contract_revision_id": created.json()["current_revision"]["id"], "effective_date": "2026-09-14", "trigger_type": "CLIENT_APPROVAL", "source_clause": "CLAUSE-ARCH-1", "source_reference": "synthetic://architecture-approval", "source_document_version_id": source_id, "approval_evidence": "Owner recorded exact approval", "policy_version": "TIMING_POLICY_V1", "reason": "Record architecture approval"})
    assert recorded.status_code == 200, recorded.text
    evaluated = client.get(f"/api/admin/contracts/{contract_id}/start-prerequisites", headers=headers("OWNER_SPONSOR"))
    fact = {item["fact"]: item for item in evaluated.json()["facts"]}["CLIENT_ARCHITECTURE_APPROVED"]
    assert fact["state"] == "RECORDED" and fact["required_for"] == ["CONTRACT_DURATION_START"]
    assert "CLIENT_ARCHITECTURE_APPROVAL_REQUIRED" not in evaluated.json()["blockers_by_transition"]["DESIGN_START"]


def test_exception_stage_transition_is_idempotent(client):
    suffix = uuid4().hex[:8]
    ensure_contract_template(client)
    proposal_id, _ = make_accepted_proposal(client, f"Exception transition {suffix}")
    created = client.post("/api/admin/contracts", headers=headers("OWNER_SPONSOR", "exception-maker"), json={"proposal_id": proposal_id})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]
    changed = client.post(f"/api/admin/contracts/{contract_id}/stage", headers=headers("OWNER_SPONSOR", "exception-owner"), json={"stage": "NEEDS_ACTION", "reason": "Synthetic meaningful stage transition"})
    assert changed.status_code == 200, changed.text
    with SessionLocal() as db:
        automatic_transition_tasks = [item for item in db.query(WorkflowTask).filter(WorkflowTask.context_type == "CONTRACT", WorkflowTask.context_id == contract_id, WorkflowTask.task_type == "CONTRACT_EXCEPTION_REVIEW").all() if str((item.evidence_summary or {}).get("condition_key", "")).startswith("STAGE_TRANSITION:")]
        assert len(automatic_transition_tasks) == 1
    assert changed.json()["proactive_exceptions"]["created"]
    first = client.post(f"/api/admin/contracts/{contract_id}/evaluate-exceptions", headers=headers("OWNER_SPONSOR", "exception-owner"))
    second = client.post(f"/api/admin/contracts/{contract_id}/evaluate-exceptions", headers=headers("OWNER_SPONSOR", "exception-owner"))
    assert first.status_code == 200, first.text
    assert second.status_code == 200, second.text
    with SessionLocal() as db:
        tasks = db.query(WorkflowTask).filter(WorkflowTask.context_type == "CONTRACT", WorkflowTask.context_id == contract_id, WorkflowTask.task_type == "CONTRACT_EXCEPTION_REVIEW").all()
        transition_tasks = [item for item in tasks if str((item.evidence_summary or {}).get("condition_key", "")).startswith("STAGE_TRANSITION:")]
        notifications = db.query(NotificationEvent).filter(NotificationEvent.contract_id == contract_id, NotificationEvent.event_type == "CONTRACT_EXCEPTION_REVIEW_REQUIRED").all()
        assert len(transition_tasks) == 1
        assert len(notifications) == len(tasks)
        first_transition_id = transition_tasks[0].id
    later = client.post(f"/api/admin/contracts/{contract_id}/stage", headers=headers("OWNER_SPONSOR", "exception-owner"), json={"stage": "AUTHORITY_REVIEW", "reason": "Synthetic later Contract stage transition"})
    assert later.status_code == 200, later.text
    evaluated = client.post(f"/api/admin/contracts/{contract_id}/evaluate-exceptions", headers=headers("OWNER_SPONSOR", "exception-owner"))
    assert evaluated.status_code == 200, evaluated.text
    with SessionLocal() as db:
        transition_tasks = [item for item in db.query(WorkflowTask).filter(WorkflowTask.context_type == "CONTRACT", WorkflowTask.context_id == contract_id, WorkflowTask.task_type == "CONTRACT_EXCEPTION_REVIEW").all() if str((item.evidence_summary or {}).get("condition_key", "")).startswith("STAGE_TRANSITION:")]
        assert len(transition_tasks) == 2
    completed = client.post(f"/api/tasks/{first_transition_id}/complete", headers=headers("OWNER_SPONSOR"))
    assert completed.status_code == 200, completed.text
    repeat_after_completion = client.post(f"/api/admin/contracts/{contract_id}/evaluate-exceptions", headers=headers("OWNER_SPONSOR", "exception-owner"))
    assert repeat_after_completion.status_code == 200, repeat_after_completion.text
    with SessionLocal() as db:
        transition_tasks = [item for item in db.query(WorkflowTask).filter(WorkflowTask.context_type == "CONTRACT", WorkflowTask.context_id == contract_id, WorkflowTask.task_type == "CONTRACT_EXCEPTION_REVIEW").all() if str((item.evidence_summary or {}).get("condition_key", "")).startswith("STAGE_TRANSITION:")]
        assert len(transition_tasks) == 2
        assert any(item.id == first_transition_id and str(item.status).upper() == "COMPLETED" for item in transition_tasks)


def test_canonical_worker_discovers_aged_contract_input_exception(client):
    suffix = uuid4().hex[:8]
    ensure_contract_template(client)
    proposal_id, _ = make_accepted_proposal(client, f"Worker time reconciliation {suffix}")
    created = client.post("/api/admin/contracts", headers=headers("OWNER_SPONSOR", "worker-maker"), json={"proposal_id": proposal_id})
    assert created.status_code == 200, created.text
    contract_id = created.json()["id"]
    revision_id = created.json()["current_revision"]["id"]
    input_response = client.post(
        f"/api/admin/contracts/{contract_id}/client-inputs",
        headers=headers("OWNER_SPONSOR", "worker-owner"),
        json={"sequence": 1, "title": "Synthetic aged client document", "source_type": "CLIENT_DOCUMENT"},
    )
    assert input_response.status_code == 200, input_response.text

    with SessionLocal() as db:
        requirement = db.scalar(
            select(ContractClientInputRequirement).where(
                ContractClientInputRequirement.contract_id == contract_id,
                ContractClientInputRequirement.contract_revision_id == revision_id,
            )
        )
        assert requirement
        requirement.created_at = utcnow() - timedelta(days=8)
        db.commit()

    reconciled = worker.reconcile_contract_exceptions_once(
        worker_id="synthetic-time-worker",
        limit=50,
    )
    assert reconciled[0] >= 1
    assert reconciled[1] == 0
    assert reconciled[2] >= 1

    repeated = worker.reconcile_contract_exceptions_once(
        worker_id="synthetic-time-worker",
        limit=50,
    )
    assert repeated[0] >= 1
    assert repeated[1] == 0
    assert repeated[2] == 0

    with SessionLocal() as db:
        tasks = db.scalars(
            select(WorkflowTask).where(
                WorkflowTask.context_type == "CONTRACT",
                WorkflowTask.context_id == contract_id,
                WorkflowTask.task_type == "CONTRACT_EXCEPTION_REVIEW",
            )
        ).all()
        aged = [
            item for item in tasks
            if (item.evidence_summary or {}).get("condition_key")
            == "INPUTS:AGED_REQUIRED_DOCUMENTS"
        ]
        assert len(aged) == 1
