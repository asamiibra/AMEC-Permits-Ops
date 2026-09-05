"""Deterministic BD Proposal workspace services."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, true, false
from sqlalchemy.orm import Session

from ..models import (
    AuditEvent,
    DefinitionEntry,
    DefinitionRevision,
    MasterContentModuleBinding,
    Opportunity,
    ProposalAcceptedRevision,
    ProposalOutputArtifact,
    ProposalOwnerSetting,
    ProposalSourceEvidence,
    ProposalNote,
    ProposalIntakeArtifact,
)
from .master_content import canonical_master_content_candidates, definition_lookup, resolve_master_content_purpose
from .master_content import definition_projection, governance_projection
from .bd_proposal_forms_v2 import forms_v2_projection, snapshot_forms_v2, v2_readiness
from .owner_decisions import runtime_decision_value

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
    return resolve_master_content_purpose(db, module="BD", usage_type=usage_type)


def definitions_for_proposal(db: Session, terms: list[str]) -> list[dict[str, Any]]:
    result = []
    for term in terms:
        item = definition_lookup(db, term)
        if item:
            result.append(item)
    return result


def definitions_for_bd(db: Session) -> list[dict[str, Any]]:
    """Return current semantic definitions bound to BD, never client values."""
    rows = db.scalars(
        select(DefinitionEntry)
        .join(MasterContentModuleBinding, MasterContentModuleBinding.definition_id == DefinitionEntry.id)
        .where(
            MasterContentModuleBinding.module == "BD",
            MasterContentModuleBinding.active == true(),
            DefinitionEntry.status == "ACTIVE",
        )
        .order_by(DefinitionEntry.term)
    ).all()
    return [definition_projection(db, row) for row in rows if row.current_revision_id and db.get(DefinitionRevision, row.current_revision_id)]


def engineering_references_for_proposal(db: Session, proposal: Opportunity) -> dict[str, Any]:
    """Resolve Engineering Works through the shared canonical eligibility seam."""
    if proposal.status != "PROPOSAL_PREPARATION":
        return {
            "status": "DEFERRED",
            "label": "Available during Engineering Preparation",
            "items": [],
            "truth": "DASHBOARD_MASTER_CONTENT",
        }
    items: list[dict[str, Any]] = []
    for candidate in canonical_master_content_candidates(db, module="ENGINEERING", usage_type="AVAILABLE", content_type="ENGINEERING_WORK"):
        items.append({
            "id": candidate["id"],
            "ref": candidate["ref"],
            "title": candidate["title"],
            "version_id": candidate["version_id"],
            "version": candidate["version"],
            "hash": candidate["hash"],
            "source_type": candidate.get("source_type"),
            "discipline": candidate.get("discipline"),
            "managed_in": "/dashboard",
        })
    return {
        "status": "RESOLVED" if items else "UNRESOLVED",
        "label": "Current eligible Engineering Works",
        "items": items,
        "truth": "DASHBOARD_MASTER_CONTENT",
    }


def proposal_configuration(db: Session, proposal: Opportunity) -> dict[str, Any]:
    """Business-facing Proposal consumption of Dashboard-governed content."""
    template = master_content_purpose(db, "PROPOSAL_TEMPLATE")
    checklist = master_content_purpose(db, "PROPOSAL_CHECKLIST")
    definitions = definitions_for_bd(db)
    accepted = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == proposal.id).order_by(ProposalAcceptedRevision.revision_number.desc()))

    def card(label: str, resolution: dict[str, Any]) -> dict[str, Any]:
        item = resolution.get("item")
        if item:
            return {
                "label": label,
                "status": "READY",
                "ref": item["ref"],
                "title": item["title"],
                "version": item["version"],
                "master_content_id": item["id"],
                "document_version_id": item["version_id"],
                "hash": item["hash"],
                "managed_in": "/dashboard",
                "purpose": item["purpose"],
            }
        status = "CONFIGURATION_CONFLICT" if resolution.get("status") == "AMBIGUOUS" else "OWNER_CONFIRMATION_REQUIRED"
        return {
            "label": label,
            "status": status,
            "message": "Configuration needs Owner attention" if status == "CONFIGURATION_CONFLICT" else "Owner confirmation required before final Proposal generation/acceptance",
            "managed_in": "/dashboard",
            "purpose": resolution.get("purpose"),
            "candidates": len(resolution.get("candidates", [])),
        }

    return {
        "proposal_template": card("Proposal Template", template),
        "proposal_checklist": card("Proposal Checklist", checklist),
        "definitions": {
            "status": "AVAILABLE" if definitions else "NONE_CONFIGURED",
            "count": len(definitions),
            "items": definitions,
            "managed_in": "/dashboard",
            "truth": "DASHBOARD_DEFINITION_SEMANTIC_ONLY",
        },
        "engineering_references": engineering_references_for_proposal(db, proposal),
        "accepted_revision": {
            "revision_number": accepted.revision_number,
            "proposal_template": {"ref": accepted.template_ref, "version_id": accepted.template_version_id, "version": accepted.template_version, "hash": accepted.template_hash},
            "proposal_checklist": {"ref": accepted.checklist_ref, "version_id": accepted.checklist_version_id, "version": accepted.checklist_version, "hash": accepted.checklist_hash},
            "rule": "Accepted output remains pinned to this exact Dashboard content even after later publication.",
        } if accepted else None,
        "stage1_requiredness": "Dashboard configuration does not block initial intake; template/checklist readiness is enforced at final validation/acceptance.",
        "transaction_boundary": "Proposal sources, client values, notes, and generated outputs remain Proposal transaction data.",
    }


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


def intake_readiness(db: Session, proposal: Opportunity) -> dict[str, Any]:
    """Stage 1 readiness; intentionally narrower than final Proposal Accept."""
    fields = proposal.proposal_fields_json or {}
    sources = _sources(db, proposal.id)
    current = [item for item in sources if item.status == "CURRENT"]
    blockers: list[dict[str, str]] = []
    if not proposal.client_account_id:
        blockers.append({"code": "CLIENT_REQUIRED", "label": "Client context required", "section": "client"})
    if not current:
        blockers.append({"code": "SOURCE_EVIDENCE_REQUIRED", "label": "No source evidence received", "section": "sources"})
    if not proposal.title.strip():
        blockers.append({"code": "DESCRIPTION_REQUIRED", "label": "Proposal description required", "section": "client_request"})
    if proposal.reference_state not in {"PROVISIONAL", "CANONICAL"}:
        blockers.append({"code": "REFERENCE_STATE_INVALID", "label": "Proposal reference state is invalid", "section": "header"})
    if any(item.verification_state != "READ_BACK_VERIFIED" for item in current):
        blockers.append({"code": "SOURCE_VERIFICATION_REQUIRED", "label": "Source verification incomplete", "section": "sources"})
    conflicts = [item for item in sources if item.status == "CONFLICT" and not any(row.supersedes_id == item.id for row in current)]
    if conflicts:
        blockers.append({"code": "IDENTITY_CONFLICT_UNRESOLVED", "label": "Identity or source conflict unresolved", "section": "conflicts"})
    warnings = []
    if not fields.get("client_scope_of_work"):
        warnings.append({"code": "CLIENT_SCOPE_REVIEW", "label": "Client Requested Scope needs review", "section": "client_request"})
    if not (fields.get("location") or fields.get("site_context")):
        warnings.append({"code": "SITE_REVIEW", "label": "Site / Property context needs review", "section": "site"})
    return {"ready": not blockers, "blockers": blockers, "warnings": warnings, "source_count": len(current), "current_owner": "Business Development" if not blockers else "Business Development", "next_actor": "Engineering" if not blockers else "Business Development"}


def _blocking_items(validation: dict[str, Any], readiness: dict[str, Any], intake: dict[str, Any]) -> list[dict[str, Any]]:
    return [*(validation.get("blockers") or []), *(readiness.get("blocking") or []), *(intake.get("blockers") or [])]


def proposal_breakdown(db: Session, proposal: Opportunity, forms: dict[str, Any] | None = None) -> dict[str, Any]:
    """Project the existing Proposal scope/contribution data for Owner readability.

    This is deliberately a read projection. ProposalServiceScopeItem,
    ProposalEngineeringContribution, and ProposalExternalCostAssumption remain
    the authoritative structured sources; no ProposalBreakdown table is added.
    """
    fields = proposal.proposal_fields_json or {}
    forms = forms or forms_v2_projection(db, proposal)
    items: list[dict[str, Any]] = []
    for item in forms.get("service_scope_items") or []:
        items.append({
            "id": item["id"],
            "kind": "Service scope",
            "label": item["description"],
            "included": item["included"],
            "status": item.get("status"),
            "source": "AMEC Scope / Engineering Preparation",
            "lineage": {"entity": "ProposalServiceScopeItem", "id": item["id"]},
        })
    for item in forms.get("engineering_contributions") or []:
        items.append({
            "id": item["id"],
            "kind": "Technical input",
            "label": item.get("contribution_type", "Engineering contribution").replace("_", " ").title(),
            "detail": item["content"],
            "discipline": item.get("discipline_code"),
            "status": item.get("status"),
            "source": "Engineering Preparation",
            "lineage": {"entity": "ProposalEngineeringContribution", "id": item["id"]},
        })
    for item in forms.get("external_cost_assumptions") or []:
        items.append({
            "id": item["id"],
            "kind": "External / pass-through assumption",
            "label": item["description"],
            "detail": item.get("rationale"),
            "amount": item.get("estimated_amount"),
            "currency": item.get("currency"),
            "status": item.get("status"),
            "source": "Commercial planning",
            "lineage": {"entity": "ProposalExternalCostAssumption", "id": item["id"]},
        })
    technical_deliverables = fields.get("technical_deliverables")
    if technical_deliverables:
        values = technical_deliverables if isinstance(technical_deliverables, list) else [technical_deliverables]
        for index, value in enumerate(values):
            detail = value if isinstance(value, str) else value.get("description") or value.get("title") or str(value)
            items.append({
                "id": f"technical-deliverable-{index}",
                "kind": "Technical deliverable",
                "label": detail,
                "source": "Engineering Preparation",
                "lineage": {"field": "technical_deliverables", "index": index},
            })
    return {
        "source": "Current ProposalServiceScopeItem, ProposalEngineeringContribution, ProposalExternalCostAssumption, and technical-deliverable projection",
        "items": items,
        "commercial_summary": {
            "price": fields.get("price"),
            "currency": fields.get("currency") or "QAR",
            "duration": fields.get("duration") or fields.get("period"),
            "payment_terms": fields.get("payment_terms") or fields.get("payment_condition"),
            "inclusions": fields.get("inclusions"),
            "exclusions": fields.get("exclusions"),
        },
        "has_content": bool(items or any((fields.get(key) for key in ("inclusions", "exclusions", "price", "duration", "payment_terms", "payment_condition")))),
        "truth": "PROPOSAL_TRANSACTION_PROJECTION",
    }


def proposal_authority(db: Session, proposal: Opportunity, validation: dict[str, Any], readiness: dict[str, Any], intake: dict[str, Any], current: ProposalAcceptedRevision | None = None) -> dict[str, Any]:
    policy = str(runtime_decision_value(db, "PROPOSAL_ACCEPT_AUTHORITY", "OWNER_OR_AUTHORIZED_COMMERCIAL_APPROVER")).upper()
    required_authority = "Owner" if policy == "OWNER_ONLY" else "Owner or authorized Commercial Approver"
    blockers = _blocking_items(validation, readiness, intake)
    commercial_states = {"PROPOSAL_HANDOVER", "READY_FOR_QUOTATION", "COMMERCIAL_REVIEW", "QUOTATION_IN_PROGRESS"}
    if current:
        status = "ACCEPTED"
        status_label = "Accepted Proposal revision recorded"
        last_decision = f"Accepted by {current.accepted_by} on {current.accepted_at.isoformat()}"
    elif proposal.status in commercial_states and blockers:
        status = "BLOCKED"
        status_label = "Proposal review blocked by readiness"
        last_decision = "No human Proposal review recorded"
    elif proposal.status in commercial_states:
        status = "REVIEW_REQUIRED"
        status_label = "Proposal Review / Authority Required"
        last_decision = "No human Proposal review recorded"
    elif proposal.status == "CLOSED":
        status = "CLOSED"
        status_label = "Proposal commercially closed"
        last_decision = "No further Proposal acceptance action"
    else:
        status = "NOT_YET_REQUIRED"
        status_label = "Review becomes relevant after Engineering Preparation"
        last_decision = "No human Proposal review recorded"
    return {
        "status": status,
        "status_label": status_label,
        "required_authority": required_authority,
        "current_reviewer": "Business Development" if proposal.status in commercial_states else ("Engineering" if proposal.status == "PROPOSAL_PREPARATION" else "Business Development"),
        "readiness_blockers": blockers,
        "last_review_decision": last_decision,
        "next_action": "Accept Proposal" if status == "REVIEW_REQUIRED" else "Resolve Proposal readiness blockers" if status == "BLOCKED" else "Proceed to Contract handoff" if status == "ACCEPTED" else "Review Proposal when technically ready",
        "accept_eligible": status == "REVIEW_REQUIRED" and not blockers,
        "policy_source": "PROPOSAL_ACCEPT_AUTHORITY runtime Owner decision",
        "government_authority": False,
    }


def owner_lane_memberships(proposal: Opportunity, validation: dict[str, Any], readiness: dict[str, Any], intake: dict[str, Any], authority: dict[str, Any]) -> dict[str, Any]:
    blockers = _blocking_items(validation, readiness, intake)
    need_action = bool(blockers) or proposal.status == "CLIENT_RESPONSE_PENDING"
    authority_review = authority["status"] == "REVIEW_REQUIRED" and not need_action
    ready_close = proposal.status in {"CLIENT_RESPONSE_PENDING", "ACCEPTED", "CONTRACT_HANDOVER", "CLOSED"} and not need_action
    memberships = ["ALL"]
    if need_action:
        memberships.append("NEED_ACTION")
    if authority_review:
        memberships.append("AUTHORITY_REVIEW")
    if ready_close:
        memberships.append("READY_CLOSE")
    primary = "NEED_ACTION" if need_action else "AUTHORITY_REVIEW" if authority_review else "READY_CLOSE" if ready_close else "ALL"
    return {
        "primary": primary,
        "memberships": memberships,
        "reason_codes": [item.get("code") for item in blockers],
        "reason_labels": [item.get("label") for item in blockers],
        "predicate_version": "bd-proposal-owner-lanes-v1",
    }


def owner_lane_definitions() -> list[dict[str, str]]:
    return [
        {"code": "ALL", "label": "All", "predicate": "accessible Proposal rows after current search/stage/project isolation"},
        {"code": "NEED_ACTION", "label": "Need Action", "predicate": "current validation/readiness/intake blockers or client response follow-up"},
        {"code": "AUTHORITY_REVIEW", "label": "Authority Review", "predicate": "commercial review lifecycle, no blockers, human Proposal Accept authority required"},
        {"code": "READY_CLOSE", "label": "Ready / Close", "predicate": "client response, accepted, contract handoff, or closed lifecycle with no active blockers"},
    ]


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
    current_sources = [item for item in sources if item.status == "CURRENT"]
    superseded_conflicts = [item for item in sources if item.status == "CONFLICT" and any(current.supersedes_id == item.id for current in current_sources)]
    conflicts = [item for item in sources if item.status == "CONFLICT" and item not in superseded_conflicts]
    if superseded_conflicts:
        warnings.append({"code": "SOURCE_CONFLICT_HISTORY", "label": "A prior source revision was superseded and remains in history"})
    if conflicts:
        blockers.append({"code": "SOURCE_CONFLICTS_UNRESOLVED", "label": "Resolve conflicting source evidence"})
    if not (fields.get("inclusions") or fields.get("exclusions")):
        warnings.append({"code": "COMMERCIAL_BOUNDARIES_REVIEW", "label": "Confirm inclusions and exclusions"})
    from .proposal_final_hardening import hardening_projection
    hardening = hardening_projection(db, proposal)
    blockers.extend(hardening["accept_blockers"])
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
        "hardening": hardening,
    }


def proposal_projection(db: Session, proposal: Opportunity) -> dict[str, Any]:
    fields = proposal.proposal_fields_json or {}
    sources = _sources(db, proposal.id)
    revisions = db.scalars(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == proposal.id).order_by(ProposalAcceptedRevision.revision_number.desc())).all()
    current = revisions[0] if revisions else None
    validation = validate_proposal(db, proposal)
    readiness = v2_readiness(db, proposal, validation)
    stage_labels = {
        "RECEIVED": "Intake & Sources", "IN_REVIEW": "Intake & Sources", "PROPOSAL_PREPARATION": "Engineering Preparation",
        "PROPOSAL_HANDOVER": "Commercial Review", "READY_FOR_QUOTATION": "Ready for Quotation", "COMMERCIAL_REVIEW": "Commercial Review", "QUOTATION_IN_PROGRESS": "Quotation in Progress",
        "CLIENT_RESPONSE_PENDING": "Client Response", "ACCEPTED": "Contract Handoff", "CONTRACT_HANDOVER": "Contract Handoff", "CLOSED": "Closed",
    }
    intake = intake_readiness(db, proposal)
    configuration = proposal_configuration(db, proposal)
    notes = db.scalars(select(ProposalNote).where(ProposalNote.proposal_id == proposal.id).order_by(ProposalNote.created_at.desc())).all()
    site_photos = [item for item in sources if item.source_type == "SITE_PHOTO" and item.status == "CURRENT"]
    forms = forms_v2_projection(db, proposal)
    breakdown = proposal_breakdown(db, proposal, forms)
    from .proposal_final_hardening import hardening_projection
    hardening = hardening_projection(db, proposal, forms)
    current_owner = "Engineering" if proposal.status == "PROPOSAL_PREPARATION" else "Business Development"
    blockers = _blocking_items(validation, readiness, intake)
    next_action = (
        "Complete technical Proposal preparation" if proposal.status == "PROPOSAL_PREPARATION" else
        "Resolve intake blockers" if proposal.status in {"RECEIVED", "IN_REVIEW"} and blockers else
        "Proceed to Engineering Preparation" if proposal.status in {"RECEIVED", "IN_REVIEW"} else
        "Resolve Proposal readiness blockers" if proposal.status in {"PROPOSAL_HANDOVER", "COMMERCIAL_REVIEW", "QUOTATION_IN_PROGRESS"} and blockers else
        "Review Proposal Authority" if proposal.status in {"PROPOSAL_HANDOVER", "READY_FOR_QUOTATION", "COMMERCIAL_REVIEW", "QUOTATION_IN_PROGRESS"} else
        "Follow up client response" if proposal.status == "CLIENT_RESPONSE_PENDING" else
        "Proceed to Contract handoff" if proposal.status in {"ACCEPTED", "CONTRACT_HANDOVER"} else
        "No further Proposal action" if proposal.status == "CLOSED" else
        "Review Proposal"
    )
    authority = proposal_authority(db, proposal, validation, readiness, intake, current)
    lanes = owner_lane_memberships(proposal, validation, readiness, intake, authority)
    outputs = db.scalars(select(ProposalOutputArtifact).where(ProposalOutputArtifact.proposal_id == proposal.id).order_by(ProposalOutputArtifact.created_at.desc())).all()
    stage_events = db.scalars(
        select(AuditEvent)
        .where(
            AuditEvent.entity_type == "Opportunity",
            AuditEvent.entity_id == proposal.id,
            AuditEvent.event_type.in_((
                "BD_PROPOSAL_PROCEEDED_TO_ENGINEERING",
                "PROPOSAL_PROCEEDED_TO_PREPARATION",
                "ENGINEERING_PROPOSAL_READY_FOR_BD",
                "BD_PROPOSAL_HUMAN_ACCEPTED",
                "PROPOSAL_CONTRACT_TRANSITION",
            )),
        )
        .order_by(AuditEvent.occurred_at)
    ).all()
    stage_gate = {
        "current_stage": proposal.status,
        "intake": {
            "state": "COMPLETED" if intake["ready"] else "RECONCILIATION_REQUIRED" if proposal.status not in {"RECEIVED", "IN_REVIEW"} else "INCOMPLETE",
            "blockers": intake["blockers"],
            "warnings": intake["warnings"],
            "message": "Upstream Intake reconciliation required" if proposal.status not in {"RECEIVED", "IN_REVIEW"} and not intake["ready"] else None,
        },
        "current_stage_readiness": {
            "ready": readiness["ready"],
            "blockers": readiness["blocking"],
            "warnings": readiness["warnings"],
        },
    }
    return {
        "id": proposal.id,
        "proposal_reference": proposal.opportunity_reference,
        "project_reference": proposal.canonical_project_reference or proposal.provisional_reference,
        "project_id": proposal.project_id,
        "client_account_id": proposal.client_account_id,
        "client_name": fields.get("client_name"),
        "title": proposal.title,
        "stage": proposal.status,
        "stage_label": stage_labels.get(proposal.status, proposal.status.replace("_", " ").title()),
        "lifecycle": [{"number": 1, "label": "Intake & Sources", "active": proposal.status in {"RECEIVED", "IN_REVIEW"}}, {"number": 2, "label": "Engineering Preparation", "active": proposal.status == "PROPOSAL_PREPARATION"}, {"number": 3, "label": "Commercial Review", "active": proposal.status in {"PROPOSAL_HANDOVER", "READY_FOR_QUOTATION", "COMMERCIAL_REVIEW", "QUOTATION_IN_PROGRESS"}}, {"number": 4, "label": "Client Response", "active": proposal.status == "CLIENT_RESPONSE_PENDING"}, {"number": 5, "label": "Contract Handoff", "active": proposal.status in {"ACCEPTED", "CONTRACT_HANDOVER"}}],
        "current_owner": current_owner,
        "next_actor": "Engineering" if proposal.status == "PROPOSAL_PREPARATION" else "Business Development",
        "next_action": {"label": next_action, "eligible": intake["ready"] if proposal.status in {"RECEIVED", "IN_REVIEW"} else not blockers},
        "amount": fields.get("price"),
        "last_activity": proposal.updated_at.isoformat() if proposal.updated_at else None,
        "updated_at": proposal.updated_at.isoformat() if proposal.updated_at else None,
        "fields": fields,
        "provenance": fields.get("provenance", {}),
        "amec_input": fields.get("amec_input", {}),
        "additional_information": fields.get("additional_information"),
        "sources": [_source_projection(item) for item in sources],
        "validation": validation,
        "readiness_v2": readiness,
        "intake_readiness": intake,
        "configuration": configuration,
        "notes": [{"id": row.id, "note_type": row.note_type, "content": row.content, "entered_by": row.entered_by, "related_contact": row.related_contact, "status": row.status, "provenance": row.provenance, "created_at": row.created_at.isoformat()} for row in notes],
        "site_photos": [_source_projection(item) for item in site_photos],
        "forms_v2": {**forms, "proposal_form": [{"id": item.id, "filename": item.source_filename, "source_reference": item.sor_path, "source_revision": item.source_revision, "verification_state": item.verification_state, "status": item.status, "created_at": item.created_at.isoformat()} for item in db.scalars(select(ProposalIntakeArtifact).where(ProposalIntakeArtifact.opportunity_id == proposal.id, ProposalIntakeArtifact.semantic_class == "PROPOSAL_FORM").order_by(ProposalIntakeArtifact.created_at.desc())).all()]},
        "proposal_breakdown": breakdown,
        "hardening": hardening,
        "authority": authority,
        "owner_lane": lanes,
        "outputs": {
            "available": bool(current and outputs),
            "proposal": next(({"id": row.id, "filename": row.filename, "content_hash": row.content_hash, "lineage": row.lineage, "created_at": row.created_at.isoformat()} for row in outputs if row.artifact_type == "PROPOSAL"), None),
            "checklist": next(({"id": row.id, "filename": row.filename, "content_hash": row.content_hash, "lineage": row.lineage, "created_at": row.created_at.isoformat()} for row in outputs if row.artifact_type == "CHECKLIST"), None),
            "pre_accept_message": "Available after human Proposal Accept" if not current else None,
        },
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
        "stage_gate": stage_gate,
        "stage_history": [{"event_type": event.event_type, "occurred_at": event.occurred_at.isoformat(), "actor": event.actor_id, "before": event.before_json, "after": event.after_json, "correlation_id": event.correlation_id} for event in stage_events],
        "ai_assist": validation["ai_assist"],
        "contract_eligible": bool(current and validation["ready"]),
        "synthetic_only": True,
    }


def snapshot_for_accept(db: Session, proposal: Opportunity, validation: dict[str, Any]) -> dict[str, Any]:
    fields = dict(proposal.proposal_fields_json or {})
    fields.pop("provenance", None)
    fields.pop("amec_input", None)
    source_ids = [item.id for item in _sources(db, proposal.id) if item.status == "CURRENT"]
    forms_snapshot = snapshot_forms_v2(db, proposal)
    from .proposal_final_hardening import hardening_projection, material_fingerprint
    hardening = hardening_projection(db, proposal, forms_snapshot)
    return {
        "proposal_id": proposal.id,
        "proposal_reference": proposal.opportunity_reference,
        "title": proposal.title,
        "project_reference": proposal.canonical_project_reference or proposal.provisional_reference,
        "client_account_id": proposal.client_account_id,
        "fields": fields,
        "amec_input": (proposal.proposal_fields_json or {}).get("amec_input", {}),
        "additional_information": (proposal.proposal_fields_json or {}).get("additional_information"),
        "proposal_breakdown": proposal_breakdown(db, proposal),
        "provenance": (proposal.proposal_fields_json or {}).get("provenance", {}),
        "source_ids": source_ids,
        "template": validation["template"]["item"],
        "checklist": validation["checklist"]["item"],
        "definitions": validation["definitions"],
        "dashboard_configuration": proposal_configuration(db, proposal),
        "forms_driven_v2": forms_snapshot,
        "hardening": {"unknowns": hardening["unknowns"], "conflicts": hardening["conflicts"], "material_acknowledgments": hardening["material_acknowledgments"], "active_staleness": hardening["active_staleness"], "client_responses": hardening["client_responses"], "commercial_outcome": hardening["commercial_outcome"]},
        "material_fingerprint": material_fingerprint(db, proposal, forms_snapshot),
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
