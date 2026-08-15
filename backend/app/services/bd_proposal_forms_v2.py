"""Forms-driven v2 commercial/scoping behavior for Business Development."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import (
    ClientAccount,
    DocumentVersion,
    ExternalBody,
    Jurisdiction,
    Opportunity,
    Party,
    ProposalAssumption,
    ProposalContactContext,
    ProposalEngineeringContribution,
    ProposalExpectedInputPreview,
    ProposalExternalCostAssumption,
    ProposalRegulatoryScopeIntent,
    ProposalServiceScopeItem,
    ProposalSiteContext,
    ProposalSourceEvidence,
    ProposalSourceLink,
    ProposalStakeholderIntent,
    RequirementDefinition,
    RequirementPolicyItem,
    RequirementPolicyVersion,
    ServiceType,
    ServiceTypeVersion,
    Property,
)
from .shared_domains import DomainConflict, active_policy_query, evaluate_policy, resolve_requirement_policy


def now() -> datetime:
    return datetime.now(timezone.utc)


def stable_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _iso(value: Any) -> str | None:
    return value.isoformat() if value else None


def _name(db: Session, model: Any, row_id: str | None) -> str | None:
    row = db.get(model, row_id) if row_id else None
    if not row:
        return None
    return getattr(row, "name_en", None) or getattr(row, "display_name", None) or getattr(row, "legal_name", None) or getattr(row, "code", None) or getattr(row, "name", None)


def _party_projection(db: Session, party_id: str | None) -> dict[str, Any] | None:
    party = db.get(Party, party_id) if party_id else None
    if not party:
        return None
    return {"id": party.id, "name_en": party.name_en, "name_ar": party.name_ar, "status": getattr(party.status, "value", party.status)}


def contact_projection(db: Session, proposal_id: str) -> dict[str, Any] | None:
    row = db.scalar(select(ProposalContactContext).where(ProposalContactContext.proposal_id == proposal_id))
    if not row:
        return None
    return {"id": row.id, "party": _party_projection(db, row.party_id), "display_name": row.display_name, "email": row.email, "mobile": row.mobile, "purpose": row.purpose, "status": row.status, "source_document_version_id": row.source_document_version_id, "notes": row.notes}


def site_projection(db: Session, proposal_id: str) -> dict[str, Any] | None:
    row = db.scalar(select(ProposalSiteContext).where(ProposalSiteContext.proposal_id == proposal_id))
    if not row:
        return None
    prop = db.get(Property, row.property_id) if row.property_id else None
    return {"id": row.id, "status": row.status, "property_id": row.property_id, "property": {"id": prop.id, "pin": prop.pin, "plot_number": prop.plot_number, "municipality": prop.municipality, "land_area": prop.land_area, "land_area_unit": prop.land_area_unit} if prop else None, "location_text": row.location_text, "plot_text": row.plot_text, "area_value": row.area_value, "area_unit": row.area_unit, "area_kind": row.area_kind, "site_description": row.site_description, "source_document_version_id": row.source_document_version_id, "resolution_note": row.resolution_note, "resolved_by": row.resolved_by, "resolved_at": _iso(row.resolved_at), "historical_snapshot": row.historical_snapshot or {}}


def stakeholder_projection(db: Session, row: ProposalStakeholderIntent) -> dict[str, Any]:
    return {"id": row.id, "role_code": row.role_code, "party": _party_projection(db, row.party_id), "party_id": row.party_id, "display_snapshot": row.display_snapshot, "status": row.status, "source_type": row.source_type, "source_document_version_id": row.source_document_version_id, "note": row.note}


def source_links_projection(db: Session, proposal_id: str) -> list[dict[str, Any]]:
    rows = db.scalars(select(ProposalSourceLink).where(ProposalSourceLink.proposal_id == proposal_id, ProposalSourceLink.active.is_(True)).order_by(ProposalSourceLink.created_at)).all()
    return [{"id": row.id, "source_evidence_id": row.source_evidence_id, "document_id": row.document_id, "document_version_id": row.document_version_id, "source_role": row.source_role, "added_by": row.added_by, "note": row.note} for row in rows]


def _scope_projection(db: Session, row: ProposalServiceScopeItem) -> dict[str, Any]:
    return {"id": row.id, "service_offering_code": row.service_offering_code, "scope_category_code": row.scope_category_code, "discipline_code": row.discipline_code, "description": row.description, "included": row.included, "commercial_treatment": row.commercial_treatment, "regulatory_service_type_id": row.regulatory_service_type_id, "regulatory_service_type": _name(db, ServiceType, row.regulatory_service_type_id), "external_body_id": row.external_body_id, "external_body": _name(db, ExternalBody, row.external_body_id), "source_document_version_id": row.source_document_version_id, "rationale": row.rationale, "sort_order": row.sort_order, "status": row.status}


def _regulatory_projection(db: Session, row: ProposalRegulatoryScopeIntent) -> dict[str, Any]:
    version = db.get(ServiceTypeVersion, row.service_type_version_id) if row.service_type_version_id else None
    return {"id": row.id, "proposal_scope_item_id": row.proposal_scope_item_id, "external_body_id": row.external_body_id, "external_body": _name(db, ExternalBody, row.external_body_id), "service_type_id": row.service_type_id, "service_type": _name(db, ServiceType, row.service_type_id), "service_type_version_id": row.service_type_version_id, "service_type_version": version.version if version else None, "jurisdiction_id": row.jurisdiction_id, "jurisdiction": _name(db, Jurisdiction, row.jurisdiction_id), "status": row.status, "source_type": row.source_type, "source_document_version_id": row.source_document_version_id, "source_assertion_id": row.source_assertion_id, "rationale": row.rationale, "confidence": row.confidence, "human_confirmed_by": row.human_confirmed_by, "human_confirmed_at": _iso(row.human_confirmed_at), "notes": row.notes}


def _preview_projection(db: Session, row: ProposalExpectedInputPreview | None) -> dict[str, Any] | None:
    if not row:
        return None
    stale = preview_is_stale(db, row)
    return {"id": row.id, "status": "POLICY_STALE" if stale and not row.superseded else row.status, "policy_version_ids": row.policy_version_ids, "scope_intent_ids": row.scope_intent_ids, "result_items": row.result_items, "evaluation_context": row.evaluation_context, "evaluated_at": _iso(row.evaluated_at), "evaluated_by": row.evaluated_by, "superseded": row.superseded, "stale": stale, "content_hash": row.content_hash}


def latest_preview(db: Session, proposal_id: str) -> ProposalExpectedInputPreview | None:
    return db.scalar(select(ProposalExpectedInputPreview).where(ProposalExpectedInputPreview.proposal_id == proposal_id, ProposalExpectedInputPreview.superseded.is_(False)).order_by(ProposalExpectedInputPreview.created_at.desc()))


def preview_is_stale(db: Session, row: ProposalExpectedInputPreview) -> bool:
    if row.status not in {"POLICY_RESOLVED", "POLICY_STALE"}:
        return False
    intents = list(db.scalars(select(ProposalRegulatoryScopeIntent).where(ProposalRegulatoryScopeIntent.proposal_id == row.proposal_id, ProposalRegulatoryScopeIntent.status == "HUMAN_CONFIRMED_FOR_PROPOSAL")).all())
    if sorted(row.scope_intent_ids or []) != sorted(intent.id for intent in intents):
        return True
    current_policy_ids: list[str] = []
    for intent in intents:
        if not intent.service_type_id:
            return True
        try:
            policy = resolve_requirement_policy(db, service_type_id=intent.service_type_id, jurisdiction_id=intent.jurisdiction_id, external_body_id=intent.external_body_id)
        except DomainConflict:
            return True
        if policy.purpose in {"CLIENT_COLLECTION", "PRE_APPLICATION_CLIENT_COLLECTION"}:
            current_policy_ids.append(policy.id)
    return sorted(row.policy_version_ids or []) != sorted(current_policy_ids)


def forms_v2_projection(db: Session, proposal: Opportunity) -> dict[str, Any]:
    contact = contact_projection(db, proposal.id)
    site = site_projection(db, proposal.id)
    stakeholders = [stakeholder_projection(db, row) for row in db.scalars(select(ProposalStakeholderIntent).where(ProposalStakeholderIntent.proposal_id == proposal.id).order_by(ProposalStakeholderIntent.created_at)).all()]
    scopes = [_scope_projection(db, row) for row in db.scalars(select(ProposalServiceScopeItem).where(ProposalServiceScopeItem.proposal_id == proposal.id).order_by(ProposalServiceScopeItem.sort_order, ProposalServiceScopeItem.created_at)).all()]
    regulatory = [_regulatory_projection(db, row) for row in db.scalars(select(ProposalRegulatoryScopeIntent).where(ProposalRegulatoryScopeIntent.proposal_id == proposal.id).order_by(ProposalRegulatoryScopeIntent.created_at)).all()]
    assumptions = [{"id": row.id, "category": row.category, "statement": row.statement, "materiality": row.materiality, "source_type": row.source_type, "source_reference": row.source_reference, "status": row.status, "acknowledged_by": row.acknowledged_by, "acknowledged_at": _iso(row.acknowledged_at)} for row in db.scalars(select(ProposalAssumption).where(ProposalAssumption.proposal_id == proposal.id).order_by(ProposalAssumption.created_at)).all()]
    external_costs = [{"id": row.id, "description": row.description, "external_body_id": row.external_body_id, "external_body": _name(db, ExternalBody, row.external_body_id), "estimated_amount": row.estimated_amount, "currency": row.currency, "treatment": row.treatment, "source_reference": row.source_reference, "rationale": row.rationale, "status": row.status} for row in db.scalars(select(ProposalExternalCostAssumption).where(ProposalExternalCostAssumption.proposal_id == proposal.id).order_by(ProposalExternalCostAssumption.created_at)).all()]
    engineering = [{"id": row.id, "discipline_code": row.discipline_code, "contribution_type": row.contribution_type, "content": row.content, "technical_rule_set_version_id": row.technical_rule_set_version_id, "source_document_version_id": row.source_document_version_id, "status": row.status, "contributed_by": row.contributed_by} for row in db.scalars(select(ProposalEngineeringContribution).where(ProposalEngineeringContribution.proposal_id == proposal.id).order_by(ProposalEngineeringContribution.created_at)).all()]
    preview = latest_preview(db, proposal.id)
    client = db.get(ClientAccount, proposal.client_account_id) if proposal.client_account_id else None
    source_conflicts = [{"id": row.id, "source_type": row.source_type, "content_hash": row.content_hash, "source_reference": row.source_reference, "status": row.status} for row in db.scalars(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id, ProposalSourceEvidence.status == "CONFLICT").order_by(ProposalSourceEvidence.created_at)).all()]
    return {"commercial_client": {"client_account_id": client.id, "display_name": client.display_name, "canonical_party_id": client.canonical_party_id, "party": _party_projection(db, client.canonical_party_id)} if client else None, "proposal_contact": contact, "site_context": site, "stakeholders": stakeholders, "source_links": source_links_projection(db, proposal.id), "source_conflicts": source_conflicts, "service_scope_items": scopes, "regulatory_scope_intents": regulatory, "assumptions": assumptions, "external_cost_assumptions": external_costs, "engineering_contributions": engineering, "expected_client_inputs": _preview_projection(db, preview), "safe_defaults": {"commercial_client_is_not_owner_or_applicant": True, "regulatory_scope_is_intent_only": True, "duration_is_service_estimate": True, "proposal_checklist_is_separate": True}}


def v2_readiness(db: Session, proposal: Opportunity, base_validation: dict[str, Any]) -> dict[str, Any]:
    v2 = forms_v2_projection(db, proposal)
    warnings: list[dict[str, str]] = []
    blockers: list[dict[str, str]] = []
    if not v2["proposal_contact"]:
        warnings.append({"code": "PROPOSAL_CONTACT_UNRESOLVED", "label": "Proposal contact is not recorded"})
    if not v2["site_context"] or v2["site_context"]["status"] != "LINKED":
        warnings.append({"code": "PROPERTY_UNRESOLVED", "label": "Site / Property remains unresolved; commercial acceptance may use an explicit assumption"})
    if not v2["service_scope_items"] and not (proposal.proposal_fields_json or {}).get("scope_of_work"):
        blockers.append({"code": "SERVICE_SCOPE_REQUIRED", "label": "AMEC service scope"})
    open_material = [row for row in v2["assumptions"] if row["materiality"] == "MATERIAL" and row["status"] != "ACKNOWLEDGED"]
    if open_material:
        blockers.append({"code": "MATERIAL_ASSUMPTION_ACKNOWLEDGEMENT_REQUIRED", "label": "Acknowledge material commercial assumptions"})
    conflict_sources = [row for row in (proposal.proposal_fields_json or {}).get("conflicts", []) if isinstance(row, dict) and row.get("status", "OPEN") == "OPEN"]
    source_rows = list(db.scalars(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id, ProposalSourceEvidence.status == "CONFLICT")).all())
    current_sources = list(db.scalars(select(ProposalSourceEvidence).where(ProposalSourceEvidence.proposal_id == proposal.id, ProposalSourceEvidence.status == "CURRENT")).all())
    active_source_conflicts = [row for row in source_rows if not any(current.supersedes_id == row.id for current in current_sources)]
    if conflict_sources or active_source_conflicts:
        blockers.append({"code": "MATERIAL_CONFLICT_REQUIRES_DECISION", "label": "Resolve or explicitly accept material conflicts"})
    if not v2["regulatory_scope_intents"]:
        warnings.append({"code": "REGULATORY_SCOPE_UNKNOWN", "label": "Regulatory scoping intent is not yet recorded"})
    elif not any(row["status"] == "HUMAN_CONFIRMED_FOR_PROPOSAL" for row in v2["regulatory_scope_intents"]):
        warnings.append({"code": "REGULATORY_SCOPE_CONFIRMATION_PENDING", "label": "Regulatory scoping suggestions require human confirmation"})
    preview = v2["expected_client_inputs"]
    if preview and preview["status"] in {"NO_POLICY", "POLICY_AMBIGUOUS", "POLICY_STALE"}:
        warnings.append({"code": preview["status"], "label": f"Expected Client Inputs — Preliminary: {preview['status'].replace('_', ' ').title()}"})
    return {"ready": bool(base_validation.get("ready")) and not blockers, "blocking": blockers, "warnings": warnings, "safe_default": "Regulatory/property unknowns warn unless Owner policy makes them blocking", "commercial_ready_not_regulatory_ready": True}


def set_contact(db: Session, proposal: Opportunity, payload: dict[str, Any], actor: str) -> ProposalContactContext:
    row = db.scalar(select(ProposalContactContext).where(ProposalContactContext.proposal_id == proposal.id))
    if not row:
        row = ProposalContactContext(proposal_id=proposal.id)
        db.add(row)
    for key in ("party_id", "display_name", "email", "mobile", "purpose", "status", "source_document_version_id", "notes"):
        if key in payload:
            setattr(row, key, payload[key])
    if row.party_id and not db.get(Party, row.party_id):
        raise HTTPException(422, {"code": "PARTY_NOT_FOUND", "party_id": row.party_id})
    db.flush()
    return row


def set_site_context(db: Session, proposal: Opportunity, payload: dict[str, Any], actor: str) -> ProposalSiteContext:
    row = db.scalar(select(ProposalSiteContext).where(ProposalSiteContext.proposal_id == proposal.id))
    if not row:
        row = ProposalSiteContext(proposal_id=proposal.id)
        db.add(row)
    for key in ("property_id", "status", "location_text", "plot_text", "area_value", "area_unit", "area_kind", "site_description", "site_photo_source_link_id", "source_document_version_id", "resolution_note"):
        if key in payload:
            setattr(row, key, payload[key])
    if row.property_id and not db.get(Property, row.property_id):
        raise HTTPException(422, {"code": "PROPERTY_NOT_FOUND", "property_id": row.property_id})
    if row.property_id:
        row.status = "LINKED"
        row.resolved_by = actor
        row.resolved_at = now()
    else:
        row.status = payload.get("status") or "UNRESOLVED"
        row.resolved_by = None
        row.resolved_at = None
    db.flush()
    return row


def add_source_link(db: Session, proposal: Opportunity, payload: dict[str, Any], actor: str) -> ProposalSourceLink:
    version_id = payload.get("document_version_id")
    if not version_id:
        raise HTTPException(422, {"code": "EXACT_DOCUMENT_VERSION_REQUIRED"})
    version = db.get(DocumentVersion, version_id)
    if not version:
        raise HTTPException(422, {"code": "DOCUMENT_VERSION_NOT_FOUND", "document_version_id": version_id})
    row = ProposalSourceLink(proposal_id=proposal.id, source_evidence_id=payload.get("source_evidence_id"), document_id=version.document_id, document_version_id=version.id, source_role=payload.get("source_role", "OTHER"), added_by=actor, note=payload.get("note"))
    db.add(row)
    db.flush()
    return row


def create_preview(db: Session, proposal: Opportunity, actor: str, correlation_id: str) -> ProposalExpectedInputPreview:
    intents = list(db.scalars(select(ProposalRegulatoryScopeIntent).where(ProposalRegulatoryScopeIntent.proposal_id == proposal.id, ProposalRegulatoryScopeIntent.status == "HUMAN_CONFIRMED_FOR_PROPOSAL")).all())
    items: list[dict[str, Any]] = []
    policy_ids: list[str] = []
    statuses: set[str] = set()
    for intent in intents:
        if not intent.service_type_id:
            statuses.add("APPLICABILITY_UNKNOWN")
            continue
        try:
            policy = resolve_requirement_policy(db, service_type_id=intent.service_type_id, jurisdiction_id=intent.jurisdiction_id, external_body_id=intent.external_body_id)
            if policy.purpose not in {"CLIENT_COLLECTION", "PRE_APPLICATION_CLIENT_COLLECTION"}:
                statuses.add("NO_POLICY")
                continue
            policy_ids.append(policy.id)
            result = evaluate_policy(db, policy, context={"context_type": "PROPOSAL_EXPECTED_INPUT_PREVIEW", "context_id": proposal.id, "service_type_id": intent.service_type_id, "jurisdiction_id": intent.jurisdiction_id, "external_body_id": intent.external_body_id}, evidence=[], actor_id=actor, correlation_id=correlation_id)
            definitions = {row.id: row for row in db.scalars(select(RequirementDefinition).where(RequirementDefinition.id.in_([item["requirement_definition_id"] for item in result["items"]]))).all()}
            for item in result["items"]:
                definition = definitions.get(item["requirement_definition_id"])
                items.append({**item, "label": definition.name_en if definition else item["requirement_definition_id"], "scope_intent_id": intent.id, "phase_state": "NOT_DUE" if item["applicability"] == "NOT_APPLICABLE" else "CURRENT"})
            statuses.add("POLICY_RESOLVED")
        except DomainConflict as exc:
            statuses.add("POLICY_AMBIGUOUS" if "AMBIGUOUS" in str(exc) else "NO_POLICY")
    if not intents:
        statuses.add("APPLICABILITY_UNKNOWN")
    status = "POLICY_RESOLVED" if statuses == {"POLICY_RESOLVED"} else sorted(statuses)[0]
    prior = latest_preview(db, proposal.id)
    if prior:
        prior.superseded = True
    row = ProposalExpectedInputPreview(proposal_id=proposal.id, status=status, policy_version_ids=policy_ids, scope_intent_ids=[row.id for row in intents], result_items=items, evaluation_context={"purpose": "CLIENT_COLLECTION", "generated_at": now().isoformat()}, evaluated_by=actor, content_hash=stable_hash({"policy_version_ids": policy_ids, "scope_intent_ids": [row.id for row in intents], "items": items}))
    db.add(row)
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="BD_PROPOSAL_EXPECTED_CLIENT_INPUT_PREVIEW_CREATED", entity_type="Opportunity", entity_id=proposal.id, actor_id=actor, after={"preview_id": row.id, "status": row.status, "policy_version_ids": policy_ids})
    return row


def snapshot_forms_v2(db: Session, proposal: Opportunity) -> dict[str, Any]:
    current = forms_v2_projection(db, proposal)
    current["captured_at"] = now().isoformat()
    return current
