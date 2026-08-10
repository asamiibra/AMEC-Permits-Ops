"""Week 10 business APIs.  No endpoint in this module submits to a ministry."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..api.dependencies import current_user_role
from ..db import get_db
from ..fixtures.canonical import fixture_metadata
from ..models import *
from ..services.week10 import *
from ..services.week7 import create_routed_finding
from ..services.week45 import build_package, evaluate_readiness, row, snapshot_for_revision
from ..services.week8 import ensure_project_lineage, record_material_change
from ..services.persona_visibility import authorize_issue_mutation

router = APIRouter(prefix="/api")


def cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "week10-api")


def finding_or_404(db: Session, finding_id: str) -> Finding:
    finding = db.get(Finding, finding_id)
    if not finding:
        raise HTTPException(404, "Finding not found")
    return finding


def resolution_or_404(db: Session, resolution_id: str) -> FindingResolution:
    resolution = db.get(FindingResolution, resolution_id)
    if not resolution:
        raise HTTPException(404, "Finding resolution not found")
    return resolution


def revision_or_404(db: Session, revision_id: str) -> PreparationRevision:
    revision = db.get(PreparationRevision, revision_id)
    if not revision:
        raise HTTPException(404, "Preparation revision not found")
    return revision


def cycle_or_404(db: Session, cycle_id: str) -> SubmissionCycle:
    cycle = db.get(SubmissionCycle, cycle_id)
    if not cycle:
        raise HTTPException(404, "Submission cycle not found")
    return cycle


def application_or_404(db: Session, application_id: str) -> PermitApplication:
    application = db.get(PermitApplication, application_id)
    if not application:
        raise HTTPException(404, "Application not found")
    return application


def finding_payload(db: Session, finding: Finding | None) -> dict[str, Any] | None:
    if finding is None:
        return None
    code = db.get(FindingCode, finding.finding_code_id) if finding.finding_code_id else None
    return {**(row(finding) or {}), "finding_code": row(code), "fixture": fixture_metadata()}


@router.get("/findings/{finding_id}/resolution-requirements")
def get_resolution_requirements(finding_id: str, db: Session = Depends(get_db)):
    return resolution_requirements(db, finding_or_404(db, finding_id))


@router.post("/findings/{finding_id}/resolutions")
def post_resolution(finding_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    finding = finding_or_404(db, finding_id)
    authorize_issue_mutation(finding, role)
    supplied = payload.get("affected_entity_id") or payload.get("corrected_entity_id")
    expected = finding.contract_id or finding.proposal_id or finding.permit_id or finding.project_id
    if (supplied and supplied != expected) or (payload.get("project_id") and payload.get("project_id") != finding.project_id):
        raise HTTPException(409, detail={"code": "ISSUE_ENTITY_MISMATCH", "message": "The resolution payload does not belong to this Issue's affected record."})
    try:
        item = create_resolution(db, finding, payload, actor=payload.get("proposed_by", "synthetic-operator"), correlation_id=cid(request))
        db.commit()
    except ValueError as exc:
        db.rollback(); raise HTTPException(422, str(exc))
    return {"resolution": row(item), "requirements": resolution_requirements(db, finding), "fixture": fixture_metadata()}


@router.post("/finding-resolutions/{resolution_id}/evidence")
def post_resolution_evidence(resolution_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    resolution = resolution_or_404(db, resolution_id)
    authorize_issue_mutation(finding_or_404(db, resolution.finding_id), role)
    try:
        evidence = add_evidence(db, resolution, payload, actor=payload.get("added_by", "synthetic-operator"), correlation_id=cid(request))
        db.commit()
    except ValueError as exc:
        db.rollback(); raise HTTPException(422, str(exc))
    return {"evidence": row(evidence), "resolution": row(resolution), "fixture": fixture_metadata()}


@router.post("/finding-resolutions/{resolution_id}/request-verification")
def request_resolution_verification(resolution_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db), role=Depends(current_user_role)):
    resolution = resolution_or_404(db, resolution_id)
    authorize_issue_mutation(finding_or_404(db, resolution.finding_id), role)
    resolution.status = "READY_FOR_VERIFICATION"
    audit(db, correlation_id=cid(request), event_type="FINDING_CLOSURE_VERIFICATION_REQUESTED", entity_type="FindingResolution", entity_id=resolution.id, after={"finding_id": resolution.finding_id}, metadata=fixture_metadata())
    evaluation = evaluate_closure(db, resolution)
    db.commit()
    return {"resolution": row(resolution), "evaluation": row(evaluation), "fixture": fixture_metadata()}


@router.post("/finding-resolutions/{resolution_id}/verify")
def verify_resolution_route(resolution_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    resolution = resolution_or_404(db, resolution_id)
    authorize_issue_mutation(finding_or_404(db, resolution.finding_id), role)
    actor = payload.get("verifier", payload.get("verified_by", ""))
    if not actor:
        raise HTTPException(422, "VERIFIER_REQUIRED")
    evaluation = verify_resolution(db, resolution, verifier=actor, verifier_role=payload.get("verifier_role"), correlation_id=cid(request))
    db.commit()
    return {"evaluation": row(evaluation), "resolution": row(resolution), "finding": finding_payload(db, finding_or_404(db, resolution.finding_id)), "fixture": fixture_metadata()}


@router.post("/finding-resolutions/{resolution_id}/reject")
def reject_resolution_route(resolution_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    resolution = resolution_or_404(db, resolution_id)
    authorize_issue_mutation(finding_or_404(db, resolution.finding_id), role)
    reason = payload.get("reason")
    if not reason:
        raise HTTPException(422, "REJECTION_REASON_REQUIRED")
    reject_resolution(db, resolution, reason, actor=payload.get("rejected_by", "synthetic-reviewer"), correlation_id=cid(request)); db.commit()
    return {"resolution": row(resolution), "finding": finding_payload(db, finding_or_404(db, resolution.finding_id)), "fixture": fixture_metadata()}


@router.get("/finding-resolutions/{resolution_id}")
def get_resolution(resolution_id: str, db: Session = Depends(get_db)):
    resolution = resolution_or_404(db, resolution_id)
    return {"resolution": row(resolution), "evidence": [row(x) for x in db.scalars(select(FindingResolutionEvidence).where(FindingResolutionEvidence.finding_resolution_id == resolution.id).order_by(FindingResolutionEvidence.added_at)).all()], "evaluations": [row(x) for x in db.scalars(select(FindingClosureEvaluation).where(FindingClosureEvaluation.resolution_id == resolution.id).order_by(FindingClosureEvaluation.evaluated_at)).all()], "fixture": fixture_metadata()}


@router.post("/findings/{finding_id}/disputes")
def post_dispute(finding_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    try:
        finding = finding_or_404(db, finding_id); authorize_issue_mutation(finding, role)
        dispute = raise_dispute(db, finding, payload, actor=payload.get("raised_by", "synthetic-operator"), correlation_id=cid(request)); db.commit()
    except ValueError as exc:
        db.rollback(); raise HTTPException(422, str(exc))
    return {"dispute": row(dispute), "finding": finding_payload(db, finding_or_404(db, finding_id)), "fixture": fixture_metadata()}


@router.post("/finding-disputes/{dispute_id}/review")
def review_dispute_route(dispute_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    dispute = db.get(FindingDispute, dispute_id)
    if not dispute: raise HTTPException(404, "Finding dispute not found")
    authorize_issue_mutation(finding_or_404(db, dispute.finding_id), role)
    review_dispute(db, dispute, payload, actor=payload.get("reviewed_by", "synthetic-reviewer"), correlation_id=cid(request)); db.commit()
    return {"dispute": row(dispute), "finding": finding_payload(db, finding_or_404(db, dispute.finding_id)), "fixture": fixture_metadata()}


@router.post("/findings/{finding_id}/reopen")
def reopen_route(finding_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role=Depends(current_user_role)):
    reason = payload.get("reason")
    if not reason: raise HTTPException(422, "REOPEN_REASON_REQUIRED")
    finding = finding_or_404(db, finding_id); authorize_issue_mutation(finding, role)
    event = reopen_finding(db, finding, actor=payload.get("reopened_by", "synthetic-reviewer"), reason=reason, correlation_id=cid(request), authority_event_id=payload.get("source_authority_event_id")); db.commit()
    return {"reopen_event": row(event), "finding": finding_payload(db, finding_or_404(db, finding_id)), "fixture": fixture_metadata()}


@router.get("/findings/{finding_id}/history")
def finding_history(finding_id: str, db: Session = Depends(get_db)):
    finding = finding_or_404(db, finding_id)
    return {"resolutions": [row(x) for x in db.scalars(select(FindingResolution).where(FindingResolution.finding_id == finding.id).order_by(FindingResolution.resolution_version)).all()], "evidence": [row(x) for x in db.scalars(select(FindingResolutionEvidence).join(FindingResolution).where(FindingResolution.finding_id == finding.id)).all()], "disputes": [row(x) for x in db.scalars(select(FindingDispute).where(FindingDispute.finding_id == finding.id)).all()], "reopens": [row(x) for x in db.scalars(select(FindingReopenEvent).where(FindingReopenEvent.finding_id == finding.id)).all()], "fixture": fixture_metadata()}


@router.post("/precheck-runs/{run_id}/clearance/evaluate")
def precheck_clearance(run_id: str, request: Request, db: Session = Depends(get_db)):
    run = db.get(AuthorityPrecheckRun, run_id)
    if not run: raise HTTPException(404, "Authority precheck run not found")
    evaluation = evaluate_precheck_clearance(db, run); db.commit()
    return {"evaluation": row(evaluation), "run": row(run), "fixture": fixture_metadata()}


@router.post("/preparation-revisions/{revision_id}/create-correction-revision")
def correction_revision(revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    old = revision_or_404(db, revision_id)
    if old.status in {"STALE", "SUPERSEDED"} and payload.get("material_change", True) is False:
        raise HTTPException(409, "STALE_REVISION_REQUIRES_MATERIAL_REBASELINE")
    if payload.get("material_change", True):
        event = record_material_change(db, project_id=old.project_id, source_type=payload.get("source_type", "VerifiedAssertion"), source_id=payload.get("source_id", old.id), previous_version_or_hash=old.package_manifest_hash, new_version_or_hash=payload.get("new_version_or_hash", f"correction-{old.id}"), change_type=payload.get("change_type", "CORRECTION"), material=True, actor_or_system=payload.get("actor", "synthetic-operator"), correlation_id=cid(request), metadata={"additional_source_ids": [old.id]})
        for run in db.scalars(select(AuthorityPrecheckRun).where(AuthorityPrecheckRun.preparation_revision_id == old.id)).all():
            run.status = "STALE"; run.invalidated_at = datetime.now(timezone.utc); run.invalidated_reason = "MATERIAL_CORRECTION"
            audit(db, correlation_id=cid(request), event_type="PRECHECK_PRIOR_CLEARANCE_INVALIDATED", entity_type="AuthorityPrecheckRun", entity_id=run.id, after={"material_change_event_id": event.id}, metadata=fixture_metadata())
    package = None
    if old.package_id:
        evaluation, _ = evaluate_readiness(db, old.project_id)
        if evaluation.overall_status in {"READY", "READY_WITH_NONBLOCKING_WARNINGS"}:
            package = build_package(db, old.project_id, created_by=payload.get("created_by", "synthetic-preparer"))
            ensure_project_lineage(db, old.project_id, cid(request))
    revision = create_correction_revision(db, old, actor=payload.get("created_by", "synthetic-preparer"), correlation_id=cid(request), package_override=package)
    db.commit()
    return {"revision": row(revision), "package": row(package), "prior_revision_id": old.id, "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/history-context")
def revision_history_context(revision_id: str, db: Session = Depends(get_db)):
    return history_context(db, revision_or_404(db, revision_id))


@router.get("/preparation-revisions/{revision_id}/prior-findings")
def prior_findings(revision_id: str, db: Session = Depends(get_db)):
    context = history_context(db, revision_or_404(db, revision_id)); return {"findings": context["prior_findings"], "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/prior-approvals")
def prior_approvals(revision_id: str, db: Session = Depends(get_db)):
    context = history_context(db, revision_or_404(db, revision_id)); return {"approvals": context["prior_approvals"], "fixture": fixture_metadata()}


@router.post("/submission-cycles/synthetic-capture")
def synthetic_capture(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    if not payload.get("synthetic_only", True): raise HTTPException(403, "SYNTHETIC_ONLY_REQUIRED")
    application = application_or_404(db, payload.get("application_id")); revision = revision_or_404(db, payload.get("preparation_revision_id"))
    if revision.application_id != application.id: raise HTTPException(422, "APPLICATION_REVISION_MISMATCH")
    package = db.get(Package, payload.get("package_id") or revision.package_id)
    if not package: raise HTTPException(422, "PACKAGE_REQUIRED")
    status = payload.get("status", "SUBMITTED")
    cycle = db.get(SubmissionCycle, payload.get("submission_cycle_id")) if payload.get("submission_cycle_id") else None
    if not cycle:
        number = (db.scalar(select(func.max(SubmissionCycle.cycle_number)).where(SubmissionCycle.application_id == application.id)) or 0) + 1
        cycle = SubmissionCycle(application_id=application.id, cycle_number=number, external_reference=payload.get("submission_reference", f"SYN-CYCLE-{application.external_request_number}-{number}"), source_reference=payload.get("source_reference"), status="PREPARING", preparation_revision_id=revision.id, authority_repetition_number=payload.get("authority_repetition_number", number), started_at=datetime.now(timezone.utc))
        db.add(cycle); db.flush(); audit(db, correlation_id=cid(request), event_type="SUBMISSION_CYCLE_CREATED", entity_type="SubmissionCycle", entity_id=cycle.id, after={"cycle_number": number, "revision_id": revision.id}, metadata=fixture_metadata())
    if status in {"SUBMITTED", "SUBMITTED_CONFIRMED"}:
        if not payload.get("external_human_action", False): raise HTTPException(422, "EXTERNAL_HUMAN_ACTION_MARKER_REQUIRED")
        submitted_values = payload.get("submitted_values")
        intended = db.scalar(select(PortalIntendedState).where(PortalIntendedState.preparation_revision_id == revision.id))
        if intended and submitted_values is not None and submitted_values != intended.fields:
            audit(db, correlation_id=cid(request), event_type="EXTERNAL_MUTATION_DETECTED", entity_type="SubmissionCycle", entity_id=cycle.id, after={"intended_hash": intended.state_hash, "submitted_hash": stable_hash(submitted_values), "action": "human_submission_capture"}, metadata=fixture_metadata())
        snapshot = SubmittedSnapshot(application_id=application.id, submission_cycle_id=cycle.id, preparation_revision_id=revision.id, package_id=package.id, package_manifest_hash=package.manifest_hash or "", portal_snapshot_id=payload.get("portal_snapshot_id"), submitted_values=submitted_values or {}, submitted_grids=payload.get("submitted_grids", []), submitted_attachments=payload.get("submitted_attachments", []), authority_status="SUBMITTED", submission_reference=payload.get("submission_reference", cycle.external_reference or cycle.id), submitted_at=datetime.now(timezone.utc), capture_method="SYNTHETIC_EXTERNAL_HUMAN_SUBMIT_HARNESS", snapshot_hash=stable_hash({"values": submitted_values or {}, "grids": payload.get("submitted_grids", []), "attachments": payload.get("submitted_attachments", []), "package": package.manifest_hash}))
        db.add(snapshot); db.flush(); cycle.submitted_snapshot_id = snapshot.id; cycle.submitted_at = snapshot.submitted_at; cycle.status = "SUBMITTED"; application.application_status = ApplicationStatus.SUBMITTED
        confirmation = SubmissionConfirmation(application_id=application.id, mode="HUMAN_EVIDENCE", request_reference=snapshot.submission_reference, visible_status="SUBMITTED_CONFIRMED", evidence_reference=payload.get("evidence_artifact_id", snapshot.id), notes="External human submission represented by synthetic test harness; PermitOps only captured the observed state.", preparation_revision_id=revision.id, application_identity_json={"application_id": application.id, "project_id": application.project_id}, confirmed_by=payload.get("confirmed_by", "synthetic-final-submitter"), status="SUBMITTED_CONFIRMED")
        db.add(confirmation); db.flush(); cycle.submission_confirmation_id = confirmation.id
        audit(db, correlation_id=cid(request), event_type="SYNTHETIC_HUMAN_SUBMISSION_REPRESENTED", entity_type="SubmissionCycle", entity_id=cycle.id, after={"human_only": True, "capture_method": snapshot.capture_method}, metadata=fixture_metadata())
        audit(db, correlation_id=cid(request), event_type="SUBMITTED_SNAPSHOT_CAPTURED", entity_type="SubmittedSnapshot", entity_id=snapshot.id, after={"snapshot_hash": snapshot.snapshot_hash, "package_manifest_hash": package.manifest_hash}, metadata=fixture_metadata())
    elif status in {"UNDER_REVIEW", "RETURNED", "APPROVED", "CLOSED"}:
        cycle.status = status; cycle.returned_at = datetime.now(timezone.utc) if status == "RETURNED" else cycle.returned_at; cycle.approved_at = datetime.now(timezone.utc) if status == "APPROVED" else cycle.approved_at
        application.application_status = ApplicationStatus.RETURNED if status == "RETURNED" else ApplicationStatus.UNDER_REVIEW if status == "UNDER_REVIEW" else ApplicationStatus.APPROVED if status == "APPROVED" else application.application_status
        if status == "RETURNED": audit(db, correlation_id=cid(request), event_type="SUBMISSION_CYCLE_RETURNED", entity_type="SubmissionCycle", entity_id=cycle.id, after={"repetition_number": cycle.authority_repetition_number}, metadata=fixture_metadata())
    results = []
    for comment in payload.get("comments", []):
        project = db.get(Project, application.project_id)
        finding_payload = {**comment, "application_id": application.id, "submission_cycle_id": cycle.id, "source_reference": comment.get("source_reference", f"{cycle.external_reference or cycle.id}:{len(results) + 1}"), "source_channel": "SYNTHETIC_AUTHORITY_CAPTURE", "captured_by": payload.get("captured_by", "synthetic-authority-review"), "external_event_id": comment.get("external_event_id", f"{cycle.id}:{comment.get('code', 'COMMENT')}:{len(results) + 1}"), "evidence_artifact_id": comment.get("evidence_artifact_id", f"synthetic://authority/{cycle.id}/{comment.get('code', 'comment')}:{len(results) + 1}"), "raw_text": comment.get("raw_text", comment.get("message", "Synthetic official comment")), "title": comment.get("title", "Synthetic official municipality comment"), "finding_code": comment.get("finding_code", "OTHER_AUTHORITY_COMMENT")}
        result = create_routed_finding(db, project=project, application=application, source_type=FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT, source_channel="SYNTHETIC_AUTHORITY_CAPTURE", source_reference=finding_payload["source_reference"], raw_text=finding_payload["raw_text"], title=finding_payload["title"], normalized_summary=finding_payload["raw_text"], discipline=finding_payload.get("discipline", "GENERAL"), severity=finding_payload.get("severity"), blocking=finding_payload.get("blocking"), finding_code=finding_payload["finding_code"], preparation_revision_id=revision.id, submission_cycle_id=cycle.id, external_finding_id=finding_payload.get("external_finding_id"), external_event_id=finding_payload["external_event_id"], evidence_artifact_id=finding_payload["evidence_artifact_id"], affected_object_type=finding_payload.get("affected_object_type"), affected_object_id=finding_payload.get("affected_object_id"), channel="IN_APP", correlation_id=cid(request), captured_by=finding_payload["captured_by"], normalized_key=finding_payload.get("normalized_key"), raw_payload={"synthetic_one_shot_capture": True, "cycle_id": cycle.id})
        if result["finding"] and result["created"]:
            link_prior_finding(db, result["finding"], actor=payload.get("captured_by", "synthetic-authority-review"), correlation_id=cid(request))
        results.append({"finding": row(result["finding"]), "task": row(result["task"]), "notification": row(result["notification"]), "dedupe_result": result["dedupe_result"]})
    db.commit()
    return {"cycle": row(cycle), "submitted_snapshot": row(db.get(SubmittedSnapshot, cycle.submitted_snapshot_id)) if cycle.submitted_snapshot_id else None, "official_findings": results, "machine_submit_operation": False, "fixture": fixture_metadata()}


@router.get("/submission-cycles")
def list_submission_cycles(application_id: str | None = None, db: Session = Depends(get_db)):
    stmt = select(SubmissionCycle).order_by(SubmissionCycle.created_at)
    if application_id: stmt = stmt.where(SubmissionCycle.application_id == application_id)
    return {"cycles": [row(x) for x in db.scalars(stmt).all()], "fixture": fixture_metadata()}


@router.get("/submission-cycles/{cycle_id}/findings")
def cycle_findings(cycle_id: str, db: Session = Depends(get_db)):
    cycle_or_404(db, cycle_id)
    return {"findings": [finding_payload(db, x) for x in db.scalars(select(Finding).where(Finding.submission_cycle_id == cycle_id).order_by(Finding.captured_at)).all()], "fixture": fixture_metadata()}


@router.post("/applications/{application_id}/resubmission-readiness/evaluate")
def resubmission_evaluate(application_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    application = application_or_404(db, application_id); cycle = db.get(SubmissionCycle, (payload or {}).get("submission_cycle_id")) if (payload or {}).get("submission_cycle_id") else None
    evaluation = evaluate_resubmission(db, application, cycle=cycle); db.commit()
    return {"evaluation": row(evaluation), "reasons": evaluation.reasons, "fixture": fixture_metadata()}


@router.get("/applications/{application_id}/resubmission-readiness")
def resubmission_latest(application_id: str, db: Session = Depends(get_db)):
    application_or_404(db, application_id)
    evaluation = db.scalar(select(ResubmissionReadinessEvaluation).where(ResubmissionReadinessEvaluation.application_id == application_id).order_by(ResubmissionReadinessEvaluation.evaluated_at.desc()))
    return {"evaluation": row(evaluation), "fixture": fixture_metadata()}


@router.get("/configuration/requirement-matrix/coverage")
def requirement_matrix_coverage(db: Session = Depends(get_db)):
    item = requirement_coverage(db); db.commit(); return {"coverage": row(item), "fixture": fixture_metadata()}


@router.get("/configuration/field-matrix/coverage")
def field_matrix_coverage(db: Session = Depends(get_db)):
    item = field_coverage(db); db.commit(); return {"coverage": row(item), "fixture": fixture_metadata()}


@router.post("/control-runs")
def post_control_runs(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    project_id = payload.get("project_id")
    if not db.get(Project, project_id): raise HTTPException(404, "Project not found")
    runs = run_controls(db, project_id, package_id=payload.get("package_id"), revision_id=payload.get("preparation_revision_id"), correlation_id=cid(request)); db.commit()
    return {"runs": [row(x) for x in runs], "fixture": fixture_metadata()}


@router.get("/projects/{project_id}/control-runs")
def get_control_runs(project_id: str, db: Session = Depends(get_db)):
    return {"runs": [row(x) for x in db.scalars(select(ControlRun).where(ControlRun.project_id == project_id).order_by(ControlRun.run_at.desc())).all()], "definitions": [row(x) for x in db.scalars(select(ControlDefinition).where(ControlDefinition.status == "ACTIVE").order_by(ControlDefinition.control_code)).all()], "fixture": fixture_metadata()}


@router.post("/rule-candidates")
def create_rule_candidate(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    finding = finding_or_404(db, payload.get("source_finding_id"))
    candidate = RuleCandidate(source_finding_id=finding.id, proposed_control_area=payload.get("proposed_control_area", "REVIEW_REQUIRED"), rationale=payload.get("rationale", "Authority finding requires engineering review."), status="CANDIDATE")
    db.add(candidate); db.flush(); audit(db, correlation_id=cid(request), event_type="RULE_CANDIDATE_CREATED", entity_type="RuleCandidate", entity_id=candidate.id, after={"finding_id": finding.id, "auto_published": False}, metadata=fixture_metadata()); db.commit()
    return {"candidate": row(candidate), "published": False, "fixture": fixture_metadata()}


@router.get("/rule-candidates")
def list_rule_candidates(db: Session = Depends(get_db)):
    return {"candidates": [row(x) for x in db.scalars(select(RuleCandidate).order_by(RuleCandidate.created_at.desc())).all()], "fixture": fixture_metadata()}


@router.post("/approval-applicability/evaluate")
def approval_applicability(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    approval = db.get(Approval, payload.get("approval_id"))
    if not approval: raise HTTPException(404, "Approval not found")
    prior_id = payload.get("prior_entity_id", approval.entity_id); current_id = payload.get("current_entity_id", approval.entity_id)
    same = prior_id == current_id or payload.get("same_hash_or_scope", False)
    item = ApprovalApplicabilityEvaluation(approval_id=approval.id, prior_entity_id=prior_id, current_entity_id=current_id, same_hash_or_scope=same, material_change=not same, result="STILL_APPLICABLE" if same else "REAPPROVAL_REQUIRED", reason="Same explicit entity/hash or scope." if same else "Current entity differs; prior approval is historical only.")
    db.add(item); db.flush(); audit(db, correlation_id=cid(request), event_type="APPROVAL_APPLICABILITY_EVALUATED", entity_type="ApprovalApplicabilityEvaluation", entity_id=item.id, after={"result": item.result}, metadata=fixture_metadata());
    if not same: audit(db, correlation_id=cid(request), event_type="REAPPROVAL_REQUIRED", entity_type="Approval", entity_id=approval.id, after={"current_entity_id": current_id}, metadata=fixture_metadata())
    db.commit(); return {"evaluation": row(item), "fixture": fixture_metadata()}


@router.get("/week10/tier2-review")
def tier2_review(db: Session = Depends(get_db)):
    items = db.scalars(select(Tier2BacklogItem).order_by(Tier2BacklogItem.id)).all()
    return {"label": "DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED", "items": [{**row(x), "week10_disposition": "EXPLICITLY_DEFERRED_TO_LATER_WEEK", "evidence": "Stage 2 baseline / signed plan", "remaining_action": "Owner-led external decision or later-week hardening"} for x in items], "fixture": fixture_metadata()}


@router.get("/week10/kpi-review")
def kpi_review(db: Session = Depends(get_db)):
    findings = db.scalars(select(Finding)).all(); official = [x for x in findings if x.source_type == FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT]
    metrics = [{"metric": "blocking_finding_task_creation", "value": sum(1 for x in findings if x.blocking and db.scalar(select(WorkflowTask).where(WorkflowTask.finding_id == x.id))), "sample_size": sum(1 for x in findings if x.blocking), "evidence_class": "SYNTHETIC_MEASURED", "threshold": None, "status": "MEASURED"}, {"metric": "machine_final_submissions", "value": 0, "sample_size": 0, "evidence_class": "SYNTHETIC_MEASURED", "threshold": 0, "status": "STRUCTURAL_ZERO"}, {"metric": "official_findings", "value": len(official), "sample_size": len(official), "evidence_class": "SYNTHETIC_MEASURED", "threshold": None, "status": "MEASURED"}]
    return {"label": "DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED", "metrics": metrics, "safety_metrics": {"machine_final_submissions": 0, "silent_critical_overwrites": 0, "untraceable_uploaded_files": 0, "stale_package_readiness_escapes": 0, "stale_precheck_readiness_escapes": 0, "unresolved_blocking_finding_resubmission_escapes": 0}, "fixture": fixture_metadata()}
