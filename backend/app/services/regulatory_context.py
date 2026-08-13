"""Case party and representation snapshots used by Preparation and Permit UX."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    AuthorityCase, AuthorityCaseSubject, AuthorizationGrant, CasePartySnapshot,
    ContactPoint, Party, PartyRoleAssignment, PreparationRevision, Project,
)


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _party(db: Session, party_id: str | None) -> dict[str, Any] | None:
    party = db.get(Party, party_id) if party_id else None
    if not party:
        return None
    return {"id": party.id, "party_type": str(getattr(party.party_type, "value", party.party_type)), "name_en": party.name_en, "name_ar": party.name_ar, "identifier_type": party.identifier_type, "identifier_present": bool(party.identifier_value), "status": str(getattr(party.status, "value", party.status))}


def case_party_context(db: Session, case: AuthorityCase) -> dict[str, Any]:
    assignments = db.scalars(select(PartyRoleAssignment).where(PartyRoleAssignment.authority_case_id == case.id, PartyRoleAssignment.status == "ACTIVE").order_by(PartyRoleAssignment.role_code, PartyRoleAssignment.assigned_at)).all()
    grants = db.scalars(select(AuthorizationGrant).where(AuthorizationGrant.authority_case_id == case.id).order_by(AuthorizationGrant.created_at)).all()
    contacts = db.scalars(select(ContactPoint).where(ContactPoint.authority_case_id == case.id, ContactPoint.status != "RETIRED").order_by(ContactPoint.purpose, ContactPoint.created_at)).all()
    snapshots = db.scalars(select(CasePartySnapshot).where(CasePartySnapshot.authority_case_id == case.id).order_by(CasePartySnapshot.snapshot_number.desc())).all()
    return {
        "assignments": [{**{key: value for key, value in item.__dict__.items() if not key.startswith("_")}, "party": _party(db, item.party_id)} for item in assignments],
        "authorizations": [{**{key: value for key, value in item.__dict__.items() if not key.startswith("_")}, "grantor": _party(db, item.grantor_party_id), "grantee": _party(db, item.grantee_party_id), "evidence_is_pinned": bool(item.evidence_document_version_id)} for item in grants],
        "contacts": [{key: value for key, value in item.__dict__.items() if not key.startswith("_") and key != "value"} | {"value_present": bool(item.value)} for item in contacts],
        "snapshots": [{key: value for key, value in item.__dict__.items() if not key.startswith("_") and key != "snapshot_json"} for item in snapshots],
        "role_semantics": {"commercial_client_is_not_owner_or_applicant_by_default": True, "general_mobile_is_not_regulatory_contact": True},
    }


def build_case_party_snapshot(db: Session, case: AuthorityCase, *, project: Project, preparation_revision: PreparationRevision | None, actor: str) -> CasePartySnapshot:
    assignments = db.scalars(select(PartyRoleAssignment).where(PartyRoleAssignment.authority_case_id == case.id, PartyRoleAssignment.status == "ACTIVE").order_by(PartyRoleAssignment.role_code, PartyRoleAssignment.assigned_at)).all()
    grants = db.scalars(select(AuthorizationGrant).where(AuthorizationGrant.authority_case_id == case.id, AuthorizationGrant.status != "REVOKED").order_by(AuthorizationGrant.created_at)).all()
    contacts = db.scalars(select(ContactPoint).where(ContactPoint.authority_case_id == case.id, ContactPoint.status != "RETIRED").order_by(ContactPoint.purpose, ContactPoint.created_at)).all()
    subject = db.scalar(select(AuthorityCaseSubject).where(AuthorityCaseSubject.authority_case_id == case.id))
    payload = {
        "project_id": project.id,
        "authority_case_id": case.id,
        "subject": {"type": subject.subject_type, "id": subject.subject_id, "snapshot": subject.subject_snapshot_json} if subject else {"type": case.subject_type or "Project", "id": case.subject_id or project.id},
        "party_roles": [{"role_code": item.role_code, "party": _party(db, item.party_id), "status": item.status, "valid_from": item.valid_from.isoformat() if item.valid_from else None, "valid_until": item.valid_until.isoformat() if item.valid_until else None, "source_document_version_id": item.source_document_version_id} for item in assignments],
        "authorizations": [{"id": item.id, "grantor_party": _party(db, item.grantor_party_id), "grantee_party": _party(db, item.grantee_party_id), "authorization_type": item.authorization_type, "scope": item.scope, "valid_from": item.valid_from.isoformat() if item.valid_from else None, "valid_until": item.valid_until.isoformat() if item.valid_until else None, "status": item.status, "evidence_document_version_id": item.evidence_document_version_id} for item in grants],
        "regulatory_contacts": [{"id": item.id, "purpose": item.purpose, "channel": item.channel, "value_present": bool(item.value), "party_id": item.party_id, "verified": item.verified, "status": item.status} for item in contacts],
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    number = (db.scalar(select(CasePartySnapshot.snapshot_number).where(CasePartySnapshot.authority_case_id == case.id).order_by(CasePartySnapshot.snapshot_number.desc())) or 0) + 1
    item = CasePartySnapshot(project_id=project.id, authority_case_id=case.id, preparation_revision_id=preparation_revision.id if preparation_revision else None, snapshot_number=number, snapshot_json=payload, snapshot_hash=_hash(payload), captured_by=actor)
    db.add(item)
    db.flush()
    if preparation_revision:
        preparation_revision.case_party_snapshot_id = item.id
    return item


def mark_party_context_changed(db: Session, case_id: str, *, reason: str) -> list[str]:
    revisions = db.scalars(select(PreparationRevision).where(PreparationRevision.authority_case_id == case_id, PreparationRevision.authority_state.not_in({"LOCKED", "SUBMITTED", "HISTORICAL"}))).all()
    changed: list[str] = []
    for revision in revisions:
        revision.status = "NEEDS_REVALIDATION"
        revision.authority_state = "NEEDS_REVALIDATION"
        revision.authority_snapshot_json = {**(revision.authority_snapshot_json or {}), "party_context_revalidation": {"required": True, "reason": reason}}
        changed.append(revision.id)
    return changed
