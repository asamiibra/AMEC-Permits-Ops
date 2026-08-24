"""Week 7 finding -> task -> notification workflow services."""

from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, true
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import (
    AuthorityEvent, AuthorityPrecheckItem, AuthorityPrecheckRun, Finding,
    FindingCode, FindingCodeStatus, FindingRoutingRule, FindingSeverity,
    FindingSlaPolicy, FindingSourceType, FindingStatus, NotificationEvent,
    NotificationStatus, PermitApplication, PortalValidationFindingRule,
    PreparationRevision, Project, Role, SubmissionCycle, User, WorkflowTask,
    WorkflowTaskStatus,
)
from .week45 import stable_hash


ACTIVE_FINDING_STATUSES = {
    FindingStatus.OPEN, FindingStatus.ASSIGNED, FindingStatus.IN_PROGRESS,
    FindingStatus.DISPUTED, FindingStatus.DEFERRED,
}


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def as_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(str(value).replace("Z", "+00:00")) if value else now_utc()


def sla_state(due_at: datetime | None, *, now: datetime | None = None) -> str:
    if not due_at:
        return "NO_SLA"
    current = now or now_utc()
    due = due_at if due_at.tzinfo else due_at.replace(tzinfo=timezone.utc)
    if current >= due:
        return "OVERDUE"
    if current >= due - timedelta(hours=24):
        return "DUE_SOON"
    return "ON_TIME"


def _role_value(role: Any) -> str:
    return getattr(role, "value", role)


def resolve_finding_code(db: Session, code: str | None, source_type: str) -> FindingCode | None:
    if not code:
        return None
    item = db.scalar(select(FindingCode).where(FindingCode.code == code))
    if not item or item.status != FindingCodeStatus.ACTIVE:
        return None
    if item.source_classes_allowed and source_type not in item.source_classes_allowed:
        return None
    return item


def resolve_code_for_item(db: Session, item_code: str, source_type: str) -> FindingCode | None:
    direct = resolve_finding_code(db, item_code, source_type)
    if direct:
        return direct
    mapping = {
        "SYN-DRAWING-001": "DRAWING_REVISION_MISMATCH",
        "DRAWING_REVISION_MISMATCH": "DRAWING_REVISION_MISMATCH",
        "ATTACHMENT_MISSING": "ATTACHMENT_MISSING",
        "PORTAL_REQUIRED_FIELD_MISSING": "PORTAL_REQUIRED_FIELD_MISSING",
        "TECHNICAL_TODO": "PRECHECK_TECHNICAL_TODO",
        "DOCUMENT_TODO": "PRECHECK_DOCUMENT_TODO",
    }
    return resolve_finding_code(db, mapping.get(item_code), source_type)


def _policy(db: Session, severity: str, source_type: str) -> FindingSlaPolicy | None:
    exact = db.scalar(select(FindingSlaPolicy).where(
        FindingSlaPolicy.active == true(), FindingSlaPolicy.severity == severity,
        FindingSlaPolicy.source_type == source_type,
    ))
    if exact:
        return exact
    return db.scalar(select(FindingSlaPolicy).where(
        FindingSlaPolicy.active == true(), FindingSlaPolicy.severity == severity,
        FindingSlaPolicy.source_type.is_(None),
    ))


def _route(db: Session, *, code: FindingCode | None, source_type: str, severity: str,
           discipline: str, owner_role_override: str | None = None) -> tuple[str, str, User | None]:
    if owner_role_override:
        role = owner_role_override
        user = db.scalar(select(User).where(User.role == role, User.active == true()))
        return role, "PROCESS_CHAMPION", user
    rules = list(db.scalars(select(FindingRoutingRule).where(FindingRoutingRule.active == true())).all())
    ranked: list[tuple[int, FindingRoutingRule]] = []
    for rule in rules:
        if rule.finding_code_id and (not code or rule.finding_code_id != code.id):
            continue
        if rule.source_type and rule.source_type != source_type:
            continue
        if rule.severity and rule.severity != severity:
            continue
        if rule.discipline and rule.discipline != discipline:
            continue
        score = sum(bool(x) for x in [rule.finding_code_id, rule.source_type, rule.severity, rule.discipline])
        ranked.append((score, rule))
    if not ranked:
        return "UNASSIGNED", "PROCESS_CHAMPION", None
    rule = sorted(ranked, key=lambda x: x[0], reverse=True)[0][1]
    user = db.get(User, rule.preferred_user_id) if rule.preferred_user_id else db.scalar(select(User).where(User.role == rule.owner_role, User.active == true()))
    return rule.owner_role, rule.escalation_role, user


def _dedupe_event(db: Session, *, external_event_id: str | None, source_type: str,
                  source_reference: str, payload_hash: str, normalized_key: str | None) -> tuple[AuthorityEvent | None, str]:
    if external_event_id:
        existing = db.scalar(select(AuthorityEvent).where(AuthorityEvent.external_event_id == external_event_id))
        if existing:
            return existing, "DUPLICATE_EVENT_LINKED"
    exact_reference = db.scalar(select(AuthorityEvent).where(AuthorityEvent.source_type == source_type, AuthorityEvent.external_reference == source_reference))
    if exact_reference:
        return exact_reference, "DUPLICATE_EVENT_LINKED"
    exact = db.scalar(select(AuthorityEvent).where(AuthorityEvent.payload_hash == payload_hash))
    if exact:
        return exact, "DUPLICATE_EVENT_LINKED"
    if normalized_key:
        possible = db.scalar(select(AuthorityEvent).where(AuthorityEvent.normalized_key == normalized_key))
        if possible:
            return possible, "POSSIBLE_DUPLICATE_NEEDS_REVIEW"
    return None, "NEW_EVENT"


def _existing_finding_for_event(db: Session, event: AuthorityEvent) -> Finding | None:
    return db.scalar(select(Finding).where(Finding.authority_event_id == event.id))


def _notification_delivery(notification: NotificationEvent, *, force_failure: bool = False) -> None:
    notification.attempted_at = now_utc()
    channel = notification.channel
    if force_failure or channel in {"EMAIL", "TEAMS"}:
        notification.status = NotificationStatus.FAILED
        notification.failure_code = "MOCK_DELIVERY_FAILURE" if force_failure else "REAL_CHANNEL_NOT_CONFIGURED"
        return
    if channel not in {"IN_APP", "MOCK_EMAIL", "MOCK_TEAMS"}:
        notification.status = NotificationStatus.FAILED
        notification.failure_code = "UNKNOWN_CHANNEL"
        return
    notification.status = NotificationStatus.DELIVERED
    notification.delivered_at = now_utc()
    notification.external_message_reference = f"synthetic://notification/{notification.id}"


def create_routed_finding(
    db: Session,
    *,
    project: Project,
    application: PermitApplication,
    source_type: str,
    source_channel: str,
    source_reference: str,
    raw_text: str,
    title: str,
    normalized_summary: str | None = None,
    language: str = "en",
    translated_summary: str | None = None,
    discipline: str = "GENERAL",
    severity: str | None = None,
    blocking: bool | None = None,
    finding_code: str | None = None,
    preparation_revision_id: str | None = None,
    authority_precheck_run_id: str | None = None,
    submission_cycle_id: str | None = None,
    external_finding_id: str | None = None,
    external_event_id: str | None = None,
    occurred_at: datetime | None = None,
    evidence_artifact_id: str | None = None,
    affected_object_type: str | None = None,
    affected_object_id: str | None = None,
    requirement_code: str | None = None,
    owner_role_override: str | None = None,
    channel: str = "IN_APP",
    force_notification_failure: bool = False,
    correlation_id: str = "week7-synthetic",
    captured_by: str = "synthetic-operator",
    normalized_key: str | None = None,
    simulate_failure_at: str | None = None,
    raw_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if preparation_revision_id:
        revision = db.get(PreparationRevision, preparation_revision_id)
        if not revision or revision.application_id != application.id or revision.project_id != project.id:
            raise ValueError("PREPARATION_REVISION_CONTEXT_MISMATCH")
    if authority_precheck_run_id:
        run = db.get(AuthorityPrecheckRun, authority_precheck_run_id)
        if not run or run.application_id != application.id or run.preparation_revision_id != preparation_revision_id:
            raise ValueError("PRECHECK_REVISION_LINKAGE_REQUIRED")
    if source_type == FindingSourceType.AUTHORITY_PRECHECK and (not authority_precheck_run_id or not preparation_revision_id):
        raise ValueError("AUTHORITY_PRECHECK_REQUIRES_RUN_AND_REVISION")
    if source_type == FindingSourceType.OFFICIAL_MUNICIPALITY_COMMENT and not submission_cycle_id:
        raise ValueError("OFFICIAL_COMMENT_REQUIRES_SUBMISSION_CYCLE")

    event_payload = {"title": title, "raw_text": raw_text, "source_reference": source_reference, **(raw_payload or {})}
    payload_hash = stable_hash(jsonable_encoder(event_payload))
    existing, dedupe_status = _dedupe_event(db, external_event_id=external_event_id, source_type=source_type, source_reference=source_reference, payload_hash=payload_hash, normalized_key=normalized_key)
    if existing and dedupe_status == "DUPLICATE_EVENT_LINKED":
        duplicate = AuthorityEvent(
            project_id=project.id, application_id=application.id, source_channel=source_channel,
            source_type=source_type, external_reference=source_reference, external_event_id=external_event_id,
            occurred_at=as_dt(occurred_at), raw_evidence_artifact_id=evidence_artifact_id,
            payload_hash=payload_hash, normalized_key=normalized_key, status=dedupe_status,
            linked_authority_event_id=existing.id, raw_payload=jsonable_encoder(event_payload),
        )
        db.add(duplicate); db.flush()
        canonical_finding = _existing_finding_for_event(db, existing)
        audit(db, correlation_id=correlation_id, event_type="AUTHORITY_EVENT_DUPLICATE_LINKED", entity_type="AuthorityEvent", entity_id=duplicate.id, after={"linked_event_id": existing.id}, metadata={"synthetic": True})
        return {"event": duplicate, "finding": canonical_finding, "task": None, "notification": None, "dedupe_result": dedupe_status, "created": False}

    event = AuthorityEvent(
        project_id=project.id, application_id=application.id, source_channel=source_channel,
        source_type=source_type, external_reference=source_reference, external_event_id=external_event_id,
        occurred_at=as_dt(occurred_at), raw_evidence_artifact_id=evidence_artifact_id,
        payload_hash=payload_hash, normalized_key=normalized_key, status=dedupe_status,
        raw_payload=jsonable_encoder(event_payload),
    )
    db.add(event); db.flush()
    audit(db, correlation_id=correlation_id, event_type="AUTHORITY_EVENT_CAPTURED" if dedupe_status == "NEW_EVENT" else "AUTHORITY_EVENT_POSSIBLE_DUPLICATE", entity_type="AuthorityEvent", entity_id=event.id, after={"source_type": source_type, "status": dedupe_status}, metadata={"synthetic": True})

    code = resolve_finding_code(db, finding_code, source_type)
    actual_severity = severity or (code.default_severity if code else FindingSeverity.MAJOR)
    actual_blocking = bool(blocking if blocking is not None else (code.blocking_default if code else actual_severity == FindingSeverity.BLOCKING))
    policy = _policy(db, actual_severity, source_type)
    due_at = now_utc() + timedelta(hours=(policy.target_action_hours if policy else (code.default_sla_hours if code else 48)))
    owner_role, escalation_role, owner = _route(db, code=code, source_type=source_type, severity=actual_severity, discipline=discipline, owner_role_override=owner_role_override)
    status = FindingStatus.ASSIGNED if owner_role != "UNASSIGNED" else FindingStatus.OPEN
    finding = Finding(
        project_id=project.id, application_id=application.id, preparation_revision_id=preparation_revision_id,
        authority_precheck_run_id=authority_precheck_run_id, submission_cycle_id=submission_cycle_id,
        authority_event_id=event.id, finding_code_id=code.id if code else None, source_type=source_type,
        source_reference=source_reference, external_finding_id=external_finding_id, source_timestamp=as_dt(occurred_at),
        captured_by=captured_by, title=title, raw_text=raw_text,
        normalized_summary=normalized_summary or raw_text, language=language, translated_summary=translated_summary,
        discipline=discipline, affected_object_type=affected_object_type, affected_object_id=affected_object_id,
        requirement_code=requirement_code, severity=actual_severity, blocking=actual_blocking, status=status,
        assignee_user_id=owner.id if owner else None, assignee_role=owner_role, due_at=due_at,
        evidence_artifact_id=evidence_artifact_id, correlation_id=correlation_id,
        finding_code_version=code.version if code else None,
        finding_code_checksum=code.checksum if code else None,
    )
    db.add(finding); db.flush()
    audit(db, correlation_id=correlation_id, event_type="FINDING_CREATED", entity_type="Finding", entity_id=finding.id, after={"source_type": source_type, "severity": actual_severity, "blocking": actual_blocking, "finding_code": code.code if code else None}, metadata={"synthetic": True})
    audit(db, correlation_id=correlation_id, event_type="FINDING_CLASSIFIED", entity_type="Finding", entity_id=finding.id, after={"finding_code": code.code if code else "UNKNOWN_REVIEW", "version": code.version if code else None}, metadata={"synthetic": True})

    if simulate_failure_at == "before_task":
        raise RuntimeError("SIMULATED_TASK_CREATION_FAILURE")
    task = WorkflowTask(
        project_id=project.id, application_id=application.id, finding_id=finding.id, task_type="FINDING_REMEDIATION",
        title=title, description=normalized_summary or raw_text, owner_user_id=owner.id if owner else None,
        owner_role=owner_role, status=WorkflowTaskStatus.OPEN, priority=actual_severity,
        due_at=due_at, escalation_at=now_utc() + timedelta(hours=(policy.escalation_hours if policy else 72)), correlation_id=correlation_id,
    )
    db.add(task); db.flush()
    audit(db, correlation_id=correlation_id, event_type="WORKFLOW_TASK_CREATED", entity_type="WorkflowTask", entity_id=task.id, after={"finding_id": finding.id, "owner_role": owner_role, "escalation_role": escalation_role}, metadata={"synthetic": True})

    if simulate_failure_at == "before_notification":
        raise RuntimeError("SIMULATED_NOTIFICATION_CREATION_FAILURE")
    notification = NotificationEvent(
        finding_id=finding.id, workflow_task_id=task.id, recipient_user_id=owner.id if owner else None,
        recipient_role=owner_role, channel=channel, event_type="FINDING_ASSIGNED", status=NotificationStatus.PENDING,
        subject=title, body_preview=(normalized_summary or raw_text)[:500], correlation_id=correlation_id,
    )
    db.add(notification); db.flush()
    audit(db, correlation_id=correlation_id, event_type="NOTIFICATION_CREATED", entity_type="NotificationEvent", entity_id=notification.id, after={"channel": channel, "recipient_role": owner_role}, metadata={"synthetic": True})
    _notification_delivery(notification, force_failure=force_notification_failure)
    audit(db, correlation_id=correlation_id, event_type="NOTIFICATION_DELIVERY_ATTEMPTED", entity_type="NotificationEvent", entity_id=notification.id, after={"channel": channel}, metadata={"synthetic": True})
    audit(db, correlation_id=correlation_id, event_type="NOTIFICATION_FAILED" if notification.status == NotificationStatus.FAILED else "NOTIFICATION_DELIVERED", entity_type="NotificationEvent", entity_id=notification.id, after={"status": notification.status, "failure_code": notification.failure_code}, metadata={"synthetic": True})
    return {"event": event, "finding": finding, "task": task, "notification": notification, "dedupe_result": dedupe_status, "created": True}


def ingest_precheck_findings(db: Session, run: AuthorityPrecheckRun, *, correlation_id: str, captured_by: str = "synthetic-precheck", channel: str = "IN_APP", force_notification_failure: bool = False) -> list[dict[str, Any]]:
    revision = db.get(PreparationRevision, run.preparation_revision_id)
    application = db.get(PermitApplication, run.application_id)
    project = db.get(Project, application.project_id) if application else None
    if not revision or not application or not project:
        raise ValueError("PRECHECK_CONTEXT_NOT_FOUND")
    results = []
    for item in db.scalars(select(AuthorityPrecheckItem).where(AuthorityPrecheckItem.precheck_run_id == run.id).order_by(AuthorityPrecheckItem.id)).all():
        mapped_code = resolve_code_for_item(db, item.code, FindingSourceType.AUTHORITY_PRECHECK)
        result = create_routed_finding(
            db, project=project, application=application, source_type=FindingSourceType.AUTHORITY_PRECHECK,
            source_channel="AUTHORITY_PRECHECK", source_reference=item.id, raw_text=item.message,
            title=f"Precheck: {item.code}", normalized_summary=item.message, severity=item.severity,
            blocking=item.severity in {FindingSeverity.BLOCKING, FindingSeverity.MAJOR},
            preparation_revision_id=revision.id, authority_precheck_run_id=run.id,
            external_finding_id=item.code, external_event_id=f"{run.id}:{item.code}", occurred_at=run.run_at,
            # The authority item code is a source-system code. Resolve it
            # through the controlled Week 7 mapping before persistence.
            finding_code=mapped_code.code if mapped_code else None,
            evidence_artifact_id=run.raw_evidence_artifact_id, discipline="TECHNICAL" if "DRAWING" in item.code or "TECHNICAL" in item.code else "DOCUMENT",
            channel=channel, force_notification_failure=force_notification_failure,
            correlation_id=correlation_id, captured_by=captured_by, normalized_key=f"PRECHECK:{run.id}:{item.code}",
        )
        results.append(result)
    return results
