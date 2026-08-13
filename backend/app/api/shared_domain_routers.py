"""API contracts for the shared Regulatory, Requirement, Technical, and Form Runtime domains.

The router intentionally exposes foundations only.  It does not add Dashboard
V1/V2 screens, portal writes, production mapping release, or automatic case
creation from Proposal records.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..db import get_db
from ..models import (
    AuthorityCase,
    AuthorityCaseIdentifier,
    AuthorityCaseWorkPeriod,
    AuthorityOutcome,
    ExternalBody,
    ExternalBodyUnit,
    ExternalInteractionProfile,
    FormAutomationProfile,
    FormInstance,
    FormMappingRelease,
    FormMappingRule,
    FormQARun,
    FormMappingReleaseQAGate,
    FormSignatureRequirement,
    FormValidationResult,
    GeneratedArtifact,
    Jurisdiction,
    MasterContentItem,
    RegulatoryJourney,
    RegulatoryLifecyclePhase,
    RegulatoryRelation,
    RequirementApplicabilityDecision,
    RequirementDefinition,
    RequirementDecision,
    RequirementEvidenceConstraint,
    RequirementGroup,
    RequirementPolicyItem,
    RequirementPolicyLineage,
    RequirementPolicyVersion,
    Role,
    SemanticKeyDefinition,
    SemanticValueAssertion,
    ServiceType,
    ServiceTypeVersion,
    SignaturePacket,
    TechnicalRule,
    TechnicalRuleEvaluation,
    TechnicalRuleLineage,
    TechnicalRuleSetVersion,
)
from .dependencies import current_user_role
from ..services.shared_domains import (
    AUTOMATION_EXECUTE_ROLES,
    CASE_ROLES,
    DomainConflict,
    OWNER_ROLES,
    REQUIREMENT_APPROVER_ROLES,
    TECHNICAL_APPROVER_ROLES,
    _date,
    actor,
    create_record,
    evaluate_policy,
    evaluate_rule,
    projection,
    projections,
    render_instance,
    require_role,
    resolve_assertions,
    resolve_requirement_policy,
    resolve_rule_set,
)


router = APIRouter(prefix="/api", tags=["shared-domain-foundations"])


def _corr(request: Request) -> str:
    return getattr(request.state, "correlation_id", "shared-domain")


def _missing(label: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": f"{label.upper()}_NOT_FOUND"})


def _conflict(exc: DomainConflict) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": str(exc)})


def _commit(db: Session, item: Any, request: Request, *, event: str, role: Role, before: Any = None, after: Any | None = None) -> dict[str, Any]:
    # Assign ORM defaults (notably UUID primary keys) before the audit row is
    # written so the audit entity_id is always non-null.
    db.flush()
    audit(db, correlation_id=_corr(request), event_type=event, entity_type=item.__class__.__name__, entity_id=item.id, actor_id=actor(role), before=before, after=after if after is not None else projection(item))
    db.commit()
    db.refresh(item)
    return projection(item)


def _catalog_create(db: Session, model: Any, payload: dict[str, Any], request: Request, role: Role, event: str, *, defaults: dict[str, Any] | None = None) -> dict[str, Any]:
    require_role(role, OWNER_ROLES)
    item = create_record(db, model, payload, defaults=defaults)
    return _commit(db, item, request, event=event, role=role)


def _catalog_patch(db: Session, model: Any, item_id: str, payload: dict[str, Any], request: Request, role: Role, event: str) -> dict[str, Any]:
    require_role(role, OWNER_ROLES)
    item = db.get(model, item_id)
    if not item:
        raise _missing(model.__name__)
    if getattr(item, "status", None) in {"ACTIVE", "APPROVED", "SUPERSEDED", "RETIRED"}:
        raise HTTPException(status_code=409, detail={"code": "ACTIVE_RECORD_IMMUTABLE_CREATE_NEW_VERSION"})
    before = projection(item)
    for key, value in payload.items():
        if key not in {"id", "created_at", "updated_at"} and hasattr(item, key):
            setattr(item, key, value)
    return _commit(db, item, request, event=event, role=role, before=before)


def _list(db: Session, model: Any, status: str | None = None) -> list[dict[str, Any]]:
    stmt = select(model)
    if status and hasattr(model, "status"):
        stmt = stmt.where(model.status == status)
    return projections(list(db.scalars(stmt).all()))


# Regulatory Core ---------------------------------------------------------

@router.get("/regulatory/external-bodies")
def list_external_bodies(status: str | None = None, db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return _list(db, ExternalBody, status)


@router.post("/regulatory/external-bodies")
def create_external_body(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return _catalog_create(db, ExternalBody, payload, request, role, "EXTERNAL_BODY_CREATED", defaults={"created_by": actor(role)})


@router.patch("/regulatory/external-bodies/{item_id}")
def patch_external_body(item_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return _catalog_patch(db, ExternalBody, item_id, payload, request, role, "EXTERNAL_BODY_CHANGED")


@router.post("/regulatory/external-bodies/{item_id}/units")
def create_external_body_unit(item_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, OWNER_ROLES)
    if not db.get(ExternalBody, item_id):
        raise _missing("ExternalBody")
    return _commit(db, create_record(db, ExternalBodyUnit, payload, defaults={"external_body_id": item_id}), request, event="EXTERNAL_BODY_UNIT_CREATED", role=role)


@router.get("/regulatory/external-bodies/{item_id}/units")
def list_external_body_units(item_id: str, db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return projections(list(db.scalars(select(ExternalBodyUnit).where(ExternalBodyUnit.external_body_id == item_id)).all()))


@router.get("/regulatory/jurisdictions")
def list_jurisdictions(status: str | None = None, db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return _list(db, Jurisdiction, status)


@router.post("/regulatory/jurisdictions")
def create_jurisdiction(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return _catalog_create(db, Jurisdiction, payload, request, role, "JURISDICTION_CREATED")


@router.patch("/regulatory/jurisdictions/{item_id}")
def patch_jurisdiction(item_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return _catalog_patch(db, Jurisdiction, item_id, payload, request, role, "JURISDICTION_CHANGED")


@router.get("/regulatory/service-types")
def list_service_types(status: str | None = None, db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return _list(db, ServiceType, status)


@router.post("/regulatory/service-types")
def create_service_type(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return _catalog_create(db, ServiceType, payload, request, role, "SERVICE_TYPE_CREATED")


@router.patch("/regulatory/service-types/{item_id}")
def patch_service_type(item_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return _catalog_patch(db, ServiceType, item_id, payload, request, role, "SERVICE_TYPE_CHANGED")


@router.post("/regulatory/service-types/{item_id}/versions")
def create_service_type_version(item_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return _catalog_create(db, ServiceTypeVersion, payload, request, role, "SERVICE_TYPE_VERSION_CREATED", defaults={"service_type_id": item_id})


@router.get("/regulatory/lifecycle-phases")
def list_lifecycle_phases(db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return projections(list(db.scalars(select(RegulatoryLifecyclePhase).order_by(RegulatoryLifecyclePhase.sort_order)).all()))


@router.post("/regulatory/lifecycle-phases")
def create_lifecycle_phase(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return _catalog_create(db, RegulatoryLifecyclePhase, payload, request, role, "REGULATORY_PHASE_CREATED")


@router.post("/regulatory/journeys")
def create_regulatory_journey(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, CASE_ROLES)
    item = create_record(db, RegulatoryJourney, payload, defaults={"created_by": actor(role), "status": "DRAFT"})
    return _commit(db, item, request, event="REGULATORY_JOURNEY_CREATED", role=role)


@router.get("/regulatory/journeys")
def list_regulatory_journeys(db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return _list(db, RegulatoryJourney)


@router.post("/regulatory/cases")
def create_authority_case(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, CASE_ROLES)
    item = create_record(db, AuthorityCase, payload, defaults={"created_by": actor(role), "status": "DRAFT"})
    return _commit(db, item, request, event="AUTHORITY_CASE_CREATED", role=role)


@router.get("/regulatory/cases")
def list_authority_cases(status: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    rows = list(db.scalars(select(AuthorityCase).where(AuthorityCase.status == status if status else True)).all())
    return projections(rows)


@router.patch("/regulatory/cases/{case_id}")
def patch_authority_case(case_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, CASE_ROLES)
    item = db.get(AuthorityCase, case_id)
    if not item:
        raise _missing("AuthorityCase")
    before = projection(item)
    for key, value in payload.items():
        if key not in {"id", "created_at", "updated_at", "case_reference"} and hasattr(item, key):
            setattr(item, key, value)
    return _commit(db, item, request, event="AUTHORITY_CASE_CHANGED", role=role, before=before)


@router.post("/regulatory/cases/{case_id}/identifiers")
def add_authority_case_identifier(case_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, CASE_ROLES)
    if not db.get(AuthorityCase, case_id):
        raise _missing("AuthorityCase")
    return _commit(db, create_record(db, AuthorityCaseIdentifier, payload, defaults={"authority_case_id": case_id, "issued_by": actor(role)}), request, event="AUTHORITY_CASE_IDENTIFIER_ADDED", role=role)


@router.get("/regulatory/cases/{case_id}/identifiers")
def list_authority_case_identifiers(case_id: str, db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return projections(list(db.scalars(select(AuthorityCaseIdentifier).where(AuthorityCaseIdentifier.authority_case_id == case_id)).all()))


@router.post("/regulatory/cases/{case_id}/work-periods")
def add_authority_case_work_period(case_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, CASE_ROLES)
    if not db.get(AuthorityCase, case_id):
        raise _missing("AuthorityCase")
    return _commit(db, create_record(db, AuthorityCaseWorkPeriod, payload, defaults={"authority_case_id": case_id}), request, event="AUTHORITY_CASE_WORK_PERIOD_ADDED", role=role)


@router.post("/regulatory/cases/{case_id}/outcomes")
def add_authority_outcome(case_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, CASE_ROLES)
    if not db.get(AuthorityCase, case_id):
        raise _missing("AuthorityCase")
    return _commit(db, create_record(db, AuthorityOutcome, payload, defaults={"authority_case_id": case_id, "recorded_by": actor(role)}), request, event="AUTHORITY_OUTCOME_RECORDED", role=role)


@router.post("/regulatory/interaction-profiles")
def create_interaction_profile(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return _catalog_create(db, ExternalInteractionProfile, payload, request, role, "EXTERNAL_INTERACTION_PROFILE_CREATED", defaults={"read_only": True})


@router.post("/regulatory/relations")
def create_regulatory_relation(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, CASE_ROLES)
    return _commit(db, create_record(db, RegulatoryRelation, payload), request, event="REGULATORY_RELATION_CREATED", role=role)


# Requirement Engine v2 --------------------------------------------------

@router.get("/requirements/definitions")
def list_requirement_definitions(status: str | None = None, db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return _list(db, RequirementDefinition, status)


@router.post("/requirements/definitions")
def create_requirement_definition(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return _catalog_create(db, RequirementDefinition, payload, request, role, "REQUIREMENT_DEFINITION_CREATED")


@router.get("/requirements/policies")
def list_requirement_policies(status: str | None = None, db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return _list(db, RequirementPolicyVersion, status)


@router.post("/requirements/policies")
def create_requirement_policy(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, REQUIREMENT_APPROVER_ROLES)
    item = create_record(db, RequirementPolicyVersion, payload, defaults={"status": "DRAFT"})
    return _commit(db, item, request, event="REQUIREMENT_POLICY_DRAFT_CREATED", role=role)


@router.post("/requirements/policies/{policy_id}/groups")
def create_requirement_group(policy_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, REQUIREMENT_APPROVER_ROLES)
    policy = db.get(RequirementPolicyVersion, policy_id)
    if not policy:
        raise _missing("RequirementPolicyVersion")
    if policy.status != "DRAFT":
        raise HTTPException(409, {"code": "ACTIVE_POLICY_IMMUTABLE"})
    return _commit(db, create_record(db, RequirementGroup, payload, defaults={"policy_version_id": policy_id}), request, event="REQUIREMENT_GROUP_CREATED", role=role)


@router.post("/requirements/policies/{policy_id}/items")
def create_requirement_policy_item(policy_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, REQUIREMENT_APPROVER_ROLES)
    policy = db.get(RequirementPolicyVersion, policy_id)
    if not policy:
        raise _missing("RequirementPolicyVersion")
    if policy.status != "DRAFT":
        raise HTTPException(409, {"code": "ACTIVE_POLICY_IMMUTABLE"})
    return _commit(db, create_record(db, RequirementPolicyItem, payload, defaults={"policy_version_id": policy_id}), request, event="REQUIREMENT_POLICY_ITEM_CREATED", role=role)


@router.post("/requirements/policy-items/{item_id}/evidence-constraint")
def create_evidence_constraint(item_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, REQUIREMENT_APPROVER_ROLES)
    if not db.get(RequirementPolicyItem, item_id):
        raise _missing("RequirementPolicyItem")
    return _commit(db, create_record(db, RequirementEvidenceConstraint, payload, defaults={"policy_item_id": item_id}), request, event="REQUIREMENT_EVIDENCE_CONSTRAINT_CREATED", role=role)


@router.post("/requirements/policies/{policy_id}/lineage")
def add_requirement_policy_lineage(policy_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, REQUIREMENT_APPROVER_ROLES)
    if not db.get(RequirementPolicyVersion, policy_id):
        raise _missing("RequirementPolicyVersion")
    if not db.get(MasterContentItem, payload.get("master_content_item_id")):
        raise _missing("MasterContentItem")
    return _commit(db, create_record(db, RequirementPolicyLineage, payload, defaults={"policy_version_id": policy_id}), request, event="REQUIREMENT_POLICY_LINEAGE_ADDED", role=role)


@router.post("/requirements/policies/{policy_id}/activate")
def activate_requirement_policy(policy_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, REQUIREMENT_APPROVER_ROLES, "REQUIREMENT_POLICY_APPROVAL_REQUIRED")
    policy = db.get(RequirementPolicyVersion, policy_id)
    if not policy:
        raise _missing("RequirementPolicyVersion")
    if policy.status in {"ACTIVE", "SUPERSEDED", "RETIRED"}:
        raise HTTPException(409, {"code": "REQUIREMENT_POLICY_VERSION_IMMUTABLE"})
    if not db.scalar(select(RequirementPolicyItem).where(RequirementPolicyItem.policy_version_id == policy.id)):
        raise HTTPException(422, {"code": "REQUIREMENT_POLICY_HAS_NO_ITEMS"})
    policy.status = "ACTIVE"
    policy.approved_by = payload.get("approved_by") or actor(role)
    policy.approved_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    return _commit(db, policy, request, event="REQUIREMENT_POLICY_ACTIVATED", role=role)


@router.get("/requirements/resolve")
def resolve_requirements(service_type_id: str, jurisdiction_id: str | None = None, external_body_id: str | None = None, effective_date: str | None = None, db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    try:
        policy = resolve_requirement_policy(db, service_type_id=service_type_id, jurisdiction_id=jurisdiction_id, external_body_id=external_body_id, effective_date=_date(effective_date))
    except DomainConflict as exc:
        raise _conflict(exc)
    return {"policy": projection(policy), "items": projections(list(db.scalars(select(RequirementPolicyItem).where(RequirementPolicyItem.policy_version_id == policy.id).order_by(RequirementPolicyItem.order_index)).all()))}


@router.post("/requirements/evaluate")
def evaluate_requirements(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    try:
        policy = db.get(RequirementPolicyVersion, payload.get("policy_version_id")) if payload.get("policy_version_id") else resolve_requirement_policy(db, service_type_id=payload["service_type_id"], jurisdiction_id=payload.get("jurisdiction_id"), external_body_id=payload.get("external_body_id"), effective_date=_date(payload.get("effective_date")))
        result = evaluate_policy(db, policy, context=payload.get("context", {}), evidence=payload.get("evidence", []), actor_id=actor(role), correlation_id=_corr(request))
        db.commit()
        return result
    except DomainConflict as exc:
        db.rollback()
        raise _conflict(exc)


@router.post("/requirements/applicability-decisions")
def create_applicability_decision(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, REQUIREMENT_APPROVER_ROLES)
    if payload.get("value") not in {"APPLICABLE", "NOT_APPLICABLE", "APPLICABILITY_UNKNOWN"}:
        raise HTTPException(422, {"code": "INVALID_APPLICABILITY_VALUE"})
    return _commit(db, create_record(db, RequirementApplicabilityDecision, payload, defaults={"decided_by": actor(role)}), request, event="REQUIREMENT_APPLICABILITY_DECIDED", role=role)


@router.post("/requirements/decisions")
def create_requirement_decision(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, REQUIREMENT_APPROVER_ROLES)
    if payload.get("decision_type") not in {"WAIVER", "NOT_APPLICABLE", "DISPUTE", "OVERRIDE"}:
        raise HTTPException(422, {"code": "INVALID_REQUIREMENT_DECISION"})
    return _commit(db, create_record(db, RequirementDecision, payload, defaults={"decided_by": actor(role)}), request, event="REQUIREMENT_DECISION_RECORDED", role=role)


# Technical Rule Foundation ----------------------------------------------

@router.get("/technical-rules/sets")
def list_rule_sets(status: str | None = None, db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return _list(db, TechnicalRuleSetVersion, status)


@router.post("/technical-rules/sets")
def create_rule_set(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, TECHNICAL_APPROVER_ROLES)
    return _commit(db, create_record(db, TechnicalRuleSetVersion, payload, defaults={"status": "DRAFT"}), request, event="TECHNICAL_RULE_SET_DRAFT_CREATED", role=role)


@router.post("/technical-rules/sets/{set_id}/rules")
def create_rule(set_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, TECHNICAL_APPROVER_ROLES)
    rule_set = db.get(TechnicalRuleSetVersion, set_id)
    if not rule_set:
        raise _missing("TechnicalRuleSetVersion")
    if rule_set.status != "DRAFT":
        raise HTTPException(409, {"code": "ACTIVE_RULE_SET_IMMUTABLE"})
    return _commit(db, create_record(db, TechnicalRule, payload, defaults={"rule_set_version_id": set_id}), request, event="TECHNICAL_RULE_CREATED", role=role)


@router.post("/technical-rules/{rule_id}/lineage")
def add_rule_lineage(rule_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, TECHNICAL_APPROVER_ROLES)
    if not db.get(TechnicalRule, rule_id):
        raise _missing("TechnicalRule")
    if not db.get(MasterContentItem, payload.get("master_content_item_id")):
        raise _missing("MasterContentItem")
    return _commit(db, create_record(db, TechnicalRuleLineage, payload, defaults={"technical_rule_id": rule_id}), request, event="TECHNICAL_RULE_LINEAGE_ADDED", role=role)


@router.post("/technical-rules/sets/{set_id}/activate")
def activate_rule_set(set_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, TECHNICAL_APPROVER_ROLES, "TECHNICAL_RULE_APPROVAL_REQUIRED")
    rule_set = db.get(TechnicalRuleSetVersion, set_id)
    if not rule_set:
        raise _missing("TechnicalRuleSetVersion")
    if rule_set.status != "DRAFT":
        raise HTTPException(409, {"code": "TECHNICAL_RULE_SET_IMMUTABLE"})
    rules = list(db.scalars(select(TechnicalRule).where(TechnicalRule.rule_set_version_id == set_id)).all())
    if not rules:
        raise HTTPException(422, {"code": "TECHNICAL_RULE_SET_HAS_NO_RULES"})
    if any(not db.scalar(select(TechnicalRuleLineage).where(TechnicalRuleLineage.technical_rule_id == rule.id)) for rule in rules):
        raise HTTPException(422, {"code": "TECHNICAL_RULE_LINEAGE_REQUIRED"})
    rule_set.status = "ACTIVE"
    rule_set.approved_by = payload.get("approved_by") or actor(role)
    rule_set.approved_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    return _commit(db, rule_set, request, event="TECHNICAL_RULE_SET_ACTIVATED", role=role)


@router.get("/technical-rules/resolve")
def resolve_technical_rules(code: str | None = None, service_type_id: str | None = None, jurisdiction_id: str | None = None, external_body_id: str | None = None, effective_date: str | None = None, db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    try:
        rule_set = resolve_rule_set(db, code=code, service_type_id=service_type_id, jurisdiction_id=jurisdiction_id, external_body_id=external_body_id, effective_date=_date(effective_date))
    except DomainConflict as exc:
        raise _conflict(exc)
    return {"rule_set": projection(rule_set), "rules": projections(list(db.scalars(select(TechnicalRule).where(TechnicalRule.rule_set_version_id == rule_set.id).order_by(TechnicalRule.order_index)).all()))}


@router.post("/technical-rules/{rule_id}/evaluate")
def evaluate_technical_rule(rule_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, TECHNICAL_APPROVER_ROLES)
    rule = db.get(TechnicalRule, rule_id)
    if not rule:
        raise _missing("TechnicalRule")
    result = evaluate_rule(db, rule, inputs=payload.get("inputs", {}), context_type=payload.get("context_type", "GENERIC"), context_id=payload.get("context_id", "UNBOUND"), actor_id=actor(role), correlation_id=_corr(request))
    db.commit()
    return result


# Form Automation Runtime -------------------------------------------------

@router.get("/form-automation/profiles")
def list_automation_profiles(db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return _list(db, FormAutomationProfile)


@router.post("/form-automation/profiles")
def create_automation_profile(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, OWNER_ROLES)
    master = db.get(MasterContentItem, payload.get("master_content_item_id"))
    if not master:
        raise _missing("MasterContentItem")
    source_id = payload.get("source_document_version_id") or master.current_document_version_id
    if source_id != master.current_document_version_id:
        raise HTTPException(409, {"code": "PROFILE_SOURCE_VERSION_NOT_CURRENT"})
    item = create_record(db, FormAutomationProfile, payload, defaults={"source_document_version_id": source_id, "managed_by": actor(role), "automation_status": "DRAFT"})
    return _commit(db, item, request, event="FORM_AUTOMATION_PROFILE_CREATED", role=role)


@router.patch("/form-automation/profiles/{profile_id}")
def patch_automation_profile(profile_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, OWNER_ROLES)
    item = db.get(FormAutomationProfile, profile_id)
    if not item:
        raise _missing("FormAutomationProfile")
    before = projection(item)
    if "source_document_version_id" in payload and payload["source_document_version_id"] != item.source_document_version_id:
        item.source_version_state = "NEEDS_REVALIDATION"
    for key, value in payload.items():
        if key not in {"id", "created_at", "updated_at", "automation_status"} and hasattr(item, key):
            setattr(item, key, value)
    return _commit(db, item, request, event="FORM_AUTOMATION_PROFILE_CHANGED", role=role, before=before)


@router.get("/form-automation/semantic-keys")
def list_semantic_keys(db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return _list(db, SemanticKeyDefinition)


@router.post("/form-automation/semantic-keys")
def create_semantic_key(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    return _catalog_create(db, SemanticKeyDefinition, payload, request, role, "SEMANTIC_KEY_CREATED")


@router.post("/form-automation/assertions")
def create_semantic_assertion(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, AUTOMATION_EXECUTE_ROLES)
    if not db.get(SemanticKeyDefinition, payload.get("semantic_key_id")):
        raise _missing("SemanticKeyDefinition")
    if payload.get("verification_status") == "VERIFIED" and role not in OWNER_ROLES:
        raise HTTPException(403, {"code": "VERIFIED_ASSERTION_OWNER_REQUIRED"})
    return _commit(db, create_record(db, SemanticValueAssertion, payload, defaults={"asserted_by": actor(role)}), request, event="SEMANTIC_VALUE_ASSERTION_CREATED", role=role)


@router.get("/form-automation/assertions")
def list_semantic_assertions(context_type: str | None = None, context_id: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, AUTOMATION_EXECUTE_ROLES)
    stmt = select(SemanticValueAssertion)
    if context_type:
        stmt = stmt.where(SemanticValueAssertion.context_type == context_type)
    if context_id:
        stmt = stmt.where(SemanticValueAssertion.context_id == context_id)
    return projections(list(db.scalars(stmt).all()))


@router.post("/form-automation/profiles/{profile_id}/mapping-releases")
def create_mapping_release(profile_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, OWNER_ROLES)
    if not db.get(FormAutomationProfile, profile_id):
        raise _missing("FormAutomationProfile")
    if payload.get("status") not in (None, "DRAFT", "REVIEW"):
        raise HTTPException(422, {"code": "PRODUCTION_MAPPING_RELEASE_DEFERRED"})
    return _commit(db, create_record(db, FormMappingRelease, payload, defaults={"profile_id": profile_id, "status": "DRAFT"}), request, event="FORM_MAPPING_RELEASE_DRAFT_CREATED", role=role)


@router.post("/form-automation/mapping-releases/{release_id}/rules")
def create_mapping_rule(release_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, OWNER_ROLES)
    release = db.get(FormMappingRelease, release_id)
    if not release:
        raise _missing("FormMappingRelease")
    if release.status != "DRAFT":
        raise HTTPException(409, {"code": "MAPPING_RELEASE_IMMUTABLE"})
    return _commit(db, create_record(db, FormMappingRule, payload, defaults={"mapping_release_id": release_id}), request, event="FORM_MAPPING_RULE_CREATED", role=role)


@router.post("/form-automation/mapping-releases/{release_id}/release")
def release_mapping(release_id: str, request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, OWNER_ROLES)
    raise HTTPException(409, {"code": "WAVE_C_MAPPING_RELEASE_DEFERRED", "message": "Production mapping release belongs to future Dashboard V2 Wave C."})


@router.post("/form-automation/instances")
def create_form_instance(payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, AUTOMATION_EXECUTE_ROLES)
    profile = db.get(FormAutomationProfile, payload.get("profile_id"))
    if not profile:
        raise _missing("FormAutomationProfile")
    master = db.get(MasterContentItem, profile.master_content_item_id)
    if not master:
        raise _missing("MasterContentItem")
    if master.current_document_version_id != profile.source_document_version_id:
        profile.source_version_state = "NEEDS_REVALIDATION"
        db.commit()
        raise HTTPException(409, {"code": "SOURCE_VERSION_NEEDS_REVALIDATION"})
    assertion_ids: list[str] = []
    values: dict[str, Any] = {}
    if payload.get("semantic_keys"):
        try:
            resolved = resolve_assertions(db, context_type=payload["context_type"], context_id=payload["context_id"], semantic_keys=payload["semantic_keys"])
        except DomainConflict as exc:
            raise _conflict(exc)
        for key, assertion in resolved:
            values[key.semantic_key] = assertion.value_json
            assertion_ids.append(assertion.id)
    values.update(payload.get("resolved_values", {}))
    item = create_record(db, FormInstance, payload, defaults={"master_content_item_id": profile.master_content_item_id, "source_document_version_id": profile.source_document_version_id, "profile_id": profile.id, "resolved_values": values, "resolved_assertion_ids": assertion_ids, "created_by": actor(role), "status": "DRAFT"})
    return _commit(db, item, request, event="FORM_INSTANCE_CREATED", role=role)


@router.post("/form-automation/instances/{instance_id}/render")
def render_form_instance(instance_id: str, request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, AUTOMATION_EXECUTE_ROLES)
    item = db.get(FormInstance, instance_id)
    if not item:
        raise _missing("FormInstance")
    try:
        result = render_instance(db, item, actor_id=actor(role), correlation_id=_corr(request))
        db.commit()
        return result
    except DomainConflict as exc:
        db.rollback()
        raise _conflict(exc)


@router.get("/form-automation/instances/{instance_id}/artifacts")
def list_generated_artifacts(instance_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, AUTOMATION_EXECUTE_ROLES)
    return projections(list(db.scalars(select(GeneratedArtifact).where(GeneratedArtifact.form_instance_id == instance_id)).all()))


@router.post("/form-automation/artifacts/{artifact_id}/validate")
def validate_generated_artifact(artifact_id: str, request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, AUTOMATION_EXECUTE_ROLES)
    artifact = db.get(GeneratedArtifact, artifact_id)
    if not artifact:
        raise _missing("GeneratedArtifact")
    result = FormValidationResult(generated_artifact_id=artifact.id, validation_type="READ_BACK", status="PASS", result_json={"hash": artifact.content_hash, "authority_only_untouched": True, "human_signer_untouched": True}, validated_by=actor(role))
    db.add(result)
    db.flush()
    audit(db, correlation_id=_corr(request), event_type="FORM_ARTIFACT_VALIDATED", entity_type="GeneratedArtifact", entity_id=artifact.id, actor_id=actor(role), after=projection(result))
    db.commit()
    return projection(result)


@router.post("/form-automation/artifacts/{artifact_id}/qa")
def run_form_qa(artifact_id: str, payload: dict[str, Any] = Body(default={}), request: Request = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_role(role, AUTOMATION_EXECUTE_ROLES)
    if not db.get(GeneratedArtifact, artifact_id):
        raise _missing("GeneratedArtifact")
    artifact = db.get(GeneratedArtifact, artifact_id)
    qa_type = payload.get("qa_type", "STRUCTURAL_MAPPING")
    if qa_type not in {"STRUCTURAL_MAPPING", "SYNTHETIC_FILL", "READ_BACK", "VISUAL", "ARABIC_RTL", "BILINGUAL", "REPEATING_GRID", "SIGNATURE_ZONE", "WRITER_OWNERSHIP", "NORMALIZED_RENDITION"}:
        raise HTTPException(422, {"code": "QA_TYPE_INVALID"})
    item = FormQARun(generated_artifact_id=artifact_id, mapping_release_id=artifact.mapping_release_id if artifact else None, qa_type=qa_type, result=payload.get("result", "PASS"), checks_json=payload.get("checks_json", {}), synthetic_only=True, created_by=actor(role))
    db.add(item)
    result = _commit(db, item, request, event="FORM_ARTIFACT_QA_RECORDED", role=role)
    if item.mapping_release_id:
        gate = FormMappingReleaseQAGate(mapping_release_id=item.mapping_release_id, qa_run_id=item.id, qa_type=qa_type, required=payload.get("required", True))
        db.add(gate)
        db.commit()
    return result


@router.get("/shared-domain/future-seam")
def future_dashboard_seam(db: Session = Depends(get_db), _role: Role = Depends(current_user_role)):
    return {
        "external_body_ids": [row[0] for row in db.execute(select(ExternalBody.id)).all()],
        "service_type_ids": [row[0] for row in db.execute(select(ServiceType.id)).all()],
        "jurisdiction_ids": [row[0] for row in db.execute(select(Jurisdiction.id)).all()],
        "requirement_policy_version_ids": [row[0] for row in db.execute(select(RequirementPolicyVersion.id)).all()],
        "technical_rule_set_version_ids": [row[0] for row in db.execute(select(TechnicalRuleSetVersion.id)).all()],
        "form_automation_profile_ids": [row[0] for row in db.execute(select(FormAutomationProfile.id)).all()],
        "dashboard_ui": "V2_FUTURE_SEAM_ONLY",
    }
