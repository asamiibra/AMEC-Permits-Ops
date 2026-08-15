"""BD Proposal list and owner workbench API."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..models import AssistantHandoff, AuditEvent, ClientAccount, ConsultancyOffice, Contract, ContractRevision, Document, DocumentApprovalState, DocumentType, DocumentVersion, NotificationEvent, Opportunity, ProposalAcceptedRevision, ProposalAssumption, ProposalClientResponse, ProposalCommercialOutcome, ProposalConflict, ProposalContactContext, ProposalEngineeringContribution, ProposalExpectedInputPreview, ProposalExternalCostAssumption, ProposalIntakeArtifact, ProposalMaterialAcknowledgment, ProposalOutputArtifact, ProposalOwnerSetting, ProposalRegulatoryScopeIntent, ProposalRevision, ProposalServiceScopeItem, ProposalSiteContext, ProposalSourceEvidence, ProposalSourceLink, ProposalStakeholderIntent, ProposalStalenessEvent, ProposalUnknown, ProposalNote, Quotation, QuotationRevision, ReferenceNumber, Role, WorkflowTask, WorkflowTaskStatus
from ..config.settings import get_settings as app_settings
from ..services.backend_realignment import domain_error, require_capability
from ..services.master_content import definition_lookup
from ..services.proposal_workspace import SOURCE_TYPES, SOURCE_TO_SEMANTIC, ensure_owner_settings, master_content_purpose, output_bytes, owner_lane_definitions, proposal_configuration, proposal_projection, snapshot_for_accept, stable_hash, validate_proposal, intake_readiness
from ..services.bd_proposal_forms_v2 import add_source_link, create_preview, set_contact, set_site_context, v2_readiness
from ..services.proposal_final_hardening import hardening_projection, impacted_sections_for_source, material_fingerprint, now as hardening_now
from ..services.proposal_reference import allocate_proposal_reference
from ..services.proposals_sor import ingest_provisional_intake_artifact
from ..services.contract_workspace import accepted_revision as accepted_contract_revision, create_contract_from_proposal
from ..services.owner_decisions import applied_runtime_decision_value, runtime_decision_value

router = APIRouter(prefix="/api/bd/proposals", tags=["bd-proposal-owner-session"])


class ProposalCreate(BaseModel):
    proposal_description: str = Field(min_length=1, max_length=250)
    project_reference: str | None = None
    project_id: str | None = None
    client_account_id: str | None = None
    client_name: str | None = None


class ProposalFieldsPatch(BaseModel):
    fields: dict[str, Any] = {}
    amec_input: dict[str, Any] | None = None
    provenance: dict[str, Any] | None = None
    expected_updated_at: str | None = None


class OwnerSettingsPatch(BaseModel):
    settings: dict[str, dict[str, Any]]


class ProposalRegisterRow(BaseModel):
    id: str
    proposal_reference: str
    proposal: str
    project_ref: Any | None = None
    client: str
    activity: str
    stage: str
    stage_code: str
    amount: Any | None = None
    last_activity: str | None = None
    location: str | None = None
    current_owner: str
    next_action: dict[str, Any]
    owner_lane: dict[str, Any]
    contract_eligible: bool
    validation: dict[str, Any]


class ProposalRegisterResponse(BaseModel):
    items: list[ProposalRegisterRow]
    rows: list[ProposalRegisterRow]
    count: int
    lane_counts: dict[str, int]
    lane_options: list[dict[str, Any]]
    predicate_version: str
    filters: dict[str, Any]
    stage_options: list[str]
    amount_source: str
    last_activity_source: str
    search_fields: list[str]
    synthetic_only: bool


def _actor(role: Role, supplied: str | None = None) -> str:
    return supplied or getattr(role, "value", str(role))


def _create_proposal_record(payload: ProposalCreate, request: Request, db: Session, role: Role) -> Opportunity:
    """Create the canonical Proposal row without committing a source transaction."""
    office = db.scalar(select(ConsultancyOffice).order_by(ConsultancyOffice.office_code))
    if not office:
        raise HTTPException(503, "OFFICE_CONTEXT_REQUIRED")
    client_id = payload.client_account_id
    if not client_id and payload.client_name:
        client = ClientAccount(client_reference=f"AMEC-SYN-CLIENT-{db.query(ClientAccount).count() + 1:04d}", legal_name=payload.client_name.strip(), display_name=payload.client_name.strip(), client_type="COMPANY", data_classification="SYNTHETIC", status="ACTIVE")
        db.add(client)
        db.flush()
        client_id = client.id
    reference = allocate_proposal_reference(db)
    fields = {"client_name": payload.client_name, "project_reference": payload.project_reference, "provenance": {"client_name": "manual", "project_reference": "manual"}}
    fields = {key: value for key, value in fields.items() if value is not None}
    item = Opportunity(office_id=office.id, client_account_id=client_id, opportunity_reference=reference, title=payload.proposal_description.strip(), status="IN_REVIEW", source_type="BD_WORKSPACE", project_id=payload.project_id, reference_state="CANONICAL" if payload.project_id else "PROVISIONAL", proposal_fields_json=fields, provisional_reference=reference, canonical_project_reference=payload.project_reference)
    db.add(item)
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_DRAFT_CREATED", entity_type="Opportunity", entity_id=item.id, actor_id=_actor(role), after={"proposal_reference": reference, "status": item.status})
    return item


def _list_row(db: Session, item: Opportunity) -> dict[str, Any]:
    projection = proposal_projection(db, item)
    client = db.get(ClientAccount, item.client_account_id) if item.client_account_id else None
    fields = item.proposal_fields_json or {}
    site = (projection.get("forms_v2") or {}).get("site_context") or {}
    client_label = projection["client_name"] or ((projection.get("forms_v2") or {}).get("commercial_client") or {}).get("display_name") or (client.display_name if client else None) or item.client_account_id or "Not recorded"
    location = site.get("location_text") or fields.get("location") or site.get("site_description") or ""
    activity = fields.get("project_description") or fields.get("activity") or item.title
    search_text = " ".join(str(value or "") for value in (item.title, item.opportunity_reference, projection["project_reference"], client_label, activity, fields.get("client_scope_of_work"), fields.get("scope_of_work") or fields.get("sow"), location, projection["stage_label"], item.status)).lower()
    return {"id": item.id, "proposal_reference": item.opportunity_reference, "proposal": item.title, "project_ref": projection["project_reference"], "client": client_label, "activity": activity, "stage": projection["stage_label"], "stage_code": item.status, "amount": projection["amount"], "last_activity": projection["last_activity"], "location": location or None, "current_owner": projection["current_owner"], "next_action": projection["next_action"], "owner_lane": projection["owner_lane"], "contract_eligible": projection["contract_eligible"], "validation": projection["validation"], "_search_text": search_text}


def _register_predicate(rows: list[dict[str, Any]], *, q: str, stage: str | None, lane: str | None, client: str | None, activity: str | None, location: str | None) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Single register predicate used for visible rows and lane counts."""
    needle = q.strip().lower()
    if needle:
        rows = [row for row in rows if needle in row["_search_text"]]
    if client and client.strip():
        client_needle = client.strip().lower()
        rows = [row for row in rows if client_needle in str(row.get("client") or "").lower()]
    if activity and activity.strip():
        activity_needle = activity.strip().lower()
        rows = [row for row in rows if activity_needle in str(row.get("activity") or "").lower() or activity_needle in row["_search_text"]]
    if stage:
        rows = [row for row in rows if row["stage_code"] == stage.upper()]
    if location and location.strip():
        location_needle = location.strip().lower()
        rows = [row for row in rows if location_needle in str(row.get("location") or "").lower()]
    definitions = owner_lane_definitions()
    lane_counts = {definition["code"]: sum(1 for row in rows if definition["code"] in row["owner_lane"]["memberships"]) for definition in definitions}
    if lane:
        lane_code = lane.upper()
        if lane_code not in {definition["code"] for definition in definitions}:
            raise HTTPException(422, {"code": "PROPOSAL_LANE_INVALID", "allowed": [definition["code"] for definition in definitions]})
        rows = [row for row in rows if lane_code in row["owner_lane"]["memberships"]]
    return rows, lane_counts


@router.post("/test-support/cleanup")
def cleanup_test_proposals(proposal_ids: list[str], db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    if app_settings().app_env.upper() != "TEST":
        raise HTTPException(404, "TEST_SUPPORT_NOT_AVAILABLE")
    require_capability(role, "BD_PROPOSAL_OWNER_SETTINGS")
    removed = []
    from ..services.proposals_sor import intake_sor_root
    from shutil import rmtree
    for proposal_id in proposal_ids:
        proposal = db.get(Opportunity, proposal_id)
        if not proposal:
            continue
        reference = proposal.opportunity_reference
        quotations = db.scalars(select(Quotation).where(Quotation.opportunity_id == proposal_id)).all()
        for quotation in quotations:
            contracts = db.scalars(select(Contract).where(Contract.quotation_id == quotation.id)).all()
            for contract in contracts:
                db.query(ContractRevision).filter(ContractRevision.contract_id == contract.id).delete(synchronize_session=False)
            db.query(Contract).filter(Contract.quotation_id == quotation.id).delete(synchronize_session=False)
            db.query(QuotationRevision).filter(QuotationRevision.quotation_id == quotation.id).delete(synchronize_session=False)
        db.query(Quotation).filter(Quotation.opportunity_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalExpectedInputPreview).filter(ProposalExpectedInputPreview.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalEngineeringContribution).filter(ProposalEngineeringContribution.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalExternalCostAssumption).filter(ProposalExternalCostAssumption.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalAssumption).filter(ProposalAssumption.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalUnknown).filter(ProposalUnknown.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalConflict).filter(ProposalConflict.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalMaterialAcknowledgment).filter(ProposalMaterialAcknowledgment.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalStalenessEvent).filter(ProposalStalenessEvent.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalRevision).filter(ProposalRevision.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalClientResponse).filter(ProposalClientResponse.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalCommercialOutcome).filter(ProposalCommercialOutcome.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalRegulatoryScopeIntent).filter(ProposalRegulatoryScopeIntent.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalServiceScopeItem).filter(ProposalServiceScopeItem.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalStakeholderIntent).filter(ProposalStakeholderIntent.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalSourceLink).filter(ProposalSourceLink.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalSiteContext).filter(ProposalSiteContext.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalContactContext).filter(ProposalContactContext.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalOutputArtifact).filter(ProposalOutputArtifact.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalAcceptedRevision).filter(ProposalAcceptedRevision.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalSourceEvidence).filter(ProposalSourceEvidence.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalIntakeArtifact).filter(ProposalIntakeArtifact.opportunity_id == proposal_id).delete(synchronize_session=False)
        task_ids = [task.id for task in db.scalars(select(WorkflowTask).where(WorkflowTask.context_type == "OPPORTUNITY", WorkflowTask.context_id == proposal_id)).all()]
        db.query(NotificationEvent).filter(NotificationEvent.workflow_task_id.in_(task_ids)).delete(synchronize_session=False) if task_ids else None
        db.query(AssistantHandoff).filter(AssistantHandoff.opportunity_id == proposal_id).delete(synchronize_session=False)
        db.query(WorkflowTask).filter(WorkflowTask.id.in_(task_ids)).delete(synchronize_session=False) if task_ids else None
        db.query(NotificationEvent).filter(NotificationEvent.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(AuditEvent).filter(AuditEvent.entity_id == proposal_id).delete(synchronize_session=False)
        client = db.get(ClientAccount, proposal.client_account_id) if proposal.client_account_id else None
        proposal.client_account_id = None
        db.delete(proposal)
        db.flush()
        if client and client.client_reference.startswith("AMEC-SYN-CLIENT-") and not db.scalar(select(Opportunity).where(Opportunity.client_account_id == client.id, Opportunity.id != proposal_id)):
            db.delete(client)
        rmtree(intake_sor_root() / reference, ignore_errors=True)
        removed.append(proposal_id)
    db.commit()
    return {"status": "APPLIED", "removed": removed}


@router.get("", response_model=ProposalRegisterResponse)
def list_proposals(q: str = "", stage: str | None = None, lane: str | None = None, client: str | None = None, activity: str | None = None, location: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    rows, lane_counts = _register_predicate([_list_row(db, item) for item in db.scalars(select(Opportunity).order_by(Opportunity.updated_at.desc(), Opportunity.opportunity_reference)).all()], q=q, stage=stage, lane=lane, client=client, activity=activity, location=location)
    for row in rows:
        row.pop("_search_text", None)
    return {"items": rows, "rows": rows, "count": len(rows), "lane_counts": lane_counts, "lane_options": owner_lane_definitions(), "predicate_version": "bd-proposal-register-v2", "filters": {"q": q, "stage": stage, "lane": lane, "client": client, "activity": activity, "location": location}, "stage_options": ["RECEIVED", "IN_REVIEW", "PROPOSAL_PREPARATION", "PROPOSAL_HANDOVER", "READY_FOR_QUOTATION", "COMMERCIAL_REVIEW", "QUOTATION_IN_PROGRESS", "CLIENT_RESPONSE_PENDING", "ACCEPTED", "CONTRACT_HANDOVER", "CLOSED"], "amount_source": "proposal_fields.price", "last_activity_source": "Opportunity.updated_at material Proposal activity timestamp", "search_fields": ["client_name", "proposal.title", "project_description", "client_scope_of_work", "scope_of_work", "site_context.location_text", "site_context.site_description", "proposal_reference", "project_reference", "stage"], "synthetic_only": True}


@router.post("")
def create_proposal(payload: ProposalCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    item = _create_proposal_record(payload, request, db, role)
    db.commit()
    return proposal_projection(db, item)


@router.get("/master-content")
def proposal_master_content(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    return {"proposal_template": master_content_purpose(db, "PROPOSAL_TEMPLATE"), "proposal_checklist": master_content_purpose(db, "PROPOSAL_CHECKLIST"), "definitions": {"lookup": "/api/definitions/lookup/{term}", "truth": "DASHBOARD_DEFINITIONS"}}


@router.get("/{proposal_id}/configuration")
def proposal_configuration_view(proposal_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    """Read-only Dashboard configuration consumed by this Proposal."""
    require_capability(role, "BD_PROPOSAL_READ")
    proposal = _proposal_or_404(proposal_id, db)
    return proposal_configuration(db, proposal)


@router.get("/{proposal_id}")
def get_proposal(proposal_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    item = db.get(Opportunity, proposal_id)
    if not item:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    return proposal_projection(db, item)


def _proposal_or_404(proposal_id: str, db: Session) -> Opportunity:
    item = db.get(Opportunity, proposal_id)
    if not item:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    return item


@router.put("/{proposal_id}/contact")
def put_contact(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    set_contact(db, proposal, payload, _actor(role))
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_CONTACT_UPDATED", entity_type="Opportunity", entity_id=proposal.id, actor_id=_actor(role), after={"purpose": payload.get("purpose", "PROPOSAL_CONTACT"), "party_linked": bool(payload.get("party_id"))})
    db.commit()
    return proposal_projection(db, proposal)


@router.put("/{proposal_id}/site-context")
def put_site_context(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    row = set_site_context(db, proposal, payload, _actor(role))
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_SITE_CONTEXT_UPDATED", entity_type="ProposalSiteContext", entity_id=row.id, actor_id=_actor(role), after={"status": row.status, "property_id": row.property_id, "area_kind": row.area_kind})
    db.commit()
    return proposal_projection(db, proposal)


@router.put("/{proposal_id}/client-party")
def link_client_party(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    client = db.get(ClientAccount, proposal.client_account_id) if proposal.client_account_id else None
    party_id = payload.get("canonical_party_id")
    if not client or not party_id:
        raise HTTPException(422, {"code": "COMMERCIAL_CLIENT_AND_PARTY_REQUIRED"})
    if not db.get(__import__("backend.app.models", fromlist=["Party"]).Party, party_id):
        raise HTTPException(422, {"code": "PARTY_NOT_FOUND", "party_id": party_id})
    client.canonical_party_id = party_id
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_CLIENT_PARTY_LINKED", entity_type="ClientAccount", entity_id=client.id, actor_id=_actor(role), after={"canonical_party_id": party_id})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/stakeholders")
def add_stakeholder(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    if payload.get("party_id") and not db.get(__import__("backend.app.models", fromlist=["Party"]).Party, payload["party_id"]):
        raise HTTPException(422, {"code": "PARTY_NOT_FOUND", "party_id": payload["party_id"]})
    row = ProposalStakeholderIntent(proposal_id=proposal.id, role_code=payload.get("role_code", "OTHER"), party_id=payload.get("party_id"), display_snapshot=payload.get("display_snapshot"), status=payload.get("status", "UNKNOWN"), source_type=payload.get("source_type", "HUMAN_ENTERED"), source_document_version_id=payload.get("source_document_version_id"), note=payload.get("note"))
    db.add(row)
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_STAKEHOLDER_INTENT_UPDATED", entity_type="ProposalStakeholderIntent", entity_id=row.id, actor_id=_actor(role), after={"role_code": row.role_code, "status": row.status, "party_linked": bool(row.party_id)})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/source-links")
def link_source_version(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    row = add_source_link(db, proposal, payload, _actor(role))
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_SOURCE_VERSION_LINKED", entity_type="ProposalSourceLink", entity_id=row.id, actor_id=_actor(role), after={"document_version_id": row.document_version_id, "source_role": row.source_role})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/scope-items")
def add_scope_item(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    if not str(payload.get("description") or "").strip():
        raise HTTPException(422, {"code": "SCOPE_DESCRIPTION_REQUIRED"})
    row = ProposalServiceScopeItem(proposal_id=proposal.id, service_offering_code=payload.get("service_offering_code"), scope_category_code=payload.get("scope_category_code"), discipline_code=payload.get("discipline_code"), description=payload["description"].strip(), included=bool(payload.get("included", True)), commercial_treatment=payload.get("commercial_treatment", "AMEC_FEE"), regulatory_service_type_id=payload.get("regulatory_service_type_id"), external_body_id=payload.get("external_body_id"), source_document_version_id=payload.get("source_document_version_id"), rationale=payload.get("rationale"), sort_order=int(payload.get("sort_order", 100)), status=payload.get("status", "DRAFT"))
    db.add(row)
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_SERVICE_SCOPE_UPDATED", entity_type="ProposalServiceScopeItem", entity_id=row.id, actor_id=_actor(role), after={"description": row.description, "included": row.included})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/regulatory-scope")
def add_regulatory_scope(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    for model, key, code in (("external_body_id", "ExternalBody", "EXTERNAL_BODY_NOT_FOUND"), ("service_type_id", "ServiceType", "SERVICE_TYPE_NOT_FOUND"), ("jurisdiction_id", "Jurisdiction", "JURISDICTION_NOT_FOUND")):
        if payload.get(model) and not db.get(__import__("backend.app.models", fromlist=[key]).__dict__[key], payload[model]):
            raise HTTPException(422, {"code": code, "id": payload[model]})
    row = ProposalRegulatoryScopeIntent(proposal_id=proposal.id, proposal_scope_item_id=payload.get("proposal_scope_item_id"), external_body_id=payload.get("external_body_id"), service_type_id=payload.get("service_type_id"), service_type_version_id=payload.get("service_type_version_id"), jurisdiction_id=payload.get("jurisdiction_id"), status=payload.get("status", "DRAFT"), source_type=payload.get("source_type", "HUMAN_ENTERED"), source_document_version_id=payload.get("source_document_version_id"), source_assertion_id=payload.get("source_assertion_id"), rationale=payload.get("rationale"), confidence=payload.get("confidence"), notes=payload.get("notes"))
    db.add(row)
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_REGULATORY_SCOPE_INTENT_CREATED", entity_type="ProposalRegulatoryScopeIntent", entity_id=row.id, actor_id=_actor(role), after={"status": row.status, "external_body_id": row.external_body_id, "service_type_id": row.service_type_id, "jurisdiction_id": row.jurisdiction_id})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/regulatory-scope/{intent_id}/confirm")
def confirm_regulatory_scope(proposal_id: str, intent_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    row = db.get(ProposalRegulatoryScopeIntent, intent_id)
    if not row or row.proposal_id != proposal.id:
        raise HTTPException(404, "REGULATORY_SCOPE_INTENT_NOT_FOUND")
    if not row.service_type_id:
        raise domain_error(409, "REGULATORY_SCOPE_SERVICE_REQUIRED")
    row.status = "HUMAN_CONFIRMED_FOR_PROPOSAL"
    row.human_confirmed_by = _actor(role)
    row.human_confirmed_at = datetime.now(timezone.utc)
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_REGULATORY_SCOPE_CONFIRMED", entity_type="ProposalRegulatoryScopeIntent", entity_id=row.id, actor_id=_actor(role), after={"status": row.status, "authority_case_created": False})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/assumptions")
def add_assumption(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    if not str(payload.get("statement") or "").strip():
        raise HTTPException(422, {"code": "ASSUMPTION_STATEMENT_REQUIRED"})
    row = ProposalAssumption(proposal_id=proposal.id, category=payload.get("category", "COMMERCIAL"), statement=payload["statement"].strip(), materiality=payload.get("materiality", "INFORMATIONAL"), source_type=payload.get("source_type", "HUMAN_ENTERED"), source_reference=payload.get("source_reference"), status="OPEN")
    db.add(row)
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_ASSUMPTION_CREATED", entity_type="ProposalAssumption", entity_id=row.id, actor_id=_actor(role), after={"materiality": row.materiality})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/assumptions/{assumption_id}/acknowledge")
def acknowledge_assumption(proposal_id: str, assumption_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_ACCEPT")
    proposal = _proposal_or_404(proposal_id, db)
    row = db.get(ProposalAssumption, assumption_id)
    if not row or row.proposal_id != proposal.id:
        raise HTTPException(404, "ASSUMPTION_NOT_FOUND")
    row.status = "ACKNOWLEDGED"
    row.acknowledged_by = _actor(role)
    row.acknowledged_at = datetime.now(timezone.utc)
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_ASSUMPTION_ACKNOWLEDGED", entity_type="ProposalAssumption", entity_id=row.id, actor_id=_actor(role), after={"status": row.status})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/unknowns")
def add_unknown(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    statement = str(payload.get("statement") or "").strip()
    if not statement:
        raise HTTPException(422, {"code": "UNKNOWN_STATEMENT_REQUIRED"})
    row = ProposalUnknown(proposal_id=proposal.id, category=str(payload.get("category") or "COMMERCIAL"), statement=statement, materiality=str(payload.get("materiality") or "INFORMATIONAL"), source_type=str(payload.get("source_type") or "HUMAN_ENTERED"), source_reference=payload.get("source_reference"), status="OPEN")
    db.add(row)
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_UNKNOWN_RECORDED", entity_type="ProposalUnknown", entity_id=row.id, actor_id=_actor(role), after={"materiality": row.materiality, "status": row.status})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/conflicts")
def add_conflict(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    for key in ("field_code", "source_a", "source_b"):
        if not str(payload.get(key) or "").strip():
            raise HTTPException(422, {"code": f"CONFLICT_{key.upper()}_REQUIRED"})
    row = ProposalConflict(proposal_id=proposal.id, field_code=str(payload["field_code"]), source_a=str(payload["source_a"]), value_a=payload.get("value_a"), source_b=str(payload["source_b"]), value_b=payload.get("value_b"), materiality=str(payload.get("materiality") or "MATERIAL"), status="OPEN")
    db.add(row)
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_CONFLICT_RECORDED", entity_type="ProposalConflict", entity_id=row.id, actor_id=_actor(role), after={"field_code": row.field_code, "materiality": row.materiality, "status": row.status})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/acknowledgments")
def acknowledge_material_item(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_ACCEPT")
    proposal = _proposal_or_404(proposal_id, db)
    target_type = str(payload.get("target_type") or "").upper()
    target_id = str(payload.get("target_id") or "")
    if target_type not in {"PROPOSAL_ASSUMPTION", "PROPOSAL_UNKNOWN", "PROPOSAL_CONFLICT"} or not target_id:
        raise HTTPException(422, {"code": "MATERIAL_ACK_TARGET_REQUIRED"})
    targets = {"PROPOSAL_ASSUMPTION": ProposalAssumption, "PROPOSAL_UNKNOWN": ProposalUnknown, "PROPOSAL_CONFLICT": ProposalConflict}
    target = db.get(targets[target_type], target_id)
    if not target or target.proposal_id != proposal.id:
        raise HTTPException(404, "MATERIAL_ACK_TARGET_NOT_FOUND")
    target_hash = stable_hash({key: getattr(target, key) for key in ("id", "materiality", "status")})
    row = db.scalar(select(ProposalMaterialAcknowledgment).where(ProposalMaterialAcknowledgment.proposal_id == proposal.id, ProposalMaterialAcknowledgment.target_type == target_type, ProposalMaterialAcknowledgment.target_id == target_id))
    if not row:
        row = ProposalMaterialAcknowledgment(proposal_id=proposal.id, target_type=target_type, target_id=target_id, target_revision_hash=target_hash, acknowledged_by=_actor(role), note=payload.get("note"))
        db.add(row)
    elif row.target_revision_hash != target_hash:
        row.target_revision_hash = target_hash
        row.acknowledged_by = _actor(role)
        row.acknowledged_at = hardening_now()
        row.note = payload.get("note")
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_MATERIAL_ACKNOWLEDGED", entity_type="ProposalMaterialAcknowledgment", entity_id=row.id, actor_id=_actor(role), after={"target_type": target_type, "target_id": target_id, "acknowledged_is_not_resolved": True})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/staleness/review")
def review_proposal_staleness(proposal_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    active = db.scalars(select(ProposalStalenessEvent).where(ProposalStalenessEvent.proposal_id == proposal.id, ProposalStalenessEvent.status == "ACTIVE")).all()
    for item in active:
        item.status = "CLEARED"
        item.cleared_by = _actor(role)
        item.cleared_at = hardening_now()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_STALENESS_REVIEWED", entity_type="Opportunity", entity_id=proposal.id, actor_id=_actor(role), after={"cleared_event_ids": [item.id for item in active]})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/external-costs")
def add_external_cost(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    row = ProposalExternalCostAssumption(proposal_id=proposal.id, description=payload.get("description", "External cost estimate"), external_body_id=payload.get("external_body_id"), estimated_amount=payload.get("estimated_amount"), currency=payload.get("currency"), treatment=payload.get("treatment", "ESTIMATE_ONLY"), source_reference=payload.get("source_reference"), rationale=payload.get("rationale"))
    db.add(row)
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_EXTERNAL_COST_ADDED", entity_type="ProposalExternalCostAssumption", entity_id=row.id, actor_id=_actor(role), after={"treatment": row.treatment, "estimated_amount": row.estimated_amount})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/engineering-contributions")
def add_engineering_contribution(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "EDIT_TECHNICAL")
    proposal = _proposal_or_404(proposal_id, db)
    if not str(payload.get("content") or "").strip():
        raise HTTPException(422, {"code": "ENGINEERING_CONTRIBUTION_REQUIRED"})
    row = ProposalEngineeringContribution(proposal_id=proposal.id, discipline_code=payload.get("discipline_code"), contribution_type=payload.get("contribution_type", "TECHNICAL_SCOPE"), content=payload["content"].strip(), technical_rule_set_version_id=payload.get("technical_rule_set_version_id"), source_document_version_id=payload.get("source_document_version_id"), contributed_by=_actor(role))
    db.add(row)
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_ENGINEERING_CONTRIBUTION_ADDED", entity_type="ProposalEngineeringContribution", entity_id=row.id, actor_id=_actor(role), after={"discipline_code": row.discipline_code, "commercial_price_changed": False, "proposal_accepted": False})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/expected-client-inputs/preview")
def refresh_expected_client_inputs(proposal_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    create_preview(db, proposal, _actor(role), request.state.correlation_id)
    db.commit()
    return proposal_projection(db, proposal)


@router.get("/{proposal_id}/readiness")
def proposal_readiness(proposal_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    proposal = _proposal_or_404(proposal_id, db)
    return v2_readiness(db, proposal, validate_proposal(db, proposal))


@router.get("/{proposal_id}/intake-readiness")
def proposal_intake_readiness(proposal_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    return intake_readiness(db, _proposal_or_404(proposal_id, db))


@router.patch("/{proposal_id}")
def patch_proposal(proposal_id: str, payload: ProposalFieldsPatch, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    technical_keys = {"scope_of_work", "sow", "process_of_work", "technical_assumptions", "technical_deliverables"}
    field_keys = set((payload.fields or {}).keys())
    if role == Role.RESPONSIBLE_ENGINEER and field_keys and field_keys <= technical_keys and payload.amec_input is None and payload.provenance is None:
        require_capability(role, "EDIT_TECHNICAL")
    else:
        require_capability(role, "BD_PROPOSAL_WRITE")
    item = db.get(Opportunity, proposal_id)
    if not item:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    if payload.expected_updated_at:
        try:
            expected = datetime.fromisoformat(payload.expected_updated_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HTTPException(422, {"code": "EXPECTED_UPDATED_AT_INVALID"}) from exc
        actual = item.updated_at
        if actual and actual != expected:
            raise domain_error(409, "PROPOSAL_DRAFT_CHANGED", expected_updated_at=payload.expected_updated_at, actual_updated_at=actual.isoformat())
    current = dict(item.proposal_fields_json or {})
    current.update(payload.fields or {})
    if payload.amec_input is not None:
        current["amec_input"] = payload.amec_input
    if payload.provenance is not None:
        current["provenance"] = {**(current.get("provenance") or {}), **payload.provenance}
    item.proposal_fields_json = current
    item.status = item.status if item.status not in {"RECEIVED", "IN_REVIEW"} else "IN_REVIEW"
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_FIELDS_UPDATED", entity_type="Opportunity", entity_id=item.id, actor_id=_actor(role), after={"field_keys": sorted(payload.fields.keys()), "amec_input_updated": payload.amec_input is not None, "authority": "EDIT_TECHNICAL" if role == Role.RESPONSIBLE_ENGINEER else "BD_PROPOSAL_WRITE"})
    db.commit()
    return proposal_projection(db, item)


@router.post("/{proposal_id}/notes")
def add_note(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    content = str(payload.get("content") or "").strip()
    if not content:
        raise HTTPException(422, {"code": "NOTE_CONTENT_REQUIRED"})
    note = ProposalNote(proposal_id=proposal.id, note_type=str(payload.get("note_type") or "INTERNAL_INTAKE"), content=content, entered_by=_actor(role, payload.get("entered_by")), related_contact=payload.get("related_contact"), provenance={"kind": "human_note", "source": "client_conversation" if str(payload.get("note_type") or "").startswith(("CALL", "MEETING", "CLIENT")) else "internal_intake", "verification": "UNVERIFIED_CONTEXT"})
    db.add(note)
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_NOTE_ADDED", entity_type="ProposalNote", entity_id=note.id, actor_id=note.entered_by, after={"note_type": note.note_type, "verified_fact": False})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/site-photos")
async def add_site_photo(proposal_id: str, request: Request, file: UploadFile = File(...), source_revision: str | None = Form(default=None), actor: str | None = Form(default=None), idempotency_key: str | None = Form(default=None), db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    content = await file.read()
    if not content:
        raise HTTPException(422, {"code": "SITE_PHOTO_EMPTY"})
    digest = hashlib.sha256(content).hexdigest()
    existing = db.scalar(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id, ProposalSourceEvidence.source_type == "SITE_PHOTO", ProposalSourceEvidence.content_hash == digest))
    if not existing:
        existing = ProposalSourceEvidence(proposal_id=proposal.id, source_type="SITE_PHOTO", source_filename=file.filename or "site-photo", source_reference=f"synthetic://proposal-site-photo/{proposal.opportunity_reference}/{digest}", content_hash=digest, content_type=file.content_type or "image/*", source_revision=source_revision, provenance={"kind": "site_context", "semantic_class": "SITE_PROJECT_PHOTO", "verification": "READ_BACK_VERIFIED", "idempotency_key": idempotency_key}, status="CURRENT", verification_state="READ_BACK_VERIFIED", created_by=_actor(role, actor))
        db.add(existing)
        db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_SITE_PHOTO_REGISTERED", entity_type="ProposalSourceEvidence", entity_id=existing.id, actor_id=_actor(role, actor), after={"source_type": "SITE_PHOTO", "content_hash": digest})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/proceed")
def proceed_to_engineering(proposal_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), actor: str | None = None):
    require_capability(role, "PROCEED")
    proposal = _proposal_or_404(proposal_id, db)
    if proposal.status == "PROPOSAL_PREPARATION":
        task = db.scalar(select(WorkflowTask).where(WorkflowTask.context_type == "OPPORTUNITY", WorkflowTask.context_id == proposal.id, WorkflowTask.task_type == "PROPOSAL_PREPARATION", WorkflowTask.status.in_((WorkflowTaskStatus.OPEN, WorkflowTaskStatus.IN_PROGRESS))).order_by(WorkflowTask.created_at.desc()))
        return {"result": "IDEMPOTENT", "proposal": proposal_projection(db, proposal), "handoff": {"task_id": task.id if task else None, "created": False}, "next_route": f"/proposals/{proposal.id}/preparation"}
    if proposal.status not in {"RECEIVED", "IN_REVIEW"}:
        raise domain_error(409, "PROPOSAL_NOT_IN_INTAKE", status=proposal.status)
    readiness = intake_readiness(db, proposal)
    if not readiness["ready"]:
        raise domain_error(409, "PROPOSAL_INTAKE_BLOCKED", blockers=readiness["blockers"], warnings=readiness["warnings"])
    from .proposals_main_routers import _create_handoff_task
    current_source = db.scalar(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id, ProposalSourceEvidence.status == "CURRENT").order_by(ProposalSourceEvidence.created_at.desc()))
    proposal.status = "PROPOSAL_PREPARATION"
    handoff = _create_handoff_task(db, action="NEW_PROPOSAL", project_id=proposal.project_id, opportunity_id=proposal.id, correlation_id=request.state.correlation_id, actor=_actor(role, actor), artifact_id=current_source.id if current_source else "SOURCE_EVIDENCE")
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_PROCEEDED_TO_ENGINEERING", entity_type="Opportunity", entity_id=proposal.id, actor_id=_actor(role, actor), after={"status": proposal.status, "handoff": handoff, "next_actor": "Engineering"})
    db.commit()
    return {"result": "TRANSITIONED", "proposal": proposal_projection(db, proposal), "handoff": handoff, "next_route": f"/proposals/{proposal.id}/preparation"}


async def _register_source_content(*, proposal: Opportunity, request: Request, source_type: str, source_filename: str, content_type: str, content: bytes, source_revision: str | None, actor: str, idempotency_key: str | None, source_metadata: dict[str, Any] | None, db: Session, role: Role) -> dict[str, Any]:
    source_type = source_type.upper()
    if source_type not in SOURCE_TYPES:
        raise HTTPException(422, {"code": "SOURCE_TYPE_REQUIRED", "allowed": list(SOURCE_TYPES)})
    semantic = SOURCE_TO_SEMANTIC[source_type]
    digest = hashlib.sha256(content).hexdigest()
    # Vercel TEST has durable PostgreSQL but a read-only deployment bundle.
    # Preserve the verified source index and hash there; local TEST continues
    # to exercise the MockSynologyAdapter filesystem path.
    if app_settings().app_env.upper() == "TEST" and os.environ.get("VERCEL"):
        result = {"id": str(uuid4()), "source_filename": source_filename, "sor_path": f"synthetic://proposal-source/{proposal.opportunity_reference}/{source_type.lower()}/{digest}", "content_hash": digest, "verification_state": "READ_BACK_VERIFIED", "semantic_class": semantic}
    else:
        result = ingest_provisional_intake_artifact(db, opportunity=proposal, semantic_class=semantic, source_filename=source_filename, content_type=content_type, content=content, actor=actor, source_revision=source_revision, idempotency_key=idempotency_key, correlation_id=request.state.correlation_id)
    existing = db.scalar(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id, ProposalSourceEvidence.source_type == source_type, ProposalSourceEvidence.status == "CURRENT").order_by(ProposalSourceEvidence.created_at.desc()))
    if existing and existing.content_hash != digest:
        existing.status = "CONFLICT"
        db.add(ProposalStalenessEvent(proposal_id=proposal.id, trigger_type="SOURCE_VERSION", trigger_reference=f"{source_type}:{digest}", reason_code="SOURCE_VERSION_CHANGED", impacted_sections=impacted_sections_for_source(source_type), status="ACTIVE", detected_by=_actor(role, actor)))
    evidence = db.scalar(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id, ProposalSourceEvidence.source_type == source_type, ProposalSourceEvidence.content_hash == digest))
    if not evidence:
        evidence = ProposalSourceEvidence(proposal_id=proposal.id, source_type=source_type, source_filename=result["source_filename"], source_reference=result["sor_path"], content_hash=digest, content_type=content_type, source_revision=source_revision, provenance={"kind": "source", "source_artifact_id": result["id"], "semantic_class": semantic, "verification": result["verification_state"], **(source_metadata or {})}, conflict_key=source_type, status="CURRENT", verification_state=result["verification_state"], supersedes_id=existing.id if existing else None, created_by=actor)
        db.add(evidence)
        db.flush()
    document = db.scalar(select(Document).where(Document.logical_name == f"{proposal.opportunity_reference}:{source_type}:{digest}"))
    if not document:
        document = Document(project_id=proposal.project_id, document_type=DocumentType.OTHER, logical_name=f"{proposal.opportunity_reference}:{source_type}:{digest}", language="EN", source_system="PROPOSAL_INTAKE", current_version_id=None)
        db.add(document)
        db.flush()
        version = DocumentVersion(document_id=document.id, version_number=1, source_filename=result["source_filename"], source_path_or_reference=result["sor_path"], sha256=digest, mime_type=content_type, file_size=len(content), language="EN", revision_label=source_revision, approval_state=DocumentApprovalState.WORKING, source_system="PROPOSAL_INTAKE")
        db.add(version)
        db.flush()
        document.current_version_id = version.id
    else:
        version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document.id, DocumentVersion.sha256 == digest))
        if not version:
            next_version = (db.scalar(select(DocumentVersion.version_number).where(DocumentVersion.document_id == document.id).order_by(DocumentVersion.version_number.desc())) or 0) + 1
            version = DocumentVersion(document_id=document.id, version_number=next_version, source_filename=result["source_filename"], source_path_or_reference=result["sor_path"], sha256=digest, mime_type=content_type, file_size=len(content), language="EN", revision_label=source_revision, approval_state=DocumentApprovalState.WORKING, source_system="PROPOSAL_INTAKE")
            db.add(version)
            db.flush()
            document.current_version_id = version.id
    if not db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal.id, ProposalSourceLink.document_version_id == version.id, ProposalSourceLink.source_role == source_type)):
        db.add(ProposalSourceLink(proposal_id=proposal.id, source_evidence_id=evidence.id, document_id=document.id, document_version_id=version.id, source_role=source_type, added_by=_actor(role, actor)))
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_SOURCE_REGISTERED", entity_type="Opportunity", entity_id=proposal.id, actor_id=actor, after={"source_type": source_type, "source_evidence_id": evidence.id, "content_hash": digest, "conflict": bool(existing and existing.content_hash != digest), "initial_source": bool(source_metadata and source_metadata.get("initial_source"))})
    return {"source": {"id": evidence.id, "source_type": evidence.source_type, "content_hash": evidence.content_hash, "verification_state": evidence.verification_state, "status": evidence.status, "source_reference": evidence.source_reference}}


@router.post("/intake")
async def create_proposal_intake(request: Request, proposal_description: str = Form(...), project_reference: str | None = Form(default=None), client_name: str | None = Form(default=None), client_account_id: str | None = Form(default=None), project_id: str | None = Form(default=None), initial_source_type: str | None = Form(default=None), source_title: str | None = Form(default=None), source_date: str | None = Form(default=None), source_notes: str | None = Form(default=None), source_revision: str | None = Form(default=None), file: UploadFile | None = File(default=None), db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    """Create a Proposal and its optional initial source in one DB transaction."""
    require_capability(role, "BD_PROPOSAL_WRITE")
    source_type = initial_source_type.upper() if initial_source_type else None
    if source_type and source_type not in SOURCE_TYPES:
        raise HTTPException(422, {"code": "SOURCE_TYPE_REQUIRED", "allowed": list(SOURCE_TYPES)})
    if source_type and not file:
        raise HTTPException(422, {"code": "INITIAL_SOURCE_FILE_REQUIRED", "source_type": source_type})
    proposal = _create_proposal_record(ProposalCreate(proposal_description=proposal_description, project_reference=project_reference, client_account_id=client_account_id, client_name=client_name, project_id=project_id), request, db, role)
    result: dict[str, Any] = {}
    try:
        if source_type and file:
            content = await file.read()
            if not content:
                raise HTTPException(422, {"code": "INITIAL_SOURCE_FILE_EMPTY", "source_type": source_type})
            result = await _register_source_content(proposal=proposal, request=request, source_type=source_type, source_filename=file.filename or source_title or "source.bin", content_type=file.content_type or "application/octet-stream", content=content, source_revision=source_revision, actor=_actor(role), idempotency_key=None, source_metadata={"initial_source": True, "title": source_title, "source_date": source_date, "notes": source_notes}, db=db, role=role)
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {**result, "proposal": proposal_projection(db, proposal), "next_route": f"/opportunities/{proposal.id}"}


@router.post("/{proposal_id}/sources")
async def add_source(proposal_id: str, request: Request, source_type: str = Form(...), file: UploadFile = File(...), source_revision: str | None = Form(default=None), actor: str | None = Form(default=None), idempotency_key: str | None = Form(default=None), db: Session = Depends(get_db), role: Role = Depends(current_user_role), x_synthetic_sor: str | None = Header(default=None)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = db.get(Opportunity, proposal_id)
    if not proposal:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    content = await file.read()
    result = await _register_source_content(proposal=proposal, request=request, source_type=source_type, source_filename=file.filename or "source.bin", content_type=file.content_type or "application/octet-stream", content=content, source_revision=source_revision, actor=_actor(role, actor), idempotency_key=idempotency_key, source_metadata=None, db=db, role=role)
    db.commit()
    return {**result, "proposal": proposal_projection(db, proposal)}


@router.get("/{proposal_id}/validation")
def validation(proposal_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    item = db.get(Opportunity, proposal_id)
    if not item:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    return validate_proposal(db, item)


@router.post("/{proposal_id}/accept")
def accept(proposal_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), actor: str | None = None):
    require_capability(role, "BD_PROPOSAL_ACCEPT")
    accept_authority = runtime_decision_value(db, "PROPOSAL_ACCEPT_AUTHORITY", "OWNER_OR_AUTHORIZED_COMMERCIAL_APPROVER")
    if accept_authority == "OWNER_ONLY" and role not in {Role.SYSTEM_ADMIN, Role.OWNER_SPONSOR}:
        raise domain_error(403, "PROPOSAL_ACCEPT_OWNER_ONLY")
    item = db.scalar(select(Opportunity).where(Opportunity.id == proposal_id).with_for_update())
    if not item:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    draft_revision = db.scalar(select(ProposalRevision).where(ProposalRevision.proposal_id == item.id, ProposalRevision.status == "DRAFT").order_by(ProposalRevision.revision_number.desc()))
    allowed_accept_stages = {"PROPOSAL_HANDOVER", "READY_FOR_QUOTATION", "QUOTATION_IN_PROGRESS", "COMMERCIAL_REVIEW", "CLIENT_RESPONSE_PENDING"}
    if item.status not in allowed_accept_stages and not (item.status == "ACCEPTED" and draft_revision):
        raise domain_error(409, "PROPOSAL_ACCEPT_STAGE_BLOCKED", stage=item.status, required_stages=sorted(allowed_accept_stages))
    check = validate_proposal(db, item)
    v2_check = v2_readiness(db, item, check)
    if not check["ready"] or not v2_check["ready"]:
        raise domain_error(409, "PROPOSAL_ACCEPT_BLOCKED", blockers=check["blockers"] + v2_check["blocking"], warnings=check["warnings"] + v2_check["warnings"])
    snapshot = snapshot_for_accept(db, item, check)
    prior = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == item.id).order_by(ProposalAcceptedRevision.revision_number.desc()))
    if prior and snapshot.get("material_fingerprint") == (prior.snapshot or {}).get("material_fingerprint"):
        raise domain_error(409, "PROPOSAL_ALREADY_ACCEPTED", accepted_revision_id=prior.id, revision_number=prior.revision_number)
    revision_number = (prior.revision_number + 1) if prior else 1
    content_hash = stable_hash(snapshot)
    revision = ProposalAcceptedRevision(proposal_id=item.id, revision_number=revision_number, snapshot=snapshot, validation_snapshot={**check, "readiness_v2": v2_check}, template_ref=check["template"]["item"]["ref"], template_version_id=check["template"]["item"]["version_id"], template_version=str(check["template"]["item"]["version"]), template_hash=check["template"]["item"]["hash"], checklist_ref=check["checklist"]["item"]["ref"], checklist_version_id=check["checklist"]["item"]["version_id"], checklist_version=str(check["checklist"]["item"]["version"]), checklist_hash=check["checklist"]["item"]["hash"], definition_refs=[item["ref"] for item in check["definitions"]], content_hash=content_hash, accepted_by=_actor(role, actor), supersedes_revision_id=prior.id if prior else None)
    db.add(revision)
    db.flush()
    draft = db.scalar(select(ProposalRevision).where(ProposalRevision.proposal_id == item.id, ProposalRevision.status == "DRAFT").order_by(ProposalRevision.revision_number.desc()))
    if draft:
        draft.status = "ACCEPTED"
        draft.snapshot = snapshot
        draft.content_hash = content_hash
    for artifact_type, filename in (("PROPOSAL", f"{item.opportunity_reference}-r{revision_number}-proposal.txt"), ("CHECKLIST", f"{item.opportunity_reference}-r{revision_number}-checklist.txt")):
        content = output_bytes(revision, artifact_type)
        db.add(ProposalOutputArtifact(revision_id=revision.id, proposal_id=item.id, artifact_type=artifact_type, filename=filename, content_type="text/plain", content_hash=hashlib.sha256(content).hexdigest(), storage_reference=f"synthetic://proposal-output/{revision.id}/{artifact_type.lower()}", lineage={"accepted_revision_id": revision.id, "proposal_content_hash": content_hash, "template_version_id": revision.template_version_id, "checklist_version_id": revision.checklist_version_id, "source_ids": snapshot["source_ids"], "format": "SYNTHETIC_TEXT", "renderer": "SYNTHETIC_JSON_RENDERER_V1", "generated_by": _actor(role, actor), "read_back_verified": True}, file_size=len(content), synthetic_only=True))
    item.status = "ACCEPTED"
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_HUMAN_ACCEPTED", entity_type="Opportunity", entity_id=item.id, actor_id=_actor(role, actor), after={"accepted_revision_id": revision.id, "revision_number": revision_number, "content_hash": content_hash, "machine_accept": False})
    db.commit()
    return proposal_projection(db, item)


@router.post("/{proposal_id}/revisions")
def create_proposal_revision(proposal_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    item = _proposal_or_404(proposal_id, db)
    prior = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == item.id).order_by(ProposalAcceptedRevision.revision_number.desc()))
    if not prior:
        raise domain_error(409, "ACCEPTED_REVISION_REQUIRED")
    latest_draft = db.scalar(select(ProposalRevision).where(ProposalRevision.proposal_id == item.id, ProposalRevision.status == "DRAFT").order_by(ProposalRevision.revision_number.desc()))
    if latest_draft:
        return {"result": "IDEMPOTENT", "revision": {"id": latest_draft.id, "revision_number": latest_draft.revision_number, "status": latest_draft.status, "base_accepted_revision_id": latest_draft.base_accepted_revision_id, "change_summary": latest_draft.change_summary, "content_hash": latest_draft.content_hash}, "proposal": proposal_projection(db, item)}
    revision_number = max(prior.revision_number, db.scalar(select(ProposalRevision.revision_number).where(ProposalRevision.proposal_id == item.id).order_by(ProposalRevision.revision_number.desc())) or 0) + 1
    summary = (payload or {}).get("change_summary") or {"created_from": prior.id, "reason": (payload or {}).get("reason") or "New Proposal revision requested"}
    snapshot = dict(prior.snapshot or {})
    snapshot["revision_candidate"] = revision_number
    snapshot["revision_created_at"] = hardening_now().isoformat()
    row = ProposalRevision(proposal_id=item.id, revision_number=revision_number, base_accepted_revision_id=prior.id, status="DRAFT", change_summary=summary, snapshot=snapshot, content_hash=stable_hash(snapshot), created_by=_actor(role))
    db.add(row)
    db.flush()
    audit(db, correlation_id=request.state.correlation_id if request else "proposal-revision", event_type="BD_PROPOSAL_REVISION_CREATED", entity_type="ProposalRevision", entity_id=row.id, actor_id=_actor(role), after={"revision_number": revision_number, "base_accepted_revision_id": prior.id})
    db.commit()
    return {"result": "CREATED", "revision": {"id": row.id, "revision_number": row.revision_number, "status": row.status, "base_accepted_revision_id": row.base_accepted_revision_id, "change_summary": row.change_summary, "content_hash": row.content_hash}, "proposal": proposal_projection(db, item)}


@router.post("/{proposal_id}/client-responses")
def record_client_response(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    item = _proposal_or_404(proposal_id, db)
    if item.status not in {"ACCEPTED", "CLIENT_RESPONSE_PENDING"}:
        raise domain_error(409, "CLIENT_RESPONSE_STAGE_BLOCKED", stage=item.status, required_stages=["ACCEPTED", "CLIENT_RESPONSE_PENDING"])
    response_type = str(payload.get("response_type") or "").upper()
    allowed = {"ACCEPTED", "DECLINED", "CHANGE_REQUESTED", "EXPIRED", "WITHDRAWN", "PENDING"}
    if response_type not in allowed:
        raise HTTPException(422, {"code": "CLIENT_RESPONSE_TYPE_INVALID", "allowed": sorted(allowed)})
    idempotency_key = str(payload.get("idempotency_key") or f"client-response:{item.id}:{response_type}:{payload.get('evidence_reference') or ''}")
    existing = db.scalar(select(ProposalClientResponse).where(ProposalClientResponse.idempotency_key == idempotency_key))
    if existing:
        return {"result": "IDEMPOTENT", "response": {"id": existing.id, "response_type": existing.response_type, "recorded_by": existing.recorded_by, "recorded_at": existing.recorded_at.isoformat()}, "proposal": proposal_projection(db, item)}
    accepted = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == item.id).order_by(ProposalAcceptedRevision.revision_number.desc()))
    row = ProposalClientResponse(proposal_id=item.id, accepted_revision_id=accepted.id if accepted else None, response_type=response_type, evidence_reference=payload.get("evidence_reference"), notes=payload.get("notes"), recorded_by=_actor(role), idempotency_key=idempotency_key)
    db.add(row)
    if response_type in {"PENDING", "CHANGE_REQUESTED"}:
        item.status = "CLIENT_RESPONSE_PENDING"
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_CLIENT_RESPONSE_RECORDED", entity_type="ProposalClientResponse", entity_id=row.id, actor_id=_actor(role), after={"response_type": response_type, "accepted_revision_id": row.accepted_revision_id, "amec_accept_is_not_client_accept": True})
    db.commit()
    return {"result": "RECORDED", "response": {"id": row.id, "response_type": row.response_type, "recorded_by": row.recorded_by, "recorded_at": row.recorded_at.isoformat()}, "proposal": proposal_projection(db, item)}


@router.post("/{proposal_id}/commercial-outcome")
def record_commercial_outcome(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    item = _proposal_or_404(proposal_id, db)
    if item.status != "CLIENT_RESPONSE_PENDING":
        raise domain_error(409, "COMMERCIAL_OUTCOME_STAGE_BLOCKED", stage=item.status, required_stages=["CLIENT_RESPONSE_PENDING"])
    outcome = str(payload.get("outcome") or "").upper()
    allowed = {"WON", "LOST", "WITHDRAWN", "EXPIRED", "CONVERTED", "SUPERSEDED"}
    if outcome not in allowed:
        raise HTTPException(422, {"code": "COMMERCIAL_OUTCOME_INVALID", "allowed": sorted(allowed)})
    accepted = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == item.id).order_by(ProposalAcceptedRevision.revision_number.desc()))
    row = db.scalar(select(ProposalCommercialOutcome).where(ProposalCommercialOutcome.proposal_id == item.id))
    if not row:
        row = ProposalCommercialOutcome(proposal_id=item.id, accepted_revision_id=accepted.id if accepted else None, outcome=outcome, reason=payload.get("reason"), evidence_reference=payload.get("evidence_reference"), recorded_by=_actor(role))
        db.add(row)
    else:
        row.outcome = outcome
        row.reason = payload.get("reason")
        row.evidence_reference = payload.get("evidence_reference")
        row.recorded_by = _actor(role)
        row.recorded_at = hardening_now()
    db.flush()
    if outcome in {"LOST", "WITHDRAWN", "EXPIRED", "SUPERSEDED"}:
        item.status = "CLOSED"
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_COMMERCIAL_OUTCOME_RECORDED", entity_type="ProposalCommercialOutcome", entity_id=row.id, actor_id=_actor(role), after={"outcome": outcome, "ready_close_is_not_outcome": True})
    db.commit()
    return {"result": "RECORDED", "outcome": {"id": row.id, "outcome": row.outcome, "recorded_by": row.recorded_by, "recorded_at": row.recorded_at.isoformat()}, "proposal": proposal_projection(db, item)}


@router.get("/{proposal_id}/outputs")
def outputs(proposal_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    return {"items": [{"id": item.id, "artifact_type": item.artifact_type, "filename": item.filename, "content_hash": item.content_hash, "lineage": item.lineage, "download": f"/api/bd/proposals/{proposal_id}/outputs/{item.artifact_type.lower()}"} for item in db.scalars(select(ProposalOutputArtifact).where(ProposalOutputArtifact.proposal_id == proposal_id).order_by(ProposalOutputArtifact.created_at.desc())).all()]}


@router.get("/{proposal_id}/outputs/{artifact_type}")
def download_output(proposal_id: str, artifact_type: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    artifact = db.scalar(select(ProposalOutputArtifact).where(ProposalOutputArtifact.proposal_id == proposal_id, ProposalOutputArtifact.artifact_type == artifact_type.upper()).order_by(ProposalOutputArtifact.created_at.desc()))
    revision = db.get(ProposalAcceptedRevision, artifact.revision_id) if artifact else None
    if not artifact or not revision:
        raise HTTPException(404, "OUTPUT_NOT_FOUND")
    content = output_bytes(revision, artifact.artifact_type)
    if hashlib.sha256(content).hexdigest() != artifact.content_hash:
        raise HTTPException(409, "OUTPUT_LINEAGE_MISMATCH")
    return StreamingResponse(iter([content]), media_type=artifact.content_type, headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"', "X-Proposal-Revision": str(revision.revision_number), "X-Artifact-Hash": artifact.content_hash})


@router.get("/{proposal_id}/handoff/contract")
def contract_handoff_preview(proposal_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    revision = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == proposal_id).order_by(ProposalAcceptedRevision.revision_number.desc()))
    if not revision:
        raise HTTPException(409, "ACCEPTED_REVISION_REQUIRED")
    return {"eligible": True, "accepted_revision_id": revision.id, "revision_number": revision.revision_number, "content_hash": revision.content_hash, "contract_trigger": "OWNER_DECISION_REQUIRED", "machine_legal_contract": False}


@router.post("/{proposal_id}/handoff/contract")
def contract_handoff(proposal_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), actor: str | None = None):
    require_capability(role, "BD_PROPOSAL_HANDOFF")
    contract_policy = applied_runtime_decision_value(db, "PROPOSAL_TO_CONTRACT_POLICY")
    if contract_policy == "ACCEPT_MAKES_CONTRACT_ELIGIBLE_ADMIN_INITIATES":
        raise domain_error(403, "CONTRACT_ADMIN_INITIATION_REQUIRED", policy=contract_policy)
    proposal = db.get(Opportunity, proposal_id)
    revision = accepted_contract_revision(db, proposal_id)
    if not proposal or not revision:
        raise HTTPException(409, "ACCEPTED_REVISION_REQUIRED")
    client_id = proposal.client_account_id
    if not client_id:
        raise HTTPException(409, "CLIENT_CONTEXT_REQUIRED")
    try:
        contract = create_contract_from_proposal(db, proposal=proposal, accepted=revision, actor=_actor(role, actor), correlation_id=request.state.correlation_id)
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_CONTRACT_HANDOFF", entity_type="Opportunity", entity_id=proposal.id, actor_id=_actor(role, actor), after={"accepted_revision_id": revision.id, "contract_id": contract.id, "machine_legal_contract": False})
    db.commit()
    artifacts = {item.artifact_type: {"id": item.id, "filename": item.filename, "content_hash": item.content_hash} for item in db.scalars(select(ProposalOutputArtifact).where(ProposalOutputArtifact.revision_id == revision.id)).all()}
    fields = revision.snapshot.get("fields", {})
    client = db.get(ClientAccount, client_id)
    return {"contract_id": contract.id, "contract_reference": contract.contract_reference, "proposal_id": proposal.id, "proposal_reference": proposal.opportunity_reference, "accepted_revision_id": revision.id, "revision_number": revision.revision_number, "content_hash": revision.content_hash, "client": client.display_name if client else client_id, "project_reference": revision.snapshot.get("project_reference"), "project_description": fields.get("project_description") or revision.snapshot.get("title"), "scope": fields.get("scope_of_work") or fields.get("sow"), "amount": fields.get("price"), "currency": fields.get("currency"), "duration": fields.get("duration") or fields.get("period"), "proposal_artifact": artifacts.get("PROPOSAL"), "checklist_artifact": artifacts.get("CHECKLIST"), "source_ids": revision.snapshot.get("source_ids", []), "template": revision.snapshot.get("template"), "checklist": revision.snapshot.get("checklist"), "forms_driven_v2": revision.snapshot.get("forms_driven_v2"), "status": proposal.status, "machine_legal_contract": False, "creates_project_code": False, "creates_authority_case": False, "creates_regulatory_journey": False}


@router.get("/settings/go-live")
def get_settings(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    rows = ensure_owner_settings(db)
    db.commit()
    return {"items": [{"key": row.setting_key, "value": row.value_json, "status": row.status, "updated_by": row.updated_by, "notes": row.notes} for row in rows], "safe_default": True}


@router.put("/settings/go-live")
def put_settings(payload: OwnerSettingsPatch, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_OWNER_SETTINGS")
    rows = {row.setting_key: row for row in ensure_owner_settings(db)}
    for key, value in payload.settings.items():
        if key not in rows:
            continue
        rows[key].value_json = value
        rows[key].status = "OWNER_CONFIRMED"
        rows[key].updated_by = getattr(role, "value", str(role))
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_OWNER_SETTINGS_UPDATED", entity_type="ProposalOwnerSetting", entity_id="go-live", actor_id=getattr(role, "value", str(role)), after={"keys": sorted(payload.settings)})
    db.commit()
    return get_settings(db, role)
