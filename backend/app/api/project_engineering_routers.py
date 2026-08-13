"""Project Engineering APIs.

This router is intentionally project-scoped and exact-reference based.  It
does not create authority approval, submission packages, or construction
release records.
"""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..models import (
    ApprovedDesignBaseline, ApprovedDesignBaselineMember, Document, DocumentApprovalState,
    DocumentType, DocumentVersion, DesignChangeRequest, EngineeringCalculationRecord,
    EngineeringDeliverable, EngineeringDeliverableRevision, EngineeringMaterialTest,
    EngineeringProfessionalApproval, EngineeringProjectMember, EngineeringRendition,
    EngineeringReviewFinding, EngineeringTechnicalCheck, EngineeringWorkPackage,
    LineageEdge, ProfessionalCredential, Project, ProjectEngineeringReview, Role, TechnicalRule, TechnicalRuleSetVersion,
)
from ..services.backend_realignment import domain_error, require_capability


router = APIRouter(prefix="/api")


def _corr(request: Request) -> str:
    return getattr(request.state, "correlation_id", str(uuid4()))


def _actor(request: Request, payload: dict[str, Any] | None = None) -> str:
    return request.headers.get("X-Dev-Actor") or str((payload or {}).get("actor") or "role-actor")


def _json(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if hasattr(value, "value"):
        return value.value
    return value


def _row(item: Any) -> dict[str, Any]:
    return {key: _json(value) for key, value in item.__dict__.items() if not key.startswith("_")}


def _project(db: Session, project_id: str) -> Project:
    item = db.get(Project, project_id)
    if not item:
        raise domain_error(404, "PROJECT_NOT_FOUND", project_id=project_id)
    return item


def _active_project(db: Session, project_id: str) -> Project:
    project = _project(db, project_id)
    if not project.activated_at:
        raise domain_error(409, "ENGINEERING_APPROVED_DESIGN_BASELINE_BLOCKED_BY_PROJECT_ACTIVATION", project_id=project_id)
    return project


def _authorized(db: Session, project_id: str, role: Role, actor: str, capability: str = "ENGINEERING_PROJECT_READ") -> str:
    persona = require_capability(role, capability)
    members = db.scalars(select(EngineeringProjectMember).where(EngineeringProjectMember.project_id == project_id, EngineeringProjectMember.status == "ACTIVE")).all()
    if persona == "ENGINEERING" and members and not any(m.actor_id in {actor, role.value} for m in members):
        raise domain_error(403, "ENGINEERING_PROJECT_ACCESS_DENIED", project_id=project_id, actor=actor)
    return persona


def _lineage(db: Session, project_id: str, upstream_type: str, upstream_id: str, downstream_type: str, downstream_id: str, kind: str, request: Request, version: str | None = None) -> None:
    db.add(LineageEdge(project_id=project_id, upstream_type=upstream_type, upstream_id=upstream_id, upstream_version_or_hash=version, downstream_type=downstream_type, downstream_id=downstream_id, dependency_kind=kind, correlation_id=_corr(request)))


def _revision(db: Session, revision_id: str) -> EngineeringDeliverableRevision:
    item = db.get(EngineeringDeliverableRevision, revision_id)
    if not item:
        raise domain_error(404, "ENGINEERING_REVISION_NOT_FOUND", revision_id=revision_id)
    return item


def _revision_project(db: Session, revision_id: str, project_id: str) -> EngineeringDeliverableRevision:
    item = _revision(db, revision_id)
    if item.project_id != project_id:
        raise domain_error(409, "ENGINEERING_REVISION_PROJECT_MISMATCH", project_id=project_id, revision_project_id=item.project_id)
    return item


def _require_mutable(revision: EngineeringDeliverableRevision) -> None:
    if revision.approval_status == "PROFESSIONALLY_APPROVED" or revision.immutable_at:
        raise domain_error(409, "APPROVED_ENGINEERING_REVISION_IMMUTABLE", revision_id=revision.id, action="CREATE_NEW_REVISION")


def _active_findings(db: Session, revision_id: str) -> list[EngineeringReviewFinding]:
    return db.scalars(select(EngineeringReviewFinding).join(ProjectEngineeringReview, ProjectEngineeringReview.id == EngineeringReviewFinding.review_id).where(ProjectEngineeringReview.revision_id == revision_id, EngineeringReviewFinding.status.in_(["OPEN", "RESPONDED"]), EngineeringReviewFinding.severity.in_(["BLOCKING", "CRITICAL", "MAJOR"]))).all()


@router.get("/projects/{project_id}/engineering")
def engineering_summary(project_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _project(db, project_id)
    _authorized(db, project_id, role, _actor(request))
    packages = db.scalars(select(EngineeringWorkPackage).where(EngineeringWorkPackage.project_id == project.id).order_by(EngineeringWorkPackage.created_at)).all()
    deliverables = db.scalars(select(EngineeringDeliverable).where(EngineeringDeliverable.project_id == project.id).order_by(EngineeringDeliverable.created_at)).all()
    baselines = db.scalars(select(ApprovedDesignBaseline).where(ApprovedDesignBaseline.project_id == project.id).order_by(ApprovedDesignBaseline.created_at)).all()
    return {"project": {"id": project.id, "project_number": project.project_number, "project_name": project.project_name, "activated": bool(project.activated_at)}, "work_packages": [_row(x) for x in packages], "deliverables": [_row(x) for x in deliverables], "baselines": [_row(x) for x in baselines], "authority_approval_created": False, "construction_release_created": False, "submission_package_created": False}


@router.post("/projects/{project_id}/engineering/members")
def add_member(project_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id)
    actor = _actor(request, payload)
    _authorized(db, project_id, role, actor, "ENGINEERING_PROJECT_EDIT")
    member_actor = str(payload.get("actor_id") or "").strip()
    if not member_actor:
        raise domain_error(422, "ENGINEERING_MEMBER_ACTOR_REQUIRED")
    existing = db.scalar(select(EngineeringProjectMember).where(EngineeringProjectMember.project_id == project.id, EngineeringProjectMember.actor_id == member_actor))
    if existing:
        return _row(existing)
    item = EngineeringProjectMember(project_id=project.id, actor_id=member_actor, capability=str(payload.get("capability") or "ENGINEERING_EDIT"), added_by=actor)
    db.add(item); db.flush(); audit(db, correlation_id=_corr(request), event_type="ENGINEERING_PROJECT_MEMBER_ADDED", entity_type="EngineeringProjectMember", entity_id=item.id, actor_id=actor, after=_row(item)); db.commit()
    return _row(item)


@router.get("/projects/{project_id}/engineering/work-packages")
def list_work_packages(project_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _project(db, project_id); _authorized(db, project_id, role, _actor(request))
    return [_row(x) for x in db.scalars(select(EngineeringWorkPackage).where(EngineeringWorkPackage.project_id == project.id).order_by(EngineeringWorkPackage.created_at)).all()]


@router.post("/projects/{project_id}/engineering/work-packages")
def create_work_package(project_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_PROJECT_EDIT")
    idem = payload.get("idempotency_key")
    if idem:
        existing = db.scalar(select(EngineeringWorkPackage).where(EngineeringWorkPackage.idempotency_key == str(idem)))
        if existing: return _row(existing)
    ref = str(payload.get("package_ref") or "").strip()
    if not ref or not payload.get("title"):
        raise domain_error(422, "ENGINEERING_WORK_PACKAGE_FIELDS_REQUIRED")
    item = EngineeringWorkPackage(project_id=project.id, package_ref=ref, title=str(payload["title"]), discipline=str(payload.get("discipline") or "GENERAL"), owner_actor=actor, metadata_json=payload.get("metadata") or {}, idempotency_key=str(idem) if idem else None)
    db.add(item); db.flush(); audit(db, correlation_id=_corr(request), event_type="ENGINEERING_WORK_PACKAGE_CREATED", entity_type="EngineeringWorkPackage", entity_id=item.id, actor_id=actor, after=_row(item)); db.commit()
    return _row(item)


@router.post("/projects/{project_id}/engineering/deliverables")
def create_deliverable(project_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_PROJECT_EDIT")
    package = db.get(EngineeringWorkPackage, payload.get("work_package_id"))
    if not package or package.project_id != project.id: raise domain_error(409, "ENGINEERING_WORK_PACKAGE_PROJECT_MISMATCH")
    ref = str(payload.get("deliverable_ref") or "").strip()
    if not ref or not payload.get("title"): raise domain_error(422, "ENGINEERING_DELIVERABLE_FIELDS_REQUIRED")
    existing = db.scalar(select(EngineeringDeliverable).where(EngineeringDeliverable.work_package_id == package.id, EngineeringDeliverable.deliverable_ref == ref))
    if existing: return _row(existing)
    item = EngineeringDeliverable(project_id=project.id, work_package_id=package.id, deliverable_ref=ref, title=str(payload["title"]), discipline=str(payload.get("discipline") or package.discipline), deliverable_type=str(payload.get("deliverable_type") or "ENGINEERING_DOCUMENT"), created_by=actor)
    db.add(item); db.flush(); audit(db, correlation_id=_corr(request), event_type="ENGINEERING_DELIVERABLE_CREATED", entity_type="EngineeringDeliverable", entity_id=item.id, actor_id=actor, after=_row(item)); db.commit()
    return _row(item)


@router.post("/projects/{project_id}/engineering/deliverables/{deliverable_id}/revisions")
def create_revision(project_id: str, deliverable_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_PROJECT_EDIT")
    deliverable = db.get(EngineeringDeliverable, deliverable_id)
    if not deliverable or deliverable.project_id != project.id: raise domain_error(409, "ENGINEERING_DELIVERABLE_PROJECT_MISMATCH")
    if payload.get("idempotency_key"):
        existing = db.scalar(select(EngineeringDeliverableRevision).where(EngineeringDeliverableRevision.idempotency_key == str(payload["idempotency_key"])))
        if existing: return _row(existing)
    previous = db.get(EngineeringDeliverableRevision, payload.get("supersedes_revision_id")) if payload.get("supersedes_revision_id") else None
    if previous and (previous.deliverable_id != deliverable.id or previous.project_id != project.id): raise domain_error(409, "ENGINEERING_SUPERSEDES_PROJECT_MISMATCH")
    sequence = int(payload.get("sequence") or ((db.scalar(select(func.max(EngineeringDeliverableRevision.sequence)).where(EngineeringDeliverableRevision.deliverable_id == deliverable.id)) or 0) + 1))
    code = str(payload.get("revision_code") or f"R{sequence}")
    if db.scalar(select(EngineeringDeliverableRevision).where(EngineeringDeliverableRevision.deliverable_id == deliverable.id, EngineeringDeliverableRevision.revision_code == code)): raise domain_error(409, "ENGINEERING_REVISION_CODE_EXISTS")
    item = EngineeringDeliverableRevision(project_id=project.id, deliverable_id=deliverable.id, revision_code=code, sequence=sequence, title=str(payload.get("title") or deliverable.title), issue_purpose=str(payload.get("issue_purpose") or "FOR_REVIEW"), prepared_by=actor, supersedes_revision_id=previous.id if previous else None, idempotency_key=str(payload["idempotency_key"]) if payload.get("idempotency_key") else None)
    db.add(item); db.flush(); deliverable.current_revision_id = item.id; deliverable.status = "IN_PROGRESS"; _lineage(db, project.id, "EngineeringDeliverableRevision", previous.id if previous else deliverable.id, "EngineeringDeliverableRevision", item.id, "ENGINEERING_REVISION_SUPERSEDES" if previous else "ENGINEERING_REVISION_CREATED", request); audit(db, correlation_id=_corr(request), event_type="ENGINEERING_DELIVERABLE_REVISION_CREATED", entity_type="EngineeringDeliverableRevision", entity_id=item.id, actor_id=actor, after=_row(item)); db.commit()
    return _row(item)


@router.post("/projects/{project_id}/engineering/revisions/{revision_id}/ingest")
def ingest_rendition(project_id: str, revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_PROJECT_EDIT")
    revision = _revision_project(db, revision_id, project.id); _require_mutable(revision)
    kind = str(payload.get("rendition_kind") or "").upper()
    if kind not in {"NATIVE", "PUBLISHED"}: raise domain_error(422, "ENGINEERING_RENDITION_KIND_INVALID")
    content = str(payload.get("synthetic_content") or "ENGINEERING SYNTHETIC CONTENT").encode()
    digest = hashlib.sha256(content).hexdigest()
    document = Document(project_id=project.id, document_type=DocumentType.DRAWING_SET, logical_name=str(payload.get("filename") or f"{revision.revision_code}-{kind}"), language=str(payload.get("language") or "en"), source_system="PROJECT_ENGINEERING")
    db.add(document); db.flush()
    version = DocumentVersion(document_id=document.id, version_number=1, source_filename=str(payload.get("filename") or f"{revision.revision_code.lower()}-{kind.lower()}.bin"), source_path_or_reference=f"db://document-versions/{document.id}", sha256=digest, mime_type=str(payload.get("mime_type") or "application/octet-stream"), file_size=len(content), language=document.language, revision_label=revision.revision_code, approval_state=DocumentApprovalState.WORKING, source_system="PROJECT_ENGINEERING", synthetic_content=content, metadata_json={"engineering_project_id": project.id, "rendition_kind": kind})
    db.add(version); db.flush(); document.current_version_id = version.id
    rendition = EngineeringRendition(project_id=project.id, revision_id=revision.id, document_version_id=version.id, rendition_kind=kind, content_hash=digest, renderer_type=payload.get("renderer_type"), renderer_version=payload.get("renderer_version"), created_by=actor)
    db.add(rendition); db.flush(); _lineage(db, project.id, "DocumentVersion", version.id, "EngineeringRendition", rendition.id, "EXACT_RENDITION_BINARY", request, digest); audit(db, correlation_id=_corr(request), event_type="ENGINEERING_RENDITION_INGESTED", entity_type="EngineeringRendition", entity_id=rendition.id, actor_id=actor, after={**_row(rendition), "document_version_id": version.id}); db.commit()
    return {"rendition": _row(rendition), "document_version": {"id": version.id, "sha256": version.sha256, "filename": version.source_filename, "mime_type": version.mime_type}}


@router.post("/projects/{project_id}/engineering/revisions/{revision_id}/renditions")
def attach_rendition(project_id: str, revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_PROJECT_EDIT")
    revision = _revision_project(db, revision_id, project.id); _require_mutable(revision)
    version = db.get(DocumentVersion, payload.get("document_version_id"))
    if not version: raise domain_error(404, "DOCUMENT_VERSION_NOT_FOUND")
    document = db.get(Document, version.document_id)
    if document.project_id != project.id: raise domain_error(409, "ENGINEERING_DOCUMENT_PROJECT_MISMATCH")
    kind = str(payload.get("rendition_kind") or "").upper()
    if kind not in {"NATIVE", "PUBLISHED"}: raise domain_error(422, "ENGINEERING_RENDITION_KIND_INVALID")
    if db.scalar(select(EngineeringRendition).where(EngineeringRendition.revision_id == revision.id, EngineeringRendition.rendition_kind == kind)): raise domain_error(409, "ENGINEERING_RENDITION_KIND_EXISTS")
    rendition = EngineeringRendition(project_id=project.id, revision_id=revision.id, document_version_id=version.id, rendition_kind=kind, content_hash=version.sha256, renderer_type=payload.get("renderer_type"), renderer_version=payload.get("renderer_version"), created_by=actor)
    db.add(rendition); db.flush(); _lineage(db, project.id, "DocumentVersion", version.id, "EngineeringRendition", rendition.id, "EXACT_RENDITION_BINARY", request, version.sha256); db.commit()
    return _row(rendition)


@router.post("/projects/{project_id}/engineering/revisions/{revision_id}/reviews")
def start_review(project_id: str, revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_REVIEW")
    revision = _revision_project(db, revision_id, project.id)
    if not db.scalars(select(EngineeringRendition).where(EngineeringRendition.revision_id == revision.id)).first(): raise domain_error(409, "ENGINEERING_REVIEW_RENDITION_REQUIRED")
    number = (db.scalar(select(func.max(ProjectEngineeringReview.review_number)).where(ProjectEngineeringReview.revision_id == revision.id)) or 0) + 1
    item = ProjectEngineeringReview(project_id=project.id, revision_id=revision.id, review_number=number, started_by=actor)
    db.add(item); db.flush(); revision.status = "UNDER_REVIEW"; audit(db, correlation_id=_corr(request), event_type="ENGINEERING_REVIEW_STARTED", entity_type="ProjectEngineeringReview", entity_id=item.id, actor_id=actor, after=_row(item)); db.commit(); return _row(item)


@router.post("/projects/{project_id}/engineering/reviews/{review_id}/findings")
def add_finding(project_id: str, review_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_REVIEW")
    review = db.get(ProjectEngineeringReview, review_id)
    if not review or review.project_id != project.id: raise domain_error(404, "ENGINEERING_REVIEW_NOT_FOUND")
    item = EngineeringReviewFinding(project_id=project.id, review_id=review.id, finding_ref=str(payload.get("finding_ref") or f"F-{uuid4().hex[:8]}"), severity=str(payload.get("severity") or "MAJOR").upper(), description=str(payload.get("description") or ""), status="OPEN")
    if not item.description: raise domain_error(422, "ENGINEERING_FINDING_DESCRIPTION_REQUIRED")
    db.add(item); db.flush(); audit(db, correlation_id=_corr(request), event_type="ENGINEERING_REVIEW_FINDING_ADDED", entity_type="EngineeringReviewFinding", entity_id=item.id, actor_id=actor, after=_row(item)); db.commit(); return _row(item)


@router.post("/projects/{project_id}/engineering/findings/{finding_id}/resolve")
def resolve_finding(project_id: str, finding_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_REVIEW")
    item = db.get(EngineeringReviewFinding, finding_id)
    if not item or item.project_id != project.id: raise domain_error(404, "ENGINEERING_FINDING_NOT_FOUND")
    item.status = "RESOLVED"; item.response = str(payload.get("response") or "Human disposition recorded"); item.disposition_by = actor; item.resolved_at = datetime.now(timezone.utc); db.commit(); return _row(item)


@router.post("/projects/{project_id}/engineering/reviews/{review_id}/complete")
def complete_review(project_id: str, review_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_REVIEW")
    review = db.get(ProjectEngineeringReview, review_id)
    if not review or review.project_id != project.id: raise domain_error(404, "ENGINEERING_REVIEW_NOT_FOUND")
    if _active_findings(db, review.revision_id): raise domain_error(409, "ENGINEERING_REVIEW_BLOCKED_BY_OPEN_FINDING")
    review.status = "COMPLETED"; review.completed_by = actor; review.completed_at = datetime.now(timezone.utc); revision = _revision(db, review.revision_id); revision.status = "REVIEWED"; db.commit(); return _row(review)


@router.post("/projects/{project_id}/engineering/revisions/{revision_id}/technical-checks")
def technical_check(project_id: str, revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_REVIEW")
    revision = _revision_project(db, revision_id, project.id)
    rule_set = db.get(TechnicalRuleSetVersion, payload.get("technical_rule_set_version_id")); rule = db.get(TechnicalRule, payload.get("technical_rule_id"))
    if not rule_set or not rule or rule.rule_set_version_id != rule_set.id: raise domain_error(409, "ENGINEERING_TECHNICAL_RULE_REFERENCE_INVALID")
    inputs = payload.get("inputs") or {}; expression = rule.expression_json or {}; value_key = expression.get("input") or expression.get("input_key"); value = inputs.get(value_key) if value_key else None
    threshold = expression.get("threshold", expression.get("value")); operator = str(expression.get("operator") or "gte").lower(); result = "UNKNOWN"; reason = "Required typed input is missing"; calculated: dict[str, Any] = {}
    if value is not None and threshold is not None:
        try:
            numeric = float(value); target = float(threshold); calculated = {"input": numeric, "threshold": target, "unit": expression.get("unit")}
            result = "PASS" if {"gte": numeric >= target, "gt": numeric > target, "lte": numeric <= target, "lt": numeric < target, "eq": numeric == target}.get(operator, False) else "FAIL"; reason = f"Deterministic {operator} evaluation"
        except (TypeError, ValueError): result = "UNKNOWN"; reason = "Typed numeric input required"
    item = EngineeringTechnicalCheck(project_id=project.id, revision_id=revision.id, technical_rule_set_version_id=rule_set.id, technical_rule_id=rule.id, result=result, inputs_json=inputs, calculated_values_json=calculated, rule_version=rule_set.version, reason=reason)
    db.add(item); db.flush(); db.add(LineageEdge(project_id=project.id, upstream_type="TechnicalRuleSetVersion", upstream_id=rule_set.id, upstream_version_or_hash=rule_set.version, downstream_type="EngineeringTechnicalCheck", downstream_id=item.id, dependency_kind="EXACT_TECHNICAL_RULE_EVALUATION", correlation_id=_corr(request))); db.commit(); return _row(item)


@router.post("/projects/{project_id}/engineering/revisions/{revision_id}/calculations")
def calculation(project_id: str, revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_REVIEW")
    revision = _revision_project(db, revision_id, project.id); rule_set = db.get(TechnicalRuleSetVersion, payload.get("technical_rule_set_version_id"))
    if not rule_set: raise domain_error(409, "ENGINEERING_TECHNICAL_RULE_SET_REQUIRED")
    values = payload.get("inputs") or {}; normalized = dict(values)
    if values.get("unit") == "mm" and values.get("value") is not None: normalized["value"] = float(values["value"]) / 1000; normalized["unit"] = "m"
    result_json = {"value": normalized.get("value"), "unit": normalized.get("unit"), "method": "DETERMINISTIC_UNIT_NORMALIZATION"}; digest = hashlib.sha256(json.dumps({"rule_set": rule_set.id, "inputs": values, "normalized": normalized, "result": result_json}, sort_keys=True).encode()).hexdigest()
    item = EngineeringCalculationRecord(project_id=project.id, revision_id=revision.id, technical_rule_set_version_id=rule_set.id, input_values_json=values, normalized_units_json=normalized, result_json=result_json, result_hash=digest, created_by=actor)
    db.add(item); db.flush(); db.commit(); return _row(item)


@router.post("/projects/{project_id}/engineering/revisions/{revision_id}/professional-approval")
def professional_approval(project_id: str, revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_PROFESSIONAL_APPROVE")
    revision = _revision_project(db, revision_id, project.id); _require_mutable(revision)
    if revision.prepared_by == actor: raise domain_error(409, "ENGINEERING_SEGREGATION_OF_DUTIES_REQUIRED")
    if not payload.get("credential_reference"): raise domain_error(409, "ENGINEERING_CREDENTIAL_REFERENCE_REQUIRED")
    credential = db.get(ProfessionalCredential, payload.get("professional_credential_id")) if payload.get("professional_credential_id") else None
    if payload.get("professional_credential_id") and (not credential or credential.project_id != project.id or credential.status != "CURRENT"):
        raise domain_error(409, "ENGINEERING_PROFESSIONAL_CREDENTIAL_INVALID")
    reviews = db.scalars(select(ProjectEngineeringReview).where(ProjectEngineeringReview.revision_id == revision.id)).all()
    if not reviews or not any(x.status == "COMPLETED" for x in reviews): raise domain_error(409, "ENGINEERING_REVIEW_COMPLETION_REQUIRED")
    if _active_findings(db, revision.id): raise domain_error(409, "ENGINEERING_APPROVAL_BLOCKED_BY_OPEN_FINDING")
    renditions = db.scalars(select(EngineeringRendition).where(EngineeringRendition.revision_id == revision.id)).all(); kinds = {x.rendition_kind for x in renditions}
    if not {"NATIVE", "PUBLISHED"}.issubset(kinds): raise domain_error(409, "ENGINEERING_NATIVE_AND_PUBLISHED_RENDITIONS_REQUIRED")
    checks = db.scalars(select(EngineeringTechnicalCheck).where(EngineeringTechnicalCheck.revision_id == revision.id)).all()
    if any(x.result != "PASS" for x in checks): raise domain_error(409, "ENGINEERING_TECHNICAL_CHECK_NOT_PASS")
    item = EngineeringProfessionalApproval(project_id=project.id, revision_id=revision.id, approver_actor=actor, approver_party_id=payload.get("approver_party_id"), professional_credential_id=credential.id if credential else None, credential_reference=str(payload["credential_reference"]), pinned_rendition_ids=[x.id for x in renditions], reason=payload.get("reason"))
    db.add(item); db.flush(); revision.approval_status = "PROFESSIONALLY_APPROVED"; revision.status = "APPROVED"; revision.immutable_at = datetime.now(timezone.utc); deliverable = db.get(EngineeringDeliverable, revision.deliverable_id); deliverable.status = "APPROVED"; audit(db, correlation_id=_corr(request), event_type="ENGINEERING_PROFESSIONAL_APPROVED_EXACT_REVISION", entity_type="EngineeringProfessionalApproval", entity_id=item.id, actor_id=actor, after={**_row(item), "authority_approval": False, "construction_release": False}); db.commit(); return _row(item)


@router.post("/projects/{project_id}/engineering/baselines")
def create_baseline(project_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_PROJECT_EDIT")
    item = ApprovedDesignBaseline(project_id=project.id, baseline_ref=str(payload.get("baseline_ref") or ""), purpose=str(payload.get("purpose") or "AMEC_APPROVED_DESIGN"), created_by=actor)
    if not item.baseline_ref: raise domain_error(422, "ENGINEERING_BASELINE_REF_REQUIRED")
    db.add(item); db.flush(); audit(db, correlation_id=_corr(request), event_type="ENGINEERING_APPROVED_DESIGN_BASELINE_CANDIDATE_CREATED", entity_type="ApprovedDesignBaseline", entity_id=item.id, actor_id=actor, after=_row(item)); db.commit(); return _row(item)


def _baseline_validation(db: Session, baseline: ApprovedDesignBaseline) -> dict[str, Any]:
    members = db.scalars(select(ApprovedDesignBaselineMember).where(ApprovedDesignBaselineMember.baseline_id == baseline.id)).all(); errors: list[dict[str, Any]] = []
    if not members: errors.append({"code": "BASELINE_MEMBER_REQUIRED"})
    for member in members:
        revision = db.get(EngineeringDeliverableRevision, member.revision_id); rendition = db.get(EngineeringRendition, member.rendition_id)
        if not revision or revision.project_id != baseline.project_id: errors.append({"code": "BASELINE_MEMBER_PROJECT_MISMATCH", "member_id": member.id})
        if not rendition or rendition.project_id != baseline.project_id or (revision and rendition.revision_id != revision.id): errors.append({"code": "BASELINE_RENDITION_PROJECT_OR_REVISION_MISMATCH", "member_id": member.id})
        if revision and revision.approval_status != "PROFESSIONALLY_APPROVED": errors.append({"code": "BASELINE_MEMBER_NOT_PROFESSIONALLY_APPROVED", "revision_id": revision.id})
        if revision and _active_findings(db, revision.id): errors.append({"code": "BASELINE_MEMBER_OPEN_BLOCKING_FINDING", "revision_id": revision.id})
        if revision and any(x.result != "PASS" for x in db.scalars(select(EngineeringTechnicalCheck).where(EngineeringTechnicalCheck.revision_id == revision.id)).all()): errors.append({"code": "BASELINE_MEMBER_TECHNICAL_NOT_PASS", "revision_id": revision.id})
        if rendition and not db.get(DocumentVersion, rendition.document_version_id): errors.append({"code": "BASELINE_MEMBER_DOCUMENT_VERSION_MISSING", "rendition_id": rendition.id})
    return {"valid": not errors, "errors": errors, "member_count": len(members)}


@router.post("/projects/{project_id}/engineering/baselines/{baseline_id}/members")
def add_baseline_member(project_id: str, baseline_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_PROJECT_EDIT")
    baseline = db.get(ApprovedDesignBaseline, baseline_id)
    if not baseline or baseline.project_id != project.id: raise domain_error(404, "ENGINEERING_BASELINE_NOT_FOUND")
    if baseline.status != "CANDIDATE": raise domain_error(409, "APPROVED_DESIGN_BASELINE_IMMUTABLE")
    revision = _revision_project(db, str(payload.get("revision_id")), project.id); rendition = db.get(EngineeringRendition, payload.get("rendition_id"))
    if not rendition or rendition.project_id != project.id or rendition.revision_id != revision.id: raise domain_error(409, "ENGINEERING_BASELINE_MEMBER_EXACT_REFERENCE_REQUIRED")
    item = ApprovedDesignBaselineMember(baseline_id=baseline.id, project_id=project.id, revision_id=revision.id, rendition_id=rendition.id, member_role=str(payload.get("member_role") or "APPROVED_DESIGN_INPUT"), pinned_hash=rendition.content_hash)
    db.add(item); db.flush(); db.commit(); return _row(item)


@router.post("/projects/{project_id}/engineering/baselines/{baseline_id}/validate")
def validate_baseline(project_id: str, baseline_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); _authorized(db, project_id, role, _actor(request), "ENGINEERING_PROJECT_READ"); baseline = db.get(ApprovedDesignBaseline, baseline_id)
    if not baseline or baseline.project_id != project.id: raise domain_error(404, "ENGINEERING_BASELINE_NOT_FOUND")
    validation = _baseline_validation(db, baseline); baseline.validation_json = validation; db.commit(); return validation


@router.post("/projects/{project_id}/engineering/baselines/{baseline_id}/approve")
def approve_baseline(project_id: str, baseline_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_BASELINE_APPROVE"); baseline = db.get(ApprovedDesignBaseline, baseline_id)
    if not baseline or baseline.project_id != project.id: raise domain_error(404, "ENGINEERING_BASELINE_NOT_FOUND")
    if baseline.status != "CANDIDATE": raise domain_error(409, "APPROVED_DESIGN_BASELINE_IMMUTABLE")
    validation = _baseline_validation(db, baseline); baseline.validation_json = validation
    if not validation["valid"]: db.commit(); raise domain_error(409, "ENGINEERING_BASELINE_VALIDATION_FAILED", validation=validation)
    if not payload.get("credential_reference"): raise domain_error(409, "ENGINEERING_BASELINE_CREDENTIAL_REFERENCE_REQUIRED")
    members = db.scalars(select(ApprovedDesignBaselineMember).where(ApprovedDesignBaselineMember.baseline_id == baseline.id).order_by(ApprovedDesignBaselineMember.revision_id, ApprovedDesignBaselineMember.rendition_id)).all()
    manifest = {"baseline_id": baseline.id, "project_id": project.id, "purpose": baseline.purpose, "members": [{"revision_id": m.revision_id, "rendition_id": m.rendition_id, "pinned_hash": m.pinned_hash} for m in members], "authority_approval": False, "construction_release": False}
    baseline.manifest_json = manifest; baseline.manifest_hash = hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest(); baseline.status = "APPROVED"; baseline.approved_by = actor; baseline.approval_credential_reference = str(payload["credential_reference"]); baseline.approved_at = datetime.now(timezone.utc); audit(db, correlation_id=_corr(request), event_type="AMEC_APPROVED_DESIGN_BASELINE_APPROVED", entity_type="ApprovedDesignBaseline", entity_id=baseline.id, actor_id=actor, after={"manifest_hash": baseline.manifest_hash, "authority_approval": False, "construction_release": False}); db.commit(); return _row(baseline)


@router.get("/projects/{project_id}/engineering/baselines/{baseline_id}/manifest")
def baseline_manifest(project_id: str, baseline_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _project(db, project_id); _authorized(db, project_id, role, _actor(request)); baseline = db.get(ApprovedDesignBaseline, baseline_id)
    if not baseline or baseline.project_id != project.id: raise domain_error(404, "ENGINEERING_BASELINE_NOT_FOUND")
    return {"status": baseline.status, "baseline_ref": baseline.baseline_ref, "manifest_hash": baseline.manifest_hash, "manifest": baseline.manifest_json, "label": "AMEC Approved Design Baseline — not Authority Approved and not Construction Release"}


@router.post("/projects/{project_id}/engineering/design-changes")
def create_design_change(project_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_PROJECT_EDIT"); baseline = db.get(ApprovedDesignBaseline, payload.get("from_baseline_id"))
    if not baseline or baseline.project_id != project.id or baseline.status != "APPROVED": raise domain_error(409, "DESIGN_CHANGE_APPROVED_BASELINE_REQUIRED")
    item = DesignChangeRequest(project_id=project.id, change_ref=str(payload.get("change_ref") or ""), from_baseline_id=baseline.id, reason=str(payload.get("reason") or ""), regulatory_impact=str(payload.get("regulatory_impact") or "UNKNOWN"), commercial_impact=str(payload.get("commercial_impact") or "UNKNOWN"), created_by=actor)
    if not item.change_ref or not item.reason: raise domain_error(422, "DESIGN_CHANGE_FIELDS_REQUIRED")
    db.add(item); db.flush(); audit(db, correlation_id=_corr(request), event_type="ENGINEERING_DESIGN_CHANGE_CREATED", entity_type="DesignChangeRequest", entity_id=item.id, actor_id=actor, after=_row(item)); db.commit(); return _row(item)


@router.post("/projects/{project_id}/engineering/design-changes/{change_id}/review")
def review_design_change(project_id: str, change_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_REVIEW"); item = db.get(DesignChangeRequest, change_id)
    if not item or item.project_id != project.id: raise domain_error(404, "DESIGN_CHANGE_NOT_FOUND")
    item.status = "APPROVED_TO_PROCEED" if bool(payload.get("approve_to_proceed", True)) else "REJECTED"; item.approved_to_proceed_by = actor if item.status == "APPROVED_TO_PROCEED" else None; db.commit(); return _row(item)


@router.post("/projects/{project_id}/engineering/design-changes/{change_id}/link-revisions")
def link_change_revisions(project_id: str, change_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_PROJECT_EDIT"); item = db.get(DesignChangeRequest, change_id)
    if not item or item.project_id != project.id: raise domain_error(404, "DESIGN_CHANGE_NOT_FOUND")
    if item.status != "APPROVED_TO_PROCEED": raise domain_error(409, "DESIGN_CHANGE_APPROVAL_TO_PROCEED_REQUIRED")
    ids = [str(x) for x in payload.get("revision_ids") or []]
    if not ids or any((_revision(db, x).project_id != project.id) for x in ids): raise domain_error(409, "DESIGN_CHANGE_REVISION_PROJECT_MISMATCH")
    item.linked_revision_ids = ids; item.status = "IN_IMPLEMENTATION"; db.commit(); return _row(item)


@router.post("/projects/{project_id}/engineering/design-changes/{change_id}/mark-implemented")
def mark_change_implemented(project_id: str, change_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_PROJECT_EDIT"); item = db.get(DesignChangeRequest, change_id); baseline = db.get(ApprovedDesignBaseline, payload.get("next_baseline_id"))
    if not item or item.project_id != project.id: raise domain_error(404, "DESIGN_CHANGE_NOT_FOUND")
    if not baseline or baseline.project_id != project.id or baseline.status != "APPROVED": raise domain_error(409, "DESIGN_CHANGE_NEXT_APPROVED_BASELINE_REQUIRED")
    item.next_baseline_id = baseline.id; item.status = "IMPLEMENTED"; item.implemented_at = datetime.utcnow(); db.commit(); return _row(item)


@router.post("/projects/{project_id}/engineering/material-tests")
def material_test(project_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); _authorized(db, project_id, role, actor, "ENGINEERING_PROJECT_EDIT")
    revision = db.get(EngineeringDeliverableRevision, payload.get("revision_id")) if payload.get("revision_id") else None
    if revision and revision.project_id != project.id: raise domain_error(409, "ENGINEERING_MATERIAL_TEST_REVISION_PROJECT_MISMATCH")
    item = EngineeringMaterialTest(project_id=project.id, revision_id=revision.id if revision else None, material_code=str(payload.get("material_code") or ""), test_type=str(payload.get("test_type") or ""), result_json=payload.get("result") or {}, certificate_document_version_id=payload.get("certificate_document_version_id"), laboratory_party_id=payload.get("laboratory_party_id"), accreditation_evidence_json=payload.get("accreditation_evidence") or {})
    if not item.material_code or not item.test_type: raise domain_error(422, "ENGINEERING_MATERIAL_TEST_FIELDS_REQUIRED")
    db.add(item); db.flush(); db.commit(); return _row(item)
