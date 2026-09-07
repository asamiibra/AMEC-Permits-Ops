"""Durable downstream permit workflow projections and commands."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, true
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import (
    ApplicationStatus, ExternalSystemLink, NotificationEvent,
    NotificationStatus, PermitApplication, Project, Role, WorkflowTask,
    WorkflowTaskStatus,
)
from .week7 import now_utc

STAGE_PROJECT_SOURCES = "PROJECT_AND_SOURCES"
STAGE_VERIFY = "VERIFY_DATA"
STAGE_BY_STATUS = {
    ApplicationStatus.RETURNED.value: "COMMENTS_AND_CORRECTIONS",
    ApplicationStatus.UNDER_REVIEW.value: "AUTHORITY_REVIEW",
    ApplicationStatus.SUBMITTED.value: "AUTHORITY_REVIEW",
    "SUBMITTED_CONFIRMED": "AUTHORITY_REVIEW",
    ApplicationStatus.APPROVED.value: "HISTORY",
    "CLOSED": "HISTORY",
    "SUBMITTED_APPROVED": "HISTORY",
    ApplicationStatus.PREPARING.value: "MUNICIPALITY_PREPARATION",
    "MUNICIPALITY_PREPARATION": "MUNICIPALITY_PREPARATION",
    "VERIFIED_DRAFT": "MUNICIPALITY_PREPARATION",
}


def inferred_stage(application: PermitApplication) -> str:
    return application.workflow_stage or STAGE_BY_STATUS.get(str(getattr(application.application_status, "value", application.application_status)), STAGE_PROJECT_SOURCES)


def _next_action(application: PermitApplication, project: Project) -> dict[str, Any]:
    stage = inferred_stage(application)
    if stage == STAGE_PROJECT_SOURCES:
        return {"action_code": "ESTABLISH_PROJECT_SOURCES", "action_label": "Confirm project & sources", "reason": f"{project.project_number} needs its source-system links confirmed before verification.", "owner_role": "Permit Preparer", "stage": STAGE_PROJECT_SOURCES, "blocking": True}
    if stage == STAGE_VERIFY:
        return {"action_code": "VERIFY_PROJECT_DATA", "action_label": "Verify project data", "reason": "Project identity and source systems are confirmed; review the evidence and critical facts.", "owner_role": "Responsible Engineer", "stage": STAGE_VERIFY, "blocking": True}
    return {"action_code": "OPEN_CURRENT_STAGE", "action_label": f"Open {stage.replace('_', ' ').title()}", "reason": "Continue from the persisted permit workflow projection.", "owner_role": "Permit team", "stage": stage, "blocking": False}


def source_bindings(db: Session, project: Project, application: PermitApplication, *, strict: bool = True) -> dict[str, Any]:
    links = list(db.scalars(select(ExternalSystemLink).where(ExternalSystemLink.project_id == project.id, ExternalSystemLink.active == true())).all())
    by_type = {str(link.system_type.value if hasattr(link.system_type, "value") else link.system_type): link for link in links}
    required = {"SYNOLOGY", "EXCEL", "MUNICIPALITY"}
    missing = sorted(required - set(by_type))
    if missing and strict:
        raise HTTPException(422, detail={"code": "SOURCE_BINDING_MISSING", "missing": missing, "project_id": project.id})
    if application.project_id != project.id:
        raise HTTPException(409, detail={"code": "PROJECT_APPLICATION_MISMATCH", "project_id": project.id, "application_id": application.id})
    if any(link.project_id != project.id for link in by_type.values()):
        raise HTTPException(409, detail={"code": "SOURCE_PROJECT_MISMATCH", "project_id": project.id})
    return {"required": sorted(required), "bindings": [{"id": link.id, "system_type": key, "display_reference": link.display_reference, "external_reference": link.external_reference, "project_id": link.project_id} for key, link in sorted(by_type.items()) if key in required], "application_id": application.id}


def ensure_project_sources_task(db: Session, project: Project, application: PermitApplication) -> WorkflowTask:
    task = db.scalar(select(WorkflowTask).where(WorkflowTask.context_type == "PERMIT_WORKSPACE", WorkflowTask.context_id == project.id, WorkflowTask.task_type == "CONFIRM_PROJECT_SOURCES").order_by(WorkflowTask.created_at.desc()))
    if task:
        return task
    task = WorkflowTask(project_id=project.id, application_id=application.id, task_type="CONFIRM_PROJECT_SOURCES", title="Confirm project & sources", description="Confirm the canonical project identity and linked Synology, Excel, and Municipality sources.", owner_role="PERMIT_PREPARER", status=WorkflowTaskStatus.OPEN, priority="NORMAL", correlation_id="stage1-seed", task_family="PERMIT_WORKFLOW", context_type="PERMIT_WORKSPACE", context_id=project.id, blocking=True, next_action_code="ESTABLISH_PROJECT_SOURCES", deep_link=f"/permits/{project.id}/project-and-sources", evidence_summary={"source": "canonical project detail"})
    db.add(task); db.flush()
    return task


def workflow_projection(db: Session, project: Project, application: PermitApplication) -> dict[str, Any]:
    stage = inferred_stage(application)
    task = db.scalar(select(WorkflowTask).where(WorkflowTask.context_type == "PERMIT_WORKSPACE", WorkflowTask.context_id == project.id, WorkflowTask.status.in_((WorkflowTaskStatus.OPEN, WorkflowTaskStatus.IN_PROGRESS, WorkflowTaskStatus.ACKNOWLEDGED))).order_by(WorkflowTask.created_at.desc()))
    links = source_bindings(db, project, application, strict=False) if stage == STAGE_PROJECT_SOURCES else {"required": ["SYNOLOGY", "EXCEL", "MUNICIPALITY"], "bindings": [], "application_id": application.id}
    links["missing"] = sorted(set(links["required"]) - {item["system_type"] for item in links["bindings"]})
    return {"stage": stage, "stage_complete": stage != STAGE_PROJECT_SOURCES, "next_action": _next_action(application, project), "task": {"id": task.id, "title": task.title, "status": task.status, "owner_role": task.owner_role, "deep_link": task.deep_link} if task else None, "sources": links, "confirmed_at": application.project_sources_confirmed_at, "confirmed_by": application.project_sources_confirmed_by, "persisted": True}


def confirm_project_sources(db: Session, *, project_id: str, actor_role: Role, actor_id: str, correlation_id: str, project_reference: str | None = None) -> dict[str, Any]:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, detail={"code": "PROJECT_NOT_FOUND", "project_id": project_id})
    application = db.scalar(select(PermitApplication).where(PermitApplication.project_id == project.id).order_by(PermitApplication.external_request_number))
    if not application:
        raise HTTPException(422, detail={"code": "PROJECT_APPLICATION_MISSING", "project_id": project.id})
    if project_reference and project_reference != project.project_number:
        raise HTTPException(409, detail={"code": "PROJECT_REFERENCE_MISMATCH", "expected": project.project_number, "received": project_reference})
    allowed = {Role.SYSTEM_ADMIN, Role.OWNER_SPONSOR, Role.REQUIREMENT_STEWARD, Role.RESPONSIBLE_ENGINEER, Role.PERMIT_PREPARER}
    if actor_role not in allowed:
        raise HTTPException(403, detail={"code": "CAPABILITY_DENIED", "capability": "CONFIRM_PROJECT_SOURCES"})
    current = inferred_stage(application)
    if current == STAGE_VERIFY:
        return {"idempotent": True, "project": project, "application": application, "workflow": workflow_projection(db, project, application)}
    if current != STAGE_PROJECT_SOURCES:
        raise HTTPException(409, detail={"code": "WORKFLOW_ALREADY_ADVANCED", "current_stage": current})
    bindings = source_bindings(db, project, application, strict=True)
    before = {"workflow_stage": application.workflow_stage, "project_sources_confirmed_at": application.project_sources_confirmed_at, "project_sources_confirmed_by": application.project_sources_confirmed_by}
    now = now_utc()
    application.workflow_stage = STAGE_VERIFY
    application.project_sources_confirmed_at = now
    application.project_sources_confirmed_by = actor_id or actor_role.value
    old_task = ensure_project_sources_task(db, project, application)
    old_task.status = WorkflowTaskStatus.COMPLETED
    old_task.completed_at = now
    old_task.blocking = False
    old_task.next_action_code = "VERIFY_PROJECT_DATA"
    verify_task = db.scalar(select(WorkflowTask).where(WorkflowTask.context_type == "PERMIT_WORKSPACE", WorkflowTask.context_id == project.id, WorkflowTask.task_type == "VERIFY_PROJECT_DATA", WorkflowTask.status.in_((WorkflowTaskStatus.OPEN, WorkflowTaskStatus.IN_PROGRESS, WorkflowTaskStatus.ACKNOWLEDGED))))
    if not verify_task:
        verify_task = WorkflowTask(project_id=project.id, application_id=application.id, task_type="VERIFY_PROJECT_DATA", title="Verify project data", description="Review project identity, source evidence, and critical facts before package preparation.", owner_role="RESPONSIBLE_ENGINEER", status=WorkflowTaskStatus.OPEN, priority="NORMAL", correlation_id=correlation_id, task_family="PERMIT_WORKFLOW", context_type="PERMIT_WORKSPACE", context_id=project.id, blocking=True, next_action_code="VERIFY_PROJECT_DATA", deep_link=f"/permits/{project.id}/verify-data", evidence_summary={"confirmed_source_bindings": bindings})
        db.add(verify_task); db.flush()
    audit(db, correlation_id=correlation_id, event_type="PROJECT_SOURCES_CONFIRMED", entity_type="PermitApplication", entity_id=application.id, actor_id=actor_id, before=before, after={"workflow_stage": STAGE_VERIFY, "confirmed_by": application.project_sources_confirmed_by}, metadata={"project_id": project.id, "source_bindings": bindings})
    audit(db, correlation_id=correlation_id, event_type="WORKFLOW_TASK_COMPLETED", entity_type="WorkflowTask", entity_id=old_task.id, actor_id=actor_id, after={"status": old_task.status, "next_task_id": verify_task.id}, metadata={"command": "ConfirmProjectAndSources"})
    db.add(NotificationEvent(finding_id=None, workflow_task_id=verify_task.id, recipient_role="RESPONSIBLE_ENGINEER", channel="IN_APP", event_type="PROJECT_SOURCES_CONFIRMED", status=NotificationStatus.DELIVERED, subject="Project sources confirmed", body_preview=f"{project.project_number} is ready for project data verification.", correlation_id=correlation_id, domain="PERMIT_ADMINISTRATIVE", permit_id=application.id, severity="ADVISORY", audience=["OWNER", "ENGINEERING"], actor=actor_id, deep_link=f"/permits/{project.id}/verify-data"))
    db.commit(); db.refresh(application); db.refresh(verify_task)
    return {"idempotent": False, "project": project, "application": application, "workflow": workflow_projection(db, project, application)}
