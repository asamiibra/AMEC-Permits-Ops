"""Source-18 Owner/Engineering workflow APIs."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..models import (
    AuthorityCase,
    ConsultancyOffice,
    ExternalBody,
    Jurisdiction,
    RegulatoryJourney,
    Project,
    ServiceType,
    Source18EngineerProfile,
    Source18ExternalComment,
    Source18OfficialFormVersion,
    Source18PacketRevision,
    Source18PolicyVersion,
    Source18RosterMembership,
    Source18SubmissionCycle,
    Source18WorkflowTransaction,
    RequirementPolicyVersion,
    Role,
)
from ..services.source18 import (
    CAPABILITIES,
    TRANSACTION_MODES,
    _hash,
    _now,
    case_row,
    enforce_staffing_gate,
    packet_manifest,
    packet_row,
    refresh_packet_hash,
    require_capability,
    staffing_readiness,
    transition,
    transaction_states,
    validate_source_currentness,
)


router = APIRouter(prefix="/api/source18", tags=["source18-engineers-acceptance-committee"])


def _actor(request: Request, role: Role) -> str:
    return request.headers.get("X-Dev-Actor") or role.value


def _corr(request: Request) -> str:
    return getattr(request.state, "correlation_id", str(uuid4()))


def _public_engineer(item: Source18EngineerProfile) -> dict[str, Any]:
    return {"id": item.id, "office_id": item.office_id, "engineer_ref": item.engineer_ref, "display_name": item.display_name, "discipline": item.discipline, "grade_category": item.grade_category, "registration_number_present": bool(item.registration_number), "status": item.status, "regulatory_profile_state": item.regulatory_profile_state, "evidence_currentness": item.evidence_currentness}


def _public_transaction(item: Source18WorkflowTransaction) -> dict[str, Any]:
    return {key: value for key, value in item.__dict__.items() if not key.startswith("_") and key not in {"source_snapshot_json"}}


@router.get("/capabilities")
def capabilities(role: Role = Depends(current_user_role)):
    return {"role": role.value, "capabilities": sorted(CAPABILITIES.get(role.value, set()))}


@router.get("/offices/{office_id}/overview")
def office_overview(office_id: str, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "VIEW_REGULATORY_CASE")
    office = db.get(ConsultancyOffice, office_id)
    if not office:
        raise HTTPException(404, {"code": "OFFICE_NOT_FOUND"})
    engineers = db.scalars(select(Source18EngineerProfile).where(Source18EngineerProfile.office_id == office_id).order_by(Source18EngineerProfile.display_name)).all()
    memberships = db.scalars(select(Source18RosterMembership).where(Source18RosterMembership.office_id == office_id, Source18RosterMembership.status == "ACTIVE")).all()
    policies = db.scalars(select(Source18PolicyVersion).where(Source18PolicyVersion.policy_code == "OFFICE_STAFFING").order_by(Source18PolicyVersion.created_at.desc())).all()
    current_policy = next((item for item in policies if item.status == "CURRENT"), None)
    try:
        readiness = staffing_readiness(db, office_id)
    except HTTPException as exc:
        if exc.detail.get("code") != "STAFFING_POLICY_UNKNOWN_FAIL_CLOSED":
            raise
        readiness = {"required_count": None, "regulator_counted": None, "buffer_or_gap": None, "at_risk_engineers": [], "expired_or_expiring_engineers": [], "pending_replacements": [], "pending_roster_additions": [], "current_regulatory_entitlement": None, "source_policy_version": current_policy.version if current_policy else None, "assessment_time": _now().isoformat(), "currentness": "UNKNOWN"}
    return {"office": {"id": office.id, "office_code": office.office_code, "name_en": office.name_en, "name_ar": office.name_ar}, "engineers": [_public_engineer(item) for item in engineers], "readiness": readiness, "roster_count": len(memberships), "source18": True}


@router.post("/offices/{office_id}/policies")
def create_policy(office_id: str, payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "MANAGE_REGULATORY_POLICY")
    if not db.get(ConsultancyOffice, office_id):
        raise HTTPException(404, {"code": "OFFICE_NOT_FOUND"})
    policy = Source18PolicyVersion(policy_code=str(payload.get("policy_code") or "OFFICE_STAFFING"), version=str(payload.get("version") or "").strip(), status=str(payload.get("status") or "UNKNOWN").upper(), source_class=str(payload.get("source_class") or "REGULATORY_SOURCE_REQUIRED"), source_reference=payload.get("source_reference"), rules_json=payload.get("rules") or {}, created_by=_actor(request, role))
    if not policy.version:
        raise HTTPException(422, {"code": "POLICY_VERSION_REQUIRED"})
    if policy.status == "CURRENT":
        db.query(Source18PolicyVersion).filter(Source18PolicyVersion.policy_code == policy.policy_code, Source18PolicyVersion.status == "CURRENT").update({"status": "SUPERSEDED"})
    db.add(policy); db.commit(); db.refresh(policy)
    return {key: value for key, value in policy.__dict__.items() if not key.startswith("_")}


@router.post("/official-form-versions")
def create_official_form_version(payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "MANAGE_REGULATORY_POLICY")
    item = Source18OfficialFormVersion(form_code=str(payload.get("form_code") or "").strip(), version=str(payload.get("version") or "").strip(), status=str(payload.get("status") or "UNKNOWN").upper(), currentness_state=str(payload.get("currentness_state") or "UNKNOWN").upper(), source_document_version_id=payload.get("source_document_version_id"), provenance_json=payload.get("provenance") or {})
    if not item.form_code or not item.version:
        raise HTTPException(422, {"code": "OFFICIAL_FORM_VERSION_REQUIRED"})
    if item.currentness_state == "CURRENT":
        db.query(Source18OfficialFormVersion).filter(Source18OfficialFormVersion.form_code == item.form_code, Source18OfficialFormVersion.currentness_state == "CURRENT").update({"currentness_state": "SUPERSEDED", "status": "SUPERSEDED"})
    db.add(item); db.commit(); db.refresh(item)
    return {key: value for key, value in item.__dict__.items() if not key.startswith("_")}


@router.post("/offices/{office_id}/engineers")
def create_engineer(office_id: str, payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "EDIT_REGULATORY_PII")
    if not db.get(ConsultancyOffice, office_id):
        raise HTTPException(404, {"code": "OFFICE_NOT_FOUND"})
    item = Source18EngineerProfile(office_id=office_id, engineer_ref=str(payload.get("engineer_ref") or "").strip(), display_name=str(payload.get("display_name") or "").strip(), discipline=str(payload.get("discipline") or "").strip(), grade_category=payload.get("grade_category"), registration_number=payload.get("registration_number"), status=str(payload.get("status") or "ACTIVE").upper(), regulatory_profile_state=str(payload.get("regulatory_profile_state") or "UNKNOWN").upper(), raw_pii_json=payload.get("raw_pii") or {}, current_evidence_document_version_id=payload.get("evidence_document_version_id"), current_policy_version_id=payload.get("policy_version_id"), evidence_currentness=str(payload.get("evidence_currentness") or "UNKNOWN").upper())
    if not item.engineer_ref or not item.display_name or not item.discipline:
        raise HTTPException(422, {"code": "ENGINEER_PROFILE_FIELDS_REQUIRED"})
    db.add(item); db.commit(); db.refresh(item)
    return {"engineer": _public_engineer(item), "raw_pii_stored": bool(item.raw_pii_json), "raw_pii_returned": False}


@router.get("/engineers/{engineer_id}/pii")
def get_engineer_pii(engineer_id: str, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "VIEW_RAW_REGULATORY_PII")
    item = db.get(Source18EngineerProfile, engineer_id)
    if not item:
        raise HTTPException(404, {"code": "ENGINEER_PROFILE_NOT_FOUND"})
    return {"engineer_id": item.id, "raw_pii": item.raw_pii_json, "access_auditable": True}


@router.post("/cases")
def create_case(payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "EDIT_REGULATORY_CASE")
    office_id = str(payload.get("office_id") or "")
    office = db.get(ConsultancyOffice, office_id)
    if not office:
        raise HTTPException(422, {"code": "OFFICE_REQUIRED"})
    processing_mode = str(payload.get("processing_mode") or "").upper()
    transaction_type = str(payload.get("transaction_type") or "").upper()
    if transaction_type not in TRANSACTION_MODES:
        raise HTTPException(422, {"code": "SOURCE18_TRANSACTION_TYPE_REQUIRED"})
    if processing_mode != TRANSACTION_MODES[transaction_type]:
        raise HTTPException(409, {"code": "SOURCE18_PROCESSING_MODE_MISMATCH", "expected": TRANSACTION_MODES[transaction_type]})
    subject_type = str(payload.get("subject_type") or "OFFICE").upper()
    if subject_type not in {"OFFICE", "ENGINEER", "PROJECT"}:
        raise HTTPException(422, {"code": "SOURCE18_SUBJECT_TYPE_UNSUPPORTED"})
    service = db.get(ServiceType, payload.get("service_type_id")) if payload.get("service_type_id") else db.scalar(select(ServiceType).order_by(ServiceType.created_at))
    jurisdiction = db.get(Jurisdiction, payload.get("jurisdiction_id")) if payload.get("jurisdiction_id") else db.scalar(select(Jurisdiction).order_by(Jurisdiction.created_at))
    body = db.get(ExternalBody, payload.get("external_body_id")) if payload.get("external_body_id") else db.scalar(select(ExternalBody).order_by(ExternalBody.created_at))
    if not service or not jurisdiction or not body:
        raise HTTPException(422, {"code": "REGULATORY_CATALOG_CONTEXT_REQUIRED"})
    idem = str(payload.get("idempotency_key") or "").strip()
    if not idem:
        raise HTTPException(422, {"code": "IDEMPOTENCY_KEY_REQUIRED"})
    existing_tx = db.scalar(select(Source18WorkflowTransaction).where(Source18WorkflowTransaction.idempotency_key == idem))
    if existing_tx:
        return {"case": case_row(db.get(AuthorityCase, existing_tx.authority_case_id)), "transaction": _public_transaction(existing_tx), "idempotent_replay": True}
    profile = db.get(Source18EngineerProfile, payload.get("engineer_profile_id")) if payload.get("engineer_profile_id") else None
    if payload.get("engineer_profile_id") and (not profile or profile.office_id != office_id):
        raise HTTPException(422, {"code": "ENGINEER_PROFILE_NOT_IN_OFFICE"})
    project_id = payload.get("project_id")
    project = db.get(Project, project_id) if project_id else None
    if project_id and (not project or project.office_id != office_id):
        raise HTTPException(422, {"code": "PROJECT_NOT_IN_OFFICE"})
    if subject_type == "PROJECT" and not project:
        raise HTTPException(422, {"code": "PROJECT_REQUIRED_FOR_PROJECT_SUBJECT"})
    if subject_type == "ENGINEER" and not profile:
        raise HTTPException(422, {"code": "ENGINEER_PROFILE_REQUIRED_FOR_ENGINEER_SUBJECT"})
    if project and subject_type != "PROJECT":
        raise HTTPException(409, {"code": "PROJECT_SUBJECT_REQUIRED_FOR_PROJECT_SCOPED_CASE"})
    journey = None
    if project:
        journey = RegulatoryJourney(journey_code=f"S18-{uuid4().hex[:12].upper()}", project_id=project.id, service_type_id=service.id, jurisdiction_id=jurisdiction.id, external_body_id=body.id, status="DRAFT", created_by=_actor(request, role))
        db.add(journey); db.flush()
    case = AuthorityCase(case_reference=str(payload.get("case_reference") or f"S18-{uuid4().hex[:12].upper()}"), regulatory_journey_id=journey.id if journey else None, external_body_id=body.id, service_type_id=service.id, jurisdiction_id=jurisdiction.id, status="DRAFT", subject_type=subject_type, subject_id=project.id if project else (profile.id if profile else office_id), created_by=_actor(request, role))
    db.add(case); db.flush()
    requested = [str(value) for value in (payload.get("requested_disciplines") or [])]
    current = [str(value) for value in (payload.get("current_disciplines") or [])]
    tx = Source18WorkflowTransaction(authority_case_id=case.id, office_id=office_id, transaction_type=transaction_type, processing_mode=processing_mode, state=transaction_states(transaction_type)[0], engineer_profile_id=profile.id if profile else None, current_policy_version_id=payload.get("policy_version_id"), official_form_version_id=payload.get("official_form_version_id"), requirement_version_id=payload.get("requirement_version_id"), currentness_state=str(payload.get("currentness_state") or "UNKNOWN").upper(), remediation_exception=bool(payload.get("remediation_exception", False)), requested_disciplines_json=requested, current_disciplines_json=current, idempotency_key=idem, actor_ref=_actor(request, role), source_snapshot_json={"source_class": payload.get("source_class", "OWNER_SOURCE_18"), "captured_at": _now().isoformat()})
    if transaction_type == "OFFICE_RENEWAL" and set(requested) - set(current):
        raise HTTPException(409, {"code": "RENEWAL_SCOPE_WIDENING_REQUIRES_EXPLICIT_SOURCE_SCOPE"})
    db.add(tx); db.flush(); audit(db, correlation_id=_corr(request), event_type="SOURCE18_CASE_CREATED", entity_type="AuthorityCase", entity_id=case.id, actor_id=_actor(request, role), after={"transaction_id": tx.id, "processing_mode": processing_mode, "subject_type": "OFFICE"}); db.commit(); db.refresh(case); db.refresh(tx)
    return {"case": case_row(case), "transaction": _public_transaction(tx), "idempotent_replay": False}


@router.get("/transactions/{transaction_id}")
def get_transaction(transaction_id: str, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "VIEW_REGULATORY_CASE")
    tx = db.get(Source18WorkflowTransaction, transaction_id)
    if not tx:
        raise HTTPException(404, {"code": "SOURCE18_TRANSACTION_NOT_FOUND"})
    packets = db.scalars(select(Source18PacketRevision).where(Source18PacketRevision.transaction_id == tx.id).order_by(Source18PacketRevision.revision_number.desc())).all()
    cycles = db.scalars(select(Source18SubmissionCycle).where(Source18SubmissionCycle.transaction_id == tx.id).order_by(Source18SubmissionCycle.cycle_number.desc())).all()
    return {"transaction": _public_transaction(tx), "packets": [packet_row(item) for item in packets], "submission_cycles": [{key: value for key, value in item.__dict__.items() if not key.startswith("_") and key != "external_outcome_json"} for item in cycles]}


@router.post("/offices/{office_id}/roster-memberships")
def add_roster_membership(office_id: str, payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "MANAGE_ROSTER_UPDATE")
    engineer_id = str(payload.get("engineer_profile_id") or "")
    engineer = db.get(Source18EngineerProfile, engineer_id)
    if not db.get(ConsultancyOffice, office_id) or not engineer or engineer.office_id != office_id:
        raise HTTPException(422, {"code": "ENGINEER_PROFILE_NOT_IN_OFFICE"})
    membership = Source18RosterMembership(
        office_id=office_id, engineer_profile_id=engineer.id,
        discipline=str(payload.get("discipline") or engineer.discipline),
        regulator_counted_state="NOT_COUNTED", classified_engineer=bool(payload.get("classified_engineer", False)),
        inside_qatar=payload.get("inside_qatar"), status="PENDING_ADD",
        source_policy_version_id=payload.get("policy_version_id"), source_document_version_id=payload.get("source_document_version_id"),
    )
    db.add(membership); db.flush()
    audit(db, correlation_id=_corr(request), event_type="SOURCE18_ROSTER_ADD_PENDING", entity_type="Source18RosterMembership", entity_id=membership.id, actor_id=_actor(request, role), after={"regulator_counted_state": membership.regulator_counted_state})
    db.commit(); db.refresh(membership)
    return {key: value for key, value in membership.__dict__.items() if not key.startswith("_")}


@router.post("/transactions/{transaction_id}/responsible-engineer")
def designate_responsible_engineer(transaction_id: str, payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "MANAGE_RESPONSIBLE_ENGINEER_CHANGE")
    tx = db.get(Source18WorkflowTransaction, transaction_id)
    engineer = db.get(Source18EngineerProfile, payload.get("engineer_profile_id")) if payload.get("engineer_profile_id") else None
    change_type = str(payload.get("change_type") or "").upper()
    if not tx or tx.transaction_type != "RESPONSIBLE_ENGINEER_CHANGE":
        raise HTTPException(404, {"code": "SOURCE18_TRANSACTION_NOT_FOUND"})
    if not engineer or engineer.office_id != tx.office_id:
        raise HTTPException(422, {"code": "ENGINEER_PROFILE_NOT_IN_OFFICE"})
    if change_type not in {"ADD", "REPLACE"}:
        raise HTTPException(422, {"code": "RESPONSIBLE_ENGINEER_CHANGE_TYPE_REQUIRED"})
    if change_type == "ADD" and tx.responsible_engineer_profile_id:
        raise HTTPException(409, {"code": "RESPONSIBLE_ENGINEER_ALREADY_DESIGNATED_USE_REPLACE"})
    if change_type == "REPLACE" and not tx.responsible_engineer_profile_id:
        raise HTTPException(409, {"code": "RESPONSIBLE_ENGINEER_REPLACE_REQUIRES_EXISTING_DESIGNATION"})
    effective_from = payload.get("effective_from")
    if not effective_from:
        raise HTTPException(422, {"code": "RESPONSIBLE_ENGINEER_EFFECTIVE_DATE_REQUIRED"})
    validate_source_currentness(db, tx)
    tx.responsible_engineer_profile_id = engineer.id
    tx.responsible_engineer_effective_from = date.fromisoformat(str(effective_from))
    tx.responsible_engineer_change_type = change_type
    audit(db, correlation_id=_corr(request), event_type="SOURCE18_RESPONSIBLE_ENGINEER_DESIGNATED", entity_type="Source18WorkflowTransaction", entity_id=tx.id, actor_id=_actor(request, role), after={"engineer_profile_id": engineer.id, "change_type": change_type, "effective_from": str(effective_from)})
    db.commit(); db.refresh(tx)
    return {"transaction": _public_transaction(tx)}


@router.post("/transactions/{transaction_id}/transitions")
def transition_transaction(transaction_id: str, payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "EDIT_REGULATORY_CASE")
    tx = db.get(Source18WorkflowTransaction, transaction_id)
    if not tx:
        raise HTTPException(404, {"code": "SOURCE18_TRANSACTION_NOT_FOUND"})
    if tx.transaction_type == "RESPONSIBLE_ENGINEER_CHANGE" and payload.get("next_state") in {"OWNER_AUTHORIZATION_PREPARED", "OWNER_INTERNAL_RELEASE_APPROVED"}:
        require_capability(role, "MANAGE_RESPONSIBLE_ENGINEER_CHANGE")
    return {"transaction": _public_transaction(transition(db, tx, str(payload.get("next_state") or ""), actor=_actor(request, role), correlation_id=_corr(request)))}


@router.post("/transactions/{transaction_id}/packets")
def create_packet(transaction_id: str, payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "PREPARE_PACKET")
    tx = db.get(Source18WorkflowTransaction, transaction_id)
    if not tx:
        raise HTTPException(404, {"code": "SOURCE18_TRANSACTION_NOT_FOUND"})
    validate_source_currentness(db, tx); enforce_staffing_gate(db, tx)
    if tx.requirement_version_id:
        requirement = db.get(RequirementPolicyVersion, tx.requirement_version_id)
        if not requirement or requirement.status != "CURRENT":
            raise HTTPException(409, {"code": "SOURCE18_REQUIREMENT_VERSION_NOT_CURRENT"})
    manifest = packet_manifest(tx, payload)
    latest = db.scalar(select(Source18PacketRevision).where(Source18PacketRevision.transaction_id == tx.id).order_by(Source18PacketRevision.revision_number.desc()))
    if latest and latest.status != "RETURNED":
        raise HTTPException(409, {"code": "PACKET_REVISION_ALREADY_EXISTS_OR_NOT_RETURNED"})
    revision_number = (latest.revision_number + 1) if latest else 1
    packet = Source18PacketRevision(transaction_id=tx.id, revision_number=revision_number, status="DRAFT", packet_hash=_hash({"manifest": manifest, "required_signers": payload.get("required_signers") or []}), manifest_json=manifest, required_signers_json=payload.get("required_signers") or [], signature_state="NOT_STARTED", stamp_state="NOT_STARTED", custody_state="DIGITAL_SCAN", internal_release_state="NOT_RELEASED", supersedes_id=latest.id if latest and latest.status == "RETURNED" else None, created_by=_actor(request, role))
    db.add(packet); db.flush(); tx.state = "PACKET_PREPARED" if tx.transaction_type == "RESPONSIBLE_ENGINEER_CHANGE" and tx.state == "PACKET_PREPARED" else tx.state; audit(db, correlation_id=_corr(request), event_type="SOURCE18_PACKET_REVISION_CREATED", entity_type="Source18PacketRevision", entity_id=packet.id, actor_id=_actor(request, role), after={"revision_number": revision_number, "packet_hash": packet.packet_hash}); db.commit(); db.refresh(packet)
    return {"packet": packet_row(packet)}


@router.post("/packets/{packet_id}/release")
def release_packet(packet_id: str, request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "OWNER_INTERNAL_PACKET_RELEASE")
    packet = db.get(Source18PacketRevision, packet_id)
    if not packet:
        raise HTTPException(404, {"code": "SOURCE18_PACKET_NOT_FOUND"})
    if packet.status != "DRAFT" or packet.signature_state != "COMPLETE" or packet.stamp_state != "COMPLETE" or packet.packet_hash != _hash({"manifest": packet.manifest_json, "required_signers": packet.required_signers_json}):
        raise HTTPException(409, {"code": "PACKET_SIGNATURE_AND_STAMP_REQUIRED"})
    packet.internal_release_state = "RELEASED"; packet.status = "RELEASED"; audit(db, correlation_id=_corr(request), event_type="SOURCE18_OWNER_INTERNAL_RELEASED", entity_type="Source18PacketRevision", entity_id=packet.id, actor_id=_actor(request, role), after={"packet_hash": packet.packet_hash}); db.commit(); db.refresh(packet)
    return {"packet": packet_row(packet)}


@router.post("/packets/{packet_id}/signatures")
def capture_signatures(packet_id: str, payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "CAPTURE_SIGNATURE_EVIDENCE")
    packet = db.get(Source18PacketRevision, packet_id)
    if not packet or packet.status != "DRAFT":
        raise HTTPException(409, {"code": "PACKET_NOT_EDITABLE"})
    required = packet.required_signers_json
    supplied = payload.get("signatures") or []
    required_refs = {str(item.get("signer_ref")) for item in required}
    supplied_refs = {str(item.get("signer_ref")) for item in supplied}
    if required_refs - supplied_refs:
        raise HTTPException(409, {"code": "REQUIRED_SIGNER_MISSING", "signers": sorted(required_refs - supplied_refs)})
    if any(not item.get("evidence_ref") for item in supplied if str(item.get("signer_ref")) in required_refs):
        raise HTTPException(422, {"code": "SIGNATURE_EVIDENCE_REQUIRED"})
    packet.signature_state = "COMPLETE"; packet.manifest_json = {**packet.manifest_json, "signature_evidence": [{"signer_ref": item.get("signer_ref"), "evidence_ref": item.get("evidence_ref")} for item in supplied]}; refresh_packet_hash(packet); audit(db, correlation_id=_corr(request), event_type="SOURCE18_SIGNATURES_CAPTURED", entity_type="Source18PacketRevision", entity_id=packet.id, actor_id=_actor(request, role), after={"signature_state": packet.signature_state}); db.commit(); db.refresh(packet)
    return {"packet": packet_row(packet)}


@router.post("/packets/{packet_id}/stamp")
def capture_stamp(packet_id: str, payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "CAPTURE_STAMP_EVIDENCE")
    packet = db.get(Source18PacketRevision, packet_id)
    if not packet or not payload.get("evidence_ref"):
        raise HTTPException(422, {"code": "STAMP_EVIDENCE_REQUIRED"})
    if packet.status != "DRAFT":
        raise HTTPException(409, {"code": "PACKET_NOT_EDITABLE"})
    packet.stamp_state = "COMPLETE"; packet.manifest_json = {**packet.manifest_json, "stamp_evidence_ref": str(payload["evidence_ref"])}; refresh_packet_hash(packet); audit(db, correlation_id=_corr(request), event_type="SOURCE18_STAMP_CAPTURED", entity_type="Source18PacketRevision", entity_id=packet.id, actor_id=_actor(request, role), after={"stamp_state": packet.stamp_state}); db.commit(); db.refresh(packet)
    return {"packet": packet_row(packet)}


@router.post("/packets/{packet_id}/custody")
def record_physical_original_custody(packet_id: str, payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "PREPARE_PACKET")
    packet = db.get(Source18PacketRevision, packet_id)
    custody_ref = str(payload.get("custody_ref") or "").strip()
    if not packet or packet.status != "DRAFT":
        raise HTTPException(409, {"code": "PACKET_NOT_EDITABLE"})
    if not custody_ref:
        raise HTTPException(422, {"code": "PHYSICAL_CUSTODY_REFERENCE_REQUIRED"})
    packet.custody_state = "PHYSICAL_ORIGINAL_CUSTODY"
    packet.manifest_json = {**packet.manifest_json, "physical_original_custody_ref": custody_ref}
    refresh_packet_hash(packet)
    audit(db, correlation_id=_corr(request), event_type="SOURCE18_PHYSICAL_ORIGINAL_CUSTODY_RECORDED", entity_type="Source18PacketRevision", entity_id=packet.id, actor_id=_actor(request, role), after={"custody_state": packet.custody_state})
    db.commit(); db.refresh(packet)
    return {"packet": packet_row(packet)}


@router.post("/packets/{packet_id}/submit")
def submit_packet(packet_id: str, payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "AUTHORIZE_EXTERNAL_SUBMISSION")
    packet = db.get(Source18PacketRevision, packet_id)
    if not packet:
        raise HTTPException(404, {"code": "SOURCE18_PACKET_NOT_FOUND"})
    if packet.status != "RELEASED" or packet.internal_release_state != "RELEASED" or packet.signature_state != "COMPLETE" or packet.stamp_state != "COMPLETE":
        raise HTTPException(409, {"code": "OWNER_INTERNAL_RELEASE_SIGNATURE_STAMP_REQUIRED"})
    tx = db.get(Source18WorkflowTransaction, packet.transaction_id)
    idempotency_key = str(payload.get("idempotency_key") or "").strip()
    if not idempotency_key:
        raise HTTPException(422, {"code": "IDEMPOTENCY_KEY_REQUIRED"})
    existing_cycle = db.scalar(select(Source18SubmissionCycle).where(Source18SubmissionCycle.transaction_id == tx.id, Source18SubmissionCycle.idempotency_key == idempotency_key))
    if existing_cycle:
        return {"packet": packet_row(packet), "submission_cycle": {key: value for key, value in existing_cycle.__dict__.items() if not key.startswith("_")}, "idempotent_replay": True}
    cycle_count = db.scalar(select(func.count(Source18SubmissionCycle.id)).where(Source18SubmissionCycle.transaction_id == tx.id)) or 0
    packet.status = "SUBMITTED"; packet.submitted_at = _now(); cycle = Source18SubmissionCycle(transaction_id=tx.id, packet_revision_id=packet.id, cycle_number=int(cycle_count) + 1, idempotency_key=idempotency_key, status="SUBMITTED", external_reference=payload.get("external_reference"), external_outcome_json={"source": "HUMAN_EXTERNAL_WORKFLOW", "portal_api": False}, recorded_by=_actor(request, role)); db.add(cycle); tx.state = "SUBMITTED"; audit(db, correlation_id=_corr(request), event_type="SOURCE18_EXTERNAL_SUBMISSION_RECORDED", entity_type="Source18SubmissionCycle", entity_id=cycle.id, actor_id=_actor(request, role), after={"packet_id": packet.id, "portal_api": False}); db.commit(); db.refresh(packet); db.refresh(cycle)
    return {"packet": packet_row(packet), "submission_cycle": {key: value for key, value in cycle.__dict__.items() if not key.startswith("_")}, "idempotent_replay": False}


@router.post("/submissions/{cycle_id}/comments")
def add_comment(cycle_id: str, payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "CAPTURE_EXTERNAL_OUTCOME")
    cycle = db.get(Source18SubmissionCycle, cycle_id)
    if not cycle or not str(payload.get("comment_text") or "").strip():
        raise HTTPException(422, {"code": "EXTERNAL_COMMENT_REQUIRED"})
    comment = Source18ExternalComment(submission_cycle_id=cycle.id, comment_text=str(payload["comment_text"]).strip(), status="OPEN", source_document_version_id=payload.get("source_document_version_id"), recorded_by=_actor(request, role)); db.add(comment); cycle.status = "RETURNED_WITH_COMMENTS"; tx = db.get(Source18WorkflowTransaction, cycle.transaction_id); tx.state = "RETURNED"; audit(db, correlation_id=_corr(request), event_type="SOURCE18_EXTERNAL_COMMENT_RECORDED", entity_type="Source18ExternalComment", entity_id=comment.id, actor_id=_actor(request, role), after={"cycle_id": cycle.id, "status": cycle.status}); db.commit(); db.refresh(comment)
    return {"comment_id": comment.id, "status": comment.status, "cycle_status": cycle.status}


@router.post("/submissions/{cycle_id}/outcome")
def record_external_outcome(cycle_id: str, payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "CAPTURE_EXTERNAL_OUTCOME")
    cycle = db.get(Source18SubmissionCycle, cycle_id)
    if not cycle:
        raise HTTPException(404, {"code": "SUBMISSION_CYCLE_NOT_FOUND"})
    if payload.get("authority_only_values"):
        raise HTTPException(422, {"code": "AUTHORITY_ONLY_FIELD_WRITE_FORBIDDEN"})
    outcome = str(payload.get("outcome") or "").upper()
    if outcome not in {"APPROVED", "REJECTED", "RETURNED"}:
        raise HTTPException(422, {"code": "EXTERNAL_OUTCOME_REQUIRED"})
    tx = db.get(Source18WorkflowTransaction, cycle.transaction_id)
    cycle.status = outcome
    cycle.external_outcome_json = {"source": "HUMAN_EXTERNAL_WORKFLOW", "portal_api": False, "outcome": outcome, "reference": payload.get("external_reference")}
    if outcome in {"APPROVED", "REJECTED"}:
        tx.state = outcome
    audit(db, correlation_id=_corr(request), event_type="SOURCE18_EXTERNAL_OUTCOME_RECORDED", entity_type="Source18SubmissionCycle", entity_id=cycle.id, actor_id=_actor(request, role), after={"outcome": outcome, "portal_api": False})
    db.commit(); db.refresh(cycle)
    return {"cycle_id": cycle.id, "status": cycle.status, "portal_api": False}


@router.post("/submissions/{cycle_id}/resubmit")
def resubmit(cycle_id: str, payload: dict[str, Any], request: Request, role: Role = Depends(current_user_role), db: Session = Depends(get_db)):
    require_capability(role, "PREPARE_PACKET")
    cycle = db.get(Source18SubmissionCycle, cycle_id)
    if not cycle or cycle.status != "RETURNED_WITH_COMMENTS":
        raise HTTPException(409, {"code": "SUBMISSION_NOT_RETURNED"})
    packet = db.get(Source18PacketRevision, cycle.packet_revision_id); tx = db.get(Source18WorkflowTransaction, cycle.transaction_id)
    packet.status = "RETURNED"; tx.state = "REVISION_IN_PREPARATION" if tx.transaction_type == "ENGINEER_UPDATE" else tx.state; db.commit()
    return {"transaction_id": tx.id, "previous_cycle_id": cycle.id, "new_revision_required": True, "history_preserved": True}
