"""Canonical persona-aware projections for shared issues and domain events."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditEvent, AuthorityEvent, ClientAccount, Contract, Finding, FindingDispute, FindingReopenEvent, FindingResolution, FindingResolutionEvidence, NotificationEvent, NotificationReadState, Opportunity, PermitApplication, Project, WorkflowTask
from .backend_realignment import persona_for_role, require_capability
from .week7 import ACTIVE_FINDING_STATUSES, sla_state

PERSONAS = ("OWNER", "BUSINESS_DEVELOPMENT", "ENGINEERING")
DOMAINS = (
    "PROPOSAL_COMMERCIAL", "PROPOSAL_TECHNICAL", "CONTRACT", "PERMIT_ADMINISTRATIVE",
    "PERMIT_TECHNICAL", "AUTHORITY", "SYSTEM_INTEGRITY", "COMMUNICATION_DELIVERY",
)

TECHNICAL = {"PROPOSAL_TECHNICAL", "PERMIT_ADMINISTRATIVE", "PERMIT_TECHNICAL", "AUTHORITY"}
COMMERCIAL = {"PROPOSAL_COMMERCIAL", "CONTRACT", "COMMUNICATION_DELIVERY"}

NOTIFICATION_DOMAIN_LABELS = {
    "PROPOSAL_COMMERCIAL": "Proposal Commercial",
    "PROPOSAL_TECHNICAL": "Proposal Technical / Handoff",
    "CONTRACT": "Contract",
    "PERMIT_ADMINISTRATIVE": "Permit · Sources",
    "PERMIT_TECHNICAL": "Permit Technical",
    "AUTHORITY": "Authority",
    "COMMUNICATION_DELIVERY": "Communication Delivery",
    "SYSTEM_INTEGRITY": "System / Critical",
}

# One registry owns notification destinations, labels, and whether opening a
# target should expose an actionable control. Persona projections reuse the
# same event row and only vary the allowed destination copy/context.
NOTIFICATION_DEEP_LINK_REGISTRY = {
    "PROJECT_SOURCES_CONFIRMED": {
        "domain": "PERMIT_ADMINISTRATIVE", "stage": "VERIFY_DATA", "historical": False,
        "personas": {
            "OWNER": {"cta": "Open Permit", "context_only": True},
            "BUSINESS_DEVELOPMENT": {"cta": "View Permit context", "context_only": True},
            "ENGINEERING": {"cta": "Verify project data", "context_only": False},
        },
    },
    "ENGINEERING_PROPOSAL_READY": {
        "domain": "PROPOSAL_TECHNICAL", "stage": "PROPOSAL_PREPARATION", "historical": False,
        "personas": {
            "OWNER": {"cta": "Open Proposal", "context_only": True},
            "BUSINESS_DEVELOPMENT": {"cta": "Review Proposal", "context_only": False},
            "ENGINEERING": {"cta": "View Proposal", "context_only": True},
        },
    },
    "CLIENT_INFORMATION_REQUIRED": {
        "domain": "PROPOSAL_COMMERCIAL", "stage": "PROPOSAL_DETAIL", "historical": False,
        "personas": {
            "OWNER": {"cta": "Open Proposal", "context_only": True},
            "BUSINESS_DEVELOPMENT": {"cta": "Review client information", "context_only": False},
            "ENGINEERING": {"cta": "View Proposal context", "context_only": True},
        },
    },
    "AUTHORITY_COMMENT_CAPTURED": {
        "domain": "AUTHORITY", "stage": "COMMENTS_AND_CORRECTIONS", "historical": True,
        "personas": {
            "OWNER": {"cta": "View Authority comment", "context_only": True},
            "BUSINESS_DEVELOPMENT": {"cta": "View Authority context", "context_only": True},
            "ENGINEERING": {"cta": "Review Authority comment", "context_only": False},
        },
    },
}

RAW_ACTOR_LABELS = {
    "SYSTEM_ADMIN": "System", "DEMO_AS_OPERATOR": "System", "PERSONA_FIXTURE": "System",
    "synthetic-persona-fixture": "System", "Authority Simulator": "Authority simulator",
    "Municipality Simulator": "Municipality simulator",
}


def _title_case(value: str | None) -> str:
    return (value or "System").replace("_", " ").title()

BUSINESS_DOMAIN_LABELS = {
    "PROPOSAL_COMMERCIAL": "PROPOSAL", "PROPOSAL_TECHNICAL": "PROPOSAL",
    "CONTRACT": "CONTRACT", "PERMIT_ADMINISTRATIVE": "PERMIT",
    "PERMIT_TECHNICAL": "PERMIT", "AUTHORITY": "PERMIT",
    "SYSTEM_INTEGRITY": "SYSTEM / DATA", "COMMUNICATION_DELIVERY": "PROPOSAL",
}
TEAM_LABELS = {"OWNER": "Owner", "BUSINESS_DEVELOPMENT": "Business Development", "ENGINEERING": "Engineering", "SYSTEM_ADMIN": "Owner"}

ISSUE_COPY = {
    "Client pricing clarification required": (
        "The Proposal cannot be released until the client pricing assumption is confirmed.",
        "Client release remains blocked until the commercial assumption is confirmed.",
        "Confirm the commercial assumption in the Proposal and complete the current Business Development review.",
    ),
    "Proposal SOW needs engineering confirmation": (
        "The Proposal scope of work still needs Engineering confirmation before the commercial handoff.",
        "The Proposal cannot move cleanly into Business Development review while technical scope is unconfirmed.",
        "Review the Proposal preparation scope, record the technical decision, and return the Proposal to the handoff stage.",
    ),
    "Review Proposal release": (
        "The Proposal package is waiting for Business Development release review.",
        "The next lifecycle handoff cannot be recorded until the Proposal release decision is made.",
        "Open the Proposal, review the controlled package, and record the release or return decision.",
    ),
    "Contract scope differs from Proposal": (
        "The Contract scope does not match the approved Proposal revision.",
        "The commercial handoff is at risk because the Contract may not represent the agreed Proposal scope.",
        "Compare the Contract with the linked Proposal revision and correct the governed Contract record or return it for review.",
    ),
    "Permit drawing revision requires technical review": (
        "The current Permit drawing revision needs technical verification before Authority preparation continues.",
        "The Permit package cannot safely continue with an unverified drawing revision.",
        "Review the affected drawing and revision in the Permit technical workspace, then record the Engineering disposition.",
    ),
    "Authority returned a technical comment": (
        "The Authority returned a technical comment that requires Engineering disposition.",
        "The correction loop remains open until the comment is understood, corrected, and supported by evidence.",
        "Review the Authority comment, update the affected technical revision, and attach the correction evidence before verification.",
    ),
    "Review source integrity conflict": (
        "Two source states conflict and a human integrity decision is required before the current Project record can be confirmed.",
        "The record is not ready to be treated as authoritative while the source conflict remains unresolved.",
        "Review the current and candidate source evidence, then make the supported Owner source-integrity decision.",
    ),
}


def requested_persona(value: str | None) -> str:
    normalized = (value or "OWNER").upper()
    aliases = {
        "SYSTEM_ADMIN": "OWNER", "OWNER_SPONSOR": "OWNER", "OWNER": "OWNER",
        "COMMERCIAL_APPROVER": "BUSINESS_DEVELOPMENT", "PROCESS_CHAMPION": "BUSINESS_DEVELOPMENT",
        "BD": "BUSINESS_DEVELOPMENT", "BUSINESS_DEVELOPMENT": "BUSINESS_DEVELOPMENT",
        "RESPONSIBLE_ENGINEER": "ENGINEERING", "PERMIT_PREPARER": "ENGINEERING",
        "ENGINEERING": "ENGINEERING",
    }
    persona = aliases.get(normalized)
    if persona not in PERSONAS:
        raise ValueError(f"UNKNOWN_PERSONA:{value}")
    return persona


def inferred_domain(finding: Finding) -> str:
    if finding.domain in DOMAINS:
        return finding.domain
    if finding.source_type in {"AUTHORITY_PRECHECK", "OFFICIAL_MUNICIPALITY_COMMENT"}:
        return "AUTHORITY"
    if finding.discipline in {"ENGINEERING", "TECHNICAL", "STRUCTURAL", "ARCHITECTURAL"}:
        return "PERMIT_TECHNICAL"
    return "PERMIT_ADMINISTRATIVE"


def issue_actionability(domain: str, owner_persona: str | None, persona: str, blocking: bool) -> str:
    if persona == "OWNER":
        return "ACTIONABLE"
    if owner_persona == persona:
        return "ACTIONABLE"
    if persona == "ENGINEERING":
        if domain in TECHNICAL:
            return "ACTIONABLE"
        if domain in {"SYSTEM_INTEGRITY", "PERMIT_ADMINISTRATIVE"} and blocking:
            return "CONTEXT_ONLY"
        return "HIDDEN"
    if persona == "BUSINESS_DEVELOPMENT":
        if domain in COMMERCIAL:
            return "ACTIONABLE"
        if domain in TECHNICAL and blocking:
            return "CONTEXT_ONLY"
        return "HIDDEN"
    return "HIDDEN"


def authorize_issue_mutation(finding: Finding, role: Any) -> str:
    if finding.contract_id or finding.domain == "PROPOSAL_COMMERCIAL":
        return require_capability(role, "EDIT_COMMERCIAL")
    if finding.proposal_id and finding.domain == "PROPOSAL_TECHNICAL":
        return require_capability(role, "EDIT_TECHNICAL")
    if finding.permit_id or finding.domain in {"PERMIT_TECHNICAL", "AUTHORITY"}:
        return require_capability(role, "PERMIT_TECHNICAL")
    return require_capability(role, "PROMOTE_SOR")


def notification_visibility(domain: str | None, audience: list[str] | None, persona: str) -> str:
    normalized = {requested_persona(item) for item in (audience or []) if item}
    if persona == "OWNER" or not normalized or persona in normalized:
        return "VISIBLE"
    if persona == "ENGINEERING" and domain in TECHNICAL:
        return "VISIBLE"
    if persona == "BUSINESS_DEVELOPMENT" and domain in COMMERCIAL:
        return "VISIBLE"
    return "HIDDEN"


def principal_key(persona: str, supplied: str | None = None) -> str:
    """Return a stable synthetic principal scope until authenticated identity exists."""
    value = (supplied or f"demo:{persona}").strip()
    return value[:160] or f"demo:{persona}"


def _actor_label(value: str | None) -> str:
    if not value:
        return "System"
    return RAW_ACTOR_LABELS.get(value, value)


def notification_destination(event: NotificationEvent, persona: str, record: dict[str, Any]) -> dict[str, Any]:
    rule = NOTIFICATION_DEEP_LINK_REGISTRY.get(event.event_type)
    if not rule:
        target = deep_link(proposal_id=event.proposal_id, contract_id=event.contract_id, permit_id=event.permit_id, project_id=record.get("project_id"), domain=event.domain)
        return {"href": target or event.deep_link, "cta": "Open Proposal" if event.proposal_id else "Open Permit" if event.permit_id else "View event", "context_only": True, "stage": None, "historical": False}
    persona_rule = rule["personas"].get(persona, rule["personas"]["OWNER"])
    if event.event_type == "PROJECT_SOURCES_CONFIRMED" and event.permit_id:
        href = f"/proposals-contracts/{record.get('project_id')}/verify-data"
    elif event.event_type == "ENGINEERING_PROPOSAL_READY" and event.proposal_id:
        href = f"/proposals/{event.proposal_id}/preparation" if persona == "ENGINEERING" else f"/proposals/{event.proposal_id}"
    elif event.event_type == "CLIENT_INFORMATION_REQUIRED" and event.proposal_id:
        href = f"/proposals/{event.proposal_id}"
    elif event.event_type == "AUTHORITY_COMMENT_CAPTURED" and event.permit_id:
        href = f"/proposals-contracts/{record.get('project_id')}/comments-and-corrections"
    else:
        href = event.deep_link
    return {"href": href, "cta": persona_rule["cta"], "context_only": persona_rule["context_only"], "stage": rule["stage"], "historical": rule["historical"]}


def deep_link(*, proposal_id: str | None = None, contract_id: str | None = None,
              permit_id: str | None = None, project_id: str | None = None,
              domain: str | None = None) -> str | None:
    if proposal_id:
        return f"/proposals/{proposal_id}/preparation" if domain == "PROPOSAL_TECHNICAL" else f"/proposals/{proposal_id}"
    if contract_id:
        return f"/contracts/{contract_id}"
    if permit_id:
        return f"/permits/{project_id or permit_id}/comments-and-corrections"
    return f"/proposals-contracts/{project_id}/history" if project_id else None


def business_domain(finding: Finding) -> str:
    """Classify by the business record a person must reason about."""
    if finding.contract_id:
        return "CONTRACT"
    if finding.proposal_id:
        return "PROPOSAL"
    if finding.permit_id or finding.application_id and finding.domain in {"PERMIT_ADMINISTRATIVE", "PERMIT_TECHNICAL", "AUTHORITY"}:
        return "PERMIT"
    return "SYSTEM / DATA"


def _team(finding: Finding) -> str:
    value = finding.owner_persona or finding.assignee_role or "OWNER"
    try:
        return TEAM_LABELS.get(requested_persona(value), "Owner")
    except ValueError:
        return TEAM_LABELS.get(str(value), "Owner")


def _copy(finding: Finding) -> tuple[str, str, str]:
    for title, copy in ISSUE_COPY.items():
        if title.lower() in finding.title.lower() or finding.title.lower() in title.lower():
            return copy
    return (
        finding.normalized_summary or "A governed business record has an active Issue.",
        "The current Issue remains open until the underlying condition is corrected and verified.",
        "Review the affected business record, resolve the condition, and retain evidence for the closure decision.",
    )


def resolution_context(finding: Finding, domain: str) -> tuple[str | None, str]:
    if domain == "PROPOSAL" and finding.proposal_id:
        if inferred_domain(finding) == "PROPOSAL_TECHNICAL":
            return f"/proposals/{finding.proposal_id}/preparation", "Review Proposal preparation"
        return f"/proposals/{finding.proposal_id}", "Open Proposal"
    if domain == "CONTRACT" and finding.contract_id:
        return f"/contracts/{finding.contract_id}", "Open Contract"
    if domain == "PERMIT" and finding.permit_id:
        if inferred_domain(finding) == "PERMIT_TECHNICAL":
            return f"/proposals-contracts/{finding.project_id}/project-and-sources", "Review drawing"
        return f"/proposals-contracts/{finding.project_id}/comments-and-corrections", "Review Authority comment"
    if finding.project_id:
        return f"/proposals-contracts/{finding.project_id}/project-and-sources", "Review source"
    return None, "Review source"


def issue_route(finding: Finding, persona: str, domain: str) -> tuple[str | None, str]:
    """Return the existing business workspace for this Issue/persona pair."""
    focus = f"?issue={finding.id}"
    technical = inferred_domain(finding) == "PROPOSAL_TECHNICAL"
    if domain == "PROPOSAL" and finding.proposal_id:
        return (f"/proposals/{finding.proposal_id}/preparation{focus}", "Open Preparation") if technical and persona in {"OWNER", "ENGINEERING"} else (f"/proposals/{finding.proposal_id}{focus}", "View Proposal" if technical else "Review Proposal")
    if domain == "CONTRACT" and finding.contract_id:
        return f"/contracts/{finding.contract_id}{focus}", "Review Contract" if persona in {"OWNER", "BUSINESS_DEVELOPMENT"} else "View Contract"
    if domain == "PERMIT" and finding.project_id:
        if inferred_domain(finding) == "AUTHORITY":
            return f"/proposals-contracts/{finding.project_id}/comments-and-corrections{focus}", "Review Authority Comment" if persona == "ENGINEERING" else "View Authority Comment"
        return f"/proposals-contracts/{finding.project_id}/verify-data{focus}", "Review Drawing" if persona == "ENGINEERING" else "View Permit"
    if finding.project_id:
        return f"/proposals-contracts/{finding.project_id}/project-and-sources{focus}", "Review Source"
    return None, "Review Source"


def _entity_label(db: Session, *, proposal_id: str | None, contract_id: str | None, permit_id: str | None, project_id: str | None) -> dict[str, Any]:
    proposal = db.get(Opportunity, proposal_id) if proposal_id else None
    contract = db.get(Contract, contract_id) if contract_id else None
    permit = db.get(PermitApplication, permit_id) if permit_id else None
    project = db.get(Project, project_id) if project_id else None
    return {
        "proposal": proposal.opportunity_reference if proposal else None,
        "contract": contract.contract_reference if contract else None,
        "permit": permit.external_request_number if permit else None,
        "project": project.project_number if project else None,
        "label": (proposal.opportunity_reference if proposal else contract.contract_reference if contract else permit.external_request_number if permit else project.project_number if project else "System")
                 if (proposal or contract or permit or project) else "System",
    }


def project_issue(db: Session, finding: Finding, persona: str) -> dict[str, Any]:
    domain = inferred_domain(finding)
    actionability = issue_actionability(domain, finding.owner_persona, persona, finding.blocking)
    entity = _entity_label(db, proposal_id=finding.proposal_id, contract_id=finding.contract_id, permit_id=finding.permit_id, project_id=finding.project_id)
    link = finding.deep_link or deep_link(proposal_id=finding.proposal_id, contract_id=finding.contract_id, permit_id=finding.permit_id, project_id=finding.project_id, domain=domain)
    display_domain = business_domain(finding)
    resolution_link, resolution_cta = resolution_context(finding, display_domain)
    route, route_cta = issue_route(finding, persona, display_domain)
    what, why, next_step = _copy(finding)
    entity["type"] = display_domain
    entity["id"] = finding.contract_id or finding.proposal_id or finding.permit_id or finding.project_id
    return {
        "id": finding.id, "domain": domain, "issue_type": "FINDING", "entity_type": "Proposal" if finding.proposal_id else "Contract" if finding.contract_id else "Permit" if finding.permit_id else "Project",
        "entity_id": finding.proposal_id or finding.contract_id or finding.permit_id or finding.project_id, "project_id": finding.project_id,
        "proposal_id": finding.proposal_id, "contract_id": finding.contract_id, "permit_id": finding.permit_id,
        "severity": finding.severity, "blocking": finding.blocking, "status": finding.status,
        "owner_persona": finding.owner_persona or "OWNER", "owner_role": finding.assignee_role, "owner_team": _team(finding), "source": "Recorded Issue evidence",
        "evidence": "Evidence retained", "title": finding.title,
        "display_domain": display_domain, "business_domain": display_domain,
        "issue_detail_link": route, "resolution_link": resolution_link, "resolution_cta": resolution_cta,
        "route": route, "cta_label": route_cta,
        "what_is_wrong": what, "why_it_matters": why, "what_needs_to_happen": next_step,
        "summary": finding.normalized_summary, "created_at": finding.captured_at, "updated_at": finding.captured_at,
        "due_at": finding.due_at, "sla_state": sla_state(finding.due_at), "actionability": actionability,
        "deep_link": route or link, "affected_record": entity, "visible": actionability != "HIDDEN",
    }


def _detail_entity(db: Session, finding: Finding, domain: str) -> dict[str, Any]:
    project = db.get(Project, finding.project_id) if finding.project_id else None
    proposal = db.get(Opportunity, finding.proposal_id) if finding.proposal_id else None
    client = db.get(ClientAccount, proposal.client_account_id) if proposal and proposal.client_account_id else None
    contract = db.get(Contract, finding.contract_id) if finding.contract_id else None
    permit = db.get(PermitApplication, finding.permit_id) if finding.permit_id else None
    result: dict[str, Any] = {"type": domain, "id": finding.contract_id or finding.proposal_id or finding.permit_id or finding.project_id}
    if project:
        result["project_reference"] = project.project_number
    if proposal:
        result.update({"reference": proposal.opportunity_reference, "description": proposal.title, "stage": proposal.status.replace("_", " ").title(), "client": client.display_name if client else "Client record linked"})
    if contract:
        result.update({"reference": contract.contract_reference, "status": contract.status.replace("_", " ").title(), "related_proposal_id": proposal.id if proposal else None, "related_proposal_reference": proposal.opportunity_reference if proposal else None, "commercial_context": proposal.proposal_fields_json if proposal and proposal.proposal_fields_json else "Proposal / Contract comparison required"})
    if permit:
        result.update({"reference": permit.external_request_number, "status": str(permit.application_status), "stage": (permit.workflow_stage or "Permit review").replace("_", " ").title(), "drawing_or_package_revision": finding.affected_object_id or finding.preparation_revision_id or "Current drawing revision — reference recorded in Issue evidence", "authority": permit.authority, "municipality": permit.municipality, "authority_source": finding.source_reference, "received_at": finding.captured_at})
    if domain == "SYSTEM / DATA":
        result.update({"current_source": finding.source_reference, "candidate_source": None, "source_state": "Human decision required"})
    return result


def _evidence(db: Session, finding: Finding, domain: str) -> list[dict[str, Any]]:
    items = [{"id": f"issue-source-{finding.id}", "kind": "Issue source", "reference": finding.evidence_artifact_id or finding.source_reference, "description": finding.raw_text or finding.normalized_summary, "status": "Recorded"}]
    if finding.authority_event_id:
        event = db.get(AuthorityEvent, finding.authority_event_id)
        if event:
            items.append({"id": event.id, "kind": "Authority event", "reference": event.external_reference or event.raw_evidence_artifact_id or event.id, "description": event.raw_payload.get("message") or finding.raw_text, "status": event.status})
    if domain == "CONTRACT":
        items.append({"id": f"comparison-{finding.id}", "kind": "Proposal / Contract comparison", "reference": finding.contract_id or finding.proposal_id, "description": "The linked Proposal and Contract are the comparison sources; review the divergence in the Contract context.", "status": "Review required"})
    if domain == "SYSTEM / DATA":
        items.append({"id": f"source-candidate-{finding.id}", "kind": "Candidate source", "reference": None, "description": "No candidate source is attached yet; the Owner decision boundary is explicit.", "status": "No candidate attached"})
    return items


def issue_detail(db: Session, finding: Finding, persona: str) -> dict[str, Any]:
    issue = project_issue(db, finding, persona)
    if not issue["visible"]:
        return {"issue": issue, "visible": False}
    activity: list[dict[str, Any]] = []
    for event in db.scalars(select(AuditEvent).where(AuditEvent.entity_id == finding.id).order_by(AuditEvent.occurred_at.desc())).all():
        activity.append({"id": event.id, "type": event.event_type.replace("_", " ").title(), "at": event.occurred_at, "description": "A governed Issue activity was recorded."})
    for task in db.scalars(select(WorkflowTask).where(WorkflowTask.finding_id == finding.id).order_by(WorkflowTask.created_at.desc())).all():
        activity.append({"id": task.id, "type": "Work item", "at": task.created_at, "description": task.title, "status": task.status})
    history = {
        "resolutions": [r.id for r in db.scalars(select(FindingResolution).where(FindingResolution.finding_id == finding.id).order_by(FindingResolution.resolution_version)).all()],
        "evidence": [e.id for e in db.scalars(select(FindingResolutionEvidence).join(FindingResolution).where(FindingResolution.finding_id == finding.id)).all()],
        "disputes": [d.id for d in db.scalars(select(FindingDispute).where(FindingDispute.finding_id == finding.id)).all()],
        "reopens": [r.id for r in db.scalars(select(FindingReopenEvent).where(FindingReopenEvent.finding_id == finding.id)).all()],
    }
    return {"issue": issue, "visible": True, "affected_entity": _detail_entity(db, finding, issue["display_domain"]), "evidence": _evidence(db, finding, issue["display_domain"]), "activity": activity, "history": history, "persona_context": {"persona": persona, "actionability": issue["actionability"], "owner_team": issue["owner_team"], "can_resolve": issue["actionability"] == "ACTIONABLE"}, "closure": {"current_status": finding.status, "underlying_condition_must_be_verified": True}, "readiness": {"screen": "Issue Detail", "domain": issue["display_domain"]}}


def projected_notification_message(event: NotificationEvent, persona: str, record: dict[str, Any]) -> str:
    if event.event_type == "ENGINEERING_PROPOSAL_READY":
        if persona == "ENGINEERING": return f"{record['label']} preparation was recorded as ready for handoff."
        if persona == "BUSINESS_DEVELOPMENT": return f"{record['label']} is ready for commercial review."
        return f"Engineering completed {record['label']} preparation."
    if event.body_preview:
        return event.body_preview
    return event.subject or "ProposalOps event"


def project_notification(db: Session, event: NotificationEvent, persona: str, read_state: NotificationReadState | None = None) -> dict[str, Any]:
    permit = db.get(PermitApplication, event.permit_id) if event.permit_id else None
    record = _entity_label(db, proposal_id=event.proposal_id, contract_id=event.contract_id, permit_id=event.permit_id, project_id=permit.project_id if permit else None)
    domain = event.domain or "SYSTEM_INTEGRITY"
    visibility = notification_visibility(domain, event.audience, persona)
    record["project_id"] = permit.project_id if permit else None
    destination = notification_destination(event, persona, record)
    public_record = {key: value for key, value in record.items() if key != "project_id"}
    link = destination["href"]
    read = read_state is not None
    delivery_relevant = domain == "COMMUNICATION_DELIVERY"
    return {
        "id": event.id, "domain": domain, "event_type": event.event_type, "entity_type": "Proposal" if event.proposal_id else "Contract" if event.contract_id else "Permit" if event.permit_id else "System",
        "entity_id": event.proposal_id or event.contract_id or event.permit_id, "proposal_id": event.proposal_id, "contract_id": event.contract_id, "permit_id": event.permit_id,
        "severity": event.severity or "ADVISORY", "audience": event.audience or [], "actor": _actor_label(event.actor or event.recipient_role),
        "created_at": event.created_at, "acknowledged_at": read_state.acknowledged_at if read_state else None, "read": read, "unread": not read,
        "delivery_status": event.status if delivery_relevant else None, "delivery_relevant": delivery_relevant,
        "subject": event.subject, "message": projected_notification_message(event, persona, record),
        "display_domain": NOTIFICATION_DOMAIN_LABELS.get(domain, _title_case(domain)), "affected_record": public_record, "deep_link": link,
        "cta_label": destination["cta"], "context_only": destination["context_only"], "destination_stage": destination["stage"],
        "historical": destination["historical"], "visibility": visibility, "source_event_id": event.id,
    }


def issue_rows(db: Session, persona: str, *, domain: str | None = None, severity: str | None = None, blocking: bool | None = None) -> list[dict[str, Any]]:
    stmt = select(Finding).order_by(Finding.captured_at.desc())
    if domain: stmt = stmt.where(Finding.domain == domain)
    if severity: stmt = stmt.where(Finding.severity == severity)
    if blocking is not None: stmt = stmt.where(Finding.blocking.is_(blocking))
    return [item for item in (project_issue(db, row, persona) for row in db.scalars(stmt).all()) if item["visible"]]


def notification_rows(db: Session, persona: str, *, domain: str | None = None, unread: bool | None = None, principal: str | None = None) -> list[dict[str, Any]]:
    stmt = select(NotificationEvent).order_by(NotificationEvent.created_at.desc())
    if domain: stmt = stmt.where(NotificationEvent.domain == domain)
    events = db.scalars(stmt).all()
    states = {}
    if events:
        states = {state.notification_event_id: state for state in db.scalars(select(NotificationReadState).where(NotificationReadState.notification_event_id.in_([row.id for row in events]), NotificationReadState.persona == persona, NotificationReadState.principal_key == principal_key(persona, principal))).all()}
    projected = [project_notification(db, row, persona, states.get(row.id)) for row in events]
    visible = [item for item in projected if item["visibility"] == "VISIBLE"]
    if unread is True: return [item for item in visible if item["unread"]]
    if unread is False: return [item for item in visible if not item["unread"]]
    return visible


def issue_summary(rows: list[dict[str, Any]], persona: str) -> dict[str, Any]:
    active = [row for row in rows if row["status"] in ACTIVE_FINDING_STATUSES or str(row["status"]) in {str(item) for item in ACTIVE_FINDING_STATUSES}]
    return {
        "persona": persona, "open_issues": len(active), "critical_blocking": sum(row["blocking"] and row["severity"] == "BLOCKING" for row in active),
        "work_items_affected": len({row["entity_id"] for row in active if row["entity_id"]}), "overdue_unassigned": sum(row["sla_state"] == "OVERDUE" and not row["owner_role"] for row in active),
        "open_commercial_issues": sum(row["domain"] in COMMERCIAL for row in active), "open_technical_issues": sum(row["domain"] in TECHNICAL for row in active),
        "blocking_issues": sum(row["blocking"] for row in active), "proposals_affected": len({row["proposal_id"] for row in active if row["proposal_id"]}),
        "contracts_affected": len({row["contract_id"] for row in active if row["contract_id"]}), "permits_affected": len({row["permit_id"] for row in active if row["permit_id"]}),
    }


def notification_summary(rows: list[dict[str, Any]], persona: str) -> dict[str, Any]:
    unread = [row for row in rows if row["unread"]]
    return {
        "persona": persona, "visible": len(rows), "unread": len(unread), "proposal_updates": sum(row["proposal_id"] is not None for row in rows),
        "handoffs": sum("HANDOFF" in row["event_type"] or "READY" in row["event_type"] for row in rows),
        "permit_authority_updates": sum(row["domain"] in {"PERMIT_ADMINISTRATIVE", "PERMIT_TECHNICAL", "AUTHORITY"} for row in rows),
        "contract_updates": sum(row["contract_id"] is not None for row in rows), "client_handoff_updates": sum(row["domain"] in {"CONTRACT", "COMMUNICATION_DELIVERY"} for row in rows),
        "commercial_updates": sum(row["domain"] in COMMERCIAL for row in rows), "engineering_permit_updates": sum(row["domain"] in TECHNICAL for row in rows),
        "critical_alerts": sum(row["severity"] == "BLOCKING" for row in rows),
    }
