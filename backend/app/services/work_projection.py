"""Canonical AMEC Work projection over existing domain records.

This module is deliberately a projection, not a second task store.  It reads
WorkflowTask, domain lifecycle records, Findings, CommunicationDrafts, and
AssistantHandoffs and normalizes them into one owner-facing work list.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

PERSONA_OWNER = "OWNER"
PERSONA_BD = "BUSINESS_DEVELOPMENT"
PERSONA_ENGINEERING = "ENGINEERING"

ROLE_PERSONA = {
    "SYSTEM_ADMIN": PERSONA_OWNER,
    "OWNER_SPONSOR": PERSONA_OWNER,
    "COMMERCIAL_APPROVER": PERSONA_BD,
    "PROCESS_CHAMPION": PERSONA_BD,
    "BD_USER": PERSONA_BD,
    "BUSINESS_DEVELOPMENT": PERSONA_BD,
    "RESPONSIBLE_ENGINEER": PERSONA_ENGINEERING,
    "AUTHORIZED_ENGINEER": PERSONA_ENGINEERING,
    "REQUIREMENT_STEWARD": PERSONA_ENGINEERING,
    "PERMIT_PREPARER": PERSONA_ENGINEERING,
    "ENGINEERING": PERSONA_ENGINEERING,
}

ACTIVE_STATUSES = {"OPEN", "ACKNOWLEDGED", "IN_PROGRESS", "BLOCKED", "DISPUTED", "DRAFT", "HUMAN_REVIEW", "READY_FOR_HUMAN_SEND", "CREATED"}
DONE_STATUSES = {"COMPLETED", "CANCELLED", "RESOLVED", "CLOSED", "DISMISSED", "SENT", "DELIVERED"}


def persona_for_role(role: str | None) -> str:
    return ROLE_PERSONA.get((role or "SYSTEM_ADMIN").upper(), PERSONA_OWNER)


def _rows(db: Session, table: str) -> list[dict[str, Any]]:
    # Table names are internal constants, never request input.
    return [dict(row) for row in db.execute(text(f"SELECT * FROM {table}" )).mappings().all()]


def _json(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except (TypeError, ValueError):
        return default


def _dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).replace(tzinfo=timezone.utc) if "+" not in str(value) else datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _iso(value: Any) -> str | None:
    parsed = _dt(value)
    return parsed.isoformat() if parsed else None


def _human_role(value: str | None) -> tuple[str, str]:
    persona = persona_for_role(value)
    return persona, {PERSONA_OWNER: "Owner", PERSONA_BD: "Business Development", PERSONA_ENGINEERING: "Engineering"}[persona]


def _owner_copy(value: Any) -> str:
    text_value = str(value or "")
    return text_value.replace("quotation revision", "Proposal revision").replace("Quotation revision", "Proposal revision").replace("quotation", "Proposal").replace("Quotation", "Proposal").replace("quote", "Proposal").replace("Quote", "Proposal")


def _domain_for_task(task: dict[str, Any]) -> str:
    """Resolve the affected business entity, never the storage/source class."""
    context = str(task.get("context_type") or "").upper()
    if context in {"PROPOSAL", "OPPORTUNITY", "QUOTATION"}:
        return "PROPOSAL"
    if context == "CONTRACT":
        return "CONTRACT"
    if context in {"PERMIT", "PERMIT_WORKSPACE", "MUNICIPALITY", "APPLICATION"}:
        return "PERMIT"
    family = str(task.get("task_family") or task.get("task_type") or "").upper()
    if "CONTRACT" in family:
        return "CONTRACT"
    if "PROPOSAL" in family or "QUOT" in family:
        return "PROPOSAL"
    if "PERMIT" in family or "MUNICIPALITY" in family:
        return "PERMIT"
    return "SYSTEM"


def _domain_for_persona(persona: str, domain: str, item: dict[str, Any]) -> bool:
    if persona == PERSONA_OWNER:
        return True
    assigned = item.get("assigned_persona")
    if assigned == persona and not (persona == PERSONA_ENGINEERING and domain == "CONTRACT"):
        return True
    if persona == PERSONA_BD:
        return domain in {"PROPOSAL", "CONTRACT"} and item.get("work_type") in {"ACTION", "REVIEW", "HANDOFF", "COMMUNICATION"}
    if persona == PERSONA_ENGINEERING:
        return domain == "PERMIT" or (domain == "PROPOSAL" and item.get("work_type") in {"ACTION", "REVIEW", "HANDOFF", "BLOCKER_ACTION"})
    return False


def _issue_route(task: dict[str, Any], domain: str, issue_id: str) -> tuple[str, str]:
    focus = f"?issue={issue_id}"
    context_id = task.get("context_id")
    project_id = task.get("project_id")
    title = str(task.get("title") or "").lower()
    if domain == "PROPOSAL":
        return (f"/proposals/{context_id}/preparation{focus}", "Open Preparation") if "sow" in title or "technical" in title else (f"/proposals/{context_id}{focus}", "Review Proposal")
    if domain == "CONTRACT":
        return f"/contracts/{context_id}{focus}", "Review Contract"
    if domain == "PERMIT" and project_id:
        return (f"/proposals-contracts/{project_id}/comments-and-corrections{focus}", "Review Authority Comment") if "authority" in title or "comment" in title else (f"/proposals-contracts/{project_id}/verify-data{focus}", "Review Drawing")
    return (f"/proposals-contracts/{project_id}/project-and-sources{focus}", "Review Source") if project_id else ("/issues", "Review Source")


def _work_item(*, source_type: str, source_id: str, domain: str, work_type: str, entity_type: str, entity_id: str,
               title: str, context: str, reference: str | None, stage: str | None, assigned_persona: str,
               assigned_team: str, next_actor: str | None, priority: str | None, blocking: bool,
               due_at: Any, created_at: Any, last_activity_at: Any, deep_link: str, cta_label: str,
               status: str, project_id: str | None = None, proposal_id: str | None = None,
               contract_id: str | None = None, permit_id: str | None = None,
               canonical_action_key: str | None = None, issue_id: str | None = None) -> dict[str, Any]:
    due = _dt(due_at)
    now = datetime.now(timezone.utc)
    overdue = bool(due and due < now and status not in DONE_STATUSES)
    return {
        "id": f"{source_type}:{source_id}", "source_type": source_type, "source_id": source_id,
        "domain": domain, "work_type": work_type, "entity_type": entity_type, "entity_id": entity_id,
        "project_id": project_id, "proposal_id": proposal_id, "contract_id": contract_id, "permit_id": permit_id,
        "title": title, "business_context": context, "client_name": None, "reference": reference,
        "stage": stage, "assigned_persona": assigned_persona, "assigned_team": assigned_team,
        "assigned_user": None, "next_actor": next_actor, "priority": priority or "NORMAL", "blocking": bool(blocking),
        "due_at": _iso(due_at), "overdue": overdue, "created_at": _iso(created_at),
        "last_activity_at": _iso(last_activity_at or created_at), "deep_link": deep_link,
        "cta_label": cta_label, "status": status, "issue_id": issue_id,
        "canonical_action_key": canonical_action_key or f"{entity_type}:{entity_id}:{work_type}",
    }


def _task_items(tasks: list[dict[str, Any]], references: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for task in tasks:
        status = str(task.get("status") or "OPEN").upper()
        if status in DONE_STATUSES:
            continue
        domain = _domain_for_task(task)
        assigned_persona, assigned_team = _human_role(task.get("owner_role"))
        work_type = "BLOCKER_ACTION" if task.get("blocking") or status in {"BLOCKED", "DISPUTED"} else "REVIEW" if "REVIEW" in str(task.get("task_type") or "").upper() else "HANDOFF" if "HANDOFF" in str(task.get("task_type") or "").upper() else "ACTION"
        title = _owner_copy(task.get("title") or "Work item")
        context_copy = _owner_copy(task.get("description") or "Current workflow action")
        stage = "Issue resolution" if work_type == "BLOCKER_ACTION" else "Handoff" if work_type == "HANDOFF" else {"PROPOSAL": "Proposal review", "CONTRACT": "Contract review", "PERMIT": "Permit review"}.get(domain, "Source integrity")
        entity_id = str(task.get("finding_id") or task.get("context_id") or task["id"]) if domain == "SYSTEM" else str(task.get("context_id") or task["id"])
        entity_type = {"PROPOSAL": "Proposal", "CONTRACT": "Contract", "PERMIT": "Permit"}.get(domain, "System")
        context_ref = references.get(entity_id, {})
        if domain == "SYSTEM" and task.get("project_id"):
            context_ref = references.get(str(task.get("project_id")), context_ref)
        issue_id = task.get("finding_id")
        issue_link, issue_cta = _issue_route(task, domain, str(issue_id)) if issue_id else (task.get("deep_link") or "/work", None)
        task_title = str(task.get("title") or "").lower()
        cta = issue_cta or {"PROPOSAL": "Open Proposal", "CONTRACT": "Open Contract", "PERMIT": "Open Permit"}.get(domain, "Review source")
        result.append(_work_item(source_type="WORKFLOW_TASK", source_id=task["id"], domain=domain, work_type=work_type,
                                 entity_type=entity_type, entity_id=entity_id, title=title,
                                 context=context_copy, reference=context_ref.get("reference"),
                                 stage=stage, assigned_persona=assigned_persona,
                                 assigned_team=assigned_team, next_actor=assigned_team, priority=task.get("priority"),
                                 blocking=bool(task.get("blocking")) or status in {"BLOCKED", "DISPUTED"},
                                 due_at=task.get("due_at"), created_at=task.get("created_at"),
                                 last_activity_at=task.get("started_at") or task.get("acknowledged_at"),
                                 deep_link=issue_link, cta_label=cta, status=status,
                                 project_id=task.get("project_id"), proposal_id=context_ref.get("proposal_id"), contract_id=context_ref.get("contract_id"), permit_id=context_ref.get("permit_id"), canonical_action_key=f"FINDING:{task.get('finding_id')}" if task.get("finding_id") else None, issue_id=issue_id))
    return result


def _proposal_items(proposals: list[dict[str, Any]], contracts: list[dict[str, Any]], task_contexts: set[str]) -> list[dict[str, Any]]:
    result = []
    contract_by_quotation = {row.get("quotation_id"): row for row in contracts}
    for proposal in proposals:
        proposal_id = proposal["id"]
        if proposal_id in task_contexts:
            continue
        status = str(proposal.get("status") or "").upper()
        ref = proposal.get("opportunity_reference")
        created = proposal.get("created_at")
        updated = proposal.get("updated_at")
        if status in {"RECEIVED", "IN_REVIEW"}:
            result.append(_work_item(source_type="OPPORTUNITY", source_id=proposal_id, domain="PROPOSAL", work_type="ACTION", entity_type="Proposal", entity_id=proposal_id, title="Proceed with Proposal intake", context="Tender or client source is waiting for commercial intake.", reference=ref, stage="New Proposal Intake", assigned_persona=PERSONA_BD, assigned_team="Business Development", next_actor="Business Development", priority="NORMAL", blocking=False, due_at=None, created_at=created, last_activity_at=updated, deep_link=f"/proposals/{proposal_id}", cta_label="Open Proposal", status=status, project_id=proposal.get("project_id"), proposal_id=proposal_id))
        elif status == "PROPOSAL_PREPARATION":
            result.append(_work_item(source_type="OPPORTUNITY", source_id=proposal_id, domain="PROPOSAL", work_type="ACTION", entity_type="Proposal", entity_id=proposal_id, title="Prepare Proposal", context="Technical proposal preparation is the current next action.", reference=ref, stage="Engineering Proposal Preparation", assigned_persona=PERSONA_ENGINEERING, assigned_team="Engineering", next_actor="Engineering", priority="NORMAL", blocking=False, due_at=None, created_at=created, last_activity_at=updated, deep_link=f"/proposals/{proposal_id}/preparation", cta_label="Open Proposal", status=status, project_id=proposal.get("project_id"), proposal_id=proposal_id))
        elif status in {"PROPOSAL_HANDOVER", "READY_FOR_QUOTATION", "QUOTATION_IN_PROGRESS", "COMMERCIAL_REVIEW", "CLIENT_RESPONSE_PENDING"}:
            result.append(_work_item(source_type="OPPORTUNITY", source_id=proposal_id, domain="PROPOSAL", work_type="REVIEW" if status in {"PROPOSAL_HANDOVER", "COMMERCIAL_REVIEW"} else "HANDOFF", entity_type="Proposal", entity_id=proposal_id, title="Review Proposal" if status in {"PROPOSAL_HANDOVER", "COMMERCIAL_REVIEW"} else "Complete Proposal handoff", context="The Proposal is waiting for the next Business Development decision.", reference=ref, stage="Business Development Review / Client Response", assigned_persona=PERSONA_BD, assigned_team="Business Development", next_actor="Business Development", priority="NORMAL", blocking=False, due_at=None, created_at=created, last_activity_at=updated, deep_link=f"/proposals/{proposal_id}", cta_label="Open Proposal", status=status, project_id=proposal.get("project_id"), proposal_id=proposal_id))
    return result


def _contract_items(contracts: list[dict[str, Any]], permits_by_contract: dict[str, list[dict[str, Any]]], task_contexts: set[str]) -> list[dict[str, Any]]:
    result = []
    for contract in contracts:
        contract_id = contract["id"]
        if contract_id in task_contexts:
            continue
        status = str(contract.get("status") or "").upper()
        if status not in {"DRAFT", "CONTRACT_IN_PROGRESS", "CONTRACT_HANDOVER", "READY_FOR_ADMIN", "HANDOVER_DRAFT_READY", "HANDOVER_RELEASED"}:
            continue
        if permits_by_contract.get(contract_id):
            continue
        title = "Review Contract" if status in {"DRAFT", "CONTRACT_IN_PROGRESS"} else "Complete Contract handoff"
        result.append(_work_item(source_type="CONTRACT", source_id=contract_id, domain="CONTRACT", work_type="REVIEW" if title.startswith("Review") else "HANDOFF", entity_type="Contract", entity_id=contract_id, title=title, context="Contract lifecycle work is waiting for Business Development.", reference=contract.get("contract_reference"), stage="Contract", assigned_persona=PERSONA_BD, assigned_team="Business Development", next_actor="Business Development", priority="NORMAL", blocking=False, due_at=None, created_at=contract.get("created_at"), last_activity_at=contract.get("updated_at"), deep_link=f"/contracts/{contract_id}", cta_label="Open Contract", status=status, contract_id=contract_id, project_id=contract.get("project_id")))
    return result


def _permit_items(permits: list[dict[str, Any]], projects: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for permit in permits:
        status = str(permit.get("application_status") or "").upper()
        if status in {"APPROVED", "CLOSED", "SUBMITTED_APPROVED"}:
            continue
        project = projects.get(permit.get("project_id"), {})
        project_ref = project.get("project_number") or permit.get("external_request_number")
        workflow_stage = str(permit.get("workflow_stage") or "").upper()
        if status == "RETURNED":
            title, context, stage, blocking = "Review authority comments", "Authority comments require technical correction.", "Comments & Corrections", True
        elif workflow_stage == "VERIFY_DATA":
            title, context, stage, blocking = "Verify project data", "Project and source links are confirmed and the next technical verification is ready.", "Verify Data", False
        elif workflow_stage in {"PREPARE_PACKAGE", "MUNICIPALITY_PREPARATION"}:
            title, context, stage, blocking = "Review package", "The permit package is ready for the next technical review.", "Package Review", False
        elif workflow_stage == "FINAL_REVIEW":
            title, context, stage, blocking = "Review package", "Final permit review is waiting for a human decision.", "Final Review", False
        elif status in {"DRAFT", "PREPARING"}:
            title, context, stage, blocking = "Confirm project & sources", f"{project_ref} needs its source-system links confirmed before verification.", "Project & Sources", True
        else:
            continue
        result.append(_work_item(source_type="PERMIT_APPLICATION", source_id=permit["id"], domain="PERMIT", work_type="BLOCKER_ACTION" if blocking else "ACTION", entity_type="Permit", entity_id=permit["id"], title=title, context=context, reference=permit.get("external_request_number") or project_ref, stage=stage, assigned_persona=PERSONA_ENGINEERING, assigned_team="Engineering", next_actor="Engineering", priority="NORMAL", blocking=blocking, due_at=None, created_at=permit.get("created_at"), last_activity_at=permit.get("updated_at") or permit.get("last_status_at"), deep_link=f"/proposals-contracts/{permit.get('project_id')}/{('comments-and-corrections' if status == 'RETURNED' else 'project-and-sources')}", cta_label="Open Permit", status=status, project_id=permit.get("project_id"), permit_id=permit["id"], contract_id=permit.get("controlling_contract_id")))
    return result


def _finding_items(findings: list[dict[str, Any]], references: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for finding in findings:
        status = str(finding.get("status") or "OPEN").upper()
        if status in DONE_STATUSES:
            continue
        persona, team = _human_role(finding.get("assignee_role") or ("RESPONSIBLE_ENGINEER" if finding.get("discipline") else "OWNER_SPONSOR"))
        project_id = finding.get("project_id")
        proposal_id = finding.get("proposal_id")
        contract_id = finding.get("contract_id")
        raw_domain = str(finding.get("domain") or "").upper()
        permit_id = finding.get("permit_id") or (finding.get("application_id") if raw_domain not in {"SYSTEM", "SYSTEM_INTEGRITY"} else None)
        affected_id = contract_id or proposal_id or permit_id
        affected = references.get(str(affected_id), {}) if affected_id else {}
        domain = "CONTRACT" if contract_id else "PROPOSAL" if proposal_id else "PERMIT" if permit_id or finding.get("discipline") else "SYSTEM"
        entity_type = "Contract" if contract_id else "Proposal" if proposal_id else "Permit" if permit_id else "System"
        route_task = {
            "finding_id": finding["id"],
            "context_id": contract_id or proposal_id or permit_id,
            "project_id": project_id,
            "title": finding.get("title"),
        }
        deep_link, cta = _issue_route(route_task, domain, str(finding["id"]))
        finding_title = _owner_copy(finding.get("title") or "assigned issue")
        title = finding_title if domain == "SYSTEM" else f"Resolve {finding_title}"
        result.append(_work_item(source_type="FINDING", source_id=finding["id"], domain=domain, work_type="BLOCKER_ACTION" if finding.get("blocking") else "ACTION", entity_type=entity_type, entity_id=str(affected_id or finding["id"]), title=title, context=_owner_copy(finding.get("normalized_summary") or finding.get("raw_text") or "An assigned issue needs a governed resolution."), reference=affected.get("reference"), stage="Issue resolution", assigned_persona=persona, assigned_team=team, next_actor=team, priority=finding.get("severity"), blocking=bool(finding.get("blocking")), due_at=finding.get("due_at"), created_at=finding.get("captured_at"), last_activity_at=finding.get("captured_at"), deep_link=deep_link, cta_label=cta, status=status, project_id=project_id, permit_id=permit_id, proposal_id=proposal_id, contract_id=contract_id, canonical_action_key=f"FINDING:{finding['id']}", issue_id=finding["id"]))
    return result


def _communication_items(drafts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for draft in drafts:
        status = str(draft.get("status") or "DRAFT").upper()
        if status not in {"HUMAN_REVIEW", "READY_FOR_HUMAN_SEND"}:
            continue
        action = "Review and send" if status == "READY_FOR_HUMAN_SEND" else "Review draft"
        result.append(_work_item(source_type="COMMUNICATION_DRAFT", source_id=draft["id"], domain="PROPOSAL" if draft.get("context_type") in {"OPPORTUNITY", "PROPOSAL"} else "SYSTEM", work_type="ACTION" if status == "READY_FOR_HUMAN_SEND" else "REVIEW", entity_type="Communication", entity_id=draft["id"], title="Review missing-document email" if draft.get("communication_type") == "MISSING_DOCUMENT" else "Review client communication", context="A client communication is ready for an authorized human review and send decision.", reference=None, stage="Client response", assigned_persona=PERSONA_BD, assigned_team="Business Development", next_actor="Business Development", priority="NORMAL", blocking=False, due_at=None, created_at=draft.get("created_at"), last_activity_at=draft.get("updated_at"), deep_link=f"/notifications?draft={draft['id']}", cta_label=action, status=status))
    return result


def _handoff_items(handoffs: list[dict[str, Any]], references: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    names = {"BD_ASSISTANT": "Business Development", "ENGINEERING_REVIEW_ASSISTANT": "Engineering", "ADMIN_ASSISTANT": "Owner", "PROJECT_PERMIT_COORDINATION_ASSISTANT": "Engineering"}
    for handoff in handoffs:
        if str(handoff.get("status") or "").upper() not in {"CREATED", "ACCEPTED"}:
            continue
        to_team = names.get(handoff.get("to_assistant_id"), "Owner")
        assigned = PERSONA_BD if to_team == "Business Development" else PERSONA_ENGINEERING if to_team == "Engineering" else PERSONA_OWNER
        domain = "PROPOSAL" if handoff.get("context_type") == "OPPORTUNITY" else "CONTRACT" if handoff.get("context_type") == "CONTRACT" else "PERMIT" if handoff.get("project_id") else "SYSTEM"
        entity_type = "Proposal" if handoff.get("opportunity_id") else "Contract" if domain == "CONTRACT" else "Permit" if handoff.get("project_id") else "System"
        entity_id = str(handoff.get("opportunity_id") or handoff.get("context_id") or handoff.get("project_id") or handoff["id"])
        reference = references.get(entity_id, {}).get("reference")
        deep_link = f"/proposals/{handoff.get('opportunity_id')}" if handoff.get("opportunity_id") else f"/contracts/{handoff.get('context_id')}" if domain == "CONTRACT" else f"/proposals-contracts/{handoff.get('project_id')}/history" if handoff.get("project_id") else "/work"
        result.append(_work_item(source_type="ASSISTANT_HANDOFF", source_id=handoff["id"], domain=domain, work_type="HANDOFF", entity_type=entity_type, entity_id=entity_id, title=f"Handoff to {to_team}", context=handoff.get("reason") or "A cross-team handoff is waiting for acceptance.", reference=reference, stage="Handoff", assigned_persona=assigned, assigned_team=to_team, next_actor=to_team, priority="NORMAL", blocking=False, due_at=None, created_at=handoff.get("created_at"), last_activity_at=handoff.get("updated_at"), deep_link=deep_link, cta_label={"PROPOSAL": "Open Proposal", "CONTRACT": "Open Contract", "PERMIT": "Open Permit"}.get(domain, "Review source"), status=str(handoff.get("status") or "CREATED")))
    return result


def _reference_map(proposals: list[dict[str, Any]], contracts: list[dict[str, Any]], permits: list[dict[str, Any]], projects: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for proposal in proposals:
        result[str(proposal["id"])] = {"reference": proposal.get("opportunity_reference"), "proposal_id": proposal.get("id")}
    for contract in contracts:
        result[str(contract["id"])] = {"reference": contract.get("contract_reference"), "contract_id": contract.get("id")}
    for permit in permits:
        project = projects.get(permit.get("project_id"), {})
        result[str(permit["id"])] = {"reference": permit.get("external_request_number") or project.get("project_number"), "permit_id": permit.get("id")}
    for project in projects.values():
        result.setdefault(str(project["id"]), {"reference": project.get("project_number"), "project_id": project.get("id")})
    return result


def _dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    source_priority = {"WORKFLOW_TASK": 0, "ASSISTANT_HANDOFF": 1, "OPPORTUNITY": 2, "CONTRACT": 3, "PERMIT_APPLICATION": 4, "FINDING": 5, "COMMUNICATION_DRAFT": 6}
    chosen: dict[str, dict[str, Any]] = {}
    for item in items:
        key = item.get("canonical_action_key") or item["id"]
        current = chosen.get(key)
        if current is None or source_priority.get(item.get("source_type"), 99) < source_priority.get(current.get("source_type"), 99):
            chosen[key] = item
    return list(chosen.values())


def _recent_changes(events: list[dict[str, Any]], persona: str) -> list[dict[str, Any]]:
    result = []
    for event in sorted(events, key=lambda row: str(row.get("created_at") or ""), reverse=True):
        audience = _json(event.get("audience"), [])
        audience_values = {str(value).upper() for value in audience}
        event_type = str(event.get("event_type") or "").upper()
        if event_type not in {"ENGINEERING_PROPOSAL_READY", "CLIENT_INFORMATION_REQUIRED", "AUTHORITY_COMMENT_CAPTURED"}:
            continue
        audience_fallback = {
            PERSONA_BD: {"ENGINEERING_PROPOSAL_READY", "CLIENT_INFORMATION_REQUIRED"},
            PERSONA_ENGINEERING: {"ENGINEERING_PROPOSAL_READY", "AUTHORITY_COMMENT_CAPTURED"},
        }
        if audience and persona not in audience_values and not (persona == PERSONA_BD and "BUSINESS_DEVELOPMENT" in audience_values) and event_type not in audience_fallback.get(persona, set()):
            continue
        if event_type == "ENGINEERING_PROPOSAL_READY":
            title, detail = "Proposal preparation completed", "Engineering completed Proposal preparation and sent it to Business Development."
        elif event_type == "CLIENT_INFORMATION_REQUIRED":
            title, detail = "Client clarification requested", "Business Development needs additional client information before Proposal release."
        elif event_type == "AUTHORITY_COMMENT_CAPTURED":
            title, detail = "Authority comment captured", "A technical authority comment is available for Engineering review."
        else:
            title = event.get("subject") or "Business change recorded"
            detail = event.get("body_preview") or "A material Proposal, Contract, or Permit change was recorded."
        result.append({"id": event["id"], "title": title, "detail": detail, "when": _iso(event.get("created_at")), "deep_link": event.get("deep_link") or "/notifications"})
        if len(result) == 5:
            break
    return result


def _rank(item: dict[str, Any]) -> tuple[Any, ...]:
    priority = {"CRITICAL": 0, "HIGH": 1, "URGENT": 1, "MEDIUM": 2, "NORMAL": 3, "LOW": 4}.get(str(item.get("priority") or "NORMAL").upper(), 3)
    due = _dt(item.get("due_at")) or datetime.max.replace(tzinfo=timezone.utc)
    created = _dt(item.get("created_at")) or datetime.max.replace(tzinfo=timezone.utc)
    return (0 if item.get("blocking") else 1, 0 if item.get("overdue") else 1, due, priority, created, item.get("id") or "")


def _filter_items(items: list[dict[str, Any]], persona: str, team: str | None, domain: str | None, kpi: str | None) -> list[dict[str, Any]]:
    visible = [item for item in items if _domain_for_persona(persona, item["domain"], item)]
    if team and team.lower() not in {"all", "all teams"}:
        team_map = {"business_development": "Business Development", "engineering": "Engineering", "owner": "Owner", "unassigned": None}
        expected = team_map.get(team.lower().replace(" ", "_"), team)
        visible = [item for item in visible if (item.get("assigned_team") is None if expected is None else item.get("assigned_team") == expected)]
    if domain and domain.lower() not in {"all", "all work"}:
        visible = [item for item in visible if item.get("domain") == domain.upper()]
    if kpi and kpi.lower() not in {"all", "all work"}:
        key = kpi.lower()
        if key in {"needs_action", "action"}:
            visible = [item for item in visible if item["work_type"] in {"ACTION", "HANDOFF", "BLOCKER_ACTION", "COMMUNICATION"} and item["work_type"] != "REVIEW"]
        elif key in {"waiting_review", "review"}:
            visible = [item for item in visible if item["work_type"] == "REVIEW"]
        elif key == "blocked":
            visible = [item for item in visible if item["blocking"]]
        elif key == "overdue":
            visible = [item for item in visible if item["overdue"]]
    return sorted(visible, key=_rank)


def project_work(db: Session, *, role: str | None = None, team: str | None = None, domain: str | None = None, kpi: str | None = None) -> dict[str, Any]:
    persona = persona_for_role(role)
    logger.info("AMEC Work projection persona=%s team=%s domain=%s kpi=%s", persona, team, domain, kpi)
    try:
        projects = {row["id"]: row for row in _rows(db, "projects")}
        proposals = _rows(db, "opportunities")
        contracts = _rows(db, "contracts")
        permits = _rows(db, "permit_applications")
        tasks = _rows(db, "workflow_tasks")
        findings = _rows(db, "findings")
        drafts = _rows(db, "communication_drafts")
        handoffs = _rows(db, "assistant_handoffs")
        events = _rows(db, "notification_events")
    except Exception:
        logger.exception("AMEC Work projection failed persona=%s team=%s domain=%s kpi=%s", persona, team, domain, kpi)
        raise
    references = _reference_map(proposals, contracts, permits, projects)
    task_contexts = {str(item.get("context_id")) for item in tasks if item.get("context_id") and str(item.get("status") or "").upper() not in DONE_STATUSES}
    permits_by_contract: dict[str, list[dict[str, Any]]] = {}
    for permit in permits:
        if permit.get("controlling_contract_id"):
            permits_by_contract.setdefault(permit["controlling_contract_id"], []).append(permit)
    items = _task_items(tasks, references)
    items.extend(_proposal_items(proposals, contracts, task_contexts))
    items.extend(_contract_items(contracts, permits_by_contract, task_contexts))
    items.extend(_permit_items(permits, projects))
    items.extend(_finding_items(findings, references))
    items.extend(_communication_items(drafts))
    items.extend(_handoff_items(handoffs, references))
    items = _dedupe_items(items)
    visible = _filter_items(items, persona, team, domain, kpi)
    summary_items = _filter_items(items, persona, team, domain, None)
    all_visible = _filter_items(items, persona, None, None, None)
    summary = {
        "needs_action": sum(1 for item in summary_items if item["work_type"] in {"ACTION", "HANDOFF", "BLOCKER_ACTION", "COMMUNICATION"} and item["work_type"] != "REVIEW"),
        "waiting_review": sum(1 for item in summary_items if item["work_type"] == "REVIEW"),
        "blocked": sum(1 for item in summary_items if item["blocking"]),
        "overdue": sum(1 for item in summary_items if item["overdue"]),
    }
    return {"persona": persona, "filters": {"team": team or "all", "domain": domain or "all", "kpi": kpi or "all"}, "summary": summary, "items": visible, "handoffs": [item for item in visible if item["work_type"] == "HANDOFF"], "recent_changes": _recent_changes(events, persona), "total_visible": len(visible), "context_visible_count": len(summary_items), "unfiltered_visible_count": len(all_visible), "has_unassigned": any(item.get("assigned_team") is None for item in all_visible), "projection": "AMEC Work", "synthetic_only": True}
