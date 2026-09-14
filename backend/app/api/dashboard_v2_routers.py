"""Dashboard V2-only Waves B+C governance facade.

This router references canonical shared-domain records and never changes the
legacy /dashboard API contract.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..db import get_db
from ..models import (
    ExternalBody,
    AutomationReadinessAssessment,
    FormAutomationProfile,
    FormMappingRelease,
    FormMappingRule,
    FormQARun,
    Jurisdiction,
    MasterContentApplicability,
    MasterContentItem,
    MasterContentSourceSection,
    RequirementPolicyLineage,
    RequirementPolicyVersion,
    RegulatoryLifecyclePhase,
    ServiceType,
    TechnicalRuleLineage,
    TechnicalRuleSetVersion,
    Role,
)
from ..services.dashboard_v2_governance import (
    LINEAGE_STATUSES,
    RELEASE_STATUSES,
    SOURCE_ROLES,
    _actor,
    _commit,
    _date,
    _error,
    _form,
    applicability_projection,
    create_applicability,
    create_policy_lineage,
    create_release,
    create_technical_lineage,
    evaluate_automated_readiness,
    list_applicability,
    list_policy_lineage,
    list_technical_lineage,
    require_owner,
    require_reader,
    resolve_automation,
    transition_applicability,
    transition_lineage,
    transition_release,
    validate_release,
)
from ..services.master_content import canonical_master_content_read
from ..services.shared_domains import projection, projections


router = APIRouter(prefix="/api/dashboard-v2", tags=["dashboard-v2-governance"])


def _correlation(request: Request) -> str:
    return getattr(request.state, "correlation_id", "dashboard-v2")


@router.get("/catalogs")
def catalogs(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_reader(role)
    return {
        "external_bodies": projections(list(db.scalars(select(ExternalBody).where(ExternalBody.status != "RETIRED").order_by(ExternalBody.name_en)).all())),
        "jurisdictions": projections(list(db.scalars(select(Jurisdiction).where(Jurisdiction.status != "RETIRED").order_by(Jurisdiction.name_en)).all())),
        "service_types": projections(list(db.scalars(select(ServiceType).where(ServiceType.status != "RETIRED").order_by(ServiceType.name_en)).all())),
        "lifecycle_phases": projections(list(db.scalars(select(RegulatoryLifecyclePhase).where(RegulatoryLifecyclePhase.status != "RETIRED").order_by(RegulatoryLifecyclePhase.sort_order)).all())),
        "release_statuses": sorted(RELEASE_STATUSES),
        "lineage_statuses": sorted(LINEAGE_STATUSES),
        "source_roles": sorted(SOURCE_ROLES),
        "qa_types": ["STRUCTURAL_MAPPING", "SYNTHETIC_FILL", "READ_BACK", "VISUAL", "ARABIC_RTL", "BILINGUAL", "REPEATING_GRID", "SIGNATURE_ZONE", "WRITER_OWNERSHIP", "NORMALIZED_RENDITION"],
    }


@router.get("/forms")
def list_v2_forms(q: str = "", readiness: str | None = None, wave_a_readiness: str | None = None, automation_readiness: str | None = None, category_id: str | None = None, category_label: str | None = None, owner_status: str | None = None, module: str | None = None, ownership: str | None = None, artifact_kind: str | None = None, publisher: str | None = None, currentness: str | None = None, quality_state: str | None = None, restricted_sample: bool | None = None, language: str | None = None, external_body_id: str | None = None, jurisdiction_id: str | None = None, service_type_id: str | None = None, lifecycle_phase_id: str | None = None, applicability_status: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_reader(role)
    return canonical_master_content_read(db, role=role, content_type="FORM", q=q, category_id=category_id, category_label=category_label, owner_status=owner_status, module=module, ownership=ownership, artifact_kind=artifact_kind, publisher=publisher, currentness=currentness, wave_a_readiness=wave_a_readiness, automation_readiness=automation_readiness or readiness, quality_state=quality_state, restricted_sample=restricted_sample, language=language, external_body_id=external_body_id, jurisdiction_id=jurisdiction_id, service_type_id=service_type_id, lifecycle_phase_id=lifecycle_phase_id, applicability_status=applicability_status, include_governance=True)


@router.get("/forms/{item_id}")
def get_v2_form(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_reader(role)
    rows = canonical_master_content_read(db, role=role, content_type="FORM", item_id=item_id, include_archived=True, include_history=True, include_governance=True)
    if not rows:
        _form(db, item_id)
        raise HTTPException(status_code=403, detail={"code": "MASTER_CONTENT_NOT_APPLICABLE"})
    return rows[0]


@router.get("/forms/{item_id}/applicability")
def get_applicability(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_reader(role)
    _form(db, item_id)
    return list_applicability(db, item_id)


@router.post("/applicability")
def post_applicability(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_owner(role)
    row = create_applicability(db, payload, actor=_actor(role))
    return _commit(db, row, request_id=_correlation(request), event="DASHBOARD_V2_APPLICABILITY_CREATED", role=role)


@router.patch("/applicability/{applicability_id}")
def patch_applicability(applicability_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_owner(role)
    row = db.get(MasterContentApplicability, applicability_id)
    if not row:
        raise _error("APPLICABILITY_NOT_FOUND", 404)
    before = projection(row)
    if "status" in payload:
        transition_applicability(db, row, payload["status"], actor=_actor(role), note=payload.get("notes"))
    if "notes" in payload:
        row.notes = payload["notes"]
    return _commit(db, row, request_id=_correlation(request), event="DASHBOARD_V2_APPLICABILITY_CHANGED", role=role, before=before)


@router.get("/forms/{item_id}/policy-lineage")
def get_policy_lineage(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_reader(role)
    _form(db, item_id)
    return list_policy_lineage(db, item_id)


@router.post("/policy-lineage")
def post_policy_lineage(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_owner(role)
    row = create_policy_lineage(db, payload, actor=_actor(role))
    return _commit(db, row, request_id=_correlation(request), event="DASHBOARD_V2_POLICY_SOURCE_LINKED", role=role)


@router.patch("/policy-lineage/{lineage_id}")
def patch_policy_lineage(lineage_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_owner(role)
    row = db.get(RequirementPolicyLineage, lineage_id)
    if not row:
        raise _error("SOURCE_LINEAGE_NOT_FOUND", 404)
    before = projection(row)
    transition_lineage(row, payload.get("governance_status", row.governance_status), actor=_actor(role), note=payload.get("governance_note"))
    return _commit(db, row, request_id=_correlation(request), event="DASHBOARD_V2_POLICY_SOURCE_GOVERNANCE_CHANGED", role=role, before=before)


@router.get("/forms/{item_id}/technical-lineage")
def get_technical_lineage(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_reader(role)
    _form(db, item_id)
    return list_technical_lineage(db, item_id)


@router.post("/technical-lineage")
def post_technical_lineage(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_owner(role)
    row = create_technical_lineage(db, payload, actor=_actor(role))
    return _commit(db, row, request_id=_correlation(request), event="DASHBOARD_V2_TECHNICAL_SOURCE_LINKED", role=role)


@router.patch("/technical-lineage/{lineage_id}")
def patch_technical_lineage(lineage_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_owner(role)
    row = db.get(TechnicalRuleLineage, lineage_id)
    if not row:
        raise _error("SOURCE_LINEAGE_NOT_FOUND", 404)
    before = projection(row)
    transition_lineage(row, payload.get("governance_status", row.governance_status), actor=_actor(role), note=payload.get("governance_note"))
    return _commit(db, row, request_id=_correlation(request), event="DASHBOARD_V2_TECHNICAL_SOURCE_GOVERNANCE_CHANGED", role=role, before=before)


@router.get("/resolve-source")
def resolve_source(external_body_id: str, service_type_id: str, jurisdiction_id: str | None = None, lifecycle_phase_id: str | None = None, effective_date: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_reader(role)
    from ..services.dashboard_v2_governance import _date_match, _wave_a_state
    rows = [row for row in db.scalars(select(MasterContentApplicability).where(and_(MasterContentApplicability.external_body_id == external_body_id, MasterContentApplicability.service_type_id == service_type_id, MasterContentApplicability.status == "ACTIVE", MasterContentApplicability.jurisdiction_id == jurisdiction_id if jurisdiction_id else MasterContentApplicability.jurisdiction_id.is_(None), MasterContentApplicability.lifecycle_phase_id == lifecycle_phase_id if lifecycle_phase_id else MasterContentApplicability.lifecycle_phase_id.is_(None)))).all() if _date_match(row, _date(effective_date))]
    candidates = []
    for row in rows:
        item = db.get(MasterContentItem, row.master_content_item_id)
        if not item or item.current_document_version_id != row.source_document_version_id:
            continue
        wave_a = _wave_a_state(db, item)
        if wave_a["readiness"]["state"] in {"BLOCKED", "REFERENCE_ONLY", "SUPERSEDED"}:
            continue
        candidates.append({"applicability": applicability_projection(row), "master_content": {"id": item.id, "ref": item.ref, "title": item.title, "source_document_version_id": item.current_document_version_id}, "requirement_policy_lineage": list_policy_lineage(db, item.id), "technical_rule_lineage": list_technical_lineage(db, item.id), "wave_a_readiness": wave_a["readiness"]})
    if len(candidates) != 1:
        raise _error("NO_ELIGIBLE_GOVERNED_SOURCE" if not candidates else "AMBIGUOUS_GOVERNED_SOURCE", 409, candidate_count=len(candidates))
    return candidates[0]


@router.get("/forms/{item_id}/automation")
def get_automation(item_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_reader(role)
    _form(db, item_id)
    profiles = list(db.scalars(select(FormAutomationProfile).where(FormAutomationProfile.master_content_item_id == item_id)).all())
    result = []
    for profile in profiles:
        releases = list(db.scalars(select(FormMappingRelease).where(FormMappingRelease.profile_id == profile.id).order_by(FormMappingRelease.created_at.desc())).all())
        result.append({"profile": projection(profile), "releases": [projection(release) for release in releases], "readiness": evaluate_automated_readiness(db, profile, actor=_actor(role), persist=False)})
    return result


@router.post("/forms/{item_id}/automation-profile")
def create_v2_profile(item_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_owner(role)
    item = _form(db, item_id)
    source_id = payload.get("source_document_version_id") or item.current_document_version_id
    if source_id != item.current_document_version_id:
        raise _error("PROFILE_SOURCE_VERSION_NOT_CURRENT")
    if db.scalar(select(FormAutomationProfile).where(FormAutomationProfile.master_content_item_id == item.id)):
        raise _error("FORM_AUTOMATION_PROFILE_ALREADY_EXISTS")
    profile = FormAutomationProfile(master_content_item_id=item.id, source_document_version_id=source_id, renderer_type=payload.get("renderer_type", "SYNTHETIC_JSON"), semantic_contract_version=payload.get("semantic_contract_version", "1.0"), working_rendition_ref=payload.get("working_rendition_ref"), writer_policy_json=payload.get("writer_policy_json") or {}, source_version_state="CURRENT", automation_status="DRAFT", managed_by=_actor(role))
    db.add(profile)
    return _commit(db, profile, request_id=_correlation(request), event="DASHBOARD_V2_AUTOMATION_PROFILE_CREATED", role=role)


@router.get("/mapping-releases/{release_id}")
def get_release(release_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_reader(role)
    release = db.get(FormMappingRelease, release_id)
    if not release:
        raise _error("MAPPING_RELEASE_NOT_FOUND", 404)
    gates = list(db.scalars(select(FormQARun).where(FormQARun.mapping_release_id == release.id).order_by(FormQARun.created_at.desc())).all())
    return {"release": projection(release), "rules": projections(list(db.scalars(select(FormMappingRule).where(FormMappingRule.mapping_release_id == release.id)).all())), "qa_runs": projections(gates), "validation": validate_release(db, release)}


@router.post("/forms/{item_id}/mapping-releases")
def post_release(item_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_owner(role)
    item = _form(db, item_id)
    profile = db.scalar(select(FormAutomationProfile).where(FormAutomationProfile.master_content_item_id == item.id))
    if not profile:
        raise _error("FORM_AUTOMATION_PROFILE_NOT_FOUND", 404)
    release = create_release(db, profile, payload, actor=_actor(role))
    return _commit(db, release, request_id=_correlation(request), event="DASHBOARD_V2_MAPPING_DRAFT_CREATED", role=role)


@router.post("/mapping-releases/{release_id}/rules")
def post_release_rule(release_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_owner(role)
    release = db.get(FormMappingRelease, release_id)
    if not release:
        raise _error("MAPPING_RELEASE_NOT_FOUND", 404)
    if release.status != "DRAFT":
        raise _error("MAPPING_RELEASE_IMMUTABLE")
    if payload.get("target_writer") not in {"SYSTEM", "AMEC_USER", "HUMAN_SIGNER", "AUTHORITY_ONLY", "EXTERNAL_PARTY"}:
        raise _error("WRITER_OWNERSHIP_INVALID", 422)
    rule = FormMappingRule(mapping_release_id=release.id, logical_field_key=payload["logical_field_key"], target_key=payload["target_key"], transform_type=payload.get("transform_type", "SCALAR"), target_writer=payload["target_writer"], page_number=payload.get("page_number"), rect_json=payload.get("rect_json") or {}, capacity=payload.get("capacity"), configuration_json=payload.get("configuration_json") or {})
    db.add(rule)
    return _commit(db, rule, request_id=_correlation(request), event="DASHBOARD_V2_MAPPING_RULE_CREATED", role=role)


@router.post("/mapping-releases/{release_id}/validate")
def validate_mapping(release_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_reader(role)
    release = db.get(FormMappingRelease, release_id)
    if not release:
        raise _error("MAPPING_RELEASE_NOT_FOUND", 404)
    return validate_release(db, release)


@router.post("/mapping-releases/{release_id}/preview")
def preview_mapping(release_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    """Render a synthetic preview before release; never performs external writes."""
    require_owner(role)
    release = db.get(FormMappingRelease, release_id)
    if not release:
        raise _error("MAPPING_RELEASE_NOT_FOUND", 404)
    profile = db.get(FormAutomationProfile, release.profile_id)
    if not profile:
        raise _error("FORM_AUTOMATION_PROFILE_NOT_FOUND", 404)
    from ..models import FormInstance
    from ..services.shared_domains import render_instance
    item = _form(db, profile.master_content_item_id)
    if release.source_document_version_id != item.current_document_version_id:
        raise _error("MAPPING_SOURCE_MISMATCH")
    instance = FormInstance(master_content_item_id=item.id, source_document_version_id=release.source_document_version_id, profile_id=profile.id, mapping_release_id=release.id, context_type=payload.get("context_type", "SYNTHETIC_PREVIEW"), context_id=payload.get("context_id", "SYNTHETIC"), resolved_values=payload.get("resolved_values") or {}, resolved_assertion_ids=[], status="DRAFT", created_by=_actor(role))
    db.add(instance)
    db.flush()
    try:
        result = render_instance(db, instance, actor_id=_actor(role), correlation_id=_correlation(request))
        db.commit()
        return {"preview": True, **result}
    except Exception:
        db.rollback()
        raise


@router.post("/mapping-releases/{release_id}/{status}")
def transition_mapping(release_id: str, status: str, request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_owner(role)
    release = db.get(FormMappingRelease, release_id)
    if not release:
        raise _error("MAPPING_RELEASE_NOT_FOUND", 404)
    return transition_release(db, release, status, actor=_actor(role), request_id=_correlation(request))


@router.post("/profiles/{profile_id}/readiness/evaluate")
def evaluate_readiness(profile_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_reader(role)
    profile = db.get(FormAutomationProfile, profile_id)
    if not profile:
        raise _error("FORM_AUTOMATION_PROFILE_NOT_FOUND", 404)
    result = evaluate_automated_readiness(db, profile, actor=_actor(role), persist=True)
    return result


@router.get("/profiles/{profile_id}/readiness/history")
def readiness_history(profile_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_reader(role)
    rows = list(db.scalars(select(AutomationReadinessAssessment).where(AutomationReadinessAssessment.profile_id == profile_id).order_by(AutomationReadinessAssessment.evaluated_at.desc())).all())
    return projections(rows)


@router.get("/resolve-automation")
def resolve_automation_package(external_body_id: str, service_type_id: str, jurisdiction_id: str | None = None, lifecycle_phase_id: str | None = None, effective_date: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_reader(role)
    return resolve_automation(db, external_body_id=external_body_id, jurisdiction_id=jurisdiction_id, service_type_id=service_type_id, lifecycle_phase_id=lifecycle_phase_id, effective_date=_date(effective_date), actor=_actor(role))
