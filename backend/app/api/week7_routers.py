"""Week 7 findings console and durable work-routing APIs."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select, true
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..db import get_db
from ..fixtures.canonical import fixture_metadata
from ..models import *
from ..services.week45 import row
from ..services.week7 import (
    ACTIVE_FINDING_STATUSES, FindingSourceType, FindingStatus, NotificationStatus,
    WorkflowTaskStatus, _notification_delivery, as_dt, create_routed_finding,
    ingest_precheck_findings, now_utc, resolve_finding_code, sla_state,
)

router = APIRouter(prefix="/api")


def cid(request: Request) -> str:
    return getattr(request.state, "correlation_id", "week7-missing-correlation")


def project_or_404(db: Session, project_id: str) -> Project:
    item = db.get(Project, project_id)
    if not item:
        raise HTTPException(404, "Project not found")
    return item


def application_or_404(db: Session, application_id: str) -> PermitApplication:
    item = db.get(PermitApplication, application_id)
    if not item:
        raise HTTPException(404, "Application not found")
    return item


def finding_or_404(db: Session, finding_id: str) -> Finding:
    item = db.get(Finding, finding_id)
    if not item:
        raise HTTPException(404, "Finding not found")
    return item


def task_or_404(db: Session, task_id: str) -> WorkflowTask:
    item = db.get(WorkflowTask, task_id)
    if not item:
        raise HTTPException(404, "Workflow task not found")
    return item


def _code(db: Session, finding: Finding) -> FindingCode | None:
    return db.get(FindingCode, finding.finding_code_id) if finding.finding_code_id else None


def finding_view(db: Session, finding: Finding) -> dict[str, Any]:
    code = _code(db, finding)
    task = db.scalar(select(WorkflowTask).where(WorkflowTask.finding_id == finding.id).order_by(WorkflowTask.created_at.desc()))
    notifications = list(db.scalars(select(NotificationEvent).where(NotificationEvent.finding_id == finding.id).order_by(NotificationEvent.created_at.desc())).all())
    owner = db.get(User, finding.assignee_user_id) if finding.assignee_user_id else None
    event = db.get(AuthorityEvent, finding.authority_event_id) if finding.authority_event_id else None
    result = {
        **row(finding),
        "finding_code": row(code) if code else None,
        "owner": row(owner) if owner else None,
        "sla_state": sla_state(finding.due_at),
        "task": {**row(task), "sla_state": sla_state(task.due_at), "escalation_state": "ESCALATION_DUE" if task.escalation_at and now_utc() >= as_dt(task.escalation_at) else "NOT_DUE"} if task else None,
        "notifications": [row(n) for n in notifications],
        "authority_event": row(event) if event else None,
        "audit_timeline": [row(a) for a in db.scalars(select(AuditEvent).where(AuditEvent.entity_type.in_(["Finding", "WorkflowTask", "NotificationEvent", "AuthorityEvent"]), AuditEvent.entity_id.in_([x for x in [finding.id, task.id if task else None, event.id if event else None] if x])).order_by(AuditEvent.occurred_at.desc())).all()],
        "fixture": fixture_metadata(),
    }
    result["source_language"] = finding.language
    return result


def task_view(db: Session, task: WorkflowTask) -> dict[str, Any]:
    owner = db.get(User, task.owner_user_id) if task.owner_user_id else None
    finding = db.get(Finding, task.finding_id)
    return {**row(task), "owner": row(owner) if owner else None, "finding": {"id": finding.id, "title": finding.title, "source_type": finding.source_type, "severity": finding.severity, "status": finding.status} if finding else None, "sla_state": sla_state(task.due_at), "escalation_state": "ESCALATION_DUE" if task.escalation_at and now_utc() >= as_dt(task.escalation_at) else "NOT_DUE", "fixture": fixture_metadata()}


@router.get("/finding-codes")
def finding_codes(db: Session = Depends(get_db)):
    return {"codes": [row(x) for x in db.scalars(select(FindingCode).order_by(FindingCode.code)).all()], "fixture": fixture_metadata()}


@router.get("/finding-routing-rules")
def finding_routing_rules(db: Session = Depends(get_db)):
    return {"rules": [row(x) for x in db.scalars(select(FindingRoutingRule).order_by(FindingRoutingRule.id)).all()], "fixture": fixture_metadata()}


@router.get("/finding-sla-policies")
def finding_sla_policies(db: Session = Depends(get_db)):
    return {"policies": [row(x) for x in db.scalars(select(FindingSlaPolicy).order_by(FindingSlaPolicy.severity)).all()], "fixture": fixture_metadata()}


@router.post("/findings/from-precheck/{precheck_run_id}")
def findings_from_precheck(precheck_run_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    run = db.get(AuthorityPrecheckRun, precheck_run_id)
    if not run:
        raise HTTPException(404, "Authority precheck run not found")
    payload = payload or {}
    try:
        results = ingest_precheck_findings(db, run, correlation_id=cid(request), captured_by=payload.get("captured_by", "synthetic-precheck"), channel=payload.get("channel", "IN_APP"), force_notification_failure=bool(payload.get("force_notification_failure", False)))
        db.commit()
    except ValueError as exc:
        db.rollback(); raise HTTPException(422, str(exc))
    except RuntimeError as exc:
        db.rollback(); raise HTTPException(500, str(exc))
    except Exception:
        db.rollback(); raise
    return {"run": row(run), "results": [{"dedupe_result": x["dedupe_result"], "created": x["created"], "finding": finding_view(db, x["finding"]) if x["finding"] else None, "task": task_view(db, x["task"]) if x["task"] else None, "notification": row(x["notification"]) if x["notification"] else None} for x in results], "fixture": fixture_metadata()}


@router.post("/findings/manual-official-comment")
def manual_official_comment(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    application = application_or_404(db, payload.get("application_id"))
    project = project_or_404(db, application.project_id)
    cycle = db.get(SubmissionCycle, payload.get("submission_cycle_id")) if payload.get("submission_cycle_id") else None
    if cycle and cycle.application_id != application.id:
        raise HTTPException(422, "SUBMISSION_CYCLE_APPLICATION_MISMATCH")
    if not cycle:
        cycle = SubmissionCycle(application_id=application.id, cycle_number=int(payload.get("cycle_number", application.repetition_count + 1)), external_reference=payload.get("review_cycle_reference", f"SYN-REVIEW-{application.external_request_number}"), status="OFFICIAL_REVIEW")
        db.add(cycle); db.flush()
    try:
        result = create_routed_finding(db, project=project, application=application, source_type=FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT, source_channel=payload.get("source_channel", "MANUAL_OPERATOR"), source_reference=payload.get("source_reference", cycle.external_reference or cycle.id), raw_text=payload.get("raw_text", ""), title=payload.get("title", "Official municipality comment"), normalized_summary=payload.get("normalized_summary"), language=payload.get("language", "en"), translated_summary=payload.get("translated_summary"), discipline=payload.get("discipline", "GENERAL"), severity=payload.get("severity"), blocking=payload.get("blocking"), finding_code=payload.get("finding_code", "OTHER_AUTHORITY_COMMENT"), submission_cycle_id=cycle.id, external_finding_id=payload.get("external_finding_id"), external_event_id=payload.get("external_event_id"), occurred_at=payload.get("occurred_at"), evidence_artifact_id=payload.get("evidence_artifact_id"), affected_object_type=payload.get("affected_object_type"), affected_object_id=payload.get("affected_object_id"), requirement_code=payload.get("requirement_code"), channel=payload.get("channel", "IN_APP"), force_notification_failure=bool(payload.get("force_notification_failure", False)), correlation_id=cid(request), captured_by=payload.get("captured_by", "synthetic-operator"), normalized_key=payload.get("normalized_key"), simulate_failure_at=payload.get("simulate_failure_at"), raw_payload={"submission_cycle_id": cycle.id, "review_cycle_reference": cycle.external_reference})
        db.commit()
    except ValueError as exc:
        db.rollback(); raise HTTPException(422, str(exc))
    except RuntimeError as exc:
        db.rollback(); raise HTTPException(500, str(exc))
    except Exception:
        db.rollback(); raise
    return {"cycle": row(cycle), "result": {"dedupe_result": result["dedupe_result"], "created": result["created"], "finding": finding_view(db, result["finding"]) if result["finding"] else None, "task": task_view(db, result["task"]) if result["task"] else None, "notification": row(result["notification"]) if result["notification"] else None, "event": row(result["event"])}, "fixture": fixture_metadata()}


@router.post("/findings/from-portal-validation/{preparation_revision_id}")
def finding_from_portal_validation(preparation_revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    revision = db.get(PreparationRevision, preparation_revision_id)
    if not revision:
        raise HTTPException(404, "Preparation revision not found")
    rule = db.scalar(select(PortalValidationFindingRule).where(PortalValidationFindingRule.validation_code == payload.get("validation_code"), PortalValidationFindingRule.active == true()))
    if not rule or not rule.create_finding:
        return {"created": False, "reason": "VALIDATION_CODE_IGNORED", "fixture": fixture_metadata()}
    application = application_or_404(db, revision.application_id); project = project_or_404(db, revision.project_id); code = db.get(FindingCode, rule.finding_code_id) if rule.finding_code_id else None
    try:
        result = create_routed_finding(db, project=project, application=application, source_type=FindingSourceType.PORTAL_VALIDATION, source_channel="PORTAL_VALIDATION", source_reference=payload.get("source_reference", payload["validation_code"]), raw_text=payload.get("raw_text", payload.get("message", payload["validation_code"])), title=payload.get("title", code.title_en if code else "Portal validation issue"), normalized_summary=payload.get("normalized_summary", payload.get("message", "Configured portal validation issue")), language=payload.get("language", "en"), translated_summary=payload.get("translated_summary"), discipline=payload.get("discipline", code.discipline if code else "PORTAL"), severity=payload.get("severity", rule.severity), blocking=payload.get("blocking", rule.severity == FindingSeverity.BLOCKING), finding_code=code.code if code else None, preparation_revision_id=revision.id, external_finding_id=payload.get("external_finding_id"), external_event_id=payload.get("external_event_id"), occurred_at=payload.get("occurred_at"), evidence_artifact_id=payload.get("evidence_artifact_id", f"synthetic://portal-validation/{revision.id}"), affected_object_type=payload.get("affected_object_type"), affected_object_id=payload.get("affected_object_id"), requirement_code=payload.get("requirement_code"), owner_role_override=rule.owner_role, channel=payload.get("channel", "IN_APP"), force_notification_failure=bool(payload.get("force_notification_failure", False)), correlation_id=cid(request), captured_by=payload.get("captured_by", "synthetic-portal"), normalized_key=payload.get("normalized_key", f"PORTAL:{revision.id}:{payload['validation_code']}"), simulate_failure_at=payload.get("simulate_failure_at"), raw_payload={"validation_code": payload["validation_code"]})
        db.commit()
    except ValueError as exc:
        db.rollback(); raise HTTPException(422, str(exc))
    except RuntimeError as exc:
        db.rollback(); raise HTTPException(500, str(exc))
    except Exception:
        db.rollback(); raise
    return {"created": True, "result": {"dedupe_result": result["dedupe_result"], "finding": finding_view(db, result["finding"]), "task": task_view(db, result["task"]), "notification": row(result["notification"]), "event": row(result["event"])}, "fixture": fixture_metadata()}


@router.post("/findings/manual")
def manual_finding(payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    application = application_or_404(db, payload.get("application_id")); project = project_or_404(db, application.project_id)
    source_type = payload.get("source_type", FindingSourceType.MANUAL_OPERATOR_CAPTURE)
    if source_type == FindingSourceType.AUTHORITY_PRECHECK:
        raise HTTPException(422, "USE_PRECHECK_INGESTION_FOR_AUTHORITY_PRECHECK")
    try:
        result = create_routed_finding(db, project=project, application=application, source_type=source_type, source_channel=payload.get("source_channel", "MANUAL_OPERATOR"), source_reference=payload.get("source_reference", "manual"), raw_text=payload.get("raw_text", ""), title=payload.get("title", "Manual finding"), normalized_summary=payload.get("normalized_summary"), language=payload.get("language", "en"), translated_summary=payload.get("translated_summary"), discipline=payload.get("discipline", "GENERAL"), severity=payload.get("severity"), blocking=payload.get("blocking"), finding_code=payload.get("finding_code"), preparation_revision_id=payload.get("preparation_revision_id"), submission_cycle_id=payload.get("submission_cycle_id"), channel=payload.get("channel", "IN_APP"), force_notification_failure=bool(payload.get("force_notification_failure", False)), correlation_id=cid(request), captured_by=payload.get("captured_by", "synthetic-operator"), external_event_id=payload.get("external_event_id"), normalized_key=payload.get("normalized_key"), simulate_failure_at=payload.get("simulate_failure_at"))
        db.commit()
    except ValueError as exc:
        db.rollback(); raise HTTPException(422, str(exc))
    except RuntimeError as exc:
        db.rollback(); raise HTTPException(500, str(exc))
    except Exception:
        db.rollback(); raise
    return {"result": {"dedupe_result": result["dedupe_result"], "finding": finding_view(db, result["finding"]), "task": task_view(db, result["task"]) if result["task"] else None, "notification": row(result["notification"]) if result["notification"] else None}, "fixture": fixture_metadata()}


@router.get("/findings")
def list_findings(project_id: str | None = None, application_id: str | None = None, status: str | None = None, severity: str | None = None, source_type: str | None = None, blocking: bool | None = None, assignee_user_id: str | None = None, sla: str | None = Query(None), db: Session = Depends(get_db)):
    stmt = select(Finding).order_by(Finding.captured_at.desc())
    if project_id: stmt = stmt.where(Finding.project_id == project_id)
    if application_id: stmt = stmt.where(Finding.application_id == application_id)
    if status: stmt = stmt.where(Finding.status == status)
    if severity: stmt = stmt.where(Finding.severity == severity)
    if source_type: stmt = stmt.where(Finding.source_type == source_type)
    if blocking is not None: stmt = stmt.where(Finding.blocking.is_(blocking))
    if assignee_user_id: stmt = stmt.where(Finding.assignee_user_id == assignee_user_id)
    items = [finding_view(db, x) for x in db.scalars(stmt).all()]
    if sla: items = [x for x in items if x["sla_state"] == sla]
    return {"findings": items, "count": len(items), "fixture": fixture_metadata()}


@router.get("/findings/{finding_id}")
def get_finding(finding_id: str, db: Session = Depends(get_db)):
    return finding_view(db, finding_or_404(db, finding_id))


@router.post("/findings/{finding_id}/assign")
def assign_finding(finding_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    finding = finding_or_404(db, finding_id); before = {"assignee_user_id": finding.assignee_user_id, "assignee_role": finding.assignee_role}
    user = db.get(User, payload.get("assignee_user_id")) if payload.get("assignee_user_id") else None
    role = payload.get("assignee_role") or (user.role.value if user else finding.assignee_role)
    if user and not user.active: raise HTTPException(422, "ASSIGNEE_INACTIVE")
    if not user and role == "UNASSIGNED":
        finding.assignee_user_id = None; finding.assignee_role = "UNASSIGNED"
    else:
        finding.assignee_user_id = user.id if user else finding.assignee_user_id
        finding.assignee_role = role
    finding.status = FindingStatus.ASSIGNED
    task = db.scalar(select(WorkflowTask).where(WorkflowTask.finding_id == finding.id).order_by(WorkflowTask.created_at.desc()))
    if task:
        task.owner_user_id = finding.assignee_user_id; task.owner_role = finding.assignee_role
    audit(db, correlation_id=cid(request), event_type="FINDING_REASSIGNED" if before["assignee_role"] else "FINDING_ASSIGNED", entity_type="Finding", entity_id=finding.id, before=before, after={"assignee_user_id": finding.assignee_user_id, "assignee_role": finding.assignee_role}, metadata={"synthetic": True})
    db.commit(); return finding_view(db, finding)


@router.post("/findings/{finding_id}/dispute")
def dispute_finding(finding_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    finding = finding_or_404(db, finding_id); finding.status = FindingStatus.DISPUTED
    task = db.scalar(select(WorkflowTask).where(WorkflowTask.finding_id == finding.id).order_by(WorkflowTask.created_at.desc()))
    if task: task.status = WorkflowTaskStatus.DISPUTED
    audit(db, correlation_id=cid(request), event_type="FINDING_DISPUTED", entity_type="Finding", entity_id=finding.id, after={"reason": payload.get("reason", "Operator dispute")}, metadata={"synthetic": True}); db.commit(); return finding_view(db, finding)


@router.post("/findings/{finding_id}/note")
def note_finding(finding_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    finding = finding_or_404(db, finding_id)
    audit(db, correlation_id=cid(request), event_type="FINDING_NOTE_ADDED", entity_type="Finding", entity_id=finding.id, after={"note": payload.get("note", "")}, metadata={"synthetic": True}); db.commit(); return {"recorded": True, "finding_id": finding.id, "fixture": fixture_metadata()}


@router.get("/tasks")
def list_tasks(project_id: str | None = None, owner_user_id: str | None = None, owner_role: str | None = None, status: str | None = None, db: Session = Depends(get_db)):
    stmt = select(WorkflowTask).order_by(WorkflowTask.created_at.desc())
    if project_id: stmt = stmt.where(WorkflowTask.project_id == project_id)
    if owner_user_id: stmt = stmt.where(WorkflowTask.owner_user_id == owner_user_id)
    if owner_role: stmt = stmt.where(WorkflowTask.owner_role == owner_role)
    if status: stmt = stmt.where(WorkflowTask.status == status)
    items = [task_view(db, x) for x in db.scalars(stmt).all()]
    return {"tasks": items, "count": len(items), "fixture": fixture_metadata()}


@router.get("/tasks/{task_id}")
def get_task(task_id: str, db: Session = Depends(get_db)):
    return task_view(db, task_or_404(db, task_id))


def _task_transition(task_id: str, status: str, event: str, request: Request, db: Session) -> dict[str, Any]:
    task = task_or_404(db, task_id); task.status = status
    if status == WorkflowTaskStatus.ACKNOWLEDGED: task.acknowledged_at = now_utc()
    if status == WorkflowTaskStatus.IN_PROGRESS: task.started_at = now_utc()
    if status == WorkflowTaskStatus.COMPLETED: task.completed_at = now_utc()
    finding = db.get(Finding, task.finding_id)
    if finding and status == WorkflowTaskStatus.IN_PROGRESS: finding.status = FindingStatus.IN_PROGRESS
    if finding and status == WorkflowTaskStatus.DISPUTED: finding.status = FindingStatus.DISPUTED
    # Completing a task deliberately does not close the finding.
    audit(db, correlation_id=cid(request), event_type=event, entity_type="WorkflowTask", entity_id=task.id, after={"status": status, "finding_remains": finding.status if finding else None}, metadata={"synthetic": True}); db.commit(); return task_view(db, task)


@router.post("/tasks/{task_id}/acknowledge")
def acknowledge_task(task_id: str, request: Request, db: Session = Depends(get_db)): return _task_transition(task_id, WorkflowTaskStatus.ACKNOWLEDGED, "WORKFLOW_TASK_ACKNOWLEDGED", request, db)


@router.post("/tasks/{task_id}/start")
def start_task(task_id: str, request: Request, db: Session = Depends(get_db)): return _task_transition(task_id, WorkflowTaskStatus.IN_PROGRESS, "WORKFLOW_TASK_STARTED", request, db)


@router.post("/tasks/{task_id}/block")
def block_task(task_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db)):
    task = task_or_404(db, task_id); task.status = WorkflowTaskStatus.BLOCKED; finding = db.get(Finding, task.finding_id)
    if finding: finding.status = FindingStatus.DEFERRED
    audit(db, correlation_id=cid(request), event_type="WORKFLOW_TASK_BLOCKED", entity_type="WorkflowTask", entity_id=task.id, after={"reason": payload.get("reason", "")}, metadata={"synthetic": True}); db.commit(); return task_view(db, task)


@router.post("/tasks/{task_id}/complete")
def complete_task(task_id: str, request: Request, db: Session = Depends(get_db)): return _task_transition(task_id, WorkflowTaskStatus.COMPLETED, "WORKFLOW_TASK_COMPLETED", request, db)


@router.get("/notifications")
def list_notifications(status: str | None = None, channel: str | None = None, db: Session = Depends(get_db)):
    stmt = select(NotificationEvent).order_by(NotificationEvent.created_at.desc())
    if status: stmt = stmt.where(NotificationEvent.status == status)
    if channel: stmt = stmt.where(NotificationEvent.channel == channel)
    return {"notifications": [row(x) for x in db.scalars(stmt).all()], "fixture": fixture_metadata()}


@router.post("/notifications/{notification_id}/retry")
def retry_notification(notification_id: str, payload: dict[str, Any] | None = None, request: Request = None, db: Session = Depends(get_db)):
    notification = db.get(NotificationEvent, notification_id)
    if not notification: raise HTTPException(404, "Notification not found")
    if notification.status != NotificationStatus.FAILED: raise HTTPException(409, "ONLY_FAILED_NOTIFICATIONS_ARE_RETRYABLE")
    payload = payload or {}; notification.status = NotificationStatus.PENDING; notification.failure_code = None
    _notification_delivery(notification, force_failure=bool(payload.get("force_failure", False)))
    audit(db, correlation_id=cid(request), event_type="NOTIFICATION_RETRIED", entity_type="NotificationEvent", entity_id=notification.id, after={"status": notification.status, "failure_code": notification.failure_code}, metadata={"synthetic": True}); db.commit(); return {"notification": row(notification), "fixture": fixture_metadata()}


def open_blocking(db: Session, *, project_id: str | None = None, application_id: str | None = None, preparation_revision_id: str | None = None) -> list[Finding]:
    stmt = select(Finding).where(Finding.blocking == true(), Finding.status.in_(ACTIVE_FINDING_STATUSES))
    if project_id: stmt = stmt.where(Finding.project_id == project_id)
    if application_id: stmt = stmt.where(Finding.application_id == application_id)
    if preparation_revision_id: stmt = stmt.where(Finding.preparation_revision_id == preparation_revision_id)
    return list(db.scalars(stmt.order_by(Finding.due_at)).all())


@router.get("/projects/{project_id}/open-blocking-findings")
def project_open_blocking(project_id: str, db: Session = Depends(get_db)):
    project_or_404(db, project_id); items = open_blocking(db, project_id=project_id); return {"has_open_blocking_findings": bool(items), "findings": [finding_view(db, x) for x in items], "fixture": fixture_metadata()}


@router.get("/preparation-revisions/{preparation_revision_id}/open-blocking-findings")
def revision_open_blocking(preparation_revision_id: str, db: Session = Depends(get_db)):
    revision = db.get(PreparationRevision, preparation_revision_id)
    if not revision: raise HTTPException(404, "Preparation revision not found")
    items = open_blocking(db, preparation_revision_id=preparation_revision_id); return {"has_open_blocking_findings": bool(items), "precheck_clear": not any(x.source_type == FindingSourceType.AUTHORITY_PRECHECK for x in items), "findings": [finding_view(db, x) for x in items], "fixture": fixture_metadata()}


@router.get("/week7/report")
def week7_report(db: Session = Depends(get_db)):
    findings = list(db.scalars(select(Finding)).all()); tasks = list(db.scalars(select(WorkflowTask)).all()); notifications = list(db.scalars(select(NotificationEvent)).all())
    by_source = {source: sum(x.source_type == source for x in findings) for source in [FindingSourceType.INTERNAL_PREFLIGHT, FindingSourceType.PORTAL_VALIDATION, FindingSourceType.AUTHORITY_PRECHECK, FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT, FindingSourceType.EMAIL_NOTICE, FindingSourceType.MANUAL_OPERATOR_CAPTURE]}
    by_severity = {severity: sum(x.severity == severity for x in findings) for severity in [FindingSeverity.BLOCKING, FindingSeverity.MAJOR, FindingSeverity.ADVISORY]}
    overdue = [x for x in findings if sla_state(x.due_at) == "OVERDUE"]
    acked = [x for x in tasks if x.acknowledged_at]
    timing = [((as_dt(x.acknowledged_at) - as_dt(x.created_at)).total_seconds() / 3600) for x in acked if x.acknowledged_at and x.created_at]
    return {"label": "DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED", "period": "SYNTHETIC_CURRENT_WEEK", "fixture_set": fixture_metadata(), "cases_processed": db.scalar(select(func.count(PermitApplication.id))) or 0, "findings_created": len(findings), "findings_by_source": by_source, "findings_by_severity": by_severity, "blocking_findings": sum(x.blocking and x.status in ACTIVE_FINDING_STATUSES for x in findings), "tasks_created": len(tasks), "unassigned_tasks": sum(x.owner_role == "UNASSIGNED" for x in tasks), "notifications_created": len(notifications), "notifications_delivered": sum(x.status == NotificationStatus.DELIVERED for x in notifications), "notifications_failed": sum(x.status == NotificationStatus.FAILED for x in notifications), "acknowledgment_timing": {"count": len(timing), "average_hours": sum(timing) / len(timing) if timing else None}, "overdue_items": len(overdue), "precheck_findings": by_source[FindingSourceType.AUTHORITY_PRECHECK], "official_comment_findings": by_source[FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT], "portal_validation_findings": by_source[FindingSourceType.PORTAL_VALIDATION]}
