"""Bounded AuthorityCase Preparation + Submission Loop APIs.

The router is intentionally explicit: no proposal, activation, baseline, or
folder action creates a case; no authorization claims external submission; and
only an evidence-backed confirmation creates a confirmed submission cycle.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..models import (
    ApprovedDesignBaseline, ApprovedDesignBaselineMember, AuthorityCase,
    AuthorityCaseCreateRequest, AuthorityCaseFinding, AuthorityCaseIdentifier,
    AuthorityCaseOutcome, AuthorityCasePolicyBinding, AuthorityFindingResponse,
    AuthoritySubmissionCycle, CaseEvidenceSelection, Document, DocumentVersion,
    ExternalBody, ExternalSubmissionSnapshot, FormInstance, Jurisdiction, LineageEdge,
    PhysicalEvidenceItem, PreparationRevision, Project, RequirementApplicabilityDecision,
    RequirementDecision, RequirementDefinition, RequirementGroup,
    RequirementInstance, RequirementPolicyItem, RequirementPolicyVersion,
    RegulatoryJourney, Role, ServiceType, SubmissionAttempt, SubmissionPackage, SubmissionPackageItem,
    SubmissionPrecheckCheck, SubmissionPrecheckRun,
)


router = APIRouter(prefix="/api")


def _actor(request: Request, payload: dict[str, Any] | None = None) -> str:
    return request.headers.get("X-Dev-Actor") or str((payload or {}).get("actor") or "role-actor")


def _corr(request: Request) -> str:
    return getattr(request.state, "correlation_id", str(uuid4()))


def _json(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _row(item: Any) -> dict[str, Any]:
    return {key: _json(value) for key, value in item.__dict__.items() if not key.startswith("_")}


def _http(status: int, code: str, **extra: Any) -> HTTPException:
    return HTTPException(status_code=status, detail={"code": code, **extra})


def _runtime_role(role: Role, action: str) -> None:
    """Safe defaults while visible personas remain Owner, BD, Engineering."""
    owner = {Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN}
    engineering = {Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN, Role.RESPONSIBLE_ENGINEER, Role.REQUIREMENT_STEWARD, Role.PERMIT_PREPARER}
    if action in {"CASE_CREATE", "SUBMIT_AUTHORIZE", "EXTERNAL_CONFIRM", "OUTCOME_RECORD", "CASE_CLOSE"} and role not in owner:
        raise _http(403, "CAPABILITY_DENIED", capability=action)
    if action in {"CASE_READ", "REQUIREMENT_REVIEW", "EVIDENCE_MANAGE", "PREPARATION_MANAGE", "PACKAGE_MANAGE", "PRECHECK_RUN", "FINDING_MANAGE"} and role not in engineering | {Role.PROCESS_CHAMPION}:
        raise _http(403, "CAPABILITY_DENIED", capability=action)


def _case(db: Session, case_id: str) -> AuthorityCase:
    item = db.get(AuthorityCase, case_id)
    if not item:
        raise _http(404, "AUTHORITY_CASE_NOT_FOUND", case_id=case_id)
    return item


def _project(db: Session, project_id: str) -> Project:
    item = db.get(Project, project_id)
    if not item:
        raise _http(404, "PROJECT_NOT_FOUND", project_id=project_id)
    if not item.activated_at:
        raise _http(409, "PREPARATION_SUBMISSION_LOOP_BLOCKED_BY_PROJECT_ACTIVATION", project_id=project_id)
    return item


def _case_project(db: Session, case: AuthorityCase) -> Project:
    journey = db.get(RegulatoryJourney, case.regulatory_journey_id) if case.regulatory_journey_id else None
    journey_project = db.get(Project, journey.project_id) if journey and journey.project_id else None
    if journey_project:
        return journey_project
    raise _http(409, "AUTHORITY_CASE_PROJECT_CONTEXT_MISSING", case_id=case.id)


def _canonical_context(db: Session, payload: dict[str, Any]) -> tuple[Project, ExternalBody, Jurisdiction, ServiceType]:
    project = _project(db, str(payload.get("project_id") or ""))
    body = db.get(ExternalBody, payload.get("external_body_id"))
    jurisdiction = db.get(Jurisdiction, payload.get("jurisdiction_id"))
    service = db.get(ServiceType, payload.get("service_type_id"))
    if not body or body.status != "ACTIVE":
        raise _http(422, "CANONICAL_EXTERNAL_BODY_REQUIRED")
    if not jurisdiction or jurisdiction.status != "ACTIVE":
        raise _http(422, "CANONICAL_JURISDICTION_REQUIRED")
    if not service or service.status != "ACTIVE":
        raise _http(422, "CANONICAL_SERVICE_TYPE_REQUIRED")
    return project, body, jurisdiction, service


def _lineage(db: Session, case: AuthorityCase, downstream_type: str, downstream_id: str, request: Request, upstream_type: str = "AuthorityCase", upstream_id: str | None = None, kind: str = "CASE_EXECUTION") -> None:
    project = _case_project(db, case)
    db.add(LineageEdge(project_id=project.id, upstream_type=upstream_type, upstream_id=upstream_id or case.id, downstream_type=downstream_type, downstream_id=downstream_id, dependency_kind=kind, correlation_id=_corr(request)))


def _latest_binding(db: Session, case_id: str) -> AuthorityCasePolicyBinding | None:
    return db.scalar(select(AuthorityCasePolicyBinding).where(AuthorityCasePolicyBinding.authority_case_id == case_id))


def _policy_or_block(db: Session, case: AuthorityCase) -> RequirementPolicyVersion:
    binding = _latest_binding(db, case.id)
    if not binding or binding.resolution_state != "RESOLVED":
        raise _http(409, "REQUIREMENT_POLICY_NOT_INITIALIZED", state="REQUIREMENTS_NOT_CONFIGURED")
    policy = db.get(RequirementPolicyVersion, binding.policy_version_id)
    if not policy:
        raise _http(409, "BOUND_REQUIREMENT_POLICY_NOT_FOUND")
    return policy


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def _serialize_case(db: Session, case: AuthorityCase) -> dict[str, Any]:
    journey = None
    if case.regulatory_journey_id:
        from ..models import RegulatoryJourney
        journey = db.get(RegulatoryJourney, case.regulatory_journey_id)
    body = db.get(ExternalBody, case.external_body_id)
    jurisdiction = db.get(Jurisdiction, case.jurisdiction_id)
    service = db.get(ServiceType, case.service_type_id)
    identifiers = db.scalars(select(AuthorityCaseIdentifier).where(AuthorityCaseIdentifier.authority_case_id == case.id).order_by(AuthorityCaseIdentifier.created_at)).all()
    return {"case": _row(case), "journey": _row(journey) if journey else None, "external_body": _row(body) if body else None, "jurisdiction": _row(jurisdiction) if jurisdiction else None, "service_type": _row(service) if service else None, "identifiers": [_row(x) for x in identifiers]}


@router.get("/authority-cases")
def list_authority_cases(request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "CASE_READ")
    rows = db.scalars(select(AuthorityCase).order_by(AuthorityCase.created_at.desc())).all()
    return [_serialize_case(db, x) for x in rows]


@router.post("/authority-cases")
def create_authority_case(payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "CASE_CREATE")
    actor = _actor(request, payload)
    project, body, jurisdiction, service = _canonical_context(db, payload)
    key = str(payload.get("idempotency_key") or "").strip()
    if not key:
        raise _http(422, "CASE_IDEMPOTENCY_KEY_REQUIRED")
    prior = db.scalar(select(AuthorityCaseCreateRequest).where(AuthorityCaseCreateRequest.idempotency_key == key))
    if prior:
        return _serialize_case(db, _case(db, prior.authority_case_id))
    journey = None
    journey_id = payload.get("regulatory_journey_id")
    if journey_id:
        journey = db.get(RegulatoryJourney, journey_id)
        if not journey or journey.project_id != project.id or journey.external_body_id != body.id or journey.jurisdiction_id != jurisdiction.id or journey.service_type_id != service.id:
            raise _http(409, "REGULATORY_JOURNEY_CONTEXT_MISMATCH")
    else:
        journey = RegulatoryJourney(journey_code=str(payload.get("journey_code") or f"JRN-{project.project_number}-{str(uuid4())[:8].upper()}"), project_id=project.id, service_type_id=service.id, jurisdiction_id=jurisdiction.id, external_body_id=body.id, status="OPEN", opened_at=datetime.now(timezone.utc), created_by=actor)
        db.add(journey); db.flush()
    case_ref = str(payload.get("case_reference") or f"CASE-{project.project_number}-{str(uuid4())[:8].upper()}")
    case = AuthorityCase(case_reference=case_ref, regulatory_journey_id=journey.id, external_body_id=body.id, service_type_id=service.id, jurisdiction_id=jurisdiction.id, status="PREPARING", subject_type=str(payload.get("subject_type") or "Project"), subject_id=str(payload.get("subject_id") or project.id), opened_at=datetime.now(timezone.utc), created_by=actor)
    db.add(case); db.flush()
    db.add(AuthorityCaseCreateRequest(idempotency_key=key, authority_case_id=case.id, requested_by=actor))
    _lineage(db, case, "AuthorityCase", case.id, request, upstream_type="Project", upstream_id=project.id, kind="EXPLICIT_CASE_START")
    audit(db, correlation_id=_corr(request), event_type="AUTHORITY_CASE_CREATED", entity_type="AuthorityCase", entity_id=case.id, actor_id=actor, after={"case_reference": case.case_reference, "project_id": project.id, "external_body_id": body.id, "jurisdiction_id": jurisdiction.id, "service_type_id": service.id})
    db.commit()
    return _serialize_case(db, case)


@router.get("/authority-cases/{case_id}")
def authority_case_workspace(case_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "CASE_READ")
    case = _case(db, case_id)
    binding = _latest_binding(db, case.id)
    requirements = db.scalars(select(RequirementInstance).where(RequirementInstance.authority_case_id == case.id).order_by(RequirementInstance.created_at)).all()
    preparations = db.scalars(select(PreparationRevision).where(PreparationRevision.authority_case_id == case.id).order_by(PreparationRevision.authority_revision_number)).all()
    packages = db.scalars(select(SubmissionPackage).where(SubmissionPackage.authority_case_id == case.id).order_by(SubmissionPackage.created_at)).all()
    cycles = db.scalars(select(AuthoritySubmissionCycle).where(AuthoritySubmissionCycle.authority_case_id == case.id).order_by(AuthoritySubmissionCycle.cycle_number)).all()
    findings = db.scalars(select(AuthorityCaseFinding).where(AuthorityCaseFinding.authority_case_id == case.id).order_by(AuthorityCaseFinding.created_at)).all()
    outcomes = db.scalars(select(AuthorityCaseOutcome).where(AuthorityCaseOutcome.authority_case_id == case.id).order_by(AuthorityCaseOutcome.created_at)).all()
    return {**_serialize_case(db, case), "policy_binding": _row(binding) if binding else None, "requirements": [_row(x) for x in requirements], "preparations": [_row(x) for x in preparations], "packages": [_row(x) for x in packages], "cycles": [_row(x) for x in cycles], "findings": [_row(x) for x in findings], "outcomes": [_row(x) for x in outcomes], "state_separation": {"internal": case.status, "external": cycles[-1].status if cycles else "UNKNOWN"}}


@router.post("/authority-cases/{case_id}/requirements/initialize")
def initialize_requirements(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "REQUIREMENT_REVIEW")
    case = _case(db, case_id); _case_project(db, case)
    existing = _latest_binding(db, case.id)
    if existing:
        policy = db.get(RequirementPolicyVersion, existing.policy_version_id)
        items = db.scalars(select(RequirementInstance).where(RequirementInstance.authority_case_id == case.id).order_by(RequirementInstance.created_at)).all()
        return {"binding": _row(existing), "policy": _row(policy), "items": [_row(x) for x in items]}
    today = date.fromisoformat(str(payload.get("effective_date") or date.today()))
    query = select(RequirementPolicyVersion).where(RequirementPolicyVersion.service_type_id == case.service_type_id, RequirementPolicyVersion.jurisdiction_id == case.jurisdiction_id, RequirementPolicyVersion.external_body_id == case.external_body_id, RequirementPolicyVersion.status == "ACTIVE", or_(RequirementPolicyVersion.effective_from.is_(None), RequirementPolicyVersion.effective_from <= today), or_(RequirementPolicyVersion.effective_to.is_(None), RequirementPolicyVersion.effective_to >= today))
    policies = db.scalars(query.order_by(RequirementPolicyVersion.version)).all()
    actor = _actor(request, payload)
    if not policies:
        raise _http(409, "NO_POLICY", state="REQUIREMENTS_NOT_CONFIGURED")
    if len(policies) != 1:
        raise _http(409, "AMBIGUOUS_POLICY", policy_ids=[x.id for x in policies])
    policy = policies[0]
    binding = AuthorityCasePolicyBinding(authority_case_id=case.id, policy_version_id=policy.id, resolution_state="RESOLVED", resolved_by=actor, resolution_facts={"effective_date": today.isoformat(), "context": {"external_body_id": case.external_body_id, "jurisdiction_id": case.jurisdiction_id, "service_type_id": case.service_type_id}})
    db.add(binding); db.flush()
    items = db.scalars(select(RequirementPolicyItem).where(RequirementPolicyItem.policy_version_id == policy.id, RequirementPolicyItem.status == "ACTIVE").order_by(RequirementPolicyItem.order_index)).all()
    instances = []
    for item in items:
        instance = RequirementInstance(authority_case_id=case.id, policy_version_id=policy.id, policy_item_id=item.id, requirement_definition_id=item.requirement_definition_id, group_id=item.group_id, lifecycle_phase_id=item.phase_id, purpose=policy.purpose, applicability="APPLICABILITY_UNKNOWN", status="MISSING", dependency_state="NOT_DUE", reason="Applicability requires governed case decision", source_snapshot={"policy_version": policy.version, "policy_item_id": item.id})
        db.add(instance); instances.append(instance)
    case.status = "REQUIREMENTS_NOT_CONFIGURED" if not items else "PREPARING"
    _lineage(db, case, "RequirementPolicyVersion", policy.id, request, upstream_type="AuthorityCase", upstream_id=case.id, kind="CASE_POLICY_BINDING")
    audit(db, correlation_id=_corr(request), event_type="AUTHORITY_CASE_POLICY_BOUND", entity_type="AuthorityCasePolicyBinding", entity_id=binding.id, actor_id=actor, after={"case_id": case.id, "policy_version_id": policy.id, "item_count": len(items)})
    db.commit()
    return {"binding": _row(binding), "policy": _row(policy), "items": [_row(x) for x in instances]}


@router.get("/authority-cases/{case_id}/requirements")
def list_requirements(case_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "CASE_READ")
    _case(db, case_id)
    rows = db.scalars(select(RequirementInstance).where(RequirementInstance.authority_case_id == case_id).order_by(RequirementInstance.created_at)).all()
    return [_row(x) for x in rows]


@router.post("/authority-cases/{case_id}/requirements/{instance_id}/decision")
def requirement_decision(case_id: str, instance_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "REQUIREMENT_REVIEW")
    instance = db.get(RequirementInstance, instance_id)
    if not instance or instance.authority_case_id != case_id:
        raise _http(404, "REQUIREMENT_INSTANCE_NOT_FOUND")
    decision = str(payload.get("decision") or "")
    if decision not in {"APPLICABLE", "NOT_APPLICABLE", "APPLICABILITY_UNKNOWN", "WAIVED"}:
        raise _http(422, "INVALID_APPLICABILITY_DECISION")
    reason = str(payload.get("reason") or "").strip()
    if decision in {"NOT_APPLICABLE", "WAIVED"} and not reason:
        raise _http(422, "CONTROLLED_DECISION_REASON_REQUIRED")
    actor = _actor(request, payload)
    db.add(RequirementApplicabilityDecision(policy_item_id=instance.policy_item_id, context_type="AuthorityCase", context_id=case_id, value=decision if decision != "WAIVED" else "NOT_APPLICABLE", reason=reason, authority=str(payload.get("authority") or "CASE_AUTHORITY"), decided_by=actor))
    if decision == "APPLICABLE": instance.applicability = decision; instance.status = "MISSING"; instance.reason = "Applicable; evidence or governed form required"
    elif decision == "NOT_APPLICABLE": instance.applicability = decision; instance.status = "SATISFIED"; instance.reason = reason
    elif decision == "WAIVED": instance.applicability = "NOT_APPLICABLE"; instance.status = "WAIVED"; instance.reason = reason
    else: instance.applicability = decision; instance.status = "NEEDS_REVIEW"; instance.reason = reason or "Applicability remains unknown"
    instance.evaluated_by = actor; instance.evaluated_at = datetime.now(timezone.utc)
    audit(db, correlation_id=_corr(request), event_type="REQUIREMENT_APPLICABILITY_DECIDED", entity_type="RequirementInstance", entity_id=instance.id, actor_id=actor, after={"decision": decision, "reason": reason})
    db.commit()
    return _row(instance)


@router.post("/authority-cases/{case_id}/requirements/{instance_id}/evidence")
def select_requirement_evidence(case_id: str, instance_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "EVIDENCE_MANAGE")
    instance = db.get(RequirementInstance, instance_id)
    if not instance or instance.authority_case_id != case_id:
        raise _http(404, "REQUIREMENT_INSTANCE_NOT_FOUND")
    form_instance_id = payload.get("form_instance_id")
    form = db.get(FormInstance, form_instance_id) if form_instance_id else None
    if form_instance_id and (not form or form.context_type != "AuthorityCase" or form.context_id != case_id):
        raise _http(403, "CROSS_CASE_FORM_INSTANCE_DENIED")
    if form and form.status in {"NEEDS_REVALIDATION", "INVALIDATED"}:
        raise _http(409, "FORM_INSTANCE_NOT_ELIGIBLE", status=form.status)
    document_id = payload.get("document_version_id") or (form.source_document_version_id if form else None)
    document = db.get(DocumentVersion, document_id) if document_id else None
    if not document:
        raise _http(422, "DOCUMENT_VERSION_OR_FORM_INSTANCE_REQUIRED")
    parent = db.get(Document, document.document_id)
    case = _case(db, case_id); project = _case_project(db, case)
    if parent and parent.project_id not in {None, project.id}:
        raise _http(403, "CROSS_PROJECT_EVIDENCE_DENIED")
    today = date.today()
    stale = bool(document.valid_until and document.valid_until < today) or document.approval_state.value in {"SUPERSEDED"}
    actor = _actor(request, payload)
    selection = CaseEvidenceSelection(authority_case_id=case_id, requirement_instance_id=instance.id, document_version_id=document.id, form_instance_id=form.id if form else None, evidence_kind=str(payload.get("evidence_kind") or ("FORM" if form else "DOCUMENT")), status="STALE" if stale else "SELECTED", reason="Expired or superseded DocumentVersion" if stale else "Selected for this exact case and requirement", details_json={"document_sha256": document.sha256, "approval_state": _json(document.approval_state), "project_id": parent.project_id if parent else None, "form_instance_id": form.id if form else None, "form_status": form.status if form else None, "form_profile_id": form.profile_id if form else None, "form_mapping_release_id": form.mapping_release_id if form else None}, selected_by=actor)
    db.add(selection)
    if instance.applicability == "APPLICABLE":
        instance.status = "STALE" if stale else "SATISFIED"
        instance.reason = selection.reason
    elif instance.applicability == "APPLICABILITY_UNKNOWN":
        instance.status = "NEEDS_REVIEW"
        instance.reason = "Evidence selected but applicability remains unknown"
    db.flush(); _lineage(db, case, "RequirementEvidenceEvaluation", selection.id, request, upstream_type="DocumentVersion", upstream_id=document.id, kind="CASE_SCOPED_EVIDENCE")
    audit(db, correlation_id=_corr(request), event_type="CASE_EVIDENCE_SELECTED", entity_type="CaseEvidenceSelection", entity_id=selection.id, actor_id=actor, after={"case_id": case_id, "requirement_instance_id": instance.id, "document_version_id": document.id, "status": selection.status})
    db.commit()
    return {"selection": _row(selection), "requirement": _row(instance)}


@router.post("/authority-cases/{case_id}/physical-evidence")
def add_physical_evidence(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "EVIDENCE_MANAGE")
    case = _case(db, case_id); _case_project(db, case)
    instance = db.get(RequirementInstance, payload.get("requirement_instance_id")) if payload.get("requirement_instance_id") else None
    if instance and instance.authority_case_id != case.id:
        raise _http(403, "CROSS_CASE_PHYSICAL_EVIDENCE_DENIED")
    item = PhysicalEvidenceItem(authority_case_id=case.id, requirement_instance_id=instance.id if instance else None, item_type=str(payload.get("item_type") or "PHYSICAL_ORIGINAL"), description=str(payload.get("description") or ""), quantity=int(payload.get("quantity") or 1), status=str(payload.get("status") or "EXPECTED"), location=payload.get("location"), custodian=payload.get("custodian"), notes=payload.get("notes"))
    if not item.description:
        raise _http(422, "PHYSICAL_EVIDENCE_DESCRIPTION_REQUIRED")
    db.add(item); db.flush(); audit(db, correlation_id=_corr(request), event_type="PHYSICAL_EVIDENCE_RECORDED", entity_type="PhysicalEvidenceItem", entity_id=item.id, actor_id=_actor(request, payload), after=_row(item)); db.commit()
    return _row(item)


def _snapshot(db: Session, case: AuthorityCase, prep: PreparationRevision) -> dict[str, Any]:
    instances = db.scalars(select(RequirementInstance).where(RequirementInstance.authority_case_id == case.id).order_by(RequirementInstance.id)).all()
    evidence = db.scalars(select(CaseEvidenceSelection).where(CaseEvidenceSelection.authority_case_id == case.id).order_by(CaseEvidenceSelection.id)).all()
    physical = db.scalars(select(PhysicalEvidenceItem).where(PhysicalEvidenceItem.authority_case_id == case.id).order_by(PhysicalEvidenceItem.id)).all()
    return {"case_id": case.id, "policy_version_id": prep.authority_policy_version_id, "approved_design_baseline_id": prep.authority_approved_design_baseline_id, "requirements": [_row(x) for x in instances], "evidence": [_row(x) for x in evidence], "physical": [_row(x) for x in physical]}


@router.post("/authority-cases/{case_id}/preparations")
def create_preparation(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "PREPARATION_MANAGE")
    case = _case(db, case_id); policy = _policy_or_block(db, case)
    actor = _actor(request, payload)
    baseline_id = payload.get("approved_design_baseline_id")
    if baseline_id:
        baseline = db.get(ApprovedDesignBaseline, baseline_id)
        if not baseline or baseline.project_id != _case_project(db, case).id or baseline.status != "APPROVED":
            raise _http(409, "ENGINEERING_BASELINE_NOT_ELIGIBLE")
    last = db.scalar(select(func.max(PreparationRevision.authority_revision_number)).where(PreparationRevision.authority_case_id == case.id)) or 0
    project = _case_project(db, case)
    prep = PreparationRevision(project_id=project.id, application_id=None, sequence=last + 1, status="WORKING", scenario_version="AUTHORITY_CASE_V2", field_authority_version="CANONICAL", requirement_config_version=policy.version, rendering_config_version="CANONICAL", authority_case_id=case.id, authority_revision_number=last + 1, authority_policy_version_id=policy.id, authority_approved_design_baseline_id=baseline_id, authority_state="WORKING", created_by=actor)
    db.add(prep); db.flush(); prep.authority_snapshot_json = _snapshot(db, case, prep); _lineage(db, case, "PreparationRevision", prep.id, request, upstream_type="RequirementPolicyVersion", upstream_id=policy.id, kind="PREPARATION_POLICY_PIN")
    audit(db, correlation_id=_corr(request), event_type="PREPARATION_REVISION_CREATED", entity_type="PreparationRevision", entity_id=prep.id, actor_id=actor, after={"case_id": case.id, "revision_number": prep.authority_revision_number, "baseline_id": baseline_id}); db.commit()
    return _row(prep)


@router.post("/authority-cases/{case_id}/preparations/{preparation_id}/lock")
def lock_preparation(case_id: str, preparation_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "PREPARATION_MANAGE")
    prep = db.get(PreparationRevision, preparation_id)
    if not prep or prep.authority_case_id != case_id:
        raise _http(404, "PREPARATION_REVISION_NOT_FOUND")
    if prep.authority_state == "LOCKED": return _row(prep)
    if prep.authority_state != "WORKING": raise _http(409, "PREPARATION_REVISION_IMMUTABLE")
    case = _case(db, case_id); prep.authority_snapshot_json = _snapshot(db, case, prep); prep.authority_snapshot_hash = _hash(prep.authority_snapshot_json); prep.authority_state = "LOCKED"; prep.status = "AUTHORITY_LOCKED"; prep.authority_locked_at = datetime.now(timezone.utc)
    audit(db, correlation_id=_corr(request), event_type="PREPARATION_REVISION_LOCKED", entity_type="PreparationRevision", entity_id=prep.id, actor_id=_actor(request, payload), after={"snapshot_hash": prep.authority_snapshot_hash}); db.commit(); return _row(prep)


@router.post("/authority-cases/{case_id}/packages")
def create_package(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "PACKAGE_MANAGE")
    prep = db.get(PreparationRevision, payload.get("preparation_revision_id"))
    if not prep or prep.authority_case_id != case_id or prep.authority_state != "LOCKED": raise _http(409, "LOCKED_PREPARATION_REQUIRED")
    prior = db.scalar(select(SubmissionPackage).where(SubmissionPackage.preparation_revision_id == prep.id))
    if prior: return _row(prior)
    package = SubmissionPackage(authority_case_id=case_id, preparation_revision_id=prep.id, created_by=_actor(request, payload))
    db.add(package); db.flush(); audit(db, correlation_id=_corr(request), event_type="SUBMISSION_PACKAGE_CREATED", entity_type="SubmissionPackage", entity_id=package.id, actor_id=_actor(request, payload), after={"preparation_revision_id": prep.id}); db.commit(); return _row(package)


@router.post("/authority-cases/{case_id}/packages/{package_id}/items")
def add_package_item(case_id: str, package_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "PACKAGE_MANAGE")
    package = db.get(SubmissionPackage, package_id)
    if not package or package.authority_case_id != case_id: raise _http(404, "SUBMISSION_PACKAGE_NOT_FOUND")
    if package.state != "DRAFT": raise _http(409, "LOCKED_SUBMISSION_PACKAGE_IMMUTABLE")
    order = int(payload.get("display_order") or ((db.scalar(select(func.max(SubmissionPackageItem.display_order)).where(SubmissionPackageItem.package_id == package.id)) or 0) + 1))
    item = SubmissionPackageItem(package_id=package.id, item_type=str(payload.get("item_type") or "DOCUMENT"), requirement_instance_id=payload.get("requirement_instance_id"), evidence_selection_id=payload.get("evidence_selection_id"), document_version_id=payload.get("document_version_id"), form_instance_id=payload.get("form_instance_id"), baseline_id=payload.get("baseline_id"), baseline_member_id=payload.get("baseline_member_id"), physical_evidence_item_id=payload.get("physical_evidence_item_id"), display_order=order, section=payload.get("section"), submission_filename=payload.get("submission_filename"), label=payload.get("label"))
    if item.requirement_instance_id:
        req = db.get(RequirementInstance, item.requirement_instance_id)
        if not req or req.authority_case_id != case_id: raise _http(403, "CROSS_CASE_PACKAGE_REQUIREMENT_DENIED")
    if item.evidence_selection_id:
        evidence = db.get(CaseEvidenceSelection, item.evidence_selection_id)
        if not evidence or evidence.authority_case_id != case_id: raise _http(403, "CROSS_CASE_PACKAGE_EVIDENCE_DENIED")
    if item.form_instance_id:
        form = db.get(FormInstance, item.form_instance_id)
        if not form or form.context_type != "AuthorityCase" or form.context_id != case_id: raise _http(403, "CROSS_CASE_PACKAGE_FORM_DENIED")
        if form.status in {"NEEDS_REVALIDATION", "INVALIDATED"}: raise _http(409, "FORM_INSTANCE_NOT_ELIGIBLE", status=form.status)
    if item.document_version_id and not db.get(DocumentVersion, item.document_version_id): raise _http(422, "PACKAGE_DOCUMENT_VERSION_NOT_FOUND")
    db.add(item); db.commit(); return _row(item)


@router.post("/authority-cases/{case_id}/packages/{package_id}/lock")
def lock_package(case_id: str, package_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "PACKAGE_MANAGE")
    package = db.get(SubmissionPackage, package_id)
    if not package or package.authority_case_id != case_id: raise _http(404, "SUBMISSION_PACKAGE_NOT_FOUND")
    if package.state == "LOCKED": return _row(package)
    if package.state != "DRAFT": raise _http(409, "SUBMISSION_PACKAGE_IMMUTABLE")
    items = db.scalars(select(SubmissionPackageItem).where(SubmissionPackageItem.package_id == package.id).order_by(SubmissionPackageItem.display_order)).all()
    if not items: raise _http(409, "EXPLICIT_PACKAGE_ITEM_REQUIRED")
    manifest = [_row(x) for x in items]; package.manifest_json = {"preparation_revision_id": package.preparation_revision_id, "items": manifest}; package.manifest_hash = _hash(package.manifest_json); package.state = "LOCKED"; package.locked_at = datetime.now(timezone.utc)
    audit(db, correlation_id=_corr(request), event_type="SUBMISSION_PACKAGE_LOCKED", entity_type="SubmissionPackage", entity_id=package.id, actor_id=_actor(request, payload), after={"manifest_hash": package.manifest_hash, "item_count": len(items)}); db.commit(); return _row(package)


def _precheck(db: Session, case: AuthorityCase, prep: PreparationRevision, package: SubmissionPackage, actor: str, request: Request) -> SubmissionPrecheckRun:
    checks: list[tuple[str, str, str, str, bool, str | None, str | None]] = []
    def add(code: str, category: str, result: str, message: str, blocking: bool = True, source_type: str | None = None, source_id: str | None = None): checks.append((code, category, result, message, blocking, source_type, source_id))
    if prep.authority_state != "LOCKED": add("PREPARATION_LOCKED", "PREPARATION", "BLOCKED", "PreparationRevision must be locked")
    else: add("PREPARATION_LOCKED", "PREPARATION", "PASS", "PreparationRevision is immutable and locked", False)
    if package.state != "LOCKED": add("PACKAGE_LOCKED", "PACKAGE", "BLOCKED", "SubmissionPackage manifest must be locked")
    else: add("PACKAGE_LOCKED", "PACKAGE", "PASS", "Explicit package manifest is locked", False)
    requirements = db.scalars(select(RequirementInstance).where(RequirementInstance.authority_case_id == case.id)).all()
    groups: dict[str, list[RequirementInstance]] = {}
    for req in requirements:
        if req.group_id: groups.setdefault(req.group_id, []).append(req)
        if req.applicability == "APPLICABILITY_UNKNOWN": add("REQUIREMENT_APPLICABILITY_UNKNOWN", "REQUIREMENTS", "NEEDS_REVIEW", f"Requirement {req.id} has unknown applicability", True, "RequirementInstance", req.id)
        elif req.applicability == "NOT_APPLICABLE": add("REQUIREMENT_NOT_APPLICABLE", "REQUIREMENTS", "PASS", f"Requirement {req.id} is governed not-applicable", False, "RequirementInstance", req.id)
        elif req.status not in {"SATISFIED", "WAIVED"}: add("REQUIREMENT_NOT_SATISFIED", "REQUIREMENTS", "BLOCKED", f"Requirement {req.id}: {req.status}", True, "RequirementInstance", req.id)
        else: add("REQUIREMENT_SATISFIED", "REQUIREMENTS", "PASS", f"Requirement {req.id} is satisfied", False, "RequirementInstance", req.id)
    for group_id, rows in groups.items():
        group = db.get(RequirementGroup, group_id)
        if not group: continue
        satisfied = sum(x.status in {"SATISFIED", "WAIVED"} or x.applicability == "NOT_APPLICABLE" for x in rows)
        required = 1 if group.group_type in {"ANY_OF", "ONE_OF"} else group.min_count if group.group_type == "AT_LEAST_N" and group.min_count else len(rows)
        if satisfied < required: add("REQUIREMENT_GROUP_UNSATISFIED", "REQUIREMENTS", "BLOCKED", f"Group {group.code} requires {required} satisfied item(s), has {satisfied}", True, "RequirementGroup", group.id)
    physical = db.scalars(select(PhysicalEvidenceItem).where(PhysicalEvidenceItem.authority_case_id == case.id)).all()
    physical_blocked = any(x.status not in {"VERIFIED_AVAILABLE", "HANDED_OVER_FOR_SUBMISSION"} for x in physical if x.requirement_instance_id and any(r.id == x.requirement_instance_id and r.applicability == "APPLICABLE" for r in requirements))
    if physical_blocked: add("PHYSICAL_EVIDENCE_NOT_READY", "PHYSICAL", "BLOCKED", "Required physical original/sample is not verified available", True)
    else: add("PHYSICAL_READINESS", "PHYSICAL", "PASS", "No unresolved required physical evidence", False)
    if prep.authority_approved_design_baseline_id:
        baseline = db.get(ApprovedDesignBaseline, prep.authority_approved_design_baseline_id)
        members = db.scalars(select(ApprovedDesignBaselineMember).where(ApprovedDesignBaselineMember.baseline_id == prep.authority_approved_design_baseline_id)).all() if baseline else []
        if not baseline or baseline.project_id != _case_project(db, case).id or baseline.status != "APPROVED" or not members: add("ENGINEERING_BASELINE", "ENGINEERING", "BLOCKED", "ApprovedDesignBaseline is missing, withdrawn, mismatched, or has no members", True, "ApprovedDesignBaseline", prep.authority_approved_design_baseline_id)
        else: add("ENGINEERING_BASELINE", "ENGINEERING", "PASS", "Exact professionally approved baseline and members are pinned", False, "ApprovedDesignBaseline", baseline.id)
    else: add("ENGINEERING_BASELINE", "ENGINEERING", "NEEDS_REVIEW", "No baseline pinned; service-specific design requirements cannot pass", True)
    if not db.scalars(select(SubmissionPackageItem).where(SubmissionPackageItem.package_id == package.id)).first(): add("PACKAGE_ITEMS", "PACKAGE", "BLOCKED", "Package has no explicit items")
    else: add("PACKAGE_ITEMS", "PACKAGE", "PASS", "Package items are explicit", False)
    blocking = [x for x in checks if x[4] and x[2] in {"BLOCKED", "NEEDS_REVIEW", "STALE"}]
    result = "BLOCKED" if blocking else "PASS"
    digital = "BLOCKED" if any(x[1] in {"REQUIREMENTS", "ENGINEERING", "PACKAGE", "PREPARATION"} and x[4] and x[2] != "PASS" for x in checks) else "PASS"
    physical_result = "BLOCKED" if physical_blocked else "PASS"
    run = SubmissionPrecheckRun(authority_case_id=case.id, preparation_revision_id=prep.id, submission_package_id=package.id, policy_version_id=prep.authority_policy_version_id, package_hash=package.manifest_hash or "", result=result, digital_readiness=digital, physical_readiness=physical_result, evaluated_by=actor)
    db.add(run); db.flush()
    for code, category, check_result, message, is_blocking, source_type, source_id in checks:
        db.add(SubmissionPrecheckCheck(precheck_run_id=run.id, code=code, category=category, result=check_result, message=message, blocking=is_blocking, source_type=source_type, source_id=source_id))
    audit(db, correlation_id=_corr(request), event_type="SUBMISSION_PRECHECK_RUN", entity_type="SubmissionPrecheckRun", entity_id=run.id, actor_id=actor, after={"result": result, "package_hash": package.manifest_hash, "digital_readiness": digital, "physical_readiness": physical_result})
    return run


@router.post("/authority-cases/{case_id}/precheck")
def run_precheck(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "PRECHECK_RUN")
    case = _case(db, case_id); package = db.get(SubmissionPackage, payload.get("submission_package_id"))
    if not package or package.authority_case_id != case.id: raise _http(404, "SUBMISSION_PACKAGE_NOT_FOUND")
    prep = db.get(PreparationRevision, package.preparation_revision_id)
    run = _precheck(db, case, prep, package, _actor(request, payload), request); db.commit()
    checks = db.scalars(select(SubmissionPrecheckCheck).where(SubmissionPrecheckCheck.precheck_run_id == run.id)).all()
    return {"run": _row(run), "checks": [_row(x) for x in checks]}


@router.post("/authority-cases/{case_id}/submit/authorize")
def authorize_submission(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "SUBMIT_AUTHORIZE")
    case = _case(db, case_id); package = db.get(SubmissionPackage, payload.get("submission_package_id")); precheck = db.get(SubmissionPrecheckRun, payload.get("precheck_run_id"))
    if not package or package.authority_case_id != case.id or package.state != "LOCKED": raise _http(409, "LOCKED_PACKAGE_REQUIRED")
    if not precheck or precheck.submission_package_id != package.id or precheck.result != "PASS" or precheck.package_hash != package.manifest_hash: raise _http(409, "CURRENT_PRECHECK_PASS_REQUIRED")
    key = str(payload.get("idempotency_key") or "").strip()
    if not key: raise _http(422, "SUBMISSION_IDEMPOTENCY_KEY_REQUIRED")
    prior = db.scalar(select(SubmissionAttempt).where(SubmissionAttempt.idempotency_key == key))
    if prior: return _row(prior)
    attempt_number = (db.scalar(select(func.max(SubmissionAttempt.attempt_number)).where(SubmissionAttempt.authority_case_id == case.id)) or 0) + 1
    attempt = SubmissionAttempt(authority_case_id=case.id, preparation_revision_id=package.preparation_revision_id, submission_package_id=package.id, precheck_run_id=precheck.id, channel_code=str(payload.get("channel_code") or "MANUAL_PORTAL"), attempt_number=attempt_number, idempotency_key=key, authorized_by=_actor(request, payload))
    db.add(attempt); case.status = "PENDING_EXTERNAL_CONFIRMATION"; db.flush(); _lineage(db, case, "SubmissionAttempt", attempt.id, request, upstream_type="SubmissionPrecheckRun", upstream_id=precheck.id, kind="HUMAN_SUBMIT_AUTHORIZATION")
    audit(db, correlation_id=_corr(request), event_type="SUBMISSION_AUTHORIZED_PENDING_EXTERNAL_CONFIRMATION", entity_type="SubmissionAttempt", entity_id=attempt.id, actor_id=attempt.authorized_by, after={"machine_submit_operation": False, "state": attempt.state, "channel": attempt.channel_code}); db.commit(); return _row(attempt)


@router.post("/authority-cases/{case_id}/submit/confirm")
def confirm_external_submission(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "EXTERNAL_CONFIRM")
    case = _case(db, case_id); attempt = db.get(SubmissionAttempt, payload.get("submission_attempt_id"))
    if not attempt or attempt.authority_case_id != case.id: raise _http(404, "SUBMISSION_ATTEMPT_NOT_FOUND")
    existing = db.scalar(select(ExternalSubmissionSnapshot).where(ExternalSubmissionSnapshot.submission_attempt_id == attempt.id))
    if existing:
        cycle = db.scalar(select(AuthoritySubmissionCycle).where(AuthoritySubmissionCycle.external_submission_snapshot_id == existing.id))
        return {"snapshot": _row(existing), "cycle": _row(cycle) if cycle else None}
    source = str(payload.get("confirmation_source") or "MANUAL_CONFIRMED")
    allowed = {"MANUAL_CONFIRMED", "EMAIL_RECEIPT", "IN_PERSON_RECEIPT", "PORTAL_SCREENSHOT", "PORTAL_READBACK", "API_RESPONSE", "AUTHORITY_DOCUMENT"}
    if source not in allowed: raise _http(422, "INVALID_EXTERNAL_CONFIRMATION_SOURCE")
    actor = _actor(request, payload); package = db.get(SubmissionPackage, attempt.submission_package_id)
    snapshot = ExternalSubmissionSnapshot(submission_attempt_id=attempt.id, authority_case_id=case.id, channel_code=attempt.channel_code, package_hash=package.manifest_hash or "", external_reference=payload.get("external_reference"), external_status=str(payload.get("external_status") or "RECEIVED"), external_submitted_at=datetime.fromisoformat(payload["external_submitted_at"]) if payload.get("external_submitted_at") else datetime.now(timezone.utc), confirmation_source=source, evidence_document_version_id=payload.get("evidence_document_version_id"), confirmed_by=actor, notes=payload.get("notes"))
    db.add(snapshot); db.flush()
    next_cycle = (db.scalar(select(func.max(AuthoritySubmissionCycle.cycle_number)).where(AuthoritySubmissionCycle.authority_case_id == case.id)) or 0) + 1
    cycle = AuthoritySubmissionCycle(authority_case_id=case.id, cycle_number=next_cycle, preparation_revision_id=attempt.preparation_revision_id, submission_package_id=attempt.submission_package_id, external_submission_snapshot_id=snapshot.id, status="SUBMITTED_CONFIRMED")
    db.add(cycle); attempt.state = "EXTERNALLY_SUBMITTED_CONFIRMED"; case.status = "SUBMITTED_CONFIRMED"; db.flush()
    if payload.get("identifier_type") and payload.get("identifier_value"):
        db.add(AuthorityCaseIdentifier(authority_case_id=case.id, identifier_type=str(payload["identifier_type"]), value=str(payload["identifier_value"]), issued_by=str(payload.get("identifier_issued_by") or "EXTERNAL_AUTHORITY"), issued_at=snapshot.external_submitted_at))
    _lineage(db, case, "AuthoritySubmissionCycle", cycle.id, request, upstream_type="ExternalSubmissionSnapshot", upstream_id=snapshot.id, kind="EXTERNAL_SUBMISSION_CONFIRMED")
    audit(db, correlation_id=_corr(request), event_type="EXTERNAL_SUBMISSION_CONFIRMED", entity_type="AuthoritySubmissionCycle", entity_id=cycle.id, actor_id=actor, after={"confirmation_source": source, "external_reference": snapshot.external_reference, "machine_submit_operation": False}); db.commit(); return {"snapshot": _row(snapshot), "cycle": _row(cycle)}


@router.post("/authority-cases/{case_id}/findings")
def capture_finding(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "FINDING_MANAGE")
    case = _case(db, case_id); cycle = db.get(AuthoritySubmissionCycle, payload.get("submission_cycle_id")) if payload.get("submission_cycle_id") else None
    if cycle and cycle.authority_case_id != case.id: raise _http(403, "CROSS_CASE_FINDING_DENIED")
    title, raw = str(payload.get("title") or "").strip(), str(payload.get("raw_text") or "").strip()
    if not title or not raw: raise _http(422, "AUTHORITY_FINDING_TEXT_REQUIRED")
    finding = AuthorityCaseFinding(authority_case_id=case.id, submission_cycle_id=cycle.id if cycle else None, source_document_version_id=payload.get("source_document_version_id"), external_finding_id=payload.get("external_finding_id"), category=str(payload.get("category") or "OTHER"), title=title, raw_text=raw, status="OPEN", severity=str(payload.get("severity") or "UNSPECIFIED"), captured_by=_actor(request, payload), engineering_impact=str(payload.get("engineering_impact") or "UNKNOWN"), affected_requirement_instance_id=payload.get("requirement_instance_id"))
    db.add(finding); db.flush(); audit(db, correlation_id=_corr(request), event_type="AUTHORITY_FINDING_CAPTURED", entity_type="AuthorityCaseFinding", entity_id=finding.id, actor_id=finding.captured_by, after={"cycle_id": cycle.id if cycle else None, "category": finding.category}); db.commit(); return _row(finding)


@router.post("/authority-cases/{case_id}/findings/{finding_id}/responses")
def respond_to_finding(case_id: str, finding_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "FINDING_MANAGE")
    finding = db.get(AuthorityCaseFinding, finding_id)
    if not finding or finding.authority_case_id != case_id: raise _http(404, "AUTHORITY_FINDING_NOT_FOUND")
    text = str(payload.get("response_text") or "").strip()
    if not text: raise _http(422, "AUTHORITY_FINDING_RESPONSE_REQUIRED")
    response = AuthorityFindingResponse(finding_id=finding.id, response_text=text, supporting_evidence_json=payload.get("supporting_evidence") or {}, affected_requirement_instance_id=payload.get("requirement_instance_id"), affected_baseline_id=payload.get("baseline_id"), status="PREPARED", prepared_by=_actor(request, payload))
    db.add(response); finding.status = "RESPONSE_IN_PROGRESS"; db.commit(); return _row(response)


@router.post("/authority-cases/{case_id}/outcomes")
def record_outcome(case_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _runtime_role(role, "OUTCOME_RECORD")
    case = _case(db, case_id); cycle = db.get(AuthoritySubmissionCycle, payload.get("submission_cycle_id")) if payload.get("submission_cycle_id") else None
    if cycle and cycle.authority_case_id != case.id: raise _http(403, "CROSS_CASE_OUTCOME_DENIED")
    source_id = payload.get("source_document_version_id") or payload.get("external_submission_snapshot_id")
    if not source_id: raise _http(422, "EXTERNAL_OUTCOME_EVIDENCE_REQUIRED")
    outcome = AuthorityCaseOutcome(authority_case_id=case.id, submission_cycle_id=cycle.id if cycle else None, outcome_type=str(payload.get("outcome_type") or "UNKNOWN"), status="VERIFIED", external_identifier=payload.get("external_identifier"), source_document_version_id=payload.get("source_document_version_id"), evidence_snapshot_json={"source": source_id, "source_kind": "DOCUMENT_VERSION" if payload.get("source_document_version_id") else "EXTERNAL_SUBMISSION_SNAPSHOT"}, issued_at=datetime.fromisoformat(payload["issued_at"]) if payload.get("issued_at") else datetime.now(timezone.utc), verified_by=_actor(request, payload))
    db.add(outcome); case.status = "AUTHORITY_OUTCOME_RECORDED"; db.flush(); audit(db, correlation_id=_corr(request), event_type="AUTHORITY_OUTCOME_RECORDED", entity_type="AuthorityCaseOutcome", entity_id=outcome.id, actor_id=outcome.verified_by, after={"outcome_type": outcome.outcome_type, "construction_start_created": False}); db.commit(); return _row(outcome)
