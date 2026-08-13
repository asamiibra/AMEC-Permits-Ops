"""Project/case-scoped party, representation, contact, and subject APIs."""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..models import AuthorityCase, AuthorityCaseSubject, AuthorizationGrant, ContactPoint, Document, DocumentVersion, LineageEdge, Party, PartyRoleAssignment, Project, Property, RegulatoryJourney, Role
from ..services.regulatory_context import case_party_context, mark_party_context_changed


router = APIRouter(prefix="/api/regulatory-context", tags=["regulatory-context"])
OWNER_ROLES = {Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN}
CASE_WRITE_ROLES = OWNER_ROLES | {Role.RESPONSIBLE_ENGINEER, Role.PERMIT_PREPARER, Role.REQUIREMENT_STEWARD}


def _actor(request: Request) -> str:
    return request.headers.get("X-Dev-Actor") or "role-actor"


def _corr(request: Request) -> str:
    return getattr(request.state, "correlation_id", str(uuid4()))


def _json(value: Any) -> Any:
    if isinstance(value, (date,)):
        return value.isoformat()
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _row(item: Any, *, omit: set[str] | None = None) -> dict[str, Any]:
    omit = omit or set()
    return {key: _json(value) for key, value in item.__dict__.items() if not key.startswith("_") and key not in omit}


def _case_scope(db: Session, case_id: str) -> tuple[AuthorityCase, Project]:
    row = db.execute(select(AuthorityCase, Project).join(RegulatoryJourney, RegulatoryJourney.id == AuthorityCase.regulatory_journey_id).join(Project, Project.id == RegulatoryJourney.project_id).where(AuthorityCase.id == case_id)).first()
    if not row:
        raise HTTPException(404, {"code": "AUTHORITY_CASE_NOT_FOUND"})
    return row


def _write(role: Role) -> None:
    if role not in CASE_WRITE_ROLES:
        raise HTTPException(403, {"code": "CAPABILITY_DENIED", "capability": "CASE_PARTY_CONTEXT_WRITE"})


def _party(db: Session, party_id: str, project_id: str | None = None) -> Party:
    item = db.get(Party, party_id)
    if not item:
        raise HTTPException(422, {"code": "PARTY_NOT_FOUND", "party_id": party_id})
    return item


def _document_version_in_project(db: Session, project: Project, version_id: str | None, error_code: str) -> None:
    if not version_id:
        return
    version = db.get(DocumentVersion, version_id)
    document = db.get(Document, version.document_id) if version else None
    if not version or not document or document.project_id != project.id:
        raise HTTPException(409, {"code": error_code})


def _lineage(db: Session, project: Project, *, upstream_type: str, upstream_id: str, downstream_type: str, downstream_id: str, kind: str, request: Request) -> None:
    db.add(LineageEdge(project_id=project.id, upstream_type=upstream_type, upstream_id=upstream_id, downstream_type=downstream_type, downstream_id=downstream_id, dependency_kind=kind, correlation_id=_corr(request)))


def _date(value: Any) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError as exc:
        raise HTTPException(422, {"code": "DATE_INVALID", "value": value}) from exc


@router.get("/cases/{case_id}")
def get_case_context(case_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    if role not in CASE_WRITE_ROLES and role not in {Role.PROCESS_CHAMPION}:
        raise HTTPException(403, {"code": "CAPABILITY_DENIED", "capability": "CASE_READ"})
    case, project = _case_scope(db, case_id)
    subject = db.scalar(select(AuthorityCaseSubject).where(AuthorityCaseSubject.authority_case_id == case.id))
    return {"case": _row(case), "project": _row(project, omit={"office"}), "subject": _row(subject) if subject else None, "parties_representation": case_party_context(db, case)}


@router.post("/cases/{case_id}/subjects")
def set_case_subject(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _write(role)
    case, project = _case_scope(db, case_id)
    subject_type = str(payload.get("subject_type") or "Project").strip()
    subject_id = str(payload.get("subject_id") or project.id)
    if subject_type == "Project":
        if subject_id != project.id:
            raise HTTPException(409, {"code": "CASE_SUBJECT_PROJECT_MISMATCH"})
        snapshot = {"project_id": project.id, "project_number": project.project_number, "project_name": project.project_name}
    elif subject_type == "Property":
        property_record = db.get(Property, subject_id)
        if not property_record or property_record.project_id != project.id:
            raise HTTPException(404, {"code": "CASE_SUBJECT_PROPERTY_NOT_FOUND"})
        snapshot = _row(property_record)
    else:
        raise HTTPException(422, {"code": "CASE_SUBJECT_TYPE_NOT_CANONICAL", "subject_type": subject_type, "supported": ["Project", "Property"]})
    existing = db.scalar(select(AuthorityCaseSubject).where(AuthorityCaseSubject.authority_case_id == case.id))
    if existing:
        if existing.subject_type == subject_type and existing.subject_id == subject_id:
            return _row(existing)
        raise HTTPException(409, {"code": "CASE_SUBJECT_IMMUTABLE_CREATE_NEW_CASE"})
    item = AuthorityCaseSubject(authority_case_id=case.id, subject_type=subject_type, subject_id=subject_id, subject_snapshot_json=snapshot, created_by=_actor(request))
    db.add(item); db.flush(); case.subject_type = subject_type; case.subject_id = subject_id
    _lineage(db, project, upstream_type="Project", upstream_id=project.id, downstream_type="AuthorityCaseSubject", downstream_id=item.id, kind="CASE_SUBJECT_SNAPSHOT", request=request)
    audit(db, correlation_id=_corr(request), event_type="AUTHORITY_CASE_SUBJECT_SET", entity_type="AuthorityCaseSubject", entity_id=item.id, actor_id=_actor(request), after={"subject_type": subject_type, "subject_id": subject_id}); db.commit()
    return _row(item)


@router.post("/cases/{case_id}/party-roles")
def assign_party_role(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _write(role)
    case, project = _case_scope(db, case_id)
    party = _party(db, str(payload.get("party_id") or ""))
    role_code = str(payload.get("role_code") or "").strip().upper()
    if not role_code:
        raise HTTPException(422, {"code": "PARTY_ROLE_REQUIRED"})
    active = db.scalars(select(PartyRoleAssignment).where(PartyRoleAssignment.authority_case_id == case.id, PartyRoleAssignment.role_code == role_code, PartyRoleAssignment.status == "ACTIVE")).all()
    same = next((item for item in active if item.party_id == party.id), None)
    if same:
        return _row(same)
    for item in active:
        item.status = "SUPERSEDED"
    item = PartyRoleAssignment(project_id=project.id, authority_case_id=case.id, party_id=party.id, role_code=role_code, valid_from=_date(payload.get("valid_from")), valid_until=_date(payload.get("valid_until")), source_document_version_id=payload.get("source_document_version_id"), source_kind=str(payload.get("source_kind") or "HUMAN_CONFIRMED"), notes=payload.get("notes"), assigned_by=_actor(request))
    _document_version_in_project(db, project, item.source_document_version_id, "PARTY_ROLE_EVIDENCE_PROJECT_MISMATCH")
    db.add(item); db.flush(); _lineage(db, project, upstream_type="Party", upstream_id=party.id, downstream_type="PartyRoleAssignment", downstream_id=item.id, kind="CASE_SCOPED_PARTY_ROLE", request=request); changed = mark_party_context_changed(db, case.id, reason=f"PARTY_ROLE_{role_code}_CHANGED"); audit(db, correlation_id=_corr(request), event_type="AUTHORITY_CASE_PARTY_ROLE_ASSIGNED", entity_type="PartyRoleAssignment", entity_id=item.id, actor_id=_actor(request), after={"case_id": case.id, "project_id": project.id, "role_code": role_code, "party_id": party.id, "revalidated_preparations": changed}); db.commit()
    return {"assignment": _row(item), "revalidated_preparations": changed, "commercial_client_is_not_owner_or_applicant_by_default": True}


@router.post("/cases/{case_id}/authorizations")
def create_authorization_grant(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _write(role)
    case, project = _case_scope(db, case_id)
    grantor = _party(db, str(payload.get("grantor_party_id") or "")); grantee = _party(db, str(payload.get("grantee_party_id") or ""))
    authorization_type = str(payload.get("authorization_type") or "").strip().upper(); scope = str(payload.get("scope") or "").strip()
    if not authorization_type or not scope:
        raise HTTPException(422, {"code": "AUTHORIZATION_SCOPE_REQUIRED"})
    evidence_id = payload.get("evidence_document_version_id")
    _document_version_in_project(db, project, evidence_id, "AUTHORIZATION_EVIDENCE_PROJECT_MISMATCH")
    item = AuthorizationGrant(project_id=project.id, authority_case_id=case.id, grantor_party_id=grantor.id, grantee_party_id=grantee.id, authorization_type=authorization_type, scope=scope, valid_from=_date(payload.get("valid_from")), valid_until=_date(payload.get("valid_until")), status=str(payload.get("status") or "PENDING").upper(), evidence_document_version_id=evidence_id, notes=payload.get("notes"), created_by=_actor(request))
    db.add(item); db.flush(); _lineage(db, project, upstream_type="Party", upstream_id=grantor.id, downstream_type="AuthorizationGrant", downstream_id=item.id, kind="CASE_SCOPED_AUTHORIZATION", request=request); changed = mark_party_context_changed(db, case.id, reason="AUTHORIZATION_GRANT_CHANGED"); audit(db, correlation_id=_corr(request), event_type="AUTHORITY_CASE_AUTHORIZATION_GRANT_CREATED", entity_type="AuthorizationGrant", entity_id=item.id, actor_id=_actor(request), after={"case_id": case.id, "grantor_party_id": grantor.id, "grantee_party_id": grantee.id, "evidence_document_version_id": evidence_id, "revalidated_preparations": changed}); db.commit()
    return {"authorization": _row(item), "revalidated_preparations": changed, "filename_only_authorization": False}


@router.post("/cases/{case_id}/contacts")
def add_contact_point(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _write(role)
    case, project = _case_scope(db, case_id)
    party_id = payload.get("party_id")
    if party_id:
        _party(db, str(party_id))
    purpose = str(payload.get("purpose") or "").strip().upper(); channel = str(payload.get("channel") or "").strip().upper(); value = str(payload.get("value") or "").strip()
    if not purpose or not channel or not value:
        raise HTTPException(422, {"code": "CONTACT_PURPOSE_CHANNEL_VALUE_REQUIRED"})
    source_document_version_id = payload.get("source_document_version_id")
    _document_version_in_project(db, project, source_document_version_id, "CONTACT_POINT_EVIDENCE_PROJECT_MISMATCH")
    item = ContactPoint(project_id=project.id, authority_case_id=case.id, party_id=str(party_id) if party_id else None, purpose=purpose, channel=channel, value=value, verified=bool(payload.get("verified", False)), status="VERIFIED" if bool(payload.get("verified", False)) else "PENDING_VERIFICATION", effective_from=_date(payload.get("effective_from")), effective_until=_date(payload.get("effective_until")), maintained_by=_actor(request), source_document_version_id=source_document_version_id, notes=payload.get("notes"))
    db.add(item); db.flush(); _lineage(db, project, upstream_type="Party" if party_id else "AuthorityCase", upstream_id=str(party_id or case.id), downstream_type="ContactPoint", downstream_id=item.id, kind="PURPOSE_SPECIFIC_CONTACT", request=request); changed = mark_party_context_changed(db, case.id, reason=f"CONTACT_{purpose}_CHANGED"); audit(db, correlation_id=_corr(request), event_type="AUTHORITY_CASE_CONTACT_POINT_CREATED", entity_type="ContactPoint", entity_id=item.id, actor_id=_actor(request), after={"case_id": case.id, "purpose": purpose, "channel": channel, "verified": item.verified, "revalidated_preparations": changed, "general_mobile_is_regulatory_contact": False}); db.commit()
    return {"contact": _row(item, omit={"value"}), "value_present": True, "revalidated_preparations": changed}
