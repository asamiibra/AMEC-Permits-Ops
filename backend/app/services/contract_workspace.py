"""Canonical Administration Contract workspace behavior."""

from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import (
    AuditEvent, ClientAccount, Contract, ContractAdminEvidence, ContractAdminInput,
    ContractReferenceSequence, ContractRevision, ContractTemplateSnapshot,
    Finding, LineageEdge, NotificationEvent, Opportunity, Project, ProjectActivation,
    ProposalAcceptedRevision, Quotation, QuotationRevision, WorkflowTask,
)
from .master_content import resolve_master_content_purpose
from .proposal_workspace import stable_hash
from .owner_decisions import runtime_decision_value


CONTRACT_STAGES = ("DRAFT", "NEEDS_ACTION", "AUTHORITY_REVIEW", "READY", "ACTIVE", "CLOSED")
DEFAULT_CONTRACT_INPUTS = {
    "manual_contract_policy": {"value": "SELECT_ACCEPTED_PROPOSAL_ONLY", "status": "SAFE_DEFAULT"},
    "contract_close_date_meaning": {"value": "EXPECTED_CLOSE_DATE_UNTIL_OWNER_CONFIRMED", "status": "SAFE_DEFAULT"},
    "contract_template_required": {"value": True, "status": "SAFE_DEFAULT"},
    "authority_review_meaning": {"value": "OWNER_REVIEW_REQUIRED_NOT_LEGAL_EXECUTION", "status": "SAFE_DEFAULT"},
    "project_activation_trigger": {"value": "EXPLICIT_OWNER_ACTION", "status": "SAFE_DEFAULT"},
    "project_code_assignment": {"value": "OWNER_ENTERED_UNIQUE", "status": "SAFE_DEFAULT"},
    "project_start_date_semantics": {"value": "ORIGINAL_HUMAN_ACTIVATION_DATE", "status": "SAFE_DEFAULT"},
    "contract_reopen_policy": {"value": "OWNER_DECISION_REQUIRED", "status": "SAFE_DEFAULT"},
}
CONTRACT_GO_LIVE_SPECS = [
    ("CONTRACT_REFERENCE_POLICY", "Contract reference prefix, padding, uniqueness, and Owner override policy."),
    ("CONTRACT_STAGE_NAMES", "Stage names and business meanings for Draft, Needs Action, Authority Review, Ready / Close, Active, and Closed."),
    ("CONTRACT_CLOSE_DATE_MEANING", "Whether Close Date means expected close, actual close, completion, or another Owner-defined event."),
    ("CONTRACT_AUTHORITY_REVIEW", "Authority Review meaning, authorized role, and required inputs before Ready / Close."),
    ("CONTRACT_AMOUNT_CHANGE_AUTHORITY", "Who may change amount, currency, duration, and other commercial terms after Proposal acceptance."),
    ("CONTRACT_PROPOSAL_INITIATION_RULE", "Whether Contract starts only from an accepted Proposal revision or may be manually created by Owner."),
    ("CONTRACT_REQUIRED_FIELDS", "Required Client, Contract Reference, Project / Opportunity Ref, Amount, Currency, Duration, and Close Date fields."),
    ("CONTRACT_REQUIRED_EVIDENCE", "Required signed, award, authority, commercial, or client evidence classes and storage locations."),
    ("CONTRACT_TEMPLATE_POLICY", "Canonical Dashboard Contract Template purpose and snapshot/version policy."),
    ("PROJECT_ACTIVATION_AUTHORITY", "Human Owner role and readiness gate for Project Activation."),
    ("PROJECT_CODE_POLICY", "Project Code format, uniqueness, assignment method, and mutability."),
    ("PROJECT_START_DATE_SEMANTICS", "Meaning of Start Date and preservation of the original activation event."),
    ("DOWNSTREAM_PROJECT_CONTEXT", "Canonical Contract, Client, Project Code, Start Date, and lineage fields visible to Engineering and Permit."),
    ("CLIENT_CANONICAL_SOURCE", "Canonical Client Account source and duplicate matching policy."),
    ("PROJECT_CANONICAL_SOURCE", "Canonical Project source and Project / Opportunity Reference policy."),
    ("CONTRACT_MY_WORK_ROUTING", "Owner task routing and next-action semantics for Contract work."),
    ("CONTRACT_ISSUE_ROUTING", "Issue ownership, blocking semantics, and escalation for Contract readiness."),
    ("CONTRACT_NOTIFICATION_AUDIENCE", "In-app notification audiences and follow-up policy."),
    ("CONTRACT_ARTIFACT_SOR", "Contract evidence and rendered artifact source-of-record location."),
    ("CONTRACT_REOPEN_POLICY", "Owner policy for reopening a Ready or Closed Contract."),
    ("CONTRACT_PERMIT_HANDOFF", "Explicit readiness and authority required before downstream Permit handoff."),
    ("REAL_SYNOLOGY_VERIFICATION", "Production Synology health verification remains an external go-live dependency."),
]


def now() -> datetime:
    return datetime.now(timezone.utc)


def actor_name(actor: Any) -> str:
    return getattr(actor, "value", str(actor))


def effective_contract_stages(db: Session) -> tuple[str, ...]:
    configured = runtime_decision_value(db, "CONTRACT_STAGE_POLICY", {"stages": list(CONTRACT_STAGES)})
    stages = configured.get("stages") if isinstance(configured, dict) else None
    normalized = tuple(str(item).upper() for item in stages or CONTRACT_STAGES)
    return normalized or CONTRACT_STAGES


def effective_contract_reference_policy(db: Session) -> dict[str, Any]:
    return runtime_decision_value(db, "CONTRACT_REFERENCE_POLICY", {"prefix": "C-DEMO", "padding": 3, "unique": True, "owner_override": True})


def effective_required_fields(db: Session) -> list[str]:
    return list(runtime_decision_value(db, "CONTRACT_REQUIRED_FIELDS", ["CLIENT", "CONTRACT_REFERENCE", "PROJECT_OPPORTUNITY_REFERENCE", "AMOUNT"]))


def effective_required_evidence(db: Session) -> list[str]:
    # The current safe implementation proves the accepted revision and the
    # canonical template.  Additional Owner-approved evidence classes become
    # blockers only after the corresponding Step 5 decision is applied.
    return list(runtime_decision_value(db, "CONTRACT_REQUIRED_EVIDENCE", ["ACCEPTED_PROPOSAL_REVISION", "CONTRACT_TEMPLATE_SNAPSHOT"]))


def effective_activation_fields(db: Session) -> list[str]:
    return list(runtime_decision_value(db, "PROJECT_ACTIVATION_REQUIRED_FIELDS", ["CONTRACT", "ACCEPTED_PROPOSAL_REVISION", "PROJECT_CODE", "START_DATE", "CLIENT"]))


def fields_from_revision(revision: ProposalAcceptedRevision) -> dict[str, Any]:
    return dict(revision.snapshot.get("fields") or {})


def accepted_revision(db: Session, proposal_id: str, revision_id: str | None = None) -> ProposalAcceptedRevision | None:
    if revision_id:
        row = db.get(ProposalAcceptedRevision, revision_id)
        return row if row and row.proposal_id == proposal_id and row.status == "ACCEPTED" else None
    return db.scalar(select(ProposalAcceptedRevision).where(ProposalAcceptedRevision.proposal_id == proposal_id, ProposalAcceptedRevision.status == "ACCEPTED").order_by(ProposalAcceptedRevision.revision_number.desc()))


def _next_reference(db: Session) -> str:
    sequence = db.scalar(select(ContractReferenceSequence).where(ContractReferenceSequence.sequence_key == "CONTRACT"))
    if not sequence:
        sequence = ContractReferenceSequence(sequence_key="CONTRACT", next_number=1)
        db.add(sequence)
        db.flush()
    number = sequence.next_number
    sequence.next_number += 1
    policy = effective_contract_reference_policy(db)
    prefix = str(policy.get("prefix") or "C-DEMO")
    padding = int(policy.get("padding") or 3)
    return f"{prefix}-{number:0{padding}d}"


def _snapshot_template(db: Session, contract: Contract, revision: ContractRevision, actor: str) -> dict[str, Any] | None:
    resolved = resolve_master_content_purpose(db, module="ADMIN", usage_type="CONTRACT_TEMPLATE")
    if resolved["status"] != "RESOLVED":
        return None
    item = resolved["item"]
    existing = db.scalar(select(ContractTemplateSnapshot).where(ContractTemplateSnapshot.contract_revision_id == revision.id))
    if existing:
        return {"id": existing.id, "ref": existing.master_content_ref, "version_id": existing.document_version_id, "version": existing.version, "hash": existing.content_hash, "master_content_id": existing.master_content_id}
    snap = ContractTemplateSnapshot(contract_id=contract.id, contract_revision_id=revision.id, master_content_id=item["id"], master_content_ref=item["ref"], document_version_id=item["version_id"], version=str(item["version"]), content_hash=item["hash"], captured_by=actor)
    db.add(snap)
    db.flush()
    return {"id": snap.id, "ref": snap.master_content_ref, "version_id": snap.document_version_id, "version": snap.version, "hash": snap.content_hash, "master_content_id": snap.master_content_id}


def _ensure_task_notification(db: Session, contract: Contract, correlation_id: str, actor: str) -> None:
    task = db.scalar(select(WorkflowTask).where(WorkflowTask.context_type == "CONTRACT", WorkflowTask.context_id == contract.id, WorkflowTask.status.in_(("OPEN", "IN_PROGRESS"))).order_by(WorkflowTask.created_at))
    if not task:
        task = WorkflowTask(project_id=contract.project_id, task_type="CONTRACT_ADMIN_REVIEW", title=f"Review {contract.contract_reference}", description="Owner review of Contract readiness, authority inputs, and explicit Project activation.", owner_role="OWNER", status="OPEN", priority="NORMAL", correlation_id=correlation_id, task_family="CONTRACTS", context_type="CONTRACT", context_id=contract.id, blocking=False, next_action_code="CONTRACT_READINESS", deep_link=f"/contracts/{contract.id}", evidence_summary={"contract_id": contract.id})
        db.add(task)
        db.flush()
        db.add(NotificationEvent(workflow_task_id=task.id, recipient_role="OWNER", channel="IN_APP", event_type="CONTRACT_ADMIN_REVIEW_REQUIRED", status="PENDING", subject=f"Contract review: {contract.contract_reference}", body_preview="A Contract was created from an accepted Proposal revision and needs Owner review.", correlation_id=correlation_id, domain="CONTRACT_WORKFLOW", contract_id=contract.id, proposal_id=contract.proposal_id, audience=["OWNER"], actor=actor, deep_link=f"/contracts/{contract.id}"))


def create_contract_from_proposal(db: Session, *, proposal: Opportunity, accepted: ProposalAcceptedRevision, actor: str, correlation_id: str, requested_reference: str | None = None) -> Contract:
    if not proposal.client_account_id:
        raise ValueError("CLIENT_CONTEXT_REQUIRED")
    existing = db.scalar(select(Contract).where(Contract.proposal_id == proposal.id, Contract.accepted_proposal_revision_id == accepted.id).order_by(Contract.created_at.desc()))
    if existing:
        return existing
    quotation = db.scalar(select(Quotation).where(Quotation.opportunity_id == proposal.id).order_by(Quotation.created_at.desc()))
    if not quotation:
        quotation = Quotation(opportunity_id=proposal.id, quotation_reference=f"AMEC-SYN-QTN-{db.query(Quotation).count() + 1:04d}", status="RELEASED_FOR_CONTRACT", client_account_id=proposal.client_account_id)
        db.add(quotation)
        db.flush()
    quotation_revision = db.get(QuotationRevision, quotation.current_revision_id) if quotation.current_revision_id else None
    if not quotation_revision:
        quotation_revision = QuotationRevision(quotation_id=quotation.id, revision_number=1, source_snapshot=accepted.snapshot, content_hash=accepted.content_hash, semantic_hash=stable_hash(accepted.snapshot.get("fields", {})), status="RELEASED", created_by=actor)
        db.add(quotation_revision)
        db.flush()
        quotation.current_revision_id = quotation_revision.id
    fields = fields_from_revision(accepted)
    reference = requested_reference or _next_reference(db)
    if db.scalar(select(Contract).where(Contract.contract_reference == reference)):
        raise ValueError("CONTRACT_REFERENCE_NOT_UNIQUE")
    contract = Contract(client_account_id=proposal.client_account_id, quotation_id=quotation.id, contract_reference=reference, status="DRAFT", stage="DRAFT", contract_name=f"{proposal.title} Contract", proposal_id=proposal.id, accepted_proposal_revision_id=accepted.id, project_id=proposal.project_id, project_opportunity_ref=accepted.snapshot.get("project_reference") or proposal.canonical_project_reference or proposal.provisional_reference, amount_value=fields.get("price"), currency=fields.get("currency"), duration=fields.get("duration") or fields.get("period"), field_provenance={key: {"source": "PROPOSAL_ACCEPTED_REVISION", "accepted_revision_id": accepted.id, "content_hash": accepted.content_hash} for key in ("contract_name", "project_opportunity_ref", "amount_value", "currency", "duration")}, last_activity_at=now())
    db.add(contract)
    db.flush()
    revision = ContractRevision(contract_id=contract.id, revision_number=1, controlling_quotation_revision_id=quotation_revision.id, accepted_proposal_revision_id=accepted.id, source_snapshot=accepted.snapshot, contract_name=contract.contract_name, stage=contract.stage, amount_value=contract.amount_value, currency=contract.currency, duration=contract.duration, status="DRAFT", content_hash=stable_hash({"accepted_revision_id": accepted.id, "fields": fields}), commercial_terms_snapshot={**fields, "proposal_accepted_revision_id": accepted.id, "proposal_content_hash": accepted.content_hash})
    db.add(revision)
    db.flush()
    contract.current_revision_id = revision.id
    template = _snapshot_template(db, contract, revision, actor)
    proposal.status = "CONTRACT_HANDOVER"
    _ensure_task_notification(db, contract, correlation_id, actor)
    audit(db, correlation_id=correlation_id, event_type="ADMIN_CONTRACT_CREATED_FROM_ACCEPTED_PROPOSAL", entity_type="Contract", entity_id=contract.id, actor_id=actor, after={"contract_reference": contract.contract_reference, "accepted_proposal_revision_id": accepted.id, "accepted_revision_hash": accepted.content_hash, "template_snapshot": template, "machine_legal_contract": False})
    return contract


def readiness(db: Session, contract: Contract) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    required_fields = set(effective_required_fields(db))
    if "CLIENT" in required_fields and not contract.client_account_id: blockers.append({"code": "CLIENT_CONTEXT_REQUIRED", "label": "Canonical Client"})
    if "CONTRACT_REFERENCE" in required_fields and not contract.contract_reference: blockers.append({"code": "CONTRACT_REFERENCE_REQUIRED", "label": "Contract Reference"})
    if "ACCEPTED_PROPOSAL_REVISION" in required_fields and not contract.accepted_proposal_revision_id: blockers.append({"code": "ACCEPTED_PROPOSAL_REVISION_REQUIRED", "label": "Exact accepted Proposal revision"})
    if "AMOUNT" in required_fields and not contract.amount_value: blockers.append({"code": "CONTRACT_AMOUNT_REQUIRED", "label": "Contract Amount"})
    if "CURRENCY" in required_fields and not contract.currency: blockers.append({"code": "CONTRACT_CURRENCY_REQUIRED", "label": "Contract Currency"})
    if "DURATION" in required_fields and not contract.duration: blockers.append({"code": "CONTRACT_DURATION_REQUIRED", "label": "Contract Duration"})
    if "PROJECT_OPPORTUNITY_REFERENCE" in required_fields and not contract.project_opportunity_ref: blockers.append({"code": "PROJECT_OPPORTUNITY_REFERENCE_REQUIRED", "label": "Project / Opportunity Reference"})
    if not contract.currency: warnings.append({"code": "CONTRACT_CURRENCY_REVIEW", "label": "Confirm currency"})
    template = db.scalar(select(ContractTemplateSnapshot).where(ContractTemplateSnapshot.contract_id == contract.id).order_by(ContractTemplateSnapshot.captured_at.desc()))
    required_evidence = set(effective_required_evidence(db))
    if "CONTRACT_TEMPLATE_SNAPSHOT" in required_evidence and not template: blockers.append({"code": "CONTRACT_TEMPLATE_REQUIRED", "label": "Canonical Dashboard Contract Template"})
    evidence = db.scalars(select(ContractAdminEvidence).where(ContractAdminEvidence.contract_id == contract.id)).all()
    if "COMMERCIAL_OR_AWARD_EVIDENCE" in required_evidence and not any(item.evidence_type in {"COMMERCIAL", "AWARD", "COMMERCIAL_OR_AWARD_EVIDENCE"} for item in evidence):
        blockers.append({"code": "COMMERCIAL_OR_AWARD_EVIDENCE_REQUIRED", "label": "Commercial or award evidence"})
    activation = db.scalar(select(ProjectActivation).where(ProjectActivation.contract_id == contract.id))
    activation_blockers = [] if activation else [{"code": "PROJECT_ACTIVATION_HUMAN_ACTION_REQUIRED", "label": "Explicit Project Activation"}]
    return {"ready": not blockers, "blockers": blockers, "warnings": warnings, "activation_ready": bool(activation), "activation_blockers": activation_blockers, "authority_state": contract.authority_state, "template_snapshot": template, "effective_required_fields": sorted(required_fields), "effective_required_evidence": sorted(required_evidence), "authority_review_meaning": runtime_decision_value(db, "CONTRACT_AUTHORITY_REVIEW_MEANING", "OWNER_REVIEW_REQUIRED_NOT_LEGAL_EXECUTION"), "ready_close_policy": runtime_decision_value(db, "CONTRACT_READY_CLOSE_POLICY", "REQUIRED_FIELDS_EVIDENCE_AND_OWNER_AUTHORITY_ACTION")}


def project_activation(db: Session, *, contract: Contract, project_code: str, start_date: date, actor: str, correlation_id: str, idempotency_key: str) -> tuple[Project, ProjectActivation, bool]:
    activation_fields = set(effective_activation_fields(db))
    if "CONTRACT" in activation_fields and not contract.id:
        raise ValueError("CONTRACT_REQUIRED_FOR_PROJECT_ACTIVATION")
    if "ACCEPTED_PROPOSAL_REVISION" in activation_fields and not contract.accepted_proposal_revision_id:
        raise ValueError("ACCEPTED_PROPOSAL_REVISION_REQUIRED")
    if "CLIENT" in activation_fields and not contract.client_account_id:
        raise ValueError("CLIENT_CONTEXT_REQUIRED")
    assignment = runtime_decision_value(db, "PROJECT_CODE_ASSIGNMENT_METHOD", "OWNER_ENTERED_UNIQUE")
    if assignment == "OWNER_ENTERED_UNIQUE" and not project_code.strip():
        raise ValueError("PROJECT_CODE_REQUIRED")
    code_policy = runtime_decision_value(db, "PROJECT_CODE_FORMAT", None)
    if isinstance(code_policy, dict) and code_policy.get("pattern"):
        pattern = str(code_policy["pattern"])
        if pattern == "AMEC-YYYY-NNN":
            pattern = r"AMEC-\d{4}-\d{3}"
        if not re.fullmatch(pattern, project_code):
            raise ValueError("PROJECT_CODE_FORMAT_INVALID")
    existing = db.scalar(select(ProjectActivation).where(ProjectActivation.contract_id == contract.id))
    if existing:
        project = db.get(Project, existing.project_id)
        if existing.project_code != project_code or existing.start_date != start_date:
            raise ValueError("PROJECT_ALREADY_ACTIVATED_IMMUTABLE")
        return project, existing, False
    if db.scalar(select(Project).where(Project.project_code == project_code)):
        raise ValueError("PROJECT_CODE_NOT_UNIQUE")
    proposal = db.get(Opportunity, contract.proposal_id) if contract.proposal_id else None
    project = db.get(Project, contract.project_id) if contract.project_id else None
    if not project and contract.project_opportunity_ref:
        project = db.scalar(select(Project).where(Project.project_number == contract.project_opportunity_ref))
    if not project:
        if not proposal:
            raise ValueError("PROJECT_CONTEXT_REQUIRED")
        fields = proposal.proposal_fields_json or {}
        office_id = proposal.office_id
        project = Project(project_number=contract.project_opportunity_ref or f"OPP-{contract.contract_reference}", project_name=contract.contract_name or proposal.title, office_id=office_id, workstream="CONTRACT", status="ACTIVE", municipality=str(fields.get("municipality") or fields.get("location") or "Not configured"), permit_type=str(fields.get("permit_type") or "Not configured"))
        db.add(project)
        db.flush()
    project.project_code = project_code
    project.start_date = start_date
    project.activated_at = now()
    project.activated_by = actor
    project.status = "ACTIVE"
    contract.project_id = project.id
    contract.stage = "ACTIVE"
    contract.status = "ACTIVE"
    contract.last_activity_at = now()
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else db.scalar(select(ContractRevision).where(ContractRevision.contract_id == contract.id).order_by(ContractRevision.revision_number.desc()))
    if not revision:
        raise ValueError("CONTRACT_REVISION_REQUIRED")
    activation = ProjectActivation(contract_id=contract.id, contract_revision_id=revision.id, accepted_proposal_revision_id=contract.accepted_proposal_revision_id, project_id=project.id, project_code=project_code, start_date=start_date, original_start_date=start_date, activated_by=actor, idempotency_key=idempotency_key, audit_metadata={"authority": "HUMAN_OWNER", "contract_reference": contract.contract_reference})
    db.add(activation)
    db.flush()
    for upstream_type, upstream_id, upstream_hash in (("Contract", contract.id, contract.contract_reference), ("ContractRevision", revision.id, revision.content_hash), ("ProposalAcceptedRevision", contract.accepted_proposal_revision_id, None)):
        if not upstream_id: continue
        if not db.scalar(select(LineageEdge).where(LineageEdge.project_id == project.id, LineageEdge.upstream_type == upstream_type, LineageEdge.upstream_id == upstream_id, LineageEdge.downstream_type == "Project", LineageEdge.downstream_id == project.id)):
            db.add(LineageEdge(project_id=project.id, upstream_type=upstream_type, upstream_id=upstream_id, upstream_version_or_hash=upstream_hash, downstream_type="Project", downstream_id=project.id, downstream_version_or_hash=project_code, dependency_kind="CONTRACT_PROJECT_ACTIVATION", correlation_id=correlation_id))
    audit(db, correlation_id=correlation_id, event_type="HUMAN_PROJECT_ACTIVATED_FROM_CONTRACT", entity_type="Project", entity_id=project.id, actor_id=actor, after={"contract_id": contract.id, "contract_revision_id": revision.id, "accepted_proposal_revision_id": contract.accepted_proposal_revision_id, "project_code": project_code, "start_date": start_date.isoformat(), "automatic": False})
    db.add(NotificationEvent(recipient_role="OWNER", channel="IN_APP", event_type="PROJECT_ACTIVATED", status="PENDING", subject=f"Project activated: {project.project_code}", body_preview="Owner explicitly activated the canonical Project from the Contract workbench.", correlation_id=correlation_id, domain="CONTRACT_WORKFLOW", contract_id=contract.id, proposal_id=contract.proposal_id, audience=["OWNER", "BUSINESS_DEVELOPMENT", "ENGINEERING"], actor=actor, deep_link=f"/contracts/{contract.id}"))
    return project, activation, True


def contract_projection(db: Session, contract: Contract, *, include_history: bool = True) -> dict[str, Any]:
    proposal = db.get(Opportunity, contract.proposal_id) if contract.proposal_id else None
    if not proposal and contract.quotation_id:
        quotation = db.get(Quotation, contract.quotation_id)
        proposal = db.get(Opportunity, quotation.opportunity_id) if quotation else None
    client = db.get(ClientAccount, contract.client_account_id) if contract.client_account_id else None
    project = db.get(Project, contract.project_id) if contract.project_id else None
    accepted = db.get(ProposalAcceptedRevision, contract.accepted_proposal_revision_id) if contract.accepted_proposal_revision_id else None
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    template = db.scalar(select(ContractTemplateSnapshot).where(ContractTemplateSnapshot.contract_id == contract.id).order_by(ContractTemplateSnapshot.captured_at.desc()))
    inputs = db.scalars(select(ContractAdminInput).where(ContractAdminInput.contract_id == contract.id).order_by(ContractAdminInput.input_key)).all()
    evidence = db.scalars(select(ContractAdminEvidence).where(ContractAdminEvidence.contract_id == contract.id).order_by(ContractAdminEvidence.recorded_at.desc())).all()
    tasks = db.scalars(select(WorkflowTask).where(WorkflowTask.context_type == "CONTRACT", WorkflowTask.context_id == contract.id).order_by(WorkflowTask.created_at.desc())).all()
    issues = db.scalars(select(Finding).where(Finding.contract_id == contract.id).order_by(Finding.captured_at.desc())).all()
    notifications = db.scalars(select(NotificationEvent).where(NotificationEvent.contract_id == contract.id).order_by(NotificationEvent.created_at.desc())).all()
    history = db.scalars(select(AuditEvent).where(AuditEvent.entity_type.in_(("Contract", "Project")), AuditEvent.entity_id.in_([contract.id] + ([project.id] if project else []))).order_by(AuditEvent.occurred_at.desc()).limit(50)).all() if include_history else []
    activation = db.scalar(select(ProjectActivation).where(ProjectActivation.contract_id == contract.id))
    return {"id": contract.id, "contract": {"id": contract.id, "name": contract.contract_name, "reference": contract.contract_reference, "stage": contract.stage or contract.status, "status": contract.status, "amount": contract.amount_value, "currency": contract.currency, "duration": contract.duration, "expected_close_date": contract.expected_close_date.isoformat() if contract.expected_close_date else None, "actual_close_date": contract.actual_close_date.isoformat() if contract.actual_close_date else None, "close_date_meaning": contract.close_date_meaning, "last_activity": (contract.last_activity_at or contract.updated_at).isoformat(), "authority_state": contract.authority_state}, "client": {"id": client.id, "reference": client.client_reference, "name": client.display_name} if client else None, "project": {"id": project.id, "reference": project.project_number, "code": project.project_code, "name": project.project_name, "start_date": project.start_date.isoformat() if project and project.start_date else None, "status": project.status} if project else None, "origin": {"proposal_id": proposal.id, "proposal_reference": proposal.opportunity_reference, "title": proposal.title, "accepted_revision_id": accepted.id, "revision_number": accepted.revision_number, "content_hash": accepted.content_hash, "snapshot": accepted.snapshot} if proposal and accepted else None, "current_revision": {"id": revision.id, "revision_number": revision.revision_number, "accepted_proposal_revision_id": revision.accepted_proposal_revision_id, "content_hash": revision.content_hash, "status": revision.status} if revision else None, "template": {"ref": template.master_content_ref, "version": template.version, "version_id": template.document_version_id, "hash": template.content_hash, "master_content_id": template.master_content_id} if template else None, "inputs": [{"key": item.input_key, "value": item.value_json, "entered_by": item.entered_by, "reason": item.reason, "updated_at": item.updated_at.isoformat()} for item in inputs], "evidence": [{"id": item.id, "type": item.evidence_type, "source_reference": item.source_reference, "hash": item.content_hash, "status": item.status, "recorded_by": item.recorded_by} for item in evidence], "readiness": readiness(db, contract), "activation": {"id": activation.id, "project_id": activation.project_id, "project_code": activation.project_code, "start_date": activation.start_date.isoformat(), "activated_by": activation.activated_by, "activated_at": activation.activated_at.isoformat()} if activation else None, "my_work": [{"id": item.id, "title": item.title, "status": item.status, "next_action_code": item.next_action_code, "deep_link": item.deep_link} for item in tasks], "issues": [{"id": item.id, "title": item.title, "status": item.status, "severity": item.severity, "blocking": item.blocking, "deep_link": item.deep_link} for item in issues], "notifications": [{"id": item.id, "event_type": item.event_type, "status": item.status, "subject": item.subject, "created_at": item.created_at.isoformat()} for item in notifications], "history": [{"id": item.id, "event_type": item.event_type, "entity_type": item.entity_type, "occurred_at": item.occurred_at.isoformat(), "actor": item.actor_id, "after": item.after_json} for item in history], "effective_policies": {"stage": runtime_decision_value(db, "CONTRACT_STAGE_POLICY", {"stages": list(CONTRACT_STAGES)}), "authority_review_meaning": runtime_decision_value(db, "CONTRACT_AUTHORITY_REVIEW_MEANING", "OWNER_REVIEW_REQUIRED_NOT_LEGAL_EXECUTION"), "ready_close": runtime_decision_value(db, "CONTRACT_READY_CLOSE_POLICY", "REQUIRED_FIELDS_EVIDENCE_AND_OWNER_AUTHORITY_ACTION"), "close_date": runtime_decision_value(db, "CONTRACT_CLOSE_DATE_MEANING", "EXPECTED_CLOSE_DATE_UNTIL_OWNER_CONFIRMS_ACTUAL_CLOSE"), "reference": effective_contract_reference_policy(db), "required_fields": effective_required_fields(db), "required_evidence": effective_required_evidence(db), "authority": runtime_decision_value(db, "CONTRACT_AUTHORITY_POLICY", "OWNER_ONLY_FOR_AUTHORITY_AND_EXECUTION_STATE"), "manual_new": runtime_decision_value(db, "MANUAL_NEW_CONTRACT_POLICY", "SELECT_ACCEPTED_PROPOSAL_ONLY"), "amount_change": runtime_decision_value(db, "CONTRACT_AMOUNT_CHANGE_AUTHORITY", "OWNER_ONLY_WITH_REASON_AND_NEW_REVISION"), "artifact_strategy": runtime_decision_value(db, "CONTRACT_ARTIFACT_STRATEGY", "CANONICAL_TEMPLATE_RENDER_PLUS_EVIDENCE"), "reopen": runtime_decision_value(db, "CONTRACT_REOPEN_POLICY", "OWNER_DECISION_REQUIRED_WITH_PROSPECTIVE_REVALIDATION"), "activation_trigger": runtime_decision_value(db, "CONTRACT_TO_PROJECT_TRIGGER", "EXPLICIT_OWNER_ACTION_AFTER_CONTRACT_READINESS"), "activation_authority": runtime_decision_value(db, "PROJECT_ACTIVATION_AUTHORITY", "OWNER_ONLY_HUMAN_ACTION"), "code_assignment": runtime_decision_value(db, "PROJECT_CODE_ASSIGNMENT_METHOD", "OWNER_ENTERED_UNIQUE"), "code_format": runtime_decision_value(db, "PROJECT_CODE_FORMAT", {"pattern": "AMEC-YYYY-NNN", "example": "AMEC-2026-001"}), "code_mutability": runtime_decision_value(db, "PROJECT_CODE_MUTABILITY_POLICY", "IMMUTABLE_AFTER_ACTIVATION"), "start_date": runtime_decision_value(db, "PROJECT_START_DATE_SEMANTICS", "ORIGINAL_HUMAN_ACTIVATION_DATE"), "activation_fields": effective_activation_fields(db), "close_vs_activation": runtime_decision_value(db, "CONTRACT_CLOSE_VS_PROJECT_ACTIVATION", "SEPARATE_EVENTS_WITH_LINEAGE")}}
