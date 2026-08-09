"""Bounded E5 engineering advisory and E6 commercial-closeout APIs.

The routes are deliberately synthetic/prototype-only. They use the shared
PermitOps audit, task, rendering, communication, approval, and lineage
substrate, and never perform accounting, payment, email, government, or
professional-authority actions.
"""

from datetime import datetime, timezone
import hashlib
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..db import get_db
from ..expansion.execution import PROTOTYPE_POLICY, require_human_role
from ..expansion.runtime import create_communication_draft, render_artifact, select_template
from ..models import *
from ..services.week45 import stable_hash


router = APIRouter(prefix="/api")

ENGINEER_ROLES = {"AUTHORIZED_ENGINEER", "RESPONSIBLE_ENGINEER"}
FINANCE_ROLES = {"FINANCE_ACCOUNTANT", "FINANCE_MANAGER", "COMMERCIAL_APPROVER"}
HANDOVER_ROLES = {"PROJECT_OWNER", "ADMIN_PROJECT_COORDINATOR", "RESPONSIBLE_ENGINEER"}
TRUSTED_REGULATION_STATES = {"APPROVED_FOR_TEST", "APPROVED_CONTROLLED_SOURCE"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: datetime | None) -> datetime:
    if value is None:
        return _now()
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


def _row(item: Any) -> dict[str, Any] | None:
    if item is None:
        return None
    return jsonable_encoder({column.name: getattr(item, column.name) for column in item.__table__.columns})


def _require(db: Session, model: Any, item_id: str, detail: str):
    item = db.get(model, item_id)
    if not item:
        raise HTTPException(404, detail)
    return item


def _actor(payload: dict, default: str) -> tuple[str, str]:
    return str(payload.get("actor", default)), str(payload.get("actor_role", "ADMIN_PROJECT_COORDINATOR"))


def _persisted_user_id(db: Session, actor_id: str) -> str | None:
    """Keep optional user FKs valid when synthetic callers use labels like ``engineer``."""
    if db.get(User, actor_id):
        return actor_id
    user = db.scalar(select(User).where(User.email == actor_id))
    return user.id if user else None


def _cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "e5-e6-api")


def _require_role(role: str, allowed: set[str], detail: str):
    if role not in allowed:
        raise HTTPException(403, detail)
    require_human_role(role, allowed)


def _project(db: Session, project_id: str) -> Project:
    return _require(db, Project, project_id, "PROJECT_NOT_FOUND")


def _drawing_version(db: Session, document_version_id: str) -> DocumentVersion:
    return _require(db, DocumentVersion, document_version_id, "DRAWING_VERSION_NOT_FOUND")


def _audit(db: Session, request: Request, event: str, entity_type: str, entity_id: str, actor_id: str, after: dict[str, Any] | None = None):
    audit(db, correlation_id=_cid(request), event_type=event, entity_type=entity_type, entity_id=entity_id,
          actor_id=actor_id, after=after, metadata={"synthetic_only": True, "external_effect": False,
                                                    "execution_authority": PROTOTYPE_POLICY.authority.value})


def _task(db: Session, project_id: str, task_type: str, title: str, role: str, context_type: str, context_id: str, request: Request):
    application = db.scalar(select(PermitApplication).where(PermitApplication.project_id == project_id).order_by(PermitApplication.external_request_number))
    finding = db.scalar(select(Finding).where(Finding.project_id == project_id).order_by(Finding.captured_at))
    if not application or not finding:
        return None
    item = WorkflowTask(project_id=project_id, application_id=application.id, finding_id=finding.id, task_type=task_type,
                        title=title, description=f"Synthetic bounded task for {context_type} {context_id}.", owner_role=role,
                        status="OPEN", priority="MEDIUM", correlation_id=_cid(request), assistant_id="ENGINEERING_REVIEW_ASSISTANT" if "ENGINEERING" in task_type or "DRAWING" in task_type else "PROJECT_PERMIT_COORDINATION_ASSISTANT",
                        task_family="EXPANSION", context_type=context_type, context_id=context_id, blocking=False,
                        next_action_code=task_type, deep_link=f"/{context_type.lower()}/{context_id}", evidence_summary={"synthetic_only": True})
    db.add(item)
    db.flush()
    _audit(db, request, "WORKFLOW_TASK_CREATED", "WorkflowTask", item.id, "permitops-system", {"task_type": task_type, "owner_role": role, "context_id": context_id})
    return item


def _current_version(db: Session, document_id: str) -> DocumentVersion | None:
    document = db.get(Document, document_id)
    if not document:
        return None
    if document.current_version_id:
        return db.get(DocumentVersion, document.current_version_id)
    return db.scalar(select(DocumentVersion).where(DocumentVersion.document_id == document_id).order_by(DocumentVersion.version_number.desc()))


def _regulation_snapshot(db: Session, scope: EngineeringReviewScope, review: EngineeringReview, require_approved: bool = True) -> tuple[list[RegulationVersion], list[RegulationApplicability]]:
    versions = [db.get(RegulationVersion, value) for value in scope.selected_regulation_version_ids]
    versions = [value for value in versions if value]
    applicability = db.scalars(select(RegulationApplicability).where(RegulationApplicability.review_scope_id == scope.id)).all()
    if require_approved:
        if not versions:
            raise HTTPException(409, "REGULATION_SCOPE_REQUIRED")
        for version in versions:
            if version.content_status not in TRUSTED_REGULATION_STATES:
                raise HTTPException(409, "UNAPPROVED_REGULATION_CANNOT_SUPPORT_TRUSTED_RUN")
            item = next((value for value in applicability if value.regulation_version_id == version.id), None)
            if not item or item.applicability_status != "APPROVED_APPLICABLE":
                raise HTTPException(409, "HUMAN_APPROVED_REGULATION_APPLICABILITY_REQUIRED")
    return versions, applicability


def _engineering_scope(db: Session, review: EngineeringReview, payload: dict, request: Request) -> EngineeringReviewScope:
    version_ids = [str(value) for value in payload.get("selected_regulation_version_ids", [])]
    for version_id in version_ids:
        _require(db, RegulationVersion, version_id, "REGULATION_VERSION_NOT_FOUND")
    scope = EngineeringReviewScope(engineering_review_id=review.id, project_id=review.project_id,
                                   scope_code=payload.get("scope_code", f"SCOPE-{review.discipline}-{review.id[:8]}"),
                                   discipline=payload.get("discipline", review.discipline),
                                   supported_drawing_types=payload.get("supported_drawing_types", ["PDF"]),
                                   selected_regulation_version_ids=version_ids,
                                   applicability_basis=payload.get("applicability_basis", "Human-reviewed synthetic project and discipline basis."),
                                   review_objectives=payload.get("review_objectives", ["Identify candidate discrepancies with cited evidence."]),
                                   excluded_topics=payload.get("excluded_topics", ["Certification", "Stamping", "Government submission", "DWF semantic automation"]),
                                   authorized_engineer_role=payload.get("authorized_engineer_role", "AUTHORIZED_ENGINEER"),
                                   stage2_disposition=payload.get("stage2_disposition", "UNDECIDED_STAGE2"),
                                   evidence_class=payload.get("evidence_class", "SYNTHETIC_IMPLEMENTATION_EVIDENCE"),
                                   status="CONFIGURED", synthetic_only=True)
    db.add(scope)
    db.flush()
    review.current_scope_id = scope.id
    review.discipline = scope.discipline
    _audit(db, request, "ENGINEERING_SCOPE_CONFIGURED", "EngineeringReviewScope", scope.id, payload.get("actor", "synthetic-engineering"), _row(scope))
    _task(db, review.project_id, "PREPARE_ENGINEERING_REVIEW", "Prepare engineering advisory review", scope.authorized_engineer_role, "EngineeringReview", review.id, request)
    return scope


@router.get("/projects/{project_id}/engineering-reviews")
def engineering_reviews(project_id: str, db: Session = Depends(get_db)):
    _project(db, project_id)
    return [_row(item) for item in db.scalars(select(EngineeringReview).where(EngineeringReview.project_id == project_id).order_by(EngineeringReview.created_at.desc())).all()]


@router.post("/projects/{project_id}/engineering-reviews")
def create_engineering_review(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    project = _project(db, project_id)
    document_id = payload.get("drawing_document_id")
    drawing = db.get(Document, document_id) if document_id else db.scalar(select(Document).where(Document.project_id == project_id).order_by(Document.created_at))
    if not drawing or drawing.project_id != project_id:
        raise HTTPException(409, "DRAWING_DOCUMENT_REQUIRED")
    review = EngineeringReview(project_id=project.id, discipline=payload.get("discipline", "SYNTHETIC_DEMO_DISCIPLINE"),
                               drawing_document_id=drawing.id, status="CREATED", authorized_engineer_user_id=payload.get("authorized_engineer_user_id"),
                               current_drawing_version_id=drawing.current_version_id)
    db.add(review)
    db.flush()
    _audit(db, request, "ENGINEERING_REVIEW_CREATED", "EngineeringReview", review.id, payload.get("actor", "synthetic-engineering"), {"project_id": project.id, "drawing_document_id": drawing.id})
    db.commit()
    return _row(review)


@router.get("/engineering-reviews/{review_id}")
def engineering_review_detail(review_id: str, db: Session = Depends(get_db)):
    review = _require(db, EngineeringReview, review_id, "ENGINEERING_REVIEW_NOT_FOUND")
    scope = db.get(EngineeringReviewScope, review.current_scope_id) if review.current_scope_id else None
    runs = db.scalars(select(EngineeringReviewRun).where(EngineeringReviewRun.engineering_review_id == review.id).order_by(EngineeringReviewRun.created_at)).all()
    return {"review": _row(review), "scope": _row(scope), "runs": [_row(item) for item in runs], "synthetic_only": True}


@router.post("/engineering-reviews/{review_id}/scope")
def configure_engineering_scope(review_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    review = _require(db, EngineeringReview, review_id, "ENGINEERING_REVIEW_NOT_FOUND")
    scope = _engineering_scope(db, review, payload, request)
    db.commit()
    return _row(scope)


@router.get("/engineering-reviews/{review_id}/applicable-regulations")
def applicable_regulations(review_id: str, db: Session = Depends(get_db)):
    review = _require(db, EngineeringReview, review_id, "ENGINEERING_REVIEW_NOT_FOUND")
    scope = db.get(EngineeringReviewScope, review.current_scope_id) if review.current_scope_id else None
    if not scope:
        return {"scope": None, "regulations": [], "applicability": []}
    versions = [db.get(RegulationVersion, value) for value in scope.selected_regulation_version_ids]
    return {"scope": _row(scope), "regulations": [_row(item) for item in versions if item],
            "applicability": [_row(item) for item in db.scalars(select(RegulationApplicability).where(RegulationApplicability.review_scope_id == scope.id)).all()]}


@router.post("/engineering-reviews/{review_id}/regulation-applicability/review")
def review_regulation_applicability(review_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    review = _require(db, EngineeringReview, review_id, "ENGINEERING_REVIEW_NOT_FOUND")
    scope = db.get(EngineeringReviewScope, review.current_scope_id) if review.current_scope_id else None
    if not scope:
        raise HTTPException(409, "ENGINEERING_SCOPE_REQUIRED")
    actor_id, actor_role = _actor(payload, "synthetic-engineer")
    _require_role(actor_role, ENGINEER_ROLES, "AUTHORIZED_ENGINEER_REQUIRED_FOR_APPLICABILITY")
    version = _require(db, RegulationVersion, payload["regulation_version_id"], "REGULATION_VERSION_NOT_FOUND")
    status = payload.get("applicability_status", "HUMAN_REVIEW_REQUIRED")
    if status == "APPROVED_APPLICABLE" and version.content_status not in TRUSTED_REGULATION_STATES:
        raise HTTPException(409, "UNAPPROVED_REGULATION_CANNOT_BE_APPROVED_AS_AUTHORITY")
    item = db.scalar(select(RegulationApplicability).where(RegulationApplicability.review_scope_id == scope.id, RegulationApplicability.regulation_version_id == version.id))
    if not item:
        item = RegulationApplicability(regulation_version_id=version.id, context_type="ENGINEERING_REVIEW_SCOPE", context_id=scope.id,
                                       review_scope_id=scope.id, discipline=scope.discipline)
        db.add(item)
    item.applicability_status = status
    item.approved_by_user_id = _persisted_user_id(db, actor_id) if status.startswith("APPROVED") else None
    item.effective_at = _now() if status.startswith("APPROVED") else None
    item.basis_evidence = {"basis": payload.get("basis", scope.applicability_basis), "evidence_reference": payload.get("evidence_reference", "synthetic://applicability")}
    db.flush()
    _audit(db, request, "REGULATION_APPLICABILITY_APPROVED" if status.startswith("APPROVED") else "REGULATION_APPLICABILITY_PROPOSED", "RegulationApplicability", item.id, actor_id, _row(item))
    db.commit()
    return _row(item)


def _create_review_run(db: Session, review: EngineeringReview, scope: EngineeringReviewScope, drawing: DocumentVersion, payload: dict, request: Request) -> EngineeringReviewRun:
    document = db.get(Document, drawing.document_id)
    if not document or document.project_id != review.project_id or document.id != review.drawing_document_id:
        raise HTTPException(409, "DRAWING_VERSION_PROJECT_OR_IDENTITY_MISMATCH")
    versions, applicability = _regulation_snapshot(db, scope, review, require_approved=True)
    run = EngineeringReviewRun(engineering_review_id=review.id, drawing_document_version_id=drawing.id, review_scope_id=scope.id,
                               pinned_drawing_hash=drawing.sha256, pinned_revision_label=drawing.revision_label,
                               regulation_applicability_snapshot={"version_ids": [item.id for item in versions], "applicability_ids": [item.id for item in applicability],
                                                                  "content_statuses": [item.content_status for item in versions], "trusted": True},
                               model_config_version=payload.get("model_config_version", "E5-DETERMINISTIC-ADVISORY-1.0"),
                               prompt_bundle_version=payload.get("prompt_bundle_version", "E5-SYNTHETIC-BOUNDARY-1.0"),
                               evidence_recipe={"universe": "pinned drawing + approved applicable regulation versions + approved project references", "open_web": False},
                               status="READY_FOR_ANALYSIS")
    db.add(run)
    db.flush()
    cycle_number = (db.scalar(select(func.max(DrawingReviewCycle.cycle_number)).where(DrawingReviewCycle.project_id == review.project_id, DrawingReviewCycle.discipline == scope.discipline)) or 0) + 1
    db.add(DrawingReviewCycle(project_id=review.project_id, discipline=scope.discipline, cycle_number=cycle_number,
                              input_drawing_version_id=drawing.id, review_run_id=run.id, status="CURRENT"))
    review.current_drawing_version_id = drawing.id
    review.status = "READY_FOR_ANALYSIS"
    _audit(db, request, "ENGINEERING_REVIEW_RUN_CREATED", "EngineeringReviewRun", run.id, payload.get("actor", "synthetic-engineering"), _row(run))
    _task(db, review.project_id, "RUN_ENGINEERING_ADVISORY", "Run bounded engineering advisory", "ENGINEERING_REVIEW_ASSISTANT", "EngineeringReviewRun", run.id, request)
    return run


@router.post("/engineering-reviews/{review_id}/runs")
def create_engineering_run(review_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    review = _require(db, EngineeringReview, review_id, "ENGINEERING_REVIEW_NOT_FOUND")
    scope = db.get(EngineeringReviewScope, payload.get("review_scope_id") or review.current_scope_id)
    if not scope:
        raise HTTPException(409, "ENGINEERING_SCOPE_REQUIRED")
    drawing = _drawing_version(db, payload.get("drawing_document_version_id") or review.current_drawing_version_id or "")
    run = _create_review_run(db, review, scope, drawing, payload, request)
    db.commit()
    return _row(run)


@router.get("/engineering-review-runs/{run_id}")
def engineering_run_detail(run_id: str, db: Session = Depends(get_db)):
    run = _require(db, EngineeringReviewRun, run_id, "ENGINEERING_REVIEW_RUN_NOT_FOUND")
    return {"run": _row(run), "comments": [_row(item) for item in db.scalars(select(EngineeringComment).where(EngineeringComment.engineering_review_run_id == run.id).order_by(EngineeringComment.comment_number)).all()]}


@router.post("/engineering-review-runs/{run_id}/analyze")
def analyze_engineering_run(run_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    run = _require(db, EngineeringReviewRun, run_id, "ENGINEERING_REVIEW_RUN_NOT_FOUND")
    if run.status not in {"READY_FOR_ANALYSIS", "CREATED"}:
        raise HTTPException(409, "ENGINEERING_RUN_NOT_ANALYZABLE")
    drawing = _drawing_version(db, run.drawing_document_version_id)
    if drawing.sha256 != run.pinned_drawing_hash or drawing.revision_label != run.pinned_revision_label:
        run.status = "INVALID_INPUT"
        _audit(db, request, "ENGINEERING_REVIEW_INVALIDATED", "EngineeringReviewRun", run.id, payload.get("actor", "synthetic-engineering"), {"reason": "DRAWING_VERSION_MISMATCH"})
        db.commit()
        raise HTTPException(409, "DRAWING_VERSION_MISMATCH_REVIEW_REQUIRED")
    run.status = "ANALYZING"
    _audit(db, request, "ENGINEERING_ANALYSIS_STARTED", "EngineeringReviewRun", run.id, payload.get("actor", "synthetic-engineering"), {"ai_advisory_only": True, "open_web": False})
    scope = _require(db, EngineeringReviewScope, run.review_scope_id, "ENGINEERING_SCOPE_REQUIRED")
    versions, _ = _regulation_snapshot(db, scope, db.get(EngineeringReview, run.engineering_review_id), require_approved=True)
    sufficient = payload.get("evidence_sufficient", True)
    existing_count = db.scalar(select(func.count(EngineeringComment.id)).where(EngineeringComment.engineering_review_run_id == run.id)) or 0
    if sufficient:
        discipline_code = "".join(ch for ch in scope.discipline.upper() if ch.isalnum())[:8] or "GEN"
        number = int(existing_count) + 1
        regulation = versions[0]
        comment = EngineeringComment(engineering_review_run_id=run.id, drawing_document_version_id=drawing.id, comment_number=number,
                                     stable_comment_number=f"ENG-{discipline_code}-{number:03d}", source_type="PROPOSED_BY_AI",
                                     proposed_text=payload.get("proposed_text", "Candidate discrepancy requires Authorized Engineer review; this is not a compliance certification."),
                                     location_reference=payload.get("location_reference", "synthetic://drawing/location/unspecified"),
                                     issue_text=payload.get("issue_text", "Candidate issue identified for human review."),
                                     rationale=payload.get("rationale", "Bounded comparison against the pinned drawing and cited controlled source."),
                                     regulation_version_id=regulation.id, regulation_evidence_reference=payload.get("regulation_evidence_reference", f"{regulation.source_uri_or_reference}#synthetic-clause"),
                                     evidence_reference=payload.get("evidence_reference", f"synthetic://drawing/{drawing.id}#evidence"), status="PROPOSED",
                                     engineer_disposition="NOT_DISPOSED", uncertainty_state="SUPPORTED_EVIDENCE", severity=payload.get("severity", "ADVISORY"),
                                     blocking=bool(payload.get("blocking", False)), required_action=payload.get("required_action", "Authorized Engineer to review and decide."),
                                     evidence_snapshot={"drawing_version_id": drawing.id, "drawing_hash": drawing.sha256, "regulation_version_id": regulation.id, "regulation_status": regulation.content_status})
        db.add(comment)
        db.flush()
        _audit(db, request, "ENGINEERING_COMMENT_PROPOSED", "EngineeringComment", comment.id, payload.get("actor", "engineering-advisory"), {"source_type": "PROPOSED_BY_AI", "not_engineer_approved": True, "stable_comment_number": comment.stable_comment_number})
    else:
        _audit(db, request, "ENGINEERING_ANALYSIS_ABSTAINED", "EngineeringReviewRun", run.id, payload.get("actor", "engineering-advisory"), {"uncertainty_state": "HUMAN_REVIEW_REQUIRED", "confident_compliance_claim": False})
    run.status = "PROPOSED_COMMENTS_READY"
    db.commit()
    return {"run": _row(run), "comments": [_row(item) for item in db.scalars(select(EngineeringComment).where(EngineeringComment.engineering_review_run_id == run.id).order_by(EngineeringComment.comment_number)).all()], "ai_advisory_only": True}


@router.get("/engineering-review-runs/{run_id}/comments")
def engineering_comments(run_id: str, db: Session = Depends(get_db)):
    _require(db, EngineeringReviewRun, run_id, "ENGINEERING_REVIEW_RUN_NOT_FOUND")
    return [_row(item) for item in db.scalars(select(EngineeringComment).where(EngineeringComment.engineering_review_run_id == run_id).order_by(EngineeringComment.comment_number)).all()]


@router.post("/engineering-comments/{comment_id}/engineer-disposition")
def engineer_disposition(comment_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    comment = _require(db, EngineeringComment, comment_id, "ENGINEERING_COMMENT_NOT_FOUND")
    run = _require(db, EngineeringReviewRun, comment.engineering_review_run_id, "ENGINEERING_REVIEW_RUN_NOT_FOUND")
    review = _require(db, EngineeringReview, run.engineering_review_id, "ENGINEERING_REVIEW_NOT_FOUND")
    actor_id, actor_role = _actor(payload, "synthetic-engineer")
    _require_role(actor_role, ENGINEER_ROLES, "AUTHORIZED_ENGINEER_REQUIRED")
    action = payload.get("action", "REQUEST_MORE_EVIDENCE")
    allowed = {"ACCEPT_COMMENT", "MODIFY_AND_ACCEPT", "REJECT_COMMENT", "REQUEST_MORE_EVIDENCE", "MARK_NOT_APPLICABLE", "RETURN_DRAWING_FOR_CORRECTION"}
    if action not in allowed:
        raise HTTPException(422, "UNSUPPORTED_ENGINEER_DISPOSITION")
    comment.engineer_disposition = action
    comment.engineer_notes = payload.get("notes")
    comment.re_reviewed_at = _now()
    comment.assigned_at = comment.assigned_at or _now()
    if action == "ACCEPT_COMMENT":
        comment.status = "ENGINEER_ACCEPTED"
        comment.closure_state = "OPEN"
        comment.required_action = payload.get("required_action", comment.required_action)
        review.status = "ACCEPTED_WITH_COMMENTS"
        event = "ENGINEERING_COMMENT_ENGINEER_ACCEPTED"
    elif action == "MODIFY_AND_ACCEPT":
        comment.status = "ENGINEER_MODIFIED"
        comment.proposed_text = payload.get("modified_text", comment.proposed_text)
        comment.closure_state = "OPEN"
        review.status = "ACCEPTED_WITH_COMMENTS"
        event = "ENGINEERING_COMMENT_ENGINEER_MODIFIED"
    elif action == "REJECT_COMMENT":
        comment.status = "ENGINEER_REJECTED"
        comment.closure_state = "NOT_APPLICABLE"
        comment.resolved_at = _now()
        event = "ENGINEERING_COMMENT_ENGINEER_REJECTED"
    elif action == "REQUEST_MORE_EVIDENCE":
        comment.status = "HUMAN_REVIEW_REQUIRED"
        comment.uncertainty_state = "HUMAN_REVIEW_REQUIRED"
        event = "ENGINEERING_COMMENT_MORE_EVIDENCE_REQUESTED"
    elif action == "MARK_NOT_APPLICABLE":
        comment.status = "NOT_APPLICABLE"
        comment.closure_state = "NOT_APPLICABLE"
        comment.resolved_at = _now()
        event = "ENGINEERING_COMMENT_RESOLVED"
    else:
        comment.status = "CORRECTION_REQUIRED"
        comment.closure_state = "OPEN"
        review.status = "ACCEPTED_WITH_COMMENTS"
        event = "ENGINEERING_COMMENT_CORRECTION_REQUESTED"
        _task(db, review.project_id, "CORRECT_DRAWING", "Correct drawing for engineering comment", "PROJECT_PERMIT_COORDINATION_ASSISTANT", "EngineeringComment", comment.id, request)
    _audit(db, request, event, "EngineeringComment", comment.id, actor_id, {"action": action, "authorized_role": actor_role, "ai_authority": False})
    db.commit()
    return _row(comment)


@router.post("/engineering-review-runs/{run_id}/engineer-no-comment")
def engineer_no_comment(run_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    run = _require(db, EngineeringReviewRun, run_id, "ENGINEERING_REVIEW_RUN_NOT_FOUND")
    actor_id, actor_role = _actor(payload, "synthetic-engineer")
    _require_role(actor_role, ENGINEER_ROLES, "AUTHORIZED_ENGINEER_REQUIRED")
    run.status = "NO_COMMENT_AFTER_ENGINEER_REVIEW"
    _audit(db, request, "ENGINEERING_NO_COMMENT_CONFIRMED", "EngineeringReviewRun", run.id, actor_id, {"explicit_engineer_disposition": True, "notes": payload.get("notes")})
    db.commit()
    return _row(run)


def _render_engineering_sheet(db: Session, run: EngineeringReviewRun, artifact_type: str, payload: dict, request: Request):
    review = _require(db, EngineeringReview, run.engineering_review_id, "ENGINEERING_REVIEW_NOT_FOUND")
    scope = _require(db, EngineeringReviewScope, run.review_scope_id, "ENGINEERING_SCOPE_REQUIRED")
    comments = db.scalars(select(EngineeringComment).where(EngineeringComment.engineering_review_run_id == run.id).order_by(EngineeringComment.comment_number)).all()
    source_ids = [run.id, run.drawing_document_version_id, scope.id] + [item.id for item in comments]
    artifact = render_artifact(db, artifact_type=artifact_type, context_type="ENGINEERING_REVIEW_RUN", context_id=run.id,
                               payload={"label": "Engineering Review / Compliance Review Sheet", "project_id": review.project_id,
                                        "drawing_version_id": run.drawing_document_version_id, "drawing_hash": run.pinned_drawing_hash,
                                        "discipline": scope.discipline, "scope_id": scope.id, "regulation_snapshot": run.regulation_applicability_snapshot,
                                        "comments": [_row(item) for item in comments], "not_a_certificate": True, **payload},
                               source_revision_ids=source_ids, template_version_id=payload.get("template_version_id"), actor=payload.get("actor", "synthetic-renderer"), correlation_id=_cid(request), project_id=review.project_id)
    event = "COMPLIANCE_SHEET_RENDERED" if artifact_type == "COMPLIANCE_SHEET" else "ENGINEERING_COMMENT_SHEET_RENDERED"
    _audit(db, request, event, "RenderedArtifact", artifact.id, payload.get("actor", "synthetic-renderer"), {"run_id": run.id, "template_version_id": artifact.template_version_id, "content_hash": artifact.content_hash})
    return artifact


@router.post("/engineering-review-runs/{run_id}/render-compliance-sheet")
def render_compliance_sheet(run_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    run = _require(db, EngineeringReviewRun, run_id, "ENGINEERING_REVIEW_RUN_NOT_FOUND")
    artifact = _render_engineering_sheet(db, run, "COMPLIANCE_SHEET", payload, request)
    db.commit()
    return {"artifact": _row(artifact), "status_label": "ENGINEERING REVIEW / COMPLIANCE REVIEW SHEET — NOT AN APPROVED CERTIFICATE"}


@router.post("/engineering-review-runs/{run_id}/render-comment-sheet")
def render_comment_sheet(run_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    run = _require(db, EngineeringReviewRun, run_id, "ENGINEERING_REVIEW_RUN_NOT_FOUND")
    comments = db.scalars(select(EngineeringComment).where(EngineeringComment.engineering_review_run_id == run.id, EngineeringComment.engineer_disposition.in_(["ACCEPT_COMMENT", "MODIFY_AND_ACCEPT"]))).all()
    if not comments:
        raise HTTPException(409, "ENGINEER_ACCEPTED_COMMENTS_REQUIRED")
    artifact = _render_engineering_sheet(db, run, "COMMENT_SHEET", {**payload, "accepted_comment_count": len(comments)}, request)
    db.commit()
    return {"artifact": _row(artifact), "accepted_comments": [_row(item) for item in comments]}


@router.get("/engineering-reviews/{review_id}/block-time")
def engineering_block_time(review_id: str, db: Session = Depends(get_db)):
    review = _require(db, EngineeringReview, review_id, "ENGINEERING_REVIEW_NOT_FOUND")
    now = _now()
    items = []
    for comment in db.scalars(select(EngineeringComment).join(EngineeringReviewRun).where(EngineeringReviewRun.engineering_review_id == review.id).order_by(EngineeringComment.comment_number)).all():
        end = _aware(comment.resolved_at or now)
        opened = _aware(comment.opened_at or comment.created_at)
        elapsed = max(0, int((end - opened).total_seconds()))
        blocked_start = _aware(comment.assigned_at or comment.opened_at or comment.created_at)
        blocked = max(0, int((end - blocked_start).total_seconds())) if comment.status in {"CORRECTION_REQUIRED", "HUMAN_REVIEW_REQUIRED"} else 0
        items.append({"comment_number": comment.stable_comment_number or comment.comment_number, "opened_at": comment.opened_at, "assigned_at": comment.assigned_at,
                      "correction_received_at": comment.correction_received_at, "engineer_re_reviewed_at": comment.re_reviewed_at,
                      "resolved_at": comment.resolved_at, "current_status": comment.status, "elapsed_open_seconds": elapsed,
                      "elapsed_blocked_seconds": blocked, "duration_semantics": "OBSERVED_DURATION_ONLY"})
    return {"review_id": review.id, "items": jsonable_encoder(items), "sla_claim": False}


@router.post("/engineering-reviews/{review_id}/new-drawing-version")
def new_drawing_version(review_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    review = _require(db, EngineeringReview, review_id, "ENGINEERING_REVIEW_NOT_FOUND")
    document = _require(db, Document, review.drawing_document_id, "DRAWING_DOCUMENT_NOT_FOUND")
    previous = _current_version(db, document.id)
    version_number = (previous.version_number if previous else 0) + 1
    content = payload.get("content", f"synthetic drawing revision {version_number}")
    digest = hashlib.sha256(content.encode()).hexdigest()
    version = DocumentVersion(document_id=document.id, version_number=version_number, source_filename=payload.get("source_filename", f"drawing-v{version_number}.pdf"),
                              source_path_or_reference=payload.get("source_path_or_reference", f"synthetic://drawing/{document.id}/v{version_number}"), sha256=digest,
                              mime_type="application/pdf", file_size=len(content), language="EN", revision_label=payload.get("revision_label", f"V{version_number}"),
                              approval_state=DocumentApprovalState.WORKING, source_system="SYNTHETIC_E5", metadata_json={"synthetic_only": True, "material_change": True})
    db.add(version)
    db.flush()
    if previous:
        previous.superseded_by = version.id
    document.current_version_id = version.id
    review.current_drawing_version_id = version.id
    cycles = db.scalars(select(DrawingReviewCycle).where(DrawingReviewCycle.project_id == review.project_id, DrawingReviewCycle.discipline == review.discipline, DrawingReviewCycle.status.in_(["OPEN", "CURRENT"]))).all()
    for cycle in cycles:
        cycle.status = "HISTORICAL"
        cycle.material_change_reason = "DRAWING_NEW_VERSION"
        cycle.invalidated_at = _now()
        run = db.get(EngineeringReviewRun, cycle.review_run_id)
        if run and run.status not in {"STALE", "SUPERSEDED"}:
            run.status = "STALE"
            _audit(db, request, "ENGINEERING_REVIEW_INVALIDATED", "EngineeringReviewRun", run.id, payload.get("actor", "synthetic-engineering"), {"reason": "DRAWING_NEW_VERSION", "new_version_id": version.id})
    _audit(db, request, "DRAWING_NEW_VERSION_REGISTERED", "DocumentVersion", version.id, payload.get("actor", "synthetic-engineering"), {"previous_version_id": previous.id if previous else None, "material_change": True})
    db.commit()
    return {"drawing_version": _row(version), "old_review_state": "HISTORICAL_STALE", "new_run_required": True}


@router.post("/engineering-reviews/{review_id}/re-review")
def engineering_re_review(review_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    review = _require(db, EngineeringReview, review_id, "ENGINEERING_REVIEW_NOT_FOUND")
    scope = _require(db, EngineeringReviewScope, review.current_scope_id, "ENGINEERING_SCOPE_REQUIRED")
    drawing = _drawing_version(db, payload.get("drawing_document_version_id") or review.current_drawing_version_id or "")
    run = _create_review_run(db, review, scope, drawing, {**payload, "actor": payload.get("actor", "synthetic-engineering")}, request)
    _audit(db, request, "ENGINEERING_RE_REVIEW_STARTED", "EngineeringReviewRun", run.id, payload.get("actor", "synthetic-engineering"), {"prior_run_ids": [item.id for item in db.scalars(select(EngineeringReviewRun).where(EngineeringReviewRun.engineering_review_id == review.id, EngineeringReviewRun.id != run.id)).all()]})
    db.commit()
    return _row(run)


def _contract_context(db: Session, contract: Contract):
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else db.scalar(select(ContractRevision).where(ContractRevision.contract_id == contract.id).order_by(ContractRevision.revision_number.desc()))
    milestone = db.scalar(select(ContractMilestone).where(ContractMilestone.contract_id == contract.id, ContractMilestone.contract_revision_id == revision.id).order_by(ContractMilestone.id)) if revision else None
    return revision, milestone


@router.get("/contracts/{contract_id}/invoice-requirement")
def invoice_requirement(contract_id: str, db: Session = Depends(get_db)):
    contract = _require(db, Contract, contract_id, "CONTRACT_NOT_FOUND")
    revision, milestone = _contract_context(db, contract)
    decision = db.scalar(select(InvoiceRequirementDecision).where(InvoiceRequirementDecision.contract_id == contract.id).order_by(InvoiceRequirementDecision.decided_at.desc()))
    return {"contract": _row(contract), "contract_revision": _row(revision), "milestone": _row(milestone), "decision": _row(decision), "authority": "HUMAN_DECISION_OR_CONFIGURED_DETERMINISTIC_RULE"}


@router.post("/contracts/{contract_id}/invoice-requirement/decision")
def decide_invoice_requirement(contract_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    contract = _require(db, Contract, contract_id, "CONTRACT_NOT_FOUND")
    revision, milestone = _contract_context(db, contract)
    if not revision:
        raise HTTPException(409, "CONTRACT_REVISION_REQUIRED")
    actor_id, actor_role = _actor(payload, "synthetic-finance")
    source = payload.get("decision_source", "HUMAN_DECISION")
    if source not in {"HUMAN_DECISION", "CONFIGURED_DETERMINISTIC_RULE"}:
        raise HTTPException(403, "AI_INFERRED_INVOICE_AUTHORITY_NOT_ALLOWED")
    if source == "HUMAN_DECISION":
        _require_role(actor_role, FINANCE_ROLES, "FINANCE_AUTHORITY_REQUIRED")
    decision_value = payload.get("decision", "NEEDS_REVIEW")
    if decision_value not in {"REQUIRED", "NOT_REQUIRED", "NEEDS_REVIEW"}:
        raise HTTPException(422, "UNSUPPORTED_INVOICE_REQUIREMENT_DECISION")
    decision = InvoiceRequirementDecision(contract_id=contract.id, contract_revision_id=revision.id, milestone_id=milestone.id if milestone else None,
                                         decision=decision_value, decision_source=source, reason=payload.get("reason", "Synthetic bounded decision; signed rule/evidence required for real use."),
                                         decided_by=actor_id if source == "HUMAN_DECISION" else None, rule_id=payload.get("rule_id") if source == "CONFIGURED_DETERMINISTIC_RULE" else None,
                                         evidence={"reference": payload.get("evidence_reference", "synthetic://invoice-requirement"), "synthetic_only": True})
    db.add(decision)
    db.flush()
    _audit(db, request, "INVOICE_REQUIREMENT_DECIDED", "InvoiceRequirementDecision", decision.id, actor_id, {"decision": decision_value, "decision_source": source, "ai_authority": False})
    db.commit()
    return _row(decision)


def _latest_invoice_revision(db: Session, invoice: Invoice) -> InvoiceRevision | None:
    return db.scalar(select(InvoiceRevision).where(InvoiceRevision.invoice_id == invoice.id).order_by(InvoiceRevision.revision_number.desc()))


@router.post("/contracts/{contract_id}/invoices")
def create_invoice(contract_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    contract = _require(db, Contract, contract_id, "CONTRACT_NOT_FOUND")
    decision = db.scalar(select(InvoiceRequirementDecision).where(InvoiceRequirementDecision.contract_id == contract.id).order_by(InvoiceRequirementDecision.decided_at.desc()))
    if not decision or decision.decision != "REQUIRED":
        raise HTTPException(409, "INVOICE_REQUIRED_DECISION_NOT_REQUIRED")
    revision, milestone = _contract_context(db, contract)
    reference = payload.get("invoice_reference", f"SYN-INV-{str(contract.id)[:8]}-{int(datetime.now().timestamp())}")
    invoice = Invoice(contract_id=contract.id, invoice_reference=reference, status="DRAFT", requirement_decision_id=decision.id)
    db.add(invoice)
    db.flush()
    invoice_revision = InvoiceRevision(invoice_id=invoice.id, revision_number=1, controlling_contract_revision_id=revision.id,
                                      controlling_milestone_id=milestone.id if milestone else None, status="DRAFT",
                                      source_snapshot={"contract_id": contract.id, "contract_revision_id": revision.id, "milestone_id": milestone.id if milestone else None, "decision_id": decision.id, "synthetic_only": True})
    db.add(invoice_revision)
    db.flush()
    invoice.current_revision_id = invoice_revision.id
    if milestone:
        db.add(InvoiceMilestone(invoice_id=invoice.id, contract_milestone_id=milestone.id, status="TRACK_ONLY"))
    db.add(LineageEdge(project_id=payload.get("project_id") or _project_for_contract(db, contract).id, upstream_type="ContractRevision", upstream_id=revision.id, upstream_version_or_hash=stable_hash(revision.id), downstream_type="InvoiceRevision", downstream_id=invoice_revision.id, downstream_version_or_hash=stable_hash(invoice_revision.id), dependency_kind="INVOICE_DERIVED_FROM_CONTRACT", correlation_id=_cid(request)))
    _audit(db, request, "INVOICE_CREATED", "Invoice", invoice.id, payload.get("actor", "synthetic-finance"), {"invoice_revision_id": invoice_revision.id, "decision_id": decision.id})
    _audit(db, request, "INVOICE_REVISION_CREATED", "InvoiceRevision", invoice_revision.id, payload.get("actor", "synthetic-finance"), _row(invoice_revision))
    db.commit()
    return {"invoice": _row(invoice), "revision": _row(invoice_revision), "decision": _row(decision)}


def _project_for_contract(db: Session, contract: Contract) -> Project:
    reference = db.scalar(select(ReferenceNumber).where(ReferenceNumber.contract_id == contract.id, ReferenceNumber.project_id.is_not(None)))
    if reference and reference.project_id:
        return _project(db, reference.project_id)
    return db.scalar(select(Project).order_by(Project.project_number)) or (_raise("SYNTHETIC_PROJECT_REQUIRED"))


def _raise(detail: str):
    raise HTTPException(409, detail)


@router.get("/invoices/{invoice_id}")
def invoice_detail(invoice_id: str, db: Session = Depends(get_db)):
    invoice = _require(db, Invoice, invoice_id, "INVOICE_NOT_FOUND")
    revision = _latest_invoice_revision(db, invoice)
    return {"invoice": _row(invoice), "revision": _row(revision), "handoffs": [_row(item) for item in db.scalars(select(AccountingHandoff).where(AccountingHandoff.invoice_id == invoice.id)).all()], "evidence": [_row(item) for item in db.scalars(select(FinanceEvidence).where(FinanceEvidence.invoice_id == invoice.id).order_by(FinanceEvidence.recorded_at)).all()], "lineage": [_row(item) for item in db.scalars(select(LineageEdge).where(LineageEdge.downstream_type == "InvoiceRevision", LineageEdge.downstream_id == (revision.id if revision else ""))).all()]}


@router.post("/invoice-revisions/{revision_id}/revisions")
def create_invoice_revision(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    previous = _require(db, InvoiceRevision, revision_id, "INVOICE_REVISION_NOT_FOUND")
    invoice = _require(db, Invoice, previous.invoice_id, "INVOICE_NOT_FOUND")
    contract = _require(db, Contract, invoice.contract_id, "CONTRACT_NOT_FOUND")
    controlling, milestone = _contract_context(db, contract)
    if controlling.id != previous.controlling_contract_revision_id:
        previous.status = "STALE"
        previous.stale_reason = "CONTRACT_REVISION_CHANGED"
    next_revision = InvoiceRevision(invoice_id=invoice.id, revision_number=previous.revision_number + 1, controlling_contract_revision_id=controlling.id,
                                    controlling_milestone_id=milestone.id if milestone else None, supersedes_revision_id=previous.id, status="DRAFT",
                                    source_snapshot={"contract_id": contract.id, "contract_revision_id": controlling.id, "milestone_id": milestone.id if milestone else None, "synthetic_only": True})
    db.add(next_revision)
    db.flush()
    invoice.current_revision_id = next_revision.id
    invoice.status = "DRAFT"
    _audit(db, request, "INVOICE_REVISION_CREATED", "InvoiceRevision", next_revision.id, payload.get("actor", "synthetic-finance"), {"supersedes_revision_id": previous.id, "material_change_revalidation": previous.status == "STALE"})
    db.commit()
    return _row(next_revision)


@router.post("/invoices/{invoice_id}/revisions")
def create_invoice_revision_from_invoice(invoice_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    """Invoice-facing alias required by the bounded E6 contract."""
    invoice = _require(db, Invoice, invoice_id, "INVOICE_NOT_FOUND")
    previous = _latest_invoice_revision(db, invoice)
    if not previous:
        raise HTTPException(409, "INVOICE_REVISION_REQUIRED")
    return create_invoice_revision(str(previous.id), payload, request, db)


@router.post("/invoice-revisions/{revision_id}/render")
def render_invoice(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = _require(db, InvoiceRevision, revision_id, "INVOICE_REVISION_NOT_FOUND")
    invoice = _require(db, Invoice, revision.invoice_id, "INVOICE_NOT_FOUND")
    contract = _require(db, Contract, invoice.contract_id, "CONTRACT_NOT_FOUND")
    controlling, milestone = _contract_context(db, contract)
    if revision.controlling_contract_revision_id != controlling.id:
        revision.status = "STALE"
        revision.stale_reason = "CONTRACT_REVISION_CHANGED"
        db.commit()
        raise HTTPException(409, "INVOICE_REVISION_STALE_REVALIDATION_REQUIRED")
    artifact = render_artifact(db, artifact_type="INVOICE", context_type="INVOICE_REVISION", context_id=revision.id,
                               payload={"invoice_reference": invoice.invoice_reference, "contract_reference": contract.contract_reference, "contract_revision_id": controlling.id,
                                        "milestone_id": milestone.id if milestone else None, "status": "DRAFT", "synthetic_label": "SYNTHETIC / NOT CLIENT APPROVED", **payload},
                               source_revision_ids=[contract.id, controlling.id, revision.id] + ([milestone.id] if milestone else []), template_version_id=payload.get("template_version_id"),
                               actor=payload.get("actor", "synthetic-finance"), correlation_id=_cid(request), project_id=_project_for_contract(db, contract).id)
    revision.template_version_id = artifact.template_version_id
    revision.rendered_artifact_id = artifact.id
    revision.render_input_hash = artifact.render_input_hash
    revision.content_hash = artifact.content_hash
    revision.status = "READY_FOR_FINANCE_REVIEW"
    invoice.status = "READY_FOR_FINANCE_REVIEW"
    _audit(db, request, "INVOICE_RENDERED", "InvoiceRevision", revision.id, payload.get("actor", "synthetic-finance"), {"artifact_id": artifact.id, "content_hash": artifact.content_hash})
    db.commit()
    return {"revision": _row(revision), "artifact": _row(artifact)}


@router.post("/invoice-revisions/{revision_id}/submit-finance-review")
def submit_invoice_finance_review(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = _require(db, InvoiceRevision, revision_id, "INVOICE_REVISION_NOT_FOUND")
    invoice = _require(db, Invoice, revision.invoice_id, "INVOICE_NOT_FOUND")
    revision.status = "FINANCE_REVIEW"
    invoice.status = "FINANCE_REVIEW"
    _task(db, _project_for_contract(db, _require(db, Contract, invoice.contract_id, "CONTRACT_NOT_FOUND")).id, "FINANCE_REVIEW_INVOICE", "Review invoice for issue", "FINANCE_ACCOUNTANT", "InvoiceRevision", revision.id, request)
    _audit(db, request, "INVOICE_SUBMITTED_FOR_FINANCE_REVIEW", "InvoiceRevision", revision.id, payload.get("actor", "synthetic-finance"), {"finance_role": "FINANCE_ACCOUNTANT"})
    db.commit()
    return _row(revision)


@router.post("/invoice-revisions/{revision_id}/finance-decision")
def finance_decision(revision_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    revision = _require(db, InvoiceRevision, revision_id, "INVOICE_REVISION_NOT_FOUND")
    invoice = _require(db, Invoice, revision.invoice_id, "INVOICE_NOT_FOUND")
    actor_id, actor_role = _actor(payload, "synthetic-finance")
    _require_role(actor_role, FINANCE_ROLES, "FINANCE_ACCOUNTANT_REQUIRED")
    decision = payload.get("decision", "RETURN_FOR_CHANGE")
    if decision not in {"APPROVE_FOR_ISSUE", "RETURN_FOR_CHANGE", "MARK_NOT_REQUIRED", "REQUEST_EVIDENCE"}:
        raise HTTPException(422, "UNSUPPORTED_FINANCE_DECISION")
    approval = Approval(approval_type="FINANCE_INVOICE_APPROVAL", entity_type="InvoiceRevision", entity_id=revision.id, status=decision,
                        decided_by=actor_id, decided_at=_now(), role_at_decision=actor_role, reason=payload.get("reason", "Synthetic finance review"), evidence_refs=[revision.content_hash] if revision.content_hash else [])
    db.add(approval)
    db.flush()
    db.add(InvoiceApproval(invoice_revision_id=revision.id, approval_id=approval.id))
    revision.status = "APPROVED_FOR_ISSUE" if decision == "APPROVE_FOR_ISSUE" else "DRAFT"
    invoice.status = revision.status
    _audit(db, request, "INVOICE_APPROVED_FOR_ISSUE" if decision == "APPROVE_FOR_ISSUE" else "INVOICE_FINANCE_DECISION_RECORDED", "InvoiceRevision", revision.id, actor_id, {"decision": decision, "approval_id": approval.id, "external_issue": False})
    db.commit()
    return {"revision": _row(revision), "approval": _row(approval), "external_issue": False}


@router.post("/invoices/{invoice_id}/accounting-handoff")
def accounting_handoff(invoice_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    invoice = _require(db, Invoice, invoice_id, "INVOICE_NOT_FOUND")
    role = payload.get("assigned_role", "GENERIC_FINANCE_HANDOFF")
    if role not in {"GENERIC_FINANCE_HANDOFF", "FINANCE_ACCOUNTANT"}:
        raise HTTPException(409, "UNRESOLVED_FINANCE_ROUTING_MUST_USE_GENERIC_HANDOFF")
    handoff = AccountingHandoff(invoice_id=invoice.id, assigned_role=role, assigned_user_id=payload.get("assigned_user_id"), status=payload.get("status", "PENDING"),
                                evidence={"synthetic_only": True, "external_accounting_write": False, "route": "GENERIC_FINANCE_HANDOFF"})
    db.add(handoff)
    db.flush()
    revision = _latest_invoice_revision(db, invoice)
    _task(db, _project_for_contract(db, _require(db, Contract, invoice.contract_id, "CONTRACT_NOT_FOUND")).id, "RECORD_INVOICE_ISSUE_EVIDENCE", "Record invoice issue evidence", "FINANCE_ACCOUNTANT", "Invoice", invoice.id, request)
    _audit(db, request, "ACCOUNTING_HANDOFF_CREATED", "AccountingHandoff", handoff.id, payload.get("actor", "synthetic-finance"), {"status": handoff.status, "external_accounting_write": False, "revision_id": revision.id if revision else None})
    db.commit()
    return _row(handoff)


@router.post("/invoices/{invoice_id}/issue-evidence")
def issue_evidence(invoice_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    invoice = _require(db, Invoice, invoice_id, "INVOICE_NOT_FOUND")
    revision = _latest_invoice_revision(db, invoice)
    if not revision or revision.status != "APPROVED_FOR_ISSUE":
        raise HTTPException(409, "INVOICE_FINANCE_APPROVAL_REQUIRED")
    evidence = FinanceEvidence(invoice_id=invoice.id, evidence_type="INVOICE_ISSUE", status="ISSUED_EVIDENCE_RECORDED", source="SYNTHETIC_EXTERNAL_EVENT", evidence_reference=payload.get("evidence_reference", "synthetic://invoice-issued"), recorded_by=payload.get("actor", "synthetic-finance"))
    db.add(evidence)
    invoice.status = "ISSUED_EVIDENCE_RECORDED"
    db.flush()
    _audit(db, request, "INVOICE_ISSUE_EVIDENCE_RECORDED", "FinanceEvidence", evidence.id, payload.get("actor", "synthetic-finance"), {"invoice_status": invoice.status, "accounting_write": False})
    db.commit()
    return {"invoice": _row(invoice), "evidence": _row(evidence), "external_issue": False}


@router.post("/invoices/{invoice_id}/payment-evidence", include_in_schema=False)
def payment_evidence(invoice_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    invoice = _require(db, Invoice, invoice_id, "INVOICE_NOT_FOUND")
    if invoice.status not in {"ISSUED_EVIDENCE_RECORDED", "SENT_EVIDENCE_RECORDED", "FOLLOW_UP"}:
        raise HTTPException(409, "ISSUE_EVIDENCE_REQUIRED_BEFORE_PAYMENT_EVIDENCE")
    evidence = FinanceEvidence(invoice_id=invoice.id, evidence_type="PAYMENT", status="PAID_EVIDENCE_RECORDED", source="SYNTHETIC_EXTERNAL_EVENT", evidence_reference=payload.get("evidence_reference", "synthetic://payment-recorded"), recorded_by=payload.get("actor", "synthetic-finance"))
    db.add(evidence)
    invoice.status = "PAID_EVIDENCE_RECORDED"
    db.flush()
    _audit(db, request, "PAYMENT_EVIDENCE_RECORDED", "FinanceEvidence", evidence.id, payload.get("actor", "synthetic-finance"), {"payment_processing": False})
    db.commit()
    return {"invoice": _row(invoice), "evidence": _row(evidence), "payment_processing": False}


@router.get("/invoices/{invoice_id}/follow-up")
def invoice_followup(invoice_id: str, db: Session = Depends(get_db)):
    invoice = _require(db, Invoice, invoice_id, "INVOICE_NOT_FOUND")
    contract = _require(db, Contract, invoice.contract_id, "CONTRACT_NOT_FOUND")
    revision = _latest_invoice_revision(db, invoice)
    milestone = db.get(ContractMilestone, revision.controlling_milestone_id) if revision and revision.controlling_milestone_id else None
    handoff = db.scalar(select(AccountingHandoff).where(AccountingHandoff.invoice_id == invoice.id).order_by(AccountingHandoff.created_at.desc()))
    evidence = db.scalars(select(FinanceEvidence).where(FinanceEvidence.invoice_id == invoice.id).order_by(FinanceEvidence.recorded_at)).all()
    due = milestone.due_at.isoformat() if milestone and milestone.due_at else None
    state = "PAYMENT_EVIDENCE_RECORDED" if invoice.status == "PAID_EVIDENCE_RECORDED" else ("AWAITING_PAYMENT" if invoice.status in {"ISSUED_EVIDENCE_RECORDED", "SENT_EVIDENCE_RECORDED"} else "AWAITING_ISSUE_EVIDENCE")
    return {"invoice_reference": invoice.invoice_reference, "project_reference": contract.contract_reference, "client": _row(db.get(ClientAccount, contract.client_account_id)), "contract": _row(contract), "milestone": _row(milestone),
            "invoice_required": True, "invoice_status": invoice.status, "issue_date_evidence": next((_row(item) for item in evidence if item.evidence_type == "INVOICE_ISSUE"), None),
            "payment_due_date": due, "payment_due_state": "CONFIGURED" if due else "DUE_DATE_UNKNOWN / NEEDS_REVIEW", "payment_follow_up_state": state,
            "finance_owner": handoff.assigned_role if handoff else "GENERIC_FINANCE_HANDOFF", "last_follow_up": None, "next_action": state, "late_claim": False}


@router.post("/invoices/{invoice_id}/communication-draft")
def invoice_communication(invoice_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    invoice = _require(db, Invoice, invoice_id, "INVOICE_NOT_FOUND")
    contact = db.scalar(select(ClientContact).join(ClientAccount).join(Contract, Contract.client_account_id == ClientAccount.id).where(Contract.id == invoice.contract_id).order_by(ClientContact.id))
    kind = payload.get("communication_type", "INVOICE_FOLLOW_UP")
    if kind not in {"INVOICE_READY_FOR_CLIENT", "INVOICE_FOLLOW_UP", "PAYMENT_FOLLOW_UP"}:
        raise HTTPException(422, "UNSUPPORTED_INVOICE_COMMUNICATION_TYPE")
    draft = create_communication_draft(db, communication_type="INVOICE", context_type="INVOICE", context_id=invoice.id,
                                       subject=payload.get("subject", f"Invoice follow-up — {invoice.invoice_reference}"), body=payload.get("body", f"Reference {invoice.invoice_reference}; status {invoice.status}. Please review through the approved human channel."),
                                       actor=payload.get("actor", "synthetic-finance"), correlation_id=_cid(request), recipient_contact_id=contact.id if contact else None)
    draft.source_revision_ids = [_latest_invoice_revision(db, invoice).id] if _latest_invoice_revision(db, invoice) else []
    draft.source_snapshot = {"invoice_id": invoice.id, "invoice_reference": invoice.invoice_reference, "communication_type": kind, "policy_state": "HUMAN_SEND", "synthetic_only": True}
    _audit(db, request, "INVOICE_COMMUNICATION_DRAFTED", "CommunicationDraft", draft.id, payload.get("actor", "synthetic-finance"), {"policy_state": "HUMAN_SEND", "sent": False})
    db.commit()
    return _row(draft)


def _handover_evaluation(db: Session, project: Project, payload: dict | None = None) -> dict[str, Any]:
    payload = payload or {}
    selected = [str(item) for item in payload.get("selected_deliverables", [])]
    checks = [
        {"code": "PROJECT_EXISTS", "status": "PASS", "reason": "Canonical project/reference exists."},
        {"code": "HANDOVER_TEMPLATE_AVAILABLE", "status": "PASS", "reason": "A synthetic handover template can be selected."},
        {"code": "SELECTED_DELIVERABLES", "status": "PASS" if selected or not payload.get("require_deliverables", False) else "BLOCKED", "reason": "Configured deliverables are present." if selected or not payload.get("require_deliverables", False) else "A configured handover deliverable is missing."},
        {"code": "REQUIRED_HUMAN_APPROVALS", "status": "PASS" if not payload.get("required_approval_missing", False) else "BLOCKED", "reason": "No additional configured approval blocker." if not payload.get("required_approval_missing", False) else "Configured human approval is missing."},
        {"code": "CLIENT_CONTACT", "status": "PASS" if payload.get("client_contact_available", True) else "NEEDS_REVIEW", "reason": "Client contact is available in synthetic context." if payload.get("client_contact_available", True) else "Client contact requires review."},
    ]
    state = "BLOCKED" if any(item["status"] == "BLOCKED" for item in checks) else ("NEEDS_REVIEW" if any(item["status"] == "NEEDS_REVIEW" for item in checks) else "READY")
    return {"project_id": project.id, "state": state, "checks": checks, "selected_deliverables": selected, "auto_project_close": False, "configured_only": True}


@router.get("/projects/{project_id}/handover-readiness")
def handover_readiness(project_id: str, db: Session = Depends(get_db)):
    project = _project(db, project_id)
    current = db.scalar(select(ProjectHandover).where(ProjectHandover.project_id == project.id).order_by(ProjectHandover.created_at.desc()))
    evaluation = _handover_evaluation(db, project, {"selected_deliverables": current.selected_deliverables} if current else None)
    return {"evaluation": evaluation, "handover": _row(current)}


@router.post("/projects/{project_id}/handovers")
def create_handover(project_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    project = _project(db, project_id)
    evaluation = _handover_evaluation(db, project, payload)
    handover = ProjectHandover(project_id=project.id, status="HANDOVER_DRAFT_READY" if evaluation["state"] == "READY" else evaluation["state"], readiness_state=evaluation["state"],
                               readiness_checks=evaluation["checks"], selected_deliverables=evaluation["selected_deliverables"], approval_state="HANDOVER_DRAFT_READY")
    db.add(handover)
    db.flush()
    _audit(db, request, "HANDOVER_READINESS_EVALUATED", "ProjectHandover", handover.id, payload.get("actor", "synthetic-handover"), evaluation)
    _audit(db, request, "PROJECT_HANDOVER_CREATED", "ProjectHandover", handover.id, payload.get("actor", "synthetic-handover"), {"readiness_state": evaluation["state"], "project_closed": False})
    db.commit()
    return {"handover": _row(handover), "evaluation": evaluation}


@router.post("/project-handovers/{handover_id}/render")
def render_handover(handover_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    handover = _require(db, ProjectHandover, handover_id, "PROJECT_HANDOVER_NOT_FOUND")
    if handover.readiness_state != "READY":
        raise HTTPException(409, "HANDOVER_READINESS_BLOCKED")
    project = _project(db, handover.project_id)
    artifact = render_artifact(db, artifact_type="HANDOVER_FORM", context_type="PROJECT_HANDOVER", context_id=handover.id,
                               payload={"project_number": project.project_number, "project_name": project.project_name, "readiness": handover.readiness_checks,
                                        "selected_deliverables": handover.selected_deliverables, "synthetic_label": "SYNTHETIC / NOT CLIENT APPROVED", **payload},
                               source_revision_ids=[handover.id, project.id], template_version_id=payload.get("template_version_id"), actor=payload.get("actor", "synthetic-handover"), correlation_id=_cid(request), project_id=project.id)
    handover.rendered_artifact_id = artifact.id
    handover.status = "HANDOVER_DRAFT_READY"
    _audit(db, request, "HANDOVER_RENDERED", "RenderedArtifact", artifact.id, payload.get("actor", "synthetic-handover"), {"handover_id": handover.id, "download": artifact.storage_reference})
    db.commit()
    return {"handover": _row(handover), "artifact": _row(artifact), "external_email": False}


@router.post("/project-handovers/{handover_id}/approval")
def approve_handover(handover_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    handover = _require(db, ProjectHandover, handover_id, "PROJECT_HANDOVER_NOT_FOUND")
    actor_id, actor_role = _actor(payload, "synthetic-project-owner")
    _require_role(actor_role, HANDOVER_ROLES, "HUMAN_HANDOVER_APPROVER_REQUIRED")
    if not handover.rendered_artifact_id:
        raise HTTPException(409, "HANDOVER_FORM_REQUIRED_BEFORE_APPROVAL")
    approval = Approval(approval_type="HANDOVER_RELEASE", entity_type="ProjectHandover", entity_id=handover.id, status="APPROVED_FOR_RELEASE", decided_by=actor_id,
                        decided_at=_now(), role_at_decision=actor_role, reason=payload.get("reason", "Synthetic human handover approval"), evidence_refs=[handover.rendered_artifact_id])
    db.add(approval)
    db.flush()
    handover.approval_id = approval.id
    handover.approval_state = "HANDOVER_APPROVED_FOR_RELEASE"
    handover.approved_by = actor_id
    handover.approved_role = actor_role
    handover.approved_at = _now()
    _audit(db, request, "HANDOVER_APPROVED_FOR_RELEASE", "ProjectHandover", handover.id, actor_id, {"approval_id": approval.id, "ai_approval": False, "project_closed": False})
    db.commit()
    return {"handover": _row(handover), "approval": _row(approval), "project_closed": False}


@router.post("/project-handovers/{handover_id}/release-evidence")
def release_handover(handover_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    handover = _require(db, ProjectHandover, handover_id, "PROJECT_HANDOVER_NOT_FOUND")
    if handover.approval_state != "HANDOVER_APPROVED_FOR_RELEASE":
        raise HTTPException(409, "HUMAN_HANDOVER_APPROVAL_REQUIRED")
    handover.release_evidence_status = "HANDOVER_RELEASE_EVIDENCE_RECORDED"
    handover.release_evidence = {"source": "SYNTHETIC_EXTERNAL_EVENT", "reference": payload.get("evidence_reference", "synthetic://handover-released"), "recorded_by": payload.get("actor", "synthetic-project-owner"), "recorded_at": _now().isoformat()}
    handover.status = "HANDOVER_RELEASED"
    _audit(db, request, "HANDOVER_RELEASE_EVIDENCE_RECORDED", "ProjectHandover", handover.id, payload.get("actor", "synthetic-project-owner"), {"release_evidence_status": handover.release_evidence_status, "auto_project_close": False})
    db.commit()
    return {"handover": _row(handover), "project_status": _row(_project(db, handover.project_id)), "project_closed": False}


@router.post("/project-handovers/{handover_id}/communication-draft")
def handover_communication(handover_id: str, payload: dict, request: Request, db: Session = Depends(get_db)):
    handover = _require(db, ProjectHandover, handover_id, "PROJECT_HANDOVER_NOT_FOUND")
    project = _project(db, handover.project_id)
    if handover.status != "HANDOVER_RELEASED":
        raise HTTPException(409, "HANDOVER_RELEASE_EVIDENCE_REQUIRED")
    draft = create_communication_draft(db, communication_type="HANDOVER", context_type="PROJECT_HANDOVER", context_id=handover.id,
                                       subject=payload.get("subject", f"Project handover — {project.project_number}"), body=payload.get("body", f"Handover output for {project.project_number} is ready for human review and manual send."),
                                       actor=payload.get("actor", "synthetic-handover"), correlation_id=_cid(request))
    draft.source_revision_ids = [handover.id, handover.rendered_artifact_id] if handover.rendered_artifact_id else [handover.id]
    draft.source_snapshot = {"project_id": project.id, "project_number": project.project_number, "handover_id": handover.id, "artifact_id": handover.rendered_artifact_id, "policy_state": "HUMAN_SEND", "synthetic_only": True}
    handover.communication_draft_id = draft.id
    _audit(db, request, "HANDOVER_COMMUNICATION_DRAFTED", "CommunicationDraft", draft.id, payload.get("actor", "synthetic-handover"), {"policy_state": "HUMAN_SEND", "sent": False})
    db.commit()
    return _row(draft)
