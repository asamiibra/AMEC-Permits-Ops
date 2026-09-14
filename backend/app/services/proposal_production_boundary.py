"""Fail-closed helpers for the Proposal production/synthetic mode boundary."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, true
from sqlalchemy.orm import Session

from ..config.settings import get_settings
from ..models import ClientAccount, DocumentVersion, Party, ProposalSourceLink


def synthetic_test_mode() -> bool:
    """Synthetic fixtures are valid only in the explicit TEST environment."""
    return get_settings().app_env.upper() == "TEST"


def production_mode() -> bool:
    settings = get_settings()
    return settings.app_env.upper() in {"AZURE-PREPROD", "PROD", "PRODUCTION"} or not settings.synthetic_only


def reject_synthetic_value(value: Any, *, code: str) -> None:
    if value is None:
        return
    encoded = json.dumps(value, sort_keys=True, default=str).upper()
    if any(token in encoded for token in ("AMEC-SYN", "SYNTHETIC://", "SYN-CAPABILITY", "SYN-POLICY", "X-DEV-ROLE")):
        raise HTTPException(409, {"code": code, "reason": "SYNTHETIC_INPUT_FORBIDDEN_IN_PRODUCTION"})


def require_canonical_active_client(db: Session, client_account_id: str | None) -> ClientAccount:
    if not client_account_id:
        raise HTTPException(409, {"code": "CANONICAL_CLIENT_ACCOUNT_REQUIRED"})
    client = db.scalar(select(ClientAccount).where(ClientAccount.id == client_account_id, ClientAccount.status == "ACTIVE"))
    if not client:
        raise HTTPException(409, {"code": "CANONICAL_CLIENT_ACCOUNT_REQUIRED", "client_account_id": client_account_id})
    reject_synthetic_value(client.client_reference, code="CANONICAL_CLIENT_ACCOUNT_REQUIRED")
    reject_synthetic_value(client.data_classification, code="CANONICAL_CLIENT_ACCOUNT_REQUIRED")
    return client


def require_exact_document_version(db: Session, version_id: str | None, *, code: str) -> DocumentVersion:
    if not version_id:
        raise HTTPException(409, {"code": code})
    version = db.get(DocumentVersion, version_id)
    if not version or not version.source_path_or_reference.startswith("storage://"):
        raise HTTPException(409, {"code": code, "reason": "DURABLE_DOCUMENT_VERSION_REQUIRED"})
    if version.synthetic_content is not None or version.superseded_by or not version.sha256 or version.file_size <= 0:
        raise HTTPException(409, {"code": code, "reason": "DOCUMENT_VERSION_INTEGRITY_METADATA_REQUIRED"})
    reject_synthetic_value({"source_system": version.source_system, "source_filename": version.source_filename, "metadata": version.metadata_json}, code=code)
    return version


def require_authorized_office(db: Session, principal: Any, *, project_id: str | None = None):
    """Resolve only the office carried by the authenticated principal.

    A production Proposal must never fall back to the first office in the
    database. Project context is checked against the same office boundary.
    """
    if production_mode() and not getattr(principal, "office_id", None):
        raise HTTPException(409, "OFFICE_CONTEXT_REQUIRED")
    office_id = getattr(principal, "office_id", None)
    if not office_id:
        from ..models import ConsultancyOffice
        office = db.scalar(select(ConsultancyOffice).where(ConsultancyOffice.status == "ACTIVE").order_by(ConsultancyOffice.office_code))
    else:
        from ..models import ConsultancyOffice
        office = db.scalar(select(ConsultancyOffice).where(ConsultancyOffice.id == office_id, ConsultancyOffice.status == "ACTIVE"))
    if not office:
        raise HTTPException(409, "OFFICE_CONTEXT_REQUIRED")
    if project_id:
        from ..models import Project
        project = db.get(Project, project_id)
        if not project or project.office_id != office.id:
            raise HTTPException(409, {"code": "OFFICE_CONTEXT_MISMATCH", "office_id": office.id, "project_id": project_id})
    return office


def require_proposal_scoped_evidence(
    db: Session,
    *,
    proposal_id: str,
    version_id: str | None,
    source_roles: tuple[str, ...],
    code: str,
    client_account_id: str | None = None,
) -> DocumentVersion:
    """Require an active ProposalSourceLink for consequential evidence.

    A durable DocumentVersion alone is not sufficient: the active link binds
    the exact Proposal, role, and (when recorded by the source bridge) Client.
    """
    version = require_exact_document_version(db, version_id, code=code)
    link = db.scalar(select(ProposalSourceLink).where(
        ProposalSourceLink.proposal_id == proposal_id,
        ProposalSourceLink.document_version_id == version.id,
        ProposalSourceLink.source_role.in_(tuple(source_roles)),
        ProposalSourceLink.active == true(),
    ))
    if not link:
        raise HTTPException(409, {"code": code, "reason": "PROPOSAL_EVIDENCE_SCOPE_REQUIRED", "proposal_id": proposal_id, "document_version_id": version.id, "source_roles": list(source_roles)})
    if client_account_id:
        metadata = version.metadata_json or {}
        bound_client = metadata.get("client_account_id") or (metadata.get("provenance") or {}).get("client_account_id")
        if bound_client is not None and str(bound_client) != str(client_account_id):
            raise HTTPException(409, {"code": code, "reason": "PROPOSAL_EVIDENCE_CLIENT_MISMATCH", "client_account_id": client_account_id})
    return version


def require_current_professional_party(db: Session, party_id: str | None, *, office_id: str | None, service_code: str, discipline: str | None = None) -> Party:
    """Resolve a current human professional party through canonical records."""
    if not party_id:
        raise HTTPException(409, "ELIGIBILITY_PROFESSIONAL_PARTY_REQUIRED")
    party = db.scalar(select(Party).where(Party.id == party_id, Party.status == "CURRENT"))
    if not party:
        raise HTTPException(409, "ELIGIBILITY_PROFESSIONAL_PARTY_NOT_CURRENT")
    # PartyRoleAssignment/Source18 roster rows are the existing authority seam.
    from ..models import PartyRoleAssignment, Source18EngineerProfile, Source18RosterMembership
    assignment = db.scalar(select(PartyRoleAssignment).where(PartyRoleAssignment.party_id == party.id, PartyRoleAssignment.status == "ACTIVE"))
    profile = db.scalar(select(Source18EngineerProfile).where(Source18EngineerProfile.display_name == (party.name_en or party.name_ar), Source18EngineerProfile.status == "ACTIVE"))
    roster = db.scalar(select(Source18RosterMembership).where(Source18RosterMembership.engineer_profile_id == profile.id, Source18RosterMembership.status == "ACTIVE")) if profile else None
    if office_id and profile and profile.office_id != office_id:
        raise HTTPException(409, "ELIGIBILITY_PROFESSIONAL_PARTY_OFFICE_MISMATCH")
    if office_id and roster and roster.office_id != office_id:
        raise HTTPException(409, "ELIGIBILITY_PROFESSIONAL_PARTY_OFFICE_MISMATCH")
    if office_id and assignment and assignment.project_id:
        from ..models import Project
        project = db.get(Project, assignment.project_id)
        if project and project.office_id != office_id:
            raise HTTPException(409, "ELIGIBILITY_PROFESSIONAL_PARTY_OFFICE_MISMATCH")
    if not assignment and not roster:
        raise HTTPException(409, {"code": "ELIGIBILITY_PROFESSIONAL_AUTHORITY_REQUIRED", "service_offering_code": service_code, "discipline": discipline})
    if discipline and profile and profile.discipline.upper() != discipline.upper():
        raise HTTPException(409, "ELIGIBILITY_PROFESSIONAL_DISCIPLINE_MISMATCH")
    return party


def content_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
