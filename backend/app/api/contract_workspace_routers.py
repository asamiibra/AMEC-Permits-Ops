"""Administration Owner Contract list, workbench, and Project activation APIs."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..models import Contract, ContractAdminEvidence, ContractAdminInput, ContractClientInputRequirement, ContractDeliverableCommitment, ContractPaymentTerm, ContractRevision, DashboardInputItem, DocumentVersion, Opportunity, ProposalAcceptedRevision, ProjectActivation, Role
from ..services.backend_realignment import domain_error, require_capability
from ..services.admin_contract_read_model import owner_contract_extensions
from ..services.contract_workspace import CONTRACT_GO_LIVE_SPECS, CONTRACT_STAGES, DEFAULT_CONTRACT_INPUTS, accepted_revision, actor_name, contract_projection, contract_revision_is_finalized, create_contract_from_proposal, effective_contract_stages, now, project_activation, readiness
from ..services.proposal_workspace import stable_hash
from ..services.owner_decisions import get_decision, runtime_decision_value


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
    payment_condition_text: str | None = Field(default=None, max_length=5000)
    contracted_scope_text: str | None = Field(default=None, max_length=10000)
    valuation_amount: Decimal | None = None
    valuation_currency: str | None = Field(default=None, max_length=20)
    valuation_basis: str | None = Field(default=None, max_length=160)
    valuation_status: str | None = Field(default=None, max_length=50)
    project_opportunity_ref: str | None = Field(default=None, max_length=120)
    reason: str = Field(min_length=3, max_length=1000)


class StagePayload(BaseModel):
    stage: str
    reason: str = Field(min_length=3, max_length=1000)


class AuthorityPayload(BaseModel):
    decision: str = Field(default="APPROVE", min_length=1, max_length=40)
    reason: str = Field(min_length=3, max_length=1000)


class AdminInputPayload(BaseModel):
    value: dict[str, Any] = {}
    reason: str = Field(min_length=3, max_length=1000)


class EvidencePayload(BaseModel):
    evidence_type: str = Field(min_length=1, max_length=100)
    source_reference: str = Field(min_length=1, max_length=600)
    source_role: str = Field(default="GENERAL", min_length=1, max_length=80)
    document_version_id: str | None = None
    content_hash: str | None = Field(default=None, max_length=64)
    metadata: dict[str, Any] = {}


class ActivationPayload(BaseModel):
    project_code: str = Field(min_length=1, max_length=80)
    start_date: date
    idempotency_key: str = Field(min_length=1, max_length=200)


class PaymentTermPayload(BaseModel):
    sequence: int = Field(ge=1)
    label: str = Field(min_length=1, max_length=160)
    term_text: str = Field(min_length=1, max_length=10000)
    basis_type: str | None = Field(default=None, max_length=60)
    percentage: Decimal | None = None
    fixed_amount: Decimal | None = None
    currency: str | None = Field(default=None, max_length=20)
    trigger_type: str | None = Field(default=None, max_length=80)
    trigger_description: str | None = Field(default=None, max_length=5000)
    due_days: int | None = None
    source_clause: str | None = Field(default=None, max_length=200)
    source_document_version_id: str | None = None
    status: str = Field(default="NEEDS_REVIEW", max_length=40)
    human_verified: bool = False
    reason: str = Field(default="Owner Contract payment-term entry", min_length=3, max_length=1000)


class DeliverablePayload(BaseModel):
    sequence: int = Field(ge=1)
    commitment_ref: str | None = Field(default=None, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    due_trigger_description: str | None = Field(default=None, max_length=5000)
    source_scope_item_id: str | None = None
    source_document_version_id: str | None = None
    status: str = Field(default="COMMITTED", max_length=40)
    reason: str = Field(default="Owner Contract deliverable entry", min_length=3, max_length=1000)


class ClientInputPayload(BaseModel):
    sequence: int = Field(ge=1)
    input_code: str | None = Field(default=None, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    required: bool = True
    status: str = Field(default="OPEN", max_length=40)
    source_type: str | None = Field(default=None, max_length=80)
    source_document_version_id: str | None = None
    reason: str = Field(default="Owner Contract client-input entry", min_length=3, max_length=1000)


def _contract_or_404(db: Session, contract_id: str) -> Contract:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(404, {"code": "CONTRACT_NOT_FOUND"})
    return contract


def _document_version_or_404(db: Session, document_version_id: str | None) -> DocumentVersion | None:
    if not document_version_id:
        return None
    version = db.get(DocumentVersion, document_version_id)
    if not version:
        raise domain_error(422, "DOCUMENT_VERSION_NOT_FOUND", document_version_id=document_version_id)
    return version


@router.get("")
def list_contracts(q: str = "", filter: str = "ALL", stage: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_READ")
    rows = []
    needle = q.strip().lower()
    for contract in db.scalars(select(Contract).order_by(Contract.updated_at.desc(), Contract.contract_reference)).all():
        detail = contract_projection(db, contract, include_history=False)
        extension = owner_contract_extensions(db, contract)
        detail["contract"].update(extension["contract"])
        detail.update({key: extension[key] for key in ("billing_readiness", "evidence_detail")})
        item = detail["contract"]
        if needle and needle not in " ".join(str(value or "").lower() for value in (item["name"], item["reference"], detail.get("client", {}).get("name") if detail.get("client") else None, contract.project_opportunity_ref)):
            continue
        if stage and stage.upper() != "ALL" and item["stage"] != stage.upper():
            continue
        if filter.upper() == "NEEDS_ACTION" and not detail["readiness"]["blockers"]:
            continue
        if filter.upper() == "AUTHORITY_REVIEW" and item["stage"] != "AUTHORITY_REVIEW":
            continue
        if filter.upper() in {"READY", "READY_CLOSE"} and item["stage"] not in {"READY", "CLOSED", "ACTIVE"}:
            continue
        close_date = item["actual_close_date"] or item["expected_close_date"] or (contract.end_date.isoformat() if contract.end_date else None)
        rows.append({"id": contract.id, "contract": item["name"], "contract_ref": item["reference"], "contract_name": item["name"], "contract_reference": item["reference"], "client": detail["client"], "project_opportunity_ref": contract.project_opportunity_ref, "project": detail["project"], "project_code": detail["project"].get("code") if detail["project"] else None, "stage": item["stage"], "status": item["status"], "amount": item["amount"], "currency": item["currency"], "close_date": close_date, "close_date_meaning": item["close_date_meaning"], "last_activity": item["last_activity"], "open": f"/contracts/{contract.id}", "next_action": detail["my_work"][0]["next_action_code"] if detail["my_work"] else None, "blockers_count": len(detail["readiness"]["blockers"]), "billing_readiness": detail["billing_readiness"]["status"]})
    manual_policy = runtime_decision_value(db, "MANUAL_NEW_CONTRACT_POLICY", "SELECT_ACCEPTED_PROPOSAL_ONLY")
    authority_policy = runtime_decision_value(db, "CONTRACT_AUTHORITY_POLICY", "OWNER_ONLY_FOR_AUTHORITY_AND_EXECUTION_STATE")
    return {"items": rows, "rows": rows, "count": len(rows), "filters": [{"key": "ALL", "label": "All Contracts"}, {"key": "NEEDS_ACTION", "label": "Needs Action"}, {"key": "AUTHORITY_REVIEW", "label": "Authority Review"}, {"key": "READY_CLOSE", "label": "Ready / Close"}], "stage_options": list(effective_contract_stages(db)), "manual_new_policy": manual_policy, "authority": authority_policy, "synthetic_only": True}


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
    legacy_to_canonical = {"CONTRACT_STAGE_NAMES": "CONTRACT_STAGE_POLICY", "CONTRACT_AUTHORITY_REVIEW": "CONTRACT_AUTHORITY_REVIEW_MEANING", "CONTRACT_PROPOSAL_INITIATION_RULE": "MANUAL_NEW_CONTRACT_POLICY", "CONTRACT_TEMPLATE_POLICY": "OFFICIAL_CONTRACT_TEMPLATE", "PROJECT_CODE_POLICY": "PROJECT_CODE_ASSIGNMENT_METHOD", "CONTRACT_ARTIFACT_SOR": "CONTRACT_ARTIFACT_STRATEGY", "CONTRACT_PERMIT_HANDOFF": "CONTRACT_TO_PROJECT_TRIGGER", "REAL_SYNOLOGY_VERIFICATION": "REAL_SYNOLOGY_CONNECTION"}
    items = []
    for key, description in CONTRACT_GO_LIVE_SPECS:
        canonical_key = legacy_to_canonical.get(key, key)
        decision = get_decision(db, canonical_key)
        default = decision.proposed_default_json if decision else DEFAULT_CONTRACT_INPUTS.get(key.lower(), {}).get("value")
        items.append({"key": key, "canonical_key": canonical_key, "title": key.replace("_", " ").title(), "requested_input": description, "status": decision.status if decision else "UNANSWERED", "blocking": decision.blocking_level if decision else ("EXTERNAL_TECHNICAL" if key == "REAL_SYNOLOGY_VERIFICATION" else "BUSINESS"), "route": "/admin/owner-decisions", "safe_default": default, "effective_value": decision.effective_value_json if decision else None, "apply_state": decision.apply_state if decision else "NOT_APPLIED", "owner_confirmed": bool(decision and decision.status in {"OWNER_CONFIRMED", "OWNER_CONFIRMED_WITH_NOTES", "OWNER_MARKED_NOT_APPLICABLE", "SAFE_DEFAULT_APPROVED_FOR_GO_LIVE"})})
    remaining = sum(1 for item in items if not item["owner_confirmed"])
    return {"context": "ADMIN_CONTRACT", "safe_defaults": DEFAULT_CONTRACT_INPUTS, "items": items, "minimum_input_count": len(items), "summary": {"total": len(items), "remaining": remaining, "ready": remaining == 0}}


@router.get("/{contract_id}")
def get_contract(contract_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_READ")
    contract = _contract_or_404(db, contract_id)
    detail = contract_projection(db, contract)
    extension = owner_contract_extensions(db, contract)
    detail["contract"].update(extension.pop("contract"))
    detail.update(extension)
    return detail


@router.get("/{contract_id}/billing-context")
def get_billing_context(contract_id: str, revision_id: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_READ")
    contract = _contract_or_404(db, contract_id)
    from ..services.contract_workspace import contract_billing_context
    return contract_billing_context(db, contract, revision_id=revision_id)


@router.patch("/{contract_id}")
def patch_contract(contract_id: str, payload: ContractPatchPayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_EDIT")
    contract = _contract_or_404(db, contract_id)
    current = contract_projection(db, contract, include_history=False)["contract"]
    accepted = db.get(ProposalAcceptedRevision, contract.accepted_proposal_revision_id) if contract.accepted_proposal_revision_id else None
    previous_revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    if not previous_revision:
        raise domain_error(409, "CONTRACT_REVISION_REQUIRED")
    if contract_revision_is_finalized(previous_revision):
        raise domain_error(409, "CONTRACT_FINALIZED_REVISION_IMMUTABLE", revision_id=previous_revision.id, amendment_policy="CREATE_PROSPECTIVE_AMENDMENT_REVISION")
    revision_number = (previous_revision.revision_number or 0) + 1
    values = {"contract_name": payload.contract_name if payload.contract_name is not None else contract.contract_name, "amount_value": payload.amount if payload.amount is not None else contract.amount_value, "currency": payload.currency if payload.currency is not None else contract.currency, "duration": payload.duration if payload.duration is not None else contract.duration, "expected_close_date": payload.expected_close_date if payload.expected_close_date is not None else contract.expected_close_date, "actual_close_date": payload.actual_close_date if payload.actual_close_date is not None else contract.actual_close_date, "project_opportunity_ref": payload.project_opportunity_ref if payload.project_opportunity_ref is not None else contract.project_opportunity_ref, "payment_condition_text": payload.payment_condition_text if payload.payment_condition_text is not None else contract.payment_condition_text, "contracted_scope_text": payload.contracted_scope_text if payload.contracted_scope_text is not None else contract.contracted_scope_text, "valuation_amount": payload.valuation_amount if payload.valuation_amount is not None else contract.valuation_amount, "valuation_currency": payload.valuation_currency if payload.valuation_currency is not None else contract.valuation_currency, "valuation_basis": payload.valuation_basis if payload.valuation_basis is not None else contract.valuation_basis, "valuation_status": payload.valuation_status if payload.valuation_status is not None else contract.valuation_status}
    before = {"contract": current, "accepted_proposal_revision_id": contract.accepted_proposal_revision_id}
    revision = ContractRevision(contract_id=contract.id, revision_number=revision_number, controlling_quotation_revision_id=previous_revision.controlling_quotation_revision_id, accepted_proposal_revision_id=contract.accepted_proposal_revision_id, source_snapshot=accepted.snapshot if accepted else previous_revision.source_snapshot, contract_name=values["contract_name"], stage=contract.stage, amount_value=values["amount_value"], currency=values["currency"], duration=values["duration"], expected_close_date=values["expected_close_date"], actual_close_date=values["actual_close_date"], payment_condition_text=values["payment_condition_text"], contracted_scope_text=values["contracted_scope_text"], valuation_amount=values["valuation_amount"], valuation_currency=values["valuation_currency"], valuation_basis=values["valuation_basis"], valuation_status=values["valuation_status"], status="DRAFT", supersedes_revision_id=previous_revision.id, commercial_terms_snapshot={**(previous_revision.commercial_terms_snapshot or {}), "contract_edit_reason": payload.reason, "accepted_proposal_revision_id": contract.accepted_proposal_revision_id}, content_hash=stable_hash(values))
    db.add(revision)
    db.flush()
    for item in db.scalars(select(ContractPaymentTerm).where(ContractPaymentTerm.contract_revision_id == previous_revision.id)).all():
        db.add(ContractPaymentTerm(contract_id=contract.id, contract_revision_id=revision.id, sequence=item.sequence, label=item.label, term_text=item.term_text, basis_type=item.basis_type, percentage=item.percentage, fixed_amount=item.fixed_amount, currency=item.currency, trigger_type=item.trigger_type, trigger_description=item.trigger_description, due_days=item.due_days, source_clause=item.source_clause, source_document_version_id=item.source_document_version_id, status=item.status, candidate_source=item.candidate_source, human_verified_by=item.human_verified_by, human_verified_at=item.human_verified_at, metadata_json=item.metadata_json))
    for item in db.scalars(select(ContractDeliverableCommitment).where(ContractDeliverableCommitment.contract_revision_id == previous_revision.id)).all():
        db.add(ContractDeliverableCommitment(contract_id=contract.id, contract_revision_id=revision.id, sequence=item.sequence, commitment_ref=item.commitment_ref, name=item.name, description=item.description, due_trigger_description=item.due_trigger_description, source_scope_item_id=item.source_scope_item_id, source_document_version_id=item.source_document_version_id, status=item.status, human_verified_by=item.human_verified_by, human_verified_at=item.human_verified_at, metadata_json=item.metadata_json))
    for item in db.scalars(select(ContractClientInputRequirement).where(ContractClientInputRequirement.contract_revision_id == previous_revision.id)).all():
        db.add(ContractClientInputRequirement(contract_id=contract.id, contract_revision_id=revision.id, sequence=item.sequence, input_code=item.input_code, title=item.title, description=item.description, required=item.required, status=item.status, source_type=item.source_type, source_document_version_id=item.source_document_version_id, human_verified_by=item.human_verified_by, human_verified_at=item.human_verified_at, metadata_json=item.metadata_json))
    contract.current_revision_id = revision.id
    contract.contract_name = values["contract_name"]
    contract.amount_value = values["amount_value"]
    contract.currency = values["currency"]
    contract.duration = values["duration"]
    contract.expected_close_date = values["expected_close_date"]
    contract.actual_close_date = values["actual_close_date"]
    contract.project_opportunity_ref = values["project_opportunity_ref"]
    contract.payment_condition_text = values["payment_condition_text"]
    contract.contracted_scope_text = values["contracted_scope_text"]
    contract.valuation_amount = values["valuation_amount"]
    contract.valuation_currency = values["valuation_currency"]
    contract.valuation_basis = values["valuation_basis"]
    contract.valuation_status = values["valuation_status"]
    contract.last_activity_at = now()
    contract.field_provenance = {**(contract.field_provenance or {}), "last_edit": {"actor": actor_name(role), "reason": payload.reason, "revision_id": revision.id}}
    audit(db, correlation_id=request.state.correlation_id, event_type="ADMIN_CONTRACT_REVISION_CREATED", entity_type="Contract", entity_id=contract.id, actor_id=actor_name(role), before=before, after={"revision_id": revision.id, "accepted_proposal_revision_id": contract.accepted_proposal_revision_id, "content_hash": revision.content_hash}, metadata={"reason": payload.reason, "historical_revision_preserved": True})
    db.commit()
    return contract_projection(db, contract)


@router.post("/{contract_id}/stage")
def stage_contract(contract_id: str, payload: StagePayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_AUTHORITY_ACTION" if payload.stage.upper() in {"AUTHORITY_REVIEW", "READY"} else "CONTRACT_CLOSE" if payload.stage.upper() == "CLOSED" else "CONTRACT_EDIT")
    allowed_stages = effective_contract_stages(db)
    if payload.stage.upper() not in allowed_stages:
        raise domain_error(422, "CONTRACT_STAGE_INVALID", allowed=list(allowed_stages))
    contract = _contract_or_404(db, contract_id)
    before = {"stage": contract.stage, "status": contract.status, "authority_state": contract.authority_state}
    contract.stage = payload.stage.upper()
    contract.status = contract.stage
    contract.authority_state = "OWNER_REVIEWED" if contract.stage in {"AUTHORITY_REVIEW", "READY"} else contract.authority_state
    contract.last_activity_at = now()
    audit(db, correlation_id=request.state.correlation_id, event_type="ADMIN_CONTRACT_STAGE_CHANGED", entity_type="Contract", entity_id=contract.id, actor_id=actor_name(role), before=before, after={"stage": contract.stage, "status": contract.status}, metadata={"reason": payload.reason, "human_action": True})
    db.commit()
    return contract_projection(db, contract)


@router.post("/{contract_id}/authority")
def decide_contract_authority(contract_id: str, payload: AuthorityPayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_AUTHORITY_ACTION")
    contract = _contract_or_404(db, contract_id)
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    if not revision:
        raise domain_error(409, "CONTRACT_REVISION_REQUIRED")
    decision = payload.decision.upper()
    if decision in {"APPROVE", "AUTHORIZE", "READY"}:
        check = readiness(db, contract)
        if not check["ready"]:
            raise domain_error(409, "CONTRACT_AUTHORITY_BLOCKED", blockers=check["blockers"])
        if contract_revision_is_finalized(revision):
            return {"decision": "ALREADY_FINALIZED", "revision_id": revision.id, "contract": contract_projection(db, contract)}
        before = {"revision_status": revision.status, "contract_stage": contract.stage, "authority_state": contract.authority_state}
        revision.status = "APPROVED"
        contract.authority_state = "AUTHORIZED_OWNER_REVIEW"
        contract.stage = "READY"
        contract.status = "READY"
        contract.last_activity_at = now()
        audit(db, correlation_id=request.state.correlation_id, event_type="ADMIN_CONTRACT_AUTHORITY_APPROVED", entity_type="Contract", entity_id=contract.id, actor_id=actor_name(role), before=before, after={"revision_id": revision.id, "revision_status": revision.status, "contract_stage": contract.stage, "legal_execution": False}, metadata={"reason": payload.reason, "human_action": True})
    elif decision in {"RETURN", "REJECT", "NEEDS_ACTION"}:
        revision.status = "DRAFT"
        contract.authority_state = "RETURNED_FOR_OWNER_ACTION"
        contract.stage = "NEEDS_ACTION"
        contract.status = "NEEDS_ACTION"
        contract.last_activity_at = now()
        audit(db, correlation_id=request.state.correlation_id, event_type="ADMIN_CONTRACT_AUTHORITY_RETURNED", entity_type="Contract", entity_id=contract.id, actor_id=actor_name(role), after={"revision_id": revision.id, "contract_stage": contract.stage}, metadata={"reason": payload.reason, "human_action": True})
    else:
        raise domain_error(422, "CONTRACT_AUTHORITY_DECISION_INVALID", allowed=["APPROVE", "RETURN"])
    db.commit()
    return {"decision": decision, "revision_id": revision.id, "contract": contract_projection(db, contract)}


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
    if payload.source_role in {"LPO", "CLIENT_DOCUMENT", "EXECUTED_CONTRACT"} and not payload.document_version_id:
        raise domain_error(422, "EXACT_DOCUMENT_VERSION_REQUIRED_FOR_CLIENT_EVIDENCE", source_role=payload.source_role)
    document = _document_version_or_404(db, payload.document_version_id)
    source_reference = payload.source_reference or (document.source_path_or_reference if document else "")
    evidence = ContractAdminEvidence(contract_id=contract.id, contract_revision_id=contract.current_revision_id, evidence_type=payload.evidence_type, source_role=payload.source_role, document_version_id=payload.document_version_id, source_reference=source_reference, content_hash=payload.content_hash or (document.sha256 if document else None), recorded_by=actor_name(role), metadata_json=payload.metadata)
    db.add(evidence)
    audit(db, correlation_id=request.state.correlation_id, event_type="ADMIN_CONTRACT_EVIDENCE_RECORDED", entity_type="Contract", entity_id=contract.id, actor_id=actor_name(role), after={"evidence_id": evidence.id, "evidence_type": payload.evidence_type, "source_reference": payload.source_reference})
    db.commit()
    return {"id": evidence.id, "status": evidence.status, "contract_id": contract.id, "source_role": evidence.source_role, "document_version_id": evidence.document_version_id}


@router.post("/{contract_id}/commercial-terms")
def add_payment_term(contract_id: str, payload: PaymentTermPayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_EDIT")
    contract = _contract_or_404(db, contract_id)
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    if not revision:
        raise domain_error(409, "CONTRACT_REVISION_REQUIRED")
    if contract_revision_is_finalized(revision):
        raise domain_error(409, "CONTRACT_FINALIZED_REVISION_IMMUTABLE", revision_id=revision.id)
    _document_version_or_404(db, payload.source_document_version_id)
    item = db.scalar(select(ContractPaymentTerm).where(ContractPaymentTerm.contract_revision_id == revision.id, ContractPaymentTerm.sequence == payload.sequence))
    if item:
        raise domain_error(409, "CONTRACT_PAYMENT_TERM_SEQUENCE_EXISTS", sequence=payload.sequence)
    item = ContractPaymentTerm(contract_id=contract.id, contract_revision_id=revision.id, sequence=payload.sequence, label=payload.label, term_text=payload.term_text, basis_type=payload.basis_type, percentage=payload.percentage, fixed_amount=payload.fixed_amount, currency=payload.currency, trigger_type=payload.trigger_type, trigger_description=payload.trigger_description, due_days=payload.due_days, source_clause=payload.source_clause, source_document_version_id=payload.source_document_version_id, status="VERIFIED" if payload.human_verified else payload.status, human_verified_by=actor_name(role) if payload.human_verified else None, human_verified_at=now() if payload.human_verified else None)
    db.add(item)
    audit(db, correlation_id=request.state.correlation_id, event_type="ADMIN_CONTRACT_PAYMENT_TERM_RECORDED", entity_type="Contract", entity_id=contract.id, actor_id=actor_name(role), after={"payment_term_id": item.id, "revision_id": revision.id, "sequence": item.sequence, "human_verified": payload.human_verified}, metadata={"reason": payload.reason})
    db.commit()
    return owner_contract_extensions(db, contract)


@router.post("/{contract_id}/deliverables")
def add_deliverable(contract_id: str, payload: DeliverablePayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_EDIT")
    contract = _contract_or_404(db, contract_id)
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    if not revision:
        raise domain_error(409, "CONTRACT_REVISION_REQUIRED")
    if contract_revision_is_finalized(revision):
        raise domain_error(409, "CONTRACT_FINALIZED_REVISION_IMMUTABLE", revision_id=revision.id)
    _document_version_or_404(db, payload.source_document_version_id)
    if db.scalar(select(ContractDeliverableCommitment).where(ContractDeliverableCommitment.contract_revision_id == revision.id, ContractDeliverableCommitment.sequence == payload.sequence)):
        raise domain_error(409, "CONTRACT_DELIVERABLE_SEQUENCE_EXISTS", sequence=payload.sequence)
    item = ContractDeliverableCommitment(contract_id=contract.id, contract_revision_id=revision.id, sequence=payload.sequence, commitment_ref=payload.commitment_ref, name=payload.name, description=payload.description, due_trigger_description=payload.due_trigger_description, source_scope_item_id=payload.source_scope_item_id, source_document_version_id=payload.source_document_version_id, status=payload.status)
    db.add(item)
    audit(db, correlation_id=request.state.correlation_id, event_type="ADMIN_CONTRACT_DELIVERABLE_RECORDED", entity_type="Contract", entity_id=contract.id, actor_id=actor_name(role), after={"deliverable_id": item.id, "revision_id": revision.id, "sequence": item.sequence}, metadata={"reason": payload.reason})
    db.commit()
    return owner_contract_extensions(db, contract)


@router.post("/{contract_id}/client-inputs")
def add_client_input(contract_id: str, payload: ClientInputPayload, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "CONTRACT_EDIT")
    contract = _contract_or_404(db, contract_id)
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    if not revision:
        raise domain_error(409, "CONTRACT_REVISION_REQUIRED")
    if contract_revision_is_finalized(revision):
        raise domain_error(409, "CONTRACT_FINALIZED_REVISION_IMMUTABLE", revision_id=revision.id)
    _document_version_or_404(db, payload.source_document_version_id)
    if db.scalar(select(ContractClientInputRequirement).where(ContractClientInputRequirement.contract_revision_id == revision.id, ContractClientInputRequirement.sequence == payload.sequence)):
        raise domain_error(409, "CONTRACT_CLIENT_INPUT_SEQUENCE_EXISTS", sequence=payload.sequence)
    item = ContractClientInputRequirement(contract_id=contract.id, contract_revision_id=revision.id, sequence=payload.sequence, input_code=payload.input_code, title=payload.title, description=payload.description, required=payload.required, status=payload.status, source_type=payload.source_type, source_document_version_id=payload.source_document_version_id)
    db.add(item)
    audit(db, correlation_id=request.state.correlation_id, event_type="ADMIN_CONTRACT_CLIENT_INPUT_RECORDED", entity_type="Contract", entity_id=contract.id, actor_id=actor_name(role), after={"client_input_id": item.id, "revision_id": revision.id, "sequence": item.sequence}, metadata={"reason": payload.reason})
    db.commit()
    return owner_contract_extensions(db, contract)


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
