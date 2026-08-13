"""Contract-driven Billing and Invoice lifecycle.

This router is deliberately bounded: it records governed billing setup,
invoice evidence, receivables, and verified payment evidence.  It never writes
an accounting journal, calls a bank, sends an invoice, or marks a project
financially settled.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..expansion.runtime import render_artifact, select_template
from ..models import (
    BillingMilestone, BillingMilestoneEligibility, BillingPlan, BillingPlanRevision,
    ClientAccount, Contract, ContractAdminEvidence, ContractPaymentTerm,
    ContractRevision, Document, DocumentVersion, FinancialAccountMaster, RenderedArtifact,
    FinancialAccountVersion, Invoice, InvoiceAcceptRecord, InvoiceApprovalRecord, InvoiceRevision,
    InvoiceIssueEvent, InvoiceLineItem, InvoiceNumberingPolicy, InvoicePaymentAllocation,
    InvoiceReference, LineageEdge, PaymentReceipt, Project, ProjectActivation,
    ReceivableFollowUp, Role, TemplateDefinition, TemplateVersion,
)
from ..services.contract_workspace import contract_billing_context, contract_revision_is_finalized
from ..services.owner_decisions import runtime_decision_value
from ..services.week45 import stable_hash


router = APIRouter(prefix="/api/billing", tags=["billing-invoice"])

OWNER = {Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN}
PLAN_WRITE = OWNER | {Role.PROCESS_CHAMPION}
VIEW = PLAN_WRITE | {Role.RESPONSIBLE_ENGINEER, Role.PERMIT_PREPARER, Role.REQUIREMENT_STEWARD}


def _actor(request: Request, payload: dict[str, Any] | None = None) -> str:
    return request.headers.get("X-Dev-Actor") or str((payload or {}).get("actor") or "billing-owner")


def _corr(request: Request) -> str:
    return getattr(request.state, "correlation_id", str(uuid4()))


def _role(role: Role, allowed: set[Role], code: str) -> None:
    if role not in allowed:
        raise HTTPException(403, {"code": "CAPABILITY_DENIED", "capability": code})


def _row(item: Any, *, mask_sensitive: bool = False) -> dict[str, Any] | None:
    if item is None:
        return None
    values = {column.name: getattr(item, column.name) for column in item.__table__.columns}
    if mask_sensitive:
        for key in ("account_reference",):
            if values.get(key):
                values[key] = f"••••{str(values[key])[-4:]}"
    return jsonable_encoder(values)


def _d(value: Any, *, field: str = "amount") -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise HTTPException(422, {"code": "MONEY_INVALID", "field": field}) from exc
    if not result.is_finite():
        raise HTTPException(422, {"code": "MONEY_INVALID", "field": field})
    return result


def _money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _date(value: Any, *, field: str) -> date:
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError) as exc:
        raise HTTPException(422, {"code": "DATE_INVALID", "field": field}) from exc


def _contract_context(db: Session, contract_id: str, revision_id: str | None = None) -> tuple[Contract, ContractRevision, dict[str, Any], Project | None]:
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(404, {"code": "CONTRACT_NOT_FOUND"})
    selected_id = revision_id or contract.current_revision_id
    revision = db.get(ContractRevision, selected_id) if selected_id else None
    if not revision or revision.contract_id != contract.id:
        raise HTTPException(409, {"code": "EXACT_FINALIZED_CONTRACT_REVISION_REQUIRED"})
    if not contract_revision_is_finalized(revision):
        raise HTTPException(409, {"code": "CONTRACT_REVISION_NOT_FINALIZED", "status": revision.status})
    if not contract.client_account_id or not db.get(ClientAccount, contract.client_account_id):
        raise HTTPException(409, {"code": "CANONICAL_CLIENT_REQUIRED"})
    context = contract_billing_context(db, contract, revision.id)
    activation = db.scalar(select(ProjectActivation).where(ProjectActivation.contract_id == contract.id, ProjectActivation.status == "ACTIVE"))
    project = db.get(Project, activation.project_id) if activation else (db.get(Project, contract.project_id) if contract.project_id else None)
    return contract, revision, context, project


def _scope_project(db: Session, project_id: str | None, contract: Contract, project: Project | None) -> None:
    if project_id and (not project or project.id != project_id):
        raise HTTPException(403, {"code": "CROSS_PROJECT_BILLING_CONTEXT_DENIED"})


def _audit(db: Session, request: Request, event: str, entity_type: str, entity_id: str, actor: str, after: dict[str, Any] | None = None) -> None:
    safe = after or {}
    for key in ("account_reference", "iban", "bank_account", "payment_evidence"):
        safe.pop(key, None)
    audit(db, correlation_id=_corr(request), event_type=event, entity_type=entity_type, entity_id=entity_id, actor_id=actor, after=safe)


def _lineage(db: Session, request: Request, project_id: str | None, upstream_type: str, upstream_id: str, downstream_type: str, downstream_id: str, kind: str) -> None:
    if project_id:
        db.add(LineageEdge(project_id=project_id, upstream_type=upstream_type, upstream_id=upstream_id, downstream_type=downstream_type, downstream_id=downstream_id, dependency_kind=kind, correlation_id=_corr(request)))


def _contract_amount(revision: ContractRevision, fallback: Contract) -> Decimal | None:
    raw = revision.amount_value or fallback.amount_value
    if not raw:
        return None
    match = re.search(r"[-+]?\d[\d,]*(?:\.\d+)?", str(raw))
    return _money(Decimal(match.group(0).replace(",", ""))) if match else None


def _plan_revision(db: Session, plan_revision_id: str) -> tuple[BillingPlanRevision, BillingPlan, Contract, ContractRevision, Project | None]:
    revision = db.get(BillingPlanRevision, plan_revision_id)
    if not revision:
        raise HTTPException(404, {"code": "BILLING_PLAN_REVISION_NOT_FOUND"})
    plan = db.get(BillingPlan, revision.billing_plan_id)
    contract = db.get(Contract, revision.contract_id)
    contract_revision = db.get(ContractRevision, revision.contract_revision_id)
    project = db.get(Project, revision.project_id) if revision.project_id else None
    if not plan or not contract or not contract_revision:
        raise HTTPException(409, {"code": "BILLING_PLAN_LINEAGE_BROKEN"})
    return revision, plan, contract, contract_revision, project


def _milestone_amount(db: Session, plan_revision: BillingPlanRevision, contract: Contract, contract_revision: ContractRevision, payload: dict[str, Any]) -> Decimal | None:
    basis = str(payload.get("basis_type") or "").upper()
    currency = str(payload.get("currency") or plan_revision.currency).upper()
    if currency != plan_revision.currency.upper():
        raise HTTPException(409, {"code": "CURRENCY_MISMATCH"})
    if basis == "FIXED_AMOUNT":
        return _money(_d(payload.get("basis_amount"), field="basis_amount"))
    if basis == "PERCENTAGE_OF_CONTRACT":
        percentage = _d(payload.get("percentage"), field="percentage")
        if percentage <= 0 or percentage > 100:
            raise HTTPException(422, {"code": "PERCENTAGE_OUT_OF_RANGE"})
        base = _contract_amount(contract_revision, contract)
        if base is None:
            raise HTTPException(409, {"code": "CONTRACT_AMOUNT_REQUIRED"})
        return _money(base * percentage / Decimal("100"))
    if basis == "VALUATION":
        if str(contract_revision.valuation_status).upper() not in {"OWNER_CONFIRMED", "VERIFIED", "HUMAN_VERIFIED"}:
            raise HTTPException(409, {"code": "VALUATION_NOT_AUTHORIZED_FOR_BILLING"})
        if not contract_revision.valuation_amount or str(contract_revision.valuation_currency).upper() != currency:
            raise HTTPException(409, {"code": "VALUATION_NOT_AUTHORIZED_FOR_BILLING"})
        return _money(_d(contract_revision.valuation_amount, field="valuation_amount"))
    if basis in {"EVENT_AMOUNT", "MANUAL_APPROVED"}:
        return _money(_d(payload.get("basis_amount"), field="basis_amount"))
    if basis == "REIMBURSABLE":
        raise HTTPException(409, {"code": "REIMBURSABLE_POLICY_REQUIRED"})
    raise HTTPException(422, {"code": "BASIS_TYPE_NOT_ENABLED", "basis_type": basis})


def _line_total(line: InvoiceLineItem) -> Decimal:
    return _money(_d(line.calculated_line_amount or 0))


def _amount_in_words(amount: Decimal, currency: str) -> str:
    # Deterministic English renderer; locale/template policy can replace this
    # later without changing the stored payable amount.
    ones = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
    tens = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
    def words(n: int) -> str:
        if n < 20: return ones[n]
        if n < 100: return tens[n // 10] + (f"-{ones[n % 10]}" if n % 10 else "")
        if n < 1000: return f"{ones[n // 100]} hundred" + (f" {words(n % 100)}" if n % 100 else "")
        if n < 1_000_000: return f"{words(n // 1000)} thousand" + (f" {words(n % 1000)}" if n % 1000 else "")
        return str(n)
    value = _money(amount)
    whole, minor = int(value), int((value - int(value)) * 100)
    return f"{words(whole)} {currency.upper()}" + (f" and {words(minor)} minor" if minor else "")


def _invoice_revision(db: Session, invoice_id: str, revision_id: str | None = None) -> tuple[Invoice, Contract, InvoiceRevision, BillingPlanRevision | None, Project | None]:
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, {"code": "INVOICE_NOT_FOUND"})
    revision = db.get(InvoiceRevision, revision_id or invoice.current_revision_id) if (revision_id or invoice.current_revision_id) else None
    if not revision or revision.invoice_id != invoice.id:
        raise HTTPException(404, {"code": "INVOICE_REVISION_NOT_FOUND"})
    contract = db.get(Contract, invoice.contract_id)
    if not contract:
        raise HTTPException(409, {"code": "INVOICE_CONTRACT_MISSING"})
    plan_revision = db.get(BillingPlanRevision, revision.billing_plan_revision_id) if revision.billing_plan_revision_id else None
    project = db.get(Project, invoice.project_id) if invoice.project_id else None
    return invoice, contract, revision, plan_revision, project


def _lines(db: Session, revision_id: str) -> list[InvoiceLineItem]:
    return db.scalars(select(InvoiceLineItem).where(InvoiceLineItem.invoice_revision_id == revision_id).order_by(InvoiceLineItem.sequence)).all()


def _overbilling(db: Session, milestone_id: str, invoice_id: str) -> Decimal:
    rows = db.execute(select(InvoiceLineItem, InvoiceRevision, Invoice).join(InvoiceRevision, InvoiceRevision.id == InvoiceLineItem.invoice_revision_id).join(Invoice, Invoice.id == InvoiceRevision.invoice_id).where(InvoiceLineItem.billing_milestone_id == milestone_id, Invoice.id != invoice_id, Invoice.status.in_({"ACCEPTED_INTERNAL", "ISSUED"}))).all()
    return sum((_line_total(line) for line, _revision, _invoice in rows if line.affects_payable_total), Decimal("0.00"))


def _precheck(db: Session, invoice: Invoice, contract: Contract, revision: InvoiceRevision, plan_revision: BillingPlanRevision | None) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    contract_revision = db.get(ContractRevision, revision.controlling_contract_revision_id)
    checks.append({"code": "CONTRACT_CLIENT_PROJECT", "status": "PASS" if contract_revision and contract.client_account_id else "BLOCKED", "reason": "Canonical Contract, exact revision, and Client are present."})
    plan = db.get(BillingPlan, plan_revision.billing_plan_id) if plan_revision else None
    checks.append({"code": "ACTIVE_BILLING_PLAN", "status": "PASS" if plan and plan.status == "ACTIVE" else "BLOCKED", "reason": "An active BillingPlan is required."})
    lines = _lines(db, revision.id)
    checks.append({"code": "LINE_CALCULATION", "status": "PASS" if lines and all(_line_total(x) >= 0 for x in lines) else "BLOCKED", "reason": "Invoice lines have deterministic non-negative calculated amounts."})
    checks.append({"code": "CURRENCY", "status": "PASS" if revision.currency and plan_revision and revision.currency.upper() == plan_revision.currency.upper() else "BLOCKED", "reason": "Invoice and BillingPlan currency match."})
    checks.append({"code": "DUE_DATE", "status": "PASS" if revision.due_date else "NEEDS_REVIEW", "reason": "Due date is explicit or derived from a verified due-days term."})
    milestone_ok = True
    overbilling_ok = True
    overbilling_reasons: list[str] = []
    for line in lines:
        if not line.billing_milestone_id:
            continue
        milestone = db.get(BillingMilestone, line.billing_milestone_id)
        if not milestone or milestone.eligibility_state != "ELIGIBLE":
            milestone_ok = False
            continue
        committed = _overbilling(db, milestone.id, invoice.id)
        ceiling = _d(milestone.calculated_amount or 0)
        current = _line_total(line)
        if committed + current > ceiling:
            overbilling_ok = False
            overbilling_reasons.append(f"{milestone.id}: committed {committed + current} exceeds {ceiling}")
    checks.append({"code": "MILESTONE_ELIGIBILITY", "status": "PASS" if milestone_ok else "BLOCKED", "reason": "Every linked charge milestone is eligible."})
    checks.append({"code": "OVERBILLING", "status": "PASS" if overbilling_ok else "BLOCKED", "reason": "Milestone invoiceable amounts are checked against accepted/issued totals.", "details": overbilling_reasons})
    result = "BLOCKED" if any(item["status"] == "BLOCKED" for item in checks) else "NEEDS_REVIEW" if any(item["status"] == "NEEDS_REVIEW" for item in checks) else "PASS"
    return {"result": result, "checks": checks}


def _resolve_account(db: Session, currency: str, as_of: date, version_id: str | None = None) -> FinancialAccountVersion:
    if version_id:
        version = db.get(FinancialAccountVersion, version_id)
        if not version or version.currency.upper() != currency.upper() or version.status != "ACTIVE" or version.effective_from > as_of or (version.effective_to and version.effective_to < as_of):
            raise HTTPException(409, {"code": "FINANCIAL_ACCOUNT_VERSION_NOT_ELIGIBLE"})
        master = db.get(FinancialAccountMaster, version.financial_account_master_id)
        if not master or master.status != "ACTIVE":
            raise HTTPException(409, {"code": "FINANCIAL_ACCOUNT_MASTER_NOT_ACTIVE"})
        return version
    rows = db.scalars(select(FinancialAccountVersion).join(FinancialAccountMaster).where(FinancialAccountVersion.currency == currency.upper(), FinancialAccountVersion.status == "ACTIVE", FinancialAccountMaster.status == "ACTIVE", FinancialAccountVersion.effective_from <= as_of, (FinancialAccountVersion.effective_to.is_(None) | (FinancialAccountVersion.effective_to >= as_of)))).all()
    if not rows:
        raise HTTPException(409, {"code": "FINANCIAL_ACCOUNT_VERSION_REQUIRED"})
    if len(rows) > 1:
        raise HTTPException(409, {"code": "FINANCIAL_ACCOUNT_VERSION_AMBIGUOUS", "count": len(rows)})
    return rows[0]


def _mask_account(version: FinancialAccountVersion) -> dict[str, Any]:
    return {"id": version.id, "master_id": version.financial_account_master_id, "version_number": version.version_number, "bank_name": version.bank_name, "account_name": version.account_name, "account_reference": f"••••{version.account_reference[-4:]}", "currency": version.currency, "effective_from": version.effective_from.isoformat(), "effective_to": version.effective_to.isoformat() if version.effective_to else None, "status": version.status}


@router.get("/summary")
def billing_summary(db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, VIEW, "BILLING_VIEW")
    return {"plans": db.query(BillingPlan).count(), "milestones": db.query(BillingMilestone).count(), "invoices": db.query(Invoice).count(), "payment_receipts": db.query(PaymentReceipt).count(), "financial_accounts": db.query(FinancialAccountMaster).count(), "automation_defaults": {"auto_prepare_draft": False, "auto_accept": False, "auto_issue": False, "auto_mark_paid": False}}


@router.post("/plans")
def create_billing_plan(payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, PLAN_WRITE, "BILLING_PLAN_MANAGE")
    contract, revision, context, project = _contract_context(db, str(payload.get("contract_id") or ""), payload.get("contract_revision_id"))
    currency = str(payload.get("currency") or revision.currency or contract.currency or "").upper()
    if not currency:
        raise HTTPException(409, {"code": "CONTRACT_CURRENCY_REQUIRED"})
    existing = db.scalar(select(BillingPlan).where(BillingPlan.contract_id == contract.id, BillingPlan.contract_revision_id == revision.id, BillingPlan.status.not_in({"CANCELLED", "SUPERSEDED"})))
    if existing:
        return {"plan": _row(existing), "revision": _row(db.get(BillingPlanRevision, existing.current_revision_id))}
    plan = BillingPlan(contract_id=contract.id, contract_revision_id=revision.id, project_id=project.id if project else None, client_account_id=contract.client_account_id, currency=currency, automation_mode=str(payload.get("automation_mode") or "MANUAL").upper(), status="DRAFT", created_by=_actor(request, payload))
    db.add(plan); db.flush()
    plan_revision = BillingPlanRevision(billing_plan_id=plan.id, revision_number=1, contract_id=contract.id, contract_revision_id=revision.id, project_id=project.id if project else None, client_account_id=contract.client_account_id, contract_amount=_contract_amount(revision, contract), currency=currency, valuation_amount=revision.valuation_amount, valuation_currency=revision.valuation_currency, valuation_status=revision.valuation_status, status="DRAFT", created_by=_actor(request, payload), source_snapshot={"contract_billing_context": context, "project_activation_status": context.get("project_activation_status")})
    db.add(plan_revision); db.flush(); plan.current_revision_id = plan_revision.id
    _lineage(db, request, project.id if project else None, "ContractRevision", revision.id, "BillingPlanRevision", plan_revision.id, "BILLING_PLAN_FROM_EXACT_CONTRACT_REVISION")
    _audit(db, request, "BILLING_PLAN_CREATED", "BillingPlan", plan.id, _actor(request, payload), {"contract_revision_id": revision.id, "project_id": project.id if project else None, "automation_mode": plan.automation_mode})
    db.commit()
    return {"plan": _row(plan), "revision": _row(plan_revision), "context": context}


@router.get("/plans/{plan_id}")
def get_billing_plan(plan_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, VIEW, "BILLING_VIEW")
    plan = db.get(BillingPlan, plan_id)
    if not plan:
        raise HTTPException(404, {"code": "BILLING_PLAN_NOT_FOUND"})
    revision = db.get(BillingPlanRevision, plan.current_revision_id) if plan.current_revision_id else None
    milestones = db.scalars(select(BillingMilestone).where(BillingMilestone.billing_plan_revision_id == (revision.id if revision else "")).order_by(BillingMilestone.sequence)).all()
    return {"plan": _row(plan), "revision": _row(revision), "milestones": [_row(x) for x in milestones]}


@router.post("/plans/{plan_id}/revisions")
def revise_billing_plan(plan_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, PLAN_WRITE, "BILLING_PLAN_MANAGE")
    plan = db.get(BillingPlan, plan_id)
    if not plan or plan.status in {"CANCELLED", "SUPERSEDED"}:
        raise HTTPException(404, {"code": "BILLING_PLAN_NOT_FOUND"})
    previous = db.get(BillingPlanRevision, plan.current_revision_id)
    contract, contract_revision, context, project = _contract_context(db, plan.contract_id, plan.contract_revision_id)
    number = (db.scalar(select(func.max(BillingPlanRevision.revision_number)).where(BillingPlanRevision.billing_plan_id == plan.id)) or 0) + 1
    revision = BillingPlanRevision(billing_plan_id=plan.id, revision_number=number, contract_id=contract.id, contract_revision_id=contract_revision.id, project_id=project.id if project else None, client_account_id=contract.client_account_id, contract_amount=_contract_amount(contract_revision, contract), currency=str(payload.get("currency") or plan.currency).upper(), valuation_amount=contract_revision.valuation_amount, valuation_currency=contract_revision.valuation_currency, valuation_status=contract_revision.valuation_status, status="DRAFT", supersedes_revision_id=previous.id if previous else None, created_by=_actor(request, payload), source_snapshot={"reason": payload.get("reason"), "contract_billing_context": context})
    db.add(revision); db.flush(); plan.current_revision_id = revision.id; plan.status = "DRAFT"
    _lineage(db, request, project.id if project else None, "BillingPlanRevision", previous.id if previous else contract_revision.id, "BillingPlanRevision", revision.id, "BILLING_PLAN_REVISION_SUPERSEDES")
    _audit(db, request, "BILLING_PLAN_REVISED", "BillingPlanRevision", revision.id, _actor(request, payload), {"supersedes_revision_id": previous.id if previous else None})
    db.commit()
    return _row(revision)


@router.post("/plans/{plan_id}/activate")
def activate_billing_plan(plan_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, OWNER, "BILLING_PLAN_APPROVE")
    plan = db.get(BillingPlan, plan_id)
    if not plan:
        raise HTTPException(404, {"code": "BILLING_PLAN_NOT_FOUND"})
    revision = db.get(BillingPlanRevision, plan.current_revision_id) if plan.current_revision_id else None
    if not revision:
        raise HTTPException(409, {"code": "BILLING_PLAN_REVISION_REQUIRED"})
    activation = db.scalar(select(ProjectActivation).where(ProjectActivation.contract_id == plan.contract_id, ProjectActivation.status == "ACTIVE"))
    policy = str(runtime_decision_value(db, "BILLING_PROJECT_REQUIREMENT_POLICY", "REQUIRED")).upper()
    if not activation and policy in {"REQUIRED", "PROJECT_REQUIRED"}:
        raise HTTPException(409, {"code": "PROJECT_ACTIVATION_REQUIRED", "policy": policy})
    if revision.status not in {"DRAFT", "UNDER_REVIEW", "NEEDS_REVALIDATION"}:
        if plan.status == "ACTIVE":
            return {"plan": _row(plan), "revision": _row(revision)}
        raise HTTPException(409, {"code": "BILLING_PLAN_REVISION_NOT_ACTIVATABLE"})
    if activation:
        plan.project_id = revision.project_id = activation.project_id
    revision.status = "ACTIVE"; revision.approved_by = _actor(request, payload); revision.approved_at = datetime.now(timezone.utc); plan.status = "ACTIVE"; plan.activated_by = _actor(request, payload); plan.activated_at = datetime.now(timezone.utc)
    _audit(db, request, "BILLING_PLAN_ACTIVATED", "BillingPlan", plan.id, _actor(request, payload), {"revision_id": revision.id, "project_id": plan.project_id, "project_policy": policy})
    db.commit()
    return {"plan": _row(plan), "revision": _row(revision)}


@router.post("/plan-revisions/{plan_revision_id}/milestones")
def create_billing_milestone(plan_revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, PLAN_WRITE, "BILLING_MILESTONE_REVIEW")
    plan_revision, plan, contract, contract_revision, project = _plan_revision(db, plan_revision_id)
    if plan_revision.status == "SUPERSEDED" or plan.status == "CANCELLED":
        raise HTTPException(409, {"code": "BILLING_PLAN_REVISION_IMMUTABLE"})
    basis = str(payload.get("basis_type") or "").upper()
    source_term_id = payload.get("source_contract_payment_term_id")
    if source_term_id:
        source_term = db.get(ContractPaymentTerm, source_term_id)
        if not source_term or source_term.contract_id != contract.id or source_term.contract_revision_id != contract_revision.id:
            raise HTTPException(409, {"code": "CONTRACT_PAYMENT_TERM_LINEAGE_MISMATCH"})
    amount = _milestone_amount(db, plan_revision, contract, contract_revision, payload)
    seq = int(payload.get("sequence") or ((db.scalar(select(func.max(BillingMilestone.sequence)).where(BillingMilestone.billing_plan_revision_id == plan_revision.id)) or 0) + 1))
    trigger = str(payload.get("trigger_type") or "MANUAL_EVIDENCE").upper()
    item = BillingMilestone(billing_plan_revision_id=plan_revision.id, sequence=seq, name=str(payload.get("name") or f"Milestone {seq}"), description=payload.get("description"), source_contract_payment_term_id=source_term_id, basis_type=basis, basis_amount=_d(payload["basis_amount"]) if payload.get("basis_amount") is not None else None, percentage=_d(payload["percentage"]) if payload.get("percentage") is not None else None, calculated_amount=amount, currency=plan_revision.currency, trigger_type=trigger, trigger_description=payload.get("trigger_description"), due_days=int(payload["due_days"]) if payload.get("due_days") is not None else None, eligibility_state="WAITING_TRIGGER", remaining_invoiceable_amount=amount, status="DRAFT", created_by=_actor(request, payload), source_snapshot={"contract_revision_id": contract_revision.id, "source_contract_payment_term_id": source_term_id, "reimbursable": False})
    db.add(item); db.flush(); _lineage(db, request, project.id if project else None, "BillingPlanRevision", plan_revision.id, "BillingMilestone", item.id, "BILLING_MILESTONE_FROM_PLAN_REVISION"); _audit(db, request, "BILLING_MILESTONE_CREATED", "BillingMilestone", item.id, _actor(request, payload), {"basis_type": basis, "trigger_type": trigger, "calculated_amount": str(amount) if amount is not None else None}); db.commit()
    return _row(item)


@router.post("/milestones/{milestone_id}/eligibility")
def evaluate_milestone(milestone_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, PLAN_WRITE, "BILLING_MILESTONE_REVIEW")
    item = db.get(BillingMilestone, milestone_id)
    if not item:
        raise HTTPException(404, {"code": "BILLING_MILESTONE_NOT_FOUND"})
    plan_revision, plan, contract, contract_revision, project = _plan_revision(db, item.billing_plan_revision_id)
    trigger = item.trigger_type
    state, reason = "WAITING_TRIGGER", "Required trigger evidence is not present."
    evidence = dict(payload.get("trigger_evidence") or {})
    if payload.get("decision") == "ELIGIBLE" and role in OWNER:
        state, reason = "ELIGIBLE", "Owner recorded the configured trigger evidence."
    elif trigger == "CONTRACT_AUTHORIZED" and contract_revision_is_finalized(contract_revision):
        state, reason = "ELIGIBLE", "Exact ContractRevision is finalized."
    elif trigger == "PROJECT_ACTIVATED" and project:
        state, reason = "ELIGIBLE", "Canonical ProjectActivation exists."
    elif trigger in {"LPO_RECEIVED", "MANUAL_EVIDENCE", "PERMIT_APPROVED", "DELIVERABLE_ACCEPTED", "HANDOVER_ACCEPTED", "DATE_REACHED", "OTHER"} and evidence.get("document_version_id"):
        version = db.get(DocumentVersion, evidence["document_version_id"]); document = db.get(Document, version.document_id) if version else None
        if not version or not document or (project and document.project_id not in {None, project.id}):
            raise HTTPException(403, {"code": "TRIGGER_EVIDENCE_PROJECT_MISMATCH"})
        state, reason = "ELIGIBLE", "Exact trigger evidence is pinned."
    item.eligibility_state = state; item.status = "READY" if state == "ELIGIBLE" else "DRAFT"
    record = BillingMilestoneEligibility(billing_milestone_id=item.id, state=state, evaluated_by=_actor(request, payload), reason=reason, trigger_evidence=evidence)
    db.add(record); db.flush(); _audit(db, request, "BILLING_MILESTONE_ELIGIBILITY_EVALUATED", "BillingMilestoneEligibility", record.id, _actor(request, payload), {"milestone_id": item.id, "state": state, "reason": reason}); db.commit()
    return {"milestone": _row(item), "eligibility": _row(record)}


@router.post("/invoices")
def create_invoice(payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, PLAN_WRITE, "INVOICE_CREATE")
    ids = [str(x) for x in (payload.get("milestone_ids") or [])]
    if not ids:
        raise HTTPException(409, {"code": "BILLING_MILESTONE_REQUIRED", "manual_invoice_disabled": True})
    milestones = [db.get(BillingMilestone, item) for item in ids]
    if any(item is None for item in milestones):
        raise HTTPException(404, {"code": "BILLING_MILESTONE_NOT_FOUND"})
    plan_revision, plan, contract, contract_revision, project = _plan_revision(db, milestones[0].billing_plan_revision_id)
    if any(item.billing_plan_revision_id != plan_revision.id or item.eligibility_state != "ELIGIBLE" for item in milestones):
        raise HTTPException(409, {"code": "ELIGIBLE_MILESTONES_REQUIRED"})
    if plan.status != "ACTIVE" or plan_revision.status != "ACTIVE":
        raise HTTPException(409, {"code": "ACTIVE_BILLING_PLAN_REQUIRED"})
    invoice_id = str(uuid4())
    invoice = Invoice(id=invoice_id, contract_id=contract.id, project_id=project.id if project else None, client_account_id=contract.client_account_id, billing_plan_id=plan.id, invoice_reference=f"DRAFT-{invoice_id[:12].upper()}", invoice_ref_status="NOT_ALLOCATED", status="DRAFT", requirement_decision_id=None)
    db.add(invoice); db.flush()
    invoice_date = _date(payload.get("invoice_date") or date.today().isoformat(), field="invoice_date")
    if payload.get("due_date") and role not in OWNER:
        raise HTTPException(403, {"code": "DUE_DATE_OVERRIDE_OWNER_ONLY"})
    due_date = _date(payload["due_date"], field="due_date") if payload.get("due_date") else None
    due_days = [item.due_days for item in milestones if item.due_days is not None]
    if due_date is None and due_days and len(set(due_days)) == 1:
        due_date = invoice_date + timedelta(days=due_days[0])
    revision = InvoiceRevision(invoice_id=invoice.id, revision_number=1, controlling_contract_revision_id=contract_revision.id, billing_plan_revision_id=plan_revision.id, status="DRAFT", invoice_date=invoice_date, due_date=due_date, due_date_basis=f"DUE_DAYS:{due_days[0]}" if due_days and len(set(due_days)) == 1 else "HUMAN_ENTERED" if due_date else None, description=payload.get("description") or "Billing milestone invoice", currency=plan_revision.currency, source_snapshot={"contract_id": contract.id, "contract_revision_id": contract_revision.id, "billing_plan_revision_id": plan_revision.id, "milestone_ids": ids, "client_account_id": contract.client_account_id, "project_id": project.id if project else None})
    db.add(revision); db.flush(); invoice.current_revision_id = revision.id
    sequence = 1
    for item in milestones:
        amount = _money(_d(item.remaining_invoiceable_amount or item.calculated_amount or 0))
        if amount <= 0:
            raise HTTPException(409, {"code": "MILESTONE_NO_REMAINING_INVOICEABLE_AMOUNT", "milestone_id": item.id})
        db.add(InvoiceLineItem(invoice_revision_id=revision.id, sequence=sequence, line_role="CHARGE", item_code=item.name, description=item.description or item.name, quantity=Decimal("1"), unit="LOT", unit_price=amount, currency=item.currency, calculated_line_amount=amount, billing_milestone_id=item.id, affects_payable_total=True, source_reference=item.id)); sequence += 1
    for info in payload.get("informational_lines") or []:
        db.add(InvoiceLineItem(invoice_revision_id=revision.id, sequence=sequence, line_role="INFORMATION", item_code=info.get("item_code"), description=str(info.get("description") or "Information"), quantity=_d(info["quantity"], field="quantity") if info.get("quantity") is not None else None, unit=info.get("unit"), unit_price=_d(info["unit_price"], field="unit_price") if info.get("unit_price") is not None else None, currency=plan_revision.currency, calculated_line_amount=Decimal("0.00"), affects_payable_total=False, source_reference=info.get("source_reference"))); sequence += 1
    _calculate_revision(db, revision)
    _lineage(db, request, project.id if project else None, "BillingPlanRevision", plan_revision.id, "InvoiceRevision", revision.id, "INVOICE_DERIVED_FROM_BILLING_PLAN")
    _audit(db, request, "INVOICE_CREATED", "Invoice", invoice.id, _actor(request, payload), {"invoice_revision_id": revision.id, "billing_plan_revision_id": plan_revision.id, "official_reference_allocated": False})
    db.commit()
    return {"invoice": _row(invoice), "revision": _row(revision), "lines": [_row(x) for x in _lines(db, revision.id)]}


def _calculate_revision(db: Session, revision: InvoiceRevision) -> InvoiceRevision:
    db.flush()
    lines = _lines(db, revision.id)
    gross = sum((_line_total(x) for x in lines if x.line_role == "CHARGE" and x.affects_payable_total), Decimal("0"))
    adjustments = sum((_line_total(x) for x in lines if x.line_role == "ADJUSTMENT" and x.affects_payable_total), Decimal("0"))
    revision.gross_charge_total = _money(gross); revision.adjustment_total = _money(adjustments); revision.payable_total = _money(gross + adjustments); revision.amount_in_words = _amount_in_words(revision.payable_total, revision.currency or "QAR")
    return revision


@router.get("/invoices")
def list_invoices(project_id: str | None = None, contract_id: str | None = None, lane: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, VIEW, "BILLING_VIEW")
    query = select(Invoice).order_by(Invoice.created_at.desc())
    if project_id: query = query.where(Invoice.project_id == project_id)
    if contract_id: query = query.where(Invoice.contract_id == contract_id)
    rows = db.scalars(query).all()
    items = []
    for invoice in rows:
        revision = db.get(InvoiceRevision, invoice.current_revision_id) if invoice.current_revision_id else None
        receivable = _receivable(db, invoice, revision) if revision else {"state": "NOT_ISSUED", "outstanding": None}
        stage = "AUTHORITY_REVIEW" if invoice.status in {"ACCEPTED_INTERNAL", "FINANCE_REVIEW"} else "READY_CLOSE" if invoice.status == "ISSUED" else "NEED_ACTION" if invoice.status in {"DRAFT", "NEEDS_REVALIDATION"} else "ALL"
        if lane and lane not in {"ALL", stage, receivable.get("state")}:
            continue
        items.append({"invoice": _row(invoice), "revision": _row(revision), "stage": stage, "receivable": receivable})
    return {"items": items, "total": len(items), "lanes": {"all": len(rows), "need_action": sum(x["stage"] == "NEED_ACTION" for x in items), "authority_review": sum(x["stage"] == "AUTHORITY_REVIEW" for x in items), "ready_close": sum(x["stage"] == "READY_CLOSE" for x in items)}}


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, VIEW, "BILLING_VIEW")
    invoice, contract, revision, plan_revision, project = _invoice_revision(db, invoice_id)
    references = db.scalars(select(InvoiceReference).where(InvoiceReference.invoice_revision_id == revision.id)).all()
    approvals = db.scalars(select(InvoiceApprovalRecord).where(InvoiceApprovalRecord.invoice_revision_id == revision.id)).all()
    issue = db.scalar(select(InvoiceIssueEvent).where(InvoiceIssueEvent.invoice_id == invoice.id))
    artifact = db.get(RenderedArtifact, issue.rendered_artifact_id) if issue else None
    return {"invoice": _row(invoice), "contract": _row(contract), "project": _row(project), "revision": _row(revision), "lines": [_row(x) for x in _lines(db, revision.id)], "references": [_row(x) for x in references], "approvals": [_row(x) for x in approvals], "issue": _row(issue), "artifact": _row(artifact), "receivable": _receivable(db, invoice, revision), "settlement": "DEFERRED_TO_FINANCIAL_SETTLEMENT"}


@router.post("/invoices/{invoice_id}/revisions")
def create_invoice_revision(invoice_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, PLAN_WRITE, "INVOICE_EDIT_DRAFT")
    invoice, contract, previous, plan_revision, project = _invoice_revision(db, invoice_id)
    if invoice.status in {"ISSUED", "VOIDED"} or previous.status in {"ACCEPTED_INTERNAL", "ISSUED"}:
        raise HTTPException(409, {"code": "ISSUED_OR_ACCEPTED_INVOICE_IMMUTABLE"})
    if not plan_revision:
        raise HTTPException(409, {"code": "BILLING_PLAN_REVISION_REQUIRED"})
    number = (db.scalar(select(func.max(InvoiceRevision.revision_number)).where(InvoiceRevision.invoice_id == invoice.id)) or 0) + 1
    next_revision = InvoiceRevision(invoice_id=invoice.id, revision_number=number, controlling_contract_revision_id=previous.controlling_contract_revision_id, billing_plan_revision_id=previous.billing_plan_revision_id, status="DRAFT", supersedes_revision_id=previous.id, invoice_date=_date(payload.get("invoice_date") or previous.invoice_date or date.today().isoformat(), field="invoice_date"), due_date=_date(payload["due_date"], field="due_date") if payload.get("due_date") else previous.due_date, due_date_basis=previous.due_date_basis, description=payload.get("description") or previous.description, currency=previous.currency, source_snapshot={**(previous.source_snapshot or {}), "supersedes_revision_id": previous.id, "reason": payload.get("reason")})
    db.add(next_revision); db.flush()
    prior_lines = _lines(db, previous.id)
    for line in prior_lines:
        db.add(InvoiceLineItem(invoice_revision_id=next_revision.id, sequence=line.sequence, line_role=line.line_role, item_code=line.item_code, description=line.description, quantity=line.quantity, unit=line.unit, unit_price=line.unit_price, currency=line.currency, calculated_line_amount=line.calculated_line_amount, billing_milestone_id=line.billing_milestone_id, affects_payable_total=line.affects_payable_total, source_reference=line.source_reference))
    invoice.current_revision_id = next_revision.id; invoice.status = "DRAFT"; _calculate_revision(db, next_revision); _audit(db, request, "INVOICE_REVISION_CREATED", "InvoiceRevision", next_revision.id, _actor(request, payload), {"supersedes_revision_id": previous.id}); db.commit()
    return {"invoice": _row(invoice), "revision": _row(next_revision), "lines": [_row(x) for x in _lines(db, next_revision.id)]}


@router.post("/invoice-revisions/{revision_id}/calculate")
def calculate_invoice(revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, PLAN_WRITE, "INVOICE_EDIT_DRAFT")
    revision = db.get(InvoiceRevision, revision_id)
    if not revision or revision.status in {"ACCEPTED_INTERNAL", "ISSUED"}:
        raise HTTPException(409, {"code": "INVOICE_REVISION_IMMUTABLE"})
    if payload.get("lines") is not None:
        for line in _lines(db, revision.id): db.delete(line)
        db.flush()
        for index, value in enumerate(payload["lines"], 1):
            role_name = str(value.get("line_role") or "CHARGE").upper()
            if role_name == "ADJUSTMENT" and not bool(runtime_decision_value(db, "BILLING_ADJUSTMENTS_ENABLED", False)):
                raise HTTPException(409, {"code": "ADJUSTMENTS_NOT_ENABLED"})
            milestone = db.get(BillingMilestone, value.get("billing_milestone_id")) if value.get("billing_milestone_id") else None
            amount = _money(_d(value.get("calculated_line_amount"), field="calculated_line_amount")) if value.get("calculated_line_amount") is not None else _money(_d(value.get("quantity", 1), field="quantity") * _d(value.get("unit_price", 0), field="unit_price"))
            if milestone:
                amount = _money(_d(milestone.remaining_invoiceable_amount or 0))
            if amount < 0:
                raise HTTPException(409, {"code": "NEGATIVE_INVOICE_LINE_DISABLED"})
            if str(value.get("currency") or revision.currency).upper() != str(revision.currency).upper():
                raise HTTPException(409, {"code": "CURRENCY_MISMATCH"})
            db.add(InvoiceLineItem(invoice_revision_id=revision.id, sequence=index, line_role=role_name, item_code=value.get("item_code"), description=str(value.get("description") or "Invoice line"), quantity=_d(value["quantity"], field="quantity") if value.get("quantity") is not None else None, unit=value.get("unit"), unit_price=_d(value["unit_price"], field="unit_price") if value.get("unit_price") is not None else None, currency=str(value.get("currency") or revision.currency).upper(), calculated_line_amount=amount, billing_milestone_id=milestone.id if milestone else None, affects_payable_total=role_name != "INFORMATION", source_reference=value.get("source_reference")))
    _calculate_revision(db, revision); _audit(db, request, "INVOICE_AMOUNT_CALCULATED", "InvoiceRevision", revision.id, _actor(request, payload), {"gross_charge_total": str(revision.gross_charge_total), "payable_total": str(revision.payable_total)}); db.commit()
    return {"revision": _row(revision), "lines": [_row(x) for x in _lines(db, revision.id)]}


@router.post("/invoice-revisions/{revision_id}/references")
def add_invoice_reference(revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, PLAN_WRITE, "INVOICE_REFERENCE_MANAGE")
    revision = db.get(InvoiceRevision, revision_id)
    if not revision or revision.status in {"ISSUED"}:
        raise HTTPException(409, {"code": "INVOICE_REVISION_IMMUTABLE"})
    value = str(payload.get("value") or "").strip(); reference_type = str(payload.get("reference_type") or "").strip().upper()
    if not value or not reference_type:
        raise HTTPException(422, {"code": "TYPED_REFERENCE_REQUIRED"})
    item = InvoiceReference(invoice_revision_id=revision.id, reference_type=reference_type, value=value, issuer_or_source=payload.get("issuer_or_source"), issued_at=datetime.fromisoformat(payload["issued_at"]) if payload.get("issued_at") else None, source_document_version_id=payload.get("source_document_version_id"), status=str(payload.get("status") or "PENDING_VERIFICATION").upper(), notes=payload.get("notes"))
    db.add(item); db.flush(); _audit(db, request, "INVOICE_REFERENCE_RECORDED", "InvoiceReference", item.id, _actor(request, payload), {"invoice_revision_id": revision.id, "reference_type": reference_type}); db.commit(); return _row(item)


@router.post("/invoice-revisions/{revision_id}/approvals")
def add_invoice_approval(revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, PLAN_WRITE, "INVOICE_APPROVAL_VERIFY")
    revision = db.get(InvoiceRevision, revision_id)
    if not revision or revision.status == "ISSUED": raise HTTPException(409, {"code": "INVOICE_REVISION_IMMUTABLE"})
    item = InvoiceApprovalRecord(invoice_revision_id=revision.id, approval_type=str(payload.get("approval_type") or "CONFIGURED_APPROVAL"), status=str(payload.get("status") or "PENDING").upper(), approval_reference=payload.get("approval_reference"), approving_party_or_body=payload.get("approving_party_or_body"), decision_date=_date(payload["decision_date"], field="decision_date") if payload.get("decision_date") else None, source_document_version_id=payload.get("source_document_version_id"), notes=payload.get("notes"), verified_by=_actor(request, payload) if str(payload.get("status") or "").upper() == "VERIFIED" else None, verified_at=datetime.now(timezone.utc) if str(payload.get("status") or "").upper() == "VERIFIED" else None)
    db.add(item); db.flush(); _audit(db, request, "INVOICE_APPROVAL_REFERENCE_RECORDED", "InvoiceApprovalRecord", item.id, _actor(request, payload), {"approval_type": item.approval_type, "status": item.status}); db.commit(); return _row(item)


@router.post("/invoice-revisions/{revision_id}/accept")
def accept_invoice(revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, OWNER, "INVOICE_ACCEPT")
    invoice, contract, revision, plan_revision, project = _invoice_revision(db, str(payload.get("invoice_id") or ""), revision_id) if payload.get("invoice_id") else (None, None, db.get(InvoiceRevision, revision_id), None, None)
    if invoice is None:
        if not revision: raise HTTPException(404, {"code": "INVOICE_REVISION_NOT_FOUND"})
        invoice, contract, revision, plan_revision, project = _invoice_revision(db, revision.invoice_id, revision.id)
    if revision.status == "ACCEPTED_INTERNAL":
        existing = db.scalar(select(InvoiceAcceptRecord).where(InvoiceAcceptRecord.invoice_revision_id == revision.id)); return {"invoice": _row(invoice), "revision": _row(revision), "accept": _row(existing)}
    if revision.status in {"ISSUED", "CANCELLED"}: raise HTTPException(409, {"code": "INVOICE_REVISION_NOT_ACCEPTABLE"})
    precheck = _precheck(db, invoice, contract, revision, plan_revision)
    if precheck["result"] != "PASS": raise HTTPException(409, {"code": "INVOICE_ACCEPT_PRECHECK_BLOCKED", "precheck": precheck})
    key = str(payload.get("idempotency_key") or "").strip()
    if not key: raise HTTPException(422, {"code": "ACCEPT_IDEMPOTENCY_KEY_REQUIRED"})
    prior = db.scalar(select(InvoiceAcceptRecord).where(InvoiceAcceptRecord.idempotency_key == key))
    if prior: return {"invoice": _row(invoice), "revision": _row(revision), "accept": _row(prior), "precheck": precheck}
    accepted = InvoiceAcceptRecord(invoice_revision_id=revision.id, accepted_by=_actor(request, payload), accepted_role=role.value, idempotency_key=key, precheck_snapshot=precheck); db.add(accepted); db.flush(); revision.status = "ACCEPTED_INTERNAL"; revision.accepted_by = _actor(request, payload); revision.accepted_at = datetime.now(timezone.utc); invoice.status = "ACCEPTED_INTERNAL"; _audit(db, request, "INVOICE_ACCEPTED_INTERNAL", "InvoiceAcceptRecord", accepted.id, _actor(request, payload), {"invoice_revision_id": revision.id, "invoice_id": invoice.id}); db.commit(); return {"invoice": _row(invoice), "revision": _row(revision), "accept": _row(accepted), "precheck": precheck}


@router.post("/financial-accounts")
def create_financial_account(payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, OWNER, "FINANCIAL_ACCOUNT_MANAGE")
    item = FinancialAccountMaster(legal_entity_party_id=payload.get("legal_entity_party_id"), legal_entity_ref=str(payload.get("legal_entity_ref") or "").strip(), account_name=str(payload.get("account_name") or "").strip(), status="DRAFT", created_by=_actor(request, payload))
    if not item.legal_entity_ref or not item.account_name: raise HTTPException(422, {"code": "LEGAL_ENTITY_AND_ACCOUNT_NAME_REQUIRED"})
    db.add(item); db.flush(); _audit(db, request, "FINANCIAL_ACCOUNT_MASTER_CREATED", "FinancialAccountMaster", item.id, _actor(request, payload), {"legal_entity_ref": item.legal_entity_ref, "status": item.status}); db.commit(); return _row(item)


@router.post("/financial-accounts/{master_id}/versions")
def create_financial_account_version(master_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, OWNER, "FINANCIAL_ACCOUNT_MANAGE")
    master = db.get(FinancialAccountMaster, master_id)
    if not master: raise HTTPException(404, {"code": "FINANCIAL_ACCOUNT_MASTER_NOT_FOUND"})
    version_number = (db.scalar(select(func.max(FinancialAccountVersion.version_number)).where(FinancialAccountVersion.financial_account_master_id == master.id)) or 0) + 1
    item = FinancialAccountVersion(financial_account_master_id=master.id, version_number=version_number, bank_name=str(payload.get("bank_name") or ""), account_name=str(payload.get("account_name") or master.account_name), account_reference=str(payload.get("account_reference") or ""), currency=str(payload.get("currency") or "").upper(), effective_from=_date(payload.get("effective_from") or date.today().isoformat(), field="effective_from"), effective_to=_date(payload["effective_to"], field="effective_to") if payload.get("effective_to") else None, status="DRAFT", payment_instruction_metadata=payload.get("payment_instruction_metadata") or {}, created_by=_actor(request, payload))
    if not item.bank_name or not item.account_reference or not item.currency: raise HTTPException(422, {"code": "FINANCIAL_ACCOUNT_FIELDS_REQUIRED"})
    db.add(item); db.flush(); _audit(db, request, "FINANCIAL_ACCOUNT_VERSION_CREATED", "FinancialAccountVersion", item.id, _actor(request, payload), {"master_id": master.id, "version_number": item.version_number, "currency": item.currency}); db.commit(); return _mask_account(item)


@router.post("/financial-account-versions/{version_id}/approve")
def approve_financial_account_version(version_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, OWNER, "FINANCIAL_ACCOUNT_APPROVE")
    item = db.get(FinancialAccountVersion, version_id)
    if not item: raise HTTPException(404, {"code": "FINANCIAL_ACCOUNT_VERSION_NOT_FOUND"})
    master = db.get(FinancialAccountMaster, item.financial_account_master_id)
    if not master: raise HTTPException(409, {"code": "FINANCIAL_ACCOUNT_MASTER_NOT_FOUND"})
    item.status = "ACTIVE"; item.approved_by = _actor(request, payload); item.approved_at = datetime.now(timezone.utc); master.status = "ACTIVE"; _audit(db, request, "FINANCIAL_ACCOUNT_VERSION_APPROVED", "FinancialAccountVersion", item.id, _actor(request, payload), {"master_id": master.id, "version_number": item.version_number, "currency": item.currency}); db.commit(); return _mask_account(item)


@router.post("/invoice-revisions/{revision_id}/issue")
def issue_invoice(revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, OWNER, "INVOICE_ISSUE")
    revision = db.get(InvoiceRevision, revision_id)
    if not revision: raise HTTPException(404, {"code": "INVOICE_REVISION_NOT_FOUND"})
    invoice, contract, revision, plan_revision, project = _invoice_revision(db, revision.invoice_id, revision.id)
    key = str(payload.get("idempotency_key") or "").strip()
    if not key: raise HTTPException(422, {"code": "ISSUE_IDEMPOTENCY_KEY_REQUIRED"})
    prior = db.scalar(select(InvoiceIssueEvent).where(InvoiceIssueEvent.idempotency_key == key))
    if prior: return {"invoice": _row(invoice), "revision": _row(revision), "issue": _row(prior)}
    existing = db.scalar(select(InvoiceIssueEvent).where(InvoiceIssueEvent.invoice_id == invoice.id))
    if existing: raise HTTPException(409, {"code": "INVOICE_ALREADY_ISSUED", "issue_event_id": existing.id})
    if revision.status != "ACCEPTED_INTERNAL": raise HTTPException(409, {"code": "INVOICE_ACCEPT_REQUIRED"})
    precheck = _precheck(db, invoice, contract, revision, plan_revision)
    if precheck["result"] != "PASS": raise HTTPException(409, {"code": "INVOICE_ISSUE_PRECHECK_BLOCKED", "precheck": precheck})
    issue_date = revision.invoice_date or date.today()
    account = _resolve_account(db, revision.currency or plan_revision.currency, issue_date, payload.get("financial_account_version_id"))
    template = select_template(db, payload.get("template_version_id"), "INVOICE")
    official_ref = _allocate_invoice_ref(db, issue_date, _actor(request, payload))
    artifact = render_artifact(db, artifact_type="INVOICE", context_type="INVOICE_REVISION", context_id=revision.id, payload={"invoice_reference": official_ref, "contract_reference": contract.contract_reference, "client_account_id": contract.client_account_id, "project_id": project.id if project else None, "description": revision.description, "currency": revision.currency, "lines": [_row(x) for x in _lines(db, revision.id)], "gross_charge_total": str(revision.gross_charge_total), "payable_total": str(revision.payable_total), "amount_in_words": revision.amount_in_words, "invoice_date": issue_date.isoformat(), "due_date": revision.due_date.isoformat() if revision.due_date else None, "financial_account_version_id": account.id, "source_sample_policy": "REFERENCE_ONLY"}, source_revision_ids=[contract.id, revision.controlling_contract_revision_id, plan_revision.id if plan_revision else revision.id], template_version_id=template.id, actor=_actor(request, payload), correlation_id=_corr(request), project_id=project.id if project else None)
    event = InvoiceIssueEvent(invoice_id=invoice.id, invoice_revision_id=revision.id, official_invoice_ref=official_ref, invoice_date=issue_date, issued_by=_actor(request, payload), idempotency_key=key, template_version_id=template.id, financial_account_version_id=account.id, rendered_artifact_id=artifact.id, source_snapshot={"contract_revision_id": revision.controlling_contract_revision_id, "billing_plan_revision_id": revision.billing_plan_revision_id, "financial_account_version_id": account.id, "template_version_id": template.id, "artifact_id": artifact.id})
    db.add(event); db.flush(); invoice.invoice_reference = official_ref; invoice.invoice_ref_status = "ALLOCATED"; invoice.status = "ISSUED"; revision.status = "ISSUED"
    for line in _lines(db, revision.id):
        if line.billing_milestone_id and line.affects_payable_total:
            milestone = db.get(BillingMilestone, line.billing_milestone_id); milestone.invoiced_amount = _money(_d(milestone.invoiced_amount or 0) + _line_total(line)); milestone.remaining_invoiceable_amount = _money(max(Decimal("0"), _d(milestone.calculated_amount or 0) - _d(milestone.invoiced_amount or 0)));
    _lineage(db, request, project.id if project else None, "InvoiceIssueEvent", event.id, "RenderedArtifact", artifact.id, "ISSUED_INVOICE_ARTIFACT"); _audit(db, request, "INVOICE_ISSUED", "InvoiceIssueEvent", event.id, _actor(request, payload), {"invoice_id": invoice.id, "official_invoice_ref": official_ref, "template_version_id": template.id, "financial_account_version_id": account.id, "artifact_id": artifact.id}); db.commit()
    return {"invoice": _row(invoice), "revision": _row(revision), "issue": _row(event), "artifact": _row(artifact), "financial_account": _mask_account(account)}


def _allocate_invoice_ref(db: Session, issue_date: date, actor: str) -> str:
    policy = db.scalar(select(InvoiceNumberingPolicy).where(InvoiceNumberingPolicy.policy_key == "INVOICE" ).with_for_update())
    if not policy:
        policy = InvoiceNumberingPolicy(policy_key="INVOICE", prefix="INV-AMEC", padding=6, next_number=1, version="V1", status="ACTIVE", no_reuse=True, updated_by=actor); db.add(policy); db.flush()
    if policy.status != "ACTIVE": raise HTTPException(409, {"code": "INVOICE_NUMBERING_POLICY_INACTIVE"})
    value = f"{policy.prefix}-{issue_date.year}-{policy.next_number:0{policy.padding}d}"; policy.next_number += 1; policy.updated_by = actor; return value


def _receivable(db: Session, invoice: Invoice, revision: InvoiceRevision | None) -> dict[str, Any]:
    if not revision or invoice.status != "ISSUED": return {"state": "NOT_ISSUED", "issued_payable_amount": None, "verified_paid_amount": "0.00", "outstanding_amount": None, "overpayment_amount": "0.00"}
    paid = sum((_d(item.allocated_amount) for item in db.scalars(select(InvoicePaymentAllocation).where(InvoicePaymentAllocation.invoice_id == invoice.id, InvoicePaymentAllocation.status == "ALLOCATED")).all()), Decimal("0"))
    payable = _d(revision.payable_total or 0); outstanding = payable - paid; over = max(Decimal("0"), -outstanding); now = date.today()
    state = "PAID" if outstanding <= 0 else "PARTIALLY_PAID" if paid > 0 else "OVERDUE" if revision.due_date and revision.due_date < now else "DUE" if revision.due_date and revision.due_date <= now else "NOT_DUE"
    return {"state": state, "issued_payable_amount": str(_money(payable)), "verified_paid_amount": str(_money(paid)), "outstanding_amount": str(_money(max(Decimal("0"), outstanding))), "overpayment_amount": str(_money(over)), "due_date": revision.due_date.isoformat() if revision.due_date else None}


@router.get("/invoices/{invoice_id}/receivable")
def invoice_receivable(invoice_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, VIEW, "BILLING_VIEW")
    invoice, _contract, revision, _plan_revision, _project = _invoice_revision(db, invoice_id)
    return _receivable(db, invoice, revision)


@router.post("/payments")
def record_payment(payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, PLAN_WRITE, "PAYMENT_RECORD")
    invoice = db.get(Invoice, payload.get("invoice_id")) if payload.get("invoice_id") else None
    contract_id = str(payload.get("contract_id") or (invoice.contract_id if invoice else ""))
    contract, _contract_revision, _context, project = _contract_context(db, contract_id, None)
    client_id = str(payload.get("client_account_id") or (invoice.client_account_id if invoice else contract.client_account_id))
    if client_id != contract.client_account_id: raise HTTPException(403, {"code": "PAYMENT_CLIENT_CONTRACT_MISMATCH"})
    payment_project_id = payload.get("project_id") or (invoice.project_id if invoice else project.id if project else None); _scope_project(db, payment_project_id, contract, project)
    amount = _money(_d(payload.get("amount"), field="amount")); currency = str(payload.get("currency") or contract.currency or "").upper()
    if amount <= 0 or not currency: raise HTTPException(422, {"code": "PAYMENT_AMOUNT_CURRENCY_REQUIRED"})
    evidence_id = payload.get("evidence_document_version_id")
    if evidence_id:
        version = db.get(DocumentVersion, evidence_id); document = db.get(Document, version.document_id) if version else None
        if not version or not document or (project and document.project_id not in {None, project.id}): raise HTTPException(403, {"code": "PAYMENT_EVIDENCE_PROJECT_MISMATCH"})
    key = str(payload.get("idempotency_key") or "").strip()
    if not key: raise HTTPException(422, {"code": "PAYMENT_IDEMPOTENCY_KEY_REQUIRED"})
    existing = db.scalar(select(PaymentReceipt).where(PaymentReceipt.idempotency_key == key))
    if existing: return _row(existing)
    item = PaymentReceipt(client_account_id=client_id, contract_id=contract.id, project_id=payment_project_id, received_date=_date(payload.get("received_date") or date.today().isoformat(), field="received_date"), amount=amount, currency=currency, reference=str(payload.get("reference") or "").strip(), payment_method=payload.get("payment_method"), evidence_document_version_id=evidence_id, verification_status="OBSERVED", recorded_by=_actor(request, payload), notes=payload.get("notes"), idempotency_key=key)
    if not item.reference: raise HTTPException(422, {"code": "PAYMENT_REFERENCE_REQUIRED"})
    db.add(item); db.flush(); _audit(db, request, "PAYMENT_RECEIPT_RECORDED", "PaymentReceipt", item.id, _actor(request, payload), {"contract_id": contract.id, "project_id": payment_project_id, "amount": str(amount), "currency": currency, "verification_status": item.verification_status}); db.commit(); return _row(item)


@router.post("/payments/{payment_id}/verify")
def verify_payment(payment_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, OWNER, "PAYMENT_VERIFY")
    item = db.get(PaymentReceipt, payment_id)
    if not item: raise HTTPException(404, {"code": "PAYMENT_NOT_FOUND"})
    if item.verification_status == "VERIFIED": return _row(item)
    if item.verification_status == "REVERSED": raise HTTPException(409, {"code": "PAYMENT_REVERSED"})
    item.verification_status = "VERIFIED"; item.verified_by = _actor(request, payload); item.verified_at = datetime.now(timezone.utc); _audit(db, request, "PAYMENT_RECEIPT_VERIFIED", "PaymentReceipt", item.id, _actor(request, payload), {"verification_status": item.verification_status}); db.commit(); return _row(item)


@router.post("/payments/{payment_id}/allocate")
def allocate_payment(payment_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, OWNER, "PAYMENT_ALLOCATE")
    payment = db.get(PaymentReceipt, payment_id); invoice = db.get(Invoice, payload.get("invoice_id"))
    if not payment or not invoice: raise HTTPException(404, {"code": "PAYMENT_OR_INVOICE_NOT_FOUND"})
    if payment.verification_status != "VERIFIED": raise HTTPException(409, {"code": "VERIFIED_PAYMENT_REQUIRED"})
    if invoice.status != "ISSUED": raise HTTPException(409, {"code": "ISSUED_INVOICE_REQUIRED"})
    key = str(payload.get("idempotency_key") or "").strip()
    if not key: raise HTTPException(422, {"code": "ALLOCATION_IDEMPOTENCY_KEY_REQUIRED"})
    existing = db.scalar(select(InvoicePaymentAllocation).where(InvoicePaymentAllocation.idempotency_key == key))
    if existing: return _row(existing)
    revision = db.get(InvoiceRevision, invoice.current_revision_id)
    if not revision or payment.currency.upper() != str(revision.currency).upper(): raise HTTPException(409, {"code": "PAYMENT_CURRENCY_MISMATCH"})
    amount = _money(_d(payload.get("allocated_amount"), field="allocated_amount")); used = sum((_d(x.allocated_amount) for x in db.scalars(select(InvoicePaymentAllocation).where(InvoicePaymentAllocation.payment_receipt_id == payment.id, InvoicePaymentAllocation.status == "ALLOCATED")).all()), Decimal("0")); receivable = _receivable(db, invoice, revision); outstanding = _d(receivable["outstanding_amount"] or 0)
    if amount <= 0 or used + amount > _d(payment.amount) or amount > outstanding: raise HTTPException(409, {"code": "PAYMENT_ALLOCATION_OVER_LIMIT", "unallocated_payment": str(_d(payment.amount) - used), "outstanding": str(outstanding)})
    allocation = InvoicePaymentAllocation(payment_receipt_id=payment.id, invoice_id=invoice.id, allocated_amount=amount, currency=payment.currency, allocated_by=_actor(request, payload), idempotency_key=key); db.add(allocation); db.flush(); _lineage(db, request, invoice.project_id, "PaymentReceipt", payment.id, "InvoicePaymentAllocation", allocation.id, "VERIFIED_PAYMENT_ALLOCATION"); _audit(db, request, "PAYMENT_ALLOCATED", "InvoicePaymentAllocation", allocation.id, _actor(request, payload), {"payment_id": payment.id, "invoice_id": invoice.id, "allocated_amount": str(amount), "currency": payment.currency}); db.commit(); return {"allocation": _row(allocation), "receivable": _receivable(db, invoice, revision)}


@router.post("/invoices/{invoice_id}/follow-ups")
def record_follow_up(invoice_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, PLAN_WRITE, "RECEIVABLE_FOLLOW_UP")
    invoice = db.get(Invoice, invoice_id)
    if not invoice: raise HTTPException(404, {"code": "INVOICE_NOT_FOUND"})
    item = ReceivableFollowUp(invoice_id=invoice.id, follow_up_date=_date(payload.get("follow_up_date") or date.today().isoformat(), field="follow_up_date"), channel=str(payload.get("channel") or "INTERNAL_NOTE"), contact_party_id=payload.get("contact_party_id"), note=str(payload.get("note") or "").strip(), outcome=payload.get("outcome"), next_follow_up_at=datetime.fromisoformat(payload["next_follow_up_at"]) if payload.get("next_follow_up_at") else None, recorded_by=_actor(request, payload))
    if not item.note: raise HTTPException(422, {"code": "FOLLOW_UP_NOTE_REQUIRED"})
    db.add(item); db.flush(); _audit(db, request, "RECEIVABLE_FOLLOW_UP_RECORDED", "ReceivableFollowUp", item.id, _actor(request, payload), {"invoice_id": invoice.id, "channel": item.channel, "payment_status_unchanged": True}); db.commit(); return _row(item)


@router.get("/invoices/{invoice_id}/download")
def download_invoice(invoice_id: str, db: Session = Depends(get_db), role: Role = Depends(current_user_role)):
    _role(role, VIEW, "INVOICE_EXPORT")
    invoice = db.get(Invoice, invoice_id); issue = db.scalar(select(InvoiceIssueEvent).where(InvoiceIssueEvent.invoice_id == invoice_id)) if invoice else None
    if not invoice: raise HTTPException(404, {"code": "INVOICE_NOT_FOUND"})
    if not issue: raise HTTPException(409, {"code": "ISSUED_INVOICE_ARTIFACT_REQUIRED"})
    artifact = db.get(RenderedArtifact, issue.rendered_artifact_id)
    return {"invoice_id": invoice.id, "invoice_reference": issue.official_invoice_ref, "artifact": _row(artifact), "download_policy": "EXACT_ISSUED_ARTIFACT"}
