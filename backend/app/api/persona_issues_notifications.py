from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Finding, NotificationEvent, NotificationReadState, WorkflowTask
from ..services.persona_visibility import NOTIFICATION_DEEP_LINK_REGISTRY, issue_detail, issue_rows, issue_summary, notification_rows, notification_summary, principal_key, requested_persona

router = APIRouter(prefix="/api", tags=["persona-issues-notifications"])


def persona_or_422(value: str | None, demo_role: str | None = None) -> str:
    try:
        # In synthetic mode the controlled Demo As role is the authority. The
        # query value remains useful for service tests and unauthenticated
        # backend clients, but cannot override an explicit role header.
        return requested_persona(demo_role or value)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/issues")
def list_persona_issues(persona: str = Query("OWNER"), domain: str | None = None, severity: str | None = None, blocking: bool | None = None, x_dev_role: str | None = Header(None), db: Session = Depends(get_db)):
    selected = persona_or_422(persona, x_dev_role)
    rows = issue_rows(db, selected, domain=domain, severity=severity, blocking=blocking)
    return {"persona": selected, "issues": rows, "count": len(rows), "source": "Canonical Issue", "projection": "backend", "synthetic_only": True}


@router.get("/issues/summary")
def summarize_persona_issues(persona: str = Query("OWNER"), x_dev_role: str | None = Header(None), db: Session = Depends(get_db)):
    selected = persona_or_422(persona, x_dev_role)
    rows = issue_rows(db, selected)
    return {"summary": issue_summary(rows, selected), "count_reconciliation": {"list_count": len(rows), "open_count": issue_summary(rows, selected)["open_issues"]}, "source": "Canonical Issue", "projection": "backend"}


@router.get("/issues/{issue_id}")
def get_persona_issue(issue_id: str, persona: str = Query("OWNER"), x_dev_role: str | None = Header(None), db: Session = Depends(get_db)):
    # Keep the legacy shared-runtime compatibility endpoint distinct from the
    # canonical ID route; both are reachable under /issues for old clients.
    if issue_id == "unified":
        from .recovery_routers import unified_issues
        return unified_issues(db)
    selected = persona_or_422(persona, x_dev_role)
    finding = db.get(Finding, issue_id)
    if not finding:
        raise HTTPException(404, detail={"code": "ISSUE_NOT_FOUND", "message": "This Issue is no longer available."})
    result = issue_detail(db, finding, selected)
    if not result.get("visible"):
        raise HTTPException(404, detail={"code": "ISSUE_NOT_AVAILABLE", "message": "This Issue is not available for the selected persona."})
    return result


@router.get("/notifications")
def list_persona_notifications(persona: str = Query("OWNER"), domain: str | None = None, unread: bool | None = None, x_dev_role: str | None = Header(None), x_dev_user: str | None = Header(None), db: Session = Depends(get_db)):
    selected = persona_or_422(persona, x_dev_role)
    scope = principal_key(selected, x_dev_user)
    rows = notification_rows(db, selected, domain=domain, unread=unread, principal=scope)
    return {"persona": selected, "notifications": rows, "count": len(rows), "read_state_scope": scope, "source": "NotificationEvent", "projection": "backend", "synthetic_only": True}


@router.get("/notifications/summary")
def summarize_persona_notifications(persona: str = Query("OWNER"), x_dev_role: str | None = Header(None), x_dev_user: str | None = Header(None), db: Session = Depends(get_db)):
    selected = persona_or_422(persona, x_dev_role)
    rows = notification_rows(db, selected, principal=principal_key(selected, x_dev_user))
    summary = notification_summary(rows, selected)
    return {"summary": summary, "count_reconciliation": {"list_count": len(rows), "visible_count": summary["visible"], "unread_count": summary["unread"]}, "read_state_scope": principal_key(selected, x_dev_user), "source": "NotificationEvent", "projection": "backend"}


@router.get("/notifications/mapping")
def notification_mapping(persona: str = Query("OWNER"), x_dev_role: str | None = Header(None)):
    selected = persona_or_422(persona, x_dev_role)
    return {"persona": selected, "mappings": {event_type: {"domain": rule["domain"], "stage": rule["stage"], **rule["personas"].get(selected, rule["personas"]["OWNER"])} for event_type, rule in NOTIFICATION_DEEP_LINK_REGISTRY.items()}}


@router.get("/notifications/{notification_id}")
def get_persona_notification(notification_id: str, persona: str = Query("OWNER"), x_dev_role: str | None = Header(None), x_dev_user: str | None = Header(None), db: Session = Depends(get_db)):
    selected = persona_or_422(persona, x_dev_role)
    rows = notification_rows(db, selected, principal=principal_key(selected, x_dev_user))
    item = next((row for row in rows if row["id"] == notification_id), None)
    if not item:
        raise HTTPException(404, detail={"code": "NOTIFICATION_NOT_AVAILABLE", "message": "This Notification is not available for the selected persona."})
    return {"notification": item, "persona": selected, "read_state_scope": principal_key(selected, x_dev_user)}


@router.post("/notifications/{notification_id}/acknowledge")
def acknowledge_persona_notification(notification_id: str, persona: str = Query("OWNER"), x_dev_role: str | None = Header(None), x_dev_user: str | None = Header(None), db: Session = Depends(get_db)):
    selected = persona_or_422(persona, x_dev_role)
    event = db.get(NotificationEvent, notification_id)
    if not event:
        raise HTTPException(404, "NOTIFICATION_NOT_FOUND")
    from ..services.week7 import now_utc
    scope = principal_key(selected, x_dev_user)
    state = db.scalar(select(NotificationReadState).where(NotificationReadState.notification_event_id == event.id, NotificationReadState.persona == selected, NotificationReadState.principal_key == scope))
    changed = state is None
    if state is None:
        state = NotificationReadState(notification_event_id=event.id, persona=selected, principal_key=scope, acknowledged_at=now_utc())
        db.add(state)
    db.commit()
    task = db.get(WorkflowTask, event.workflow_task_id) if event.workflow_task_id else None
    return {"acknowledged": True, "changed": changed, "notification_id": event.id, "persona": selected, "read_state_scope": scope, "acknowledged_at": state.acknowledged_at, "task_id": task.id if task else None, "task_status": task.status if task else None, "task_unchanged": True}
