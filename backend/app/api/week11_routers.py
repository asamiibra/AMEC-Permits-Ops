"""Week 11 monitoring, read-contract, drift, fallback, and observability APIs."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..db import get_db
from ..fixtures.canonical import fixture_metadata
from ..models import *
from ..services.week11 import contract_fingerprint, due_run, execute_monitoring_run, manual_capture, metrics, now_utc
from ..services.week45 import row

router = APIRouter(prefix="/api")


def cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "week11-missing-correlation")


def policy_or_404(db: Session, policy_id: str) -> MonitoringPolicy:
    item = db.get(MonitoringPolicy, policy_id)
    if not item:
        raise HTTPException(404, "Monitoring policy not found")
    return item


def application_or_404(db: Session, application_id: str) -> PermitApplication:
    item = db.get(PermitApplication, application_id)
    if not item:
        raise HTTPException(404, "Application not found")
    return item


def run_view(result: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in result.items():
        if hasattr(value, "__table__"):
            output[key] = row(value)
        elif isinstance(value, list):
            output[key] = [row(x) if hasattr(x, "__table__") else x for x in value]
        else:
            output[key] = value
    return output


@router.get("/monitoring/policies")
def monitoring_policies(db: Session = Depends(get_db)):
    return {"policies": [row(x) for x in db.scalars(select(MonitoringPolicy).order_by(MonitoringPolicy.effective_from)).all()], "fixture": fixture_metadata(), "production_read_approved": False}


@router.post("/monitoring/policies/{policy_id}/synthetic-enable")
def enable_synthetic(policy_id: str, request: Request, db: Session = Depends(get_db)):
    policy = policy_or_404(db, policy_id)
    if policy.environment == "PRODUCTION":
        raise HTTPException(403, "PRODUCTION_READ_REQUIRES_EXPLICIT_APPROVAL")
    policy.enabled = True; policy.status = "SYNTHETIC_ACTIVE"; policy.evidence_class = "SYNTHETIC_MEASURED"
    audit(db, correlation_id=cid(request), event_type="MONITORING_POLICY_ENABLED", entity_type="MonitoringPolicy", entity_id=policy.id, after={"status": policy.status, "environment": policy.environment}, metadata=fixture_metadata()); db.commit()
    return {"policy": row(policy), "production_approved": False, "fixture": fixture_metadata()}


@router.post("/monitoring/policies/{policy_id}/pause")
def pause_policy(policy_id: str, request: Request, db: Session = Depends(get_db)):
    policy = policy_or_404(db, policy_id); policy.enabled = False; policy.status = "PAUSED"
    audit(db, correlation_id=cid(request), event_type="MONITORING_POLICY_PAUSED", entity_type="MonitoringPolicy", entity_id=policy.id, after={"status": policy.status}, metadata=fixture_metadata()); db.commit(); return {"policy": row(policy), "fixture": fixture_metadata()}


@router.get("/monitoring/runs")
def monitoring_runs(application_id: str | None = None, status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(MonitoringRun).order_by(MonitoringRun.scheduled_for.desc())
    if application_id: stmt = stmt.where(MonitoringRun.application_id == application_id)
    if status: stmt = stmt.where(MonitoringRun.status == status)
    return {"runs": [row(x) for x in db.scalars(stmt).all()], "fixture": fixture_metadata()}


@router.post("/monitoring/run-due-synthetic")
def run_due_synthetic(payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    payload = payload or {}
    result = due_run(db, policy_id=payload.get("policy_id"), application_id=payload.get("application_id"), observed_override=payload.get("observed_state") or payload.get("observed_override"), correlation_id=cid(request))
    return {**result, "runs": [run_view(x) for x in result.get("runs", [])], "fixture": fixture_metadata()}


@router.post("/applications/{application_id}/monitor-now")
def monitor_now(application_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    application_or_404(db, application_id); payload = payload or {}
    result = due_run(db, application_id=application_id, observed_override=payload.get("observed_state") or payload.get("observed_override"), correlation_id=cid(request))
    if not result.get("runs"):
        raise HTTPException(409, "NO_ACTIVE_MONITORING_POLICY")
    return {**result, "runs": [run_view(x) for x in result["runs"]], "fixture": fixture_metadata()}


@router.get("/monitoring/runs/{run_id}")
def monitoring_run(run_id: str, db: Session = Depends(get_db)):
    run = db.get(MonitoringRun, run_id)
    if not run: raise HTTPException(404, "Monitoring run not found")
    return {"run": row(run), "decisions": [row(x) for x in db.scalars(select(MonitoringExecutionDecision).where(MonitoringExecutionDecision.run_id == run.id)).all()], "checks": [row(x) for x in db.scalars(select(MonitoringCheck).where(MonitoringCheck.monitoring_run_id == run.id)).all()], "status_observations": [row(x) for x in db.scalars(select(AuthorityStatusObservation).where(AuthorityStatusObservation.monitoring_run_id == run.id)).all()], "comment_observations": [row(x) for x in db.scalars(select(AuthorityCommentObservation).where(AuthorityCommentObservation.monitoring_run_id == run.id)).all()], "snapshot": row(db.scalar(select(MonitoringStateSnapshot).where(MonitoringStateSnapshot.monitoring_run_id == run.id))), "comparison": row(db.scalar(select(AuthorityStateComparison).where(AuthorityStateComparison.monitoring_run_id == run.id))), "fixture": fixture_metadata()}


@router.get("/monitoring/runs/{run_id}/comparison")
def monitoring_comparison(run_id: str, db: Session = Depends(get_db)):
    item = db.scalar(select(AuthorityStateComparison).where(AuthorityStateComparison.monitoring_run_id == run_id))
    if not item: raise HTTPException(404, "Monitoring comparison not found")
    return {"comparison": row(item), "fixture": fixture_metadata()}


@router.post("/monitoring/manual-capture")
def monitoring_manual_capture(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    try: result = manual_capture(db, payload, correlation_id=cid(request))
    except ValueError as exc: raise HTTPException(422, str(exc))
    return {"capture": row(result["capture"]), "monitoring": result["monitoring"], "fixture": fixture_metadata()}


@router.get("/applications/{application_id}/monitoring-history")
def monitoring_history(application_id: str, db: Session = Depends(get_db)):
    application_or_404(db, application_id)
    runs = db.scalars(select(MonitoringRun).where(MonitoringRun.application_id == application_id).order_by(MonitoringRun.scheduled_for.desc())).all()
    return {"application_id": application_id, "runs": [row(x) for x in runs], "checks": [row(x) for x in db.scalars(select(MonitoringCheck).join(MonitoringRun).where(MonitoringRun.application_id == application_id).order_by(MonitoringCheck.checked_at.desc())).all()], "fallbacks": [row(x) for x in db.scalars(select(HumanMonitoringCapture).where(HumanMonitoringCapture.application_id == application_id).order_by(HumanMonitoringCapture.captured_at.desc())).all()], "fixture": fixture_metadata()}


@router.get("/portal-contracts")
def portal_contracts(db: Session = Depends(get_db)):
    return {"contracts": [{**row(x), "computed_fingerprint": contract_fingerprint(x)} for x in db.scalars(select(PortalReadContract).order_by(PortalReadContract.operation)).all()], "fixture": fixture_metadata()}


@router.post("/portal-contracts/{contract_id}/validate")
def validate_contract(contract_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    contract = db.get(PortalReadContract, contract_id)
    if not contract: raise HTTPException(404, "Portal read contract not found")
    payload = payload or {}; observed = payload.get("observed_fingerprint") or contract_fingerprint(contract)
    passed = observed == contract.expected_structural_fingerprint
    validation = PortalContractValidationRun(adapter_id=contract.adapter_id, adapter_version=contract.adapter_version, contract_version=contract.contract_version, environment=payload.get("environment", "TEST"), test_fixture_version=payload.get("test_fixture_version", fixture_metadata()["fixture_version"]), operations_tested=payload.get("operations_tested", [contract.operation]), pass_count=1 if passed else 0, fail_count=0 if passed else 1, result="PASS" if passed else "FAIL", reviewed_by=payload.get("reviewed_by"), reviewed_at=now_utc() if payload.get("reviewed_by") and passed else None)
    db.add(validation); db.flush(); audit(db, correlation_id=cid(request), event_type="PORTAL_CONTRACT_VALIDATED", entity_type="PortalContractValidationRun", entity_id=validation.id, after={"result": validation.result, "contract_id": contract.id}, metadata=fixture_metadata()); db.commit(); return {"validation": row(validation), "fixture": fixture_metadata()}


@router.get("/portal-drift-events")
def portal_drift_events(status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(PortalDriftEvent).order_by(PortalDriftEvent.detected_at.desc())
    if status: stmt = stmt.where(PortalDriftEvent.status == status)
    return {"events": [row(x) for x in db.scalars(stmt).all()], "fixture": fixture_metadata()}


@router.post("/portal-drift-events/{drift_id}/revalidate")
def revalidate_drift(drift_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    drift = db.get(PortalDriftEvent, drift_id)
    if not drift: raise HTTPException(404, "Portal drift event not found")
    payload = payload or {}; validation = db.scalar(select(PortalContractValidationRun).where(PortalContractValidationRun.adapter_id == drift.adapter_id, PortalContractValidationRun.adapter_version == drift.adapter_version, PortalContractValidationRun.result == "PASS").order_by(PortalContractValidationRun.reviewed_at.desc(), PortalContractValidationRun.id.desc()))
    if not validation or not validation.reviewed_by: raise HTTPException(409, "PASSING_REVIEWED_CONTRACT_VALIDATION_REQUIRED")
    drift.status = "REVALIDATED"; drift.revalidated_at = now_utc(); drift.revalidated_by = payload.get("revalidated_by") or validation.reviewed_by
    policies = db.scalars(select(MonitoringPolicy).where(MonitoringPolicy.adapter_id == drift.adapter_id, MonitoringPolicy.adapter_version == drift.adapter_version)).all()
    for policy in policies: policy.status = "SYNTHETIC_ACTIVE" if policy.environment != "PRODUCTION" else "PAUSED"; policy.enabled = policy.environment != "PRODUCTION"
    audit(db, correlation_id=cid(request), event_type="PORTAL_READ_PATH_REENABLED", entity_type="PortalDriftEvent", entity_id=drift.id, after={"validation_id": validation.id, "production_reenabled": False}, metadata=fixture_metadata()); db.commit(); return {"drift": row(drift), "validation": row(validation), "re_enabled": True, "production_approved": False, "fixture": fixture_metadata()}


@router.get("/external-mutations")
def external_mutations(application_id: str | None = None, db: Session = Depends(get_db)):
    stmt = select(ExternalMutationObservation).order_by(ExternalMutationObservation.detected_at.desc())
    if application_id: stmt = stmt.where(ExternalMutationObservation.application_id == application_id)
    return {"mutations": [row(x) for x in db.scalars(stmt).all()], "fixture": fixture_metadata()}


@router.get("/notifications/observability")
def notification_observability(db: Session = Depends(get_db)):
    attempts = db.scalars(select(NotificationDeliveryAttempt).order_by(NotificationDeliveryAttempt.attempted_at.desc())).all()
    notifications = db.scalars(select(NotificationEvent).order_by(NotificationEvent.created_at.desc())).all()
    return {"notifications": [row(x) for x in notifications], "attempts": [row(x) for x in attempts], "fallback_recipient_visible": any(x.recipient_role == "PROCESS_CHAMPION" for x in notifications), "delivery_failure_rate": sum(x.result == "FAILED" for x in attempts) / len(attempts) if attempts else 0.0, "fixture": fixture_metadata()}


@router.post("/operator-timings")
def record_operator_timing(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    started = datetime.fromisoformat(payload["started_at"].replace("Z", "+00:00")) if payload.get("started_at") else now_utc()
    completed = datetime.fromisoformat(payload["completed_at"].replace("Z", "+00:00")) if payload.get("completed_at") else now_utc()
    item = OperatorTaskTiming(user_role=payload.get("user_role", "PERMIT_PREPARER"), scenario_variant=payload.get("scenario_variant", "INDIVIDUAL_OWNER"), task_type=payload.get("task_type", "PREPARATION"), preparation_revision_id=payload.get("preparation_revision_id"), started_at=started, completed_at=completed, duration_ms=int(payload.get("duration_ms", max(0, (completed - started).total_seconds() * 1000))), correction_count=int(payload.get("correction_count", 0)), navigation_count=payload.get("navigation_count"), evidence_views=payload.get("evidence_views"), source=payload.get("source", "SYNTHETIC_SHADOW"))
    db.add(item); db.flush(); audit(db, correlation_id=cid(request), event_type="ASSISTED_TIMING_RECORDED", entity_type="OperatorTaskTiming", entity_id=item.id, after={"task_type": item.task_type, "duration_ms": item.duration_ms, "sensitive_content": False}, metadata=fixture_metadata()); db.commit(); return {"timing": row(item), "fixture": fixture_metadata()}


@router.get("/week11/report")
def week11_report(db: Session = Depends(get_db)):
    return {"report": metrics(db), "production_automated_monitoring": "BLOCKED_EXTERNAL / FALLBACK_MANUAL", "optional_automation_branch": "NOT_AUTHORIZED_NOT_BLOCKING", "fixture": fixture_metadata()}
