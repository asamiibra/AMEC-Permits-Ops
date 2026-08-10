"""Deterministic synthetic records for the shared persona projections."""

from datetime import datetime, timedelta, timezone
from uuid import NAMESPACE_URL, uuid5

from sqlalchemy import select

from ..models import AssistantHandoff, Contract, Finding, NotificationEvent, Opportunity, PermitApplication, Project, WorkflowTask

FIXTURE_CORRELATION = "persona-issues-notifications-v1"


def _id(kind: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"proposalops/{FIXTURE_CORRELATION}/{kind}"))


def seed_persona_issues_notifications(db) -> bool:
    """Insert the representative issue/event set once; never reset live rows."""
    existing = db.scalars(select(Finding).where(Finding.correlation_id == FIXTURE_CORRELATION)).all()
    if existing:
        changed = False
        for item in existing:
            if item.title in {"Contract scope differs from quotation", "Contract scope differs from Proposal"}:
                item.title = "Contract scope differs from Proposal"
                item.normalized_summary = "Review the Contract terms against the approved Proposal revision."
                item.raw_text = item.normalized_summary
                changed = True
            if item.domain == "SYSTEM_INTEGRITY" and item.title != "Review source integrity conflict":
                item.title = "Review source integrity conflict"
                item.normalized_summary = "GHCE-2026-0142 stored source needs a human decision before it can become the current project record."
                item.raw_text = item.normalized_summary
                item.permit_id = None
                changed = True
        for item in db.scalars(select(WorkflowTask).where(WorkflowTask.correlation_id == FIXTURE_CORRELATION)).all():
            if item.title == "Contract scope differs from quotation":
                item.title = "Contract scope differs from Proposal"
                item.description = "Review the Contract terms against the approved Proposal revision."
                changed = True
            if item.title == "Source reconciliation needs owner review":
                item.title = "Review source integrity conflict"
                item.description = "GHCE-2026-0142 stored source needs a human decision before it can become the current project record."
                item.context_type = "SYSTEM"
                item.next_action_code = "REVIEW_SOURCE"
                changed = True
        for item in db.scalars(select(NotificationEvent).where(NotificationEvent.correlation_id == FIXTURE_CORRELATION)).all():
            if item.event_type == "ENGINEERING_PROPOSAL_READY" and item.subject != "Proposal preparation completed":
                item.subject = "Proposal preparation completed"
                item.body_preview = "Engineering completed Proposal preparation and sent it to Business Development."
                changed = True
            if item.event_type == "CLIENT_INFORMATION_REQUIRED" and item.subject != "Client clarification requested":
                item.subject = "Client information requirement identified"
                item.body_preview = "Additional client information was identified as required before Proposal release."
                item.domain = "PROPOSAL_COMMERCIAL"
                item.status = "DELIVERED"
            if item.event_type == "AUTHORITY_COMMENT_CAPTURED" and item.subject != "Historical authority comment received":
                item.subject = "Historical authority comment received"
                item.body_preview = "A prior authority cycle recorded a technical comment for Engineering review."
                changed = True
        project = db.scalar(select(Project).order_by(Project.project_number))
        proposal = db.scalar(select(Opportunity).where(Opportunity.project_id == project.id).order_by(Opportunity.opportunity_reference)) if project else None
        contract = db.scalar(select(Contract).where(Contract.project_id == project.id).order_by(Contract.contract_reference)) if project else None
        if project:
            changed = _ensure_demo_handoffs(db, project, proposal, contract) or changed
            application = db.scalar(select(PermitApplication).where(PermitApplication.project_id == project.id).order_by(PermitApplication.external_request_number))
            changed = _ensure_project_sources_notification(db, project, application) or changed
        return changed
    project = db.scalar(select(Project).order_by(Project.project_number))
    application = db.scalar(select(PermitApplication).where(PermitApplication.project_id == project.id).order_by(PermitApplication.external_request_number)) if project else None
    proposal = db.scalar(select(Opportunity).where(Opportunity.project_id == project.id).order_by(Opportunity.opportunity_reference)) if project else db.scalar(select(Opportunity).order_by(Opportunity.opportunity_reference))
    contract = db.scalar(select(Contract).where(Contract.project_id == project.id).order_by(Contract.contract_reference)) if project else None
    if not project or not application:
        return False
    now = datetime.now(timezone.utc)
    records = [
        ("commercial", "PROPOSAL_COMMERCIAL", "Client pricing clarification required", "Confirm the commercial assumption before release.", "MAJOR", True, "COMMERCIAL_APPROVER", proposal.id if proposal else None, None, None, "/proposals/%s" % proposal.id if proposal else None, -2),
        ("proposal-technical", "PROPOSAL_TECHNICAL", "Proposal SOW needs engineering confirmation", "Engineering evidence is required before the proposal can move to commercial review.", "BLOCKING", True, "RESPONSIBLE_ENGINEER", proposal.id if proposal else None, None, None, "/proposals/%s/preparation" % proposal.id if proposal else None, -1),
        ("proposal-review", "PROPOSAL_COMMERCIAL", "Review Proposal release", "Review the completed Proposal package before Business Development releases it to the client.", "ADVISORY", False, "COMMERCIAL_APPROVER", proposal.id if proposal else None, None, None, "/proposals/%s" % proposal.id if proposal else None, -2),
        ("contract", "CONTRACT", "Contract scope differs from Proposal", "Review the Contract terms against the approved Proposal revision.", "MAJOR", True, "COMMERCIAL_APPROVER", proposal.id if proposal else None, contract.id if contract else None, None, "/contracts/%s" % contract.id if contract else None, -3),
        ("permit-technical", "PERMIT_TECHNICAL", "Permit drawing revision requires technical review", "Confirm the current drawing revision before authority preparation.", "BLOCKING", True, "RESPONSIBLE_ENGINEER", None, None, application.id, "/permits/%s/comments-and-corrections" % project.id, -4),
        ("authority", "AUTHORITY", "Authority returned a technical comment", "A returned authority comment is waiting for engineering disposition.", "MAJOR", True, "RESPONSIBLE_ENGINEER", None, None, application.id, "/permits/%s/comments-and-corrections" % project.id, -5),
        ("system", "SYSTEM_INTEGRITY", "Review source integrity conflict", "GHCE-2026-0142 stored source needs a human decision before it can become the current project record.", "ADVISORY", False, "SYSTEM_ADMIN", None, None, None, "/proposals-contracts/%s/history" % project.id, -6),
    ]
    findings: list[Finding] = []
    tasks: list[WorkflowTask] = []
    for key, domain, title, summary, severity, blocking, role, proposal_id, contract_id, permit_id, link, age in records:
        finding = Finding(
            id=_id(f"finding-{key}"), project_id=project.id, application_id=application.id,
            source_type="PERSONA_FIXTURE", source_reference=f"synthetic://persona/{key}",
            source_timestamp=now + timedelta(days=age), captured_at=now + timedelta(days=age), captured_by="synthetic-persona-fixture",
            title=title, raw_text=summary, normalized_summary=summary, language="en", discipline="COMMERCIAL" if domain in {"PROPOSAL_COMMERCIAL", "CONTRACT"} else "ENGINEERING",
            severity=severity, blocking=blocking, status="OPEN", assignee_role=role, due_at=now + timedelta(hours=12 if blocking else 72),
            evidence_artifact_id=f"synthetic://evidence/{key}", correlation_id=FIXTURE_CORRELATION,
            domain=domain, proposal_id=proposal_id, contract_id=contract_id, permit_id=permit_id,
            owner_persona="BUSINESS_DEVELOPMENT" if role == "COMMERCIAL_APPROVER" else "ENGINEERING" if role == "RESPONSIBLE_ENGINEER" else "OWNER", deep_link=link,
        )
        task = WorkflowTask(
            id=_id(f"task-{key}"), project_id=project.id, application_id=application.id, finding_id=finding.id,
            task_type="PROPOSAL_REVIEW" if key == "proposal-review" else "PERSONA_ISSUE_REMEDIATION", title=title, description=summary, owner_role=role,
            status="OPEN", priority=severity, due_at=finding.due_at, correlation_id=FIXTURE_CORRELATION,
            task_family="AMEC_WORK", context_type="SYSTEM" if key == "system" else "CONTRACT" if contract_id else "PROPOSAL" if proposal_id else "PERMIT",
            context_id=contract_id or proposal_id or permit_id, blocking=blocking, next_action_code="REVIEW_ISSUE", deep_link=link,
            evidence_summary={"source": "synthetic persona fixture", "issue_id": finding.id},
        )
        findings.append(finding); tasks.append(task)
    db.add_all(findings); db.flush(); db.add_all(tasks); db.flush()
    # A finding-linked alert and a pure awareness event demonstrate that
    # notifications can reference an issue/task or stand alone as a domain event.
    db.add(NotificationEvent(
        id=_id("notification-permit"), finding_id=findings[5].id, workflow_task_id=tasks[5].id,
        recipient_role="RESPONSIBLE_ENGINEER", channel="IN_APP", event_type="AUTHORITY_COMMENT_CAPTURED", status="DELIVERED",
        subject="Historical authority comment received", body_preview="A prior authority cycle recorded a technical comment for Engineering review.",
        created_at=now + timedelta(days=-5), delivered_at=now + timedelta(days=-5), correlation_id=FIXTURE_CORRELATION,
        domain="AUTHORITY", permit_id=application.id, severity="MAJOR", audience=["OWNER", "ENGINEERING"], actor="Authority Simulator",
        deep_link=f"/permits/{project.id}/comments-and-corrections",
    ))
    db.add(NotificationEvent(
        id=_id("notification-handoff"), finding_id=None, workflow_task_id=None,
        recipient_role="ENGINEERING", channel="IN_APP", event_type="ENGINEERING_PROPOSAL_READY", status="DELIVERED",
        subject="Proposal preparation completed", body_preview="Engineering completed Proposal preparation and sent it to Business Development.", created_at=now + timedelta(days=-1), delivered_at=now + timedelta(days=-1),
        correlation_id=FIXTURE_CORRELATION, domain="PROPOSAL_TECHNICAL", proposal_id=proposal.id if proposal else None,
        severity="ADVISORY", audience=["OWNER", "BUSINESS_DEVELOPMENT", "ENGINEERING"], actor="Engineering",
        deep_link=f"/proposals/{proposal.id}/preparation" if proposal else None,
    ))
    db.add(NotificationEvent(
        id=_id("notification-commercial"), finding_id=findings[0].id, workflow_task_id=tasks[0].id,
        recipient_role="COMMERCIAL_APPROVER", channel="IN_APP", event_type="CLIENT_INFORMATION_REQUIRED", status="DELIVERED",
        subject="Client information requirement identified", body_preview="Additional client information was identified as required before Proposal release.", created_at=now + timedelta(days=-2), delivered_at=now + timedelta(days=-2),
        correlation_id=FIXTURE_CORRELATION, domain="PROPOSAL_COMMERCIAL", proposal_id=proposal.id if proposal else None,
        severity="MAJOR", audience=["OWNER", "BUSINESS_DEVELOPMENT"], actor="Business Development",
        deep_link=f"/proposals/{proposal.id}" if proposal else None,
    ))
    db.add(NotificationEvent(
        id=_id("notification-project-sources"), finding_id=None, workflow_task_id=None,
        recipient_role="PERMIT_PREPARER", channel="IN_APP", event_type="PROJECT_SOURCES_CONFIRMED", status="DELIVERED",
        subject="Project sources confirmed", body_preview="Project sources were confirmed and the Permit is ready for data verification.",
        created_at=now - timedelta(hours=2), delivered_at=now - timedelta(hours=2), correlation_id=FIXTURE_CORRELATION,
        domain="PERMIT_ADMINISTRATIVE", permit_id=application.id, severity="ADVISORY", audience=["OWNER", "ENGINEERING"], actor="System",
    ))
    _ensure_demo_handoffs(db, project, proposal, contract)
    return True


def _ensure_project_sources_notification(db, project, application) -> bool:
    if not application or db.scalar(select(NotificationEvent).where(NotificationEvent.event_type == "PROJECT_SOURCES_CONFIRMED", NotificationEvent.permit_id == application.id)):
        return False
    happened = datetime.now(timezone.utc) - timedelta(hours=2)
    db.add(NotificationEvent(
        id=_id("notification-project-sources"), finding_id=None, workflow_task_id=None,
        recipient_role="PERMIT_PREPARER", channel="IN_APP", event_type="PROJECT_SOURCES_CONFIRMED", status="DELIVERED",
        subject="Project sources confirmed", body_preview="Project sources were confirmed and the Permit is ready for data verification.",
        created_at=happened, delivered_at=happened, correlation_id=FIXTURE_CORRELATION,
        domain="PERMIT_ADMINISTRATIVE", permit_id=application.id, severity="ADVISORY", audience=["OWNER", "ENGINEERING"], actor="System",
    ))
    return True


def _ensure_demo_handoffs(db, project, proposal, contract) -> bool:
    """Keep the synthetic owner queue visibly cross-lifecycle and idempotent."""
    changed = False
    specs = [
        ("OPPORTUNITY", proposal.id if proposal else None, proposal.id if proposal else None, "ENGINEERING_REVIEW_ASSISTANT", "BD_ASSISTANT", "Proposal preparation handoff is waiting for Business Development review."),
        ("CONTRACT", contract.id if contract else None, None, "BD_ASSISTANT", "PROJECT_PERMIT_COORDINATION_ASSISTANT", "Contract is ready for the governed Contract to Permit handoff."),
    ]
    for context_type, context_id, opportunity_id, from_id, to_id, reason in specs:
        if not context_id:
            continue
        existing = db.scalar(select(AssistantHandoff).where(AssistantHandoff.context_id == context_id, AssistantHandoff.reason == reason))
        if existing:
            continue
        db.add(AssistantHandoff(from_assistant_id=from_id, to_assistant_id=to_id, context_type=context_type, context_id=context_id, project_id=project.id, opportunity_id=opportunity_id, source_revision_ids=[], status="CREATED", reason=reason))
        changed = True
    return changed
