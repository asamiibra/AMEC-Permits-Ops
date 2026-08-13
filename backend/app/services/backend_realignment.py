"""Canonical backend contracts for the ProposalOps realignment.

The repository predates the ProposalOps vocabulary.  This module is the
translation seam: it keeps the existing SQLAlchemy entities and permit engine
authoritative while making the new commands, personas, predicates, projections
and typed failures explicit.
"""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    AuditEvent,
    Contract,
    ContractRevision,
    Finding,
    Opportunity,
    PermitApplication,
    Project,
    ProjectArtifactRecord,
    ProposalIntakeArtifact,
    Quotation,
    QuotationRevision,
    ReferenceNumber,
    Role,
    WorkflowTask,
)


CANONICAL_PERSONAS = ("OWNER", "BUSINESS_DEVELOPMENT", "ENGINEERING")

ROLE_TO_PERSONA = {
    Role.OWNER_SPONSOR.value: "OWNER",
    # SYSTEM_ADMIN is an internal test/operations role, not one of the three
    # user-facing personas.  It retains existing backend maintenance access.
    Role.SYSTEM_ADMIN.value: "SYSTEM_ADMIN",
    Role.PROCESS_CHAMPION.value: "BUSINESS_DEVELOPMENT",
    "COMMERCIAL_APPROVER": "BUSINESS_DEVELOPMENT",
    "BD_USER": "BUSINESS_DEVELOPMENT",
    "BUSINESS_DEVELOPMENT": "BUSINESS_DEVELOPMENT",
    Role.RESPONSIBLE_ENGINEER.value: "ENGINEERING",
    Role.REQUIREMENT_STEWARD.value: "ENGINEERING",
    Role.PERMIT_PREPARER.value: "ENGINEERING",
    "AUTHORIZED_ENGINEER": "ENGINEERING",
    "ENGINEERING": "ENGINEERING",
}

CAPABILITY_MATRIX = {
    "SYSTEM_ADMIN": {"READ_ALL", "PROMOTE_SOR", "PROCEED", "CREATE_CONTRACT", "INITIATE_PERMIT", "INTAKE", "EDIT_COMMERCIAL", "EDIT_TECHNICAL", "PROPOSAL_PREPARATION", "ENGINEERING_READY", "PERMIT_TECHNICAL", "MASTER_FORM_WRITE", "MASTER_REPORT_WRITE", "MASTER_ENGINEERING_WRITE", "DEFINITION_WRITE", "MASTER_CONTENT_ARCHIVE", "MASTER_CONTENT_BINDING_WRITE", "MASTER_CATEGORY_WRITE", "MASTER_CONTENT_GOVERNANCE_WRITE", "MASTER_CONTENT_INGEST_VERSION", "MASTER_SOURCE_VERIFY_CURRENTNESS", "MASTER_SOURCE_MANAGE_QUALITY", "MASTER_SOURCE_SECTION_MANAGE", "MASTER_READINESS_EVALUATE", "MASTER_ACCEPT_RISK", "MASTER_RESTRICTED_SAMPLE_VIEW", "MASTER_RESTRICTED_SAMPLE_DOWNLOAD", "BD_PROPOSAL_READ", "BD_PROPOSAL_WRITE", "BD_PROPOSAL_ACCEPT", "BD_PROPOSAL_HANDOFF", "BD_PROPOSAL_OWNER_SETTINGS", "CONTRACT_READ", "CONTRACT_CREATE", "CONTRACT_EDIT", "CONTRACT_AUTHORITY_ACTION", "CONTRACT_CLOSE", "CONTRACT_ADMIN_INPUT_WRITE", "PROJECT_ACTIVATE", "ENGINEERING_PROJECT_READ", "ENGINEERING_PROJECT_EDIT", "ENGINEERING_REVIEW", "ENGINEERING_CATEGORY_ASSIGNMENT_MANAGE", "ENGINEERING_PROFESSIONAL_APPROVE", "ENGINEERING_BASELINE_APPROVE"},
    "OWNER": {"READ_ALL", "PROMOTE_SOR", "PROCEED", "CREATE_CONTRACT", "INITIATE_PERMIT", "INTAKE", "EDIT_COMMERCIAL", "EDIT_TECHNICAL", "PROPOSAL_PREPARATION", "ENGINEERING_READY", "PERMIT_TECHNICAL", "MASTER_FORM_WRITE", "MASTER_REPORT_WRITE", "MASTER_ENGINEERING_WRITE", "DEFINITION_WRITE", "MASTER_CONTENT_ARCHIVE", "MASTER_CONTENT_BINDING_WRITE", "MASTER_CATEGORY_WRITE", "MASTER_CONTENT_GOVERNANCE_WRITE", "MASTER_CONTENT_INGEST_VERSION", "MASTER_SOURCE_VERIFY_CURRENTNESS", "MASTER_SOURCE_MANAGE_QUALITY", "MASTER_SOURCE_SECTION_MANAGE", "MASTER_READINESS_EVALUATE", "MASTER_ACCEPT_RISK", "MASTER_RESTRICTED_SAMPLE_VIEW", "MASTER_RESTRICTED_SAMPLE_DOWNLOAD", "BD_PROPOSAL_READ", "BD_PROPOSAL_WRITE", "BD_PROPOSAL_ACCEPT", "BD_PROPOSAL_HANDOFF", "BD_PROPOSAL_OWNER_SETTINGS", "CONTRACT_READ", "CONTRACT_CREATE", "CONTRACT_EDIT", "CONTRACT_AUTHORITY_ACTION", "CONTRACT_CLOSE", "CONTRACT_ADMIN_INPUT_WRITE", "PROJECT_ACTIVATE", "ENGINEERING_PROJECT_READ", "ENGINEERING_PROJECT_EDIT", "ENGINEERING_REVIEW", "ENGINEERING_CATEGORY_ASSIGNMENT_MANAGE", "ENGINEERING_PROFESSIONAL_APPROVE", "ENGINEERING_BASELINE_APPROVE"},
    "BUSINESS_DEVELOPMENT": {
        "READ_ALL", "INTAKE", "EDIT_COMMERCIAL", "PROCEED", "CREATE_CONTRACT", "INITIATE_PERMIT", "BD_PROPOSAL_READ", "BD_PROPOSAL_WRITE", "BD_PROPOSAL_ACCEPT", "BD_PROPOSAL_HANDOFF", "BD_PROPOSAL_OWNER_SETTINGS", "CONTRACT_READ",
    },
    "ENGINEERING": {
        "READ_ALL", "EDIT_TECHNICAL", "PROPOSAL_PREPARATION", "ENGINEERING_READY", "PERMIT_TECHNICAL", "BD_PROPOSAL_READ", "CONTRACT_READ", "ENGINEERING_PROJECT_READ", "ENGINEERING_PROJECT_EDIT", "ENGINEERING_REVIEW", "ENGINEERING_CATEGORY_ASSIGNMENT_MANAGE", "ENGINEERING_PROFESSIONAL_APPROVE", "ENGINEERING_BASELINE_APPROVE",
    },
}

# One registry drives both summary counts and list filters.  States are stored
# as strings in the legacy expansion tables and are intentionally not renamed.
KPI_PREDICATES = {
    "open_proposals": {"entity": "proposal", "states": frozenset({"RECEIVED", "IN_REVIEW", "PROPOSAL_PREPARATION", "PROPOSAL_HANDOVER", "READY_FOR_QUOTATION", "QUOTATION_IN_PROGRESS", "COMMERCIAL_REVIEW", "CLIENT_RESPONSE_PENDING"})},
    "open_contracts": {"entity": "contract", "states": frozenset({"DRAFT", "CONTRACT_IN_PROGRESS", "READY_FOR_ADMIN"})},
    "proposal_handover": {"entity": "proposal", "states": frozenset({"PROPOSAL_HANDOVER"})},
    "contract_handover": {"entity": "contract", "states": frozenset({"CONTRACT_HANDOVER", "HANDOVER_DRAFT_READY", "HANDOVER_RELEASED"})},
    "proposals_in_process": {"entity": "proposal", "states": frozenset({"PROPOSAL_PREPARATION", "QUOTATION_IN_PROGRESS", "COMMERCIAL_REVIEW", "PROPOSAL_HANDOVER"})},
    "contracts_in_process": {"entity": "contract", "states": frozenset({"DRAFT", "CONTRACT_IN_PROGRESS", "CONTRACT_HANDOVER"})},
}

PROPOSAL_STAGE_LABELS = {
    "RECEIVED": "Intake",
    "IN_REVIEW": "Intake Review",
    "PROPOSAL_PREPARATION": "Engineering Preparation",
    "PROPOSAL_HANDOVER": "Engineering Ready for BD",
    "READY_FOR_QUOTATION": "Ready for Quotation",
    "QUOTATION_IN_PROGRESS": "BD Commercial Review",
    "COMMERCIAL_REVIEW": "BD Commercial Review",
    "CLIENT_RESPONSE_PENDING": "Client Response",
    "CONTRACT_HANDOVER": "Contracted",
    "ACCEPTED": "Accepted",
    "CLOSED": "Closed",
}

LIST_FILTERS = {
    "open": ("open_proposals", "open_contracts"),
    "handover": ("proposal_handover", "contract_handover"),
    "in_process": ("proposals_in_process", "contracts_in_process"),
    "needs_action": ("proposal_handover", "contract_handover"),
    "ready": ("proposal_handover", "contract_handover"),
    "closed": (),
}


def persona_for_role(role: Role | str) -> str:
    value = role.value if isinstance(role, Role) else str(role)
    return ROLE_TO_PERSONA.get(value, "OWNER" if value == "SYSTEM_ADMIN" else "ENGINEERING")


def require_capability(role: Role | str, capability: str) -> str:
    persona = persona_for_role(role)
    if capability not in CAPABILITY_MATRIX.get(persona, set()):
        raise HTTPException(status_code=403, detail={"code": "CAPABILITY_DENIED", "persona": persona, "capability": capability})
    return persona


def domain_error(status_code: int, code: str, **details: Any) -> HTTPException:
    return HTTPException(status_code=status_code, detail={"code": code, **details})


def proposal_contracts(db: Session, proposal_id: str) -> list[Contract]:
    return list(db.scalars(select(Contract).join(Quotation).where(Quotation.opportunity_id == proposal_id).order_by(Contract.created_at)).all())


def proposal_sources(db: Session, proposal: Opportunity) -> list[dict[str, Any]]:
    intake = db.scalars(select(ProposalIntakeArtifact).where(ProposalIntakeArtifact.opportunity_id == proposal.id).order_by(ProposalIntakeArtifact.created_at)).all()
    canonical = db.scalars(select(ProjectArtifactRecord).where(ProjectArtifactRecord.opportunity_id == proposal.id).order_by(ProjectArtifactRecord.created_at)).all()
    result: list[dict[str, Any]] = []
    for item in intake:
        promoted = (item.metadata_json or {}).get("promotion_state") == "CANONICAL_VERIFIED"
        result.append({
            "id": item.id,
            "artifact_class": item.semantic_class,
            "filename": item.source_filename,
            "path": item.sor_path,
            "content_hash": item.content_hash,
            "verification_status": item.verification_state,
            "reference_state": "HISTORICAL_PROVISIONAL" if promoted else "PROVISIONAL",
            "promotion_state": (item.metadata_json or {}).get("promotion_state", "PROVISIONAL"),
            "authoritative": False if promoted else item.status == "REGISTERED",
            "version": (item.metadata_json or {}).get("version", 1),
            "uploaded_at": item.created_at.isoformat() if item.created_at else None,
            "current": item.status == "REGISTERED",
            "sor_binding": "PROPOSAL_INTAKE_SOR",
        })
    for item in canonical:
        result.append({
            "id": item.id,
            "artifact_class": item.semantic_class,
            "filename": item.source_filename,
            "path": item.sor_path,
            "content_hash": item.content_hash,
            "verification_status": item.verification_state,
            "reference_state": "CANONICAL",
            "promotion_state": "CANONICAL",
            "authoritative": item.status == "REGISTERED" and item.verification_state == "READ_BACK_VERIFIED",
            "version": (item.audit_metadata or {}).get("version", 1),
            "uploaded_at": item.created_at.isoformat() if item.created_at else None,
            "current": item.status == "REGISTERED",
            "sor_binding": "CANONICAL_PROJECT_SOR",
        })
    return result


def proposal_stage(status: str, has_contract: bool = False) -> str:
    if has_contract:
        return "Contracted" if status != "CLOSED" else "Closed"
    return PROPOSAL_STAGE_LABELS.get(status, status.replace("_", " ").title())


def proposal_next_action(status: str, *, has_contract: bool, contract_id: str | None, source_count: int, project_id: str | None) -> dict[str, Any]:
    if has_contract and contract_id:
        return {"code": "VIEW_CONTRACT", "label": "View Contract", "primary": "OPEN", "owner_role": "BUSINESS_DEVELOPMENT", "eligible": True, "route": f"/contracts/{contract_id}"}
    if status in {"RECEIVED", "IN_REVIEW"}:
        if not source_count:
            return {"code": "PROCEED", "label": "Proceed", "primary": "PROCEED", "owner_role": "BUSINESS_DEVELOPMENT", "eligible": False, "disabled_reason": "Proceed unavailable — source intake incomplete", "route": None}
        return {"code": "PROCEED", "label": "Proceed", "primary": "PROCEED", "owner_role": "BUSINESS_DEVELOPMENT", "eligible": True, "route": None}
    if status == "PROPOSAL_PREPARATION":
        return {"code": "OPEN_PREPARATION", "label": "Open Preparation", "primary": "OPEN", "owner_role": "ENGINEERING", "eligible": True, "route": None}
    if status in {"PROPOSAL_HANDOVER", "READY_FOR_QUOTATION", "QUOTATION_IN_PROGRESS", "COMMERCIAL_REVIEW", "CLIENT_RESPONSE_PENDING"}:
        return {"code": "CREATE_CONTRACT", "label": "Contract", "primary": "CONTRACT", "owner_role": "BUSINESS_DEVELOPMENT", "eligible": True, "route": None}
    return {"code": "OPEN_PROPOSAL", "label": "Open", "primary": "OPEN", "owner_role": "BUSINESS_DEVELOPMENT", "eligible": True, "route": None}


def _field_projection(fields: dict[str, Any]) -> dict[str, Any]:
    return {
        key: {"current_value": value, "status": "CANDIDATE", "source_count": 0, "last_changed": None, "owner": "UNVERIFIED"}
        for key, value in fields.items()
    }


def proposal_projection(db: Session, proposal: Opportunity) -> dict[str, Any]:
    project = db.get(Project, proposal.project_id) if proposal.project_id else None
    contracts = proposal_contracts(db, proposal.id)
    sources = proposal_sources(db, proposal)
    contract = contracts[-1] if contracts else None
    for field in _field_projection(proposal.proposal_fields_json or {}).values():
        field["source_count"] = len(sources)
    tasks = db.scalars(select(WorkflowTask).where(WorkflowTask.context_type == "OPPORTUNITY", WorkflowTask.context_id == proposal.id).order_by(WorkflowTask.created_at.desc())).all()
    history = db.scalars(select(AuditEvent).where(AuditEvent.entity_type == "Opportunity", AuditEvent.entity_id == proposal.id).order_by(AuditEvent.occurred_at.desc()).limit(20)).all()
    issues = db.scalars(select(Finding).where(Finding.proposal_id == proposal.id).order_by(Finding.captured_at.desc()).limit(20)).all()
    return {
        "id": proposal.id,
        "entity_type": "Proposal",
        "proposal_reference": proposal.opportunity_reference,
        "title": proposal.title,
        "client_id": proposal.client_account_id,
        "project": {"id": project.id, "reference": project.project_number, "name": project.project_name} if project else None,
        "reference_state": proposal.reference_state,
        "provisional_reference": proposal.provisional_reference or proposal.opportunity_reference,
        "canonical_project_reference": project.project_number if project else None,
        "current_stage": proposal_stage(proposal.status, bool(contracts)),
        "responsibility": "ENGINEERING" if proposal.status == "PROPOSAL_PREPARATION" else "BUSINESS_DEVELOPMENT",
        "fields": _field_projection(proposal.proposal_fields_json or {}),
        "sources": sources,
        "current_revision": _current_proposal_revision(db, proposal, contracts),
        "related_contracts": [contract_projection(db, contract, include_history=False) for contract in contracts],
        "issues": [{"id": item.id, "title": item.title, "summary": item.normalized_summary, "severity": item.severity, "status": item.status, "blocking": item.blocking, "deep_link": item.deep_link} for item in issues],
        "history": [{"event_type": item.event_type, "occurred_at": item.occurred_at.isoformat(), "actor": item.actor_id} for item in history],
        "next_action": proposal_next_action(proposal.status, has_contract=bool(contracts), contract_id=contract.id if contract else None, source_count=sum(1 for item in sources if item["current"]), project_id=proposal.project_id),
        "readiness": {
            "source_evidence": bool(sources),
            "verified_sor": bool(sources) and all(item["verification_status"] == "READ_BACK_VERIFIED" for item in sources if item["authoritative"]),
            "client_context": bool(proposal.client_account_id),
            "description": bool(proposal.title.strip()),
            "reference_state": proposal.reference_state in {"PROVISIONAL", "CANONICAL"},
        },
        "source_count": sum(1 for item in sources if item["current"]),
        "client": {"id": proposal.client_account_id} if proposal.client_account_id else None,
        "last_activity": proposal.updated_at.isoformat() if proposal.updated_at else None,
    }


def _current_proposal_revision(db: Session, proposal: Opportunity, contracts: list[Contract]) -> dict[str, Any] | None:
    revision = None
    if contracts:
        quotation = db.get(Quotation, contracts[-1].quotation_id)
        revision = db.get(QuotationRevision, quotation.current_revision_id) if quotation and quotation.current_revision_id else None
    if not revision:
        quotation = db.scalar(select(Quotation).where(Quotation.opportunity_id == proposal.id).order_by(Quotation.created_at.desc()))
        revision = db.get(QuotationRevision, quotation.current_revision_id) if quotation and quotation.current_revision_id else None
    if not revision:
        return None
    return {"id": revision.id, "revision_number": revision.revision_number, "status": revision.status, "content_hash": revision.content_hash, "canonical_name": "ProposalRevision"}


def _next_action(tasks: list[WorkflowTask]) -> dict[str, Any] | None:
    task = next((item for item in tasks if item.status not in {"COMPLETED", "CANCELLED"}), None)
    return {"task_id": task.id, "code": task.next_action_code, "owner_role": task.owner_role, "title": task.title} if task else None


def contract_projection(db: Session, contract: Contract, *, include_history: bool = True) -> dict[str, Any]:
    quotation = db.get(Quotation, contract.quotation_id)
    proposal = db.get(Opportunity, quotation.opportunity_id) if quotation else None
    project = db.get(Project, contract.project_id or (proposal.project_id if proposal else None))
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    permits = db.scalars(select(PermitApplication).where(PermitApplication.controlling_contract_id == contract.id).order_by(PermitApplication.created_at)).all()
    sources = db.scalars(select(ProjectArtifactRecord).where(ProjectArtifactRecord.contract_id == contract.id).order_by(ProjectArtifactRecord.created_at)).all()
    history = db.scalars(select(AuditEvent).where(AuditEvent.entity_type == "Contract", AuditEvent.entity_id == contract.id).order_by(AuditEvent.occurred_at.desc()).limit(20)).all() if include_history else []
    issues = db.scalars(select(Finding).where(Finding.contract_id == contract.id).order_by(Finding.captured_at.desc()).limit(20)).all()
    terms = revision.commercial_terms_snapshot or {} if revision else {}
    proposal_amount = (proposal.proposal_fields_json or {}).get("price") if proposal else None
    contract_amount = terms.get("price") if isinstance(terms, dict) else None
    return {
        "id": contract.id,
        "entity_type": "Contract",
        "reference": contract.contract_reference,
        "status": contract.status,
        "project": {"id": project.id, "reference": project.project_number, "name": project.project_name} if project else None,
        "project_id": project.id if project else contract.project_id,
        "related_proposal_id": proposal.id if proposal else None,
        "related_proposal": {"id": proposal.id, "reference": proposal.opportunity_reference, "title": proposal.title, "status": proposal.status} if proposal else None,
        "current_revision": {"id": revision.id, "revision_number": revision.revision_number, "status": revision.status, "terms": revision.commercial_terms_snapshot or {}} if revision else None,
        "amount": contract_amount or proposal_amount,
        "proposal_amount": proposal_amount,
        "contract_amount": contract_amount or proposal_amount,
        "end_date": contract.end_date.isoformat() if contract.end_date else None,
        "sources": [{"id": item.id, "artifact_class": item.semantic_class, "content_hash": item.content_hash, "verification_status": item.verification_state, "path": item.sor_path} for item in sources],
        "divergences": [],
        "handoff": {"status": contract.status, "human_final_submission": True},
        "permits": [permit_projection(item) for item in permits],
        "issues": [{"id": item.id, "title": item.title, "summary": item.normalized_summary, "severity": item.severity, "status": item.status, "blocking": item.blocking, "deep_link": item.deep_link} for item in issues],
        "history": [{"event_type": item.event_type, "occurred_at": item.occurred_at.isoformat(), "actor": item.actor_id} for item in history],
        "next_action": {"code": "OPEN_PERMIT" if permits else "INITIATE_PERMIT", "label": "Open Permit" if permits else "Permit", "primary": "OPEN_PERMIT" if permits else "INITIATE_PERMIT", "eligible": bool(project), "route": f"/proposals-contracts/{project.id}/project-and-sources" if project else None, "disabled_reason": None if project else "Permit unavailable — canonical Project Reference required"},
    }


def permit_projection(application: PermitApplication) -> dict[str, Any]:
    status = application.application_status.value if hasattr(application.application_status, "value") else str(application.application_status)
    return {"id": application.id, "external_request_number": application.external_request_number, "status": status, "project_id": application.project_id, "controlling_contract_id": application.controlling_contract_id, "human_final_submission": True}


def kpi_counts(proposals: list[dict[str, Any]], contracts: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for key, spec in KPI_PREDICATES.items():
        rows = proposals if spec["entity"] == "proposal" else contracts
        state_key = "proposal_status" if spec["entity"] == "proposal" else "status"
        counts[key] = sum(1 for item in rows if item.get(state_key) in spec["states"])
    return counts


def matches_filter(state: str | None, filter_name: str, entity: str) -> bool:
    if filter_name == "all" or not filter_name:
        return True
    predicates = LIST_FILTERS.get(filter_name.lower())
    if predicates is None:
        return False
    key = next((name for name in predicates if KPI_PREDICATES[name]["entity"] == entity), None)
    if filter_name.lower() == "closed":
        return state in {"CLOSED", "RELEASED", "ACCEPTED", "APPROVED"}
    return bool(key and state in KPI_PREDICATES[key]["states"])


def identity_check(proposal: Opportunity, project: Project | None, *, requested_project_id: str | None = None) -> None:
    if requested_project_id and (not project or requested_project_id != project.id):
        raise domain_error(409, "PROJECT_IDENTITY_CONFLICT", requested_project_id=requested_project_id, proposal_project_id=proposal.project_id)
    if proposal.project_id and project and proposal.project_id != project.id:
        raise domain_error(409, "PROJECT_IDENTITY_CONFLICT", proposal_project_id=proposal.project_id, project_id=project.id)
