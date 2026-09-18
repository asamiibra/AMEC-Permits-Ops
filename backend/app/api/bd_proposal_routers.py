"""BD Proposal list and owner workbench API."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.dependencies import authenticated_actor, authenticated_principal_context, current_user_role
from ..audit.service import audit
from ..db import get_db
from ..models import AssistantHandoff, AuditEvent, ClientAccount, ClientContact, ConsultancyOffice, Contract, ContractRevision, Document, DocumentApprovalState, DocumentType, DocumentVersion, EvidenceArtifact, ExternalBody, Jurisdiction, NotificationEvent, Opportunity, Party, ProposalAcceptedRevision, ProposalAcceptanceVerification, ProposalAssumption, ProposalClientResponse, ProposalCommercialOutcome, ProposalConflict, ProposalContactContext, ProposalContractHandoff, ProposalCommercialRelease, ProposalDistributionEvent, ProposalEngineeringContribution, ProposalExpectedInputPreview, ProposalExternalCostAssumption, ProposalIntakeArtifact, ProposalLpoReconciliation, ProposalMaterialAcknowledgment, ProposalOutputArtifact, ProposalOwnerSetting, ProposalRegulatoryScopeIntent, ProposalRevision, ProposalScopeConfirmation, ProposalServiceEligibility, ProposalServiceScopeItem, ProposalSiteContext, ProposalSourceEvidence, ProposalSourceLink, ProposalStakeholderIntent, ProposalStalenessEvent, ProposalTechnicalAssessment, ProposalUnknown, ProposalNote, Quotation, QuotationRevision, ReferenceNumber, Role, ServiceType, WorkflowTask, WorkflowTaskStatus
from ..config.settings import get_settings as app_settings
from ..services.backend_realignment import domain_error, require_capability
from ..services.master_content import definition_lookup
from ..services.proposal_workspace import SOURCE_TYPES, SOURCE_TO_SEMANTIC, ensure_owner_settings, master_content_purpose, output_bytes, production_output_bytes, owner_lane_definitions, proposal_configuration, proposal_projection, snapshot_for_accept, stable_hash, validate_proposal, intake_readiness
from ..services.bd_proposal_forms_v2 import add_source_link, create_preview, set_contact, set_site_context, v2_readiness
from ..services.proposal_final_hardening import causal_revalidation_blockers, hardening_projection, impacted_sections_for_source, material_fingerprint, master_content_fingerprint, now as hardening_now
from ..services.proposal_reference import allocate_proposal_reference
from ..services.proposal_production_boundary import production_mode, require_authorized_office, require_canonical_active_client, require_exact_document_version, require_proposal_scoped_evidence, reject_synthetic_value, synthetic_test_mode
from ..services.proposals_sor import _safe_filename, ingest_provisional_intake_artifact, read_proposal_source_bytes
from ..services.contract_workspace import accepted_revision as accepted_contract_revision, create_contract_from_proposal
from ..services.proposal_commercial_controls import authorize_release, confirm_scope, create_handoff as create_proposal_handoff, handoff_predicate, record_distribution, record_eligibility, record_technical_assessment, reconcile_lpo, verify_acceptance
from ..services.owner_decisions import applied_runtime_decision_value, runtime_decision_value
from ..storage import DocumentStorageService, StorageError, StorageTarget, create_binary_store

router = APIRouter(prefix="/api/bd/proposals", tags=["bd-proposal-owner-session"])


class ProposalCreate(BaseModel):
    proposal_description: str = Field(min_length=1, max_length=250)
    project_reference: str | None = None
    project_id: str | None = None
    client_account_id: str | None = None
    client_name: str | None = None
    idempotency_key: str | None = Field(default=None, max_length=200)
    # Source-workspace promotion may create a provisional Proposal before a
    # canonical CRM ClientAccount is known. This flag is only set by the
    # authenticated Synology source route; ordinary Proposal creation remains
    # fail-closed on canonical client identity.
    provisional_source_identity: bool = False


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
    # The compatibility parameter is intentionally ignored. Consequential
    # audit identity comes from the authenticated request principal.
    return authenticated_actor() or getattr(role, "value", str(role))


def _create_proposal_record(payload: ProposalCreate, request: Request, db: Session, role: Role) -> Opportunity:
    """Create the canonical Proposal row without committing a source transaction."""
    principal = authenticated_principal_context()
    client_id = payload.client_account_id
    if production_mode():
        reject_synthetic_value(payload.proposal_description, code="CANONICAL_PROPOSAL_CONTEXT_REQUIRED")
        reject_synthetic_value(payload.project_reference, code="CANONICAL_PROPOSAL_CONTEXT_REQUIRED")
        if not (payload.provisional_source_identity and not client_id):
            client = require_canonical_active_client(db, client_id)
            client_id = client.id
    office = require_authorized_office(db, principal, project_id=payload.project_id)
    if payload.idempotency_key:
        existing = db.scalar(select(Opportunity).where(Opportunity.idempotency_key == payload.idempotency_key))
        if existing:
            if production_mode() and existing.office_id != office.id:
                raise HTTPException(409, {"code": "OFFICE_CONTEXT_MISMATCH", "office_id": office.id})
            return existing
    if not production_mode() and not client_id and payload.client_name:
        client = ClientAccount(client_reference=f"AMEC-SYN-CLIENT-{db.query(ClientAccount).count() + 1:04d}", legal_name=payload.client_name.strip(), display_name=payload.client_name.strip(), client_type="COMPANY", data_classification="SYNTHETIC", status="ACTIVE")
        db.add(client)
        db.flush()
        client_id = client.id
    reference = allocate_proposal_reference(db)
    fields = {"intake_client_name": payload.client_name, "project_reference": payload.project_reference, "provenance": {"intake_client_name": "manual", "project_reference": "manual"}}
    if payload.provisional_source_identity:
        fields["source_identity_state"] = "PROVISIONAL_UNRESOLVED"
        fields["client_resolution_state"] = "UNRESOLVED_PROVISIONAL"
    fields = {key: value for key, value in fields.items() if value is not None}
    item = Opportunity(office_id=office.id, client_account_id=client_id, opportunity_reference=reference, title=payload.proposal_description.strip(), status="IN_REVIEW", source_type="BD_WORKSPACE", project_id=payload.project_id, reference_state="CANONICAL" if payload.project_id else "PROVISIONAL", proposal_fields_json=fields, idempotency_key=payload.idempotency_key, provisional_reference=reference, canonical_project_reference=payload.project_reference)
    db.add(item)
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_DRAFT_CREATED", entity_type="Opportunity", entity_id=item.id, actor_id=_actor(role), after={"proposal_reference": reference, "status": item.status})
    return item


def _list_row(db: Session, item: Opportunity) -> dict[str, Any]:
    """Compatibility wrapper for callers that need one register row.

    The register endpoint uses ``_register_rows`` below so it can bulk-load
    relationship state. Keeping this wrapper avoids changing the public shape
    for any internal callers while preventing the detail projection from
    becoming an accidental list endpoint dependency.
    """
    return _register_rows(db, [item])[0]


def _register_rows(db: Session, items: list[Opportunity]) -> list[dict[str, Any]]:
    """Build the worklist projection with bounded bulk reads.

    ``proposal_projection`` is intentionally a detail-page projection. It
    resolves governed content, forms-v2, hardening fingerprints, commercial
    controls, and history, which is correct for one Proposal but creates an
    N+1 query chain for a register. This projection contains only fields and
    predicates needed by the register and bulk-loads all proposal-scoped
    tables once. Detail routes continue to use the full projection.
    """
    if not items:
        return []
    ids = [item.id for item in items]
    clients = {
        row.id: row
        for row in db.scalars(select(ClientAccount).where(ClientAccount.id.in_({item.client_account_id for item in items if item.client_account_id}))).all()
    }
    sources = db.scalars(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id.in_(ids)).order_by(ProposalSourceEvidence.created_at)).all()
    accepted = db.scalars(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id.in_(ids), ProposalAcceptedRevision.status == "ACCEPTED")).all()
    unknowns = db.scalars(select(ProposalUnknown).where(ProposalUnknown.proposal_id.in_(ids))).all()
    conflicts = db.scalars(select(ProposalConflict).where(ProposalConflict.proposal_id.in_(ids))).all()
    acknowledgments = db.scalars(select(ProposalMaterialAcknowledgment).where(ProposalMaterialAcknowledgment.proposal_id.in_(ids))).all()
    staleness = db.scalars(select(ProposalStalenessEvent).where(ProposalStalenessEvent.proposal_id.in_(ids))).all()
    assumptions = db.scalars(select(ProposalAssumption).where(ProposalAssumption.proposal_id.in_(ids))).all()
    scopes = db.scalars(select(ProposalServiceScopeItem).where(ProposalServiceScopeItem.proposal_id.in_(ids))).all()
    sites = db.scalars(select(ProposalSiteContext).where(ProposalSiteContext.proposal_id.in_(ids))).all()
    source_by_proposal: dict[str, list[ProposalSourceEvidence]] = {proposal_id: [] for proposal_id in ids}
    for row in sources:
        source_by_proposal.setdefault(row.proposal_id, []).append(row)
    accepted_by_proposal: dict[str, ProposalAcceptedRevision] = {}
    for row in accepted:
        current = accepted_by_proposal.get(row.proposal_id)
        if current is None or row.revision_number > current.revision_number:
            accepted_by_proposal[row.proposal_id] = row
    unknown_by_proposal: dict[str, list[ProposalUnknown]] = {proposal_id: [] for proposal_id in ids}
    conflict_by_proposal: dict[str, list[ProposalConflict]] = {proposal_id: [] for proposal_id in ids}
    ack_by_proposal: dict[str, set[tuple[str, str]]] = {proposal_id: set() for proposal_id in ids}
    staleness_by_proposal: dict[str, list[ProposalStalenessEvent]] = {proposal_id: [] for proposal_id in ids}
    assumptions_by_proposal: dict[str, list[ProposalAssumption]] = {proposal_id: [] for proposal_id in ids}
    scopes_by_proposal: dict[str, list[ProposalServiceScopeItem]] = {proposal_id: [] for proposal_id in ids}
    site_by_proposal: dict[str, ProposalSiteContext] = {}
    for row in unknowns:
        unknown_by_proposal.setdefault(row.proposal_id, []).append(row)
    for row in conflicts:
        conflict_by_proposal.setdefault(row.proposal_id, []).append(row)
    for row in acknowledgments:
        ack_by_proposal.setdefault(row.proposal_id, set()).add((row.target_type, row.target_id))
    for row in staleness:
        staleness_by_proposal.setdefault(row.proposal_id, []).append(row)
    for row in assumptions:
        assumptions_by_proposal.setdefault(row.proposal_id, []).append(row)
    for row in scopes:
        scopes_by_proposal.setdefault(row.proposal_id, []).append(row)
    for row in sites:
        site_by_proposal[row.proposal_id] = row

    # These are shared governed inputs. Resolve each only once for the whole
    # response instead of once per row.
    template = master_content_purpose(db, "PROPOSAL_TEMPLATE")
    checklist = master_content_purpose(db, "PROPOSAL_CHECKLIST")
    current_master_fingerprint = master_content_fingerprint(db)
    stage_labels = {
        "RECEIVED": "Intake & Sources", "IN_REVIEW": "Intake & Sources", "PROPOSAL_PREPARATION": "Engineering Preparation",
        "PROPOSAL_HANDOVER": "Commercial Review", "READY_FOR_QUOTATION": "Ready for Quotation", "COMMERCIAL_REVIEW": "Commercial Review", "QUOTATION_IN_PROGRESS": "Quotation in Progress",
        "CLIENT_RESPONSE_PENDING": "Client Response", "ACCEPTED": "Contract Handoff", "CONTRACT_HANDOVER": "Contract Handoff", "CLOSED": "Closed",
    }
    rows: list[dict[str, Any]] = []
    for item in items:
        fields = item.proposal_fields_json or {}
        item_sources = source_by_proposal.get(item.id, [])
        current_sources = [row for row in item_sources if row.status == "CURRENT"]
        item_unknowns = unknown_by_proposal.get(item.id, [])
        item_conflicts = conflict_by_proposal.get(item.id, [])
        item_acks = ack_by_proposal.get(item.id, set())
        item_staleness = staleness_by_proposal.get(item.id, [])
        item_assumptions = assumptions_by_proposal.get(item.id, [])
        item_scopes = scopes_by_proposal.get(item.id, [])
        blockers: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []
        required = {
            "CLIENT_REQUIRED": bool(item.client_account_id),
            "DESCRIPTION_REQUIRED": bool(item.title.strip()),
            "SCOPE_OF_WORK_REQUIRED": bool(str(fields.get("scope_of_work") or fields.get("sow") or "").strip()),
            "CLIENT_SCOPE_OF_WORK_REQUIRED": bool(str(fields.get("client_scope_of_work") or "").strip()),
            "PRICE_REQUIRED": bool(str(fields.get("price") or "").strip()),
            "DURATION_REQUIRED": bool(str(fields.get("duration") or fields.get("period") or "").strip()),
            "PROPOSAL_TEMPLATE_REQUIRED": template["status"] == "RESOLVED",
            "PROPOSAL_CHECKLIST_REQUIRED": checklist["status"] == "RESOLVED",
        }
        labels = {
            "CLIENT_REQUIRED": "Client", "DESCRIPTION_REQUIRED": "Proposal Description", "SCOPE_OF_WORK_REQUIRED": "Scope of Work",
            "CLIENT_SCOPE_OF_WORK_REQUIRED": "Client Scope of Work", "PRICE_REQUIRED": "Price", "DURATION_REQUIRED": "Duration",
            "PROPOSAL_TEMPLATE_REQUIRED": "Dashboard Proposal Template", "PROPOSAL_CHECKLIST_REQUIRED": "Dashboard Proposal Checklist",
        }
        blockers.extend({"code": code, "label": labels[code]} for code, present in required.items() if not present)
        if not item_sources:
            blockers.append({"code": "SOURCE_EVIDENCE_REQUIRED", "label": "Source evidence"})
        for source_type in SOURCE_TYPES:
            if not any(row.source_type == source_type and row.status == "CURRENT" for row in item_sources):
                warnings.append({"code": f"{source_type}_MISSING", "label": source_type.replace("_", " ").title()})
        superseded = {row.id for row in item_sources if row.status == "CONFLICT" and any(current.supersedes_id == row.id for current in current_sources)}
        active_conflicts = [row for row in item_sources if row.status == "CONFLICT" and row.id not in superseded]
        if active_conflicts:
            blockers.append({"code": "SOURCE_CONFLICTS_UNRESOLVED", "label": "Resolve conflicting source evidence"})
        elif superseded:
            warnings.append({"code": "SOURCE_CONFLICT_HISTORY", "label": "A prior source revision was superseded and remains in history"})
        if not (fields.get("inclusions") or fields.get("exclusions")):
            warnings.append({"code": "COMMERCIAL_BOUNDARIES_REVIEW", "label": "Confirm inclusions and exclusions"})
        open_unknowns = [row for row in item_unknowns if row.status == "OPEN" and row.materiality in {"MATERIAL", "BLOCKING"} and ("PROPOSAL_UNKNOWN", row.id) not in item_acks]
        open_material_conflicts = [row for row in item_conflicts if row.status == "OPEN" and row.materiality in {"MATERIAL", "BLOCKING"} and ("PROPOSAL_CONFLICT", row.id) not in item_acks]
        active_staleness = [row for row in item_staleness if row.status == "ACTIVE"]
        blockers.extend({"code": "MATERIAL_UNKNOWN_REQUIRES_ACKNOWLEDGMENT", "label": row.statement} for row in open_unknowns)
        blockers.extend({"code": "MATERIAL_CONFLICT_REQUIRES_ACKNOWLEDGMENT", "label": f"{row.field_code}: {row.source_a} vs {row.source_b}"} for row in open_material_conflicts)
        if active_staleness:
            blockers.append({"code": "SOURCE_CHANGE_REQUIRES_REVIEW", "label": "Source or governed input changed; review impacted Proposal sections before Accept"})
        accepted_revision = accepted_by_proposal.get(item.id)
        if accepted_revision and (accepted_revision.snapshot or {}).get("master_content_fingerprint") and (accepted_revision.snapshot or {}).get("master_content_fingerprint") != current_master_fingerprint:
            blockers.append({"code": "MASTER_CONTENT_REVALIDATION_REQUIRED", "label": "Create an explicit Proposal revision to revalidate changed master content before Accept"})
        intake_blockers = []
        if not item.client_account_id:
            intake_blockers.append({"code": "CLIENT_REQUIRED", "label": "Client context required"})
        if not current_sources:
            intake_blockers.append({"code": "SOURCE_EVIDENCE_REQUIRED", "label": "No source evidence received"})
        if not item.title.strip():
            intake_blockers.append({"code": "DESCRIPTION_REQUIRED", "label": "Proposal description required"})
        if item.reference_state not in {"PROVISIONAL", "CANONICAL"}:
            intake_blockers.append({"code": "REFERENCE_STATE_INVALID", "label": "Proposal reference state is invalid"})
        if any(row.verification_state != "READ_BACK_VERIFIED" for row in current_sources):
            intake_blockers.append({"code": "SOURCE_VERIFICATION_REQUIRED", "label": "Source verification incomplete"})
        blockers.extend(intake_blockers)
        readiness_blockers = []
        if not item_scopes and not str(fields.get("scope_of_work") or fields.get("sow") or "").strip():
            readiness_blockers.append({"code": "SERVICE_SCOPE_REQUIRED", "label": "AMEC service scope"})
        if any(row.materiality == "MATERIAL" and row.status != "ACKNOWLEDGED" for row in item_assumptions):
            readiness_blockers.append({"code": "MATERIAL_ASSUMPTION_ACKNOWLEDGEMENT_REQUIRED", "label": "Acknowledge material commercial assumptions"})
        if active_conflicts:
            readiness_blockers.append({"code": "MATERIAL_CONFLICT_REQUIRES_DECISION", "label": "Resolve or explicitly accept material conflicts"})
        blockers.extend(readiness_blockers)
        blockers = list({row["code"]: row for row in blockers}.values())
        validation = {
            "ready": not blockers,
            "blockers": blockers,
            "warnings": warnings,
            "source_count": len(current_sources),
            "conflict_count": len(active_conflicts),
            "template": template,
            "checklist": checklist,
            "definitions": [],
            "ai_assist": {"enabled": False, "response": None, "typed_error": "AI_ASSIST_DISABLED"},
            "authority": "OWNER_DECISION_REQUIRED",
            "register_projection": True,
        }
        authority_review = item.status in {"PROPOSAL_HANDOVER", "READY_FOR_QUOTATION", "COMMERCIAL_REVIEW", "QUOTATION_IN_PROGRESS"} and not blockers and not accepted_revision
        need_action = bool(blockers) or item.status == "CLIENT_RESPONSE_PENDING"
        ready_close = item.status in {"CLIENT_RESPONSE_PENDING", "ACCEPTED", "CONTRACT_HANDOVER", "CLOSED"} and not need_action
        memberships = ["ALL"]
        if need_action:
            memberships.append("NEED_ACTION")
        if authority_review:
            memberships.append("AUTHORITY_REVIEW")
        if ready_close:
            memberships.append("READY_CLOSE")
        primary = "NEED_ACTION" if need_action else "AUTHORITY_REVIEW" if authority_review else "READY_CLOSE" if ready_close else "ALL"
        owner_lane = {"primary": primary, "memberships": memberships, "reason_codes": [row["code"] for row in blockers], "reason_labels": [row["label"] for row in blockers], "predicate_version": "bd-proposal-owner-lanes-v1"}
        current_owner = "Engineering" if item.status == "PROPOSAL_PREPARATION" else "Business Development"
        next_action = (
            "Complete technical Proposal preparation" if item.status == "PROPOSAL_PREPARATION" else
            "Resolve intake blockers" if item.status in {"RECEIVED", "IN_REVIEW"} and blockers else
            "Proceed to Engineering Preparation" if item.status in {"RECEIVED", "IN_REVIEW"} else
            "Resolve Proposal readiness blockers" if item.status in {"PROPOSAL_HANDOVER", "COMMERCIAL_REVIEW", "QUOTATION_IN_PROGRESS"} and blockers else
            "Review Proposal Authority" if item.status in {"PROPOSAL_HANDOVER", "READY_FOR_QUOTATION", "COMMERCIAL_REVIEW", "QUOTATION_IN_PROGRESS"} else
            "Follow up client response" if item.status == "CLIENT_RESPONSE_PENDING" else
            "Proceed to Contract handoff" if item.status in {"ACCEPTED", "CONTRACT_HANDOVER"} else
            "No further Proposal action" if item.status == "CLOSED" else "Review Proposal"
        )
        client = clients.get(item.client_account_id)
        client_label = (client.display_name or client.legal_name if client else None) or item.client_account_id or "Not recorded"
        site = site_by_proposal.get(item.id)
        location = (site.location_text if site else None) or fields.get("location") or (site.site_description if site else None) or ""
        activity = fields.get("project_description") or fields.get("activity") or item.title
        project_ref = item.canonical_project_reference or item.provisional_reference
        contract_eligible = bool(accepted_revision and handoff_predicate(db, item.id)["eligible"])
        search_text = " ".join(str(value or "") for value in (item.title, item.opportunity_reference, project_ref, client_label, activity, fields.get("client_scope_of_work"), fields.get("scope_of_work") or fields.get("sow"), location, stage_labels.get(item.status, item.status.replace("_", " ").title()), item.status)).lower()
        rows.append({"id": item.id, "proposal_reference": item.opportunity_reference, "proposal": item.title, "project_ref": project_ref, "client": client_label, "activity": activity, "stage": stage_labels.get(item.status, item.status.replace("_", " ").title()), "stage_code": item.status, "amount": fields.get("price"), "last_activity": item.updated_at.isoformat() if item.updated_at else None, "location": location or None, "current_owner": current_owner, "next_action": {"label": next_action, "eligible": not blockers, "blockers": len(blockers)}, "owner_lane": owner_lane, "contract_eligible": contract_eligible, "validation": validation, "fixture_classification": item.fixture_classification, "_search_text": search_text})
    return rows


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
    rows, lane_counts = _register_predicate(_register_rows(db, db.scalars(select(Opportunity).order_by(Opportunity.updated_at.desc(), Opportunity.opportunity_reference)).all()), q=q, stage=stage, lane=lane, client=client, activity=activity, location=location)
    for row in rows:
        row.pop("_search_text", None)
    return {"items": rows, "rows": rows, "count": len(rows), "lane_counts": lane_counts, "lane_options": owner_lane_definitions(), "predicate_version": "bd-proposal-register-v2", "filters": {"q": q, "stage": stage, "lane": lane, "client": client, "activity": activity, "location": location}, "stage_options": ["RECEIVED", "IN_REVIEW", "PROPOSAL_PREPARATION", "PROPOSAL_HANDOVER", "READY_FOR_QUOTATION", "COMMERCIAL_REVIEW", "QUOTATION_IN_PROGRESS", "CLIENT_RESPONSE_PENDING", "ACCEPTED", "CONTRACT_HANDOVER", "CLOSED"], "amount_source": "proposal_fields.price", "last_activity_source": "Opportunity.updated_at material Proposal activity timestamp", "search_fields": ["client_name", "proposal.title", "project_description", "client_scope_of_work", "scope_of_work", "site_context.location_text", "site_context.site_description", "proposal_reference", "project_reference", "stage"], "synthetic_only": any(row.get("fixture_classification") == "SYNTHETIC_OWNER_TEST" for row in rows)}


@router.post("")
def create_proposal(payload: ProposalCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    if payload.idempotency_key:
        existing = db.scalar(select(Opportunity).where(Opportunity.idempotency_key == payload.idempotency_key))
        if existing:
            return {**proposal_projection(db, existing), "result": "IDEMPOTENT"}
    item = _create_proposal_record(payload, request, db, role)
    db.commit()
    return {**proposal_projection(db, item), "result": "CREATED"}


@router.get("/master-content")
def proposal_master_content(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    return {"proposal_template": master_content_purpose(db, "PROPOSAL_TEMPLATE"), "proposal_checklist": master_content_purpose(db, "PROPOSAL_CHECKLIST"), "definitions": {"lookup": "/api/definitions/lookup/{term}", "truth": "DASHBOARD_DEFINITIONS"}}


@router.get("/clients")
def proposal_clients(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    """Return active canonical Clients available to Proposal intake."""
    require_capability(role, "BD_PROPOSAL_READ")
    items = db.scalars(
        select(ClientAccount)
        .where(ClientAccount.status == "ACTIVE")
        .order_by(ClientAccount.display_name, ClientAccount.client_reference)
    ).all()
    return {
        "items": [
            {
                "id": item.id,
                "name": item.display_name,
                "reference": item.client_reference,
                "status": item.status,
            }
            for item in items
        ],
        "count": len(items),
    }


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
    return proposal_projection(db, item, role)


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
    if not db.get(Party, party_id):
        raise HTTPException(422, {"code": "PARTY_NOT_FOUND", "party_id": party_id})
    client.canonical_party_id = party_id
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_CLIENT_PARTY_LINKED", entity_type="ClientAccount", entity_id=client.id, actor_id=_actor(role), after={"canonical_party_id": party_id})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/stakeholders")
def add_stakeholder(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    if payload.get("party_id") and not db.get(Party, payload["party_id"]):
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
        model_class = {"ExternalBody": ExternalBody, "ServiceType": ServiceType, "Jurisdiction": Jurisdiction}[key]
        if payload.get(model) and not db.get(model_class, payload[model]):
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
    if production_mode():
        raise domain_error(409, "CAUSAL_REVALIDATION_REQUIRED", active_event_ids=[item.id for item in active])
    for item in active:
        item.status = "CLEARED"
        item.cleared_by = _actor(role)
        item.cleared_at = hardening_now()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_STALENESS_REVIEWED", entity_type="Opportunity", entity_id=proposal.id, actor_id=_actor(role), after={"cleared_event_ids": [item.id for item in active]})
    db.commit()
    return proposal_projection(db, proposal)


@router.post("/{proposal_id}/staleness/revalidate")
def revalidate_proposal_staleness(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = _proposal_or_404(proposal_id, db)
    accepted = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == proposal.id).order_by(ProposalAcceptedRevision.revision_number.desc()))
    revision_id = payload.get("revision_id")
    revision = db.scalar(select(ProposalRevision).where(ProposalRevision.id == revision_id, ProposalRevision.proposal_id == proposal.id, ProposalRevision.status == "DRAFT"))
    if not accepted or not revision or revision.base_accepted_revision_id != accepted.id:
        raise domain_error(409, "CAUSAL_REVALIDATION_REVISION_REQUIRED", accepted_revision_id=accepted.id if accepted else None)
    active = db.scalars(select(ProposalStalenessEvent).where(ProposalStalenessEvent.proposal_id == proposal.id, ProposalStalenessEvent.status == "ACTIVE")).all()
    requested_ids = set(payload.get("event_ids") or [item.id for item in active])
    if not active or {item.id for item in active} != requested_ids:
        raise domain_error(409, "ALL_ACTIVE_STALENESS_EVENTS_MUST_BE_REVALIDATED")
    blockers = causal_revalidation_blockers(db, proposal, revision, active)
    if blockers:
        raise domain_error(409, blockers[0], blockers=blockers, server_derived_result="BLOCKED")
    next_revision = ProposalAcceptedRevision(
        proposal_id=proposal.id,
        revision_number=accepted.revision_number + 1,
        snapshot=dict(revision.snapshot or {}),
        validation_snapshot={**(accepted.validation_snapshot or {}), "causal_revalidation": {"source_revision_id": revision.id, "event_ids": sorted(requested_ids), "server_derived_result": "PASS"}},
        template_ref=accepted.template_ref,
        template_version_id=accepted.template_version_id,
        template_version=accepted.template_version,
        template_hash=accepted.template_hash,
        checklist_ref=accepted.checklist_ref,
        checklist_version_id=accepted.checklist_version_id,
        checklist_version=accepted.checklist_version,
        checklist_hash=accepted.checklist_hash,
        definition_refs=list(accepted.definition_refs or []),
        content_hash=revision.content_hash,
        accepted_by=_actor(role),
        supersedes_revision_id=accepted.id,
    )
    db.add(next_revision)
    revision.status = "ACCEPTED"
    db.flush()
    for item in active:
        item.status = "CLEARED"
        item.cleared_by = _actor(role)
        item.cleared_at = hardening_now()
        item.revalidation_revision_id = revision.id
        item.revalidation_accepted_revision_id = next_revision.id
        item.revalidated_by = _actor(role)
        item.revalidated_at = hardening_now()
        item.revalidation_result = "PASS"
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_STALENESS_CAUSALLY_REVALIDATED", entity_type="Opportunity", entity_id=proposal.id, actor_id=_actor(role), after={"event_ids": sorted(requested_ids), "revalidation_revision_id": revision.id, "revalidation_accepted_revision_id": next_revision.id, "result": "PASS"})
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
    incoming_fields = dict(payload.fields or {})
    if production_mode() and "client_account_id" in incoming_fields:
        if str(incoming_fields.pop("client_account_id")) != str(item.client_account_id):
            raise domain_error(409, "CANONICAL_CLIENT_ID_IMMUTABLE", client_account_id=item.client_account_id)
    if "client_name" in incoming_fields:
        current["intake_client_name"] = incoming_fields.pop("client_name")
        current["provenance"] = {**(current.get("provenance") or {}), "intake_client_name": "manual"}
    current.update(incoming_fields)
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
    operation_key = idempotency_key or f"proposal-source:{proposal.id}:{source_type}:{digest}"
    prior_intake = db.scalar(select(ProposalIntakeArtifact).where(ProposalIntakeArtifact.idempotency_key == operation_key))
    if prior_intake:
        prior_evidence = db.scalar(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id, ProposalSourceEvidence.content_hash == digest, ProposalSourceEvidence.source_type == source_type).order_by(ProposalSourceEvidence.created_at.desc()))
        if prior_evidence:
            return {"source": {"id": prior_evidence.id, "source_type": prior_evidence.source_type, "content_hash": prior_evidence.content_hash, "verification_state": prior_evidence.verification_state, "status": prior_evidence.status, "source_reference": prior_evidence.source_reference}}
    production_version = None
    production_document = None
    # Production sources use the same verified provider-neutral storage service
    # as generated outputs. The legacy local/Synology adapter remains confined
    # to synthetic TEST fixtures.
    if production_mode():
        workspace = (proposal.proposal_fields_json or {}).get("source_workspace") or {}
        if not (workspace and proposal.client_account_id is None):
            require_canonical_active_client(db, proposal.client_account_id)
        store = create_binary_store()
        target = StorageTarget(store.provider_id, getattr(getattr(store, "config", None), "container", None) or getattr(getattr(store, "config", None), "share", ""), f"proposal-intake/{proposal.id}/{source_type.lower()}")
        production_document = Document(project_id=proposal.project_id, document_type=DocumentType.OTHER, logical_name=f"{proposal.opportunity_reference}:{source_type}:{digest}", language="EN", source_system="PROPOSAL_INTAKE")
        db.add(production_document)
        db.flush()
        try:
            stored = DocumentStorageService(store).store_version(db, document=production_document, content=content, filename=source_filename, mime_type=content_type, target=target, actor=actor, correlation_id=request.state.correlation_id, idempotency_key=operation_key, source_system="PROPOSAL_INTAKE", metadata={"proposal_id": proposal.id, "source_type": source_type, "source_revision": source_revision, **(source_metadata or {})})
        except StorageError as exc:
            raise domain_error(503, "PRODUCTION_SOURCE_STORAGE_FAILED", storage_code=exc.code.value) from exc
        production_version = stored.version
        intake = ProposalIntakeArtifact(opportunity_id=proposal.id, project_id=proposal.project_id, opportunity_reference=proposal.opportunity_reference, artifact_type=source_type, semantic_class=semantic, source_filename=source_filename, stored_filename=source_filename, sor_path=production_version.source_path_or_reference, content_hash=digest, content_type=content_type or "application/octet-stream", file_size=len(content), uploaded_by=actor, source_revision=source_revision, idempotency_key=operation_key, verification_state="READ_BACK_VERIFIED", status="REGISTERED", metadata_json={"document_version_id": production_version.id, "storage_provider": store.provider_id, "correlation_id": request.state.correlation_id})
        db.add(intake)
        db.flush()
        result = {"id": intake.id, "source_filename": source_filename, "sor_path": production_version.source_path_or_reference, "content_hash": digest, "verification_state": "READ_BACK_VERIFIED", "semantic_class": semantic}
    # Vercel TEST has durable PostgreSQL but a read-only deployment bundle.
    # Preserve the verified source index and hash there; local TEST continues
    # to exercise the MockSynologyAdapter filesystem path.
    if production_version is None and app_settings().app_env.upper() == "TEST" and os.environ.get("VERCEL"):
        result = {"id": str(uuid4()), "source_filename": source_filename, "sor_path": f"synthetic://proposal-source/{proposal.opportunity_reference}/{source_type.lower()}/{digest}", "content_hash": digest, "verification_state": "READ_BACK_VERIFIED", "semantic_class": semantic}
    elif production_version is None:
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
    if not document and production_document is None:
        local_fixture_metadata = {"synthetic_only": True, "sensitivity_class": "SYNTHETIC", **(source_metadata or {})} if app_settings().synthetic_only else dict(source_metadata or {})
        document = Document(project_id=proposal.project_id, document_type=DocumentType.OTHER, logical_name=f"{proposal.opportunity_reference}:{source_type}:{digest}", language="EN", source_system="PROPOSAL_INTAKE", current_version_id=None)
        db.add(document)
        db.flush()
        version = DocumentVersion(document_id=document.id, version_number=1, source_filename=result["source_filename"], source_path_or_reference=result["sor_path"], sha256=digest, mime_type=content_type, file_size=len(content), language="EN", revision_label=source_revision, approval_state=DocumentApprovalState.WORKING, source_system="PROPOSAL_INTAKE", metadata_json=local_fixture_metadata)
        db.add(version)
        db.flush()
        document.current_version_id = version.id
    elif production_version is not None:
        document = production_document
        version = production_version
    else:
        version = db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document.id, DocumentVersion.sha256 == digest))
        if not version:
            next_version = (db.scalar(select(DocumentVersion.version_number).where(DocumentVersion.document_id == document.id).order_by(DocumentVersion.version_number.desc())) or 0) + 1
            local_fixture_metadata = {"synthetic_only": True, "sensitivity_class": "SYNTHETIC", **(source_metadata or {})} if app_settings().synthetic_only else dict(source_metadata or {})
            version = DocumentVersion(document_id=document.id, version_number=next_version, source_filename=result["source_filename"], source_path_or_reference=result["sor_path"], sha256=digest, mime_type=content_type, file_size=len(content), language="EN", revision_label=source_revision, approval_state=DocumentApprovalState.WORKING, source_system="PROPOSAL_INTAKE", metadata_json=local_fixture_metadata)
            db.add(version)
            db.flush()
            document.current_version_id = version.id
    if not db.scalar(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal.id, ProposalSourceLink.document_version_id == version.id, ProposalSourceLink.source_role == source_type)):
        db.add(ProposalSourceLink(proposal_id=proposal.id, source_evidence_id=evidence.id, document_id=document.id, document_version_id=version.id, source_role=source_type, added_by=_actor(role, actor)))
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_SOURCE_REGISTERED", entity_type="Opportunity", entity_id=proposal.id, actor_id=actor, after={"source_type": source_type, "source_evidence_id": evidence.id, "content_hash": digest, "conflict": bool(existing and existing.content_hash != digest), "initial_source": bool(source_metadata and source_metadata.get("initial_source"))})
    return {"source": {"id": evidence.id, "source_type": evidence.source_type, "content_hash": evidence.content_hash, "verification_state": evidence.verification_state, "status": evidence.status, "source_reference": evidence.source_reference}}


@router.post("/intake")
async def create_proposal_intake(request: Request, proposal_description: str = Form(...), project_reference: str | None = Form(default=None), client_name: str | None = Form(default=None), client_account_id: str | None = Form(default=None), project_id: str | None = Form(default=None), initial_source_type: str | None = Form(default=None), source_title: str | None = Form(default=None), source_date: str | None = Form(default=None), source_notes: str | None = Form(default=None), source_revision: str | None = Form(default=None), contact_name: str | None = Form(default=None), contact_email: str | None = Form(default=None), idempotency_key: str | None = Form(default=None), file: UploadFile | None = File(default=None), db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    """Create a Proposal and its optional initial source in one DB transaction."""
    require_capability(role, "BD_PROPOSAL_WRITE")
    source_type = initial_source_type.upper() if initial_source_type else None
    if source_type and source_type not in SOURCE_TYPES:
        raise HTTPException(422, {"code": "SOURCE_TYPE_REQUIRED", "allowed": list(SOURCE_TYPES)})
    # Client Information is a source context made from human-entered client
    # context and contact metadata; unlike a tender source it has no required
    # external file. The other source contexts must retain their file gate.
    if source_type and not file and source_type != "CLIENT_DATA":
        raise HTTPException(422, {"code": "INITIAL_SOURCE_FILE_REQUIRED", "source_type": source_type})
    existing = db.scalar(select(Opportunity).where(Opportunity.idempotency_key == idempotency_key)) if idempotency_key else None
    if existing:
        return {"result": "IDEMPOTENT", "proposal": proposal_projection(db, existing), "next_route": f"/opportunities/{existing.id}"}
    proposal = _create_proposal_record(ProposalCreate(proposal_description=proposal_description, project_reference=project_reference, client_account_id=client_account_id, client_name=client_name, project_id=project_id, idempotency_key=idempotency_key), request, db, role)
    result: dict[str, Any] = {}
    try:
        if source_type and file:
            content = await file.read()
            if not content:
                raise HTTPException(422, {"code": "INITIAL_SOURCE_FILE_EMPTY", "source_type": source_type})
            result = await _register_source_content(proposal=proposal, request=request, source_type=source_type, source_filename=file.filename or source_title or "source.bin", content_type=file.content_type or "application/octet-stream", content=content, source_revision=source_revision, actor=_actor(role), idempotency_key=idempotency_key, source_metadata={"initial_source": True, "title": source_title, "source_date": source_date, "notes": source_notes}, db=db, role=role)
        elif source_type == "CLIENT_DATA":
            contact = (contact_name or "").strip()
            email = (contact_email or "").strip()
            if not contact and not email:
                raise HTTPException(422, {"code": "CLIENT_INFORMATION_CONTACT_REQUIRED"})
            set_contact(db, proposal, {"display_name": contact or None, "email": email or None, "purpose": "PROPOSAL_CONTACT", "status": "HUMAN_ENTERED", "notes": source_notes or None}, _actor(role))
            metadata_lines = [
                f"Client: {(client_name or '').strip()}",
                f"Contact: {contact or 'Not recorded'}",
                f"Email: {email or 'Not recorded'}",
                f"Source title: {(source_title or 'Client Information').strip()}",
                f"Source date: {(source_date or 'Not recorded').strip()}",
                f"Notes: {(source_notes or 'Not recorded').strip()}",
            ]
            result = await _register_source_content(
                proposal=proposal,
                request=request,
                source_type=source_type,
                source_filename=source_title.strip() if source_title and source_title.strip() else "client-information.txt",
                content_type="text/plain",
                content=("HUMAN-ENTERED CLIENT INFORMATION\n" + "\n".join(metadata_lines)).encode("utf-8"),
                source_revision=None,
                actor=_actor(role),
                idempotency_key=idempotency_key,
                source_metadata={"initial_source": True, "context": "CLIENT_INFORMATION", "title": source_title, "source_date": source_date, "notes": source_notes},
                db=db,
                role=role,
            )
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {**result, "proposal": proposal_projection(db, proposal), "next_route": f"/opportunities/{proposal.id}"}


@router.post("/{proposal_id}/sources")
async def add_source(proposal_id: str, request: Request, source_type: str = Form(...), file: UploadFile = File(...), source_revision: str | None = Form(default=None), logical_category: str | None = Form(default=None), actor: str | None = Form(default=None), idempotency_key: str | None = Form(default=None), db: Session = Depends(get_db), role: Role = Depends(current_user_role), x_synthetic_sor: str | None = Header(default=None)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = db.get(Opportunity, proposal_id)
    if not proposal:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    content = await file.read()
    allowed_categories = {"TENDER_DOCUMENTS", "PHOTOS_IMAGES", "EMAIL", "CLIENT_DATA", "CLIENT_DOCUMENTS", "PROJECT_INFORMATION", "OTHER_UNCLASSIFIED"}
    if logical_category and logical_category not in allowed_categories:
        raise HTTPException(422, {"code": "SOURCE_CATEGORY_INVALID", "allowed": sorted(allowed_categories)})
    result = await _register_source_content(proposal=proposal, request=request, source_type=source_type, source_filename=file.filename or "source.bin", content_type=file.content_type or "application/octet-stream", content=content, source_revision=source_revision, actor=_actor(role, actor), idempotency_key=idempotency_key, source_metadata={"logical_category": logical_category} if logical_category else None, db=db, role=role)
    db.commit()
    return {**result, "proposal": proposal_projection(db, proposal)}


@router.post("/{proposal_id}/sources/batch")
async def add_sources_batch(
    proposal_id: str,
    request: Request,
    files: list[UploadFile] = File(...),
    source_types: str = Form(default="[]"),
    logical_categories: str = Form(default="[]"),
    db: Session = Depends(get_db),
    role: Role = Depends(current_user_role),
):
    """Stage Owner-added sources atomically before Proposal generation."""
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = db.get(Opportunity, proposal_id)
    if not proposal:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    try:
        types = json.loads(source_types or "[]")
        categories = json.loads(logical_categories or "[]")
    except (TypeError, json.JSONDecodeError) as exc:
        raise HTTPException(422, "SOURCE_BATCH_METADATA_INVALID") from exc
    if not isinstance(types, list) or not isinstance(categories, list) or len(types) != len(files) or len(categories) != len(files):
        raise HTTPException(422, "SOURCE_BATCH_METADATA_COUNT_MISMATCH")
    allowed_categories = {"TENDER_DOCUMENTS", "PHOTOS_IMAGES", "EMAIL", "CLIENT_DATA", "CLIENT_DOCUMENTS", "PROJECT_INFORMATION", "OTHER_UNCLASSIFIED"}
    if any(category not in allowed_categories for category in categories):
        raise HTTPException(422, {"code": "SOURCE_CATEGORY_INVALID", "allowed": sorted(allowed_categories)})
    try:
        results = []
        for upload, source_type, category in zip(files, types, categories):
            content = await upload.read()
            results.append(await _register_source_content(
                proposal=proposal,
                request=request,
                source_type=str(source_type),
                source_filename=upload.filename or "source.bin",
                content_type=upload.content_type or "application/octet-stream",
                content=content,
                source_revision=None,
                actor=_actor(role),
                idempotency_key=None,
                source_metadata={"logical_category": category, "owner_staged": True},
                db=db,
                role=role,
            ))
        db.commit()
    except Exception:
        db.rollback()
        raise
    return {"result": "SOURCES_STAGED", "proposal_id": proposal_id, "sources": results, "count": len(results)}


@router.get("/{proposal_id}/sources/{source_id}/content")
def read_source_content(proposal_id: str, source_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    proposal = db.get(Opportunity, proposal_id)
    if not proposal:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    evidence = db.scalar(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal_id, ProposalSourceEvidence.id == source_id))
    if not evidence:
        raise HTTPException(404, "SOURCE_NOT_FOUND")
    links = db.scalars(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal_id, ProposalSourceLink.source_evidence_id == evidence.id)).all()
    if len(links) != 1:
        raise HTTPException(409, "PROPOSAL_SOURCE_READBACK_LINKAGE_MISMATCH")
    link = links[0]
    version = db.get(DocumentVersion, link.document_version_id)
    document = db.get(Document, link.document_id)
    source_artifact_id = (evidence.provenance or {}).get("source_artifact_id")
    artifact = db.get(ProposalIntakeArtifact, source_artifact_id) if source_artifact_id else None
    if (
        not version
        or not document
        or version.document_id != document.id
        or not artifact
        or artifact.opportunity_id != proposal_id
        or evidence.proposal_id != proposal_id
        or link.proposal_id != proposal_id
        or link.source_evidence_id != evidence.id
        or link.document_version_id != version.id
        or evidence.content_hash != version.sha256
        or version.source_path_or_reference != artifact.sor_path
        or version.file_size != artifact.file_size
        or artifact.content_hash != version.sha256
    ):
        raise HTTPException(409, "PROPOSAL_SOURCE_READBACK_LINKAGE_MISMATCH")
    if version.source_path_or_reference.startswith("storage://"):
        try:
            with DocumentStorageService(create_binary_store()).read_verified(version) as readback:
                content = readback.read()
        except StorageError as exc:
            raise domain_error(503, "PROPOSAL_SOURCE_READBACK_UNAVAILABLE", storage_code=exc.code.value) from exc
    else:
        content = read_proposal_source_bytes(
            opportunity_reference=proposal.opportunity_reference,
            sor_path=artifact.sor_path,
            expected_sha256=version.sha256,
            expected_file_size=version.file_size,
        )
    filename = Path(artifact.source_filename or evidence.source_filename or "source.bin").name
    return Response(
        content=content,
        media_type=artifact.content_type or evidence.content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{_safe_filename(filename)}"',
            "X-Proposal-Source-Evidence-Id": evidence.id,
            "X-Proposal-Source-Link-Id": link.id,
            "X-Document-Version-Id": version.id,
            "X-Proposal-Intake-Artifact-Id": artifact.id,
            "X-Content-SHA256": hashlib.sha256(content).hexdigest(),
        },
    )


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
    if production_mode() and applied_runtime_decision_value(db, "PROPOSAL_OUTPUT_FORMAT_POLICY") is None:
        raise domain_error(409, "OWNER_DECISION_REQUIRED", decision_key="PROPOSAL_OUTPUT_FORMAT_POLICY")
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
    if prior and not draft_revision and snapshot.get("material_fingerprint") == (prior.snapshot or {}).get("material_fingerprint"):
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
    for artifact_type, filename in (("PROPOSAL", f"{item.opportunity_reference}-r{revision_number}-proposal.pdf"), ("CHECKLIST", f"{item.opportunity_reference}-r{revision_number}-checklist.pdf")):
        if synthetic_test_mode():
            content = output_bytes(revision, artifact_type)
            db.add(ProposalOutputArtifact(revision_id=revision.id, proposal_id=item.id, artifact_type=artifact_type, filename=filename, content_type="text/plain", content_hash=hashlib.sha256(content).hexdigest(), storage_reference=f"synthetic://proposal-output/{revision.id}/{artifact_type.lower()}", lineage={"accepted_revision_id": revision.id, "proposal_content_hash": content_hash, "template_version_id": revision.template_version_id, "checklist_version_id": revision.checklist_version_id, "source_ids": snapshot["source_ids"], "format": "SYNTHETIC_TEXT", "renderer": "SYNTHETIC_JSON_RENDERER_V1", "generated_by": _actor(role, actor), "read_back_verified": True}, file_size=len(content), synthetic_only=True))
            continue
        try:
            content, render_lineage = production_output_bytes(db, revision, artifact_type)
            output_content_type = render_lineage.get("content_type", "application/pdf")
            output_format = str(render_lineage.get("format", "PDF")).lower()
            output_extension = "docx" if output_format == "docx" else "pdf"
            filename = f"{item.opportunity_reference}-r{revision_number}-{artifact_type.lower()}.{output_extension}"
            store = create_binary_store()
            target = StorageTarget(store.provider_id, getattr(getattr(store, "config", None), "container", None) or getattr(getattr(store, "config", None), "share", ""), f"proposal-outputs/{item.id}/{revision.id}/{artifact_type.lower()}")
            document = Document(project_id=item.project_id, document_type=DocumentType.OTHER, logical_name=f"{item.opportunity_reference}:{artifact_type}:r{revision_number}", language="EN", source_system="PROPOSAL_OUTPUT")
            db.add(document)
            db.flush()
            stored = DocumentStorageService(store).store_version(db, document=document, content=content, filename=filename, mime_type=output_content_type, target=target, actor=_actor(role, actor), correlation_id=request.state.correlation_id, idempotency_key=f"proposal-output:{revision.id}:{artifact_type}", source_system="PROPOSAL_OUTPUT", metadata={"proposal_id": item.id, "accepted_revision_id": revision.id, "renderer": render_lineage["renderer"]})
            with DocumentStorageService(store).read_verified(stored.version) as readback:
                readback_bytes = readback.read()
            if hashlib.sha256(readback_bytes).hexdigest() != hashlib.sha256(content).hexdigest() or len(readback_bytes) != len(content):
                raise ValueError("PRODUCTION_ARTIFACT_READBACK_MISMATCH")
            db.add(ProposalOutputArtifact(revision_id=revision.id, proposal_id=item.id, artifact_type=artifact_type, filename=filename, content_type=output_content_type, content_hash=hashlib.sha256(content).hexdigest(), storage_reference=stored.version.source_path_or_reference, document_version_id=stored.version.id, lineage={**render_lineage, "proposal_content_hash": content_hash, "source_ids": snapshot["source_ids"], "read_back_verified": True, "storage_operation_id": stored.operation.id}, file_size=len(content), synthetic_only=False))
        except StorageError as exc:
            raise domain_error(503, "PRODUCTION_ARTIFACT_STORAGE_FAILED", storage_code=exc.code.value) from exc
        except ValueError as exc:
            raise domain_error(503, str(exc)) from exc
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
    accepted = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == item.id).order_by(ProposalAcceptedRevision.revision_number.desc()))
    if production_mode():
        if not accepted:
            raise domain_error(409, "ACCEPTED_REVISION_REQUIRED")
        if payload.get("accepted_revision_id") != accepted.id:
            raise domain_error(409, "CLIENT_RESPONSE_REVISION_REQUIRED", accepted_revision_id=accepted.id)
        client = require_canonical_active_client(db, item.client_account_id)
        client_account_id = payload.get("client_account_id")
        if client_account_id != client.id:
            raise domain_error(409, "CLIENT_RESPONSE_CLIENT_MISMATCH", client_account_id=client.id)
        contact_id = payload.get("client_contact_id")
        contact = db.scalar(select(ClientContact).where(ClientContact.id == contact_id, ClientContact.client_account_id == client.id, ClientContact.status == "ACTIVE")) if contact_id else None
        if not contact:
            raise domain_error(409, "CLIENT_RESPONSE_CONTACT_REQUIRED")
        if response_type == "ACCEPTED":
            distributed = db.scalar(select(ProposalDistributionEvent).where(ProposalDistributionEvent.proposal_id == item.id, ProposalDistributionEvent.accepted_revision_id == accepted.id, ProposalDistributionEvent.delivery_status == "DELIVERED"))
            if not distributed:
                raise domain_error(409, "CLIENT_RESPONSE_DISTRIBUTION_REQUIRED")
        evidence_version = require_exact_document_version(db, payload.get("evidence_document_version_id"), code="CLIENT_RESPONSE_DOCUMENT_VERSION_REQUIRED")
        require_proposal_scoped_evidence(db, proposal_id=item.id, version_id=evidence_version.id, source_roles=("CLIENT_RESPONSE", "CLIENT_ACCEPTANCE"), code="CLIENT_RESPONSE_DOCUMENT_VERSION_REQUIRED", client_account_id=client.id)
        evidence_reference = str(payload.get("evidence_reference") or f"document-version:{evidence_version.id}").strip()
        reject_synthetic_value(evidence_reference, code="CLIENT_RESPONSE_EVIDENCE_REQUIRED")
    else:
        client_account_id = payload.get("client_account_id")
        contact_id = payload.get("client_contact_id")
        evidence_version = None
        evidence_reference = payload.get("evidence_reference")
    existing = db.scalar(select(ProposalClientResponse).where(ProposalClientResponse.idempotency_key == idempotency_key))
    if existing:
        if (
            existing.proposal_id != item.id
            or existing.accepted_revision_id != (accepted.id if accepted else None)
            or existing.response_type != response_type
            or existing.client_account_id != client_account_id
            or existing.client_contact_id != contact_id
            or existing.evidence_document_version_id != (evidence_version.id if evidence_version else payload.get("evidence_document_version_id"))
        ):
            raise domain_error(409, "IDEMPOTENCY_KEY_SCOPE_MISMATCH")
        return {"result": "IDEMPOTENT", "response": {"id": existing.id, "response_type": existing.response_type, "recorded_by": existing.recorded_by, "recorded_at": existing.recorded_at.isoformat()}, "proposal": proposal_projection(db, item)}
    row = ProposalClientResponse(proposal_id=item.id, accepted_revision_id=accepted.id if accepted else None, client_account_id=client_account_id, client_contact_id=contact_id, response_type=response_type, evidence_reference=evidence_reference, evidence_document_version_id=evidence_version.id if evidence_version else payload.get("evidence_document_version_id"), evidence_sha256=evidence_version.sha256 if evidence_version else payload.get("evidence_sha256"), notes=payload.get("notes"), recorded_by=_actor(role), idempotency_key=idempotency_key)
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


def _control_result(row: Any, *, idempotent: bool = False) -> dict[str, Any]:
    return {"result": "IDEMPOTENT" if idempotent else "RECORDED", "control": {column.name: getattr(row, column.name) for column in row.__table__.columns}}


@router.post("/{proposal_id}/technical-assessments")
def record_proposal_technical_assessment(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "EDIT_TECHNICAL")
    try:
        row = record_technical_assessment(db, proposal_id, payload, actor=_actor(role))
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_TECHNICAL_ASSESSMENT_RECORDED", entity_type="ProposalTechnicalAssessment", entity_id=row.id, actor_id=_actor(role), after={"proposal_id": proposal_id, "status": row.status, "assessment_hash": row.assessment_hash})
    db.commit()
    return _control_result(row)


@router.post("/{proposal_id}/scope-confirmations")
def confirm_proposal_scope(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    try:
        row = confirm_scope(db, proposal_id, payload, actor=_actor(role), capability="BD_PROPOSAL_WRITE", correlation_id=request.state.correlation_id)
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_SCOPE_CONFIRMED", entity_type="ProposalScopeConfirmation", entity_id=row.id, actor_id=_actor(role), after={"proposal_id": proposal_id, "scope_revision_hash": row.scope_revision_hash, "service_offering_codes": row.service_offering_codes})
    db.commit()
    return _control_result(row)


@router.post("/{proposal_id}/service-eligibility")
def record_proposal_service_eligibility(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    try:
        row = record_eligibility(db, proposal_id, payload, actor=_actor(role))
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_SERVICE_ELIGIBILITY_RECORDED", entity_type="ProposalServiceEligibility", entity_id=row.id, actor_id=_actor(role), after={"proposal_id": proposal_id, "service_offering_code": row.service_offering_code, "result": row.result})
    db.commit()
    return _control_result(row)


@router.post("/{proposal_id}/commercial-release")
def authorize_proposal_commercial_release(proposal_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_ACCEPT")
    try:
        row, idempotent = authorize_release(db, proposal_id, payload or {}, actor=_actor(role), capability="BD_PROPOSAL_ACCEPT", correlation_id=request.state.correlation_id)
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_COMMERCIAL_RELEASE_AUTHORIZED", entity_type="ProposalCommercialRelease", entity_id=row.id, actor_id=_actor(role), after={"proposal_id": proposal_id, "accepted_revision_id": row.accepted_revision_id, "content_hash": row.content_hash, "idempotent": idempotent})
    db.commit()
    return _control_result(row, idempotent=idempotent)


@router.post("/{proposal_id}/distribution")
def record_proposal_distribution(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    try:
        row, idempotent = record_distribution(db, proposal_id, payload, actor=_actor(role), correlation_id=request.state.correlation_id)
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_DISTRIBUTED", entity_type="ProposalDistributionEvent", entity_id=row.id, actor_id=_actor(role), after={"proposal_id": proposal_id, "accepted_revision_id": row.accepted_revision_id, "channel": row.channel, "evidence_reference": row.evidence_reference, "idempotent": idempotent})
    db.commit()
    return _control_result(row, idempotent=idempotent)


@router.post("/{proposal_id}/acceptance-verification")
def verify_proposal_client_acceptance(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    try:
        row, idempotent = verify_acceptance(db, proposal_id, payload, actor=_actor(role), correlation_id=request.state.correlation_id)
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_CLIENT_ACCEPTANCE_VERIFIED", entity_type="ProposalAcceptanceVerification", entity_id=row.id, actor_id=_actor(role), after={"proposal_id": proposal_id, "accepted_revision_id": row.accepted_revision_id, "client_response_id": row.client_response_id, "idempotent": idempotent})
    db.commit()
    return _control_result(row, idempotent=idempotent)


@router.post("/{proposal_id}/lpo-reconciliation")
def reconcile_proposal_lpo(proposal_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    try:
        row, idempotent = reconcile_lpo(db, proposal_id, payload, actor=_actor(role), correlation_id=request.state.correlation_id)
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_LPO_RECONCILIATED", entity_type="ProposalLpoReconciliation", entity_id=row.id, actor_id=_actor(role), after={"proposal_id": proposal_id, "accepted_revision_id": row.accepted_revision_id, "result": row.result, "variance_count": len(row.variances), "idempotent": idempotent})
    db.commit()
    return _control_result(row, idempotent=idempotent)


@router.get("/{proposal_id}/outputs")
def outputs(proposal_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    return {"items": [{"id": item.id, "artifact_type": item.artifact_type, "filename": item.filename, "content_hash": item.content_hash, "document_version_id": item.document_version_id, "storage_reference": item.storage_reference, "synthetic_only": item.synthetic_only, "lineage": item.lineage, "download": f"/api/bd/proposals/{proposal_id}/outputs/{item.artifact_type.lower()}"} for item in db.scalars(select(ProposalOutputArtifact).where(ProposalOutputArtifact.proposal_id == proposal_id).order_by(ProposalOutputArtifact.created_at.desc())).all()]}


@router.get("/{proposal_id}/outputs/{artifact_type}")
def download_output(proposal_id: str, artifact_type: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    artifact = db.scalar(select(ProposalOutputArtifact).where(ProposalOutputArtifact.proposal_id == proposal_id, ProposalOutputArtifact.artifact_type == artifact_type.upper()).order_by(ProposalOutputArtifact.created_at.desc()))
    revision = db.get(ProposalAcceptedRevision, artifact.revision_id) if artifact else None
    if not artifact or not revision:
        raise HTTPException(404, "OUTPUT_NOT_FOUND")
    if artifact.synthetic_only:
        if not synthetic_test_mode():
            raise HTTPException(409, "SYNTHETIC_OUTPUT_FORBIDDEN")
        content = output_bytes(revision, artifact.artifact_type)
    else:
        if not artifact.document_version_id:
            raise HTTPException(409, "OUTPUT_DOCUMENT_VERSION_REQUIRED")
        version = db.get(DocumentVersion, artifact.document_version_id)
        if not version:
            raise HTTPException(409, "OUTPUT_DOCUMENT_VERSION_REQUIRED")
        try:
            with DocumentStorageService(create_binary_store()).read_verified(version) as readback:
                content = readback.read()
        except StorageError as exc:
            raise domain_error(503, "OUTPUT_STORAGE_READBACK_FAILED", storage_code=exc.code.value) from exc
    if hashlib.sha256(content).hexdigest() != artifact.content_hash or len(content) != artifact.file_size:
        raise HTTPException(409, "OUTPUT_LINEAGE_MISMATCH")
    return StreamingResponse(iter([content]), media_type=artifact.content_type, headers={"Content-Disposition": f'attachment; filename="{artifact.filename}"', "X-Proposal-Revision": str(revision.revision_number), "X-Artifact-Hash": artifact.content_hash})


@router.get("/{proposal_id}/handoff/contract")
def contract_handoff_preview(proposal_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    predicate = handoff_predicate(db, proposal_id)
    if not predicate.get("accepted_revision_id"):
        raise HTTPException(409, "ACCEPTED_REVISION_REQUIRED")
    return {**predicate, "contract_trigger": "OWNER_DECISION_REQUIRED", "machine_legal_contract": False, "project_activation_created": False}


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
        handoff_row, handoff_idempotent = create_proposal_handoff(db, proposal_id, {}, actor=_actor(role, actor), correlation_id=request.state.correlation_id)
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    try:
        contract = create_contract_from_proposal(db, proposal=proposal, accepted=revision, actor=_actor(role, actor), correlation_id=request.state.correlation_id)
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_CONTRACT_HANDOFF", entity_type="Opportunity", entity_id=proposal.id, actor_id=_actor(role, actor), after={"accepted_revision_id": revision.id, "contract_id": contract.id, "machine_legal_contract": False})
    db.commit()
    artifacts = {item.artifact_type: {"id": item.id, "filename": item.filename, "content_hash": item.content_hash} for item in db.scalars(select(ProposalOutputArtifact).where(ProposalOutputArtifact.revision_id == revision.id)).all()}
    fields = revision.snapshot.get("fields", {})
    client = db.get(ClientAccount, client_id)
    return {"contract_id": contract.id, "contract_reference": contract.contract_reference, "handoff_id": handoff_row.id, "handoff_idempotent": handoff_idempotent, "contract_handoff_eligible": True, "proposal_id": proposal.id, "proposal_reference": proposal.opportunity_reference, "accepted_revision_id": revision.id, "revision_number": revision.revision_number, "content_hash": revision.content_hash, "client": client.display_name if client else client_id, "project_reference": revision.snapshot.get("project_reference"), "project_description": fields.get("project_description") or revision.snapshot.get("title"), "scope": fields.get("scope_of_work") or fields.get("sow"), "amount": fields.get("price"), "currency": fields.get("currency"), "duration": fields.get("duration") or fields.get("period"), "proposal_artifact": artifacts.get("PROPOSAL"), "checklist_artifact": artifacts.get("CHECKLIST"), "source_ids": revision.snapshot.get("source_ids", []), "template": revision.snapshot.get("template"), "checklist": revision.snapshot.get("checklist"), "forms_driven_v2": revision.snapshot.get("forms_driven_v2"), "status": proposal.status, "machine_legal_contract": False, "creates_project_code": False, "creates_authority_case": False, "creates_regulatory_journey": False}


@router.post("/{proposal_id}/handoff/contract-eligibility")
def contract_handoff_eligibility(proposal_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), actor: str | None = None):
    """Persist Proposal→Contract handoff eligibility without creating a Contract."""
    require_capability(role, "BD_PROPOSAL_WRITE")
    try:
        row, idempotent = create_proposal_handoff(db, proposal_id, {}, actor=_actor(role, actor), correlation_id=request.state.correlation_id)
    except ValueError as exc:
        raise domain_error(409, str(exc)) from exc
    db.commit()
    return {"result": "IDEMPOTENT" if idempotent else "ELIGIBLE", "handoff_id": row.id, "proposal_id": proposal_id, "accepted_revision_id": row.accepted_revision_id, "status": row.status, "contract_created": False, "project_activation_created": False, "machine_legal_contract": False}


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
