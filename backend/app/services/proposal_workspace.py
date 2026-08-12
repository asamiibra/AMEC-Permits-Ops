"""Deterministic BD Proposal workspace services."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    DefinitionEntry,
    DefinitionRevision,
    DocumentVersion,
    MasterContentItem,
    MasterContentModuleBinding,
    Opportunity,
    ProposalAcceptedRevision,
    ProposalOutputArtifact,
    ProposalOwnerSetting,
    ProposalSourceEvidence,
)
from .master_content import definition_lookup

SOURCE_TYPES = ("TENDER_DOCUMENT", "TENDER_EMAIL", "TENDER_PHOTO", "CLIENT_DATA")
SOURCE_TO_SEMANTIC = {
    "TENDER_DOCUMENT": "TENDER_DOCUMENT_SOURCE",
    "TENDER_EMAIL": "TENDER_EMAIL_SOURCE",
    "TENDER_PHOTO": "TENDER_IMAGE_SOURCE",
    "CLIENT_DATA": "CLIENT_SOURCE",
}

DEFAULT_OWNER_SETTINGS = {
    "bd_profile": {"default_stage": "IN_REVIEW", "require_human_accept": True, "ai_mode": "DISABLED"},
    "authority_semantics": {"status": "OWNER_DECISION_REQUIRED", "value": "No automatic authority approval is inferred."},
    "contract_trigger": {"status": "OWNER_DECISION_REQUIRED", "value": "Accepted Proposal may be handed to Contract; no automatic legal contract is created."},
    "close_semantics": {"status": "OWNER_DECISION_REQUIRED", "value": "Proposal close status requires Owner policy confirmation."},
}


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def master_content_purpose(db: Session, usage_type: str) -> dict[str, Any]:
    usage_type = usage_type.upper()
    rows = db.scalars(
        select(MasterContentItem)
        .join(MasterContentModuleBinding, MasterContentModuleBinding.master_content_id == MasterContentItem.id)
        .where(
            MasterContentModuleBinding.module == "BD",
            MasterContentModuleBinding.usage_type == usage_type,
            MasterContentModuleBinding.active.is_(True),
            MasterContentItem.status == "ACTIVE",
        )
        .order_by(MasterContentItem.updated_at.desc(), MasterContentItem.ref)
    ).all()
    resolved = []
    for item in rows:
        version = db.get(DocumentVersion, item.current_document_version_id) if item.current_document_version_id else None
        if version:
            resolved.append({
                "id": item.id,
                "ref": item.ref,
                "title": item.title,
                "content_type": item.content_type,
                "version_id": version.id,
                "version": version.version_number,
                "hash": version.sha256,
                "source_filename": version.source_filename,
                "usage_type": usage_type,
                "canonical": True,
            })
    return {
        "purpose": usage_type,
        "status": "RESOLVED" if len(resolved) == 1 else "AMBIGUOUS" if len(resolved) > 1 else "UNRESOLVED",
        "canonical_count": len(resolved),
        "item": resolved[0] if len(resolved) == 1 else None,
        "candidates": resolved,
        "truth": "DASHBOARD_MASTER_CONTENT",
    }


def definitions_for_proposal(db: Session, terms: list[str]) -> list[dict[str, Any]]:
    result = []
    for term in terms:
        item = definition_lookup(db, term)
        if item:
            result.append(item)
    return result


def _sources(db: Session, proposal_id: str) -> list[ProposalSourceEvidence]:
    return db.scalars(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal_id).order_by(ProposalSourceEvidence.created_at)).all()


def _source_projection(item: ProposalSourceEvidence) -> dict[str, Any]:
    return {
        "id": item.id,
        "source_type": item.source_type,
        "source_filename": item.source_filename,
        "source_reference": item.source_reference,
        "content_hash": item.content_hash,
        "content_type": item.content_type,
        "source_revision": item.source_revision,
        "provenance": item.provenance or {},
        "conflict_key": item.conflict_key,
        "status": item.status,
        "verification_state": item.verification_state,
        "created_by": item.created_by,
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


def validate_proposal(db: Session, proposal: Opportunity) -> dict[str, Any]:
    fields = proposal.proposal_fields_json or {}
    sources = _sources(db, proposal.id)
    template = master_content_purpose(db, "PROPOSAL_TEMPLATE")
    checklist = master_content_purpose(db, "PROPOSAL_CHECKLIST")
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    required = {
        "CLIENT_REQUIRED": bool(proposal.client_account_id),
        "DESCRIPTION_REQUIRED": bool(proposal.title.strip()),
        "SCOPE_OF_WORK_REQUIRED": bool(str(fields.get("scope_of_work") or fields.get("sow") or "").strip()),
        "CLIENT_SCOPE_OF_WORK_REQUIRED": bool(str(fields.get("client_scope_of_work") or "").strip()),
        "PRICE_REQUIRED": bool(str(fields.get("price") or "").strip()),
        "DURATION_REQUIRED": bool(str(fields.get("duration") or fields.get("period") or "").strip()),
        "PROPOSAL_TEMPLATE_REQUIRED": template["status"] == "RESOLVED",
        "PROPOSAL_CHECKLIST_REQUIRED": checklist["status"] == "RESOLVED",
    }
    labels = {
        "CLIENT_REQUIRED": "Client",
        "DESCRIPTION_REQUIRED": "Proposal Description",
        "SCOPE_OF_WORK_REQUIRED": "Scope of Work",
        "CLIENT_SCOPE_OF_WORK_REQUIRED": "Client Scope of Work",
        "PRICE_REQUIRED": "Price",
        "DURATION_REQUIRED": "Duration",
        "PROPOSAL_TEMPLATE_REQUIRED": "Dashboard Proposal Template",
        "PROPOSAL_CHECKLIST_REQUIRED": "Dashboard Proposal Checklist",
    }
    for code, present in required.items():
        if not present:
            blockers.append({"code": code, "label": labels[code]})
    if not sources:
        blockers.append({"code": "SOURCE_EVIDENCE_REQUIRED", "label": "Source evidence"})
    for source_type in SOURCE_TYPES:
        if not any(item.source_type == source_type and item.status == "CURRENT" for item in sources):
            warnings.append({"code": f"{source_type}_MISSING", "label": source_type.replace("_", " ").title()})
    conflicts = [item for item in sources if item.status == "CONFLICT"]
    if conflicts:
        blockers.append({"code": "SOURCE_CONFLICTS_UNRESOLVED", "label": "Resolve conflicting source evidence"})
    if not (fields.get("inclusions") or fields.get("exclusions")):
        warnings.append({"code": "COMMERCIAL_BOUNDARIES_REVIEW", "label": "Confirm inclusions and exclusions"})
    definition_terms = fields.get("definition_terms") or []
    return {
        "ready": not blockers,
        "blockers": blockers,
        "warnings": warnings,
        "source_count": len([item for item in sources if item.status == "CURRENT"]),
        "conflict_count": len(conflicts),
        "template": template,
        "checklist": checklist,
        "definitions": definitions_for_proposal(db, definition_terms),
        "ai_assist": {"enabled": False, "response": None, "typed_error": "AI_ASSIST_DISABLED"},
        "authority": "OWNER_DECISION_REQUIRED",
    }


def proposal_projection(db: Session, proposal: Opportunity) -> dict[str, Any]:
    fields = proposal.proposal_fields_json or {}
    sources = _sources(db, proposal.id)
    revisions = db.scalars(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == proposal.id).order_by(ProposalAcceptedRevision.revision_number.desc())).all()
    current = revisions[0] if revisions else None
    validation = validate_proposal(db, proposal)
    return {
        "id": proposal.id,
        "proposal_reference": proposal.opportunity_reference,
        "project_reference": proposal.canonical_project_reference or proposal.provisional_reference,
        "project_id": proposal.project_id,
        "client_account_id": proposal.client_account_id,
        "client_name": fields.get("client_name"),
        "title": proposal.title,
        "stage": proposal.status,
        "stage_label": proposal.status.replace("_", " ").title(),
        "amount": fields.get("price"),
        "last_activity": proposal.updated_at.isoformat() if proposal.updated_at else None,
        "fields": fields,
        "provenance": fields.get("provenance", {}),
        "amec_input": fields.get("amec_input", {}),
        "sources": [_source_projection(item) for item in sources],
        "validation": validation,
        "current_revision": {
            "id": current.id,
            "revision_number": current.revision_number,
            "content_hash": current.content_hash,
            "accepted_by": current.accepted_by,
            "accepted_at": current.accepted_at.isoformat(),
            "template": {"ref": current.template_ref, "version_id": current.template_version_id, "version": current.template_version, "hash": current.template_hash},
            "checklist": {"ref": current.checklist_ref, "version_id": current.checklist_version_id, "version": current.checklist_version, "hash": current.checklist_hash},
        } if current else None,
        "revision_history": [{"id": item.id, "revision_number": item.revision_number, "content_hash": item.content_hash, "accepted_at": item.accepted_at.isoformat(), "accepted_by": item.accepted_by} for item in revisions],
        "ai_assist": validation["ai_assist"],
        "contract_eligible": bool(current and validation["ready"]),
        "synthetic_only": True,
    }


def snapshot_for_accept(db: Session, proposal: Opportunity, validation: dict[str, Any]) -> dict[str, Any]:
    fields = dict(proposal.proposal_fields_json or {})
    fields.pop("provenance", None)
    fields.pop("amec_input", None)
    source_ids = [item.id for item in _sources(db, proposal.id) if item.status == "CURRENT"]
    return {
        "proposal_id": proposal.id,
        "proposal_reference": proposal.opportunity_reference,
        "title": proposal.title,
        "project_reference": proposal.canonical_project_reference or proposal.provisional_reference,
        "client_account_id": proposal.client_account_id,
        "fields": fields,
        "amec_input": (proposal.proposal_fields_json or {}).get("amec_input", {}),
        "provenance": (proposal.proposal_fields_json or {}).get("provenance", {}),
        "source_ids": source_ids,
        "template": validation["template"]["item"],
        "checklist": validation["checklist"]["item"],
        "definitions": validation["definitions"],
        "accepted_at": _now().isoformat(),
    }


def output_bytes(revision: ProposalAcceptedRevision, artifact_type: str) -> bytes:
    if artifact_type == "PROPOSAL":
        body = revision.snapshot
        title = "AMEC Proposal"
    else:
        body = {"proposal_reference": revision.snapshot.get("proposal_reference"), "revision": revision.revision_number, "checklist": revision.snapshot.get("checklist"), "validation": revision.validation_snapshot, "source_ids": revision.snapshot.get("source_ids", [])}
        title = "AMEC Proposal Checklist"
    return (title + "\n" + json.dumps(body, indent=2, sort_keys=True, default=str) + "\n").encode()


def ensure_owner_settings(db: Session, actor: str = "owner-demo-seed") -> list[ProposalOwnerSetting]:
    rows = []
    for key, value in DEFAULT_OWNER_SETTINGS.items():
        row = db.scalar(select(ProposalOwnerSetting).where(ProposalOwnerSetting.setting_key == key))
        if not row:
            row = ProposalOwnerSetting(setting_key=key, value_json=value, status="SAFE_DEFAULT", updated_by=actor, notes="Safe default pending explicit Owner confirmation.")
            db.add(row)
        rows.append(row)
    db.flush()
    return rows
