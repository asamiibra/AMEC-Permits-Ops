"""Unified four-assistant operating experience over shared workflow records."""

from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select, true
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import AssistantHandoff, AuditEvent, CommunicationDelivery, CommunicationDraft, Finding, LineageEdge, Opportunity, Project, SystemBlock, WorkflowTask

CANONICAL_ASSISTANTS = (
    "BD_ASSISTANT",
    "ADMIN_ASSISTANT",
    "ENGINEERING_REVIEW_ASSISTANT",
    "PROJECT_PERMIT_COORDINATION_ASSISTANT",
)

CAPABILITY_MAP = {
    "BD_ASSISTANT": ["RFQ_INTAKE", "OPPORTUNITY_REVIEW", "BD_CHECKLIST", "QUOTATION_FIELD_REVIEW", "QUOTATION_PREPARATION", "COMMERCIAL_REVIEW_HANDOFF", "CLIENT_RESPONSE_TRACKING"],
    "ADMIN_ASSISTANT": ["CONTRACT_PREPARATION", "CONTRACT_REVIEW_HANDOFF", "CLIENT_CHECKLIST", "MISSING_DOCUMENT_FOLLOWUP", "CONTRACT_MILESTONE_FOLLOWUP", "MUNICIPALITY_FORM_PREPARATION", "REFERENCE_PREPARATION", "ADMIN_COMMUNICATION_DRAFT"],
    "ENGINEERING_REVIEW_ASSISTANT": ["ENGINEERING_REVIEW_PREPARATION", "REGULATION_APPLICABILITY_REVIEW", "ENGINEERING_ADVISORY_ANALYSIS", "ENGINEER_COMMENT_REVIEW", "COMMENT_SHEET_PREPARATION", "DRAWING_REVISION_REVIEW", "BLOCK_TIME_TRACKING"],
    "PROJECT_PERMIT_COORDINATION_ASSISTANT": ["REFERENCE_ASSIGNMENT", "PROJECT_BOOTSTRAP", "SERVER_SYNOLOGY_LINK", "PROJECT_STATUS", "ADMIN_DOCUMENT_REVIEW", "SYSTEM_BLOCK_MANAGEMENT", "PERMIT_HANDOFF", "PERMIT_WORKFLOW_COORDINATION", "AUTHORITY_CHANGE_FOLLOWUP", "FINANCE_HANDOFF", "PROJECT_HANDOVER"],
}

ASSISTANT_OWNER_ROLE = {
    "BD_ASSISTANT": "COMMERCIAL_APPROVER",
    "ADMIN_ASSISTANT": "ADMIN_PROJECT_COORDINATOR",
    "ENGINEERING_REVIEW_ASSISTANT": "AUTHORIZED_ENGINEER",
    "PROJECT_PERMIT_COORDINATION_ASSISTANT": "PERMIT_PREPARER",
}


def _row(item: Any) -> dict[str, Any] | None:
    if not item:
        return None
    return {column.name: getattr(item, column.name) for column in item.__table__.columns}


def assistant_for_task(task: WorkflowTask) -> str:
    if task.assistant_id in CANONICAL_ASSISTANTS:
        return task.assistant_id
    value = (task.task_family or task.task_type or "").upper()
    if any(token in value for token in ("RFQ", "QUOT", "COMMERCIAL")):
        return "BD_ASSISTANT"
    if any(token in value for token in ("ENGINEER", "DRAWING", "COMPLIANCE", "COMMENT_SHEET")):
        return "ENGINEERING_REVIEW_ASSISTANT"
    if any(token in value for token in ("CONTRACT", "CHECKLIST", "DOCUMENT", "ADMIN", "REFERENCE", "MISSING", "MUNICIPALITY_FORM")):
        return "ADMIN_ASSISTANT"
    return "PROJECT_PERMIT_COORDINATION_ASSISTANT"


def derive_next_action(task: WorkflowTask) -> str:
    if task.status in {"BLOCKED", "DISPUTED"} or task.blocking:
        return "RESOLVE_BLOCKER"
    if task.status in {"OPEN", "ACKNOWLEDGED"}:
        return task.next_action_code or "REVIEW_AND_ASSIGN"
    if task.status == "IN_PROGRESS":
        return task.next_action_code or "CONTINUE_ASSISTED_WORK"
    return task.next_action_code or "VIEW_EVIDENCE"


def derive_next_action_details(task: WorkflowTask) -> dict[str, Any]:
    assistant = assistant_for_task(task)
    code = derive_next_action(task)
    labels = {
        "RESOLVE_BLOCKER": "Resolve blocker",
        "ACCEPT_HANDOFF": "Accept assistant handoff",
        "AUTHORIZED_ENGINEER_REVIEW": "Review engineering comment",
        "PREPARE_CONTRACT": "Prepare contract",
        "PREPARE_ENGINEERING_REVIEW": "Prepare engineering review",
        "FINAL_HUMAN_REVIEW": "Complete final human review",
        "BEGIN_ASSISTED_WORK": "Begin assisted work",
        "CONTINUE_ASSISTED_WORK": "Continue assisted work",
        "VIEW_EVIDENCE": "Review evidence",
    }
    reason = "Derived from the shared WorkflowTask state and blocking controls."
    if task.blocking or task.status in {"BLOCKED", "DISPUTED"}:
        reason = "A canonical blocking control must be resolved before downstream work continues."
    elif task.status in {"OPEN", "ACKNOWLEDGED"}:
        reason = f"The shared workflow is waiting for the {task.owner_role} role."
    return {
        "code": code,
        "label": labels.get(code, code.replace("_", " ").title()),
        "reason": reason,
        "assistant_id": assistant,
        "assigned_role": task.owner_role,
        "deep_link": task.deep_link or (f"/work/{task.context_id}" if task.context_id else "/work"),
        "deterministic": True,
    }


def _task_card(task: WorkflowTask) -> dict[str, Any]:
    assistant = assistant_for_task(task)
    next_action = derive_next_action_details(task)
    return {
        **_row(task), "assistant_id": assistant, "next_action": next_action["code"], "next_action_details": next_action,
        "owner": {"role": task.owner_role, "user_id": task.owner_user_id},
        "blocking": bool(task.blocking or task.status == "BLOCKED"),
        "demo_as": True, "synthetic_only": True,
    }


def build_my_work(db: Session, *, assistant_id: str | None = None, role: str | None = None) -> dict[str, Any]:
    if assistant_id and assistant_id not in CANONICAL_ASSISTANTS:
        raise HTTPException(422, "CANONICAL_ASSISTANT_SET_VIOLATION")
    tasks = db.scalars(select(WorkflowTask).order_by(WorkflowTask.created_at.desc())).all()
    cards = [_task_card(task) for task in tasks if (not assistant_id or assistant_for_task(task) == assistant_id) and (not role or task.owner_role == role or task.owner_user_id == role)]
    drafts = db.scalars(select(CommunicationDraft).order_by(CommunicationDraft.created_at.desc())).all()
    blocks = db.scalars(select(SystemBlock).where(SystemBlock.blocking == true()).order_by(SystemBlock.created_at.desc())).all()
    handoffs = db.scalars(select(AssistantHandoff).where(AssistantHandoff.status.in_(("CREATED", "ACCEPTED"))).order_by(AssistantHandoff.created_at.desc())).all()
    summary = {
        "action_required": sum(1 for item in cards if item["status"] in {"OPEN", "ACKNOWLEDGED", "IN_PROGRESS"}),
        "reviews_waiting": sum(1 for item in drafts if item.status in {"HUMAN_REVIEW", "READY_FOR_HUMAN_SEND"}),
        "blocked_work": len(blocks) + sum(1 for item in cards if item["blocking"]),
        "authority_changes": 0,
        "communication_drafts": len(drafts),
        "delivery_failures": sum(1 for draft in drafts for delivery in db.scalars(select(CommunicationDelivery).where(CommunicationDelivery.communication_draft_id == draft.id)).all() if delivery.delivery_status == "FAILED"),
    }
    return {"assistant_ids": list(CANONICAL_ASSISTANTS), "selected_assistant": assistant_id, "role": role or "DEMO_AS_OPERATOR", "summary": summary,
            "items": cards, "communications": [_row(item) for item in drafts], "issues": [_row(item) for item in blocks],
            "handoffs": [_row(item) for item in handoffs], "canonical_queue": "WorkflowTask", "next_action_policy": "DETERMINISTIC_SHARED_STATE",
            "synthetic_only": True, "human_send_required": True, "production_role_switch_allowed": False}


def build_context_packet(db: Session, *, assistant_id: str, task: WorkflowTask) -> dict[str, Any]:
    if assistant_id not in CANONICAL_ASSISTANTS:
        raise HTTPException(422, "CANONICAL_ASSISTANT_SET_VIOLATION")
    project = db.get(Project, task.project_id) if task.project_id else None
    finding = db.get(Finding, task.finding_id) if task.finding_id else None
    return {
        "assistant_id": assistant_id,
        "caller_role": task.owner_role,
        "entity": {"context_type": task.context_type, "context_id": task.context_id, "project_id": task.project_id},
        "current_workflow_stage": task.task_family or task.task_type,
        "task": _row(task),
        "relevant_evidence": task.evidence_summary or {},
        "verified_facts": {"project_number": project.project_number if project else None, "project_name": project.project_name if project else None},
        "blocking_controls": [{"finding_id": finding.id, "title": finding.title, "blocking": finding.blocking}] if finding and finding.blocking else [],
        "current_revisions": list(task.evidence_summary.get("source_revision_ids", [])) if task.evidence_summary else [],
        "communication_state": "HUMAN_SEND",
        "policy": {"execution_authority": "PROTOTYPE_DEV_ONLY", "human_review_required": True, "external_actions": False},
        "next_action": derive_next_action_details(task),
        "synthetic_only": True,
    }


def create_handoff(db: Session, *, from_assistant_id: str, to_assistant_id: str, context_type: str, context_id: str,
                   reason: str, actor: str, correlation_id: str, project_id: str | None = None,
                   opportunity_id: str | None = None, source_revision_ids: list[str] | None = None) -> AssistantHandoff:
    if from_assistant_id not in CANONICAL_ASSISTANTS or to_assistant_id not in CANONICAL_ASSISTANTS or from_assistant_id == to_assistant_id:
        raise HTTPException(422, "INVALID_CANONICAL_ASSISTANT_HANDOFF")
    if context_type == "OPPORTUNITY" and not opportunity_id and db.get(Opportunity, context_id):
        opportunity_id = context_id
    if opportunity_id and not db.get(Opportunity, opportunity_id):
        opportunity_id = None
    if context_type == "PROJECT" and not project_id:
        project_id = context_id
    task = None
    project = db.get(Project, project_id) if project_id else None
    finding = db.scalar(select(Finding).where(Finding.project_id == project_id).order_by(Finding.captured_at)) if project_id else None
    from ..models import PermitApplication
    application = db.scalar(select(PermitApplication).where(PermitApplication.project_id == project_id).order_by(PermitApplication.external_request_number)) if project_id else None
    task = WorkflowTask(project_id=project_id, application_id=application.id if application else None, finding_id=finding.id if finding else None, task_type="ASSISTANT_HANDOFF",
                        title=f"Handoff to {to_assistant_id}", description=reason, owner_role=ASSISTANT_OWNER_ROLE[to_assistant_id], status="OPEN",
                        priority="MEDIUM", correlation_id=correlation_id, assistant_id=to_assistant_id, task_family="HANDOFF",
                        context_type=context_type, context_id=context_id, next_action_code="ACCEPT_HANDOFF", deep_link=f"/work/{context_id}", blocking=False,
                        evidence_summary={"source_revision_ids": sorted(str(item) for item in (source_revision_ids or [])), "same_context_required": True,
                                          "project_truth_id": project_id, "opportunity_truth_id": opportunity_id})
    db.add(task)
    db.flush()
    handoff = AssistantHandoff(from_assistant_id=from_assistant_id, to_assistant_id=to_assistant_id, context_type=context_type,
                               context_id=context_id, project_id=project_id, opportunity_id=opportunity_id,
                               source_revision_ids=sorted(str(item) for item in (source_revision_ids or [])),
                               workflow_task_id=task.id if task else None, status="CREATED", reason=reason)
    db.add(handoff)
    db.flush()
    audit(db, correlation_id=correlation_id, event_type="ASSISTANT_HANDOFF_CREATED", entity_type="AssistantHandoff", entity_id=handoff.id,
          actor_id=actor, after={"from_assistant_id": from_assistant_id, "to_assistant_id": to_assistant_id, "context_id": context_id, "status": "CREATED"},
          metadata={"synthetic_only": True, "source_revision_ids": handoff.source_revision_ids})
    return handoff


def accept_handoff(db: Session, handoff: AssistantHandoff, *, actor: str, correlation_id: str) -> AssistantHandoff:
    if handoff.status != "CREATED":
        raise HTTPException(409, "HANDOFF_NOT_ACCEPTABLE")
    handoff.status = "ACCEPTED"
    handoff.accepted_by = actor
    handoff.accepted_at = datetime.now(timezone.utc)
    if handoff.workflow_task_id:
        task = db.get(WorkflowTask, handoff.workflow_task_id)
        if task:
            task.status = "ACKNOWLEDGED"
            task.next_action_code = "BEGIN_ASSISTED_WORK"
    audit(db, correlation_id=correlation_id, event_type="ASSISTANT_HANDOFF_ACCEPTED", entity_type="AssistantHandoff", entity_id=handoff.id,
          actor_id=(actor or "synthetic-operator")[:36], after={"status": handoff.status, "accepted_by": actor}, metadata={"synthetic_only": True})
    return handoff
