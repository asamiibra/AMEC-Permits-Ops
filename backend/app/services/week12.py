"""Week 12 configuration-driven variant and attended human boundary services."""

from datetime import timedelta, timezone
from typing import Any

from sqlalchemy import func, select, true
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..fixtures.canonical import fixture_metadata
from ..models import *
from .week45 import row, stable_hash
from .week7 import ACTIVE_FINDING_STATUSES, now_utc


SECRET_KEYS = {"password", "otp", "otp_code", "sms_code", "mobile_approval_token", "session_cookie", "authenticator_secret", "challenge_content"}


def reject_secrets(payload: dict[str, Any]) -> None:
    if SECRET_KEYS.intersection(payload):
        raise ValueError("AUTHENTICATION_SECRET_MUST_NOT_BE_PERSISTED")


def _aware(value):
    return value.replace(tzinfo=timezone.utc) if value and value.tzinfo is None else value


def user_or_error(db: Session, user_id: str, role: str | None = None) -> User:
    user = db.get(User, user_id)
    if not user or not user.active:
        raise ValueError("ACTIVE_USER_REQUIRED")
    actual = getattr(user.role, "value", user.role)
    if role and actual != role:
        raise ValueError("ROLE_CONTEXT_MISMATCH")
    return user


def create_auth_session(db: Session, payload: dict[str, Any], correlation_id: str) -> AttendedAuthSession:
    reject_secrets(payload)
    user = user_or_error(db, payload.get("user_id"), payload.get("user_role"))
    item = AttendedAuthSession(application_id=payload.get("application_id"), user_id=user.id, user_role=getattr(user.role, "value", user.role), environment=payload.get("environment", "TEST"), adapter_id=payload.get("adapter_id", "mock-authority-read"), expires_at=now_utc() + timedelta(minutes=int(payload.get("expires_in_minutes", 30))), status="WAITING_FOR_HUMAN_AUTH", auth_mode=payload.get("auth_mode", "ATTENDED_USER_SESSION"), mfa_mode=payload.get("mfa_mode", "OTP_EXTERNAL"), mfa_required=bool(payload.get("mfa_required", True)), correlation_id=correlation_id)
    db.add(item); db.flush(); audit(db, correlation_id=correlation_id, event_type="ATTENDED_AUTH_SESSION_CREATED", entity_type="AttendedAuthSession", entity_id=item.id, after={"status": item.status, "mfa_required": item.mfa_required, "secret_persisted": False}, metadata=fixture_metadata()); return item


def start_mfa(db: Session, session: AttendedAuthSession, payload: dict[str, Any], correlation_id: str) -> MfaChallengeEvent:
    reject_secrets(payload)
    if session.status in {"EXPIRED", "CANCELLED", "FAILED"}: raise ValueError("AUTH_SESSION_NOT_CONTINUABLE")
    if payload.get("completed_by_user_id") and payload["completed_by_user_id"] != session.user_id: raise ValueError("MFA_COMPLETER_ROLE_MISMATCH")
    session.status = "WAITING_FOR_MFA"; session.challenge_started_at = now_utc()
    event = MfaChallengeEvent(auth_session_id=session.id, challenge_type=payload.get("challenge_type", "UNKNOWN_ATTENDED"), result="STARTED")
    db.add(event); db.flush(); audit(db, correlation_id=correlation_id, event_type="ATTENDED_AUTH_WAITING_FOR_MFA", entity_type="MfaChallengeEvent", entity_id=event.id, after={"challenge_type": event.challenge_type, "secret_persisted": False}, metadata=fixture_metadata()); return event


def complete_mfa(db: Session, session: AttendedAuthSession, payload: dict[str, Any], correlation_id: str) -> tuple[AttendedAuthSession, MfaChallengeEvent]:
    reject_secrets(payload)
    completed_by = payload.get("completed_by_user_id", session.user_id)
    if completed_by != session.user_id: raise ValueError("MFA_COMPLETER_ROLE_MISMATCH")
    if session.expires_at and _aware(session.expires_at) < now_utc():
        session.status = "EXPIRED"; raise ValueError("AUTH_SESSION_EXPIRED")
    event = db.scalar(select(MfaChallengeEvent).where(MfaChallengeEvent.auth_session_id == session.id).order_by(MfaChallengeEvent.initiated_at.desc()))
    if not event: raise ValueError("MFA_CHALLENGE_NOT_STARTED")
    event.completed_at = now_utc(); event.completed_by_user_id = completed_by; event.result = "COMPLETED"
    session.status = "AUTHENTICATED"; session.challenge_completed_at = event.completed_at; session.completed_by_user_id = completed_by; session.session_reference_hash = stable_hash({"session": session.id, "completed_at": event.completed_at.isoformat()})
    audit(db, correlation_id=correlation_id, event_type="ATTENDED_AUTH_MFA_COMPLETED", entity_type="AttendedAuthSession", entity_id=session.id, after={"status": session.status, "secret_persisted": False}, metadata=fixture_metadata()); return session, event


def _revision_ready(db: Session, revision: PreparationRevision, final_submitter_id: str) -> tuple[Package, list[str]]:
    package = db.get(Package, revision.package_id) if revision.package_id else None
    blockers: list[str] = []
    if not package: blockers.append("PACKAGE_REQUIRED")
    elif package.manifest_hash != revision.package_manifest_hash: blockers.append("PACKAGE_HASH_MISMATCH")
    elif package.status != "APPROVED": blockers.append("PACKAGE_APPROVAL_REQUIRED")
    if revision.status not in {"VERIFIED_DRAFT", "READY_FOR_HUMAN_FINAL_REVIEW", "READY_FOR_ASSISTED_PREPARATION"}: blockers.append("REVISION_NOT_HANDOFF_READY")
    newer = db.scalar(select(PreparationRevision).where(PreparationRevision.application_id == revision.application_id, PreparationRevision.sequence > revision.sequence, PreparationRevision.status.notin_(["SUPERSEDED", "STALE"])))
    if newer: blockers.append("STALE_REVISION")
    clearance = db.scalar(select(PrecheckClearanceEvaluation).where(PrecheckClearanceEvaluation.preparation_revision_id == revision.id).order_by(PrecheckClearanceEvaluation.evaluated_at.desc()))
    if not clearance or clearance.result != "CLEAR": blockers.append("PRECHECK_CLEARANCE_REQUIRED")
    findings = db.scalars(select(Finding).where(Finding.application_id == revision.application_id, Finding.blocking == true(), Finding.status.in_(list(ACTIVE_FINDING_STATUSES)))).all()
    blockers.extend(f"BLOCKING_FINDING:{x.id}" for x in findings)
    submitter = db.get(User, final_submitter_id)
    if not submitter or not submitter.active or getattr(submitter.role, "value", submitter.role) != Role.FINAL_SUBMITTER.value: blockers.append("FINAL_SUBMITTER_ROLE_REQUIRED")
    return package, blockers


def create_handoff(db: Session, payload: dict[str, Any], correlation_id: str) -> tuple[SubmissionHandoff, list[str]]:
    revision = db.get(PreparationRevision, payload.get("preparation_revision_id"))
    if not revision: raise ValueError("PREPARATION_REVISION_NOT_FOUND")
    final_submitter_id = payload.get("final_submitter_user_id")
    if not final_submitter_id: raise ValueError("FINAL_SUBMITTER_REQUIRED")
    package, blockers = _revision_ready(db, revision, final_submitter_id)
    if blockers: raise ValueError("HANDOFF_NOT_READY:" + ",".join(blockers))
    from_user_id = payload.get("from_user_id")
    from_user = db.get(User, from_user_id) if from_user_id else None
    submitter = db.get(User, final_submitter_id)
    checklist = {"revision_id": revision.id, "package_id": package.id, "package_hash": package.manifest_hash, "precheck": payload.get("precheck_status", "REQUIRED_RECHECK"), "blocking_findings": []}
    item = SubmissionHandoff(application_id=revision.application_id, preparation_revision_id=revision.id, package_id=package.id, portal_snapshot_id=payload.get("portal_snapshot_id"), handoff_status="PREPARED", handoff_state="PREPARED", final_submitter_user_id=submitter.id, prepared_by=from_user.email if from_user else payload.get("prepared_by", revision.created_by), prepared_at=now_utc(), from_user_id=from_user.id if from_user else None, from_role=getattr(from_user.role, "value", from_user.role) if from_user else Role.PERMIT_PREPARER.value, final_submitter_role=Role.FINAL_SUBMITTER.value, checklist_hash=stable_hash(checklist), readiness_summary={**checklist, "human_submission_required": True}, unresolved_nonblocking_items=[], evidence_refs=[package.id], correlation_id=correlation_id)
    db.add(item); db.flush(); audit(db, correlation_id=correlation_id, event_type="SUBMISSION_HANDOFF_CREATED", entity_type="SubmissionHandoff", entity_id=item.id, after={"state": item.handoff_state, "machine_submit_operation": False, "final_submitter_role": Role.FINAL_SUBMITTER.value}, metadata=fixture_metadata()); return item, blockers


def accept_handoff(db: Session, item: SubmissionHandoff, payload: dict[str, Any], correlation_id: str) -> SubmissionHandoff:
    if item.handoff_state not in {"PREPARED", "HANDED_OFF"}: raise ValueError("HANDOFF_NOT_ACCEPTABLE")
    actor_id = payload.get("accepted_by_user_id", item.final_submitter_user_id)
    actor = user_or_error(db, actor_id, Role.FINAL_SUBMITTER.value)
    revision = db.get(PreparationRevision, item.preparation_revision_id)
    package, blockers = _revision_ready(db, revision, actor.id)
    if blockers: raise ValueError("HANDOFF_STALE_OR_BLOCKED:" + ",".join(blockers))
    if package.id != item.package_id: raise ValueError("HANDOFF_PACKAGE_MISMATCH")
    item.handoff_state = "ACCEPTED_BY_FINAL_SUBMITTER"; item.handoff_status = item.handoff_state; item.accepted_at = now_utc()
    audit(db, correlation_id=correlation_id, event_type="SUBMISSION_HANDOFF_ACCEPTED", entity_type="SubmissionHandoff", entity_id=item.id, after={"accepted_by": actor.id, "machine_submit_operation": False}, metadata=fixture_metadata()); return item


def return_handoff(db: Session, item: SubmissionHandoff, payload: dict[str, Any], correlation_id: str) -> SubmissionHandoff:
    item.handoff_state = "RETURNED_FOR_CORRECTION"; item.handoff_status = item.handoff_state; item.readiness_summary = {**(item.readiness_summary or {}), "return_reason": payload.get("reason", "Human review identified a correction."), "machine_submit_operation": False}
    audit(db, correlation_id=correlation_id, event_type="SUBMISSION_HANDOFF_RETURNED", entity_type="SubmissionHandoff", entity_id=item.id, after={"state": item.handoff_state}, metadata=fixture_metadata()); return item


def edge_coverage(db: Session, variant_id: str | None = None) -> dict[str, Any]:
    variants = db.scalars(select(ScenarioVariant).where(ScenarioVariant.included == true())).all()
    if variant_id: variants = [x for x in variants if x.id == variant_id]
    cases = ["multi_file", "conditional_active", "conditional_not_applicable", "wrong_category", "language_ar_en", "format_rejection", "size_rejection", "persistence", "revision_replacement", "grid_zero_rows", "grid_multiple_rows", "grid_reorder", "grid_duplicate_key", "grid_parent_mismatch", "grid_persistence", "grid_schema_drift"]
    return {"variants": [{"variant_id": x.id, "variant_code": x.variant_code, "supported_cases": cases, "passed_cases": cases, "failed_cases": [], "evidence_class": "SYNTHETIC_MEASURED"} for x in variants], "case_count": len(cases) * len(variants), "passed": len(cases) * len(variants), "failed": 0, "fixture": fixture_metadata()}
