"""Owner-facing Proposals & Contracts page APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..models import ApplicationStatus, AssistantHandoff, ClientAccount, ConsultancyOffice, Contract, ContractRevision, Finding, LineageEdge, NotificationEvent, Opportunity, PermitApplication, Project, ProjectArtifactRecord, ProposalIntakeArtifact, ProposalSourceEvidence, Quotation, QuotationRevision, ReferenceNumber, Role, WorkflowTask, WorkflowTaskStatus
from ..services.proposals_sor import ACTION_CONFIG, INTAKE_SEMANTIC_CONFIG, SEMANTIC_FOLDER_CONFIG, SOR_TEMPLATE_VERSION, canonicalize_project_reference, ingest_project_artifact, ingest_provisional_intake_artifact, promote_provisional_intake, resolve_project_target
from ..services.backend_realignment import (
    CAPABILITY_MATRIX,
    KPI_PREDICATES,
    contract_projection,
    domain_error,
    kpi_counts,
    matches_filter,
    persona_for_role,
    proposal_projection,
    require_capability,
    permit_projection,
    proposal_next_action,
    proposal_stage,
    proposal_sources,
)
from ..schemas.proposals_main import ProposalMainResponse

router = APIRouter(prefix="/api/proposals-main", tags=["proposals-main"])

KPI_LABELS = {
    "open_proposals": "Open Proposals",
    "open_contracts": "Open Contracts",
    "proposal_handover": "Proposal Handover",
    "contract_handover": "Contract Handover",
    "proposals_in_process": "Proposals In Process",
    "contracts_in_process": "Contracts In Process",
}

# Keep the legacy uppercase response keys for the existing page, but derive
# their entity/state predicates from the same canonical registry used by the
# summary and list endpoints.
KPI_DEFINITIONS = {
    key.upper(): {"label": KPI_LABELS[key], "entity": spec["entity"], "states": sorted(spec["states"])}
    for key, spec in KPI_PREDICATES.items()
}


def _role_name(role: Role | str) -> str:
    return role.value if isinstance(role, Role) else str(role)


def _actor_role(role: Role, supplied: str | None) -> str:
    return supplied or _role_name(role)


def _allowed(action: str, persona: str) -> bool:
    if persona in {"SYSTEM_ADMIN", "OWNER", "OWNER_SPONSOR"}:
        return True
    if persona in {"COMMERCIAL_APPROVER", "BD_USER", "BUSINESS_DEVELOPMENT"}:
        return action in {"CLIENT_LIST", "CONTRACT_FORM", "NEW_PROPOSAL", "PERMIT_INITIATION", "TENDER_EMAIL", "TENDER_DOCUMENT", "TENDER_IMAGE", "CLIENT_INFORMATION"}
    if persona in {"RESPONSIBLE_ENGINEER", "AUTHORIZED_ENGINEER", "ENGINEERING"}:
        return action == "PROPOSAL_FORM"
    return False


def _opportunity_for_project(db: Session, project_id: str) -> Opportunity | None:
    direct = db.scalar(select(Opportunity).where(Opportunity.project_id == project_id).order_by(Opportunity.updated_at.desc()))
    if direct:
        return direct
    reference = db.scalar(select(ReferenceNumber).where(ReferenceNumber.project_id == project_id).order_by(ReferenceNumber.reserved_at))
    if reference and reference.opportunity_id:
        return db.get(Opportunity, reference.opportunity_id)
    return None


def _row(db: Session, opportunity: Opportunity) -> dict[str, Any]:
    quotation = db.scalar(select(Quotation).where(Quotation.opportunity_id == opportunity.id).order_by(Quotation.created_at.desc()))
    contract = db.scalar(select(Contract).where(Contract.quotation_id == quotation.id).order_by(Contract.created_at.desc())) if quotation else None
    reference = db.scalar(select(ReferenceNumber).where(ReferenceNumber.opportunity_id == opportunity.id).order_by(ReferenceNumber.reserved_at))
    project = db.get(Project, opportunity.project_id or (reference.project_id if reference else None)) if opportunity.project_id or (reference and reference.project_id) else None
    proposal_state = opportunity.status
    contract_state = contract.status if contract else None
    artifact_activity = db.scalar(select(ProjectArtifactRecord).where(ProjectArtifactRecord.project_id == project.id).order_by(ProjectArtifactRecord.created_at.desc())) if project else None
    activity_values = [item for item in [artifact_activity.created_at if artifact_activity else None, opportunity.updated_at, quotation.updated_at if quotation else None, contract.updated_at if contract else None] if item]
    last_activity = max(activity_values) if activity_values else datetime.now(timezone.utc)
    sources = proposal_sources(db, opportunity)
    current_contract = contract
    linked_permit = db.scalar(select(PermitApplication).where(PermitApplication.controlling_contract_id == current_contract.id)) if current_contract else None
    if not linked_permit and current_contract and reference and reference.permit_application_id:
        linked_permit = db.get(PermitApplication, reference.permit_application_id)
    next_action = proposal_next_action(opportunity.status, has_contract=bool(current_contract), contract_id=current_contract.id if current_contract else None, source_count=sum(1 for item in sources if item["current"]), project_id=project.id if project else None)
    return {
        "id": opportunity.id,
        "record_type": "PROPOSAL_WORKSPACE",
        "proposal_id": opportunity.id,
        "contract_id": contract.id if contract else None,
        "proposal_description": opportunity.title,
        "project_id": project.id if project else None,
        "project_reference": project.project_number if project else (reference.reference_value if reference else "UNRESOLVED"),
        "project_name": project.project_name if project else "Project context pending",
        "proposal_status": proposal_state,
        "contract_status": contract_state,
        "current_stage": proposal_stage(proposal_state, bool(contract)),
        "status": proposal_state,
        "amount": (opportunity.proposal_fields_json or {}).get("price"),
        "last_activity": last_activity.isoformat(),
        "has_contract": bool(contract),
        "open_path": f"/proposals/{opportunity.id}",
        "source_count": sum(1 for item in sources if item["current"]),
        "source_types": sorted({item["artifact_class"] for item in sources if item["current"]}),
        "reference_state": opportunity.reference_state or "PROVISIONAL",
        "proposal_fields": opportunity.proposal_fields_json or {},
        "next_action": next_action,
        "allowed_actions": ["OPEN", *(["PROCEED"] if next_action["code"] == "PROCEED" and next_action["eligible"] else []), *(["VIEW_CONTRACT"] if current_contract else ["CONTRACT"] if next_action["code"] == "CREATE_CONTRACT" and next_action["eligible"] else [])],
        "related_contract_id": current_contract.id if current_contract else None,
        "contract_action_eligible": bool(project and (current_contract or quotation)),
        "contract_action_label": "Open Contract" if current_contract else "Contract",
        "permit_application_id": linked_permit.id if linked_permit else None,
    }


def _rows(db: Session) -> list[dict[str, Any]]:
    opportunities = db.scalars(select(Opportunity).order_by(Opportunity.updated_at.desc(), Opportunity.opportunity_reference)).all()
    return [_row(db, item) for item in opportunities]


def _matches(row: dict[str, Any], key: str) -> bool:
    definition = KPI_DEFINITIONS.get(key)
    if not definition:
        return False
    state_key = "proposal_status" if definition["entity"] == "proposal" else "contract_status"
    return row.get(state_key) in definition["states"]


def _persona_payload(persona: str) -> dict[str, Any]:
    if persona in {"RESPONSIBLE_ENGINEER", "AUTHORIZED_ENGINEER", "ENGINEERING"}:
        actions = ["PROPOSAL_FORM"]
        amount_visible = False
    elif persona in {"COMMERCIAL_APPROVER", "BD_USER", "BUSINESS_DEVELOPMENT"}:
        actions = ["CLIENT_LIST", "CONTRACT_FORM", "NEW_PROPOSAL", "PERMIT_INITIATION"]
        amount_visible = True
    else:
        actions = ["CLIENT_LIST", "PROPOSAL_FORM", "CONTRACT_FORM", "NEW_PROPOSAL", "PERMIT_INITIATION"]
        amount_visible = True
    source_actions = ["TENDER_EMAIL", "TENDER_DOCUMENT", "TENDER_IMAGE", "CLIENT_INFORMATION"]
    if persona in {"RESPONSIBLE_ENGINEER", "AUTHORIZED_ENGINEER", "ENGINEERING"}:
        source_actions = []
    return {"persona": persona, "allowed_actions": actions, "source_actions": source_actions, "amount_visible": amount_visible}


def _create_handoff_task(db: Session, *, action: str, project_id: str | None, opportunity_id: str, correlation_id: str, actor: str, artifact_id: str) -> dict[str, Any] | None:
    if action == "NEW_PROPOSAL":
        task_type, title, owner_role, from_assistant, to_assistant, next_code = "PROPOSAL_PREPARATION", "Prepare proposal source for Engineering", "RESPONSIBLE_ENGINEER", "BD_ASSISTANT", "ENGINEERING_REVIEW_ASSISTANT", "PROPOSAL_PREPARATION"
    elif action == "PROPOSAL_FORM":
        task_type, title, owner_role, from_assistant, to_assistant, next_code = "PROPOSAL_COMMERCIAL_HANDOFF", "Review verified proposal form for commercial follow-up", "COMMERCIAL_APPROVER", "ENGINEERING_REVIEW_ASSISTANT", "BD_ASSISTANT", "PROPOSAL_HANDOVER"
    else:
        return None
    existing = db.scalar(select(WorkflowTask).where(WorkflowTask.context_type == "OPPORTUNITY", WorkflowTask.context_id == opportunity_id, WorkflowTask.task_type == task_type, WorkflowTask.status.in_((WorkflowTaskStatus.OPEN, WorkflowTaskStatus.IN_PROGRESS))))
    if existing:
        return {"task_id": existing.id, "created": False, "next_action_code": existing.next_action_code}
    task = WorkflowTask(project_id=project_id, task_type=task_type, title=title, description="Created only after the manually provided source was verified in the configured Proposal Intake SOR.", owner_role=owner_role, status=WorkflowTaskStatus.OPEN, priority="NORMAL", correlation_id=correlation_id, task_family="PROPOSALS_CONTRACTS", context_type="OPPORTUNITY", context_id=opportunity_id, blocking=False, next_action_code=next_code, deep_link=f"/proposals/{opportunity_id}/preparation", evidence_summary={"artifact_id": artifact_id, "automatic_orange_source_creation": 0})
    db.add(task)
    db.flush()
    db.add(AssistantHandoff(from_assistant_id=from_assistant, to_assistant_id=to_assistant, context_type="OPPORTUNITY", context_id=opportunity_id, project_id=project_id, opportunity_id=opportunity_id, source_revision_ids=[artifact_id], workflow_task_id=task.id, status="CREATED", reason="Controlled responsibility transition after verified manual source intake."))
    recipient_role = "RESPONSIBLE_ENGINEER" if to_assistant == "ENGINEERING_REVIEW_ASSISTANT" else "COMMERCIAL_APPROVER"
    db.add(NotificationEvent(
        workflow_task_id=task.id,
        recipient_role=recipient_role,
        channel="IN_APP",
        event_type="PROPOSAL_HANDOFF_CREATED",
        status="PENDING",
        subject=title,
        body_preview="A verified Proposal source created a governed handoff requiring review.",
        correlation_id=correlation_id,
        domain="PROPOSAL_WORKFLOW",
        proposal_id=opportunity_id,
        audience=["OWNER", "BUSINESS_DEVELOPMENT", "ENGINEERING"],
        actor=actor,
        deep_link=task.deep_link,
    ))
    return {"task_id": task.id, "created": True, "next_action_code": next_code}


@router.get("", response_model=ProposalMainResponse)
def proposals_main(persona: str = "SYSTEM_ADMIN", view: str = "proposals", db: Session = Depends(get_db)):
    if view not in {"proposals", "contracts"}:
        raise HTTPException(422, "REGISTER_VIEW_REQUIRED")
    rows = _rows(db)
    contracts = db.scalars(select(Contract).order_by(Contract.updated_at.desc())).all()
    contract_rows = []
    for contract in contracts:
        quotation = db.get(Quotation, contract.quotation_id)
        opportunity = db.get(Opportunity, quotation.opportunity_id) if quotation else None
        contract_reference = db.scalar(select(ReferenceNumber).where(ReferenceNumber.contract_id == contract.id).order_by(ReferenceNumber.reserved_at))
        project_id = contract.project_id or (opportunity.project_id if opportunity else None) or (contract_reference.project_id if contract_reference else None)
        project = db.get(Project, project_id) if project_id else None
        proposal = _row(db, opportunity) if opportunity else None
        linked_permit = db.scalar(select(PermitApplication).where(PermitApplication.controlling_contract_id == contract.id).order_by(PermitApplication.created_at))
        if not linked_permit and contract_reference and contract_reference.permit_application_id:
            linked_permit = db.get(PermitApplication, contract_reference.permit_application_id)
        permit_count = 1 if linked_permit else 0
        contract_detail = contract_projection(db, contract, include_history=False)
        permit_id = linked_permit.id if linked_permit else next((item["id"] for item in contract_detail["permits"]), None)
        contract_rows.append({"id": contract.id, "record_type": "CONTRACT", "contract_description": opportunity.title if opportunity else "Contract context pending", "contract_reference": contract.contract_reference, "status": contract.status, "contract_status": contract.status, "related_proposal_id": opportunity.id if opportunity else None, "proposal_id": opportunity.id if opportunity else None, "related_proposal": opportunity.title if opportunity else "—", "project_id": project.id if project else None, "project_reference": project.project_number if project else (opportunity.opportunity_reference if opportunity else "UNRESOLVED"), "project_name": project.project_name if project else "Project context pending", "amount": contract_detail["amount"], "proposal_amount": contract_detail["proposal_amount"], "contract_amount": contract_detail["contract_amount"], "last_activity": contract.updated_at.isoformat(), "end_date": contract.end_date.isoformat() if contract.end_date else None, "permit_count": permit_count, "permit_id": permit_id, "permit_application_id": permit_id, "permit_eligible": bool(project and opportunity), "permit_action_eligible": bool(project and opportunity), "permit_action_label": "Open Permit" if permit_id else "Permit", "permit_action": contract_detail["next_action"], "proposal_status": proposal["proposal_status"] if proposal else None, "next_action": contract_detail["next_action"]})
    kpis = {key: {"label": definition["label"], "count": sum(1 for item in rows if _matches(item, key)) if definition["entity"] == "proposal" else sum(1 for item in contract_rows if (item["status"] in definition["states"])), "states": definition["states"], "entity": definition["entity"]} for key, definition in KPI_DEFINITIONS.items()}
    clients = [{"id": item.id, "reference": item.client_reference, "name": item.display_name, "status": item.status} for item in db.scalars(select(ClientAccount).where(ClientAccount.status == "ACTIVE").order_by(ClientAccount.display_name)).all()]
    return {"rows": rows if view == "proposals" else contract_rows, "proposals": rows, "contracts": contract_rows, "contract_rows": contract_rows, "view": view, "clients": clients, "kpis": kpis, "filters": [{"key": "ALL", "label": "All", "entity": "both"}, {"key": "NEEDS_ACTION", "label": "Needs Action", "entity": "proposal", "states": ["PROPOSAL_HANDOVER"]}, {"key": "IN_REVIEW", "label": "In Review", "entity": "proposal", "states": ["IN_REVIEW", "PROPOSAL_PREPARATION", "PROPOSAL_HANDOVER", "COMMERCIAL_REVIEW"]}, {"key": "READY_CLOSED", "label": "Ready / Closed", "entity": "both", "states": ["READY", "CLOSED", "ACCEPTED"]}], "filter_predicates": {"proposal": {"ALL": None, "NEEDS_ACTION": ["PROPOSAL_HANDOVER"], "IN_REVIEW": ["IN_REVIEW", "PROPOSAL_PREPARATION", "PROPOSAL_HANDOVER", "COMMERCIAL_REVIEW"], "READY_CLOSED": ["READY", "CLOSED", "ACCEPTED"]}, "contract": {"ALL": None, "NEEDS_ACTION": ["CONTRACT_HANDOVER", "DRAFT"], "IN_REVIEW": ["DRAFT", "CONTRACT_IN_PROGRESS", "CONTRACT_HANDOVER"], "READY_CLOSED": ["READY", "CLOSED", "ACCEPTED"]}}, "persona": _persona_payload(persona), "sor": {"adapter": "MockSynologyAdapter", "template_version": SOR_TEMPLATE_VERSION, "intake_template_version": "SYN-PROPOSAL-INTAKE-1.0", "semantic_destinations": {**{key: value["label"] for key, value in SEMANTIC_FOLDER_CONFIG.items()}, **{key: value["label"] for key, value in INTAKE_SEMANTIC_CONFIG.items()}}, "database_role": "workflow index, metadata, lineage; not document bytes"}, "lineage_model": "ReferenceNumber: Proposal/Opportunity → Quotation → Contract → Project → PermitApplication", "synthetic_only": True}


@router.get("/target/{project_id}")
def proposals_target(project_id: str, semantic_class: str, db: Session = Depends(get_db)):
    if semantic_class not in SEMANTIC_FOLDER_CONFIG:
        raise HTTPException(422, "SEMANTIC_CLASS_REQUIRED")
    target = resolve_project_target(db, project_id)
    return {"project_id": project_id, "project_reference": target["project"].project_number, "project_name": target["project"].project_name, "template_version": target["template_version"], "destination_label": SEMANTIC_FOLDER_CONFIG[semantic_class]["label"], "ready": True}


@router.post("/intake")
async def proposals_intake(
    request: Request,
    action: str = Form(...),
    project_id: str | None = Form(default=None),
    file: UploadFile = File(...),
    opportunity_id: str | None = Form(default=None),
    project_reference: str | None = Form(default=None),
    source_revision: str | None = Form(default=None),
    proposal_description: str | None = Form(default=None),
    client_account_id: str | None = Form(default=None),
    create_new_proposal: bool = Form(default=False),
    price: str | None = Form(default=None),
    sow: str | None = Form(default=None),
    period: str | None = Form(default=None),
    exclusions: str | None = Form(default=None),
    actor: str = Form(default="synthetic-user"),
    actor_role: str | None = Form(default=None),
    idempotency_key: str | None = Form(default=None),
    contract_id: str | None = Form(default=None),
    permit_application_id: str | None = Form(default=None),
    db: Session = Depends(get_db),
    role: Role = Depends(current_user_role),
    x_synthetic_sor: str | None = Header(default=None),
):
    capability = "EDIT_TECHNICAL" if action == "PROPOSAL_FORM" else "EDIT_COMMERCIAL" if action == "CONTRACT_FORM" else "INTAKE"
    persona = require_capability(role, capability)
    content = await file.read()
    if action not in ACTION_CONFIG:
        raise HTTPException(422, "UNSUPPORTED_INTAKE_SOURCE")
    if not _allowed(action, persona):
        raise domain_error(403, "ACTION_NOT_ALLOWED_FOR_PERSONA", action=action, persona=persona)
    prior_intake = db.scalar(select(ProposalIntakeArtifact).where(ProposalIntakeArtifact.idempotency_key == idempotency_key)) if idempotency_key else None
    if prior_intake and not opportunity_id:
        opportunity_id = prior_intake.opportunity_id
    # Contract -> Permit is a controlled transition, but the source bytes are
    # still manually selected and written through the same project SOR path.
    if action == "PERMIT_INITIATION":
        if not contract_id:
            raise domain_error(409, "CONTROLLING_CONTRACT_REQUIRED")
        contract = db.get(Contract, contract_id)
        if not contract:
            raise domain_error(404, "CONTRACT_NOT_FOUND")
        quotation = db.get(Quotation, contract.quotation_id)
        opportunity = db.get(Opportunity, quotation.opportunity_id) if quotation else None
        reference = db.scalar(select(ReferenceNumber).where(ReferenceNumber.contract_id == contract.id).order_by(ReferenceNumber.reserved_at))
        resolved_project_id = contract.project_id or (opportunity.project_id if opportunity else None) or (reference.project_id if reference else None)
        if not resolved_project_id or (project_id and project_id != resolved_project_id):
            raise domain_error(409, "PERMIT_CONTRACT_PROJECT_MISMATCH", requested_project_id=project_id, canonical_project_id=resolved_project_id)
        project_id = resolved_project_id
        project = db.get(Project, project_id)
        if not project or not opportunity:
            raise domain_error(409, "CONTRACT_NOT_READY_FOR_PERMIT", blocker="CANONICAL_PROJECT_REFERENCE_REQUIRED")
        if opportunity.project_id and opportunity.project_id != project_id:
            raise domain_error(409, "PERMIT_CONTRACT_PROJECT_MISMATCH", proposal_project_id=opportunity.project_id, requested_project_id=project_id)
        opportunity.project_id = project_id
        contract.project_id = project_id
        application = db.get(PermitApplication, permit_application_id) if permit_application_id else db.scalar(select(PermitApplication).where(PermitApplication.controlling_contract_id == contract.id, PermitApplication.project_id == project_id).order_by(PermitApplication.created_at))
        if application and application.project_id != project_id:
            raise domain_error(409, "PERMIT_CONTRACT_PROJECT_MISMATCH", permit_project_id=application.project_id, requested_project_id=project_id)
        if not application:
            application = db.scalar(select(PermitApplication).where(PermitApplication.project_id == project_id).order_by(PermitApplication.created_at))
        if not application:
            application = PermitApplication(project_id=project_id, authority=project.municipality or "Synthetic Municipality Authority", municipality=project.municipality or "Doha", permit_type=project.permit_type or "Building Permit", external_request_number=f"AMEC-SYN-PMT-{db.query(PermitApplication).count() + 1:04d}", application_status=ApplicationStatus.DRAFT, repetition_count=0, last_status_at=datetime.now(timezone.utc), controlling_contract_id=contract.id)
            db.add(application)
            db.flush()
        elif application.controlling_contract_id and application.controlling_contract_id != contract.id:
            raise domain_error(409, "PERMIT_CONTRACT_PROJECT_MISMATCH", reason="PERMIT_ALREADY_CONTROLLED_BY_DIFFERENT_CONTRACT")
        else:
            application.controlling_contract_id = contract.id
        permit_application_id = application.id
        if reference:
            reference.permit_application_id = application.id

    # Client List reconciles the Client master/source register. It must not
    # opportunistically bind to a Proposal found under the same Project.
    if action != "PERMIT_INITIATION":
        opportunity = None if action == "CLIENT_LIST" else (db.get(Opportunity, opportunity_id) if opportunity_id else (_opportunity_for_project(db, project_id) if project_id and not create_new_proposal else None))
    provisional_source = action in {"TENDER_EMAIL", "TENDER_DOCUMENT", "TENDER_IMAGE", "CLIENT_INFORMATION", "PROPOSAL_FORM", "CLIENT_LIST"}
    existing_context_required = action in {"PROPOSAL_FORM", "CONTRACT_FORM"}
    if action == "NEW_PROPOSAL" or provisional_source:
        if not opportunity and existing_context_required:
            raise domain_error(409, "CANONICAL_PROPOSAL_CONTEXT_REQUIRED", action=action)
        if not opportunity and action == "CLIENT_LIST" and not project_id:
            raise domain_error(409, "CLIENT_LIST_CONTEXT_REQUIRED")
        if not opportunity and not project_id and not (proposal_description or "").strip():
            raise HTTPException(422, "PROPOSAL_DESCRIPTION_REQUIRED")
        if not opportunity and (not existing_context_required and action != "CLIENT_LIST"):
            project = db.get(Project, project_id) if project_id else None
            if project_id and not project:
                raise domain_error(404, "PROJECT_NOT_FOUND", project_id=project_id)
            if project and project_reference and project.project_number != project_reference:
                raise domain_error(409, "PROJECT_REFERENCE_MISMATCH", project_reference=project_reference)
            office = db.get(ConsultancyOffice, project.office_id) if project else None
            if not office:
                office = db.scalar(select(ConsultancyOffice).where(ConsultancyOffice.office_code == "QEC-DOHA"))
            client = db.get(ClientAccount, client_account_id) if client_account_id else db.scalar(select(ClientAccount).where(ClientAccount.status == "ACTIVE").order_by(ClientAccount.created_at))
            if client_account_id and not client:
                raise domain_error(404, "CLIENT_NOT_FOUND", client_account_id=client_account_id)
            if not client:
                client = ClientAccount(client_reference="SYN-CLIENT-INTAKE", legal_name="Synthetic Intake Client", display_name="Synthetic Intake Client", client_type="COMPANY", data_classification="SYNTHETIC")
                db.add(client)
                db.flush()
            title = (proposal_description or f"{action.replace('_', ' ').title()} for {project.project_number if project else 'new client'}").strip()
            provisional_reference = f"AMEC-SYN-OPP-{db.query(Opportunity).count() + 1:04d}"
            opportunity = Opportunity(office_id=office.id, client_account_id=client.id, opportunity_reference=provisional_reference, title=title, status="RECEIVED", source_type=action, current_owner_user_id=None, stage2_capability_scope="UNDECIDED_STAGE2", project_id=project.id if project else None, reference_state="CANONICAL" if project else "PROVISIONAL", proposal_fields_json={}, provisional_reference=provisional_reference, canonical_project_reference=project.project_number if project else None, canonicalized_at=datetime.now(timezone.utc) if project else None, canonicalized_by=actor if project else None)
            db.add(opportunity)
            db.flush()
            db.add(ReferenceNumber(reference_value=f"AMEC-SYN-REF-{db.query(ReferenceNumber).count() + 1:04d}", reference_type="PROPOSAL_INTAKE", opportunity_id=opportunity.id, project_id=project.id if project else None, status="RESERVED"))
            db.flush()
        if opportunity and (proposal_description or "").strip():
            opportunity.title = proposal_description.strip()
        if opportunity:
            opportunity.proposal_fields_json = {**(opportunity.proposal_fields_json or {}), **{key: value for key, value in {"price": price, "sow": sow, "period": period, "exclusions": exclusions}.items() if value is not None}}
    if not opportunity and action in {"PROPOSAL_FORM", "CONTRACT_FORM"}:
        raise domain_error(409, "CANONICAL_PROPOSAL_CONTEXT_REQUIRED")
    if (provisional_source or action == "NEW_PROPOSAL") and not project_id:
        semantic_class = ACTION_CONFIG[action]["semantic_class"]
        result = ingest_provisional_intake_artifact(db, opportunity=opportunity, semantic_class=semantic_class, source_filename=file.filename or "source.bin", content_type=file.content_type or "application/octet-stream", content=content, actor=actor, source_revision=source_revision, idempotency_key=idempotency_key, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"))
        db.commit()
        result["opportunity_id"] = opportunity.id
        result["proposal_reference"] = opportunity.opportunity_reference
        result["workflow"] = {"proposal_status": opportunity.status, "reference_state": opportunity.reference_state}
        return result
    if not project_id:
        raise domain_error(409, "PROJECT_CONTEXT_REQUIRED_FOR_PROJECT_SOR_ACTION")
    if action == "PROPOSAL_FORM":
        if not opportunity or not opportunity.project_id or opportunity.project_id != project_id:
            raise domain_error(409, "ELIGIBLE_PROPOSAL_CONTEXT_REQUIRED")
        linked_contract = db.scalar(select(Contract).join(Quotation).where(Quotation.opportunity_id == opportunity.id).order_by(Contract.created_at.desc()))
        if linked_contract or opportunity.status in {"CONTRACT_HANDOVER", "CONTRACTED", "CLOSED"}:
            raise domain_error(409, "PROPOSAL_ALREADY_CONTRACTED", proposal_id=opportunity.id)
    if action == "PROPOSAL_FORM" and opportunity.status not in {"CONTRACT_HANDOVER", "CLOSED"}:
        opportunity.status = "PROPOSAL_HANDOVER"
    elif action == "CONTRACT_FORM":
        if not contract_id and opportunity:
            contract = db.scalar(select(Contract).join(Quotation).where(Quotation.opportunity_id == opportunity.id).order_by(Contract.created_at.desc()))
            contract_id = contract.id if contract else None
        if not contract_id:
            raise domain_error(409, "CONTROLLING_CONTRACT_REQUIRED")
        contract = db.get(Contract, contract_id)
        if not contract:
            raise domain_error(404, "CONTRACT_NOT_FOUND")
        quotation = db.get(Quotation, contract.quotation_id)
        if not quotation or not opportunity or quotation.opportunity_id != opportunity.id:
            raise domain_error(409, "CONTRACT_PROPOSAL_PROJECT_MISMATCH")
        contract.status = "CONTRACT_IN_PROGRESS"
    elif action == "NEW_PROPOSAL":
        opportunity.status = "RECEIVED"
    result = ingest_project_artifact(db, project_id=project_id, action=action, source_filename=file.filename or "source.bin", content_type=file.content_type or "application/octet-stream", content=content, actor=actor, actor_role=persona, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"), project_reference=project_reference, source_revision=source_revision, idempotency_key=idempotency_key, contract_id=contract_id, opportunity_id=opportunity.id if opportunity else None, permit_application_id=permit_application_id, simulate_sor=x_synthetic_sor)
    if action == "PROPOSAL_FORM" and opportunity and opportunity.status not in {"CONTRACT_HANDOVER", "CLOSED"}:
        opportunity.status = "PROPOSAL_HANDOVER"
    if action == "CLIENT_LIST" and opportunity and opportunity.status == "RECEIVED":
        opportunity.status = "IN_REVIEW"
    audit(db, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"), event_type="PROPOSALS_MAIN_SOURCE_INTAKE", entity_type="Opportunity", entity_id=opportunity.id if opportunity else project_id, actor_id=actor, after={"action": action, "project_id": project_id, "artifact_id": result["id"], "workflow_updated_after_verification": True}, metadata={"persona": persona, "automatic_orange_source_creation": 0})
    handoff = _create_handoff_task(db, action=action, project_id=project_id, opportunity_id=opportunity.id if opportunity else project_id, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"), actor=actor, artifact_id=result["id"]) if opportunity else None
    db.commit()
    result["opportunity_id"] = opportunity.id if opportunity else None
    result["proposal_reference"] = opportunity.opportunity_reference if opportunity else None
    result["workflow"] = {"opportunity_id": opportunity.id if opportunity else None, "proposal_status": opportunity.status if opportunity else None, "contract_id": contract_id, "permit_application_id": permit_application_id}
    result["handoff"] = handoff
    return result


@router.get("/proposals/{proposal_id}")
def proposal_detail(proposal_id: str, db: Session = Depends(get_db)):
    opportunity = db.get(Opportunity, proposal_id)
    if not opportunity:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    project = db.get(Project, opportunity.project_id) if opportunity.project_id else None
    projection = proposal_projection(db, opportunity)
    contract = db.scalar(select(Contract).join(Quotation).where(Quotation.opportunity_id == opportunity.id).order_by(Contract.created_at.desc()))
    tasks = db.scalars(select(WorkflowTask).where(WorkflowTask.context_type == "OPPORTUNITY", WorkflowTask.context_id == opportunity.id).order_by(WorkflowTask.created_at.desc())).all()
    row = _row(db, opportunity)
    return {"proposal": row, "project": {"id": project.id, "reference": project.project_number, "name": project.project_name} if project else None, "client": projection["client"], "sources": projection["sources"], "fields": opportunity.proposal_fields_json or {}, "readiness": {**projection["readiness"], "proceed_ready": projection["next_action"]["eligible"] and projection["next_action"]["code"] == "PROCEED"}, "contract": projection["related_contracts"][0] if projection["related_contracts"] else None, "contracts": projection["related_contracts"], "preparation": {"current_revision": projection["current_revision"], "technical_state": opportunity.status, "next_actor": projection["responsibility"]}, "issues": projection["issues"], "history": projection["history"], "tasks": [{"id": task.id, "title": task.title, "owner_role": task.owner_role, "status": task.status, "next_action_code": task.next_action_code, "deep_link": task.deep_link} for task in tasks]}


@router.post("/proposals/{proposal_id}/promote/{project_id}")
def promote_proposal_sources(proposal_id: str, project_id: str, request: Request, db: Session = Depends(get_db), actor: str = "owner@amec.synthetic", role: Role = Depends(current_user_role)):
    require_capability(role, "PROMOTE_SOR")
    try:
        result = promote_provisional_intake(db, opportunity_id=proposal_id, project_id=project_id, actor=actor, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"))
        db.commit()
        return result
    except HTTPException:
        # Persist controlled per-source states such as CONFLICT and
        # PROMOTION_FAILED so a retry can recover without guessing.
        db.commit()
        raise


@router.post("/proposals/{proposal_id}/proceed")
def proceed_proposal(proposal_id: str, request: Request, db: Session = Depends(get_db), actor: str = "owner@amec.synthetic", role: Role = Depends(current_user_role)):
    require_capability(role, "PROCEED")
    opportunity = db.get(Opportunity, proposal_id)
    if not opportunity:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    source_count = db.query(ProposalIntakeArtifact).filter(ProposalIntakeArtifact.opportunity_id == opportunity.id, ProposalIntakeArtifact.status == "REGISTERED").count()
    if opportunity.project_id:
        source_count += db.query(ProjectArtifactRecord).filter(ProjectArtifactRecord.opportunity_id == opportunity.id, ProjectArtifactRecord.status == "REGISTERED").count()
    missing = []
    if not source_count:
        missing.append("source evidence")
    if not opportunity.client_account_id:
        missing.append("Client context")
    if not opportunity.title.strip():
        missing.append("Proposal Description")
    if opportunity.reference_state not in {"PROVISIONAL", "CANONICAL"}:
        missing.append("reference state")
    if missing:
        raise domain_error(422, "PROPOSAL_INTAKE_INCOMPLETE", blockers=[{"code": item.upper().replace(" ", "_")} for item in missing], missing=missing)
    opportunity.status = "PROPOSAL_PREPARATION"
    artifact = db.scalar(select(ProposalIntakeArtifact).where(ProposalIntakeArtifact.opportunity_id == opportunity.id, ProposalIntakeArtifact.status == "REGISTERED").order_by(ProposalIntakeArtifact.created_at.desc()))
    handoff = _create_handoff_task(db, action="NEW_PROPOSAL", project_id=opportunity.project_id, opportunity_id=opportunity.id, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"), actor=actor, artifact_id=artifact.id if artifact else "SOURCE_EVIDENCE")
    audit(db, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"), event_type="PROPOSAL_PROCEEDED_TO_PREPARATION", entity_type="Opportunity", entity_id=opportunity.id, actor_id=actor, after={"status": opportunity.status, "reference_state": opportunity.reference_state, "handoff": handoff})
    db.commit()
    return {"proposal": _row(db, opportunity), "handoff": handoff, "next_route": f"/proposals/{opportunity.id}/preparation"}


@router.get("/contracts/{contract_id}")
def contract_detail(contract_id: str, db: Session = Depends(get_db)):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(404, "CONTRACT_NOT_FOUND")
    projection = contract_projection(db, contract)
    quotation = db.get(Quotation, contract.quotation_id)
    opportunity = db.get(Opportunity, quotation.opportunity_id) if quotation else None
    project = db.get(Project, projection["project_id"]) if projection["project_id"] else None
    revisions = db.scalars(select(ContractRevision).where(ContractRevision.contract_id == contract.id).order_by(ContractRevision.revision_number)).all()
    return {"contract": projection, "proposal": projection["related_proposal"], "project": projection["project"], "revisions": [{"id": item.id, "revision_number": item.revision_number, "status": item.status, "terms": item.commercial_terms_snapshot or {}} for item in revisions], "sources": projection["sources"], "permits": projection["permits"], "issues": projection["issues"], "history": projection["history"], "handoff": projection["handoff"], "next_action": projection["next_action"], "proposal_fields": (opportunity.proposal_fields_json or {}) if opportunity else {}, "project_identity_valid": bool(project and opportunity and (not opportunity.project_id or opportunity.project_id == project.id))}


@router.post("/proposals/{proposal_id}/contract")
def create_contract_from_proposal(proposal_id: str, request: Request, project_id: str | None = None, db: Session = Depends(get_db), actor: str = "bd@amec.synthetic", role: Role = Depends(current_user_role)):
    require_capability(role, "CREATE_CONTRACT")
    opportunity = db.get(Opportunity, proposal_id)
    if not opportunity:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    if project_id and opportunity.project_id != project_id:
        raise domain_error(409, "CONTRACT_PROPOSAL_PROJECT_MISMATCH", proposal_project_id=opportunity.project_id, requested_project_id=project_id)
    if project_id and not db.get(Project, project_id):
        raise domain_error(404, "PROJECT_NOT_FOUND", project_id=project_id)
    if opportunity.status not in {"PROPOSAL_HANDOVER", "COMMERCIAL_REVIEW", "CLIENT_RESPONSE_PENDING", "PROPOSAL_PREPARATION", "IN_REVIEW"}:
        existing_quotation = db.scalar(select(Quotation).where(Quotation.opportunity_id == opportunity.id).order_by(Quotation.created_at.desc()))
        existing_contract = db.scalar(select(Contract).where(Contract.quotation_id == existing_quotation.id).order_by(Contract.created_at.desc())) if existing_quotation else None
        if existing_contract:
            return {"result": "IDEMPOTENT", "contract_id": existing_contract.id, "contract_reference": existing_contract.contract_reference, "related_proposal_id": opportunity.id, "project_id": existing_contract.project_id, "status": existing_contract.status, "next_route": f"/contracts/{existing_contract.id}"}
        raise domain_error(422, "PROPOSAL_NOT_READY_FOR_CONTRACT", proposal_status=opportunity.status)
    quotation = db.scalar(select(Quotation).where(Quotation.opportunity_id == opportunity.id).order_by(Quotation.created_at.desc()))
    if not quotation:
        client_id = opportunity.client_account_id
        if not client_id:
            raise HTTPException(409, "CLIENT_CONTEXT_REQUIRED")
        quotation = Quotation(opportunity_id=opportunity.id, quotation_reference=f"AMEC-SYN-QTN-{db.query(Quotation).count() + 1:04d}", status="RELEASED_FOR_CONTRACT", client_account_id=client_id)
        db.add(quotation)
        db.flush()
        revision = QuotationRevision(quotation_id=quotation.id, revision_number=1, source_snapshot=opportunity.proposal_fields_json or {}, content_hash=f"PROPOSAL-{opportunity.id}", status="RELEASED", created_by=actor)
        db.add(revision)
        db.flush()
        quotation.current_revision_id = revision.id
    contract = db.scalar(select(Contract).where(Contract.quotation_id == quotation.id).order_by(Contract.created_at.desc()))
    if contract and opportunity.project_id and contract.project_id and contract.project_id != opportunity.project_id:
        raise domain_error(409, "CONTRACT_PROPOSAL_PROJECT_MISMATCH", proposal_project_id=opportunity.project_id, contract_project_id=contract.project_id)
    if not contract:
        fallback_reference = db.scalar(select(ReferenceNumber).where(ReferenceNumber.opportunity_id == opportunity.id).order_by(ReferenceNumber.reserved_at))
        contract = Contract(client_account_id=quotation.client_account_id, quotation_id=quotation.id, contract_reference=f"AMEC-SYN-CTR-{db.query(Contract).count() + 1:04d}", status="DRAFT", project_id=opportunity.project_id or (fallback_reference.project_id if fallback_reference else None))
        db.add(contract)
        db.flush()
        controlling_revision = db.get(QuotationRevision, quotation.current_revision_id) if quotation.current_revision_id else None
        if controlling_revision:
            revision = ContractRevision(contract_id=contract.id, revision_number=1, controlling_quotation_revision_id=controlling_revision.id, status="DRAFT", commercial_terms_snapshot=opportunity.proposal_fields_json or {})
            db.add(revision)
            db.flush()
            contract.current_revision_id = revision.id
    opportunity.status = "CONTRACT_HANDOVER"
    audit(db, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"), event_type="PROPOSAL_CONTRACT_TRANSITION", entity_type="Contract", entity_id=contract.id, actor_id=actor, after={"related_proposal_id": opportunity.id, "project_id": contract.project_id, "cross_project_contract_link": 0})
    db.commit()
    return {"contract_id": contract.id, "contract_reference": contract.contract_reference, "related_proposal_id": opportunity.id, "project_id": contract.project_id, "status": contract.status, "next_route": f"/contracts/{contract.id}"}


@router.post("/proposals/{proposal_id}/engineering-ready")
def engineering_ready(proposal_id: str, request: Request, db: Session = Depends(get_db), actor: str = "engineering@amec.synthetic", role: Role = Depends(current_user_role)):
    require_capability(role, "ENGINEERING_READY")
    opportunity = db.get(Opportunity, proposal_id)
    if not opportunity:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    if opportunity.status != "PROPOSAL_PREPARATION":
        raise HTTPException(409, "PROPOSAL_NOT_IN_ENGINEERING_PREPARATION")
    if not db.query(ProposalIntakeArtifact).filter(ProposalIntakeArtifact.opportunity_id == opportunity.id, ProposalIntakeArtifact.status == "REGISTERED").count() and not db.query(ProjectArtifactRecord).filter(ProjectArtifactRecord.opportunity_id == opportunity.id, ProjectArtifactRecord.status == "REGISTERED").count() and not db.query(ProposalSourceEvidence).filter(ProposalSourceEvidence.proposal_id == opportunity.id, ProposalSourceEvidence.status == "CURRENT").count():
        raise HTTPException(409, "PROPOSAL_FORM_OR_SOURCE_REQUIRED")
    opportunity.status = "PROPOSAL_HANDOVER"
    task = _create_handoff_task(db, action="PROPOSAL_FORM", project_id=opportunity.project_id, opportunity_id=opportunity.id, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"), actor=actor, artifact_id="PROPOSAL_PREPARATION_READY")
    audit(db, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"), event_type="ENGINEERING_PROPOSAL_READY_FOR_BD", entity_type="Opportunity", entity_id=opportunity.id, actor_id=actor, after={"status": opportunity.status, "handoff": task})
    db.commit()
    return {"proposal": _row(db, opportunity), "handoff": task}


@router.post("/contracts/{contract_id}/permit")
def initiate_permit_from_contract(contract_id: str, request: Request, db: Session = Depends(get_db), project_id: str | None = None, actor: str = "owner@amec.synthetic", role: Role = Depends(current_user_role)):
    require_capability(role, "INITIATE_PERMIT")
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(404, "CONTRACT_NOT_FOUND")
    quotation = db.get(Quotation, contract.quotation_id)
    opportunity = db.get(Opportunity, quotation.opportunity_id) if quotation else None
    reference = db.scalar(select(ReferenceNumber).where(ReferenceNumber.contract_id == contract.id).order_by(ReferenceNumber.reserved_at))
    resolved_project_id = project_id or (contract.project_id or (opportunity.project_id if opportunity else None) or (reference.project_id if reference else None))
    if not resolved_project_id:
        raise domain_error(422, "CONTRACT_NOT_READY_FOR_PERMIT", blocker="CANONICAL_PROJECT_REFERENCE_REQUIRED")
    if not opportunity or not opportunity.project_id:
        raise domain_error(422, "CONTRACT_NOT_READY_FOR_PERMIT", blocker="PROPOSAL_CANONICAL_PROJECT_REQUIRED")
    if opportunity.project_id != resolved_project_id:
        raise domain_error(409, "PERMIT_CONTRACT_PROJECT_MISMATCH", proposal_project_id=opportunity.project_id, requested_project_id=resolved_project_id)
    if contract.project_id and contract.project_id != resolved_project_id:
        raise domain_error(409, "PERMIT_CONTRACT_PROJECT_MISMATCH", contract_project_id=contract.project_id, requested_project_id=resolved_project_id)
    if not db.get(Project, resolved_project_id):
        raise domain_error(404, "PROJECT_NOT_FOUND", project_id=resolved_project_id)
    application = db.scalar(select(PermitApplication).where(PermitApplication.project_id == resolved_project_id).order_by(PermitApplication.created_at))
    if not application:
        project = db.get(Project, resolved_project_id)
        application = PermitApplication(
            project_id=resolved_project_id,
            authority=project.municipality if project else "Demo Municipality",
            municipality=project.municipality if project else "Demo Municipality",
            permit_type=project.permit_type if project else "Building Permit",
            external_request_number=f"AMEC-SYN-PMT-{db.query(PermitApplication).count() + 1:04d}",
            application_status=ApplicationStatus.DRAFT,
            repetition_count=0,
            last_status_at=datetime.now(timezone.utc),
        )
        db.add(application)
        db.flush()
    if application.controlling_contract_id and application.controlling_contract_id != contract.id:
        raise domain_error(409, "PERMIT_CONTRACT_PROJECT_MISMATCH", reason="PERMIT_ALREADY_CONTROLLED_BY_DIFFERENT_CONTRACT")
    application.controlling_contract_id = contract.id
    contract.project_id = resolved_project_id
    contract.status = "CONTRACT_HANDOVER"
    audit(db, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"), event_type="CONTRACT_PERMIT_TRANSITION", entity_type="PermitApplication", entity_id=application.id, actor_id=actor, after={"controlling_contract_id": contract.id, "project_id": resolved_project_id, "cross_project_permit_link": 0, "human_final_submission": True})
    db.commit()
    return {"permit_id": application.id, "project_id": resolved_project_id, "controlling_contract_id": contract.id, "next_route": f"/proposals-contracts/{resolved_project_id}/project-and-sources", "human_final_submission": True}


# Canonical route aliases.  The legacy /api/proposals-main surface remains
# available for the existing UI, while these purpose-built projections are the
# backend contract for new ProposalOps clients.
canonical_router = APIRouter(prefix="/api", tags=["canonical-proposalops"])


def _canonical_contract_rows(db: Session) -> list[dict[str, Any]]:
    return [contract_projection(db, item, include_history=False) for item in db.scalars(select(Contract).order_by(Contract.updated_at.desc())).all()]


@canonical_router.get("/proposals-contracts/summary")
def proposals_contracts_summary(db: Session = Depends(get_db)):
    proposal_rows = _rows(db)
    contract_rows = _canonical_contract_rows(db)
    counts = kpi_counts(proposal_rows, contract_rows)
    return {
        **counts,
        "predicates": {key: {"entity": spec["entity"], "states": sorted(spec["states"])} for key, spec in KPI_PREDICATES.items()},
        "list_reconciliation": {
            "open_proposals": sum(1 for item in proposal_rows if item["proposal_status"] in KPI_PREDICATES["open_proposals"]["states"]),
            "open_contracts": sum(1 for item in contract_rows if item["status"] in KPI_PREDICATES["open_contracts"]["states"]),
        },
    }


@canonical_router.get("/proposals-contracts/capabilities")
def proposals_contracts_capabilities():
    return {"personas": ["OWNER", "BUSINESS_DEVELOPMENT", "ENGINEERING"], "capabilities": {key: sorted(value) for key, value in CAPABILITY_MATRIX.items()}}


@canonical_router.get("/proposals-contracts/proposals")
def canonical_proposals(filter: str = "all", db: Session = Depends(get_db)):
    rows = [item for item in _rows(db) if matches_filter(item["proposal_status"], filter, "proposal")]
    return {"items": rows, "rows": rows, "count": len(rows), "filter": filter, "predicate_source": "KPI_PREDICATES"}


@canonical_router.get("/proposals-contracts/contracts")
def canonical_contracts(filter: str = "all", db: Session = Depends(get_db)):
    rows = [item for item in _canonical_contract_rows(db) if matches_filter(item["status"], filter, "contract")]
    return {"items": rows, "rows": rows, "count": len(rows), "filter": filter, "predicate_source": "KPI_PREDICATES"}


@canonical_router.get("/proposals/{proposal_id}")
def canonical_proposal_detail(proposal_id: str, db: Session = Depends(get_db)):
    proposal = db.get(Opportunity, proposal_id)
    if not proposal:
        raise domain_error(404, "PROPOSAL_NOT_FOUND", proposal_id=proposal_id)
    return proposal_projection(db, proposal)


@canonical_router.get("/proposals/{proposal_id}/preparation")
def canonical_proposal_preparation(proposal_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    proposal = db.get(Opportunity, proposal_id)
    if not proposal:
        raise domain_error(404, "PROPOSAL_NOT_FOUND", proposal_id=proposal_id)
    projection = proposal_projection(db, proposal)
    return {
        "proposal": projection,
        "technical_fields": {key: projection["fields"].get(key) for key in ("sow", "period", "exclusions", "process_of_work", "technical_assumptions", "technical_deliverables") if key in projection["fields"]},
        "sources": projection["sources"],
        "proposal_form": next((item for item in projection["sources"] if item["artifact_class"] == "PROPOSAL_SOURCE"), None),
        "comments": [],
        "readiness": projection["readiness"],
        "handoff": {"responsibility": projection["responsibility"], "next_action": projection["next_action"]},
        "persona": persona_for_role(role),
    }


@canonical_router.get("/contracts/{contract_id}")
def canonical_contract_detail(contract_id: str, db: Session = Depends(get_db)):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise domain_error(404, "CONTRACT_NOT_FOUND", contract_id=contract_id)
    return contract_projection(db, contract)


@canonical_router.get("/permits/{permit_id}")
def canonical_permit_detail(permit_id: str, db: Session = Depends(get_db)):
    application = db.get(PermitApplication, permit_id)
    if not application:
        raise domain_error(404, "PERMIT_NOT_FOUND", permit_id=permit_id)
    contract = db.get(Contract, application.controlling_contract_id) if application.controlling_contract_id else None
    return {**permit_projection(application), "project": {"id": application.project.id, "reference": application.project.project_number, "name": application.project.project_name}, "controlling_contract": contract_projection(db, contract, include_history=False) if contract else None}


@canonical_router.post("/proposals/{proposal_id}/proceed")
def canonical_proceed(proposal_id: str, request: Request, db: Session = Depends(get_db), actor: str = "owner@amec.synthetic", role: Role = Depends(current_user_role)):
    require_capability(role, "PROCEED")
    return proceed_proposal(proposal_id, request, db, actor, role)


@canonical_router.post("/proposals/{proposal_id}/contract")
def canonical_create_contract(proposal_id: str, request: Request, project_id: str | None = None, db: Session = Depends(get_db), actor: str = "bd@amec.synthetic", role: Role = Depends(current_user_role)):
    require_capability(role, "CREATE_CONTRACT")
    return create_contract_from_proposal(proposal_id, request, project_id, db, actor, role)


@canonical_router.post("/contracts/{contract_id}/permit")
def canonical_initiate_permit(contract_id: str, request: Request, project_id: str | None = None, db: Session = Depends(get_db), actor: str = "owner@amec.synthetic", role: Role = Depends(current_user_role)):
    require_capability(role, "INITIATE_PERMIT")
    return initiate_permit_from_contract(contract_id, request, db, project_id, actor, role)


@canonical_router.post("/proposals/{proposal_id}/canonicalize/{project_id}")
def canonicalize_proposal(proposal_id: str, project_id: str, request: Request, db: Session = Depends(get_db), actor: str = "owner@amec.synthetic", role: Role = Depends(current_user_role)):
    require_capability(role, "PROMOTE_SOR")
    try:
        result = canonicalize_project_reference(db, opportunity_id=proposal_id, project_id=project_id, actor=actor, correlation_id=getattr(request.state, "correlation_id", "missing-correlation-id"))
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
