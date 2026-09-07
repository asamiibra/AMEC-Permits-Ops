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
from fastapi.responses import JSONResponse, Response
from sqlalchemy import select, func, true
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..models import (
    ApprovedDesignBaseline, ApprovedDesignBaselineMember, AuthorityCase, AuthorityCaseFinding, Document, DocumentApprovalState,
    DocumentType, DocumentVersion, DesignChangeRequest, EngineeringCalculationRecord,
    EngineeringDeliverable, EngineeringDeliverableRevision, EngineeringMaterialTest,
    EngineeringProfessionalApproval, EngineeringProjectMember, EngineeringRendition,
    EngineeringReviewFinding, EngineeringTechnicalCheck, EngineeringWorkPackage,
    EngineeringAICommentArtifact, EngineeringAuthorityFindingLink, EngineeringCategoryAssignment, EngineeringInternalReviewComment, EngineeringReviewCategory, LineageEdge, ProfessionalCredential, Project, ProjectEngineeringReview, Role, TechnicalRule, TechnicalRuleSetVersion,
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
    return {key: _json(value) for key, value in item.__dict__.items() if not key.startswith("_") and key != "synthetic_content"}


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


def _category(db: Session, category_id: str) -> EngineeringReviewCategory:
    item = db.get(EngineeringReviewCategory, category_id)
    if not item or not item.active:
        raise domain_error(404, "ENGINEERING_REVIEW_CATEGORY_NOT_FOUND", category_id=category_id)
    return item


def _review_project(db: Session, review_id: str, project_id: str) -> ProjectEngineeringReview:
    review = db.get(ProjectEngineeringReview, review_id)
    if not review or review.project_id != project_id:
        raise domain_error(404, "ENGINEERING_REVIEW_NOT_FOUND", review_id=review_id)
    return review


def _revision_policy() -> dict[str, Any]:
    return {"business_format": "R{sequence}", "sequence_start": 1, "zero_based_literal_codes": False, "document_version_is_separate": True, "owner_confirmation_required_for_change": True}


def _drawing_review_row(db: Session, review: ProjectEngineeringReview) -> dict[str, Any]:
    revision = db.get(EngineeringDeliverableRevision, review.revision_id)
    deliverable = db.get(EngineeringDeliverable, revision.deliverable_id) if revision else None
    package = db.get(EngineeringWorkPackage, deliverable.work_package_id) if deliverable else None
    category = db.get(EngineeringReviewCategory, review.review_category_id) if review.review_category_id else None
    renditions = db.scalars(select(EngineeringRendition).where(EngineeringRendition.revision_id == review.revision_id).order_by(EngineeringRendition.rendition_kind)).all()
    documents = {item.id: item for item in db.scalars(select(DocumentVersion).where(DocumentVersion.id.in_([item.document_version_id for item in renditions]))).all()} if renditions else {}
    findings = db.scalars(select(EngineeringReviewFinding).where(EngineeringReviewFinding.review_id == review.id).order_by(EngineeringReviewFinding.finding_ref)).all()
    internal_comments = db.scalars(select(EngineeringInternalReviewComment).where(EngineeringInternalReviewComment.review_id == review.id).order_by(EngineeringInternalReviewComment.created_at)).all()
    links = db.scalars(select(EngineeringAuthorityFindingLink).where(EngineeringAuthorityFindingLink.review_id == review.id).order_by(EngineeringAuthorityFindingLink.created_at)).all()
    open_blockers = [item for item in findings if item.status in {"OPEN", "RESPONDED"} and item.severity in {"BLOCKING", "CRITICAL", "MAJOR"}]
    return {"id": review.id, "project_id": review.project_id, "project": _row(db.get(Project, review.project_id)), "review_category": _row(category), "discipline": deliverable.discipline if deliverable else None, "work_package": _row(package), "deliverable": _row(deliverable), "revision": _row(revision), "revision_policy": _revision_policy(), "date": review.created_at.isoformat() if review.created_at else None, "status": review.status, "lane": "NEED_ACTION" if open_blockers else "READY_CLOSE" if revision and revision.approval_status == "PROFESSIONALLY_APPROVED" else "AUTHORITY_REVIEW" if links else "ALL", "action": "SUBMIT_FOR_INTERNAL_REVIEW" if review.status in {"OPEN", "CREATED"} else "SEND_TO_PROFESSIONAL_APPROVAL_QUEUE" if review.status in {"COMPLETED", "REVIEWED"} else "OPEN_NEXT_REVISION_STEP" if revision and revision.approval_status == "PROFESSIONALLY_APPROVED" else "REVIEW_REQUIRED", "renditions": [{**_row(item), "document_version": _row(documents.get(item.document_version_id)), "exact_reference": True} for item in renditions], "findings": [_row(item) for item in findings], "internal_comments": [_row(item) for item in internal_comments], "ai_comment_artifacts": [_row(item) for item in db.scalars(select(EngineeringAICommentArtifact).where(EngineeringAICommentArtifact.review_id == review.id).order_by(EngineeringAICommentArtifact.generated_at.desc())).all()], "authority_links": [_row(item) for item in links], "authority_review_meaning": "INTERNAL_ENGINEERING_REVIEW_OR_CANONICAL_EXTERNAL_LINK_ONLY; NOT_EXTERNAL_AUTHORITY_APPROVAL", "professional_approval": [_row(item) for item in db.scalars(select(EngineeringProfessionalApproval).where(EngineeringProfessionalApproval.revision_id == review.revision_id)).all()]}


def _exact_rendition(db: Session, review: ProjectEngineeringReview, rendition_id: str) -> tuple[EngineeringRendition, DocumentVersion]:
    rendition = db.get(EngineeringRendition, rendition_id)
    if not rendition or rendition.project_id != review.project_id or rendition.revision_id != review.revision_id:
        raise domain_error(404, "ENGINEERING_EXACT_RENDITION_NOT_FOUND", rendition_id=rendition_id, review_id=review.id)
    document_version = db.get(DocumentVersion, rendition.document_version_id)
    if not document_version:
        raise domain_error(409, "ENGINEERING_RENDITION_DOCUMENT_VERSION_MISSING", rendition_id=rendition.id)
    return rendition, document_version


def _authority_finding_for_project(db: Session, finding_id: str, project_id: str) -> AuthorityCaseFinding:
    finding = db.get(AuthorityCaseFinding, finding_id)
    case = db.get(AuthorityCase, finding.authority_case_id) if finding else None
    if not finding or not case or case.subject_type != "PROJECT" or case.subject_id != project_id:
        raise domain_error(404, "ENGINEERING_AUTHORITY_FINDING_NOT_FOUND", finding_id=finding_id)
    return finding


@router.get("/projects/{project_id}/engineering")
def engineering_summary(project_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _project(db, project_id)
    _authorized(db, project_id, role, _actor(request))
    packages = db.scalars(select(EngineeringWorkPackage).where(EngineeringWorkPackage.project_id == project.id).order_by(EngineeringWorkPackage.created_at)).all()
    deliverables = db.scalars(select(EngineeringDeliverable).where(EngineeringDeliverable.project_id == project.id).order_by(EngineeringDeliverable.created_at)).all()
    baselines = db.scalars(select(ApprovedDesignBaseline).where(ApprovedDesignBaseline.project_id == project.id).order_by(ApprovedDesignBaseline.created_at)).all()
    return {"project": {"id": project.id, "project_number": project.project_number, "project_name": project.project_name, "activated": bool(project.activated_at)}, "work_packages": [_row(x) for x in packages], "deliverables": [_row(x) for x in deliverables], "baselines": [_row(x) for x in baselines], "authority_approval_created": False, "construction_release_created": False, "submission_package_created": False}


@router.get("/engineering/review-categories")
def list_review_categories(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "ENGINEERING_PROJECT_READ")
    return {"items": [_row(item) for item in db.scalars(select(EngineeringReviewCategory).order_by(EngineeringReviewCategory.sort_order, EngineeringReviewCategory.name)).all()], "taxonomy": "CONFIGURED_ENGINEERING_REVIEW_CATEGORY", "discipline_is_separate": True, "sketch_abbreviations_interpreted": False}


@router.post("/engineering/review-categories")
def create_review_category(payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    require_capability(role, "ENGINEERING_CATEGORY_ASSIGNMENT_MANAGE")
    actor = _actor(request, payload)
    code = str(payload.get("code") or "").strip().upper()
    name = str(payload.get("name") or "").strip()
    if not code or not name:
        raise domain_error(422, "ENGINEERING_REVIEW_CATEGORY_FIELDS_REQUIRED")
    if db.scalar(select(EngineeringReviewCategory).where(EngineeringReviewCategory.code == code)):
        raise domain_error(409, "ENGINEERING_REVIEW_CATEGORY_CODE_EXISTS", code=code)
    item = EngineeringReviewCategory(code=code, name=name, description=payload.get("description"), discipline=payload.get("discipline"), stage_class=payload.get("stage_class"), active=bool(payload.get("active", True)), sort_order=int(payload.get("sort_order", 100)), source_kind=str(payload.get("source_kind") or "OWNER_CONFIGURED"), created_by=actor)
    db.add(item); db.flush(); audit(db, correlation_id=_corr(request), event_type="ENGINEERING_REVIEW_CATEGORY_CREATED", entity_type="EngineeringReviewCategory", entity_id=item.id, actor_id=actor, after={**_row(item), "discipline_is_separate": True, "global_role_created": False}); db.commit()
    return _row(item)


@router.get("/projects/{project_id}/engineering/review-categories")
def project_review_categories(project_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _project(db, project_id); _authorized(db, project_id, role, _actor(request))
    assignments = db.scalars(select(EngineeringCategoryAssignment).where(EngineeringCategoryAssignment.project_id == project.id).order_by(EngineeringCategoryAssignment.created_at)).all()
    return {"project": _row(project), "categories": [_row(item) for item in db.scalars(select(EngineeringReviewCategory).where(EngineeringReviewCategory.active == true()).order_by(EngineeringReviewCategory.sort_order, EngineeringReviewCategory.name)).all()], "assignments": [_row(item) for item in assignments], "visible_global_roles": ["OWNER", "BUSINESS_DEVELOPMENT", "ENGINEERING"]}


@router.post("/projects/{project_id}/engineering/review-categories/{category_id}/assignments")
def assign_review_category(project_id: str, category_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id); actor = _actor(request, payload); require_capability(role, "ENGINEERING_CATEGORY_ASSIGNMENT_MANAGE")
    category = _category(db, category_id)
    package = db.get(EngineeringWorkPackage, payload.get("work_package_id")) if payload.get("work_package_id") else None
    if package and package.project_id != project.id:
        raise domain_error(409, "ENGINEERING_ASSIGNMENT_WORK_PACKAGE_PROJECT_MISMATCH")
    assignee = str(payload.get("assignee_actor") or "").strip()
    if not assignee:
        raise domain_error(422, "ENGINEERING_ASSIGNMENT_ASSIGNEE_REQUIRED")
    existing = db.scalar(select(EngineeringCategoryAssignment).where(EngineeringCategoryAssignment.project_id == project.id, EngineeringCategoryAssignment.work_package_id == (package.id if package else None), EngineeringCategoryAssignment.review_category_id == category.id))
    if existing:
        existing.assignee_actor = assignee; existing.team = payload.get("team"); existing.responsibility = str(payload.get("responsibility") or existing.responsibility); existing.capability = str(payload.get("capability") or existing.capability); existing.effective_state = str(payload.get("effective_state") or "ACTIVE")
        item = existing; event = "ENGINEERING_CATEGORY_ASSIGNMENT_CHANGED"
    else:
        item = EngineeringCategoryAssignment(project_id=project.id, work_package_id=package.id if package else None, review_category_id=category.id, assignee_actor=assignee, team=payload.get("team"), responsibility=str(payload.get("responsibility") or "ENGINEERING_REVIEW"), capability=str(payload.get("capability") or "ENGINEERING_REVIEW"), effective_state=str(payload.get("effective_state") or "ACTIVE"), created_by=actor)
        db.add(item); event = "ENGINEERING_CATEGORY_ASSIGNMENT_CREATED"
    db.flush(); _lineage(db, project.id, "EngineeringReviewCategory", category.id, "EngineeringCategoryAssignment", item.id, "ENGINEERING_CATEGORY_ASSIGNED", request, category.code); audit(db, correlation_id=_corr(request), event_type=event, entity_type="EngineeringCategoryAssignment", entity_id=item.id, actor_id=actor, after={**_row(item), "global_role_created": False, "professional_approval_granted": False}); db.commit()
    return {"assignment": _row(item), "category": _row(category), "visible_global_roles": ["OWNER", "BUSINESS_DEVELOPMENT", "ENGINEERING"]}


@router.get("/projects/{project_id}/engineering/drawing-review")
def drawing_review_list(project_id: str, request: Request, lane: str | None = None, q: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _project(db, project_id)
    _authorized(db, project_id, role, _actor(request))
    reviews = db.scalars(select(ProjectEngineeringReview).where(ProjectEngineeringReview.project_id == project.id).order_by(ProjectEngineeringReview.created_at.desc())).all()
    items = [_drawing_review_row(db, review) for review in reviews]
    if lane and lane.upper() != "ALL":
        items = [item for item in items if item["lane"] == lane.upper()]
    if q:
        needle = q.casefold()
        items = [item for item in items if needle in json.dumps(item, default=str).casefold()]
    return {"project": _row(project), "columns": ["project", "review_category", "revision", "date", "status", "action"], "lanes": ["ALL", "NEED_ACTION", "AUTHORITY_REVIEW", "READY_CLOSE"], "items": items, "authority_review_label": "Internal engineering review / canonical external link only"}


@router.get("/projects/{project_id}/engineering/drawing-review/{review_id}")
def drawing_review_detail(project_id: str, review_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _project(db, project_id)
    _authorized(db, project_id, role, _actor(request))
    return _drawing_review_row(db, _review_project(db, review_id, project_id))


@router.post("/projects/{project_id}/engineering/reviews/{review_id}/review-category")
def set_review_category(project_id: str, review_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id)
    actor = _actor(request, payload)
    _authorized(db, project_id, role, actor, "ENGINEERING_CATEGORY_ASSIGNMENT_MANAGE")
    review = _review_project(db, review_id, project.id)
    category = _category(db, str(payload.get("review_category_id") or ""))
    revision = _revision_project(db, review.revision_id, project.id)
    review.review_category_id = category.id
    _lineage(db, project.id, "EngineeringReviewCategory", category.id, "ProjectEngineeringReview", review.id, "ENGINEERING_REVIEW_CATEGORY_APPLIED", request, category.code)
    audit(db, correlation_id=_corr(request), event_type="ENGINEERING_REVIEW_CATEGORY_CHANGED", entity_type="ProjectEngineeringReview", entity_id=review.id, actor_id=actor, after={"review_category_id": category.id, "discipline": db.get(EngineeringDeliverable, revision.deliverable_id).discipline})
    db.commit()
    return _drawing_review_row(db, review)


@router.post("/projects/{project_id}/engineering/drawing-review/{review_id}/proceed")
def proceed_drawing_review(project_id: str, review_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id)
    actor = _actor(request, payload)
    _authorized(db, project_id, role, actor, "ENGINEERING_REVIEW")
    review = _review_project(db, review_id, project.id)
    action = str(payload.get("action") or "").upper()
    transitions = {"SUBMIT_FOR_INTERNAL_REVIEW": "INTERNAL_REVIEW", "SEND_TO_PROFESSIONAL_APPROVAL_QUEUE": "READY_FOR_PROFESSIONAL_APPROVAL", "OPEN_NEXT_REVISION_STEP": "NEXT_REVISION_REQUIRED"}
    if action not in transitions:
        raise domain_error(422, "ENGINEERING_DRAWING_REVIEW_ACTION_INVALID", allowed_actions=list(transitions))
    review.status = transitions[action]
    audit(db, correlation_id=_corr(request), event_type="ENGINEERING_DRAWING_REVIEW_PROCEEDED", entity_type="ProjectEngineeringReview", entity_id=review.id, actor_id=actor, after={"action": action, "status": review.status, "external_authority_approval": False, "construction_release": False})
    db.commit()
    return _drawing_review_row(db, review)


@router.get("/projects/{project_id}/engineering/drawing-review/{review_id}/renditions/{rendition_id}/open")
def open_drawing_rendition(project_id: str, review_id: str, rendition_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _project(db, project_id)
    actor = _actor(request)
    _authorized(db, project_id, role, actor)
    review = _review_project(db, review_id, project.id)
    rendition, document_version = _exact_rendition(db, review, rendition_id)
    audit(db, correlation_id=_corr(request), event_type="ENGINEERING_DRAWING_RENDITION_OPENED", entity_type="EngineeringRendition", entity_id=rendition.id, actor_id=actor, after={"review_id": review.id, "revision_id": review.revision_id, "document_version_id": document_version.id, "exact_reference": True})
    db.commit()
    return {"rendition": _row(rendition), "document_version": _row(document_version), "exact_reference": True, "latest_lookup_used": False}


@router.get("/projects/{project_id}/engineering/drawing-review/{review_id}/renditions/{rendition_id}/download")
def download_drawing_rendition(project_id: str, review_id: str, rendition_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _project(db, project_id)
    actor = _actor(request)
    _authorized(db, project_id, role, actor)
    review = _review_project(db, review_id, project.id)
    rendition, document_version = _exact_rendition(db, review, rendition_id)
    content = document_version.synthetic_content or b""
    audit(db, correlation_id=_corr(request), event_type="ENGINEERING_DRAWING_RENDITION_DOWNLOADED", entity_type="EngineeringRendition", entity_id=rendition.id, actor_id=actor, after={"review_id": review.id, "revision_id": review.revision_id, "document_version_id": document_version.id, "sha256": document_version.sha256, "exact_reference": True})
    db.commit()
    return Response(content=content, media_type=document_version.mime_type or "application/octet-stream", headers={"Content-Disposition": f'attachment; filename="{document_version.source_filename}"', "X-Engineering-Document-Version": document_version.id, "X-Engineering-Exact-Revision": review.revision_id})


@router.post("/projects/{project_id}/engineering/drawing-review/{review_id}/internal-comments")
def add_internal_drawing_comment(project_id: str, review_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id)
    actor = _actor(request, payload)
    _authorized(db, project_id, role, actor, "ENGINEERING_REVIEW")
    review = _review_project(db, review_id, project.id)
    revision = _revision_project(db, review.revision_id, project.id)
    document_version_id = str(payload.get("document_version_id") or "")
    if not document_version_id or not db.scalar(select(EngineeringRendition).where(EngineeringRendition.revision_id == revision.id, EngineeringRendition.document_version_id == document_version_id)):
        raise domain_error(409, "ENGINEERING_INTERNAL_COMMENT_EXACT_DOCUMENT_REQUIRED")
    text = str(payload.get("comment_text") or "").strip()
    if not text:
        raise domain_error(422, "ENGINEERING_INTERNAL_COMMENT_TEXT_REQUIRED")
    item = EngineeringInternalReviewComment(project_id=project.id, review_id=review.id, revision_id=revision.id, drawing_document_version_id=document_version_id, comment_text=text, location_reference=payload.get("location_reference"), created_by=actor)
    db.add(item); db.flush()
    _lineage(db, project.id, "DocumentVersion", document_version_id, "EngineeringInternalReviewComment", item.id, "ENGINEERING_INTERNAL_COMMENT_EXACT_DRAWING", request)
    audit(db, correlation_id=_corr(request), event_type="ENGINEERING_INTERNAL_REVIEW_COMMENT_CREATED", entity_type="EngineeringInternalReviewComment", entity_id=item.id, actor_id=actor, after={**_row(item), "external_authority_comment": False})
    db.commit()
    return _row(item)


@router.post("/projects/{project_id}/engineering/drawing-review/{review_id}/ai-comments")
def generate_ai_drawing_comment(project_id: str, review_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id)
    actor = _actor(request, payload)
    _authorized(db, project_id, role, actor, "ENGINEERING_REVIEW")
    review = _review_project(db, review_id, project.id)
    revision = _revision_project(db, review.revision_id, project.id)
    rendition = db.scalar(select(EngineeringRendition).where(EngineeringRendition.revision_id == revision.id, EngineeringRendition.rendition_kind == "PUBLISHED"))
    if not rendition:
        raise domain_error(409, "ENGINEERING_AI_PUBLISHED_RENDITION_REQUIRED")
    findings = db.scalars(select(EngineeringReviewFinding).where(EngineeringReviewFinding.review_id == review.id).order_by(EngineeringReviewFinding.finding_ref)).all()
    comments = db.scalars(select(EngineeringInternalReviewComment).where(EngineeringInternalReviewComment.review_id == review.id).order_by(EngineeringInternalReviewComment.created_at)).all()
    summary = "; ".join([f"{item.finding_ref}: {item.description}" for item in findings] + [f"Internal comment: {item.comment_text}" for item in comments]) or "No human findings or internal comments recorded."
    draft = f"AI-assisted / draft — Review {review.id} for exact revision {revision.revision_code}. Candidate review summary: {summary} This artifact is not professional approval, an authority finding, or an authority response."
    document_version = db.get(DocumentVersion, rendition.document_version_id)
    item = EngineeringAICommentArtifact(project_id=project.id, review_id=review.id, revision_id=revision.id, drawing_document_version_id=rendition.document_version_id, draft_text=draft, metadata_json={"pinned_project_id": project.id, "pinned_deliverable_revision_id": revision.id, "pinned_drawing_document_version_id": rendition.document_version_id, "prompt_version": "ENGINEERING-DRAWING-COMMENTS-1.0", "runtime": "DETERMINISTIC_SYNTHETIC_REVIEW_ASSISTANT", "generated_at": datetime.now(timezone.utc).isoformat()}, generated_by=actor)
    db.add(item); db.flush()
    _lineage(db, project.id, "ProjectEngineeringReview", review.id, "EngineeringAICommentArtifact", item.id, "AI_REVIEW_DRAFT", request)
    _lineage(db, project.id, "DocumentVersion", rendition.document_version_id, "EngineeringAICommentArtifact", item.id, "AI_DRAFT_PINNED_DRAWING", request, document_version.sha256 if document_version else None)
    audit(db, correlation_id=_corr(request), event_type="ENGINEERING_AI_COMMENT_GENERATED", entity_type="EngineeringAICommentArtifact", entity_id=item.id, actor_id=actor, after={**_row(item), "approval_changed": False, "authority_finding_created": False})
    db.commit()
    return _row(item)


@router.get("/projects/{project_id}/engineering/drawing-review/{review_id}/ai-comments/{artifact_id}/download")
def download_ai_drawing_comment(project_id: str, review_id: str, artifact_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _project(db, project_id)
    actor = _actor(request)
    _authorized(db, project_id, role, actor)
    review = _review_project(db, review_id, project.id)
    item = db.get(EngineeringAICommentArtifact, artifact_id)
    if not item or item.project_id != project.id or item.review_id != review.id:
        raise domain_error(404, "ENGINEERING_AI_COMMENT_ARTIFACT_NOT_FOUND", artifact_id=artifact_id)
    audit(db, correlation_id=_corr(request), event_type="ENGINEERING_AI_COMMENT_DOWNLOADED", entity_type="EngineeringAICommentArtifact", entity_id=item.id, actor_id=actor, after={"status": item.status, "approval_changed": False, "authority_finding_created": False})
    db.commit()
    return JSONResponse(content={"artifact": _row(item), "label": "AI-assisted / draft", "professional_approval": False, "authority_response": False}, headers={"Content-Disposition": f'attachment; filename="engineering-review-{review.id}-ai-draft.json"'})


@router.get("/projects/{project_id}/engineering/drawing-review/{review_id}/authority-comment-seam")
def authority_comment_seam(project_id: str, review_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _project(db, project_id)
    _authorized(db, project_id, role, _actor(request))
    review = _review_project(db, review_id, project.id)
    links = db.scalars(select(EngineeringAuthorityFindingLink).where(EngineeringAuthorityFindingLink.review_id == review.id)).all()
    return {"canonical_type": "AuthorityCaseFinding", "exists_in_current_runtime": True, "creates_external_truth": False, "engineering_can_close_finding": False, "link_contract": {"upstream_type": "AuthorityCaseFinding", "downstream_type": "EngineeringDeliverableRevision", "review_category_supported": True, "project_scope_required": True, "dependency_kind": "AUTHORITY_FINDING_AFFECTS_ENGINEERING_REVISION"}, "links": [_row(item) for item in links], "required_downstream_statement": "ENGINEERING_EXTERNAL_AUTHORITY_COMMENT_SEAM_COMPATIBLE_WITH_AUTHORITY_FINDING"}


@router.post("/projects/{project_id}/engineering/drawing-review/{review_id}/authority-findings/{finding_id}/link")
def link_authority_finding(project_id: str, review_id: str, finding_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id)
    actor = _actor(request)
    _authorized(db, project_id, role, actor, "ENGINEERING_REVIEW")
    review = _review_project(db, review_id, project.id)
    finding = _authority_finding_for_project(db, finding_id, project.id)
    existing = db.scalar(select(EngineeringAuthorityFindingLink).where(EngineeringAuthorityFindingLink.authority_finding_id == finding.id, EngineeringAuthorityFindingLink.revision_id == review.revision_id))
    if existing:
        return _row(existing)
    item = EngineeringAuthorityFindingLink(project_id=project.id, review_id=review.id, revision_id=review.revision_id, review_category_id=review.review_category_id, authority_finding_id=finding.id, created_by=actor)
    db.add(item); db.flush()
    _lineage(db, project.id, "AuthorityCaseFinding", finding.id, "EngineeringDeliverableRevision", review.revision_id, "AUTHORITY_FINDING_AFFECTS_ENGINEERING_REVISION", request)
    audit(db, correlation_id=_corr(request), event_type="ENGINEERING_AUTHORITY_FINDING_LINKED", entity_type="EngineeringAuthorityFindingLink", entity_id=item.id, actor_id=actor, after={"authority_finding_id": finding.id, "revision_id": review.revision_id, "engineering_can_close_finding": False})
    db.commit()
    return _row(item)


@router.post("/projects/{project_id}/engineering/drawing-review/{review_id}/authority-findings/{finding_id}/design-change")
def design_change_from_authority_finding(project_id: str, review_id: str, finding_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    project = _active_project(db, project_id)
    actor = _actor(request, payload)
    _authorized(db, project_id, role, actor, "ENGINEERING_PROJECT_EDIT")
    review = _review_project(db, review_id, project.id)
    finding = _authority_finding_for_project(db, finding_id, project.id)
    link = db.scalar(select(EngineeringAuthorityFindingLink).where(EngineeringAuthorityFindingLink.authority_finding_id == finding.id, EngineeringAuthorityFindingLink.revision_id == review.revision_id))
    if not link:
        raise domain_error(409, "ENGINEERING_AUTHORITY_FINDING_LINK_REQUIRED")
    baseline = db.get(ApprovedDesignBaseline, payload.get("from_baseline_id"))
    if not baseline or baseline.project_id != project.id or baseline.status != "APPROVED":
        raise domain_error(409, "DESIGN_CHANGE_APPROVED_BASELINE_REQUIRED")
    change_ref = str(payload.get("change_ref") or f"DCF-{finding.external_finding_id or finding.id[:8]}")
    item = DesignChangeRequest(project_id=project.id, change_ref=change_ref, from_baseline_id=baseline.id, reason=str(payload.get("reason") or f"Engineering response to canonical AuthorityCaseFinding {finding.id}"), regulatory_impact="AUTHORITY_FINDING_LINKED", commercial_impact=str(payload.get("commercial_impact") or "UNKNOWN"), created_by=actor)
    db.add(item); db.flush()
    _lineage(db, project.id, "AuthorityCaseFinding", finding.id, "DesignChangeRequest", item.id, "AUTHORITY_FINDING_DESIGN_CHANGE", request)
    audit(db, correlation_id=_corr(request), event_type="ENGINEERING_DESIGN_CHANGE_REQUEST_FROM_AUTHORITY_FINDING", entity_type="DesignChangeRequest", entity_id=item.id, actor_id=actor, after={"authority_finding_id": finding.id, "status": item.status, "authority_finding_closed": False})
    db.commit()
    return _row(item)


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
    deliverable = db.scalar(select(EngineeringDeliverable).where(EngineeringDeliverable.id == deliverable_id).with_for_update())
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
    db.add(item)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise domain_error(409, "ENGINEERING_REVISION_SEQUENCE_CONFLICT", deliverable_id=deliverable.id)
    deliverable.current_revision_id = item.id; deliverable.status = "IN_PROGRESS"; _lineage(db, project.id, "EngineeringDeliverableRevision", previous.id if previous else deliverable.id, "EngineeringDeliverableRevision", item.id, "ENGINEERING_REVISION_SUPERSEDES" if previous else "ENGINEERING_REVISION_CREATED", request); audit(db, correlation_id=_corr(request), event_type="ENGINEERING_REVISION_ALLOCATED", entity_type="EngineeringDeliverableRevision", entity_id=item.id, actor_id=actor, after={**_row(item), "allocation_policy": _revision_policy(), "document_version_is_separate": True}); db.commit()
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
    category = _category(db, str(payload["review_category_id"])) if payload.get("review_category_id") else None
    item = ProjectEngineeringReview(project_id=project.id, revision_id=revision.id, review_category_id=category.id if category else None, review_number=number, started_by=actor)
    db.add(item); db.flush(); revision.status = "UNDER_REVIEW"
    if category:
        _lineage(db, project.id, "EngineeringReviewCategory", category.id, "ProjectEngineeringReview", item.id, "ENGINEERING_REVIEW_CATEGORY_APPLIED", request, category.code)
    audit(db, correlation_id=_corr(request), event_type="ENGINEERING_REVIEW_STARTED", entity_type="ProjectEngineeringReview", entity_id=item.id, actor_id=actor, after=_row(item)); db.commit(); return _row(item)


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
