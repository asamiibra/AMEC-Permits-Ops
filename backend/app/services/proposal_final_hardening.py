"""Forms-v2 hardening projections and typed Proposal commands."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    Opportunity,
    ProposalAcceptedRevision,
    ProposalClientResponse,
    ProposalCommercialOutcome,
    ProposalConflict,
    ProposalMaterialAcknowledgment,
    ProposalRevision,
    ProposalSourceEvidence,
    ProposalStalenessEvent,
    ProposalUnknown,
)
from .proposal_workspace import stable_hash


def now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def material_fingerprint(db: Session, proposal: Opportunity, forms: dict[str, Any] | None = None) -> str:
    fields = dict(proposal.proposal_fields_json or {})
    fields.pop("provenance", None)
    normalized_forms = dict(forms or {})
    normalized_forms.pop("captured_at", None)
    return stable_hash({
        "proposal_id": proposal.id,
        "title": proposal.title,
        "project_reference": proposal.canonical_project_reference or proposal.provisional_reference,
        "client_account_id": proposal.client_account_id,
        "fields": fields,
        "forms": normalized_forms,
        "source_hashes": sorted((item.content_hash, item.source_type, item.status) for item in db.scalars(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id)).all()),
        "master_content": master_content_fingerprint(db),
    })


def master_content_fingerprint(db: Session) -> str:
    """Capture the exact reusable sources that a Proposal would resolve now."""
    from .master_content import resolve_master_content_purpose

    resolutions = []
    for purpose in ("PROPOSAL_TEMPLATE", "PROPOSAL_CHECKLIST"):
        result = resolve_master_content_purpose(db, module="BD", usage_type=purpose)
        resolutions.append({
            "purpose": purpose,
            "status": result["status"],
            "candidates": sorted((item["id"], item["version_id"], item["hash"]) for item in result.get("candidates", [])),
        })
    return stable_hash(resolutions)


def hardening_projection(db: Session, proposal: Opportunity, forms: dict[str, Any] | None = None) -> dict[str, Any]:
    unknowns = list(db.scalars(select(ProposalUnknown).where(ProposalUnknown.proposal_id == proposal.id).order_by(ProposalUnknown.created_at)).all())
    conflicts = list(db.scalars(select(ProposalConflict).where(ProposalConflict.proposal_id == proposal.id).order_by(ProposalConflict.created_at)).all())
    acknowledgments = list(db.scalars(select(ProposalMaterialAcknowledgment).where(ProposalMaterialAcknowledgment.proposal_id == proposal.id).order_by(ProposalMaterialAcknowledgment.acknowledged_at.desc())).all())
    ack_by_target = {(item.target_type, item.target_id): item for item in acknowledgments}
    staleness = list(db.scalars(select(ProposalStalenessEvent).where(ProposalStalenessEvent.proposal_id == proposal.id).order_by(ProposalStalenessEvent.created_at.desc())).all())
    active_staleness = [item for item in staleness if item.status == "ACTIVE"]
    revisions = list(db.scalars(select(ProposalRevision).where(ProposalRevision.proposal_id == proposal.id).order_by(ProposalRevision.revision_number.desc())).all())
    responses = list(db.scalars(select(ProposalClientResponse).where(ProposalClientResponse.proposal_id == proposal.id).order_by(ProposalClientResponse.recorded_at.desc())).all())
    outcome = db.scalar(select(ProposalCommercialOutcome).where(ProposalCommercialOutcome.proposal_id == proposal.id))
    accepted = db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == proposal.id).order_by(ProposalAcceptedRevision.revision_number.desc()))
    fingerprint = material_fingerprint(db, proposal, forms)
    accepted_fingerprint = (accepted.snapshot or {}).get("material_fingerprint") if accepted else None
    current_master_fingerprint = master_content_fingerprint(db)
    accepted_master_fingerprint = (accepted.snapshot or {}).get("master_content_fingerprint") if accepted else None
    master_content_changed = bool(accepted and accepted_master_fingerprint and accepted_master_fingerprint != current_master_fingerprint)
    draft_revalidation_open = bool(accepted and any(item.status == "DRAFT" and item.base_accepted_revision_id == accepted.id for item in revisions))
    master_revalidation_required = master_content_changed and not draft_revalidation_open
    material_open_unknowns = [item for item in unknowns if item.status == "OPEN" and item.materiality in {"MATERIAL", "BLOCKING"} and ("PROPOSAL_UNKNOWN", item.id) not in ack_by_target]
    material_open_conflicts = [item for item in conflicts if item.status == "OPEN" and item.materiality in {"MATERIAL", "BLOCKING"} and ("PROPOSAL_CONFLICT", item.id) not in ack_by_target]
    return {
        "stakeholders": forms.get("stakeholders", []) if forms else [],
        "unknowns": [{"id": item.id, "category": item.category, "statement": item.statement, "materiality": item.materiality, "source_type": item.source_type, "source_reference": item.source_reference, "status": item.status, "resolution": item.resolution, "resolved_by": item.resolved_by, "resolved_at": _iso(item.resolved_at), "acknowledged": ("PROPOSAL_UNKNOWN", item.id) in ack_by_target} for item in unknowns],
        "conflicts": [{"id": item.id, "field_code": item.field_code, "source_a": item.source_a, "value_a": item.value_a, "source_b": item.source_b, "value_b": item.value_b, "materiality": item.materiality, "status": item.status, "resolution": item.resolution, "resolver": item.resolver, "resolved_at": _iso(item.resolved_at), "acknowledged": ("PROPOSAL_CONFLICT", item.id) in ack_by_target} for item in conflicts],
        "material_acknowledgments": [{"id": item.id, "target_type": item.target_type, "target_id": item.target_id, "target_revision_hash": item.target_revision_hash, "acknowledged_by": item.acknowledged_by, "acknowledged_at": _iso(item.acknowledged_at), "note": item.note} for item in acknowledgments],
        "staleness": [{"id": item.id, "trigger_type": item.trigger_type, "trigger_reference": item.trigger_reference, "reason_code": item.reason_code, "impacted_sections": item.impacted_sections, "status": item.status, "detected_by": item.detected_by, "created_at": _iso(item.created_at)} for item in staleness],
        "active_staleness": [{"id": item.id, "reason_code": item.reason_code, "impacted_sections": item.impacted_sections, "trigger_reference": item.trigger_reference} for item in active_staleness],
        "current_information_changed": bool(accepted and accepted_fingerprint and accepted_fingerprint != fingerprint),
        "master_content_changed": master_content_changed,
        "master_revalidation_required": master_revalidation_required,
        "master_content_fingerprint": current_master_fingerprint,
        "accepted_master_content_fingerprint": accepted_master_fingerprint,
        "accepted_fingerprint": accepted_fingerprint,
        "current_fingerprint": fingerprint,
        "revisions": [{"id": item.id, "revision_number": item.revision_number, "base_accepted_revision_id": item.base_accepted_revision_id, "status": item.status, "change_summary": item.change_summary, "content_hash": item.content_hash, "created_by": item.created_by} for item in revisions],
        "client_responses": [{"id": item.id, "accepted_revision_id": item.accepted_revision_id, "response_type": item.response_type, "evidence_reference": item.evidence_reference, "notes": item.notes, "recorded_by": item.recorded_by, "recorded_at": _iso(item.recorded_at)} for item in responses],
        "commercial_outcome": {"id": outcome.id, "accepted_revision_id": outcome.accepted_revision_id, "outcome": outcome.outcome, "reason": outcome.reason, "evidence_reference": outcome.evidence_reference, "recorded_by": outcome.recorded_by, "recorded_at": _iso(outcome.recorded_at)} if outcome else None,
        "material_open_unknowns": [{"id": item.id, "label": item.statement} for item in material_open_unknowns],
        "material_open_conflicts": [{"id": item.id, "label": f"{item.field_code}: {item.source_a} vs {item.source_b}"} for item in material_open_conflicts],
        "accept_blockers": [{"code": "MATERIAL_UNKNOWN_REQUIRES_ACKNOWLEDGMENT", "label": item.statement} for item in material_open_unknowns] + [{"code": "MATERIAL_CONFLICT_REQUIRES_ACKNOWLEDGMENT", "label": f"{item.field_code}: {item.source_a} vs {item.source_b}"} for item in material_open_conflicts] + ([{"code": "SOURCE_CHANGE_REQUIRES_REVIEW", "label": "Source or governed input changed; review impacted Proposal sections before Accept"}] if active_staleness else []) + ([{"code": "MASTER_CONTENT_REVALIDATION_REQUIRED", "label": "Create an explicit Proposal revision to revalidate changed master content before Accept"}] if master_revalidation_required else []),
        "boundaries": {"client_response_is_not_amec_accept": True, "ready_close_is_not_outcome": True, "acknowledged_is_not_resolved": True, "authority_case_created": False},
    }


def impacted_sections_for_source(source_type: str) -> list[str]:
    return {
        "TENDER_DOCUMENT": ["client_request", "site_property", "engineering_preparation", "regulatory_scoping", "commercial", "expected_client_inputs", "readiness"],
        "TENDER_EMAIL": ["client_request", "stakeholders", "commercial", "readiness"],
        "TENDER_PHOTO": ["site_property", "area_semantics", "readiness"],
        "CLIENT_DATA": ["client_contacts", "stakeholders", "site_property", "client_request", "readiness"],
        "SITE_PHOTO": ["site_property", "readiness"],
    }.get(source_type, ["readiness"])
