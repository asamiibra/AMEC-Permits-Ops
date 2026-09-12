"""Canonical Administration Contract workspace behavior."""

from __future__ import annotations

from datetime import date, datetime, timezone
import re
from typing import Any
from uuid import uuid4

from sqlalchemy import or_, select, true
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import (
    AuditEvent, AuthorityCase, ClientAccount, ClientContact, ContactPoint, Contract, ContractAdminEvidence, ContractAdminInput,
    ContractClientInputRequirement, ContractDeliverableCommitment, ContractPaymentTerm,
    ContractReferenceSequence, ContractRevision, ContractTemplateSnapshot, DocumentVersion,
    Finding, LineageEdge, NotificationEvent, Opportunity, Project, ProjectActivation,
    Party, PartyRoleAssignment, ProposalAcceptedRevision, Quotation, QuotationRevision, RegulatoryJourney, ServiceEngagement, WorkflowTask,
    BillingMilestone, BillingPlan, BillingPlanRevision, ContractAdministrativeClosure, HandoverAcceptance,
    HandoverPackage, Invoice, InvoicePaymentAllocation, InvoiceRevision, PaymentReceipt, ServiceScopeClosure,
)
from .master_content import resolve_master_content_purpose
from .proposal_workspace import stable_hash
from .owner_decisions import runtime_decision_value
from .business_v1_controls import advance_payment_gate, commercial_reconciliation, maker_checker_gate


CONTRACT_STAGES = ("DRAFT", "NEEDS_ACTION", "AUTHORITY_REVIEW", "READY", "ACTIVE", "CLOSED")
IMMUTABLE_CONTRACT_REVISION_STATUSES = {"EXECUTED_EVIDENCE_RECORDED", "FINALIZED"}
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
CONTRACT_ORIGIN_POLICIES = {"REQUIRE_ACCEPTED_PROPOSAL", "ALLOW_AUTHORIZED_STANDALONE", "ALLOW_LEGACY_EXCEPTION"}
OPERATIONAL_CONTACT_PURPOSES = frozenset({
    "GENERAL_PROJECT_FOLLOWUP",
    "MISSING_DOCUMENT_REQUEST",
    "CONTRACT_COMMUNICATION",
    "AUTHORITY_FOLLOWUP",
    "HANDOVER_COORDINATION",
    "BILLING_FOLLOWUP",
})
OPERATIONAL_CONTACT_ROLE = "OPERATIONAL_CONTACT"
OPERATIONAL_CONTACT_ORGANIZATION_ROLE = "OPERATIONAL_CONTACT_ORGANIZATION"
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


def contract_administrative_close(
    db: Session,
    *,
    package_id: str,
    actor: str,
    correlation_id: str,
) -> dict[str, Any]:
    """The sole service that may create a Contract administrative closure."""
    package = db.scalar(select(HandoverPackage).where(HandoverPackage.id == package_id).with_for_update())
    if not package:
        raise ValueError("HANDOVER_PACKAGE_NOT_FOUND")
    service = db.scalar(select(ServiceEngagement).where(ServiceEngagement.id == package.service_engagement_id).with_for_update())
    if not service:
        raise ValueError("SERVICE_ENGAGEMENT_REQUIRED")
    services = db.scalars(select(ServiceEngagement).where(ServiceEngagement.contract_id == service.contract_id)).all()
    blockers: list[str] = []
    if any(item.project_id != service.project_id for item in services):
        blockers.append("SERVICE_PROJECT_SCOPE_MISMATCH")
    if any(item.contract_revision_id != service.contract_revision_id for item in services):
        blockers.append("SERVICE_CONTRACT_REVISION_SCOPE_MISMATCH")
    for item in services:
        closure = db.scalar(select(ServiceScopeClosure).where(ServiceScopeClosure.service_engagement_id == item.id))
        acceptance = db.get(HandoverAcceptance, closure.handover_acceptance_id) if closure and closure.handover_acceptance_id else None
        if item.status != "CLOSED" or not closure:
            blockers.append(f"SERVICE_CLOSURE_REQUIRED:{item.id}")
        if not acceptance or acceptance.acceptance_status not in {"ACCEPTED", "ACCEPTED_WITH_REMARKS"}:
            blockers.append(f"HANDOVER_RECEIPT_ACK_REQUIRED:{item.id}")
    exact_revision = db.get(ContractRevision, service.contract_revision_id)
    if not exact_revision:
        blockers.append("EXACT_CONTRACT_REVISION_REQUIRED")
    elif not contract_revision_is_accepted(exact_revision):
        blockers.append("CONTRACT_ACCEPTANCE_REQUIRED")
    if not db.scalar(select(ContractAdminEvidence).where(ContractAdminEvidence.contract_id == service.contract_id, ContractAdminEvidence.contract_revision_id == service.contract_revision_id, ContractAdminEvidence.source_role == "EXECUTED_CONTRACT", ContractAdminEvidence.status.in_({"RECORDED", "VERIFIED", "APPROVED"}))):
        blockers.append("EXECUTED_CONTRACT_EVIDENCE_REQUIRED")
    if blockers:
        raise ValueError("CONTRACT_ADMIN_CLOSE_BLOCKED:" + ",".join(blockers))
    contract = db.scalar(select(Contract).where(Contract.id == service.contract_id).with_for_update())
    if not contract:
        raise ValueError("CONTRACT_NOT_FOUND")
    existing = db.scalar(select(ContractAdministrativeClosure).where(ContractAdministrativeClosure.contract_id == service.contract_id))
    if existing:
        return {"contract_administrative_closure": existing, "idempotent": True, "financial_settlement": "SEPARATE", "project_archive": "SEPARATE"}
    closure = ContractAdministrativeClosure(
        contract_id=service.contract_id,
        project_id=service.project_id,
        contract_revision_id=service.contract_revision_id,
        service_closure_ids_json=[item.id for item in services],
        closed_by=actor,
        evidence_json={
            "financial_settlement_separate": True,
            "project_archive_separate": True,
            "exact_service_closure_predicate": True,
            "handover_delivery_receipt_acknowledgment": True,
            "executed_contract_evidence": True,
        },
    )
    db.add(closure)
    before_contract = {"stage": contract.stage, "status": contract.status}
    contract.stage = "CLOSED"
    contract.status = "CLOSED"
    contract.last_activity_at = now()
    audit(db, correlation_id=correlation_id, event_type="CONTRACT_ADMINISTRATIVE_CLOSURE_RECORDED", entity_type="ContractAdministrativeClosure", entity_id=closure.id, actor_id=actor, after={"contract_id": service.contract_id, "contract_revision_id": service.contract_revision_id, "service_closure_ids": [item.id for item in services], "status": "CLOSED"}, metadata={"canonical_close_service": True, "financial_settlement_separate": True, "project_archive_separate": True})
    audit(db, correlation_id=correlation_id, event_type="ADMIN_CONTRACT_CLOSED_BY_CANONICAL_SERVICE", entity_type="Contract", entity_id=contract.id, actor_id=actor, before=before_contract, after={"stage": contract.stage, "status": contract.status, "closure_id": closure.id}, metadata={"canonical_close_service": True})
    db.commit()
    db.refresh(closure)
    return {"contract_administrative_closure": closure, "idempotent": False, "financial_settlement": "SEPARATE", "project_archive": "SEPARATE"}


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


def effective_contract_origin_policy(db: Session) -> str:
    configured = str(runtime_decision_value(db, "CONTRACT_STANDALONE_CONTRACT_POLICY", "REQUIRE_ACCEPTED_PROPOSAL")).upper()
    return configured if configured in CONTRACT_ORIGIN_POLICIES else "REQUIRE_ACCEPTED_PROPOSAL"


def contract_revision_is_finalized(revision: ContractRevision | None) -> bool:
    """Return whether the revision is immutable, not merely authority-reviewed."""
    return bool(revision and str(revision.status or "").upper() in IMMUTABLE_CONTRACT_REVISION_STATUSES)


def contract_revision_is_accepted(revision: ContractRevision | None) -> bool:
    """Require an explicit acceptance record for the exact immutable revision."""
    if not revision or str(revision.status or "").upper() not in IMMUTABLE_CONTRACT_REVISION_STATUSES:
        return False
    acceptance = (revision.admin_input_snapshot or {}).get("acceptance") or {}
    return bool(
        acceptance.get("revision_id") == revision.id
        and acceptance.get("accepted_by")
        and acceptance.get("accepted_at")
    )


def contract_revision_is_authority_reviewed(revision: ContractRevision | None) -> bool:
    return bool(revision and str(revision.status or "").upper() == "APPROVED")


def _document_version_projection(db: Session, document_version_id: str | None) -> dict[str, Any] | None:
    if not document_version_id:
        return None
    version = db.get(DocumentVersion, document_version_id)
    if not version:
        return {"id": document_version_id, "status": "MISSING"}
    return {"id": version.id, "document_id": version.document_id, "version_number": version.version_number, "filename": version.source_filename, "source_reference": version.source_path_or_reference, "sha256": version.sha256, "approval_state": str(version.approval_state.value if hasattr(version.approval_state, "value") else version.approval_state)}


def _revision_terms(db: Session, revision_id: str | None) -> tuple[list[ContractPaymentTerm], list[ContractDeliverableCommitment], list[ContractClientInputRequirement]]:
    if not revision_id:
        return [], [], []
    return (
        db.scalars(select(ContractPaymentTerm).where(ContractPaymentTerm.contract_revision_id == revision_id).order_by(ContractPaymentTerm.sequence)).all(),
        db.scalars(select(ContractDeliverableCommitment).where(ContractDeliverableCommitment.contract_revision_id == revision_id).order_by(ContractDeliverableCommitment.sequence)).all(),
        db.scalars(select(ContractClientInputRequirement).where(ContractClientInputRequirement.contract_revision_id == revision_id).order_by(ContractClientInputRequirement.sequence)).all(),
    )


def contract_billing_context(db: Session, contract: Contract, revision_id: str | None = None) -> dict[str, Any]:
    """Return a read-only Contract-to-Billing setup context.

    This function has no Invoice, Payment, BillingMilestone, or settlement
    writes.  It is intentionally a dependency/readiness seam for a later
    billing workstream.
    """
    revision = db.get(ContractRevision, revision_id) if revision_id else (db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None)
    if revision and revision.contract_id != contract.id:
        revision = None
    payment_terms, deliverables, client_inputs = _revision_terms(db, revision.id if revision else None)
    activation = db.scalar(select(ProjectActivation).where(ProjectActivation.contract_id == contract.id))
    evidence = db.scalars(select(ContractAdminEvidence).where(ContractAdminEvidence.contract_id == contract.id, ContractAdminEvidence.contract_revision_id == (revision.id if revision else None))).all() if revision else []
    lpo_evidence = [item for item in evidence if item.source_role in {"LPO", "CLIENT_DOCUMENT", "EXECUTED_CONTRACT"}]
    blockers: list[dict[str, str]] = []
    if not revision:
        blockers.append({"code": "CONTRACT_REVISION_REQUIRED", "label": "Current Contract revision"})
    elif not contract_revision_is_finalized(revision):
        blockers.append({"code": "CONTRACT_AUTHORITY_REQUIRED", "label": "Contract authority / finalized revision"})
    if not contract.client_account_id:
        blockers.append({"code": "CLIENT_CONTEXT_REQUIRED", "label": "Canonical Client"})
    if not contract.amount_value or not contract.currency:
        blockers.append({"code": "CONTRACT_AMOUNT_CURRENCY_REQUIRED", "label": "Contract Amount and Currency"})
    project_policy = str(runtime_decision_value(db, "BILLING_PROJECT_REQUIREMENT_POLICY", "REQUIRED")).upper()
    if not activation and project_policy in {"REQUIRED", "PROJECT_REQUIRED"}:
        blockers.append({"code": "PROJECT_ACTIVATION_HUMAN_ACTION_REQUIRED", "label": "Explicit Project Activation"})
    if not payment_terms or any(str(item.status).upper() not in {"VERIFIED", "HUMAN_VERIFIED", "CONFIRMED"} for item in payment_terms):
        blockers.append({"code": "PAYMENT_TERMS_REVIEW_REQUIRED", "label": "Human-verified Contract payment terms"})
    if not contract.payment_condition_text:
        blockers.append({"code": "PAYMENT_CONDITION_REVIEW_REQUIRED", "label": "Contract Payment Condition"})
    if contract.valuation_status not in {"UNKNOWN_NON_AUTHORITATIVE", "NOT_PROVIDED", "OWNER_CONFIRMED"} and contract.valuation_amount is None:
        blockers.append({"code": "VALUATION_DATA_INCONSISTENT", "label": "Valuation basis"})
    status = "READY_FOR_BILLING_SETUP" if not blockers else "NEEDS_PAYMENT_TERM_REVIEW" if any(item["code"].startswith("PAYMENT_") for item in blockers) else "NEEDS_CONTRACT_AUTHORITY" if any(item["code"] == "CONTRACT_AUTHORITY_REQUIRED" for item in blockers) else "NEEDS_PROJECT_ACTIVATION" if any(item["code"] == "PROJECT_ACTIVATION_HUMAN_ACTION_REQUIRED" for item in blockers) else "NOT_READY"
    return {
        "contract_id": contract.id,
        "contract_reference": contract.contract_reference,
        "revision": {"id": revision.id, "revision_number": revision.revision_number, "status": revision.status, "content_hash": revision.content_hash} if revision else None,
        "revision_selection": {"requested_revision_id": revision_id, "latest_lookup_used": revision_id is None, "exact_revision_pinned": bool(revision)},
        "status": status,
        "blockers": blockers,
        "client_account_id": contract.client_account_id,
        "project_id": activation.project_id if activation else None,
        "project_code": activation.project_code if activation else None,
        "project_activation_status": "ACTIVE" if activation else "NOT_ACTIVATED",
        "project_required_policy": project_policy,
        "contract_project_context_snapshot": {"project_opportunity_ref": contract.project_opportunity_ref, "project_description": contract.contract_name, "location_or_property_context": (revision.source_snapshot or {}).get("location_or_property_context") if revision else None, "source": "CONTRACT_OR_ACCEPTED_PROPOSAL_SNAPSHOT", "canonical_project_created": bool(activation)},
        "proposal_opportunity_ref": contract.project_opportunity_ref,
        "project_start_date": activation.start_date.isoformat() if activation else None,
        "contract_amount": {"value": contract.amount_value, "currency": contract.currency},
        "valuation": {"value": str(contract.valuation_amount) if contract.valuation_amount is not None else None, "currency": contract.valuation_currency, "basis": contract.valuation_basis, "status": contract.valuation_status},
        "payment_condition": contract.payment_condition_text,
        "duration": contract.duration,
        "contracted_scope": contract.contracted_scope_text,
        "payment_terms": [{"id": item.id, "sequence": item.sequence, "label": item.label, "term_text": item.term_text, "basis_type": item.basis_type, "percentage": str(item.percentage) if item.percentage is not None else None, "fixed_amount": str(item.fixed_amount) if item.fixed_amount is not None else None, "currency": item.currency, "trigger_type": item.trigger_type, "trigger_description": item.trigger_description, "due_days": item.due_days, "source_clause": item.source_clause, "source_document": _document_version_projection(db, item.source_document_version_id), "status": item.status, "human_verified_by": item.human_verified_by, "human_verified_at": item.human_verified_at.isoformat() if item.human_verified_at else None} for item in payment_terms],
        "deliverables": [{"id": item.id, "sequence": item.sequence, "commitment_ref": item.commitment_ref, "name": item.name, "description": item.description, "due_trigger_description": item.due_trigger_description, "status": item.status, "source_document": _document_version_projection(db, item.source_document_version_id), "human_verified_by": item.human_verified_by} for item in deliverables],
        "client_inputs": [{"id": item.id, "sequence": item.sequence, "input_code": item.input_code, "title": item.title, "description": item.description, "required": item.required, "status": item.status, "source_type": item.source_type, "source_document": _document_version_projection(db, item.source_document_version_id), "human_verified_by": item.human_verified_by} for item in client_inputs],
        "lpo_or_client_evidence": [{"id": item.id, "type": item.evidence_type, "source_role": item.source_role, "document": _document_version_projection(db, item.document_version_id), "source_reference": item.source_reference, "status": item.status} for item in lpo_evidence],
        "invoice_created": False,
        "billing_milestone_created": False,
        "invoice_implementation": "BILLING_INVOICE_IMPLEMENTATION_DEFERRED_TO_NEXT_WORKSTREAM",
        "external_agreement_consumption": "AMEC_PROFESSIONAL_SERVICES_CONTRACT_ONLY",
    }


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


def capture_current_contract_template(
    db: Session,
    *,
    contract_id: str,
    actor: str,
    correlation_id: str,
    reason: str,
    idempotency_key: str | None = None,
) -> dict[str, Any]:
    """Capture the exact current Dashboard Contract Template once.

    This is deliberately pre-finalization and contract-scoped.  The locked
    Contract row serializes concurrent callers; an existing snapshot is an
    idempotent committed result and is never replaced.
    """
    contract = db.scalar(select(Contract).where(Contract.id == contract_id).with_for_update())
    if not contract:
        raise ValueError("CONTRACT_NOT_FOUND")
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    if not revision:
        raise ValueError("CONTRACT_REVISION_REQUIRED")
    if contract_revision_is_finalized(revision):
        raise ValueError("FINALIZED_CONTRACT_SNAPSHOT_BACKFILL_FORBIDDEN")

    existing = db.scalar(
        select(ContractTemplateSnapshot)
        .where(ContractTemplateSnapshot.contract_id == contract.id)
        .order_by(ContractTemplateSnapshot.captured_at.desc())
    )
    if existing:
        return {
            "decision": "ALREADY_CAPTURED",
            "captured": False,
            "snapshot": {
                "id": existing.id,
                "master_content_id": existing.master_content_id,
                "reference": existing.master_content_ref,
                "document_version_id": existing.document_version_id,
                "version": existing.version,
                "hash": existing.content_hash,
                "contract_revision_id": existing.contract_revision_id,
            },
        }

    resolved = resolve_master_content_purpose(db, module="ADMIN", usage_type="CONTRACT_TEMPLATE")
    if resolved["status"] == "AMBIGUOUS":
        raise ValueError("CONTRACT_TEMPLATE_CONFIGURATION_CONFLICT")
    if resolved["status"] != "RESOLVED":
        raise ValueError("CONTRACT_TEMPLATE_NOT_RESOLVED")
    item = resolved["item"]
    snapshot = ContractTemplateSnapshot(
        contract_id=contract.id,
        contract_revision_id=revision.id,
        master_content_id=item["id"],
        master_content_ref=item["ref"],
        document_version_id=item["version_id"],
        version=str(item["version"]),
        content_hash=item["hash"],
        captured_by=actor,
    )
    db.add(snapshot)
    db.flush()
    audit(
        db,
        correlation_id=correlation_id,
        event_type="ADMIN_CONTRACT_TEMPLATE_SNAPSHOT_CAPTURED",
        entity_type="Contract",
        entity_id=contract.id,
        actor_id=actor,
        after={
            "contract_revision_id": revision.id,
            "master_content_id": snapshot.master_content_id,
            "master_content_ref": snapshot.master_content_ref,
            "document_version_id": snapshot.document_version_id,
            "version": snapshot.version,
            "content_hash": snapshot.content_hash,
        },
        metadata={"idempotency_key": idempotency_key, "pre_finalization": True, "resolver": "ADMIN/CONTRACT_TEMPLATE", "reason": reason},
    )
    db.commit()
    return {
        "decision": "CAPTURED",
        "captured": True,
        "snapshot": {
            "id": snapshot.id,
            "master_content_id": snapshot.master_content_id,
            "reference": snapshot.master_content_ref,
            "document_version_id": snapshot.document_version_id,
            "version": snapshot.version,
            "hash": snapshot.content_hash,
            "contract_revision_id": snapshot.contract_revision_id,
        },
    }


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
    contract = Contract(client_account_id=proposal.client_account_id, quotation_id=quotation.id, contract_reference=reference, status="DRAFT", stage="DRAFT", contract_name=f"{proposal.title} Contract", proposal_id=proposal.id, accepted_proposal_revision_id=accepted.id, project_id=proposal.project_id, project_opportunity_ref=accepted.snapshot.get("project_reference") or proposal.canonical_project_reference or proposal.provisional_reference, amount_value=fields.get("price"), currency=fields.get("currency"), duration=fields.get("duration") or fields.get("period"), payment_condition_text=fields.get("payment_condition") or fields.get("payment_terms"), contracted_scope_text=fields.get("scope") or fields.get("scope_of_work"), valuation_amount=fields.get("valuation_amount"), valuation_currency=fields.get("valuation_currency"), valuation_basis=fields.get("valuation_basis"), valuation_status=fields.get("valuation_status") or "UNKNOWN_NON_AUTHORITATIVE", field_provenance={key: {"source": "PROPOSAL_ACCEPTED_REVISION", "accepted_revision_id": accepted.id, "content_hash": accepted.content_hash} for key in ("contract_name", "project_opportunity_ref", "amount_value", "currency", "duration")}, last_activity_at=now())
    db.add(contract)
    db.flush()
    revision = ContractRevision(contract_id=contract.id, revision_number=1, controlling_quotation_revision_id=quotation_revision.id, accepted_proposal_revision_id=accepted.id, source_snapshot=accepted.snapshot, contract_name=contract.contract_name, stage=contract.stage, amount_value=contract.amount_value, currency=contract.currency, duration=contract.duration, payment_condition_text=contract.payment_condition_text, contracted_scope_text=contract.contracted_scope_text, valuation_amount=contract.valuation_amount, valuation_currency=contract.valuation_currency, valuation_basis=contract.valuation_basis, valuation_status=contract.valuation_status, status="DRAFT", content_hash=stable_hash({"accepted_revision_id": accepted.id, "fields": fields}), commercial_terms_snapshot={**fields, "proposal_accepted_revision_id": accepted.id, "proposal_content_hash": accepted.content_hash}, admin_input_snapshot={"maker_checker": {"preparer": actor, "prepared_at": now().isoformat(), "source": "AUTHENTICATED_CONTRACT_CREATOR"}})
    db.add(revision)
    db.flush()
    contract.current_revision_id = revision.id
    template = _snapshot_template(db, contract, revision, actor)
    proposal.status = "CONTRACT_HANDOVER"
    _ensure_task_notification(db, contract, correlation_id, actor)
    audit(db, correlation_id=correlation_id, event_type="ADMIN_CONTRACT_CREATED_FROM_ACCEPTED_PROPOSAL", entity_type="Contract", entity_id=contract.id, actor_id=actor, after={"contract_reference": contract.contract_reference, "accepted_proposal_revision_id": accepted.id, "accepted_revision_hash": accepted.content_hash, "template_snapshot": template, "machine_legal_contract": False})
    return contract


def readiness(db: Session, contract: Contract, *, enforce_maker_checker: bool = True) -> dict[str, Any]:
    blockers: list[dict[str, str]] = []
    warnings: list[dict[str, str]] = []
    required_fields = set(effective_required_fields(db))
    origin_policy = effective_contract_origin_policy(db)
    if not contract.accepted_proposal_revision_id and origin_policy == "REQUIRE_ACCEPTED_PROPOSAL":
        blockers.append({"code": "CONTRACT_ORIGIN_RECONCILIATION_REQUIRED", "label": "Proposal origin needs reconciliation before this Contract can be accepted."})
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
    accepted = db.get(ProposalAcceptedRevision, contract.accepted_proposal_revision_id) if contract.accepted_proposal_revision_id else None
    proposal_fields = dict((accepted.snapshot or {}).get("fields") or {}) if accepted else {}
    current_revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    contract_fields = {
        "amount": contract.amount_value,
        "currency": contract.currency,
        "duration": contract.duration,
        "payment_terms": contract.payment_condition_text,
        "scope": contract.contracted_scope_text,
    }
    all_order_evidence = [item for item in evidence if item.source_role in {"LPO", "PO"}]
    order_evidence = []
    invalid_order_evidence = []
    superseded_order_evidence = []
    cross_contract_order_evidence = []
    for item in all_order_evidence:
        source_version = db.get(DocumentVersion, item.document_version_id) if item.document_version_id else None
        source_metadata = source_version.metadata_json if source_version and isinstance(source_version.metadata_json, dict) else {}
        evidence_metadata = item.metadata_json if isinstance(item.metadata_json, dict) else {}
        if source_metadata.get("contract_id") not in {None, contract.id} or evidence_metadata.get("contract_id") not in {None, contract.id}:
            cross_contract_order_evidence.append(item)
        if (
            source_version
            and source_version.document.current_version_id == source_version.id
            and not source_version.superseded_by
            and source_metadata.get("contract_id") in {None, contract.id}
            and evidence_metadata.get("contract_id") in {None, contract.id}
        ):
            order_evidence.append(item)
        else:
            invalid_order_evidence.append(item)
            if source_version and (source_version.superseded_by or getattr(source_version.approval_state, "value", str(source_version.approval_state)).upper() == "SUPERSEDED"):
                superseded_order_evidence.append(item)
    structured_orders = [item.metadata_json.get("commercial_terms") for item in order_evidence if isinstance(item.metadata_json, dict) and isinstance(item.metadata_json.get("commercial_terms"), dict)]
    lpo_policy = runtime_decision_value(db, "CONTRACT_LPO_REQUIREDNESS_POLICY", "OWNER_DEFINITION_REQUIRED")
    order_applicable = lpo_policy == "REQUIRED" or bool(all_order_evidence)
    order_reason = None if order_applicable else f"CONTRACT_LPO_REQUIREDNESS_POLICY={lpo_policy}; no PO/LPO comparison is applicable to this Contract."
    order_source_state = None
    if cross_contract_order_evidence:
        order_source_state = "BLOCKED_CROSS_CONTRACT_SOURCE"
    elif any((item.metadata_json or {}).get("exception_requested") and not (item.metadata_json or {}).get("exception_authorized") for item in all_order_evidence):
        order_source_state = "BLOCKED_UNAUTHORIZED_EXCEPTION"
    elif any((item.metadata_json or {}).get("superseded") is True for item in all_order_evidence) or superseded_order_evidence:
        order_source_state = "BLOCKED_SUPERSEDED_SOURCE"
    elif invalid_order_evidence or (all_order_evidence and len(structured_orders) != len(order_evidence)):
        order_source_state = "BLOCKED_UNSTRUCTURED_SOURCE"
    commercial_control = commercial_reconciliation(
        proposal_fields,
        contract_fields,
        structured_orders[0] if len(structured_orders) == 1 else None,
        order_applicable=order_applicable,
        not_applicable_reason=order_reason,
        order_source_count=len(all_order_evidence),
        order_source_state=order_source_state,
    )
    if commercial_control["status"] != "PASS":
        blockers.append({"code": "CONTRACT_COMMERCIAL_RECONCILIATION_MISMATCH", "label": "Exact accepted Proposal / PO / LPO commercial reconciliation"})
    if "COMMERCIAL_OR_AWARD_EVIDENCE" in required_evidence and not any(item.evidence_type in {"COMMERCIAL", "AWARD", "COMMERCIAL_OR_AWARD_EVIDENCE"} for item in evidence):
        blockers.append({"code": "COMMERCIAL_OR_AWARD_EVIDENCE_REQUIRED", "label": "Commercial or award evidence"})
    activation = db.scalar(select(ProjectActivation).where(ProjectActivation.contract_id == contract.id))
    activation_blockers = [] if activation else [{"code": "PROJECT_ACTIVATION_HUMAN_ACTION_REQUIRED", "label": "Explicit Project Activation"}]
    lpo_received = any(item.source_role == "LPO" and item.status in {"RECEIVED", "VERIFIED", "HUMAN_VERIFIED", "APPROVED"} for item in evidence)
    if lpo_policy == "REQUIRED" and not lpo_received:
        blockers.append({"code": "CONTRACT_LPO_REQUIRED", "label": "LPO DocumentVersion"})
    advance_input = db.scalar(select(ContractAdminInput).where(ContractAdminInput.contract_id == contract.id, ContractAdminInput.input_key == "ADVANCE_PAYMENT_ACTIVATION_GATE"))
    advance_control = advance_payment_gate(advance_input.value_json if advance_input else None, [{"source_role": item.source_role, "status": item.status, "metadata": item.metadata_json} for item in evidence])
    if advance_control["status"] == "BLOCKED":
        activation_blockers.extend({"code": code, "label": "Objective advance-payment evidence"} for code in advance_control["blockers"])
    maker_checker = maker_checker_gate((current_revision.admin_input_snapshot if current_revision else None), enforce=enforce_maker_checker)
    if enforce_maker_checker and maker_checker["status"] != "PASS":
        blockers.append({"code": "CONTRACT_MAKER_CHECKER_REQUIRED", "label": "Recorded independent Contract maker/checker and Proposal reconciliation"})
    return {"ready": not blockers, "blockers": blockers, "warnings": warnings, "activation_ready": bool(activation) and not any(item["code"] == "OBJECTIVE_ADVANCE_PAYMENT_EVIDENCE_REQUIRED" for item in activation_blockers), "activation_blockers": activation_blockers, "authority_state": contract.authority_state, "template_snapshot": template, "effective_required_fields": sorted(required_fields), "effective_required_evidence": sorted(required_evidence), "authority_review_meaning": runtime_decision_value(db, "CONTRACT_AUTHORITY_REVIEW_MEANING", "OWNER_REVIEW_REQUIRED_NOT_LEGAL_EXECUTION"), "ready_close_policy": runtime_decision_value(db, "CONTRACT_READY_CLOSE_POLICY", "REQUIRED_FIELDS_EVIDENCE_AND_OWNER_AUTHORITY_ACTION"), "lpo_requiredness_policy": lpo_policy, "lpo_received": lpo_received, "origin_policy": origin_policy, "origin_resolved": bool(contract.accepted_proposal_revision_id), "accepted": contract_revision_is_accepted(current_revision), "authority_reviewed": contract_revision_is_authority_reviewed(current_revision), "source10_controls": {"proposal_lpo_reconciliation": commercial_control, "advance_payment_gate": advance_control, "maker_checker": maker_checker}}


def _contract_evidence(db: Session, contract_id: str, revision_id: str | None = None) -> list[ContractAdminEvidence]:
    query = select(ContractAdminEvidence).where(ContractAdminEvidence.contract_id == contract_id)
    if revision_id:
        query = query.where(ContractAdminEvidence.contract_revision_id == revision_id)
    return db.scalars(query.order_by(ContractAdminEvidence.recorded_at)).all()


def _contact_is_current(contact: ContactPoint, evaluated_on: date) -> tuple[bool, str | None]:
    if not contact.verified or str(contact.status).upper() not in {"VERIFIED", "ACTIVE", "CURRENT"}:
        return False, "PURPOSE_CONTACT_UNVERIFIED_OR_INACTIVE"
    if contact.effective_from and contact.effective_from > evaluated_on:
        return False, "PURPOSE_CONTACT_NOT_YET_EFFECTIVE"
    if contact.effective_until and contact.effective_until < evaluated_on:
        return False, "PURPOSE_CONTACT_EXPIRED"
    return True, None


def _party_summary(db: Session, party_id: str | None) -> dict[str, Any] | None:
    party = db.get(Party, party_id) if party_id else None
    if not party:
        return None
    return {"id": party.id, "name": party.name_en or party.name_ar, "party_type": str(getattr(party.party_type, "value", party.party_type))}


def resolve_operational_contact(
    db: Session,
    *,
    project: Project | None,
    contract: Contract,
    purpose: str,
) -> dict[str, Any]:
    """Resolve an exact, current, purpose-specific contact without fallback.

    ContactPoint and PartyRoleAssignment remain the canonical party/contact
    records.  The append-only ContractAdminEvidence binding supplies the
    Contract boundary and preserves routing history without adding a contact
    subsystem or allowing a generic ClientContact substitution.
    """
    normalized_purpose = str(purpose or "").strip().upper()
    project_id = project.id if project else contract.project_id
    base: dict[str, Any] = {
        "status": "CONTACT_RESOLUTION_REQUIRED",
        "contract_id": contract.id,
        "project_id": project_id,
        "purpose": normalized_purpose,
        "generic_fallback_used": False,
        "generic_fallback_policy": "DISALLOWED",
        "missing": [],
        "next_action": "Assign a verified purpose-specific operational contact and organization.",
    }
    if normalized_purpose not in OPERATIONAL_CONTACT_PURPOSES:
        return {**base, "blocker_code": "OPERATIONAL_CONTACT_PURPOSE_UNSUPPORTED", "missing": ["SUPPORTED_CONTACT_PURPOSE"]}
    if not project_id:
        return {**base, "blocker_code": "PROJECT_CONTEXT_REQUIRED", "missing": ["PROJECT"]}

    revision_id = contract.current_revision_id
    bindings = [
        item for item in _contract_evidence(db, contract.id, revision_id)
        if item.source_role == "OPERATIONAL_CONTACT_ROUTING"
        and str((item.metadata_json or {}).get("purpose") or "").upper() == normalized_purpose
    ]
    binding = max(bindings, key=lambda item: (int((item.metadata_json or {}).get("binding_sequence") or 0), item.recorded_at, item.id)) if bindings else None
    if not binding:
        return {**base, "blocker_code": "PURPOSE_SPECIFIC_CONTACT_MISSING", "missing": ["OPERATIONAL_CONTACT_ROUTING"]}

    metadata = binding.metadata_json or {}
    contact_point_id = str(metadata.get("contact_point_id") or "")
    contact = db.scalar(select(ContactPoint).where(ContactPoint.id == contact_point_id, ContactPoint.project_id == project_id)) if contact_point_id else None
    if not contact:
        return {**base, "blocker_code": "CONTACT_SCOPE_MISMATCH", "missing": ["PROJECT_SCOPED_CONTACT_POINT"]}
    if str(contact.purpose).upper() != normalized_purpose:
        return {**base, "blocker_code": "CONTACT_PURPOSE_MISMATCH", "contact_point_id": contact.id, "missing": [normalized_purpose]}
    current, current_error = _contact_is_current(contact, now().date())
    if not current:
        return {**base, "blocker_code": current_error, "contact_point_id": contact.id, "missing": ["CURRENT_VERIFIED_CONTACT_POINT"]}

    operational_party_id = str(metadata.get("operational_contact_party_id") or contact.party_id or "")
    organization_party_id = str(metadata.get("organization_party_id") or "")
    practical_role = str(metadata.get("practical_role") or "").strip()
    assignment_rows = db.scalars(select(PartyRoleAssignment).where(
        PartyRoleAssignment.project_id == project_id,
        PartyRoleAssignment.authority_case_id == contact.authority_case_id,
        PartyRoleAssignment.status == "ACTIVE",
    )).all()
    active_on = now().date()
    role_rows = [
        item for item in assignment_rows
        if (not item.valid_from or item.valid_from <= active_on)
        and (not item.valid_until or item.valid_until >= active_on)
    ]
    contact_role = next((item for item in role_rows if item.role_code == OPERATIONAL_CONTACT_ROLE and item.party_id == operational_party_id), None)
    organization_role = next((item for item in role_rows if item.role_code == OPERATIONAL_CONTACT_ORGANIZATION_ROLE and item.party_id == organization_party_id), None)
    missing: list[str] = []
    if not operational_party_id or not contact_role:
        missing.append("OPERATIONAL_CONTACT_ROLE")
    if not organization_party_id or not organization_role:
        missing.append("OPERATIONAL_CONTACT_ORGANIZATION")
    client = db.get(ClientAccount, contract.client_account_id) if contract.client_account_id else None
    if client and client.canonical_party_id and organization_party_id != client.canonical_party_id:
        missing.append("CLIENT_ORGANIZATION_MATCH")
    if not practical_role:
        missing.append("PRACTICAL_ROLE")
    if missing:
        return {**base, "blocker_code": "OPERATIONAL_CONTACT_RELATIONSHIP_INCOMPLETE", "contact_point_id": contact.id, "missing": sorted(set(missing)), "operational_contact_party_id": operational_party_id or None, "organization_party_id": organization_party_id or None, "practical_role": practical_role or None}

    operational_party = _party_summary(db, operational_party_id)
    organization_party = _party_summary(db, organization_party_id)
    return {
        **base,
        "status": "RESOLVED",
        "blocker_code": None,
        "contact_point_id": contact.id,
        "operational_contact_party_id": operational_party_id,
        "operational_contact": operational_party,
        "organization_party_id": organization_party_id,
        "organization": organization_party,
        "practical_role": practical_role,
        "channel": contact.channel,
        "value_present": bool(contact.value),
        "verified": contact.verified,
        "contact_status": contact.status,
        "effective_from": contact.effective_from.isoformat() if contact.effective_from else None,
        "effective_until": contact.effective_until.isoformat() if contact.effective_until else None,
        "binding_evidence_id": binding.id,
        "resolved_at": now().isoformat(),
        "next_action": "Human review of the purpose-specific contact before communication.",
    }


def operational_contact_routing_projection(db: Session, contract: Contract, project: Project | None = None) -> dict[str, Any]:
    routes = {purpose: resolve_operational_contact(db, project=project, contract=contract, purpose=purpose) for purpose in sorted(OPERATIONAL_CONTACT_PURPOSES)}
    return {
        "purposes": routes,
        "generic_fallback_policy": "DISALLOWED",
        "unresolved_purposes": [purpose for purpose, result in routes.items() if result["status"] != "RESOLVED"],
        "source_of_record": "PROJECT_PARTY_ROLE_AND_CONTACT_POINT_BOUND_TO_CONTRACT_EVIDENCE",
        "external_send": "HUMAN_CONTROLLED",
    }


def contract_start_prerequisites(db: Session, contract: Contract) -> dict[str, Any]:
    """Evaluate start facts without changing any canonical state.

    Payment facts are read from Billing's Invoice/Payment/Allocation records;
    this service intentionally does not create a second payment state machine.
    """
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    evidence = _contract_evidence(db, contract.id, revision.id if revision else None)
    executed = next((item for item in evidence if item.source_role == "EXECUTED_CONTRACT"), None)
    client_copy = next((item for item in evidence if item.source_role == "CLIENT_COPY_DISTRIBUTION"), None)
    operations_handoff = next((item for item in evidence if item.source_role == "OPERATIONS_HANDOFF"), None)
    advance_input = db.scalar(select(ContractAdminInput).where(ContractAdminInput.contract_id == contract.id, ContractAdminInput.input_key == "ADVANCE_PAYMENT_ACTIVATION_GATE"))
    configured_advance = bool((advance_input.value_json or {}).get("required")) if advance_input else False
    terms = db.scalars(select(ContractPaymentTerm).where(ContractPaymentTerm.contract_revision_id == (revision.id if revision else ""))).all() if revision else []
    advance_terms = [item for item in terms if str(item.trigger_type or "").upper() in {"ADVANCE", "ADVANCE_PAYMENT", "PRE_ACTIVATION"} or bool((item.metadata_json or {}).get("advance_before_start"))]
    advance_required = configured_advance or bool(advance_terms)
    invoices = db.scalars(select(Invoice).where(Invoice.contract_id == contract.id)).all()
    invoice_ids = [item.id for item in invoices]
    invoice_revisions = db.scalars(select(InvoiceRevision).where(InvoiceRevision.invoice_id.in_(invoice_ids))) .all() if invoice_ids else []
    advance_milestones = db.scalars(select(BillingMilestone).where(BillingMilestone.source_contract_payment_term_id.in_([item.id for item in advance_terms]))) .all() if advance_terms else []
    advance_milestone_ids = {item.id for item in advance_milestones}
    matching_revisions = [item for item in invoice_revisions if item.controlling_contract_revision_id == (revision.id if revision else None) and (item.controlling_milestone_id in advance_milestone_ids or not advance_milestone_ids)]
    issued_invoice_ids = {item.invoice_id for item in matching_revisions if item.status in {"ISSUED", "ACCEPTED_INTERNAL"}}
    payments = db.scalars(select(PaymentReceipt).where(PaymentReceipt.contract_id == contract.id)).all()
    verified_payments = [item for item in payments if str(item.verification_status).upper() == "VERIFIED"]
    allocations = db.scalars(select(InvoicePaymentAllocation).where(InvoicePaymentAllocation.invoice_id.in_(list(issued_invoice_ids)), InvoicePaymentAllocation.status == "ALLOCATED")) .all() if issued_invoice_ids else []
    allocated_payment_ids = {item.payment_receipt_id for item in allocations}
    advance_satisfied = not advance_required or bool(verified_payments and allocated_payment_ids.intersection({item.id for item in verified_payments}))
    def fact(name: str, state: str, required: bool, detail: Any = None) -> dict[str, Any]:
        return {"fact": name, "state": state, "required": required, "detail": detail}
    facts = [
        fact("CONTRACT_EXECUTED", "RECORDED" if executed else "MISSING", True, executed.id if executed else None),
        fact("CLIENT_COPY_DISTRIBUTED", "RECORDED" if client_copy else "MISSING", True, client_copy.id if client_copy else None),
        fact("OPERATIONS_HANDOFF", "RECORDED" if operations_handoff else "MISSING", True, operations_handoff.id if operations_handoff else None),
        fact("ADVANCE_REQUIREMENT", "REQUIRED" if advance_required else "NOT_APPLICABLE", advance_required, [item.id for item in advance_terms]),
        fact("ADVANCE_PAYMENT_RECEIVED", "RECORDED" if payments else "MISSING" if advance_required else "NOT_APPLICABLE", advance_required, [item.id for item in payments]),
        fact("ADVANCE_PAYMENT_VERIFIED", "RECORDED" if verified_payments else "MISSING" if advance_required else "NOT_APPLICABLE", advance_required, [item.id for item in verified_payments]),
        fact("ADVANCE_PAYMENT_ALLOCATED", "RECORDED" if allocations else "MISSING" if advance_required else "NOT_APPLICABLE", advance_required, [item.id for item in allocations]),
        fact("REQUIRED_ADVANCE_SATISFIED", "SATISFIED" if advance_satisfied else "UNSATISFIED", advance_required),
        fact("PROJECT_ACTIVATION", "RECORDED" if db.scalar(select(ProjectActivation).where(ProjectActivation.contract_id == contract.id)) else "MISSING", True),
        fact("CONTRACT_DURATION_START", "RECORDED" if any((item.metadata_json or {}).get("duration_start_fact") for item in evidence) else "NOT_RECORDED", False),
        fact("MUNICIPALITY_WORK_START", "NOT_RECORDED", False),
    ]
    blockers = [item["fact"] for item in facts if item["required"] and item["state"] in {"MISSING", "UNSATISFIED"}]
    commercial_ready = not [item for item in facts if item["fact"] in {"CONTRACT_EXECUTED", "CLIENT_COPY_DISTRIBUTED", "OPERATIONS_HANDOFF", "REQUIRED_ADVANCE_SATISFIED"} and item["state"] not in {"RECORDED", "SATISFIED", "NOT_APPLICABLE"}]
    return {"status": "COMMERCIAL_START_READY" if commercial_ready else "COMMERCIAL_START_BLOCKED", "facts": facts, "blockers": blockers, "required_advance": {"applicability": "REQUIRED" if advance_required else "NOT_APPLICABLE", "term_ids": [item.id for item in advance_terms], "invoice_revision_ids": [item.id for item in matching_revisions], "verified_payment_ids": [item.id for item in verified_payments], "allocation_ids": [item.id for item in allocations], "satisfied": advance_satisfied}, "policy_version": "CONTRACT_START_PREREQUISITES_V1"}


def contract_readiness_states(db: Session, contract: Contract) -> dict[str, Any]:
    """Return independent readiness states with their evidence boundaries."""
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    evidence = _contract_evidence(db, contract.id, revision.id if revision else None)
    services = db.scalars(select(ServiceEngagement).where(ServiceEngagement.contract_id == contract.id)).all()
    service_codes = {str(item.service_offering_code or "").upper() for item in services}
    design_applicable = bool(service_codes & {"DESIGN", "DESIGN_PERMIT", "PERMIT"})
    authority_applicable = bool(service_codes & {"PERMIT", "DESIGN_PERMIT", "AUTHORITY", "CIVIL_DEFENSE", "MAINTENANCE_PERMIT"})
    required_inputs = db.scalars(select(ContractClientInputRequirement).where(ContractClientInputRequirement.contract_id == contract.id, ContractClientInputRequirement.required == true())).all()
    def input_state(keys: set[str], *, all_required: bool = False) -> tuple[list[str], list[str]]:
        rows = [item for item in required_inputs if str(item.input_code or "").upper() in keys]
        required = [str(item.input_code or item.title) for item in rows] if rows else (sorted(keys) if all_required else [])
        current = [str(item.input_code or item.title) for item in rows if str(item.status).upper() in {"RECEIVED", "VERIFIED", "CONFIRMED", "COMPLETE", "CLOSED"}]
        return required, current
    def evidence_state(roles: set[str]) -> tuple[list[str], list[str]]:
        required = sorted(roles)
        current = sorted({item.source_role for item in evidence if item.source_role in roles and str(item.status).upper() in {"RECORDED", "RECEIVED", "VERIFIED", "APPROVED"}})
        return required, current
    start = contract_start_prerequisites(db, contract)
    executed_roles, current_roles = evidence_state({"EXECUTED_CONTRACT", "CLIENT_COPY_DISTRIBUTION", "OPERATIONS_HANDOFF"})
    design_keys, design_current = input_state({"OLD_DRAWINGS", "EXISTING_DRAWINGS", "PROJECT_SKETCH", "TITLE_DEED", "ID", "IDENTITY"})
    authority_roles, authority_current = evidence_state({"AUTHORITY_SUBMISSION", "AUTHORITY_APPROVAL", "FULL_SUBMISSION_DOSSIER"})
    def state(name: str, applicable: bool, required: list[str], current: list[str], *, policy: str, extra_blockers: list[str] | None = None) -> dict[str, Any]:
        missing = sorted(set(required) - set(current))
        missing.extend(extra_blockers or [])
        return {"name": name, "applicability": "APPLICABLE" if applicable else "NOT_APPLICABLE", "required_evidence": required, "current_evidence": current, "missing_evidence": sorted(set(missing)), "policy_version": policy, "evaluated_at": now().isoformat(), "result": "NOT_APPLICABLE" if not applicable else "READY" if not missing else "BLOCKED"}
    design = state("DESIGN_START_READY", design_applicable, design_keys, design_current, policy="CONTRACT_DESIGN_START_MINIMUM_DOSSIER_V1", extra_blockers=[] if not design_applicable or db.scalar(select(ProjectActivation).where(ProjectActivation.contract_id == contract.id)) else ["PROJECT_ACTIVATION"])
    authority = state("AUTHORITY_SUBMISSION_READY", authority_applicable, authority_roles, authority_current, policy="CONTRACT_AUTHORITY_SUBMISSION_DOSSIER_V1")
    service = state("SERVICE_EXECUTION_READY", bool(services), executed_roles + (["PROJECT_ACTIVATION"] if services else []), current_roles + (["PROJECT_ACTIVATION"] if db.scalar(select(ProjectActivation).where(ProjectActivation.contract_id == contract.id)) else []), policy="CONTRACT_SERVICE_EXECUTION_GATE_V1")
    commercial_blockers = [item for item in start["blockers"] if item != "PROJECT_ACTIVATION"]
    commercial_current = ["CONTRACT_EXECUTED", "CLIENT_COPY_DISTRIBUTION", "OPERATIONS_HANDOFF", "REQUIRED_ADVANCE_SATISFIED"] if not commercial_blockers and start["required_advance"]["satisfied"] else []
    commercial = state("COMMERCIAL_START_READY", True, ["CONTRACT_EXECUTED", "CLIENT_COPY_DISTRIBUTION", "OPERATIONS_HANDOFF", "REQUIRED_ADVANCE_SATISFIED"], commercial_current, policy="CONTRACT_COMMERCIAL_START_GATE_V1", extra_blockers=commercial_blockers)
    return {"policy_version": "CONTRACT_READINESS_STATES_V1", "evaluated_at": now().isoformat(), "states": {"COMMERCIAL_START_READY": commercial, "DESIGN_START_READY": design, "AUTHORITY_SUBMISSION_READY": authority, "SERVICE_EXECUTION_READY": service}}


def project_activation(db: Session, *, contract: Contract, project_code: str, start_date: date, actor: str, correlation_id: str, idempotency_key: str) -> tuple[Project, ProjectActivation, bool]:
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    if not contract_revision_is_accepted(revision):
        raise ValueError("CONTRACT_ACCEPTANCE_REQUIRED")
    if not db.scalar(select(ContractAdminEvidence).where(ContractAdminEvidence.contract_id == contract.id, ContractAdminEvidence.contract_revision_id == revision.id, ContractAdminEvidence.source_role == "EXECUTED_CONTRACT")):
        raise ValueError("EXECUTED_CONTRACT_EVIDENCE_REQUIRED")
    activation_fields = set(effective_activation_fields(db))
    if "CONTRACT" in activation_fields and not contract.id:
        raise ValueError("CONTRACT_REQUIRED_FOR_PROJECT_ACTIVATION")
    if "ACCEPTED_PROPOSAL_REVISION" in activation_fields and not contract.accepted_proposal_revision_id:
        raise ValueError("ACCEPTED_PROPOSAL_REVISION_REQUIRED")
    if "CLIENT" in activation_fields and not contract.client_account_id:
        raise ValueError("CLIENT_CONTEXT_REQUIRED")
    configured_gate = db.scalar(select(ContractAdminInput).where(ContractAdminInput.contract_id == contract.id, ContractAdminInput.input_key == "ADVANCE_PAYMENT_ACTIVATION_GATE"))
    evidence = db.scalars(select(ContractAdminEvidence).where(ContractAdminEvidence.contract_id == contract.id)).all()
    advance_control = advance_payment_gate(configured_gate.value_json if configured_gate else None, [{"source_role": item.source_role, "status": item.status, "metadata": item.metadata_json} for item in evidence])
    if advance_control["status"] == "BLOCKED":
        raise ValueError("OBJECTIVE_ADVANCE_PAYMENT_EVIDENCE_REQUIRED")
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
    revision = revision or db.scalar(select(ContractRevision).where(ContractRevision.contract_id == contract.id).order_by(ContractRevision.revision_number.desc()))
    if not revision:
        raise ValueError("CONTRACT_REVISION_REQUIRED")
    activation = ProjectActivation(contract_id=contract.id, contract_revision_id=revision.id, accepted_proposal_revision_id=contract.accepted_proposal_revision_id, project_id=project.id, project_code=project_code, start_date=start_date, original_start_date=start_date, activated_by=actor, idempotency_key=idempotency_key, audit_metadata={"authority": "HUMAN_OWNER", "contract_reference": contract.contract_reference, "advance_payment_gate": advance_control})
    db.add(activation)
    db.flush()
    for upstream_type, upstream_id, upstream_hash in (("Contract", contract.id, contract.contract_reference), ("ContractRevision", revision.id, revision.content_hash), ("ProposalAcceptedRevision", contract.accepted_proposal_revision_id, None)):
        if not upstream_id: continue
        if not db.scalar(select(LineageEdge).where(LineageEdge.project_id == project.id, LineageEdge.upstream_type == upstream_type, LineageEdge.upstream_id == upstream_id, LineageEdge.downstream_type == "Project", LineageEdge.downstream_id == project.id)):
            db.add(LineageEdge(project_id=project.id, upstream_type=upstream_type, upstream_id=upstream_id, upstream_version_or_hash=upstream_hash, downstream_type="Project", downstream_id=project.id, downstream_version_or_hash=project_code, dependency_kind="CONTRACT_PROJECT_ACTIVATION", correlation_id=correlation_id))
    audit(db, correlation_id=correlation_id, event_type="HUMAN_PROJECT_ACTIVATED_FROM_CONTRACT", entity_type="Project", entity_id=project.id, actor_id=actor, after={"contract_id": contract.id, "contract_revision_id": revision.id, "accepted_proposal_revision_id": contract.accepted_proposal_revision_id, "project_code": project_code, "start_date": start_date.isoformat(), "automatic": False})
    db.add(NotificationEvent(recipient_role="OWNER", channel="IN_APP", event_type="PROJECT_ACTIVATED", status="PENDING", subject=f"Project activated: {project.project_code}", body_preview="Owner explicitly activated the canonical Project from the Contract workbench.", correlation_id=correlation_id, domain="CONTRACT_WORKFLOW", contract_id=contract.id, proposal_id=contract.proposal_id, audience=["OWNER", "BUSINESS_DEVELOPMENT", "ENGINEERING"], actor=actor, deep_link=f"/contracts/{contract.id}"))
    return project, activation, True


def contract_operations_projection(db: Session, contract: Contract) -> dict[str, Any]:
    """Project Contract/Mobilization operations from canonical domain records.

    This is deliberately read-only.  Operations sees Contract, Project
    Activation, ServiceEngagement, WorkflowTask, Finding, NotificationEvent,
    and Contract evidence; it does not create a second operational truth store.
    """
    revision = db.get(ContractRevision, contract.current_revision_id) if contract.current_revision_id else None
    activation = db.scalar(select(ProjectActivation).where(ProjectActivation.contract_id == contract.id))
    project = db.get(Project, activation.project_id) if activation else (db.get(Project, contract.project_id) if contract.project_id else None)
    readiness_result = readiness(db, contract, enforce_maker_checker=True)
    services = db.scalars(select(ServiceEngagement).where(ServiceEngagement.contract_id == contract.id).order_by(ServiceEngagement.created_at)).all()
    task_query = select(WorkflowTask).where(WorkflowTask.context_type == "CONTRACT", WorkflowTask.context_id == contract.id)
    if project:
        task_query = select(WorkflowTask).where(or_(WorkflowTask.context_id == contract.id, WorkflowTask.project_id == project.id))
    tasks = db.scalars(task_query.order_by(WorkflowTask.created_at.desc())).all()
    findings_query = select(Finding).where(Finding.contract_id == contract.id)
    if project:
        findings_query = select(Finding).where(or_(Finding.contract_id == contract.id, Finding.project_id == project.id))
    findings = db.scalars(findings_query.order_by(Finding.captured_at.desc())).all()
    notifications = db.scalars(select(NotificationEvent).where(NotificationEvent.contract_id == contract.id).order_by(NotificationEvent.created_at.desc())).all()
    evidence = db.scalars(select(ContractAdminEvidence).where(ContractAdminEvidence.contract_id == contract.id).order_by(ContractAdminEvidence.recorded_at.desc())).all()
    start_prerequisites = contract_start_prerequisites(db, contract)
    readiness_states = contract_readiness_states(db, contract)
    operational_contact_routing = operational_contact_routing_projection(db, contract, project)
    open_tasks = [item for item in tasks if str(item.status).upper() not in {"CLOSED", "COMPLETED", "CANCELLED"}]
    current_time = now()
    overdue_tasks = [item for item in open_tasks if item.due_at and item.due_at < (current_time.replace(tzinfo=None) if item.due_at.tzinfo is None else current_time)]
    open_blocking_findings = [item for item in findings if item.blocking and str(item.status).upper() not in {"CLOSED", "RESOLVED", "DISMISSED"}]
    required_inputs = db.scalars(select(ContractClientInputRequirement).where(ContractClientInputRequirement.contract_id == contract.id, ContractClientInputRequirement.required == true())).all()
    open_required_inputs = [item for item in required_inputs if str(item.status).upper() not in {"RECEIVED", "VERIFIED", "CONFIRMED", "CLOSED", "COMPLETE"}]
    blockers = [item["code"] for item in readiness_result["blockers"]]
    blockers.extend(f"BLOCKING_FINDING:{item.id}" for item in open_blocking_findings)
    if not activation:
        schedule_state = "PROJECT_ACTIVATION_REQUIRED"
    elif not project or str(project.status).upper() != "ACTIVE":
        schedule_state = "PROJECT_NOT_ACTIVE"
    elif overdue_tasks:
        schedule_state = "OVERDUE_ACTION"
    else:
        schedule_state = "ON_TRACK"
    next_task = overdue_tasks[0] if overdue_tasks else (open_tasks[0] if open_tasks else None)
    if readiness_result["blockers"]:
        next_action = readiness_result["blockers"][0]["label"]
        responsible_action = "OWNER"
    elif not activation:
        next_action = "Explicit Owner Project Activation"
        responsible_action = "OWNER"
    elif next_task:
        next_action = next_task.next_action_code or next_task.title
        responsible_action = next_task.owner_role
    elif open_blocking_findings:
        next_action = open_blocking_findings[0].title
        responsible_action = open_blocking_findings[0].assignee_role or "RESPONSIBLE_ENGINEER"
    else:
        next_action = "No open Contract/Mobilization action"
        responsible_action = "OWNER"
    executed_evidence = [item for item in evidence if str(item.source_role).upper() == "EXECUTED_CONTRACT" and item.contract_revision_id == (revision.id if revision else None)]
    duration_start = next(((item.metadata_json or {}).get("duration_start_fact") for item in evidence if (item.metadata_json or {}).get("duration_start_fact")), None)
    expected_end = contract.expected_close_date or contract.end_date
    days_remaining = (expected_end - current_time.date()).days if expected_end else None
    extension_history = [item for item in evidence if str(item.source_role).upper() == "CONTRACT_EXTENSION"]
    extension_state = "EXTENSION_REVIEW_REQUIRED" if expected_end and days_remaining is not None and days_remaining < 0 and str(contract.status).upper() not in {"CLOSED", "COMPLETE"} else "NO_EXTENSION_RISK_RECORDED"
    if extension_history:
        extension_state = "EXTENSION_RECORDED_PENDING_OWNER_REVIEW"
    billing_plan = db.scalar(select(BillingPlan).where(BillingPlan.contract_id == contract.id, BillingPlan.status != "CANCELLED").order_by(BillingPlan.created_at.desc()))
    billing_plan_revision = db.get(BillingPlanRevision, billing_plan.current_revision_id) if billing_plan and billing_plan.current_revision_id else None
    milestones = db.scalars(select(BillingMilestone).where(BillingMilestone.billing_plan_revision_id == billing_plan_revision.id)).all() if billing_plan_revision else []
    earned = [item for item in milestones if str(item.eligibility_state).upper() in {"ELIGIBLE", "EARNED", "MILESTONE_EARNED"} and (item.remaining_invoiceable_amount or 0) > 0]
    invoice_revisions = db.scalars(select(InvoiceRevision).where(InvoiceRevision.controlling_contract_revision_id == (revision.id if revision else ""))).all() if revision else []
    issued_milestones = {item.controlling_milestone_id for item in invoice_revisions if item.status == "ISSUED"}
    billing_state = "READY_TO_INVOICE" if earned else "INVOICE_ISSUED" if any(item.status == "ISSUED" for item in invoice_revisions) else "NO_INVOICE_DUE_SIGNAL"
    collection_state = "NOT_ISSUED" if not invoice_revisions else "ISSUED" if any(item.status == "ISSUED" for item in invoice_revisions) else "PREPARATION"
    return {
        "status": "BLOCKED" if blockers else "READY",
        "source_of_record": "CANONICAL_CONTRACT_PROJECT_MOBILIZATION_READ_MODEL",
        "contract": {"id": contract.id, "reference": contract.contract_reference, "status": contract.status, "stage": contract.stage, "current_revision_id": revision.id if revision else None, "accepted": contract_revision_is_accepted(revision), "authority_reviewed": contract_revision_is_authority_reviewed(revision)},
        "project": {"id": project.id, "reference": project.project_number, "code": project.project_code, "status": project.status, "start_date": project.start_date.isoformat() if project and project.start_date else None} if project else None,
        "dates": {"contract_end": (contract.expected_close_date or contract.end_date).isoformat() if (contract.expected_close_date or contract.end_date) else None, "project_start": activation.start_date.isoformat() if activation else None, "close_date_meaning": contract.close_date_meaning},
        "mobilization": {"project_activation": "ACTIVE" if activation and project and str(project.status).upper() == "ACTIVE" else "REQUIRED", "service_engagement_count": len(services), "service_engagements": [{"id": item.id, "service_ref": item.service_ref, "status": item.status, "project_id": item.project_id, "contract_revision_id": item.contract_revision_id} for item in services]},
        "controls": {"blockers": blockers, "open_readiness_blockers": readiness_result["blockers"], "open_blocking_findings": [{"id": item.id, "title": item.title, "status": item.status, "severity": item.severity, "assignee_role": item.assignee_role} for item in open_blocking_findings], "open_tasks": [{"id": item.id, "title": item.title, "status": item.status, "priority": item.priority, "owner_role": item.owner_role, "due_at": item.due_at.isoformat() if item.due_at else None, "next_action_code": item.next_action_code} for item in open_tasks], "overdue_task_count": len(overdue_tasks), "required_input_state": "OPEN_REQUIRED_INPUTS" if open_required_inputs else "NO_OPEN_REQUIRED_INPUTS", "required_input_count": len(open_required_inputs), "extension_state": extension_state, "invoice_due_state": billing_state, "earned_not_invoiced_state": "EARNED_BUT_NOT_INVOICED" if earned and not issued_milestones.intersection({item.id for item in earned}) else "NO_EARNED_NOT_INVOICED_SIGNAL", "collection_state": collection_state, "contact_state": "CONTACT_RESOLUTION_REQUIRED" if services and operational_contact_routing["unresolved_purposes"] else "PURPOSE_CONTACT_AVAILABLE"},
        "schedule_state": schedule_state,
        "delay_state": "OVERDUE" if overdue_tasks else "NO_OVERDUE_TASKS",
        "risk_state": "BLOCKED" if open_blocking_findings or readiness_result["blockers"] else "NO_BLOCKING_RISK_RECORDED",
        "responsible_action": responsible_action,
        "next_action": next_action,
        "start_prerequisites": start_prerequisites,
        "readiness_states": readiness_states,
        "operational_contact_routing": operational_contact_routing,
        "contract_clock": {"contract_date": revision.created_at.date().isoformat() if revision and revision.created_at else None, "period_or_duration": contract.duration, "duration_start_rule": "EXPLICIT_DURATION_START_FACT; PROJECT_ACTIVATION_NOT_IMPLIED", "duration_start_fact": duration_start, "original_expected_end": expected_end.isoformat() if expected_end else None, "current_expected_end": expected_end.isoformat() if expected_end else None, "days_remaining": days_remaining, "extension_history": [{"id": item.id, "recorded_at": item.recorded_at.isoformat(), "source_reference": item.source_reference, "metadata": item.metadata_json} for item in extension_history], "extension_state": extension_state},
        "billing_readiness": {"state": billing_state, "milestone_ids": [item.id for item in earned], "invoice_revision_ids": [item.id for item in invoice_revisions], "invoice_issue_is_separate_human_action": True, "collection_state": collection_state},
        "executed_evidence": [{"id": item.id, "contract_id": item.contract_id, "contract_revision_id": item.contract_revision_id, "document_version_id": item.document_version_id, "source_reference": item.source_reference, "content_hash": item.content_hash, "recorded_by": item.recorded_by, "recorded_at": item.recorded_at.isoformat(), "metadata": item.metadata_json} for item in executed_evidence],
        "notification_count": len(notifications),
        "auditability": "AUDIT_EVENTS_AND_CANONICAL_ROWS",
        "external_send": "HUMAN_CONTROLLED",
    }


def contract_projection(db: Session, contract: Contract, *, include_history: bool = True) -> dict[str, Any]:
    proposal = db.get(Opportunity, contract.proposal_id) if contract.proposal_id else None
    if not proposal and contract.quotation_id:
        quotation = db.get(Quotation, contract.quotation_id)
        proposal = db.get(Opportunity, quotation.opportunity_id) if quotation else None
    client = db.get(ClientAccount, contract.client_account_id) if contract.client_account_id else None
    contacts = db.scalars(select(ClientContact).where(ClientContact.client_account_id == contract.client_account_id, ClientContact.status == "ACTIVE").order_by(ClientContact.name)).all() if contract.client_account_id else []
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
    billing = contract_billing_context(db, contract)
    payment_terms, deliverables, client_inputs = _revision_terms(db, revision.id if revision else None)
    acceptance = (revision.admin_input_snapshot or {}).get("acceptance") if revision else None
    return {"id": contract.id, "contract": {"id": contract.id, "name": contract.contract_name, "reference": contract.contract_reference, "stage": contract.stage or contract.status, "status": contract.status, "amount": contract.amount_value, "currency": contract.currency, "duration": contract.duration, "expected_close_date": contract.expected_close_date.isoformat() if contract.expected_close_date else None, "actual_close_date": contract.actual_close_date.isoformat() if contract.actual_close_date else None, "close_date_meaning": contract.close_date_meaning, "last_activity": (contract.last_activity_at or contract.updated_at).isoformat(), "authority_state": contract.authority_state}, "client": {"id": client.id, "reference": client.client_reference, "name": client.display_name} if client else None, "project": {"id": project.id, "reference": project.project_number, "code": project.project_code, "name": project.project_name, "start_date": project.start_date.isoformat() if project and project.start_date else None, "status": project.status} if project else None, "origin": {"proposal_id": proposal.id, "proposal_reference": proposal.opportunity_reference, "title": proposal.title, "accepted_revision_id": accepted.id, "revision_number": accepted.revision_number, "content_hash": accepted.content_hash, "snapshot": accepted.snapshot} if proposal and accepted else None, "current_revision": {"id": revision.id, "revision_number": revision.revision_number, "accepted_proposal_revision_id": revision.accepted_proposal_revision_id, "content_hash": revision.content_hash, "status": revision.status, "accepted": contract_revision_is_accepted(revision), "authority_reviewed": contract_revision_is_authority_reviewed(revision), "maker_checker": (revision.admin_input_snapshot or {}).get("maker_checker") if revision else None, "accepted_by": acceptance.get("accepted_by") if acceptance else None, "accepted_at": acceptance.get("accepted_at") if acceptance else None} if revision else None, "template": {"ref": template.master_content_ref, "version": template.version, "version_id": template.document_version_id, "hash": template.content_hash, "master_content_id": template.master_content_id} if template else None, "inputs": [{"key": item.input_key, "value": item.value_json, "entered_by": item.entered_by, "reason": item.reason, "updated_at": item.updated_at.isoformat()} for item in inputs], "evidence": [{"id": item.id, "type": item.evidence_type, "source_reference": item.source_reference, "hash": item.content_hash, "status": item.status, "recorded_by": item.recorded_by, "contract_revision_id": item.contract_revision_id, "document_version_id": item.document_version_id, "recorded_at": item.recorded_at.isoformat(), "metadata": item.metadata_json} for item in evidence], "executed_evidence": [{"id": item.id, "source_reference": item.source_reference, "document_version_id": item.document_version_id, "content_hash": item.content_hash, "status": item.status, "recorded_by": item.recorded_by, "recorded_at": item.recorded_at.isoformat(), "contract_revision_id": item.contract_revision_id, "metadata": item.metadata_json} for item in evidence if str(item.source_role).upper() == "EXECUTED_CONTRACT"], "readiness": readiness(db, contract), "activation": {"id": activation.id, "project_id": activation.project_id, "project_code": activation.project_code, "start_date": activation.start_date.isoformat(), "activated_by": activation.activated_by, "activated_at": activation.activated_at.isoformat()} if activation else None, "operations": contract_operations_projection(db, contract), "my_work": [{"id": item.id, "title": item.title, "status": item.status, "next_action_code": item.next_action_code, "deep_link": item.deep_link} for item in tasks], "issues": [{"id": item.id, "title": item.title, "status": item.status, "severity": item.severity, "blocking": item.blocking, "deep_link": item.deep_link} for item in issues], "notifications": [{"id": item.id, "event_type": item.event_type, "status": item.status, "subject": item.subject, "created_at": item.created_at.isoformat()} for item in notifications], "history": [{"id": item.id, "event_type": item.event_type, "entity_type": item.entity_type, "occurred_at": item.occurred_at.isoformat(), "actor": item.actor_id, "after": item.after_json} for item in history], "effective_policies": {"stage": runtime_decision_value(db, "CONTRACT_STAGE_POLICY", {"stages": list(CONTRACT_STAGES)}), "authority_review_meaning": runtime_decision_value(db, "CONTRACT_AUTHORITY_REVIEW_MEANING", "OWNER_REVIEW_REQUIRED_NOT_LEGAL_EXECUTION"), "ready_close": runtime_decision_value(db, "CONTRACT_READY_CLOSE_POLICY", "REQUIRED_FIELDS_EVIDENCE_AND_OWNER_AUTHORITY_ACTION"), "close_date": runtime_decision_value(db, "CONTRACT_CLOSE_DATE_MEANING", "EXPECTED_CLOSE_DATE_UNTIL_OWNER_CONFIRMS_CLOSE"), "reference": effective_contract_reference_policy(db), "required_fields": effective_required_fields(db), "required_evidence": effective_required_evidence(db), "authority": runtime_decision_value(db, "CONTRACT_AUTHORITY_POLICY", "OWNER_ONLY_FOR_AUTHORITY_AND_EXECUTION_STATE"), "manual_new": runtime_decision_value(db, "MANUAL_NEW_CONTRACT_POLICY", "SELECT_ACCEPTED_PROPOSAL_ONLY"), "origin_policy": effective_contract_origin_policy(db), "amount_change": runtime_decision_value(db, "CONTRACT_AMOUNT_CHANGE_AUTHORITY", "OWNER_ONLY_WITH_REASON_AND_NEW_REVISION"), "artifact_strategy": runtime_decision_value(db, "CONTRACT_ARTIFACT_STRATEGY", "CANONICAL_TEMPLATE_RENDER_PLUS_EVIDENCE"), "reopen": runtime_decision_value(db, "CONTRACT_REOPEN_POLICY", "OWNER_DECISION_REQUIRED_WITH_PROSPECTIVE_REVALIDATION"), "activation_trigger": runtime_decision_value(db, "CONTRACT_TO_PROJECT_TRIGGER", "EXPLICIT_OWNER_ACTION_AFTER_CONTRACT_READINESS"), "activation_authority": runtime_decision_value(db, "PROJECT_ACTIVATION_AUTHORITY", "OWNER_ONLY_HUMAN_ACTION"), "code_assignment": runtime_decision_value(db, "PROJECT_CODE_ASSIGNMENT_METHOD", "OWNER_ENTERED_UNIQUE"), "code_format": runtime_decision_value(db, "PROJECT_CODE_FORMAT", {"pattern": "AMEC-YYYY-NNN", "example": "AMEC-2026-001"}), "code_mutability": runtime_decision_value(db, "PROJECT_CODE_MUTABILITY_POLICY", "IMMUTABLE_AFTER_ACTIVATION"), "start_date": runtime_decision_value(db, "PROJECT_START_DATE_SEMANTICS", "ORIGINAL_HUMAN_ACTIVATION_DATE"), "activation_fields": effective_activation_fields(db), "close_vs_activation": runtime_decision_value(db, "CONTRACT_CLOSE_VS_PROJECT_ACTIVATION", "SEPARATE_EVENTS_WITH_LINEAGE")}}
