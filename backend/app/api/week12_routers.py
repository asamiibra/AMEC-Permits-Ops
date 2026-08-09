"""Week 12 supported-variant and human submission-boundary APIs."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..db import get_db
from ..fixtures.canonical import fixture_metadata
from ..models import *
from ..services.week12 import accept_handoff, create_auth_session, create_handoff, edge_coverage, complete_mfa, reject_secrets, return_handoff, start_mfa
from ..services.week45 import row

router = APIRouter(prefix="/api")


def cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "week12-missing-correlation")


def auth_or_404(db: Session, session_id: str) -> AttendedAuthSession:
    item = db.get(AttendedAuthSession, session_id)
    if not item: raise HTTPException(404, "Attended auth session not found")
    return item


def handoff_or_404(db: Session, handoff_id: str) -> SubmissionHandoff:
    item = db.get(SubmissionHandoff, handoff_id)
    if not item: raise HTTPException(404, "Submission handoff not found")
    return item


@router.get("/scenario-variants")
def scenario_variants(scenario_id: str | None = None, db: Session = Depends(get_db)):
    stmt = select(ScenarioVariant).where(ScenarioVariant.included.is_(True)).order_by(ScenarioVariant.variant_code)
    if scenario_id: stmt = stmt.where(ScenarioVariant.scenario_id == scenario_id)
    return {"variants": [row(x) for x in db.scalars(stmt).all()], "signed_scope_only": True, "fixture": fixture_metadata()}


@router.get("/scenario-variants/{variant_id}/compatibility")
def variant_compatibility(variant_id: str, db: Session = Depends(get_db)):
    variant = db.get(ScenarioVariant, variant_id)
    if not variant: raise HTTPException(404, "Scenario variant not found")
    item = db.scalar(select(VariantCompatibilityResult).where(VariantCompatibilityResult.scenario_id == variant.scenario_id, VariantCompatibilityResult.second_variant == variant.variant_code))
    if not item: item = db.scalar(select(VariantCompatibilityResult).where(VariantCompatibilityResult.scenario_id == variant.scenario_id))
    return {"variant": row(variant), "compatibility": row(item), "core_code_fork_required": bool(item.core_code_fork_required) if item else False, "fixture": fixture_metadata()}


@router.get("/rendering/coverage")
def rendering_coverage(variant_id: str | None = None, db: Session = Depends(get_db)):
    stmt = select(TargetRenderingCoverage).order_by(TargetRenderingCoverage.variant_id, TargetRenderingCoverage.target_type)
    if variant_id: stmt = stmt.where(TargetRenderingCoverage.variant_id == variant_id)
    rows = db.scalars(stmt).all()
    return {"coverage": [row(x) for x in rows], "missing_supported_mappings": sum(len(x.missing_fields) for x in rows), "blocked_external": sum(len(x.blocked_external) for x in rows), "fixture": fixture_metadata()}


@router.post("/rendering/validate-supported-variants")
def validate_rendering(payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    rows = db.scalars(select(TargetRenderingCoverage)).all(); missing = sum(len(x.missing_fields) for x in rows)
    result = "PASS" if missing == 0 else "NEEDS_REVIEW"
    audit(db, correlation_id=cid(request), event_type="TARGET_RENDERING_COVERAGE_EVALUATED", entity_type="TargetRenderingCoverage", entity_id="W12-COVERAGE", after={"result": result, "missing_supported_mappings": missing}, metadata=fixture_metadata()); db.commit()
    return {"result": result, "missing_supported_mappings": missing, "coverage": [row(x) for x in rows], "frontend_only_rendering": False, "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{revision_id}/handoff-readiness")
def handoff_readiness(revision_id: str, final_submitter_user_id: str | None = None, db: Session = Depends(get_db)):
    revision = db.get(PreparationRevision, revision_id)
    if not revision: raise HTTPException(404, "Preparation revision not found")
    package = db.get(Package, revision.package_id) if revision.package_id else None
    blockers = []
    if not package: blockers.append("PACKAGE_REQUIRED")
    elif package.manifest_hash != revision.package_manifest_hash: blockers.append("PACKAGE_HASH_MISMATCH")
    elif package.status != "APPROVED": blockers.append("PACKAGE_APPROVAL_REQUIRED")
    if revision.status not in {"VERIFIED_DRAFT", "READY_FOR_HUMAN_FINAL_REVIEW", "READY_FOR_ASSISTED_PREPARATION"}: blockers.append("REVISION_NOT_HANDOFF_READY")
    newer = db.scalar(select(PreparationRevision).where(PreparationRevision.application_id == revision.application_id, PreparationRevision.sequence > revision.sequence, PreparationRevision.status.notin_(["SUPERSEDED", "STALE"])))
    if newer: blockers.append("STALE_REVISION")
    clearance = db.scalar(select(PrecheckClearanceEvaluation).where(PrecheckClearanceEvaluation.preparation_revision_id == revision.id).order_by(PrecheckClearanceEvaluation.evaluated_at.desc()))
    if not clearance or clearance.result != "CLEAR": blockers.append("PRECHECK_CLEARANCE_REQUIRED")
    findings = db.scalars(select(Finding).where(Finding.application_id == revision.application_id, Finding.blocking.is_(True), Finding.status.in_([FindingStatus.OPEN, FindingStatus.ASSIGNED, FindingStatus.IN_PROGRESS, FindingStatus.DISPUTED, FindingStatus.DEFERRED]))).all()
    blockers.extend(f"BLOCKING_FINDING:{x.id}" for x in findings)
    if final_submitter_user_id:
        user = db.get(User, final_submitter_user_id)
        if not user or getattr(user.role, "value", user.role) != Role.FINAL_SUBMITTER.value: blockers.append("FINAL_SUBMITTER_ROLE_REQUIRED")
    return {"ready": not blockers, "revision": row(revision), "package": row(package), "blocking_findings": [row(x) for x in findings], "blockers": blockers, "machine_submit_operation": False, "fixture": fixture_metadata()}


@router.post("/submission-handoffs")
def submission_handoff(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    try: item, blockers = create_handoff(db, payload, cid(request))
    except ValueError as exc: db.rollback(); raise HTTPException(409, str(exc))
    db.commit(); return {"handoff": row(item), "blockers": blockers, "human_submission_required": True, "machine_submit_operation": False, "fixture": fixture_metadata()}


@router.post("/submission-handoffs/{handoff_id}/accept")
def accept_submission_handoff(handoff_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    item = handoff_or_404(db, handoff_id)
    try: accept_handoff(db, item, payload or {}, cid(request))
    except ValueError as exc: db.rollback(); raise HTTPException(409, str(exc))
    db.commit(); return {"handoff": row(item), "accepted_is_submission": False, "machine_submit_operation": False, "fixture": fixture_metadata()}


@router.post("/submission-handoffs/{handoff_id}/return-for-correction")
def return_submission_handoff(handoff_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    item = handoff_or_404(db, handoff_id); return_handoff(db, item, payload or {}, cid(request)); db.commit(); return {"handoff": row(item), "machine_submit_operation": False, "fixture": fixture_metadata()}


@router.post("/attended-auth-sessions")
def attended_auth_session(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    try: item = create_auth_session(db, payload, cid(request))
    except ValueError as exc: db.rollback(); raise HTTPException(422, str(exc))
    db.commit(); return {"session": row(item), "secret_fields_persisted": False, "fixture": fixture_metadata()}


@router.post("/attended-auth-sessions/{session_id}/mfa-started")
def attended_mfa_started(session_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    session = auth_or_404(db, session_id)
    try: event = start_mfa(db, session, payload or {}, cid(request))
    except ValueError as exc: db.rollback(); raise HTTPException(409, str(exc))
    db.commit(); return {"session": row(session), "challenge": row(event), "secret_fields_persisted": False, "fixture": fixture_metadata()}


@router.post("/attended-auth-sessions/{session_id}/mfa-completed")
def attended_mfa_completed(session_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    session = auth_or_404(db, session_id)
    try: item, event = complete_mfa(db, session, payload or {}, cid(request))
    except ValueError as exc: db.rollback(); raise HTTPException(409, str(exc))
    db.commit(); return {"session": row(item), "challenge": row(event), "secret_fields_persisted": False, "fixture": fixture_metadata()}


@router.post("/attended-auth-sessions/{session_id}/cancel")
def attended_auth_cancel(session_id: str, request: Request, db: Session = Depends(get_db)):
    session = auth_or_404(db, session_id); session.status = "CANCELLED"; audit(db, correlation_id=cid(request), event_type="ATTENDED_AUTH_CANCELLED", entity_type="AttendedAuthSession", entity_id=session.id, after={"status": session.status}, metadata=fixture_metadata()); db.commit(); return {"session": row(session), "fixture": fixture_metadata()}


@router.post("/attended-auth-sessions/{session_id}/expire")
def attended_auth_expire(session_id: str, request: Request, db: Session = Depends(get_db)):
    session = auth_or_404(db, session_id); session.status = "EXPIRED"; audit(db, correlation_id=cid(request), event_type="ATTENDED_AUTH_EXPIRED", entity_type="AttendedAuthSession", entity_id=session.id, after={"status": session.status}, metadata=fixture_metadata()); db.commit(); return {"session": row(session), "fixture": fixture_metadata()}


@router.post("/human-takeover")
def human_takeover(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    reject_secrets(payload)
    item = HumanTakeoverEvent(application_id=payload.get("application_id"), session_reference=payload.get("session_reference"), initiated_by=payload.get("initiated_by", "authorized-human"), reason=payload.get("reason", "Human takeover requested."), prior_state_hash=payload.get("prior_state_hash"), reread_required=True, reconciliation_result="REREAD_REQUIRED", correlation_id=cid(request))
    db.add(item); db.flush(); audit(db, correlation_id=cid(request), event_type="ATTENDED_AUTH_TAKEN_OVER", entity_type="HumanTakeoverEvent", entity_id=item.id, after={"reread_required": True, "secret_persisted": False}, metadata=fixture_metadata()); db.commit(); return {"takeover": row(item), "resume_requires_reread": True, "fixture": fixture_metadata()}


@router.get("/week12/edge-coverage")
def week12_edge_coverage(variant_id: str | None = None, db: Session = Depends(get_db)):
    return edge_coverage(db, variant_id)


@router.get("/week12/report")
def week12_report(db: Session = Depends(get_db)):
    variants = db.scalars(select(ScenarioVariant).where(ScenarioVariant.included.is_(True))).all()
    compatibility = db.scalars(select(VariantCompatibilityResult)).all()
    coverage = db.scalars(select(TargetRenderingCoverage)).all()
    auth = db.scalars(select(AttendedAuthSession)).all()
    handoffs = db.scalars(select(SubmissionHandoff)).all()
    return {"label": "DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED", "variants": [row(x) for x in variants], "compatibility": [row(x) for x in compatibility], "rendering": {"rows": len(coverage), "missing_supported_mappings": sum(len(x.missing_fields) for x in coverage), "coverage_percent": min([x.coverage_percent for x in coverage], default=0)}, "edge_coverage": edge_coverage(db), "attended_auth": {"sessions": len(auth), "secret_persistence": 0, "mfa_completed": sum(x.status == "AUTHENTICATED" for x in auth)}, "handoff": {"created": len(handoffs), "accepted": sum(x.handoff_state == "ACCEPTED_BY_FINAL_SUBMITTER" for x in handoffs), "machine_submit_operation": False}, "optional_automation_branch": "NOT_AUTHORIZED_NOT_BLOCKING", "fixture": fixture_metadata()}
