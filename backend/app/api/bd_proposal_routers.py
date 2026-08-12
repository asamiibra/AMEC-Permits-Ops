"""BD Proposal list and owner workbench API."""

from __future__ import annotations

import hashlib
import os
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
from ..models import AuditEvent, ClientAccount, ConsultancyOffice, Contract, ContractRevision, Opportunity, ProposalAcceptedRevision, ProposalIntakeArtifact, ProposalOutputArtifact, ProposalOwnerSetting, ProposalSourceEvidence, Quotation, QuotationRevision, ReferenceNumber, Role
from ..config.settings import get_settings as app_settings
from ..services.backend_realignment import domain_error, require_capability
from ..services.master_content import definition_lookup
from ..services.proposal_workspace import SOURCE_TYPES, SOURCE_TO_SEMANTIC, ensure_owner_settings, master_content_purpose, output_bytes, proposal_projection, snapshot_for_accept, stable_hash, validate_proposal
from ..services.proposals_sor import ingest_provisional_intake_artifact

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


class OwnerSettingsPatch(BaseModel):
    settings: dict[str, dict[str, Any]]


def _actor(role: Role, supplied: str | None = None) -> str:
    return supplied or getattr(role, "value", str(role))


def _list_row(db: Session, item: Opportunity) -> dict[str, Any]:
    projection = proposal_projection(db, item)
    return {"id": item.id, "proposal_reference": item.opportunity_reference, "proposal": item.title, "project_ref": projection["project_reference"], "client": projection["client_name"] or item.client_account_id or "Not recorded", "stage": projection["stage_label"], "stage_code": item.status, "amount": projection["amount"], "last_activity": projection["last_activity"], "location": (item.proposal_fields_json or {}).get("location"), "contract_eligible": projection["contract_eligible"], "validation": projection["validation"]}


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
        db.query(ProposalOutputArtifact).filter(ProposalOutputArtifact.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalAcceptedRevision).filter(ProposalAcceptedRevision.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalSourceEvidence).filter(ProposalSourceEvidence.proposal_id == proposal_id).delete(synchronize_session=False)
        db.query(ProposalIntakeArtifact).filter(ProposalIntakeArtifact.opportunity_id == proposal_id).delete(synchronize_session=False)
        db.query(AuditEvent).filter(AuditEvent.entity_id == proposal_id).delete(synchronize_session=False)
        client = db.get(ClientAccount, proposal.client_account_id) if proposal.client_account_id else None
        db.delete(proposal)
        if client and client.client_reference.startswith("AMEC-SYN-CLIENT-") and not db.scalar(select(Opportunity).where(Opportunity.client_account_id == client.id, Opportunity.id != proposal_id)):
            db.delete(client)
        rmtree(intake_sor_root() / reference, ignore_errors=True)
        removed.append(proposal_id)
    db.commit()
    return {"status": "APPLIED", "removed": removed}


@router.get("")
def list_proposals(q: str = "", stage: str | None = None, location: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    rows = [_list_row(db, item) for item in db.scalars(select(Opportunity).order_by(Opportunity.updated_at.desc(), Opportunity.opportunity_reference)).all()]
    needle = q.strip().lower()
    if needle:
        rows = [row for row in rows if needle in " ".join(str(row.get(key) or "").lower() for key in ("proposal", "proposal_reference", "project_ref", "client", "location"))]
    if stage:
        rows = [row for row in rows if row["stage_code"] == stage.upper()]
    if location:
        rows = [row for row in rows if str(row.get("location") or "").lower() == location.lower()]
    return {"items": rows, "rows": rows, "count": len(rows), "filters": {"q": q, "stage": stage, "location": location}, "stage_options": ["RECEIVED", "IN_REVIEW", "PROPOSAL_PREPARATION", "PROPOSAL_HANDOVER", "ACCEPTED", "CONTRACT_HANDOVER", "CLOSED"], "amount_source": "proposal_fields.price", "last_activity_source": "Opportunity.updated_at", "synthetic_only": True}


@router.post("")
def create_proposal(payload: ProposalCreate, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    office = db.scalar(select(ConsultancyOffice).order_by(ConsultancyOffice.office_code))
    if not office:
        raise HTTPException(503, "OFFICE_CONTEXT_REQUIRED")
    client_id = payload.client_account_id
    if not client_id and payload.client_name:
        client = ClientAccount(client_reference=f"AMEC-SYN-CLIENT-{db.query(ClientAccount).count() + 1:04d}", legal_name=payload.client_name.strip(), display_name=payload.client_name.strip(), client_type="COMPANY", data_classification="SYNTHETIC", status="ACTIVE")
        db.add(client)
        db.flush()
        client_id = client.id
    number = db.query(Opportunity).count() + 1
    reference = f"AMEC-SYN-PROP-{number:04d}"
    fields = {"client_name": payload.client_name, "project_reference": payload.project_reference, "provenance": {"client_name": "manual", "project_reference": "manual"}}
    fields = {key: value for key, value in fields.items() if value is not None}
    item = Opportunity(office_id=office.id, client_account_id=client_id, opportunity_reference=reference, title=payload.proposal_description.strip(), status="IN_REVIEW", source_type="BD_WORKSPACE", project_id=payload.project_id, reference_state="CANONICAL" if payload.project_id else "PROVISIONAL", proposal_fields_json=fields, provisional_reference=reference, canonical_project_reference=payload.project_reference)
    db.add(item)
    db.flush()
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_DRAFT_CREATED", entity_type="Opportunity", entity_id=item.id, actor_id=_actor(role), after={"proposal_reference": reference, "status": item.status})
    db.commit()
    return proposal_projection(db, item)


@router.get("/master-content")
def proposal_master_content(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    return {"proposal_template": master_content_purpose(db, "PROPOSAL_TEMPLATE"), "proposal_checklist": master_content_purpose(db, "PROPOSAL_CHECKLIST"), "definitions": {"lookup": "/api/definitions/lookup/{term}", "truth": "DASHBOARD_DEFINITIONS"}}


@router.get("/{proposal_id}")
def get_proposal(proposal_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_READ")
    item = db.get(Opportunity, proposal_id)
    if not item:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    return proposal_projection(db, item)


@router.patch("/{proposal_id}")
def patch_proposal(proposal_id: str, payload: ProposalFieldsPatch, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    item = db.get(Opportunity, proposal_id)
    if not item:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    current = dict(item.proposal_fields_json or {})
    current.update(payload.fields or {})
    if payload.amec_input is not None:
        current["amec_input"] = payload.amec_input
    if payload.provenance is not None:
        current["provenance"] = {**(current.get("provenance") or {}), **payload.provenance}
    item.proposal_fields_json = current
    item.status = item.status if item.status not in {"RECEIVED", "IN_REVIEW"} else "IN_REVIEW"
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_FIELDS_UPDATED", entity_type="Opportunity", entity_id=item.id, actor_id=_actor(role), after={"field_keys": sorted(payload.fields.keys()), "amec_input_updated": payload.amec_input is not None})
    db.commit()
    return proposal_projection(db, item)


@router.post("/{proposal_id}/sources")
async def add_source(proposal_id: str, request: Request, source_type: str = Form(...), file: UploadFile = File(...), source_revision: str | None = Form(default=None), actor: str | None = Form(default=None), idempotency_key: str | None = Form(default=None), db: Session = Depends(get_db), role: Role = Depends(current_user_role), x_synthetic_sor: str | None = Header(default=None)):
    require_capability(role, "BD_PROPOSAL_WRITE")
    proposal = db.get(Opportunity, proposal_id)
    source_type = source_type.upper()
    if not proposal:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    if source_type not in SOURCE_TYPES:
        raise HTTPException(422, {"code": "SOURCE_TYPE_REQUIRED", "allowed": list(SOURCE_TYPES)})
    content = await file.read()
    semantic = SOURCE_TO_SEMANTIC[source_type]
    digest = hashlib.sha256(content).hexdigest()
    # Vercel TEST has durable PostgreSQL but a read-only deployment bundle.
    # Preserve the verified source index and hash there; local TEST continues
    # to exercise the MockSynologyAdapter filesystem path.
    if app_settings().app_env.upper() == "TEST" and os.environ.get("VERCEL"):
        result = {"id": str(uuid4()), "source_filename": file.filename or "source.bin", "sor_path": f"synthetic://proposal-source/{proposal.opportunity_reference}/{source_type.lower()}/{digest}", "content_hash": digest, "verification_state": "READ_BACK_VERIFIED", "semantic_class": semantic}
    else:
        result = ingest_provisional_intake_artifact(db, opportunity=proposal, semantic_class=semantic, source_filename=file.filename or "source.bin", content_type=file.content_type or "application/octet-stream", content=content, actor=_actor(role, actor), source_revision=source_revision, idempotency_key=idempotency_key, correlation_id=request.state.correlation_id)
    existing = db.scalar(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id, ProposalSourceEvidence.source_type == source_type, ProposalSourceEvidence.status == "CURRENT").order_by(ProposalSourceEvidence.created_at.desc()))
    if existing and existing.content_hash != digest:
        existing.status = "CONFLICT"
    evidence = db.scalar(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id, ProposalSourceEvidence.source_type == source_type, ProposalSourceEvidence.content_hash == digest))
    if not evidence:
        evidence = ProposalSourceEvidence(proposal_id=proposal.id, source_type=source_type, source_filename=result["source_filename"], source_reference=result["sor_path"], content_hash=digest, content_type=file.content_type or "application/octet-stream", source_revision=source_revision, provenance={"kind": "source", "source_artifact_id": result["id"], "semantic_class": semantic, "verification": result["verification_state"]}, conflict_key=source_type, status="CURRENT", verification_state=result["verification_state"], supersedes_id=existing.id if existing else None, created_by=_actor(role, actor))
        db.add(evidence)
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_SOURCE_REGISTERED", entity_type="Opportunity", entity_id=proposal.id, actor_id=_actor(role, actor), after={"source_type": source_type, "source_evidence_id": evidence.id, "content_hash": digest, "conflict": bool(existing and existing.content_hash != digest)})
    db.commit()
    return {"source": {"id": evidence.id, "source_type": evidence.source_type, "content_hash": evidence.content_hash, "verification_state": evidence.verification_state, "status": evidence.status, "source_reference": evidence.source_reference}, "proposal": proposal_projection(db, proposal)}


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
    item = db.get(Opportunity, proposal_id)
    if not item:
        raise HTTPException(404, "PROPOSAL_NOT_FOUND")
    check = validate_proposal(db, item)
    if not check["ready"]:
        raise domain_error(409, "PROPOSAL_ACCEPT_BLOCKED", blockers=check["blockers"], warnings=check["warnings"])
    snapshot = snapshot_for_accept(db, item, check)
    prior = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == item.id).order_by(ProposalAcceptedRevision.revision_number.desc()))
    revision_number = (prior.revision_number + 1) if prior else 1
    content_hash = stable_hash(snapshot)
    revision = ProposalAcceptedRevision(proposal_id=item.id, revision_number=revision_number, snapshot=snapshot, validation_snapshot=check, template_ref=check["template"]["item"]["ref"], template_version_id=check["template"]["item"]["version_id"], template_version=str(check["template"]["item"]["version"]), template_hash=check["template"]["item"]["hash"], checklist_ref=check["checklist"]["item"]["ref"], checklist_version_id=check["checklist"]["item"]["version_id"], checklist_version=str(check["checklist"]["item"]["version"]), checklist_hash=check["checklist"]["item"]["hash"], definition_refs=[item["ref"] for item in check["definitions"]], content_hash=content_hash, accepted_by=_actor(role, actor), supersedes_revision_id=prior.id if prior else None)
    db.add(revision)
    db.flush()
    for artifact_type, filename in (("PROPOSAL", f"{item.opportunity_reference}-r{revision_number}-proposal.txt"), ("CHECKLIST", f"{item.opportunity_reference}-r{revision_number}-checklist.txt")):
        content = output_bytes(revision, artifact_type)
        db.add(ProposalOutputArtifact(revision_id=revision.id, proposal_id=item.id, artifact_type=artifact_type, filename=filename, content_type="text/plain", content_hash=hashlib.sha256(content).hexdigest(), storage_reference=f"synthetic://proposal-output/{revision.id}/{artifact_type.lower()}", lineage={"accepted_revision_id": revision.id, "proposal_content_hash": content_hash, "template_version_id": revision.template_version_id, "checklist_version_id": revision.checklist_version_id, "source_ids": snapshot["source_ids"]}, file_size=len(content), synthetic_only=True))
    item.status = "ACCEPTED"
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_HUMAN_ACCEPTED", entity_type="Opportunity", entity_id=item.id, actor_id=_actor(role, actor), after={"accepted_revision_id": revision.id, "revision_number": revision_number, "content_hash": content_hash, "machine_accept": False})
    db.commit()
    return proposal_projection(db, item)


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
    proposal = db.get(Opportunity, proposal_id)
    revision = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == proposal_id).order_by(ProposalAcceptedRevision.revision_number.desc()))
    if not proposal or not revision:
        raise HTTPException(409, "ACCEPTED_REVISION_REQUIRED")
    client_id = proposal.client_account_id
    if not client_id:
        raise HTTPException(409, "CLIENT_CONTEXT_REQUIRED")
    quotation = db.scalar(select(Quotation).where(Quotation.opportunity_id == proposal.id).order_by(Quotation.created_at.desc()))
    if not quotation:
        quotation = Quotation(opportunity_id=proposal.id, quotation_reference=f"AMEC-SYN-QTN-{db.query(Quotation).count() + 1:04d}", status="RELEASED_FOR_CONTRACT", client_account_id=client_id)
        db.add(quotation)
        db.flush()
        quotation_revision = QuotationRevision(quotation_id=quotation.id, revision_number=1, source_snapshot=revision.snapshot, content_hash=revision.content_hash, semantic_hash=stable_hash(revision.snapshot.get("fields", {})), status="RELEASED", created_by=_actor(role, actor))
        db.add(quotation_revision)
        db.flush()
        quotation.current_revision_id = quotation_revision.id
    contract = db.scalar(select(Contract).where(Contract.quotation_id == quotation.id).order_by(Contract.created_at.desc()))
    if not contract:
        contract = Contract(client_account_id=client_id, quotation_id=quotation.id, contract_reference=f"AMEC-SYN-CTR-{db.query(Contract).count() + 1:04d}", status="DRAFT", project_id=proposal.project_id)
        db.add(contract)
        db.flush()
        db.add(ContractRevision(contract_id=contract.id, revision_number=1, controlling_quotation_revision_id=quotation.current_revision_id, status="DRAFT", commercial_terms_snapshot={**revision.snapshot.get("fields", {}), "proposal_accepted_revision_id": revision.id, "proposal_content_hash": revision.content_hash}))
    proposal.status = "CONTRACT_HANDOVER"
    audit(db, correlation_id=request.state.correlation_id, event_type="BD_PROPOSAL_CONTRACT_HANDOFF", entity_type="Opportunity", entity_id=proposal.id, actor_id=_actor(role, actor), after={"accepted_revision_id": revision.id, "contract_id": contract.id, "machine_legal_contract": False})
    db.commit()
    return {"contract_id": contract.id, "contract_reference": contract.contract_reference, "proposal_id": proposal.id, "accepted_revision_id": revision.id, "revision_number": revision.revision_number, "content_hash": revision.content_hash, "status": proposal.status, "machine_legal_contract": False}


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
