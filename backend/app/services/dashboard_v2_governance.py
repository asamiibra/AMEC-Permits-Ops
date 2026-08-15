"""Dashboard V2 Waves B+C governance facade over canonical shared domains."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import (
    AutomationReadinessAssessment,
    ExternalBody,
    FormAutomationProfile,
    FormMappingRelease,
    FormMappingReleaseQAGate,
    FormMappingRule,
    FormQARun,
    DocumentVersion,
    MasterContentGovernanceProfile,
    SemanticKeyDefinition,
    Jurisdiction,
    MasterContentApplicability,
    MasterContentItem,
    MasterContentQualityFlag,
    MasterContentSourceSection,
    RequirementPolicyLineage,
    RequirementPolicyVersion,
    RegulatoryLifecyclePhase,
    ServiceType,
    TechnicalRuleLineage,
    TechnicalRule,
    TechnicalRuleSetVersion,
)
from .forms_governance import evaluate_readiness as evaluate_wave_a_readiness
from .shared_domains import projection


OWNER_ROLES = {"SYSTEM_ADMIN", "OWNER_SPONSOR"}
READ_ROLES = OWNER_ROLES | {"PROCESS_CHAMPION", "REQUIREMENT_STEWARD", "RESPONSIBLE_ENGINEER", "PERMIT_PREPARER"}
SOURCE_ROLES = {"PRIMARY", "SUPPORTING", "INTERPRETIVE", "SUPERSEDED"}
LINEAGE_STATUSES = {"DRAFT", "ACTIVE", "NEEDS_REVALIDATION", "SUPERSEDED", "RETIRED"}
RELEASE_STATUSES = {"DRAFT", "REVIEW", "APPROVED", "RELEASED", "NEEDS_REVALIDATION", "SUPERSEDED", "RETIRED"}
QA_TYPES = {"STRUCTURAL_MAPPING", "SYNTHETIC_FILL", "READ_BACK", "VISUAL", "ARABIC_RTL", "BILINGUAL", "REPEATING_GRID", "SIGNATURE_ZONE", "WRITER_OWNERSHIP", "NORMALIZED_RENDITION"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _actor(role: Any) -> str:
    return getattr(role, "value", str(role))


def _role_value(role: Any) -> str:
    return getattr(role, "value", str(role))


def require_owner(role: Any) -> None:
    if _role_value(role) not in OWNER_ROLES:
        raise HTTPException(403, {"code": "DASHBOARD_V2_OWNER_GOVERNANCE_REQUIRED"})


def require_reader(role: Any) -> None:
    if _role_value(role) not in READ_ROLES:
        raise HTTPException(403, {"code": "DASHBOARD_V2_GOVERNANCE_NOT_AUTHORIZED"})


def _error(code: str, status: int = 409, **details: Any) -> HTTPException:
    return HTTPException(status, {"code": code, **details})


def _date(value: str | date | None) -> date:
    if value is None:
        return date.today()
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _commit(db: Session, item: Any, *, request_id: str, event: str, role: Any, before: Any = None, after: Any = None) -> dict[str, Any]:
    db.flush()
    audit(db, correlation_id=request_id, event_type=event, entity_type=item.__class__.__name__, entity_id=item.id, actor_id=_actor(role), before=before, after=after if after is not None else projection(item))
    db.commit()
    db.refresh(item)
    return projection(item)


def _form(db: Session, item_id: str) -> MasterContentItem:
    item = db.get(MasterContentItem, item_id)
    if not item or item.content_type != "FORM":
        raise _error("V2_FORM_NOT_FOUND", 404)
    return item


def _current_version_id(item: MasterContentItem) -> str:
    if not item.current_document_version_id:
        raise _error("SOURCE_VERSION_MISSING")
    return item.current_document_version_id


def _version_matches_form(db: Session, item: MasterContentItem, version_id: str) -> None:
    version = db.get(DocumentVersion, version_id)
    if not version or version.document_id != item.document_id:
        raise _error("SOURCE_VERSION_FORM_MISMATCH")


def _date_match(row: Any, effective: date) -> bool:
    return (row.effective_from is None or row.effective_from <= effective) and (row.effective_to is None or row.effective_to >= effective)


def _wave_a_state(db: Session, item: MasterContentItem) -> dict[str, Any]:
    result = evaluate_wave_a_readiness(db, item, persist=False)
    profile = db.scalar(select(MasterContentGovernanceProfile).where(MasterContentGovernanceProfile.master_content_item_id == item.id))
    flags = list(db.scalars(select(MasterContentQualityFlag).where(MasterContentQualityFlag.master_content_item_id == item.id, MasterContentQualityFlag.status == "OPEN")).all())
    return {"readiness": result, "profile": profile, "quality_flags": flags}


def applicability_projection(row: MasterContentApplicability) -> dict[str, Any]:
    return projection(row)


def list_applicability(db: Session, item_id: str | None = None, *, effective_date: date | None = None) -> list[dict[str, Any]]:
    stmt = select(MasterContentApplicability).order_by(MasterContentApplicability.created_at.desc())
    if item_id:
        stmt = stmt.where(MasterContentApplicability.master_content_item_id == item_id)
    rows = list(db.scalars(stmt).all())
    if effective_date:
        rows = [row for row in rows if _date_match(row, effective_date)]
    return [applicability_projection(row) for row in rows]


def create_applicability(db: Session, payload: dict[str, Any], *, actor: str) -> MasterContentApplicability:
    item = _form(db, payload["master_content_item_id"])
    version_id = payload.get("source_document_version_id") or _current_version_id(item)
    _version_matches_form(db, item, version_id)
    for model, key, code in ((ExternalBody, "external_body_id", "EXTERNAL_BODY_NOT_FOUND"), (ServiceType, "service_type_id", "SERVICE_TYPE_NOT_FOUND")):
        if not db.get(model, payload.get(key)):
            raise _error(code, 404)
    if payload.get("jurisdiction_id") and not db.get(Jurisdiction, payload["jurisdiction_id"]):
        raise _error("JURISDICTION_NOT_FOUND", 404)
    if payload.get("lifecycle_phase_id") and not db.get(RegulatoryLifecyclePhase, payload["lifecycle_phase_id"]):
        raise _error("LIFECYCLE_PHASE_NOT_FOUND", 404)
    status = payload.get("status", "DRAFT").upper()
    if status not in LINEAGE_STATUSES:
        raise _error("APPLICABILITY_STATUS_INVALID", 422)
    if status == "ACTIVE":
        require_owner(actor)
    row = MasterContentApplicability(master_content_item_id=item.id, source_document_version_id=version_id, external_body_id=payload["external_body_id"], jurisdiction_id=payload.get("jurisdiction_id"), service_type_id=payload["service_type_id"], lifecycle_phase_id=payload.get("lifecycle_phase_id"), status="DRAFT", effective_from=_date(payload["effective_from"]) if payload.get("effective_from") else None, effective_to=_date(payload["effective_to"]) if payload.get("effective_to") else None, notes=payload.get("notes"), confirmed_by=actor if status == "ACTIVE" else None, confirmed_at=_now() if status == "ACTIVE" else None)
    db.add(row)
    db.flush()
    if status == "ACTIVE":
        row.status = "ACTIVE"
    return row


def transition_applicability(db: Session, row: MasterContentApplicability, status: str, *, actor: str, note: str | None = None) -> None:
    status = status.upper()
    if status not in LINEAGE_STATUSES:
        raise _error("APPLICABILITY_STATUS_INVALID", 422)
    if row.status in {"ACTIVE", "RETIRED", "SUPERSEDED"} and status not in {"NEEDS_REVALIDATION", "RETIRED", "SUPERSEDED"}:
        raise _error("APPLICABILITY_HISTORY_IMMUTABLE")
    if status == "ACTIVE":
        require_owner(actor)
        row.confirmed_by, row.confirmed_at = actor, _now()
    row.status = status
    if note:
        row.notes = note


def _lineage_row(db: Session, model: Any, row_id: str) -> Any:
    row = db.get(model, row_id)
    if not row:
        raise _error("SOURCE_LINEAGE_NOT_FOUND", 404)
    return row


def validate_source_section(db: Session, item_id: str, version_id: str, section_id: str | None) -> None:
    _version_matches_form(db, _form(db, item_id), version_id)
    if section_id:
        section = db.get(MasterContentSourceSection, section_id)
        if not section or section.master_content_item_id != item_id or section.document_version_id != version_id:
            raise _error("SOURCE_SECTION_VERSION_MISMATCH")


def _lineage_projection(row: Any) -> dict[str, Any]:
    return projection(row)


def list_policy_lineage(db: Session, item_id: str | None = None) -> list[dict[str, Any]]:
    stmt = select(RequirementPolicyLineage).order_by(RequirementPolicyLineage.created_at.desc())
    if item_id:
        stmt = stmt.where(RequirementPolicyLineage.master_content_item_id == item_id)
    return [_lineage_projection(row) for row in db.scalars(stmt).all()]


def list_technical_lineage(db: Session, item_id: str | None = None) -> list[dict[str, Any]]:
    stmt = select(TechnicalRuleLineage).order_by(TechnicalRuleLineage.created_at.desc())
    if item_id:
        stmt = stmt.where(TechnicalRuleLineage.master_content_item_id == item_id)
    return [_lineage_projection(row) for row in db.scalars(stmt).all()]


def create_policy_lineage(db: Session, payload: dict[str, Any], *, actor: str) -> RequirementPolicyLineage:
    policy = db.get(RequirementPolicyVersion, payload["policy_version_id"])
    if not policy:
        raise _error("REQUIREMENT_POLICY_NOT_FOUND", 404)
    validate_source_section(db, payload["master_content_item_id"], payload["document_version_id"], payload.get("source_section_id"))
    row = RequirementPolicyLineage(policy_version_id=policy.id, master_content_item_id=payload["master_content_item_id"], document_version_id=payload["document_version_id"], source_section_id=payload.get("source_section_id"), relation_type=payload.get("relation_type", "SOURCE_OF_POLICY"), source_role=payload.get("source_role", "PRIMARY"), governance_status="DRAFT", governance_note=payload.get("governance_note"))
    if row.source_role not in SOURCE_ROLES:
        raise _error("SOURCE_ROLE_INVALID", 422)
    db.add(row)
    db.flush()
    return row


def create_technical_lineage(db: Session, payload: dict[str, Any], *, actor: str) -> TechnicalRuleLineage:
    ruleset = db.get(TechnicalRuleSetVersion, payload.get("technical_rule_set_version_id"))
    if not ruleset:
        raise _error("TECHNICAL_RULE_SET_NOT_FOUND", 404)
    rule_id = payload.get("technical_rule_id")
    if not rule_id:
        raise _error("TECHNICAL_RULE_REQUIRED", 422)
    rule = db.get(TechnicalRule, rule_id)
    if not rule or rule.rule_set_version_id != ruleset.id:
        raise _error("TECHNICAL_RULE_RULESET_MISMATCH", 409)
    row = TechnicalRuleLineage(technical_rule_id=rule_id, master_content_item_id=payload["master_content_item_id"], document_version_id=payload["document_version_id"], source_section_id=payload.get("source_section_id"), relation_type=payload.get("relation_type", "SOURCE_OF_RULE"), source_role=payload.get("source_role", "PRIMARY"), governance_status="DRAFT", governance_note=payload.get("governance_note"))
    validate_source_section(db, row.master_content_item_id, row.document_version_id, row.source_section_id)
    if row.source_role not in SOURCE_ROLES:
        raise _error("SOURCE_ROLE_INVALID", 422)
    db.add(row)
    db.flush()
    return row


def transition_lineage(row: Any, status: str, *, actor: str, note: str | None = None) -> None:
    status = status.upper()
    if status not in LINEAGE_STATUSES:
        raise _error("LINEAGE_STATUS_INVALID", 422)
    if row.governance_status in {"ACTIVE", "RETIRED", "SUPERSEDED"} and status == "DRAFT":
        raise _error("LINEAGE_HISTORY_IMMUTABLE")
    row.governance_status = status
    if status == "ACTIVE":
        require_owner(actor)
        row.confirmed_by, row.confirmed_at = actor, _now()
    if note:
        row.governance_note = note


def _release_rules(db: Session, release_id: str) -> list[FormMappingRule]:
    return list(db.scalars(select(FormMappingRule).where(FormMappingRule.mapping_release_id == release_id).order_by(FormMappingRule.id)).all())


def release_checksum(db: Session, release: FormMappingRelease) -> str:
    rules = [projection(row) for row in _release_rules(db, release.id)]
    payload = {"profile_id": release.profile_id, "source_document_version_id": release.source_document_version_id, "semantic_contract_version": release.semantic_contract_version, "renderer_type": release.renderer_type, "renderer_version": release.renderer_version, "normalized_rendition_hash": release.normalized_rendition_hash, "rules": rules}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()


def _profile_release_defaults(profile: FormAutomationProfile, payload: dict[str, Any]) -> dict[str, Any]:
    return {"master_content_item_id": profile.master_content_item_id, "source_document_version_id": profile.source_document_version_id, "semantic_contract_version": profile.semantic_contract_version, "renderer_type": profile.renderer_type, "renderer_version": payload.get("renderer_version", "SYNTHETIC_RENDERER_1"), "normalized_rendition_ref": profile.working_rendition_ref}


def create_release(db: Session, profile: FormAutomationProfile, payload: dict[str, Any], *, actor: str) -> FormMappingRelease:
    if profile.source_version_state != "CURRENT":
        raise _error("MAPPING_NEEDS_REVALIDATION")
    item = _form(db, profile.master_content_item_id)
    if profile.source_document_version_id != _current_version_id(item):
        profile.source_version_state = "NEEDS_REVALIDATION"
        raise _error("MAPPING_SOURCE_MISMATCH")
    data = _profile_release_defaults(profile, payload)
    row = FormMappingRelease(profile_id=profile.id, version=payload["version"], status="DRAFT", mapping_json=payload.get("mapping_json") or {}, **data)
    db.add(row)
    db.flush()
    return row


def validate_release(db: Session, release: FormMappingRelease) -> dict[str, Any]:
    profile = db.get(FormAutomationProfile, release.profile_id)
    reasons: list[str] = []
    rules = _release_rules(db, release.id)
    if not profile:
        reasons.append("FORM_AUTOMATION_PROFILE_NOT_FOUND")
    else:
        item = _form(db, profile.master_content_item_id)
        if release.master_content_item_id != item.id:
            reasons.append("MAPPING_FORM_MISMATCH")
        if release.source_document_version_id != profile.source_document_version_id or release.source_document_version_id != item.current_document_version_id:
            reasons.append("MAPPING_SOURCE_MISMATCH")
        if profile.source_version_state != "CURRENT":
            reasons.append("MAPPING_NEEDS_REVALIDATION")
    if not rules:
        reasons.append("MAPPING_HAS_NO_RULES")
    keys = {row.semantic_key for row in db.scalars(select(SemanticKeyDefinition).where(SemanticKeyDefinition.status == "ACTIVE")).all()}
    for rule in rules:
        if rule.logical_field_key not in keys:
            reasons.append(f"SEMANTIC_KEY_NOT_FOUND:{rule.logical_field_key}")
        if rule.target_writer not in {"SYSTEM", "AMEC_USER", "HUMAN_SIGNER", "AUTHORITY_ONLY", "EXTERNAL_PARTY"}:
            reasons.append(f"WRITER_OWNERSHIP_INVALID:{rule.target_key}")
        if not rule.target_key:
            reasons.append("TARGET_IDENTITY_MISSING")
        if rule.transform_type == "REPEATING_GRID" and (rule.capacity is None or rule.capacity < 1):
            reasons.append(f"REPEATING_GRID_CAPACITY_MISSING:{rule.target_key}")
        if rule.transform_type == "CALCULATED_VALUE" and not rule.configuration_json.get("formula"):
            reasons.append(f"CALCULATED_VALUE_FORMULA_MISSING:{rule.target_key}")
    return {"valid": not reasons, "reasons": list(dict.fromkeys(reasons)), "mapping_checksum": release_checksum(db, release), "rule_count": len(rules)}


def transition_release(db: Session, release: FormMappingRelease, status: str, *, actor: str, request_id: str) -> dict[str, Any]:
    status = status.upper()
    if status not in RELEASE_STATUSES:
        raise _error("MAPPING_RELEASE_STATUS_INVALID", 422)
    before = projection(release)
    if status == "REVIEW":
        if release.status != "DRAFT":
            raise _error("MAPPING_RELEASE_TRANSITION_INVALID")
        result = validate_release(db, release)
        if not result["valid"]:
            raise _error("MAPPING_VALIDATION_FAILED", reasons=result["reasons"])
        release.mapping_checksum = result["mapping_checksum"]
        release.reviewed_by, release.reviewed_at = actor, _now()
    elif status == "APPROVED":
        if release.status != "REVIEW":
            raise _error("MAPPING_APPROVAL_REQUIRES_REVIEW")
        release.approved_by, release.approved_at = actor, _now()
    elif status == "RELEASED":
        if release.status != "APPROVED":
            raise _error("MAPPING_RELEASE_REQUIRES_APPROVAL")
        result = validate_release(db, release)
        if not result["valid"]:
            raise _error("MAPPING_VALIDATION_FAILED", reasons=result["reasons"])
        gates = list(db.scalars(select(FormMappingReleaseQAGate).where(FormMappingReleaseQAGate.mapping_release_id == release.id, FormMappingReleaseQAGate.required.is_(True))).all())
        passed = {gate.qa_type for gate in gates if db.get(FormQARun, gate.qa_run_id) and db.get(FormQARun, gate.qa_run_id).result == "PASS"}
        required = {"STRUCTURAL_MAPPING", "SYNTHETIC_FILL", "READ_BACK", "WRITER_OWNERSHIP"}
        if not required.issubset(passed):
            raise _error("QA_GATES_INCOMPLETE", required=sorted(required), passed=sorted(passed))
        release.mapping_checksum = result["mapping_checksum"]
        release.released_by, release.released_at = actor, _now()
        profile = db.get(FormAutomationProfile, release.profile_id)
        if profile:
            profile.automation_status = "ACTIVE"
    elif status == "RETIRED":
        if release.status not in {"RELEASED", "APPROVED"}:
            raise _error("MAPPING_RETIREMENT_INVALID")
        release.retired_by, release.retired_at = actor, _now()
    elif status == "NEEDS_REVALIDATION":
        if release.status == "RELEASED":
            release.invalidation_reason = "Source or governance changed; revalidation required."
            profile = db.get(FormAutomationProfile, release.profile_id)
            if profile:
                profile.automation_status = "NEEDS_REVALIDATION"
    elif status in {"SUPERSEDED"} and release.status not in {"RELEASED", "APPROVED"}:
        raise _error("MAPPING_SUPERSESSION_INVALID")
    release.status = status
    return _commit(db, release, request_id=request_id, event=f"DASHBOARD_V2_MAPPING_{status}", role=actor, before=before)


def evaluate_automated_readiness(db: Session, profile: FormAutomationProfile, *, actor: str, persist: bool = True) -> dict[str, Any]:
    item = _form(db, profile.master_content_item_id)
    source_version = _current_version_id(item)
    reasons: list[str] = []
    evidence: dict[str, Any] = {"master_content_item_id": item.id, "source_document_version_id": source_version, "profile_id": profile.id}
    wave_a = _wave_a_state(db, item)
    wave_a_readiness = wave_a["readiness"]
    evidence["wave_a_state"] = wave_a_readiness["state"]
    if item.status != "ACTIVE": reasons.append("SOURCE_NOT_CURRENT")
    if profile.source_document_version_id != source_version:
        reasons.append("MAPPING_SOURCE_MISMATCH")
        profile.source_version_state = "NEEDS_REVALIDATION"
    if profile.source_version_state != "CURRENT": reasons.append("MAPPING_NEEDS_REVALIDATION")
    governance_profile = wave_a["profile"]
    if governance_profile and governance_profile.restricted_reference_sample: reasons.append("RESTRICTED_SOURCE")
    if governance_profile and governance_profile.content_ownership_class in {"EXTERNAL_OFFICIAL"} and governance_profile.currentness_status != "VERIFIED_CURRENT": reasons.append("SOURCE_NOT_CURRENT")
    if any(flag.severity == "BLOCKING" for flag in wave_a["quality_flags"]): reasons.append("QUALITY_BLOCKED")
    active_applicability = list(db.scalars(select(MasterContentApplicability).where(MasterContentApplicability.master_content_item_id == item.id, MasterContentApplicability.source_document_version_id == source_version, MasterContentApplicability.status == "ACTIVE")).all())
    if not active_applicability: reasons.append("NO_ACTIVE_APPLICABILITY")
    evidence["applicability_ids"] = [row.id for row in active_applicability]
    release = db.scalar(select(FormMappingRelease).where(FormMappingRelease.profile_id == profile.id, FormMappingRelease.status == "RELEASED").order_by(FormMappingRelease.released_at.desc()))
    if not release: reasons.append("MAPPING_NOT_RELEASED")
    else:
        evidence["mapping_release_id"] = release.id
        if release.source_document_version_id != source_version: reasons.append("MAPPING_SOURCE_MISMATCH")
        validation = validate_release(db, release)
        if validation["mapping_checksum"] != release.mapping_checksum: reasons.append("MAPPING_CHECKSUM_INVALID")
        if not validation["valid"]: reasons.extend(validation["reasons"])
        gates = list(db.scalars(select(FormMappingReleaseQAGate).where(FormMappingReleaseQAGate.mapping_release_id == release.id, FormMappingReleaseQAGate.required.is_(True))).all())
        passed = {gate.qa_type for gate in gates if db.get(FormQARun, gate.qa_run_id) and db.get(FormQARun, gate.qa_run_id).result == "PASS"}
        required_qa = {"STRUCTURAL_MAPPING", "SYNTHETIC_FILL", "READ_BACK", "WRITER_OWNERSHIP"}
        if governance_profile and governance_profile.language_profile in {"AR", "AR_EN_BILINGUAL"}: required_qa.add("ARABIC_RTL")
        evidence["qa_passed"] = sorted(passed)
        evidence["qa_required"] = sorted(required_qa)
        reasons.extend(f"QA_FAILED:{qa_type}" for qa_type in sorted(required_qa - passed))
    if not reasons and wave_a_readiness["state"] not in {"MANUAL_USE_READY", "BLOCKED"}:
        reasons.append("WAVE_A_SOURCE_NOT_ELIGIBLE")
    state = "AUTOMATED_USE_READY" if not reasons else ("NEEDS_REVALIDATION" if any(code in " ".join(reasons) for code in ("MAPPING_SOURCE_MISMATCH", "MAPPING_NEEDS_REVALIDATION", "SOURCE_NOT_CURRENT")) else "BLOCKED")
    result = {"state": state, "blocking_reasons": list(dict.fromkeys(reasons)), "evidence": evidence, "profile_id": profile.id, "source_document_version_id": source_version, "mapping_release_id": release.id if release else None, "evaluated_at": _now().isoformat()}
    if persist:
        assessment = AutomationReadinessAssessment(profile_id=profile.id, master_content_item_id=item.id, source_document_version_id=source_version, mapping_release_id=release.id if release else None, state=state, blocking_reasons=result["blocking_reasons"], evidence_json=evidence, evaluated_by=actor)
        db.add(assessment)
        db.flush()
        audit(db, correlation_id="dashboard-v2-readiness", event_type="DASHBOARD_V2_AUTOMATION_READINESS_EVALUATED", entity_type="AutomationReadinessAssessment", entity_id=assessment.id, actor_id=actor, after=result)
        db.commit()
    return result


def resolve_automation(db: Session, *, external_body_id: str, jurisdiction_id: str | None, service_type_id: str, lifecycle_phase_id: str | None, effective_date: date, actor: str) -> dict[str, Any]:
    stmt = select(MasterContentApplicability).where(MasterContentApplicability.external_body_id == external_body_id, MasterContentApplicability.service_type_id == service_type_id, MasterContentApplicability.status == "ACTIVE", MasterContentApplicability.jurisdiction_id == jurisdiction_id if jurisdiction_id else MasterContentApplicability.jurisdiction_id.is_(None), MasterContentApplicability.lifecycle_phase_id == lifecycle_phase_id if lifecycle_phase_id else MasterContentApplicability.lifecycle_phase_id.is_(None))
    rows = [row for row in db.scalars(stmt).all() if _date_match(row, effective_date)]
    candidates: list[dict[str, Any]] = []
    for row in rows:
        item = db.get(MasterContentItem, row.master_content_item_id)
        profile = db.scalar(select(FormAutomationProfile).where(FormAutomationProfile.master_content_item_id == item.id)) if item else None
        if not item or item.status != "ACTIVE" or item.needs_review or not profile: continue
        result = evaluate_automated_readiness(db, profile, actor=actor, persist=False)
        if result["state"] == "AUTOMATED_USE_READY":
            release = db.get(FormMappingRelease, result["mapping_release_id"])
            candidates.append({"applicability": projection(row), "master_content": {"id": item.id, "ref": item.ref, "title": item.title}, "profile": projection(profile), "mapping_release": projection(release), "readiness": result})
    if len(candidates) != 1:
        raise _error("NO_ELIGIBLE_AUTOMATION" if not candidates else "AMBIGUOUS_AUTOMATION", 409, candidate_count=len(candidates))
    return candidates[0]
