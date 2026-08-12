"""Administration Owner Contract list, workbench, and Project activation APIs."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..models import Contract, ContractAdminEvidence, ContractAdminInput, ContractRevision, DashboardInputItem, Opportunity, ProposalAcceptedRevision, ProjectActivation, Role
from ..services.backend_realignment import domain_error, require_capability
from ..services.contract_workspace import CONTRACT_GO_LIVE_SPECS, CONTRACT_STAGES, DEFAULT_CONTRACT_INPUTS, accepted_revision, actor_name, contract_projection, create_contract_from_proposal, now, project_activation, readiness
from ..services.proposal_workspace import stable_hash
from ..services.owner_decisions import runtime_decision_value


router = APIRouter(prefix="/api/admin/contracts", tags=["administration-contract-owner-session"])


class ContractCreatePayload(BaseModel):
    proposal_id: str | None = None
    accepted_revision_id: str | None = None
    contract_reference: str | None = Field(default=None, max_length=100)


class ContractPatchPayload(BaseModel):
    contract_name: str | None = Field(default=None, max_length=250)
    amount: str | None = Field(default=None, max_length=100)
    currency: str | None = Field(default=None, max_length=20)
    duration: str | None = Field(default=None, max_length=120)
    expected_close_date: date | None = None
    actual_close_date: date | None = None
    close_date_meaning: str | None = Field(default=None, max_length=120)
    project_opportunity_ref: str | None = Field(default=None, max_length=120)
    reason: str = Field(min_length=3, max_length=1000)


class StagePayload(BaseModel):
    stage: str
    reason: str = Field(min_length=3, max_length=1000)


class AdminInputPayload(BaseModel):
    value: dict[str, Any] = {}
    reason: str = Field(min_length=3, max_length=1000)


class EvidencePayload(BaseModel):
    evidence_type: str = Field(min_length=1, max_length=100)
    source_reference: str = Field(min_length=1, max_length=600)
    content_hash: str | None = Field(default=None, max_length=64)
    metadata: dict[str, Any] = {}


class ActivationPayload(BaseModel):
    project_code: str = Field(min_length=1, max_length=80)
    start_date: date
    idempotency_key: str = Field(min_length=1, max_length=200)


def _contract_or_404(db: Session, contract_id: str) -> Contract:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(404, {"code": "CONTRACT_NOT_FOUND"})
    return contract


@router.get("")
def list_contracts(q: str = "", filter: str = "ALL", stage: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_READ")
    rows = []
    needle = q.strip().lower()
    for contract in db.scalars(select(Contract).order_by(Contract.updated_at.desc(), Contract.contract_reference)).all():
        detail = contract_projection(db, contract, include_history=False)
        item = detail["contract"]
        if needle and needle not in " ".join(str(value or "").lower() for value in (item["name"], item["reference"], detail.get("client", {}).get("name") if detail.get("client") else None, contract.project_opportunity_ref)):
            continue
        if stage and stage.upper() != "ALL" and item["stage"] != stage.upper():
            continue
        if filter.upper() == "NEEDS_ACTION" and item["stage"] not in {"DRAFT", "NEEDS_ACTION"}:
            continue
        if filter.upper() == "AUTHORITY_REVIEW" and item["stage"] != "AUTHORITY_REVIEW":
            continue
        if filter.upper() in {"READY", "READY_CLOSE"} and item["stage"] not in {"READY", "CLOSED", "ACTIVE"}:
            continue
        close_date = item["actual_close_date"] or item["expected_close_date"] or (contract.end_date.isoformat() if contract.end_date else None)
        rows.append({"id": contract.id, "contract": item["name"], "contract_ref": item["reference"], "client": detail["client"], "project_opportunity_ref": contract.project_opportunity_ref, "project": detail["project"], "stage": item["stage"], "status": item["status"], "amount": item["amount"], "currency": item["currency"], "close_date": close_date, "last_activity": item["last_activity"], "open": f"/contracts/{contract.id}", "accepted_proposal_revision_id": contract.accepted_proposal_revision_id})
    manual_policy = runtime_decision_value(db, "MANUAL_NEW_CONTRACT_POLICY", "SELECT_ACCEPTED_PROPOSAL_ONLY")
    authority_policy = runtime_decision_value(db, "CONTRACT_AUTHORITY_POLICY", "OWNER_ONLY_FOR_AUTHORITY_AND_EXECUTION_STATE")
    return {"items": rows, "rows": rows, "count": len(rows), "filters": [{"key": "ALL", "label": "All Contracts"}, {"key": "NEEDS_ACTION", "label": "Needs Action"}, {"key": "AUTHORITY_REVIEW", "label": "Authority Review"}, {"key": "READY_CLOSE", "label": "Ready / Close"}], "stage_options": list(CONTRACT_STAGES), "manual_new_policy": manual_policy, "authority": authority_policy, "synthetic_only": True}


@router.post("")
def create_contract(payload: ContractCreatePayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_CREATE")
    if not payload.proposal_id:
        raise domain_error(422, "MANUAL_CONTRACT_POLICY_REQUIRES_ACCEPTED_PROPOSAL", policy="SELECT_ACCEPTED_PROPOSAL_ONLY")
    proposal = db.get(Opportunity, payload.proposal_id)
    revision = accepted_revision(db, payload.proposal_id, payload.accepted_revision_id)
    if not proposal or not revision:
        raise domain_error(409, "ACCEPTED_PROPOSAL_REVISION_REQUIRED")
    try:
        contract = create_contract_from_proposal(db, proposal=proposal, accepted=revision, actor=actor_name(role), correlation_id=request.state.correlation_id, requested_reference=payload.contract_reference)
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    db.commit()
    return contract_projection(db, contract)


@router.post("/from-proposal/{proposal_id}")
def create_from_proposal(proposal_id: str, payload: ContractCreatePayload | None = None, request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_CREATE")
    proposal = db.get(Opportunity, proposal_id)
    revision = accepted_revision(db, proposal_id, payload.accepted_revision_id if payload else None)
    if not proposal or not revision:
        raise domain_error(409, "ACCEPTED_PROPOSAL_REVISION_REQUIRED")
    try:
        contract = create_contract_from_proposal(db, proposal=proposal, accepted=revision, actor=actor_name(role), correlation_id=request.state.correlation_id if request else "contract-create", requested_reference=payload.contract_reference if payload else None)
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    db.commit()
    return contract_projection(db, contract)


@router.get("/inputs/go-live")
def contract_inputs_go_live(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_READ")
    items = [{"key": key, "title": key.replace("_", " ").title(), "requested_input": description, "status": "PROPOSED_DEFAULT" if key in {"CONTRACT_REFERENCE_POLICY", "CONTRACT_STAGE_NAMES", "CONTRACT_TEMPLATE_POLICY", "PROJECT_ACTIVATION_AUTHORITY", "PROJECT_START_DATE_SEMANTICS", "CONTRACT_REOPEN_POLICY"} else "NEEDS_CONFIRMATION", "blocking": "EXTERNAL_TECHNICAL" if key == "REAL_SYNOLOGY_VERIFICATION" else "BUSINESS", "route": "/admin/contract-setup", "safe_default": DEFAULT_CONTRACT_INPUTS.get(key.lower(), {}).get("value")} for key, description in CONTRACT_GO_LIVE_SPECS]
    return {"context": "ADMIN_CONTRACT", "safe_defaults": DEFAULT_CONTRACT_INPUTS, "items": items, "minimum_input_count": 22, "summary": {"total": len(items), "remaining": len(items), "ready": False}}


@router.get("/{contract_id}")
def get_contract(contract_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_READ")
    return contract_projection(db, _contract_or_404(db, contract_id))


@router.patch("/{contract_id}")
def patch_contract(contract_id: str, payload: ContractPatchPayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_EDIT")
    contract = _contract_or_404(db, contract_id)
    current = contract_projection(db, contract, include_history=False)["contract"]
    accepted = db.get(ProposalAcceptedRevision, contract.accepted_proposal_revision_id) if contract.accepted_proposal_revision_id else None
    previous_revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    if not previous_revision:
        raise domain_error(409, "CONTRACT_REVISION_REQUIRED")
    revision_number = (previous_revision.revision_number or 0) + 1
    values = {"contract_name": payload.contract_name if payload.contract_name is not None else contract.contract_name, "amount_value": payload.amount if payload.amount is not None else contract.amount_value, "currency": payload.currency if payload.currency is not None else contract.currency, "duration": payload.duration if payload.duration is not None else contract.duration, "expected_close_date": payload.expected_close_date if payload.expected_close_date is not None else contract.expected_close_date, "actual_close_date": payload.actual_close_date if payload.actual_close_date is not None else contract.actual_close_date, "project_opportunity_ref": payload.project_opportunity_ref if payload.project_opportunity_ref is not None else contract.project_opportunity_ref}
    before = {"contract": current, "accepted_proposal_revision_id": contract.accepted_proposal_revision_id}
    revision = ContractRevision(contract_id=contract.id, revision_number=revision_number, controlling_quotation_revision_id=previous_revision.controlling_quotation_revision_id, accepted_proposal_revision_id=contract.accepted_proposal_revision_id, source_snapshot=accepted.snapshot if accepted else previous_revision.source_snapshot, contract_name=values["contract_name"], stage=contract.stage, amount_value=values["amount_value"], currency=values["currency"], duration=values["duration"], expected_close_date=values["expected_close_date"], actual_close_date=values["actual_close_date"], status="DRAFT", supersedes_revision_id=previous_revision.id, commercial_terms_snapshot={**(previous_revision.commercial_terms_snapshot or {}), "contract_edit_reason": payload.reason, "accepted_proposal_revision_id": contract.accepted_proposal_revision_id}, content_hash=stable_hash(values))
    db.add(revision)
    db.flush()
    contract.current_revision_id = revision.id
    contract.contract_name = values["contract_name"]
    contract.amount_value = values["amount_value"]
    contract.currency = values["currency"]
    contract.duration = values["duration"]
    contract.expected_close_date = values["expected_close_date"]
    contract.actual_close_date = values["actual_close_date"]
    contract.project_opportunity_ref = values["project_opportunity_ref"]
    contract.last_activity_at = now()
    contract.field_provenance = {**(contract.field_provenance or {}), "last_edit": {"actor": actor_name(role), "reason": payload.reason, "revision_id": revision.id}}
    audit(db, correlation_id=request.state.correlation_id, event_type="ADMIN_CONTRACT_REVISION_CREATED", entity_type="Contract", entity_id=contract.id, actor_id=actor_name(role), before=before, after={"revision_id": revision.id, "accepted_proposal_revision_id": contract.accepted_proposal_revision_id, "content_hash": revision.content_hash}, metadata={"reason": payload.reason, "historical_revision_preserved": True})
    db.commit()
    return contract_projection(db, contract)


@router.post("/{contract_id}/stage")
def stage_contract(contract_id: str, payload: StagePayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_AUTHORITY_ACTION" if payload.stage.upper() in {"AUTHORITY_REVIEW", "READY"} else "CONTRACT_CLOSE" if payload.stage.upper() == "CLOSED" else "CONTRACT_EDIT")
    if payload.stage.upper() not in CONTRACT_STAGES:
        raise domain_error(422, "CONTRACT_STAGE_INVALID", allowed=list(CONTRACT_STAGES))
    contract = _contract_or_404(db, contract_id)
    before = {"stage": contract.stage, "status": contract.status, "authority_state": contract.authority_state}
    contract.stage = payload.stage.upper()
    contract.status = contract.stage
    contract.authority_state = "OWNER_REVIEWED" if contract.stage in {"AUTHORITY_REVIEW", "READY"} else contract.authority_state
    contract.last_activity_at = now()
    audit(db, correlation_id=request.state.correlation_id, event_type="ADMIN_CONTRACT_STAGE_CHANGED", entity_type="Contract", entity_id=contract.id, actor_id=actor_name(role), before=before, after={"stage": contract.stage, "status": contract.status}, metadata={"reason": payload.reason, "human_action": True})
    db.commit()
    return contract_projection(db, contract)


@router.get("/{contract_id}/readiness")
def get_readiness(contract_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_READ")
    return readiness(db, _contract_or_404(db, contract_id))


@router.get("/{contract_id}/history")
def get_history(contract_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_READ")
    return {"items": contract_projection(db, _contract_or_404(db, contract_id))["history"], "rewrite_policy": "APPEND_ONLY"}


@router.get("/{contract_id}/inputs")
def get_inputs(contract_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_READ")
    return contract_projection(db, _contract_or_404(db, contract_id))["inputs"]


@router.put("/{contract_id}/inputs/{input_key}")
def put_input(contract_id: str, input_key: str, payload: AdminInputPayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_ADMIN_INPUT_WRITE")
    contract = _contract_or_404(db, contract_id)
    item = db.scalar(select(ContractAdminInput).where(ContractAdminInput.contract_id == contract.id, ContractAdminInput.input_key == input_key))
    if not item:
        item = ContractAdminInput(contract_id=contract.id, input_key=input_key, value_json=payload.value, entered_by=actor_name(role), reason=payload.reason)
        db.add(item)
    else:
        item.value_json = payload.value
        item.entered_by = actor_name(role)
        item.reason = payload.reason
    audit(db, correlation_id=request.state.correlation_id, event_type="ADMIN_CONTRACT_INPUT_UPDATED", entity_type="Contract", entity_id=contract.id, actor_id=actor_name(role), after={"input_key": input_key, "value": payload.value}, metadata={"reason": payload.reason})
    db.commit()
    return contract_projection(db, contract)["inputs"]


@router.post("/{contract_id}/evidence")
def add_evidence(contract_id: str, payload: EvidencePayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_EDIT")
    contract = _contract_or_404(db, contract_id)
    evidence = ContractAdminEvidence(contract_id=contract.id, contract_revision_id=contract.current_revision_id, evidence_type=payload.evidence_type, source_reference=payload.source_reference, content_hash=payload.content_hash, recorded_by=actor_name(role), metadata_json=payload.metadata)
    db.add(evidence)
    audit(db, correlation_id=request.state.correlation_id, event_type="ADMIN_CONTRACT_EVIDENCE_RECORDED", entity_type="Contract", entity_id=contract.id, actor_id=actor_name(role), after={"evidence_id": evidence.id, "evidence_type": payload.evidence_type, "source_reference": payload.source_reference})
    db.commit()
    return {"id": evidence.id, "status": evidence.status, "contract_id": contract.id}


@router.get("/{contract_id}/activation")
def get_activation(contract_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_READ")
    return contract_projection(db, _contract_or_404(db, contract_id))["activation"]


@router.post("/{contract_id}/activate-project")
def activate_project(contract_id: str, payload: ActivationPayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "PROJECT_ACTIVATE")
    contract = _contract_or_404(db, contract_id)
    check = readiness(db, contract)
    if not check["ready"]:
        raise domain_error(409, "PROJECT_ACTIVATION_BLOCKED", blockers=check["blockers"])
    try:
        project, activation, created = project_activation(db, contract=contract, project_code=payload.project_code.strip(), start_date=payload.start_date, actor=actor_name(role), correlation_id=request.state.correlation_id, idempotency_key=payload.idempotency_key)
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    db.commit()
    return {"created": created, "activation": {"id": activation.id, "project_id": project.id, "project_code": activation.project_code, "start_date": activation.start_date.isoformat(), "activated_by": activation.activated_by, "activated_at": activation.activated_at.isoformat()}, "contract": contract_projection(db, contract)}


@router.get("/{contract_id}/project-context")
def project_context(contract_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_READ")
    detail = contract_projection(db, _contract_or_404(db, contract_id))
    return {"client": detail["client"], "project": detail["project"], "contract": {"id": detail["contract"]["id"], "reference": detail["contract"]["reference"], "stage": detail["contract"]["stage"]}, "proposal_origin": detail["origin"], "engineering_context": "READ_ONLY_CONTRACT_PROJECT_CONTEXT", "permit_context": "READ_ONLY_CANONICAL_PROJECT_AND_CONTROLLING_CONTRACT"}
