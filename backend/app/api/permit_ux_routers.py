"""Owner-facing Permit / Authority Case projections.

This module is intentionally a read-model boundary.  Authority-case writes
continue to use the canonical Preparation + Submission Loop routes.
"""

from __future__ import annotations

import csv
import io
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..db import get_db
from ..models import (
    ApprovedDesignBaseline,
    ApprovedDesignBaselineMember,
    AuthorityCase,
    AuthorityCaseFinding,
    AuthorityCaseIdentifier,
    AuthorityCaseOutcome,
    AuthorityCaseSubject,
    AuthorityCasePolicyBinding,
    AuthorityFindingResponse,
    AuthoritySubmissionCycle,
    CaseEvidenceSelection,
    Document,
    DocumentVersion,
    EngineeringDeliverable,
    EngineeringDeliverableRevision,
    EngineeringProfessionalApproval,
    EngineeringProjectMember,
    EngineeringRendition,
    ExternalBody,
    FormInstance,
    GeneratedArtifact,
    Jurisdiction,
    Party,
    PreparationRevision,
    Project,
    ProjectActivation,
    Property,
    PropertyOwnership,
    RegulatoryJourney,
    RequirementInstance,
    Role,
    ServiceType,
    SubmissionAttempt,
    SubmissionPackage,
    SubmissionPrecheckCheck,
    SubmissionPrecheckRun,
    AuditEvent,
)
from ..services.regulatory_context import case_party_context

router = APIRouter(prefix="/api/permit-ux", tags=["permit-ux"])


def _json(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _row(value: Any, *, omit: set[str] | None = None) -> dict[str, Any] | None:
    if value is None:
        return None
    omit = omit or set()
    return {k: _json(v) for k, v in value.__dict__.items() if not k.startswith("_") and k not in omit}


def _actor(request: Request, role: Role) -> str:
    return request.headers.get("X-Dev-Actor") or role.value


def _owner(role: Role) -> bool:
    return role in {Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN}


def _visible_project_ids(db: Session, request: Request, role: Role) -> set[str] | None:
    if _owner(role):
        return None
    actor = _actor(request, role)
    member_ids = set(db.scalars(select(EngineeringProjectMember.project_id).where(EngineeringProjectMember.actor_id == actor, EngineeringProjectMember.status == "ACTIVE")).all())
    assigned_ids = set(db.scalars(select(Project.id).where(Project.assigned_engineer == actor)).all())
    return member_ids | assigned_ids


def _joined_cases(db: Session, request: Request, role: Role):
    visible = _visible_project_ids(db, request, role)
    query = select(AuthorityCase, RegulatoryJourney, Project).join(RegulatoryJourney, RegulatoryJourney.id == AuthorityCase.regulatory_journey_id).join(Project, Project.id == RegulatoryJourney.project_id)
    if visible is not None:
        if not visible:
            return []
        query = query.where(Project.id.in_(visible))
    return db.execute(query.order_by(AuthorityCase.created_at.desc())).all()


def _identifier(db: Session, case_id: str) -> dict[str, Any] | None:
    priorities = {"PERMIT_NUMBER": 0, "LICENSE_NUMBER": 1, "APPLICATION_NUMBER": 2, "OFFICIAL_APPLICATION": 3, "AUTHORITY_CASE": 4}
    rows = db.scalars(select(AuthorityCaseIdentifier).where(AuthorityCaseIdentifier.authority_case_id == case_id, AuthorityCaseIdentifier.active.is_(True)).order_by(AuthorityCaseIdentifier.created_at)).all()
    if not rows:
        return None
    item = sorted(rows, key=lambda x: (priorities.get(x.identifier_type, 99), x.created_at))[0]
    return {"value": item.value, "identifier_type": item.identifier_type, "source_id": item.id}


def _derive_status(case: AuthorityCase, requirements: list[Any], findings: list[Any], packages: list[Any], attempts: list[Any], cycles: list[Any], prechecks: list[Any], precheck_checks: list[Any], outcome: Any) -> dict[str, Any]:
    blocking = [r for r in requirements if r.status in {"MISSING", "NEEDS_REVIEW", "STALE", "BLOCKED"} and r.applicability != "NOT_APPLICABLE"]
    physical_block = any(r.result == "FAIL" and r.blocking for r in precheck_checks)
    package_ready = bool(packages and packages[0].state in {"LOCKED", "READY", "SUBMITTED"})
    latest_attempt = attempts[0] if attempts else None
    latest_cycle = cycles[0] if cycles else None
    if outcome:
        stage = "CLOSED" if case.status == "CLOSED" else "DECISION_RECEIVED"
    elif findings:
        stage = "RESUBMISSION" if cycles else "RESPONSE_REQUIRED"
    elif latest_attempt and latest_attempt.state == "PENDING_EXTERNAL_CONFIRMATION":
        stage = "PENDING_EXTERNAL_CONFIRMATION"
    elif latest_cycle and latest_cycle.status in {"SUBMITTED_CONFIRMED", "UNDER_REVIEW", "RECEIVED"}:
        stage = "SUBMITTED"
    elif prechecks and prechecks[0].result in {"BLOCKED", "FAIL"}:
        stage = "PRECHECK"
    elif package_ready:
        stage = "READY_TO_SUBMIT"
    elif packages or case.status in {"PREPARING", "REQUIREMENTS_NOT_CONFIGURED"}:
        stage = "PREPARING"
    elif requirements:
        stage = "REQUIREMENTS"
    else:
        stage = "SETUP"
    if outcome and case.status == "CLOSED":
        system_status = "CLOSED"
    elif blocking or physical_block:
        system_status = "BLOCKED"
    elif findings:
        system_status = "NEEDS_ACTION"
    elif latest_attempt and latest_attempt.state == "PENDING_EXTERNAL_CONFIRMATION":
        system_status = "WAITING_EXTERNAL"
    elif any(r.status == "STALE" for r in requirements):
        system_status = "STALE"
    else:
        system_status = "ON_TRACK"
    return {
        "stage": stage,
        "system_status": system_status,
        "blockers": [{"source": "RequirementInstance", "id": r.id, "reason": r.reason, "status": r.status} for r in blocking] + ([{"source": "SubmissionPrecheckRun", "reason": "A blocking precheck failed"}] if physical_block else []),
        "block_count": len(blocking) + (1 if physical_block else 0),
        "open_comments": len(findings),
        "latest_external_status": latest_cycle.status if latest_cycle else None,
        "end_date": None,
        "end_date_state": "NOT_CONFIGURED",
    }


def _status_projection(db: Session, case: AuthorityCase) -> dict[str, Any]:
    requirements = db.scalars(select(RequirementInstance).where(RequirementInstance.authority_case_id == case.id)).all()
    findings = db.scalars(select(AuthorityCaseFinding).where(AuthorityCaseFinding.authority_case_id == case.id, AuthorityCaseFinding.status.not_in({"CLOSED", "RESOLVED"}))).all()
    packages = db.scalars(select(SubmissionPackage).where(SubmissionPackage.authority_case_id == case.id).order_by(SubmissionPackage.created_at.desc())).all()
    attempts = db.scalars(select(SubmissionAttempt).where(SubmissionAttempt.authority_case_id == case.id).order_by(SubmissionAttempt.authorized_at.desc())).all()
    cycles = db.scalars(select(AuthoritySubmissionCycle).where(AuthoritySubmissionCycle.authority_case_id == case.id).order_by(AuthoritySubmissionCycle.cycle_number.desc())).all()
    prechecks = db.scalars(select(SubmissionPrecheckRun).where(SubmissionPrecheckRun.authority_case_id == case.id).order_by(SubmissionPrecheckRun.evaluated_at.desc())).all()
    checks = db.scalars(select(SubmissionPrecheckCheck).where(SubmissionPrecheckCheck.precheck_run_id.in_([x.id for x in prechecks[:1]])) if prechecks else select(SubmissionPrecheckCheck).where(False)).all()
    outcome = db.scalar(select(AuthorityCaseOutcome).where(AuthorityCaseOutcome.authority_case_id == case.id).order_by(AuthorityCaseOutcome.created_at.desc()))
    return _derive_status(case, requirements, findings, packages, attempts, cycles, prechecks, checks, outcome)


def _bulk_status_projection(db: Session, cases: list[AuthorityCase]) -> dict[str, dict[str, Any]]:
    ids = [x.id for x in cases]
    grouped: dict[str, dict[str, list[Any]]] = {x: {"requirements": [], "findings": [], "packages": [], "attempts": [], "cycles": [], "prechecks": [], "outcomes": []} for x in ids}
    if not ids:
        return {}
    for row in db.scalars(select(RequirementInstance).where(RequirementInstance.authority_case_id.in_(ids))).all(): grouped[row.authority_case_id]["requirements"].append(row)
    for row in db.scalars(select(AuthorityCaseFinding).where(AuthorityCaseFinding.authority_case_id.in_(ids), AuthorityCaseFinding.status.not_in({"CLOSED", "RESOLVED"}))).all(): grouped[row.authority_case_id]["findings"].append(row)
    for model, key in [(SubmissionPackage, "packages"), (SubmissionAttempt, "attempts"), (AuthoritySubmissionCycle, "cycles"), (SubmissionPrecheckRun, "prechecks")]:
        for row in db.scalars(select(model).where(model.authority_case_id.in_(ids))).all(): grouped[row.authority_case_id][key].append(row)
    for row in db.scalars(select(AuthorityCaseOutcome).where(AuthorityCaseOutcome.authority_case_id.in_(ids))).all(): grouped[row.authority_case_id]["outcomes"].append(row)
    precheck_ids = [x.id for values in grouped.values() for x in values["prechecks"]]
    checks = db.scalars(select(SubmissionPrecheckCheck).where(SubmissionPrecheckCheck.precheck_run_id.in_(precheck_ids)) if precheck_ids else select(SubmissionPrecheckCheck).where(False)).all()
    checks_by_run: dict[str, list[Any]] = {}
    for row in checks: checks_by_run.setdefault(row.precheck_run_id, []).append(row)
    output = {}
    for case in cases:
        values = grouped[case.id]
        values["packages"].sort(key=lambda x: x.created_at, reverse=True); values["attempts"].sort(key=lambda x: x.authorized_at, reverse=True); values["cycles"].sort(key=lambda x: x.cycle_number, reverse=True); values["prechecks"].sort(key=lambda x: x.evaluated_at, reverse=True); values["outcomes"].sort(key=lambda x: x.created_at, reverse=True)
        output[case.id] = _derive_status(case, values["requirements"], values["findings"], values["packages"], values["attempts"], values["cycles"], values["prechecks"], checks_by_run.get(values["prechecks"][0].id, []) if values["prechecks"] else [], values["outcomes"][0] if values["outcomes"] else None)
    return output


def _case_access(db: Session, request: Request, role: Role, case_id: str) -> tuple[AuthorityCase, RegulatoryJourney, Project]:
    row = db.execute(select(AuthorityCase, RegulatoryJourney, Project).join(RegulatoryJourney, RegulatoryJourney.id == AuthorityCase.regulatory_journey_id).join(Project, Project.id == RegulatoryJourney.project_id).where(AuthorityCase.id == case_id)).first()
    if not row:
        raise HTTPException(status_code=404, detail={"code": "AUTHORITY_CASE_NOT_FOUND"})
    case, journey, project = row
    visible = _visible_project_ids(db, request, role)
    if visible is not None and project.id not in visible:
        raise HTTPException(status_code=404, detail={"code": "AUTHORITY_CASE_NOT_FOUND"})
    return case, journey, project


def _catalog_row(item: Any) -> dict[str, Any]:
    return {"id": item.id, "code": item.code, "name_en": item.name_en, "name_ar": getattr(item, "name_ar", None)}


@router.get("/portfolio")
def portfolio(request: Request, q: str | None = None, lane: str | None = None, stage: str | None = None, system_status: str | None = None, external_body_id: str | None = None, service_type_id: str | None = None, has_blockers: bool | None = None, has_open_comments: bool | None = None, page: int = 1, page_size: int = 25, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    if role not in {Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN, Role.PROCESS_CHAMPION, Role.RESPONSIBLE_ENGINEER, Role.REQUIREMENT_STEWARD, Role.PERMIT_PREPARER}:
        raise HTTPException(status_code=403, detail={"code": "CAPABILITY_DENIED", "capability": "CASE_READ"})
    page = max(1, page); page_size = min(100, max(1, page_size))
    joined = _joined_cases(db, request, role)
    cases = [row[0] for row in joined]
    statuses = _bulk_status_projection(db, cases)
    body_ids = {x.external_body_id for x in cases}; service_ids = {x.service_type_id for x in cases}
    bodies = {x.id: x for x in db.scalars(select(ExternalBody).where(ExternalBody.id.in_(body_ids)) if body_ids else select(ExternalBody).where(False)).all()}
    services = {x.id: x for x in db.scalars(select(ServiceType).where(ServiceType.id.in_(service_ids)) if service_ids else select(ServiceType).where(False)).all()}
    case_ids = [x.id for x in cases]
    identifiers = db.scalars(select(AuthorityCaseIdentifier).where(AuthorityCaseIdentifier.authority_case_id.in_(case_ids), AuthorityCaseIdentifier.active.is_(True)).order_by(AuthorityCaseIdentifier.created_at)) if case_ids else []
    identifier_map: dict[str, list[Any]] = {}
    for identifier in identifiers: identifier_map.setdefault(identifier.authority_case_id, []).append(identifier)
    rows: list[dict[str, Any]] = []
    for case, journey, project in joined:
        if external_body_id and case.external_body_id != external_body_id: continue
        if service_type_id and case.service_type_id != service_type_id: continue
        if q and q.lower() not in " ".join([project.project_name, project.project_number, case.case_reference]).lower(): continue
        status = statuses[case.id]
        if stage and status["stage"] != stage: continue
        if system_status and status["system_status"] != system_status: continue
        if has_blockers is not None and bool(status["block_count"]) != has_blockers: continue
        if has_open_comments is not None and bool(status["open_comments"]) != has_open_comments: continue
        if lane == "NEED_ACTION" and status["system_status"] not in {"NEEDS_ACTION", "BLOCKED", "STALE"}: continue
        if lane == "AUTHORITY_REVIEW" and status["stage"] not in {"PENDING_EXTERNAL_CONFIRMATION", "SUBMITTED"}: continue
        if lane == "READY_CLOSE" and status["stage"] not in {"READY_TO_SUBMIT", "DECISION_RECEIVED", "CLOSED"}: continue
        priority = {"PERMIT_NUMBER": 0, "LICENSE_NUMBER": 1, "APPLICATION_NUMBER": 2, "OFFICIAL_APPLICATION": 3, "AUTHORITY_CASE": 4}
        matching = sorted(identifier_map.get(case.id, []), key=lambda x: (priority.get(x.identifier_type, 99), x.created_at))
        identifier = {"value": matching[0].value, "identifier_type": matching[0].identifier_type, "source_id": matching[0].id} if matching else None
        body = bodies.get(case.external_body_id); service = services.get(case.service_type_id)
        rows.append({"case_id": case.id, "project_id": project.id, "project_name": project.project_name, "project_reference": project.project_number, "case_reference": case.case_reference, "journey_id": journey.id, "journey_code": journey.journey_code, "permit_identifier": identifier, "external_body": _catalog_row(body) if body else None, "service_type": _catalog_row(service) if service else None, "authority_status": case.status, **status})
    total = len(rows)
    start = (page - 1) * page_size
    return {"items": rows[start:start + page_size], "page": page, "page_size": page_size, "total": total, "lanes": {"all": total, "need_action": sum(x["system_status"] in {"NEEDS_ACTION", "BLOCKED", "STALE"} for x in rows), "authority_review": sum(x["stage"] in {"PENDING_EXTERNAL_CONFIRMATION", "SUBMITTED"} for x in rows), "ready_close": sum(x["stage"] in {"READY_TO_SUBMIT", "DECISION_RECEIVED", "CLOSED"} for x in rows)}}


@router.get("/new/context")
def new_context(request: Request, project_id: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    if not _owner(role):
        raise HTTPException(status_code=403, detail={"code": "CAPABILITY_DENIED", "capability": "CASE_CREATE"})
    projects = db.scalars(select(Project).where(Project.activated_at.is_not(None)).order_by(Project.project_number)).all()
    selected = db.get(Project, project_id) if project_id else None
    if selected and not selected.activated_at:
        raise HTTPException(status_code=409, detail={"code": "PROJECT_NOT_ACTIVATED"})
    journeys = db.scalars(select(RegulatoryJourney).where(RegulatoryJourney.project_id == selected.id).order_by(RegulatoryJourney.created_at.desc())).all() if selected else []
    return {"projects": [{"id": p.id, "project_reference": p.project_number, "project_name": p.project_name, "municipality": p.municipality, "permit_type": p.permit_type} for p in projects], "selected_project": {"id": selected.id, "project_reference": selected.project_number, "project_name": selected.project_name, "municipality": selected.municipality, "permit_type": selected.permit_type} if selected else None, "journeys": [_row(x) for x in journeys], "external_bodies": [_catalog_row(x) for x in db.scalars(select(ExternalBody).where(ExternalBody.status == "ACTIVE").order_by(ExternalBody.name_en)).all()], "jurisdictions": [_catalog_row(x) for x in db.scalars(select(Jurisdiction).where(Jurisdiction.status == "ACTIVE").order_by(Jurisdiction.name_en)).all()], "service_types": [_catalog_row(x) for x in db.scalars(select(ServiceType).where(ServiceType.status == "ACTIVE").order_by(ServiceType.name_en)).all()], "accepted_scope_suggestions": [], "scope_note": "Accepted proposal scope is advisory; explicit authority selection is required."}


@router.get("/cases/{case_id}")
def case_workspace(case_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    case, journey, project = _case_access(db, request, role, case_id)
    body = db.get(ExternalBody, case.external_body_id); jurisdiction = db.get(Jurisdiction, case.jurisdiction_id); service = db.get(ServiceType, case.service_type_id)
    requirements = db.scalars(select(RequirementInstance).where(RequirementInstance.authority_case_id == case.id).order_by(RequirementInstance.created_at)).all()
    selections = db.scalars(select(CaseEvidenceSelection).where(CaseEvidenceSelection.authority_case_id == case.id).order_by(CaseEvidenceSelection.selected_at.desc())).all()
    documents = db.scalars(select(Document).where(Document.project_id == project.id).order_by(Document.updated_at.desc())).all()
    doc_ids = [x.id for x in documents]
    versions = db.scalars(select(DocumentVersion).where(DocumentVersion.document_id.in_(doc_ids)) if doc_ids else select(DocumentVersion).where(False)).all()
    prep = db.scalars(select(PreparationRevision).where(PreparationRevision.authority_case_id == case.id).order_by(PreparationRevision.authority_revision_number)).all()
    packages = db.scalars(select(SubmissionPackage).where(SubmissionPackage.authority_case_id == case.id).order_by(SubmissionPackage.created_at)).all()
    attempts = db.scalars(select(SubmissionAttempt).where(SubmissionAttempt.authority_case_id == case.id).order_by(SubmissionAttempt.authorized_at)).all()
    cycles = db.scalars(select(AuthoritySubmissionCycle).where(AuthoritySubmissionCycle.authority_case_id == case.id).order_by(AuthoritySubmissionCycle.cycle_number)).all()
    findings = db.scalars(select(AuthorityCaseFinding).where(AuthorityCaseFinding.authority_case_id == case.id).order_by(AuthorityCaseFinding.created_at)).all()
    outcomes = db.scalars(select(AuthorityCaseOutcome).where(AuthorityCaseOutcome.authority_case_id == case.id).order_by(AuthorityCaseOutcome.created_at)).all()
    forms = db.scalars(select(FormInstance).where(FormInstance.context_type == "AuthorityCase", FormInstance.context_id == case.id).order_by(FormInstance.created_at)).all()
    baselines = db.scalars(select(ApprovedDesignBaseline).where(ApprovedDesignBaseline.project_id == project.id, ApprovedDesignBaseline.status == "APPROVED").order_by(ApprovedDesignBaseline.approved_at.desc())).all()
    baseline_ids = [x.id for x in baselines]
    members = db.scalars(select(ApprovedDesignBaselineMember).where(ApprovedDesignBaselineMember.baseline_id.in_(baseline_ids)) if baseline_ids else select(ApprovedDesignBaselineMember).where(False)).all()
    rev_ids = [x.revision_id for x in members]
    revisions = {x.id: x for x in db.scalars(select(EngineeringDeliverableRevision).where(EngineeringDeliverableRevision.id.in_(rev_ids)) if rev_ids else select(EngineeringDeliverableRevision).where(False)).all()}
    deliverable_ids = [x.deliverable_id for x in revisions.values()]
    deliverables = {x.id: x for x in db.scalars(select(EngineeringDeliverable).where(EngineeringDeliverable.id.in_(deliverable_ids)) if deliverable_ids else select(EngineeringDeliverable).where(False)).all()}
    rendition_ids = [x.rendition_id for x in members]
    renditions = {x.id: x for x in db.scalars(select(EngineeringRendition).where(EngineeringRendition.id.in_(rendition_ids)) if rendition_ids else select(EngineeringRendition).where(False)).all()}
    approvals = {x.revision_id: x for x in db.scalars(select(EngineeringProfessionalApproval).where(EngineeringProfessionalApproval.revision_id.in_(rev_ids)) if rev_ids else select(EngineeringProfessionalApproval).where(False)).all()}
    party_ids = [x.party_id for x in db.scalars(select(PropertyOwnership).join(Property, Property.id == PropertyOwnership.property_id).where(Property.project_id == project.id)).all()]
    parties = db.scalars(select(Party).where(Party.id.in_(party_ids)) if party_ids else select(Party).where(False)).all()
    properties = db.scalars(select(Property).where(Property.project_id == project.id)).all()
    audit = db.scalars(select(AuditEvent).where(or_(and_(AuditEvent.entity_type == "AuthorityCase", AuditEvent.entity_id == case.id), and_(AuditEvent.entity_type == "Project", AuditEvent.entity_id == project.id))).order_by(AuditEvent.created_at.desc()).limit(100)).all()
    status = _status_projection(db, case)
    drawing_items = []
    for member in members:
        revision = revisions.get(member.revision_id); rendition = renditions.get(member.rendition_id); deliverable = deliverables.get(revision.deliverable_id) if revision else None
        drawing_items.append({"baseline": _row(next((b for b in baselines if b.id == member.baseline_id), None)), "member": _row(member), "deliverable": _row(deliverable), "revision": _row(revision), "rendition": _row(rendition), "professional_approval": _row(approvals.get(member.revision_id)), "review_category": None, "review_category_state": "CANONICAL_FIELD_NOT_AVAILABLE", "discipline": getattr(deliverable, "discipline", None)})
    finding_rows = []
    for finding in findings:
        responses = db.scalars(select(AuthorityFindingResponse).where(AuthorityFindingResponse.finding_id == finding.id).order_by(AuthorityFindingResponse.created_at)).all()
        finding_rows.append({"finding": _row(finding), "responses": [_row(x) for x in responses], "ai_boundary": "ADVISORY_ONLY"})
    subject = db.scalar(select(AuthorityCaseSubject).where(AuthorityCaseSubject.authority_case_id == case.id))
    return {"case": _row(case), "journey": _row(journey), "project": _row(project, omit={"office"}), "external_body": _row(body), "jurisdiction": _row(jurisdiction), "service_type": _row(service), "status": status, "permit_identifier": _identifier(db, case.id), "subject": _row(subject) if subject else {"subject_type": case.subject_type or "Project", "subject_id": case.subject_id or project.id}, "parties_representation": case_party_context(db, case), "project_details": {"projects": [_row(project, omit={"office"})], "properties": [_row(x) for x in properties], "parties": [{**_row(x), "identifier_value": "••••" if x.identifier_value else None} for x in parties], "sensitive_fields": "Masked by default; provenance remains available through source records."}, "requirements": [_row(x) for x in requirements], "evidence": [_row(x) for x in selections], "documents": [{"document": _row(x), "versions": [_row(v, omit={"synthetic_content"}) for v in versions if v.document_id == x.id]} for x in documents], "drawings": drawing_items, "forms": [{"form": _row(x), "generated_artifacts": [_row(a) for a in db.scalars(select(GeneratedArtifact).where(GeneratedArtifact.form_instance_id == x.id)).all()]} for x in forms], "comments": finding_rows, "submission_history": {"preparations": [_row(x, omit={"authority_snapshot_json"}) for x in prep], "packages": [_row(x, omit={"manifest_json"}) for x in packages], "attempts": [_row(x) for x in attempts], "cycles": [_row(x) for x in cycles]}, "permit_license": {"outcomes": [_row(x, omit={"evidence_snapshot_json"}) for x in outcomes], "system_summary": True, "official_document_available": any(x.source_document_version_id for x in outcomes)}, "history": [_row(x) for x in audit], "next_action": "Resolve blockers before precheck" if status["block_count"] else ("Review open authority comments" if status["open_comments"] else "No immediate action")}


@router.get("/exports/permit-tracker.csv")
def export_tracker(request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    if not _owner(role):
        raise HTTPException(status_code=403, detail={"code": "EXPORT_NOT_AUTHORIZED"})
    projection = portfolio(request=request, db=db, role=role)
    output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=["project_reference", "project_name", "permit_number", "case_reference", "stage", "system_status", "block_count", "open_comments", "external_body", "service_type", "end_date"])
    writer.writeheader()
    for item in projection["items"]:
        writer.writerow({"project_reference": item["project_reference"], "project_name": item["project_name"], "permit_number": (item["permit_identifier"] or {}).get("value", "Pending"), "case_reference": item["case_reference"], "stage": item["stage"], "system_status": item["system_status"], "block_count": item["block_count"], "open_comments": item["open_comments"], "external_body": (item["external_body"] or {}).get("name_en", ""), "service_type": (item["service_type"] or {}).get("name_en", ""), "end_date": item["end_date"] or "Not configured"})
    headers = {"Content-Disposition": "attachment; filename=permit-tracker.csv", "X-Export-Lineage": "permit-ux-portfolio-projection", "X-Export-Idempotency": "deterministic-filtered-projection"}
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers=headers)
