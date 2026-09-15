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
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.orm import Session

from ..api.dependencies import current_user_role
from ..audit.service import audit
from ..db import get_db
from ..expansion.runtime import render_artifact, select_template
from ..models import (
    BillingMilestone, BillingMilestoneEligibility, BillingPlan, BillingPlanRevision, BillingReadinessRequest,
    ClientAccount, ConsultancyOffice, Contract, ContractAdminEvidence, ContractPaymentTerm,
    ContractRevision, Document, DocumentVersion, FinancialAccountMaster, RenderedArtifact,
    FinancialAccountVersion, Invoice, InvoiceAcceptRecord, InvoiceApprovalRecord, InvoiceRevision,
    InvoiceIssueEvent, InvoiceDeliveryEvent, InvoiceAcknowledgment, InvoiceLineItem, InvoiceNumberingPolicy, InvoicePaymentAllocation,
    InvoiceReference, LineageEdge, PaymentReceipt, Project, ProjectActivation,
    PaymentReversalEvent, ReceivableFollowUp, ReceivableResolution, BillingFxRateRecord, ProjectExpectedExpVersion, Role, TemplateDefinition, TemplateVersion,
    User, GovernedSignatoryAuthority,
)
from ..services.contract_workspace import contract_billing_context, contract_revision_is_finalized
from ..services.finance_authorization import (
    BillingAuthorizationContext,
    billing_view_authorized,
    billing_view_scope,
    effective_billing_capabilities,
    resolve_billing_capability,
)
from .dependencies import AuthenticatedPrincipal, current_principal
from ..services.owner_decisions import runtime_decision_value
from ..services.commercial_contract_controls import compose_amec_invoice_reference
from ..services.source12_finance_controls import canonical_numbering_gate
from ..config.settings import get_settings
from ..services.week45 import stable_hash


router = APIRouter(prefix="/api/billing", tags=["billing-invoice"])

OWNER = {Role.OWNER_SPONSOR, Role.SYSTEM_ADMIN}
PLAN_WRITE = OWNER | {Role.PROCESS_CHAMPION}
VIEW = PLAN_WRITE | {Role.RESPONSIBLE_ENGINEER, Role.PERMIT_PREPARER, Role.REQUIREMENT_STEWARD}
DELIVERY_CHANNELS = {"EMAIL", "PORTAL", "IN_PERSON", "COURIER", "WHATSAPP", "OTHER"}
PAYMENT_METHODS = {"BANK_TRANSFER", "CHEQUE", "ALTERNATE_RECIPIENT", "PERSONAL_RECIPIENT"}
NON_CASH_RESOLUTION_TYPES = {"WAIVED", "WRITTEN_OFF", "NON_COLLECTIBLE", "COMMERCIAL_RELEASE"}
DUE_DATE_BASES = {"INVOICE_DATE", "ISSUE_DATE", "DELIVERY_DATE", "ACKNOWLEDGMENT_DATE", "CLIENT_APPROVAL_DATE", "FIXED_DATE", "OTHER_VERIFIED_EVENT"}
ELIGIBLE_AMEC_CONTRACT_TYPES = {"AMEC_PROFESSIONAL_SERVICES", "AMEC_SERVICE_CONTRACT"}


def _actor(request: Request, payload: dict[str, Any] | None = None) -> str:
    """Return an auditable actor identity, never a client payload in production."""
    principal = getattr(request.state, "authenticated_principal", None)
    settings = get_settings()
    # Synthetic tests may use an explicit actor envelope for fixture clarity;
    # production and Entra requests always use the authenticated application
    # user identity. Payload actor is never authoritative.
    if (
        settings.auth_mode.upper() == "DEV_HEADER"
        and settings.app_env.upper() in {"DEV", "TEST"}
        and settings.synthetic_only
    ):
        override = request.headers.get("X-Dev-Actor") or str((payload or {}).get("actor") or "").strip()
        if override:
            return override
    if principal is not None and principal.user_id:
        return principal.user_id
    raise HTTPException(401, {"code": "TRUSTED_ACTOR_REQUIRED"})


def _corr(request: Request) -> str:
    return getattr(request.state, "correlation_id", str(uuid4()))


def _business_timezone() -> tuple[str | None, ZoneInfo | None]:
    configured = get_settings().business_local_timezone.strip()
    if not configured:
        return None, None
    try:
        return configured, ZoneInfo(configured)
    except ZoneInfoNotFoundError:
        return configured, None


def _local_year_bounds() -> tuple[str | None, datetime | None, datetime | None]:
    name, zone = _business_timezone()
    if zone is None:
        return name, None, None
    now = datetime.now(zone)
    start = datetime(now.year, 1, 1, tzinfo=zone).astimezone(timezone.utc)
    end = datetime(now.year + 1, 1, 1, tzinfo=zone).astimezone(timezone.utc)
    return name, start, end


def _role(role: Role, allowed: set[Role], code: str) -> None:
    if role not in allowed:
        raise HTTPException(403, {"code": "CAPABILITY_DENIED", "capability": code})


def _authorize(
    db: Session,
    request: Request,
    principal: AuthenticatedPrincipal,
    *,
    capability: str,
    roles: set[Role],
    project_id: str | None = None,
    client_account_id: str | None = None,
    contract_id: str | None = None,
    office_id: str | None = None,
) -> None:
    request.state.authenticated_principal = principal
    context = _canonical_billing_context(
        db,
        project_id=project_id,
        client_account_id=client_account_id,
        contract_id=contract_id,
    )
    if office_id and not context.project_id:
        context = BillingAuthorizationContext(
            office_id=office_id,
            client_account_id=context.client_account_id,
            project_id=context.project_id,
        )
    resolve_billing_capability(
        db,
        principal,
        capability_code=capability,
        allowed_roles=roles,
        context=context,
        request=request,
    )


def _canonical_billing_context(
    db: Session,
    *,
    project_id: str | None = None,
    client_account_id: str | None = None,
    contract_id: str | None = None,
) -> BillingAuthorizationContext:
    """Derive target scope from canonical resources, never from the actor's office."""
    contract = db.get(Contract, contract_id) if contract_id else None
    project = db.get(Project, project_id) if project_id else None
    if contract and project_id and contract.project_id and contract.project_id != project_id:
        raise HTTPException(403, {"code": "CANONICAL_RESOURCE_SCOPE_MISMATCH"})
    if contract and client_account_id and contract.client_account_id and contract.client_account_id != client_account_id:
        raise HTTPException(403, {"code": "CANONICAL_RESOURCE_SCOPE_MISMATCH"})
    if contract:
        client_account_id = contract.client_account_id or client_account_id
        project = project or (db.get(Project, contract.project_id) if contract.project_id else None)
        project_id = project.id if project else contract.project_id
    return BillingAuthorizationContext(
        office_id=project.office_id if project else None,
        client_account_id=client_account_id,
        project_id=project_id,
    )


def _authorize_view(
    db: Session,
    request: Request,
    principal: AuthenticatedPrincipal,
    *,
    project_id: str | None = None,
    client_account_id: str | None = None,
    contract_id: str | None = None,
) -> None:
    request.state.authenticated_principal = principal
    billing_view_authorized(
        db,
        principal,
        context=_canonical_billing_context(
            db,
            project_id=project_id,
            client_account_id=client_account_id,
            contract_id=contract_id,
        ),
        request=request,
    )


def _view_scope(db: Session, principal: AuthenticatedPrincipal):
    scope = billing_view_scope(db, principal)
    if scope.empty:
        raise HTTPException(403, {"code": "SCOPED_FINANCE_CAPABILITY_REQUIRED", "capability": "BILLING_VIEW"})
    return scope


def _scope_clause(model: Any, scope: Any, *, project: str | None = "project_id", client: str | None = "client_account_id", contract: str | None = "contract_id"):
    """Build OR-of-grants / AND-of-dimensions SQL scope predicates.

    A client assignment is never expanded into all projects touched by that
    client. Canonical Contract/Project subqueries are used only when the row
    model lacks a direct dimension.
    """
    if not scope.assignment_specs:
        return false()
    from ..models import Contract

    project_column = getattr(model, project, None) if project else None
    client_column = getattr(model, client, None) if client else None
    contract_column = getattr(model, contract, None) if contract else None
    clauses = []
    for office_id, client_id, project_id in scope.assignment_specs:
        dimensions = []
        if project_id:
            if project_column is not None:
                dimensions.append(project_column == project_id)
            elif contract_column is not None:
                dimensions.append(contract_column.in_(select(Contract.id).where(Contract.project_id == project_id)))
            else:
                continue
        if office_id:
            office_projects = select(Project.id).where(Project.office_id == office_id)
            if project_column is not None:
                dimensions.append(project_column.in_(office_projects))
            elif contract_column is not None:
                dimensions.append(contract_column.in_(select(Contract.id).where(Contract.project_id.in_(office_projects))))
            else:
                continue
        if client_id:
            if client_column is not None:
                dimensions.append(client_column == client_id)
            elif contract_column is not None:
                dimensions.append(contract_column.in_(select(Contract.id).where(Contract.client_account_id == client_id)))
            elif project_column is not None and (project_id or office_id):
                dimensions.append(project_column.in_(select(Contract.project_id).where(Contract.client_account_id == client_id)))
            else:
                # A project-only row cannot safely be exposed by a client-only
                # grant: the project may contain another client's contract.
                continue
        if dimensions:
            clauses.append(and_(*dimensions))
    return or_(*clauses) if clauses else false()


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


def _validate_document_evidence(db: Session, evidence_id: str | None, project: Project | None, *, not_found_code: str, mismatch_code: str) -> None:
    if not evidence_id:
        return
    version = db.get(DocumentVersion, evidence_id)
    document = db.get(Document, version.document_id) if version else None
    if not version or not document:
        raise HTTPException(404, {"code": not_found_code})
    if project and document.project_id not in {None, project.id}:
        raise HTTPException(403, {"code": mismatch_code})


def _payment_evidence_gate(item: PaymentReceipt) -> None:
    method = str(item.payment_method or "").strip().upper()
    if not method:
        raise HTTPException(409, {"code": "PAYMENT_METHOD_REQUIRED"})
    if method not in PAYMENT_METHODS:
        raise HTTPException(409, {"code": "PAYMENT_METHOD_NOT_SUPPORTED", "allowed": sorted(PAYMENT_METHODS)})
    primary = bool(item.evidence_document_version_id or str(item.evidence_reference or "").strip())
    voucher = bool(item.receipt_voucher_document_version_id or str(item.receipt_voucher_evidence_reference or "").strip())
    if method == "BANK_TRANSFER" and not primary:
        raise HTTPException(409, {"code": "PAYMENT_TRANSFER_EVIDENCE_REQUIRED"})
    if method == "CHEQUE" and (not primary or not voucher):
        raise HTTPException(409, {"code": "PAYMENT_CHEQUE_EVIDENCE_REQUIRED", "primary_evidence": primary, "receipt_voucher": voucher})
    if method in {"ALTERNATE_RECIPIENT", "PERSONAL_RECIPIENT"}:
        context = item.custodian_context_json or {}
        if not primary or not str(context.get("recipient_name") or "").strip() or not str(context.get("custody_reference") or context.get("custodian_reference") or "").strip():
            raise HTTPException(409, {"code": "PAYMENT_CUSTODIAN_CONTEXT_REQUIRED"})


def _eligible_contract_type(db: Session, contract: Contract, revision: ContractRevision | None = None) -> str:
    configured = runtime_decision_value(db, "BILLING_ELIGIBLE_CONTRACT_TYPES", sorted(ELIGIBLE_AMEC_CONTRACT_TYPES))
    allowed = {str(item).upper() for item in (configured if isinstance(configured, list) else [configured])}
    value = str(getattr(contract, "agreement_type", None) or getattr(revision, "agreement_type", None) or "").upper()
    if value not in allowed:
        raise HTTPException(409, {"code": "CONTRACT_NOT_ELIGIBLE_FOR_AMEC_BILLING", "agreement_type": value or "UNCLASSIFIED", "allowed_types": sorted(allowed)})
    return value


def _due_basis(value: Any) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    basis = str(value).strip().upper().replace(" ", "_")
    aliases = {"INVOICE": "INVOICE_DATE", "ISSUE": "ISSUE_DATE", "DELIVERY": "DELIVERY_DATE", "ACK": "ACKNOWLEDGMENT_DATE", "APPROVAL": "CLIENT_APPROVAL_DATE"}
    basis = aliases.get(basis, basis)
    if basis not in DUE_DATE_BASES:
        raise HTTPException(422, {"code": "DUE_DATE_BASIS_NOT_SUPPORTED", "basis": basis})
    return basis


def _configure_due_date(revision: InvoiceRevision, *, invoice_date: date, basis: str | None, offset_days: int | None, fixed_date: date | None) -> None:
    revision.due_date_basis = basis
    revision.due_date_offset_days = offset_days
    revision.due_date_fixed_date = fixed_date
    revision.due_date_source_event_type = None
    revision.due_date_source_event_id = None
    revision.due_date_derived_at = None
    if basis == "FIXED_DATE":
        if not fixed_date:
            raise HTTPException(422, {"code": "FIXED_DUE_DATE_REQUIRED"})
        revision.due_date = fixed_date
        revision.due_date_status = "DERIVED"
    elif basis == "INVOICE_DATE":
        if offset_days is None:
            raise HTTPException(422, {"code": "DUE_DATE_OFFSET_REQUIRED"})
        revision.due_date = invoice_date + timedelta(days=offset_days)
        revision.due_date_status = "DERIVED"
    elif basis in {"ISSUE_DATE", "DELIVERY_DATE", "ACKNOWLEDGMENT_DATE", "CLIENT_APPROVAL_DATE", "OTHER_VERIFIED_EVENT"}:
        revision.due_date = None
        revision.due_date_status = "PENDING_EVENT"
    else:
        revision.due_date = None
        revision.due_date_status = "NOT_CONFIGURED"


def _derive_due_date(revision: InvoiceRevision, *, event_type: str, event_id: str, event_at: datetime | date) -> bool:
    basis = revision.due_date_basis
    expected = {"ISSUE_DATE": "ISSUE", "DELIVERY_DATE": "DELIVERY", "ACKNOWLEDGMENT_DATE": "ACKNOWLEDGMENT", "CLIENT_APPROVAL_DATE": "CLIENT_APPROVAL"}.get(basis or "")
    if not expected or event_type != expected:
        return False
    event_date = event_at.date() if isinstance(event_at, datetime) else event_at
    revision.due_date = event_date + timedelta(days=revision.due_date_offset_days or 0)
    revision.due_date_status = "DERIVED"
    revision.due_date_source_event_type = event_type
    revision.due_date_source_event_id = event_id
    revision.due_date_derived_at = datetime.now(timezone.utc)
    return True


def _communication_state(db: Session, invoice_id: str) -> str:
    issue = db.scalar(select(InvoiceIssueEvent).where(InvoiceIssueEvent.invoice_id == invoice_id))
    if not issue:
        invoice = db.get(Invoice, invoice_id)
        return "ACCEPTED" if invoice and invoice.status == "ACCEPTED_INTERNAL" else "DRAFT"
    delivery = db.scalar(select(InvoiceDeliveryEvent).where(InvoiceDeliveryEvent.invoice_id == invoice_id, InvoiceDeliveryEvent.status == "RECORDED").order_by(InvoiceDeliveryEvent.delivered_at.desc()))
    if not delivery:
        return "ISSUED"
    approval = db.scalar(select(InvoiceApprovalRecord).join(InvoiceRevision).where(InvoiceRevision.invoice_id == invoice_id, InvoiceApprovalRecord.approval_type.in_({"CLIENT_APPROVAL", "CLIENT_CERTIFICATION"}), InvoiceApprovalRecord.status.in_({"VERIFIED", "APPROVED", "CLIENT_APPROVED"})).order_by(InvoiceApprovalRecord.verified_at.desc()))
    if approval:
        return "CLIENT_APPROVED"
    acknowledgment = db.scalar(select(InvoiceAcknowledgment).where(InvoiceAcknowledgment.invoice_id == invoice_id, InvoiceAcknowledgment.status == "RECORDED").order_by(InvoiceAcknowledgment.acknowledged_at.desc()))
    return "ACKNOWLEDGED" if acknowledgment else "DELIVERED"


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
    _eligible_contract_type(db, contract, revision)
    if not contract.client_account_id or not db.get(ClientAccount, contract.client_account_id):
        raise HTTPException(409, {"code": "CANONICAL_CLIENT_REQUIRED"})
    context = contract_billing_context(db, contract, revision.id)
    activation = db.scalar(select(ProjectActivation).where(ProjectActivation.contract_id == contract.id, ProjectActivation.status == "ACTIVE"))
    project = db.get(Project, activation.project_id) if activation else (db.get(Project, contract.project_id) if contract.project_id else None)
    return contract, revision, context, project


def _scope_project(db: Session, project_id: str | None, contract: Contract, project: Project | None) -> None:
    if project_id and (not project or project.id != project_id):
        raise HTTPException(403, {"code": "CROSS_PROJECT_BILLING_CONTEXT_DENIED"})


def _require_issue_project_policy(db: Session, project: Project | None) -> None:
    if project:
        return
    policy = str(runtime_decision_value(db, "BILLING_PREACTIVATION_ISSUE_POLICY", "PROJECT_REQUIRED")).upper()
    if policy not in {"PRE_ACTIVATION_ALLOWED", "ALLOW"}:
        raise HTTPException(409, {"code": "PROJECT_ACTIVATION_REQUIRED_FOR_ISSUE", "policy": policy})


def _audit(db: Session, request: Request, event: str, entity_type: str, entity_id: str, actor: str, after: dict[str, Any] | None = None) -> None:
    safe = dict(after or {})
    assignment_id = getattr(request.state, "billing_authorization_assignment_id", None)
    if assignment_id:
        safe["authorization_assignment_id"] = assignment_id
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
    checks.append({"code": "DUE_DATE", "status": "PASS" if revision.due_date or revision.due_date_basis in DUE_DATE_BASES else "NEEDS_REVIEW", "reason": "Due date is derived from the pinned basis; event-based terms may remain pending until the verified event arrives."})
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
    settings = get_settings()
    numbering = canonical_numbering_gate(lambda key, default=False: runtime_decision_value(db, key, default))
    checks.append({"code": "NUMBERING_READINESS", "status": "PASS" if settings.synthetic_only or numbering["ready"] else "BLOCKED", "reason": "Invoice numbering uses the canonical Source 12 control contract and remains fail-closed in production."})
    account_ready = bool(db.scalar(select(FinancialAccountVersion.id).join(FinancialAccountMaster).where(FinancialAccountVersion.currency == (revision.currency or "").upper(), FinancialAccountVersion.status == "ACTIVE", FinancialAccountMaster.status == "ACTIVE")))
    checks.append({"code": "FINANCIAL_ACCOUNT_CONTROL", "status": "PASS" if account_ready or settings.synthetic_only else "BLOCKED", "reason": "An active legal-entity-bound financial account version is required before Issue."})
    result = "BLOCKED" if any(item["status"] == "BLOCKED" for item in checks) else "NEEDS_REVIEW" if any(item["status"] == "NEEDS_REVIEW" for item in checks) else "PASS"
    return {"result": result, "checks": checks}


def _signer_evidence(
    db: Session,
    payload: dict[str, Any],
    *,
    invoice: Invoice,
    revision: InvoiceRevision,
    project: Project | None,
    account_master: FinancialAccountMaster | None,
    issue_at: datetime,
) -> dict[str, Any]:
    """Resolve Source 13 signer authority from governed records at Issue."""
    settings = get_settings()
    if settings.synthetic_only:
        return {
            "identity": str(payload.get("signer_identity") or "SYNTHETIC_SIGNER").strip(),
            "capacity": str(payload.get("signer_capacity") or "SYNTHETIC_AUTHORIZED_FINANCE_SIGNER").strip(),
            "authority_reference": str(payload.get("signer_authority_reference") or "SYNTHETIC-SOURCE13-SIGNER").strip(),
            "evidence_reference": str(payload.get("signer_evidence_reference") or "synthetic://source13/signer-authority").strip(),
            "status": "SYNTHETIC_ONLY",
        }
    authority_id = str(payload.get("signer_authority_id") or "").strip()
    authority = db.get(GovernedSignatoryAuthority, authority_id) if authority_id else None
    if not authority:
        raise HTTPException(409, {"code": "SIGNER_AUTHORITY_RECORD_REQUIRED", "source": "SOURCE13"})
    authority_from = authority.effective_from.replace(tzinfo=timezone.utc) if authority.effective_from.tzinfo is None else authority.effective_from
    authority_to = authority.effective_to.replace(tzinfo=timezone.utc) if authority.effective_to and authority.effective_to.tzinfo is None else authority.effective_to
    if authority.status != "ACTIVE" or authority_from > issue_at or (authority_to and authority_to < issue_at):
        raise HTTPException(409, {"code": "SIGNER_AUTHORITY_NOT_ACTIVE_AT_ISSUE", "source": "SOURCE13"})
    signer_user = db.get(User, authority.user_id)
    if not signer_user or not signer_user.active:
        raise HTTPException(409, {"code": "SIGNER_USER_NOT_ACTIVE", "source": "SOURCE13"})
    normalized_capacity = authority.capacity.strip().upper().replace(" ", "_")
    if normalized_capacity not in {"GENERAL_MANAGER", "RESPONSIBLE_ACCOUNTING_SIGNER"}:
        raise HTTPException(409, {"code": "SIGNER_CAPACITY_NOT_AUTHORIZED", "source": "SOURCE13"})
    if normalized_capacity == "RESPONSIBLE_ACCOUNTING_SIGNER" and not authority.owner_authorization_reference.strip():
        raise HTTPException(409, {"code": "OWNER_SIGNER_AUTHORIZATION_REQUIRED", "source": "SOURCE13"})
    if project and authority.office_id != project.office_id:
        raise HTTPException(409, {"code": "SIGNER_OFFICE_MISMATCH", "source": "SOURCE13"})
    expected_entity = str((revision.contract_project_context_snapshot or {}).get("legal_entity_ref") or "").strip()
    if not expected_entity or not account_master or authority.legal_entity_ref != expected_entity or authority.legal_entity_ref != account_master.legal_entity_ref:
        raise HTTPException(409, {"code": "SIGNER_LEGAL_ENTITY_MISMATCH", "source": "SOURCE13"})
    if not (authority.authority_evidence_document_version_id or str(authority.authority_evidence_reference or "").strip()):
        raise HTTPException(409, {"code": "SIGNER_AUTHORITY_EVIDENCE_REQUIRED", "source": "SOURCE13"})
    signed_id = str(payload.get("signed_invoice_evidence_document_version_id") or "").strip()
    signed_version = db.get(DocumentVersion, signed_id) if signed_id else None
    signed_document = db.get(Document, signed_version.document_id) if signed_version else None
    metadata = signed_version.metadata_json if signed_version else {}
    if not signed_version or not signed_document or (project and signed_document.project_id != project.id) or not (
        metadata.get("invoice_id") == invoice.id or metadata.get("invoice_revision_id") == revision.id
    ):
        raise HTTPException(409, {"code": "SIGNED_INVOICE_EVIDENCE_REQUIRED", "source": "SOURCE13"})
    supplied_identity = str(payload.get("signer_identity") or "").strip()
    supplied_capacity = str(payload.get("signer_capacity") or "").strip().upper().replace(" ", "_")
    valid_identities = {signer_user.id, signer_user.email, signer_user.entra_object_id}
    if supplied_identity and supplied_identity not in valid_identities:
        raise HTTPException(409, {"code": "SIGNER_IDENTITY_MISMATCH", "source": "SOURCE13"})
    if supplied_capacity and supplied_capacity != normalized_capacity:
        raise HTTPException(409, {"code": "SIGNER_CAPACITY_MISMATCH", "source": "SOURCE13"})
    return {
        "identity": signer_user.id,
        "display_identity": signer_user.display_name,
        "capacity": normalized_capacity,
        "authority_type": authority.authority_type,
        "authority_id": authority.id,
        "authority_reference": authority.owner_authorization_reference,
        "authority_evidence_document_version_id": authority.authority_evidence_document_version_id,
        "authority_evidence_reference": authority.authority_evidence_reference,
        "signed_invoice_evidence_document_version_id": signed_version.id,
        "status": "PRODUCTION_EVIDENCED",
    }


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
def billing_summary(request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    scope = _view_scope(db, principal)
    if scope.empty:
        raise HTTPException(403, {"code": "SCOPED_FINANCE_CAPABILITY_REQUIRED", "capability": "BILLING_VIEW"})
    plan_clause = _scope_clause(BillingPlan, scope)
    invoice_clause = _scope_clause(Invoice, scope)
    payment_clause = _scope_clause(PaymentReceipt, scope)
    milestone_clause = _scope_clause(BillingPlanRevision, scope)
    account_clause = FinancialAccountMaster.office_id.in_(scope.office_ids) if scope.office_ids else false()
    return {"plans": db.scalar(select(func.count()).select_from(BillingPlan).where(plan_clause)) or 0, "milestones": db.scalar(select(func.count()).select_from(BillingMilestone).join(BillingPlanRevision).where(milestone_clause)) or 0, "invoices": db.scalar(select(func.count()).select_from(Invoice).where(invoice_clause)) or 0, "payment_receipts": db.scalar(select(func.count()).select_from(PaymentReceipt).where(payment_clause)) or 0, "financial_accounts": db.scalar(select(func.count()).select_from(FinancialAccountMaster).where(account_clause)) or 0, "automation_defaults": {"auto_prepare_draft": False, "auto_accept": False, "auto_issue": False, "auto_mark_paid": False}}


@router.post("/plans")
def create_billing_plan(payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, PLAN_WRITE, "BILLING_PLAN_MANAGE")
    contract, revision, context, project = _contract_context(db, str(payload.get("contract_id") or ""), payload.get("contract_revision_id"))
    _authorize(db, request, principal, capability="BILLING_PLAN_MANAGE", roles=PLAN_WRITE, project_id=project.id if project else None, client_account_id=contract.client_account_id)
    currency = str(payload.get("currency") or revision.currency or contract.currency or "").upper()
    if not currency:
        raise HTTPException(409, {"code": "CONTRACT_CURRENCY_REQUIRED"})
    existing = db.scalar(select(BillingPlan).where(BillingPlan.contract_id == contract.id, BillingPlan.contract_revision_id == revision.id, BillingPlan.status.not_in({"CANCELLED", "SUPERSEDED"})))
    if existing:
        return {"plan": _row(existing), "revision": _row(db.get(BillingPlanRevision, existing.current_revision_id))}
    billing_mode = str(payload.get("billing_mode") or "MILESTONE_EVENT").upper()
    if billing_mode not in {"SUPERVISION_MONTHLY", "MILESTONE_EVENT"}:
        raise HTTPException(422, {"code": "BILLING_MODE_NOT_SUPPORTED", "allowed": ["MILESTONE_EVENT", "SUPERVISION_MONTHLY"]})
    plan = BillingPlan(contract_id=contract.id, contract_revision_id=revision.id, project_id=project.id if project else None, client_account_id=contract.client_account_id, currency=currency, automation_mode=str(payload.get("automation_mode") or "MANUAL").upper(), billing_mode=billing_mode, status="DRAFT", created_by=_actor(request, payload))
    db.add(plan); db.flush()
    plan_revision = BillingPlanRevision(billing_plan_id=plan.id, revision_number=1, contract_id=contract.id, contract_revision_id=revision.id, project_id=project.id if project else None, client_account_id=contract.client_account_id, contract_amount=_contract_amount(revision, contract), currency=currency, billing_mode=billing_mode, valuation_amount=revision.valuation_amount, valuation_currency=revision.valuation_currency, valuation_status=revision.valuation_status, contract_project_context_snapshot=context.get("contract_project_context_snapshot") or {}, status="DRAFT", created_by=_actor(request, payload), source_snapshot={"contract_billing_context": context, "project_activation_status": context.get("project_activation_status"), "agreement_type": contract.agreement_type})
    db.add(plan_revision); db.flush(); plan.current_revision_id = plan_revision.id
    _lineage(db, request, project.id if project else None, "ContractRevision", revision.id, "BillingPlanRevision", plan_revision.id, "BILLING_PLAN_FROM_EXACT_CONTRACT_REVISION")
    _audit(db, request, "BILLING_PLAN_CREATED", "BillingPlan", plan.id, _actor(request, payload), {"contract_revision_id": revision.id, "project_id": project.id if project else None, "automation_mode": plan.automation_mode})
    db.commit()
    return {"plan": _row(plan), "revision": _row(plan_revision), "context": context}


@router.get("/plans/{plan_id}")
def get_billing_plan(plan_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    plan = db.get(BillingPlan, plan_id)
    if not plan:
        raise HTTPException(404, {"code": "BILLING_PLAN_NOT_FOUND"})
    _authorize_view(db, request, principal, project_id=plan.project_id, client_account_id=plan.client_account_id, contract_id=plan.contract_id)
    revision = db.get(BillingPlanRevision, plan.current_revision_id) if plan.current_revision_id else None
    milestones = db.scalars(select(BillingMilestone).where(BillingMilestone.billing_plan_revision_id == (revision.id if revision else "")).order_by(BillingMilestone.sequence)).all()
    revisions = db.scalars(select(BillingPlanRevision).where(BillingPlanRevision.billing_plan_id == plan.id).order_by(BillingPlanRevision.revision_number.desc())).all()
    readiness = db.scalars(select(BillingReadinessRequest).where(BillingReadinessRequest.billing_plan_revision_id == (revision.id if revision else "")).order_by(BillingReadinessRequest.requested_at.desc())).all()
    return {"plan": _row(plan), "revision": _row(revision), "revisions": [_row(x) for x in revisions], "milestones": [_milestone_projection(db, x) for x in milestones], "readiness_requests": [_row(x) for x in readiness], "context": _billing_context(db, contract_id=plan.contract_id, project_id=plan.project_id, client_account_id=plan.client_account_id), "source_of_truth": "CANONICAL_BILLING_PLAN_AND_REVISION_LINEAGE"}


@router.post("/plans/{plan_id}/revisions")
def revise_billing_plan(plan_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, PLAN_WRITE, "BILLING_PLAN_MANAGE")
    plan = db.get(BillingPlan, plan_id)
    if not plan or plan.status in {"CANCELLED", "SUPERSEDED"}:
        raise HTTPException(404, {"code": "BILLING_PLAN_NOT_FOUND"})
    previous = db.get(BillingPlanRevision, plan.current_revision_id)
    contract, contract_revision, context, project = _contract_context(db, plan.contract_id, plan.contract_revision_id)
    _authorize(db, request, principal, capability="BILLING_PLAN_MANAGE", roles=PLAN_WRITE, project_id=project.id if project else plan.project_id, client_account_id=contract.client_account_id)
    number = (db.scalar(select(func.max(BillingPlanRevision.revision_number)).where(BillingPlanRevision.billing_plan_id == plan.id)) or 0) + 1
    billing_mode = str(payload.get("billing_mode") or plan.billing_mode or "MILESTONE_EVENT").upper()
    if billing_mode not in {"SUPERVISION_MONTHLY", "MILESTONE_EVENT"}:
        raise HTTPException(422, {"code": "BILLING_MODE_NOT_SUPPORTED", "allowed": ["MILESTONE_EVENT", "SUPERVISION_MONTHLY"]})
    revision = BillingPlanRevision(billing_plan_id=plan.id, revision_number=number, contract_id=contract.id, contract_revision_id=contract_revision.id, project_id=project.id if project else None, client_account_id=contract.client_account_id, contract_amount=_contract_amount(contract_revision, contract), currency=str(payload.get("currency") or plan.currency).upper(), billing_mode=billing_mode, valuation_amount=contract_revision.valuation_amount, valuation_currency=contract_revision.valuation_currency, valuation_status=contract_revision.valuation_status, contract_project_context_snapshot=context.get("contract_project_context_snapshot") or {}, status="DRAFT", supersedes_revision_id=previous.id if previous else None, created_by=_actor(request, payload), source_snapshot={"reason": payload.get("reason"), "contract_billing_context": context, "agreement_type": contract.agreement_type})
    db.add(revision); db.flush(); plan.current_revision_id = revision.id; plan.status = "DRAFT"
    _lineage(db, request, project.id if project else None, "BillingPlanRevision", previous.id if previous else contract_revision.id, "BillingPlanRevision", revision.id, "BILLING_PLAN_REVISION_SUPERSEDES")
    _audit(db, request, "BILLING_PLAN_REVISED", "BillingPlanRevision", revision.id, _actor(request, payload), {"supersedes_revision_id": previous.id if previous else None})
    db.commit()
    return _row(revision)


@router.post("/plans/{plan_id}/activate")
def activate_billing_plan(plan_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "BILLING_PLAN_APPROVE")
    plan = db.get(BillingPlan, plan_id)
    if not plan:
        raise HTTPException(404, {"code": "BILLING_PLAN_NOT_FOUND"})
    revision = db.get(BillingPlanRevision, plan.current_revision_id) if plan.current_revision_id else None
    if not revision:
        raise HTTPException(409, {"code": "BILLING_PLAN_REVISION_REQUIRED"})
    _authorize(db, request, principal, capability="BILLING_PLAN_APPROVE", roles=OWNER, project_id=revision.project_id or plan.project_id, client_account_id=revision.client_account_id or plan.client_account_id)
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
def create_billing_milestone(plan_revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, PLAN_WRITE, "BILLING_MILESTONE_REVIEW")
    plan_revision, plan, contract, contract_revision, project = _plan_revision(db, plan_revision_id)
    _authorize(db, request, principal, capability="BILLING_MILESTONE_REVIEW", roles=PLAN_WRITE, project_id=project.id if project else plan_revision.project_id, client_account_id=contract.client_account_id)
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
def evaluate_milestone(milestone_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, PLAN_WRITE, "BILLING_MILESTONE_REVIEW")
    item = db.get(BillingMilestone, milestone_id)
    if not item:
        raise HTTPException(404, {"code": "BILLING_MILESTONE_NOT_FOUND"})
    plan_revision, plan, contract, contract_revision, project = _plan_revision(db, item.billing_plan_revision_id)
    _authorize(db, request, principal, capability="BILLING_MILESTONE_REVIEW", roles=PLAN_WRITE, project_id=project.id if project else plan_revision.project_id, client_account_id=contract.client_account_id)
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
def create_invoice(payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, PLAN_WRITE, "INVOICE_CREATE")
    ids = [str(x) for x in (payload.get("milestone_ids") or [])]
    if not ids:
        raise HTTPException(409, {"code": "BILLING_MILESTONE_REQUIRED", "manual_invoice_disabled": True})
    milestones = [db.get(BillingMilestone, item) for item in ids]
    if any(item is None for item in milestones):
        raise HTTPException(404, {"code": "BILLING_MILESTONE_NOT_FOUND"})
    plan_revision, plan, contract, contract_revision, project = _plan_revision(db, milestones[0].billing_plan_revision_id)
    _authorize(db, request, principal, capability="INVOICE_CREATE", roles=PLAN_WRITE, project_id=project.id if project else plan_revision.project_id, client_account_id=contract.client_account_id)
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
    due_days = [item.due_days for item in milestones if item.due_days is not None]
    requested_basis = _due_basis(payload.get("due_date_basis"))
    explicit_due_date = _date(payload["due_date"], field="due_date") if payload.get("due_date") else None
    if requested_basis is None:
        requested_basis = "FIXED_DATE" if explicit_due_date else "INVOICE_DATE" if due_days and len(set(due_days)) == 1 else None
    offset_days = int(payload["due_days"]) if payload.get("due_days") is not None else due_days[0] if due_days and len(set(due_days)) == 1 else None
    if offset_days is not None and offset_days < 0:
        raise HTTPException(422, {"code": "DUE_DATE_OFFSET_INVALID"})
    planned_collection_date = _date(payload["planned_collection_date"], field="planned_collection_date") if payload.get("planned_collection_date") else None
    service_start = _date(payload["service_period_start"], field="service_period_start") if payload.get("service_period_start") else None
    service_end = _date(payload["service_period_end"], field="service_period_end") if payload.get("service_period_end") else None
    if service_start and service_end and service_end < service_start:
        raise HTTPException(422, {"code": "SERVICE_PERIOD_INVALID"})
    revision = InvoiceRevision(invoice_id=invoice.id, revision_number=1, controlling_contract_revision_id=contract_revision.id, billing_plan_revision_id=plan_revision.id, status="DRAFT", invoice_date=invoice_date, planned_collection_date=planned_collection_date, service_period=payload.get("service_period"), service_period_start=service_start, service_period_end=service_end, service_period_label=payload.get("service_period_label") or payload.get("service_period"), description=payload.get("description") or "Billing milestone invoice", currency=plan_revision.currency, contract_project_context_snapshot=plan_revision.contract_project_context_snapshot or {}, source_snapshot={"contract_id": contract.id, "contract_revision_id": contract_revision.id, "billing_plan_revision_id": plan_revision.id, "milestone_ids": ids, "client_account_id": contract.client_account_id, "project_id": project.id if project else None, "contract_project_context_snapshot": plan_revision.contract_project_context_snapshot or {}, "agreement_type": contract.agreement_type})
    _configure_due_date(revision, invoice_date=invoice_date, basis=requested_basis, offset_days=offset_days, fixed_date=explicit_due_date)
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
def list_invoices(request: Request, project_id: str | None = None, contract_id: str | None = None, lane: str | None = None, q: str = "", db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    scope = _view_scope(db, principal)
    if project_id or contract_id:
        _authorize_view(db, request, principal, project_id=project_id, contract_id=contract_id)
    query = select(Invoice).where(_scope_clause(Invoice, scope)).order_by(Invoice.created_at.desc())
    if project_id: query = query.where(Invoice.project_id == project_id)
    if contract_id: query = query.where(Invoice.contract_id == contract_id)
    rows = db.scalars(query).all()
    needle = q.strip().lower()
    all_items = []
    for invoice in rows:
        revision = db.get(InvoiceRevision, invoice.current_revision_id) if invoice.current_revision_id else None
        receivable = _receivable(db, invoice, revision) if revision else {"state": "NOT_ISSUED", "outstanding": None}
        stage = "AUTHORITY_REVIEW" if invoice.status in {"ACCEPTED_INTERNAL", "FINANCE_REVIEW"} else "READY_CLOSE" if invoice.status == "ISSUED" else "NEED_ACTION" if invoice.status in {"DRAFT", "NEEDS_REVALIDATION"} else "ALL"
        contract = db.get(Contract, invoice.contract_id)
        project = db.get(Project, invoice.project_id) if invoice.project_id else None
        client = db.get(ClientAccount, invoice.client_account_id) if invoice.client_account_id else None
        searchable = " ".join(str(value or "") for value in (invoice.invoice_reference, contract.contract_reference if contract else None, contract.contract_name if contract else None, contract.project_opportunity_ref if contract else None, client.display_name if client else None, project.project_code if project else None, project.project_number if project else None)).lower()
        if needle and needle not in searchable:
            continue
        all_items.append({"invoice": _row(invoice), "contract": _row(contract), "client": _row(client), "project": _row(project), "revision": _row(revision), "stage": stage, "receivable": receivable})
    items = [item for item in all_items if not lane or lane.upper() in {"ALL", item["stage"], str(item["receivable"].get("state") or "").upper()}]
    return {"items": items, "total": len(items), "lanes": {"all": len(all_items), "need_action": sum(x["stage"] == "NEED_ACTION" for x in all_items), "authority_review": sum(x["stage"] == "AUTHORITY_REVIEW" for x in all_items), "ready_close": sum(x["stage"] == "READY_CLOSE" for x in all_items)}, "search": q, "lane": lane or "ALL"}


@router.get("/projects/{project_id}/financial-projection")
def project_financial_projection(project_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, {"code": "PROJECT_NOT_FOUND"})
    _authorize_view(db, request, principal, project_id=project.id)
    invoices = db.scalars(select(Invoice).where(Invoice.project_id == project.id).order_by(Invoice.created_at)).all()
    contracts = db.scalars(select(Contract).where((Contract.project_id == project.id) | (Contract.id.in_(select(Invoice.contract_id).where(Invoice.project_id == project.id))))).all()
    contract = contracts[0] if contracts else None
    contract_revision = db.get(ContractRevision, contract.current_revision_id) if contract and contract.current_revision_id else None
    project_value = _contract_amount(contract_revision, contract) if contract and contract_revision else None
    rows = [_invoice_projection(db, invoice) for invoice in invoices]
    total_invoiced = sum((_d(row.get("payable_amount") or 0) for row in rows), Decimal("0"))
    cash_received = sum((_d(row.get("cash_allocated_amount") or 0) for row in rows), Decimal("0"))
    non_cash_resolved = sum((_d(row.get("non_cash_resolved_amount") or 0) for row in rows), Decimal("0"))
    outstanding = sum((_d(row.get("outstanding_amount") or 0) for row in rows), Decimal("0"))
    remaining_contract_balance = max(Decimal("0"), project_value - cash_received - non_cash_resolved) if project_value is not None else None
    fx_rate = None
    qar_amount = project_value if contract and str(contract.currency or "").upper() == "QAR" else None
    if project_value is not None and contract and str(contract.currency or "").upper() != "QAR":
        fx_rate = db.scalar(select(BillingFxRateRecord).where(BillingFxRateRecord.source_currency == str(contract.currency or "").upper(), BillingFxRateRecord.status == "ACTIVE", BillingFxRateRecord.rate_effective_date <= date.today()).order_by(BillingFxRateRecord.rate_effective_date.desc(), BillingFxRateRecord.rate_record_version.desc()))
        qar_amount = _money(project_value * _d(fx_rate.qar_per_source_currency_rate)) if fx_rate else None
    milestone_rows = db.scalars(select(BillingMilestone).join(BillingPlanRevision, BillingPlanRevision.id == BillingMilestone.billing_plan_revision_id).where(BillingPlanRevision.contract_id == contract.id)).all() if contract else []
    eligible_milestones = [item for item in milestone_rows if item.eligibility_state == "ELIGIBLE"]
    billing_complete = bool(rows) and all(row.get("status") in {"ISSUED", "VOIDED"} for row in rows) and all(_d(item.remaining_invoiceable_amount or 0) <= 0 for item in eligible_milestones)
    financial_complete = bool(rows) and outstanding <= 0
    expected_exp = db.scalar(select(ProjectExpectedExpVersion).where(ProjectExpectedExpVersion.project_id == project.id, ProjectExpectedExpVersion.status == "ACTIVE").order_by(ProjectExpectedExpVersion.version.desc()))
    return {"project": _row(project), "contract": _row(contract), "currency": contract.currency if contract else None, "project_value": str(_money(project_value)) if project_value is not None else None, "qar_amount": str(_money(qar_amount)) if qar_amount is not None else None, "fx_projection": {"status": "NOT_APPLICABLE" if contract and str(contract.currency or "").upper() == "QAR" else "FX_RATE_RECORD_REQUIRED" if not fx_rate else "PASS", "source_currency": contract.currency if contract else None, "qar_per_source_currency_rate": str(fx_rate.qar_per_source_currency_rate) if fx_rate else None, "rate_record_id": fx_rate.id if fx_rate else None, "rate_source_reference": fx_rate.rate_source_reference if fx_rate else None}, "expected_exp": {"status": "NOT_SET" if not expected_exp else "PASS", "value_percent": str(expected_exp.value_percent) if expected_exp else None, "version": expected_exp.version if expected_exp else None, "source_or_note": expected_exp.source_or_note if expected_exp else None}, "total_invoiced": str(_money(total_invoiced)), "amount_received": str(_money(cash_received)), "cash_allocated_amount": str(_money(cash_received)), "non_cash_resolved_amount": str(_money(non_cash_resolved)), "remaining_contract_balance": str(_money(remaining_contract_balance)) if remaining_contract_balance is not None else None, "outstanding_amount": str(_money(outstanding)), "billing_completion_state": "COMPLETE" if billing_complete else "OPEN", "financial_completion_state": "COMPLETE" if financial_complete else "OPEN", "billing_complete": billing_complete, "financial_complete": financial_complete, "completion_basis": {"billing": "issued_invoice_and_no_remaining_invoiceable_milestone", "financial": "zero_outstanding_after_cash_or_governed_non_cash_resolution"}, "invoice_count": len(rows), "invoices": rows, "milestones": [_milestone_projection(db, item) for item in milestone_rows], "payment_history": [_payment_projection(db, item) for item in db.scalars(select(PaymentReceipt).where(PaymentReceipt.project_id == project.id).order_by(PaymentReceipt.received_date.desc())).all()], "ytd": {"policy": "CALENDAR_YEAR", "status": "CONFIGURATION_REQUIRED", "timezone": None, "invoiced": None, "collected": None}, "source_of_truth": "CANONICAL_BILLING_EVENTS"}


@router.get("/offices/{office_id}/invoice-register")
def office_invoice_register(office_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    if not db.get(ConsultancyOffice, office_id):
        raise HTTPException(404, {"code": "OFFICE_NOT_FOUND"})
    scope = _view_scope(db, principal)
    allowed_projects = {item for item in scope.project_ids if (db.get(Project, item) and db.get(Project, item).office_id == office_id)}
    if not allowed_projects and office_id not in scope.office_ids:
        raise HTTPException(403, {"code": "SCOPED_FINANCE_CAPABILITY_REQUIRED", "capability": "BILLING_VIEW"})
    rows = _office_invoice_projection(db, office_id, scope=scope)
    return {"office_id": office_id, "items": rows, "total": len(rows), "source_of_truth": "CANONICAL_BILLING_EVENTS"}


@router.get("/offices/{office_id}/open-receivables")
def office_open_receivables(office_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    if not db.get(ConsultancyOffice, office_id):
        raise HTTPException(404, {"code": "OFFICE_NOT_FOUND"})
    scope = _view_scope(db, principal)
    if office_id not in scope.office_ids and not any(db.get(Project, item) and db.get(Project, item).office_id == office_id for item in scope.project_ids):
        raise HTTPException(403, {"code": "SCOPED_FINANCE_CAPABILITY_REQUIRED", "capability": "BILLING_VIEW"})
    rows = _office_invoice_projection(db, office_id, open_only=True, scope=scope)
    total_open = sum((_d(row.get("outstanding_amount") or 0) for row in rows), Decimal("0"))
    return {"office_id": office_id, "items": rows, "total": len(rows), "aggregate_outstanding_amount": str(_money(total_open)), "source_of_truth": "CANONICAL_BILLING_EVENTS"}


@router.get("/invoices/{invoice_id}")
def get_invoice(invoice_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    invoice, contract, revision, plan_revision, project = _invoice_revision(db, invoice_id)
    _authorize_view(db, request, principal, project_id=invoice.project_id, client_account_id=invoice.client_account_id, contract_id=invoice.contract_id)
    references = db.scalars(select(InvoiceReference).where(InvoiceReference.invoice_revision_id == revision.id)).all()
    approvals = db.scalars(select(InvoiceApprovalRecord).where(InvoiceApprovalRecord.invoice_revision_id == revision.id)).all()
    issue = db.scalar(select(InvoiceIssueEvent).where(InvoiceIssueEvent.invoice_id == invoice.id))
    artifact = db.get(RenderedArtifact, issue.rendered_artifact_id) if issue else None
    deliveries = db.scalars(select(InvoiceDeliveryEvent).where(InvoiceDeliveryEvent.invoice_id == invoice.id).order_by(InvoiceDeliveryEvent.delivered_at)).all()
    acknowledgments = db.scalars(select(InvoiceAcknowledgment).where(InvoiceAcknowledgment.invoice_id == invoice.id).order_by(InvoiceAcknowledgment.acknowledged_at)).all()
    follow_ups = db.scalars(select(ReceivableFollowUp).where(ReceivableFollowUp.invoice_id == invoice.id).order_by(ReceivableFollowUp.created_at.desc())).all()
    allocations = db.scalars(select(InvoicePaymentAllocation).where(InvoicePaymentAllocation.invoice_id == invoice.id).order_by(InvoicePaymentAllocation.allocated_at)).all()
    resolutions = db.scalars(select(ReceivableResolution).where(ReceivableResolution.invoice_id == invoice.id).order_by(ReceivableResolution.created_at)).all()
    return {"invoice": _row(invoice), "contract": _row(contract), "project": _row(project), "client": _row(db.get(ClientAccount, invoice.client_account_id)) if invoice.client_account_id else None, "revision": _row(revision), "lines": [_row(x) for x in _lines(db, revision.id)], "references": [_row(x) for x in references], "approvals": [_row(x) for x in approvals], "issue": _row(issue), "artifact": _row(artifact), "communications": {"state": _communication_state(db, invoice.id), "deliveries": [_row(x) for x in deliveries], "acknowledgments": [_row(x) for x in acknowledgments]}, "receivable": _receivable(db, invoice, revision), "allocations": [_row(x) for x in allocations], "resolutions": [_row(x) for x in resolutions], "follow_ups": [_row(x) for x in follow_ups], "precheck": _precheck(db, invoice, contract, revision, plan_revision), "settlement": "DEFERRED_TO_FINANCIAL_SETTLEMENT"}


@router.get("/invoices/{invoice_id}/precheck")
def invoice_precheck(invoice_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    invoice, contract, revision, plan_revision, _project = _invoice_revision(db, invoice_id)
    _authorize_view(db, request, principal, project_id=invoice.project_id, client_account_id=invoice.client_account_id, contract_id=invoice.contract_id)
    return {**_precheck(db, invoice, contract, revision, plan_revision), "invoice_id": invoice.id, "revision_id": revision.id, "action_boundary": {"accept": "HUMAN_ONLY", "issue": "HUMAN_ONLY", "ai_protected_action_authority": 0}}


@router.post("/invoices/{invoice_id}/clone")
def clone_invoice(invoice_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, PLAN_WRITE, "INVOICE_CREATE")
    source, contract, previous, plan_revision, project = _invoice_revision(db, invoice_id)
    _authorize(db, request, principal, capability="INVOICE_CREATE", roles=PLAN_WRITE, project_id=project.id if project else source.project_id, client_account_id=source.client_account_id or contract.client_account_id)
    if not plan_revision:
        raise HTTPException(409, {"code": "BILLING_PLAN_REVISION_REQUIRED"})
    key = str(payload.get("idempotency_key") or "").strip()
    if not key:
        raise HTTPException(422, {"code": "INVOICE_CLONE_IDEMPOTENCY_KEY_REQUIRED"})
    prior = db.scalar(select(Invoice).where(Invoice.source_clone_id == source.id, Invoice.clone_idempotency_key == key))
    if prior:
        return {"invoice": _row(prior), "source_invoice_id": source.id, "copied_lifecycle_events": False}
    service_start = _date(payload["service_period_start"], field="service_period_start") if payload.get("service_period_start") else None
    service_end = _date(payload["service_period_end"], field="service_period_end") if payload.get("service_period_end") else None
    service_label = str(payload.get("service_period_label") or "").strip() or None
    if not ((service_start and service_end) or service_label):
        raise HTTPException(422, {"code": "STRUCTURED_SERVICE_PERIOD_REQUIRED"})
    if service_end and service_start and service_end < service_start:
        raise HTTPException(422, {"code": "SERVICE_PERIOD_INVALID"})
    clone = Invoice(contract_id=source.contract_id, project_id=source.project_id, client_account_id=source.client_account_id, billing_plan_id=source.billing_plan_id, invoice_reference=f"DRAFT-{uuid4().hex[:12].upper()}", invoice_ref_status="NOT_ALLOCATED", status="DRAFT", source_clone_id=source.id, clone_idempotency_key=key)
    db.add(clone); db.flush()
    invoice_date = _date(payload.get("invoice_date") or date.today().isoformat(), field="invoice_date")
    next_revision = InvoiceRevision(invoice_id=clone.id, revision_number=1, controlling_contract_revision_id=previous.controlling_contract_revision_id, billing_plan_revision_id=previous.billing_plan_revision_id, status="DRAFT", invoice_date=invoice_date, service_period=service_label or previous.service_period, service_period_start=service_start, service_period_end=service_end, service_period_label=service_label, description=payload.get("description") or previous.description, currency=previous.currency, contract_project_context_snapshot=previous.contract_project_context_snapshot or {}, source_snapshot={"clone_of_invoice_id": source.id, "copied_fields": ["current_valid_context", "permitted_invoice_lines"], "excluded_lifecycle": ["accept", "issue", "delivery", "acknowledgment", "client_approval", "payment", "allocation", "follow_up", "resolution"]})
    _configure_due_date(next_revision, invoice_date=invoice_date, basis=_due_basis(payload.get("due_date_basis")), offset_days=int(payload["due_days"]) if payload.get("due_days") is not None else None, fixed_date=_date(payload["due_date"], field="due_date") if payload.get("due_date") else None)
    db.add(next_revision); db.flush(); clone.current_revision_id = next_revision.id
    for line in _lines(db, previous.id):
        db.add(InvoiceLineItem(invoice_revision_id=next_revision.id, sequence=line.sequence, line_role=line.line_role, item_code=line.item_code, description=line.description, quantity=line.quantity, unit=line.unit, unit_price=line.unit_price, currency=line.currency, calculated_line_amount=line.calculated_line_amount, billing_milestone_id=line.billing_milestone_id, affects_payable_total=line.affects_payable_total, source_reference=line.source_reference))
    _calculate_revision(db, next_revision); _lineage(db, request, project.id if project else None, "Invoice", source.id, "Invoice", clone.id, "INVOICE_CLONED_AS_NEW_DRAFT"); _audit(db, request, "INVOICE_CLONED", "Invoice", clone.id, _actor(request, payload), {"source_invoice_id": source.id, "copied_lifecycle_events": False}); db.commit()
    return {"invoice": _row(clone), "revision": _row(next_revision), "lines": [_row(x) for x in _lines(db, next_revision.id)], "source_invoice_id": source.id, "copied_lifecycle_events": False}


@router.post("/invoices/{invoice_id}/revisions")
def create_invoice_revision(invoice_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, PLAN_WRITE, "INVOICE_EDIT_DRAFT")
    invoice, contract, previous, plan_revision, project = _invoice_revision(db, invoice_id)
    _authorize(db, request, principal, capability="INVOICE_REVISION_CREATE", roles=PLAN_WRITE, project_id=project.id if project else invoice.project_id, client_account_id=invoice.client_account_id or contract.client_account_id)
    if invoice.status in {"ISSUED", "VOIDED"} or previous.status in {"ACCEPTED_INTERNAL", "ISSUED"}:
        raise HTTPException(409, {"code": "ISSUED_OR_ACCEPTED_INVOICE_IMMUTABLE"})
    if not plan_revision:
        raise HTTPException(409, {"code": "BILLING_PLAN_REVISION_REQUIRED"})
    number = (db.scalar(select(func.max(InvoiceRevision.revision_number)).where(InvoiceRevision.invoice_id == invoice.id)) or 0) + 1
    next_invoice_date = _date(payload.get("invoice_date") or previous.invoice_date or date.today().isoformat(), field="invoice_date")
    service_start = _date(payload["service_period_start"], field="service_period_start") if payload.get("service_period_start") else previous.service_period_start
    service_end = _date(payload["service_period_end"], field="service_period_end") if payload.get("service_period_end") else previous.service_period_end
    if service_start and service_end and service_end < service_start:
        raise HTTPException(422, {"code": "SERVICE_PERIOD_INVALID"})
    next_revision = InvoiceRevision(invoice_id=invoice.id, revision_number=number, controlling_contract_revision_id=previous.controlling_contract_revision_id, billing_plan_revision_id=previous.billing_plan_revision_id, status="DRAFT", supersedes_revision_id=previous.id, invoice_date=next_invoice_date, description=payload.get("description") or previous.description, service_period=payload.get("service_period") or previous.service_period, service_period_start=service_start, service_period_end=service_end, service_period_label=payload.get("service_period_label") or previous.service_period_label or payload.get("service_period") or previous.service_period, currency=previous.currency, contract_project_context_snapshot=previous.contract_project_context_snapshot or {}, source_snapshot={**(previous.source_snapshot or {}), "supersedes_revision_id": previous.id, "reason": payload.get("reason")})
    _configure_due_date(next_revision, invoice_date=next_invoice_date, basis=_due_basis(payload.get("due_date_basis")) or previous.due_date_basis, offset_days=int(payload["due_days"]) if payload.get("due_days") is not None else previous.due_date_offset_days, fixed_date=_date(payload["due_date"], field="due_date") if payload.get("due_date") else previous.due_date_fixed_date)
    db.add(next_revision); db.flush()
    prior_lines = _lines(db, previous.id)
    for line in prior_lines:
        db.add(InvoiceLineItem(invoice_revision_id=next_revision.id, sequence=line.sequence, line_role=line.line_role, item_code=line.item_code, description=line.description, quantity=line.quantity, unit=line.unit, unit_price=line.unit_price, currency=line.currency, calculated_line_amount=line.calculated_line_amount, billing_milestone_id=line.billing_milestone_id, affects_payable_total=line.affects_payable_total, source_reference=line.source_reference))
    invoice.current_revision_id = next_revision.id; invoice.status = "DRAFT"; _calculate_revision(db, next_revision); _audit(db, request, "INVOICE_REVISION_CREATED", "InvoiceRevision", next_revision.id, _actor(request, payload), {"supersedes_revision_id": previous.id}); db.commit()
    return {"invoice": _row(invoice), "revision": _row(next_revision), "lines": [_row(x) for x in _lines(db, next_revision.id)]}


@router.post("/invoice-revisions/{revision_id}/calculate")
def calculate_invoice(revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, PLAN_WRITE, "INVOICE_EDIT_DRAFT")
    revision = db.get(InvoiceRevision, revision_id)
    if not revision or revision.status in {"ACCEPTED_INTERNAL", "ISSUED"}:
        raise HTTPException(409, {"code": "INVOICE_REVISION_IMMUTABLE"})
    invoice, contract, _revision, _plan_revision, project = _invoice_revision(db, revision.invoice_id, revision.id)
    _authorize(db, request, principal, capability="INVOICE_CALCULATE", roles=PLAN_WRITE, project_id=project.id if project else invoice.project_id, client_account_id=invoice.client_account_id or contract.client_account_id)
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
def add_invoice_reference(revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, PLAN_WRITE, "INVOICE_REFERENCE_MANAGE")
    revision = db.get(InvoiceRevision, revision_id)
    if not revision or revision.status in {"ISSUED"}:
        raise HTTPException(409, {"code": "INVOICE_REVISION_IMMUTABLE"})
    invoice, contract, _revision, _plan_revision, project = _invoice_revision(db, revision.invoice_id, revision.id)
    _authorize(db, request, principal, capability="INVOICE_REFERENCE", roles=PLAN_WRITE, project_id=project.id if project else invoice.project_id, client_account_id=invoice.client_account_id or contract.client_account_id)
    value = str(payload.get("value") or "").strip(); reference_type = str(payload.get("reference_type") or "").strip().upper()
    if not value or not reference_type:
        raise HTTPException(422, {"code": "TYPED_REFERENCE_REQUIRED"})
    item = InvoiceReference(invoice_revision_id=revision.id, reference_type=reference_type, value=value, issuer_or_source=payload.get("issuer_or_source"), issued_at=datetime.fromisoformat(payload["issued_at"]) if payload.get("issued_at") else None, source_document_version_id=payload.get("source_document_version_id"), status=str(payload.get("status") or "PENDING_VERIFICATION").upper(), notes=payload.get("notes"))
    db.add(item); db.flush(); _audit(db, request, "INVOICE_REFERENCE_RECORDED", "InvoiceReference", item.id, _actor(request, payload), {"invoice_revision_id": revision.id, "reference_type": reference_type}); db.commit(); return _row(item)


@router.post("/invoice-revisions/{revision_id}/approvals")
def add_invoice_approval(revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "INVOICE_APPROVAL_VERIFY")
    revision = db.get(InvoiceRevision, revision_id)
    if not revision or revision.status == "ISSUED": raise HTTPException(409, {"code": "INVOICE_REVISION_IMMUTABLE"})
    invoice, contract, _revision, _plan_revision, project = _invoice_revision(db, revision.invoice_id, revision.id)
    _authorize(db, request, principal, capability="INVOICE_APPROVAL", roles=OWNER, project_id=project.id if project else invoice.project_id, client_account_id=invoice.client_account_id or contract.client_account_id)
    item = InvoiceApprovalRecord(invoice_revision_id=revision.id, approval_type=str(payload.get("approval_type") or "CONFIGURED_APPROVAL"), status=str(payload.get("status") or "PENDING").upper(), approval_reference=payload.get("approval_reference"), approving_party_or_body=payload.get("approving_party_or_body"), decision_date=_date(payload["decision_date"], field="decision_date") if payload.get("decision_date") else None, source_document_version_id=payload.get("source_document_version_id"), notes=payload.get("notes"), verified_by=_actor(request, payload) if str(payload.get("status") or "").upper() == "VERIFIED" else None, verified_at=datetime.now(timezone.utc) if str(payload.get("status") or "").upper() == "VERIFIED" else None)
    db.add(item); db.flush()
    invoice = db.get(Invoice, revision.invoice_id)
    if item.status in {"VERIFIED", "APPROVED", "CLIENT_APPROVED"}:
        _derive_due_date(revision, event_type="CLIENT_APPROVAL" if item.approval_type in {"CLIENT_APPROVAL", "CLIENT_CERTIFICATION"} else "OTHER_VERIFIED_EVENT", event_id=item.id, event_at=item.decision_date or datetime.now(timezone.utc))
    _lineage(db, request, invoice.project_id if invoice else None, "InvoiceRevision", revision.id, "InvoiceApprovalRecord", item.id, "INVOICE_APPROVAL_REFERENCE")
    _audit(db, request, "INVOICE_APPROVAL_REFERENCE_RECORDED", "InvoiceApprovalRecord", item.id, _actor(request, payload), {"approval_type": item.approval_type, "status": item.status, "due_date_derived": revision.due_date_source_event_id == item.id}); db.commit(); return _row(item)


@router.post("/invoice-revisions/{revision_id}/deliveries")
def record_invoice_delivery(revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "INVOICE_DELIVERY_RECORD")
    revision = db.get(InvoiceRevision, revision_id)
    if not revision:
        raise HTTPException(404, {"code": "INVOICE_REVISION_NOT_FOUND"})
    invoice = db.get(Invoice, revision.invoice_id)
    contract = db.get(Contract, invoice.contract_id) if invoice else None
    _authorize(db, request, principal, capability="INVOICE_DELIVERY", roles=OWNER, project_id=invoice.project_id if invoice else None, client_account_id=invoice.client_account_id if invoice else (contract.client_account_id if contract else None))
    issue = db.scalar(select(InvoiceIssueEvent).where(InvoiceIssueEvent.invoice_id == invoice.id, InvoiceIssueEvent.invoice_revision_id == revision.id))
    if not issue or revision.status != "ISSUED":
        raise HTTPException(409, {"code": "ISSUED_INVOICE_REQUIRED"})
    key = str(payload.get("idempotency_key") or "").strip()
    if not key:
        raise HTTPException(422, {"code": "DELIVERY_IDEMPOTENCY_KEY_REQUIRED"})
    prior = db.scalar(select(InvoiceDeliveryEvent).where(InvoiceDeliveryEvent.idempotency_key == key))
    if prior:
        return {"delivery": _row(prior), "invoice": _row(invoice), "revision": _row(revision), "receivable": _receivable(db, invoice, revision)}
    channel = str(payload.get("channel") or "").upper()
    if channel not in DELIVERY_CHANNELS:
        raise HTTPException(422, {"code": "DELIVERY_CHANNEL_NOT_SUPPORTED", "allowed": sorted(DELIVERY_CHANNELS)})
    delivered_at = datetime.fromisoformat(str(payload.get("delivered_at") or datetime.now(timezone.utc).isoformat()))
    evidence_id = payload.get("evidence_document_version_id")
    _validate_document_evidence(db, evidence_id, db.get(Project, invoice.project_id) if invoice.project_id else None, not_found_code="DELIVERY_EVIDENCE_NOT_FOUND", mismatch_code="CROSS_PROJECT_BILLING_CONTEXT_DENIED")
    delivery_reference = str(payload.get("delivery_reference") or "").strip()
    evidence_required = channel in {"EMAIL", "WHATSAPP", "IN_PERSON", "COURIER"} or channel in {"PORTAL", "OTHER"}
    if evidence_required and not evidence_id and not delivery_reference:
        raise HTTPException(409, {"code": "DELIVERY_EVIDENCE_REQUIRED", "channel": channel})
    if channel == "WHATSAPP" and not evidence_id:
        raise HTTPException(409, {"code": "WHATSAPP_DELIVERY_ACK_REQUIRED"})
    delivery = InvoiceDeliveryEvent(invoice_id=invoice.id, issued_revision_id=revision.id, issue_event_id=issue.id, channel=channel, recipient_snapshot=payload.get("recipient_snapshot") or {}, delivered_at=delivered_at, delivery_reference=delivery_reference or None, evidence_document_version_id=evidence_id, recorded_by=_actor(request, payload), status="RECORDED", notes=payload.get("notes"), idempotency_key=key)
    db.add(delivery); db.flush()
    _derive_due_date(revision, event_type="DELIVERY", event_id=delivery.id, event_at=delivered_at)
    _lineage(db, request, invoice.project_id, "InvoiceIssueEvent", issue.id, "InvoiceDeliveryEvent", delivery.id, "INVOICE_DELIVERY_RECORD")
    _audit(db, request, "INVOICE_DELIVERY_RECORDED", "InvoiceDeliveryEvent", delivery.id, _actor(request, payload), {"invoice_id": invoice.id, "channel": channel, "due_date_derived": revision.due_date_source_event_id == delivery.id})
    db.commit()
    return {"delivery": _row(delivery), "invoice": _row(invoice), "revision": _row(revision), "receivable": _receivable(db, invoice, revision)}


@router.get("/invoices/{invoice_id}/communications")
def invoice_communications(invoice_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(404, {"code": "INVOICE_NOT_FOUND"})
    _authorize_view(db, request, principal, project_id=invoice.project_id, client_account_id=invoice.client_account_id, contract_id=invoice.contract_id)
    return {"communication_state": _communication_state(db, invoice.id), "issues": [_row(x) for x in db.scalars(select(InvoiceIssueEvent).where(InvoiceIssueEvent.invoice_id == invoice.id).order_by(InvoiceIssueEvent.issued_at)).all()], "deliveries": [_row(x) for x in db.scalars(select(InvoiceDeliveryEvent).where(InvoiceDeliveryEvent.invoice_id == invoice.id).order_by(InvoiceDeliveryEvent.delivered_at)).all()], "acknowledgments": [_row(x) for x in db.scalars(select(InvoiceAcknowledgment).where(InvoiceAcknowledgment.invoice_id == invoice.id).order_by(InvoiceAcknowledgment.acknowledged_at)).all()]}


@router.post("/invoices/{invoice_id}/acknowledgments")
def record_invoice_acknowledgment(invoice_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "INVOICE_ACKNOWLEDGMENT_RECORD")
    invoice = db.get(Invoice, invoice_id)
    issue = db.scalar(select(InvoiceIssueEvent).where(InvoiceIssueEvent.invoice_id == invoice_id)) if invoice else None
    revision = db.get(InvoiceRevision, issue.invoice_revision_id) if issue else None
    if not invoice or not issue or not revision:
        raise HTTPException(409, {"code": "ISSUED_INVOICE_REQUIRED"})
    contract = db.get(Contract, invoice.contract_id)
    _authorize(db, request, principal, capability="INVOICE_ACKNOWLEDGMENT", roles=OWNER, project_id=invoice.project_id, client_account_id=invoice.client_account_id or (contract.client_account_id if contract else None))
    key = str(payload.get("idempotency_key") or "").strip()
    if not key:
        raise HTTPException(422, {"code": "ACKNOWLEDGMENT_IDEMPOTENCY_KEY_REQUIRED"})
    prior = db.scalar(select(InvoiceAcknowledgment).where(InvoiceAcknowledgment.idempotency_key == key))
    if prior:
        return {"acknowledgment": _row(prior), "receivable": _receivable(db, invoice, revision)}
    acknowledged_at = datetime.fromisoformat(str(payload.get("acknowledged_at") or datetime.now(timezone.utc).isoformat()))
    evidence_id = payload.get("source_document_version_id")
    if evidence_id:
        evidence_version = db.get(DocumentVersion, evidence_id)
        evidence_document = db.get(Document, evidence_version.document_id) if evidence_version else None
        if not evidence_version or not evidence_document:
            raise HTTPException(404, {"code": "ACKNOWLEDGMENT_EVIDENCE_NOT_FOUND"})
        if invoice.project_id and evidence_document.project_id not in {None, invoice.project_id}:
            raise HTTPException(403, {"code": "CROSS_PROJECT_BILLING_CONTEXT_DENIED"})
    item = InvoiceAcknowledgment(invoice_id=invoice.id, issued_revision_id=revision.id, acknowledgment_reference=payload.get("acknowledgment_reference"), acknowledged_at=acknowledged_at, source_document_version_id=evidence_id, recorded_by=_actor(request, payload), status="RECORDED", notes=payload.get("notes"), idempotency_key=key)
    db.add(item); db.flush()
    _derive_due_date(revision, event_type="ACKNOWLEDGMENT", event_id=item.id, event_at=acknowledged_at)
    _lineage(db, request, invoice.project_id, "InvoiceDeliveryEvent", issue.id, "InvoiceAcknowledgment", item.id, "INVOICE_ACKNOWLEDGMENT_RECORD")
    _audit(db, request, "INVOICE_ACKNOWLEDGMENT_RECORDED", "InvoiceAcknowledgment", item.id, _actor(request, payload), {"invoice_id": invoice.id, "due_date_derived": revision.due_date_source_event_id == item.id})
    db.commit()
    return {"acknowledgment": _row(item), "revision": _row(revision), "receivable": _receivable(db, invoice, revision)}


@router.post("/invoice-revisions/{revision_id}/accept")
def accept_invoice(revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "INVOICE_ACCEPT")
    invoice, contract, revision, plan_revision, project = _invoice_revision(db, str(payload.get("invoice_id") or ""), revision_id) if payload.get("invoice_id") else (None, None, db.get(InvoiceRevision, revision_id), None, None)
    if invoice is None:
        if not revision: raise HTTPException(404, {"code": "INVOICE_REVISION_NOT_FOUND"})
        invoice, contract, revision, plan_revision, project = _invoice_revision(db, revision.invoice_id, revision.id)
    _authorize(db, request, principal, capability="INVOICE_ACCEPT", roles=OWNER, project_id=project.id if project else invoice.project_id, client_account_id=invoice.client_account_id or contract.client_account_id)
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
def create_financial_account(payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "FINANCIAL_ACCOUNT_MANAGE")
    _authorize(db, request, principal, capability="FINANCIAL_ACCOUNT_MANAGE", roles=OWNER, office_id=principal.office_id)
    item = FinancialAccountMaster(office_id=principal.office_id, legal_entity_party_id=payload.get("legal_entity_party_id"), legal_entity_ref=str(payload.get("legal_entity_ref") or "").strip(), account_name=str(payload.get("account_name") or "").strip(), status="DRAFT", created_by=_actor(request, payload))
    if not item.legal_entity_ref or not item.account_name: raise HTTPException(422, {"code": "LEGAL_ENTITY_AND_ACCOUNT_NAME_REQUIRED"})
    db.add(item); db.flush(); _audit(db, request, "FINANCIAL_ACCOUNT_MASTER_CREATED", "FinancialAccountMaster", item.id, _actor(request, payload), {"legal_entity_ref": item.legal_entity_ref, "status": item.status}); db.commit(); return _row(item)


@router.post("/financial-accounts/{master_id}/versions")
def create_financial_account_version(master_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "FINANCIAL_ACCOUNT_MANAGE")
    master = db.get(FinancialAccountMaster, master_id)
    if not master: raise HTTPException(404, {"code": "FINANCIAL_ACCOUNT_MASTER_NOT_FOUND"})
    _authorize(db, request, principal, capability="FINANCIAL_ACCOUNT_MANAGE", roles=OWNER, office_id=principal.office_id)
    version_number = (db.scalar(select(func.max(FinancialAccountVersion.version_number)).where(FinancialAccountVersion.financial_account_master_id == master.id)) or 0) + 1
    item = FinancialAccountVersion(financial_account_master_id=master.id, version_number=version_number, bank_name=str(payload.get("bank_name") or ""), account_name=str(payload.get("account_name") or master.account_name), account_reference=str(payload.get("account_reference") or ""), currency=str(payload.get("currency") or "").upper(), effective_from=_date(payload.get("effective_from") or date.today().isoformat(), field="effective_from"), effective_to=_date(payload["effective_to"], field="effective_to") if payload.get("effective_to") else None, status="DRAFT", payment_instruction_metadata=payload.get("payment_instruction_metadata") or {}, created_by=_actor(request, payload))
    if not item.bank_name or not item.account_reference or not item.currency: raise HTTPException(422, {"code": "FINANCIAL_ACCOUNT_FIELDS_REQUIRED"})
    db.add(item); db.flush(); _audit(db, request, "FINANCIAL_ACCOUNT_VERSION_CREATED", "FinancialAccountVersion", item.id, _actor(request, payload), {"master_id": master.id, "version_number": item.version_number, "currency": item.currency}); db.commit(); return _mask_account(item)


@router.post("/financial-account-versions/{version_id}/approve")
def approve_financial_account_version(version_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "FINANCIAL_ACCOUNT_APPROVE")
    item = db.get(FinancialAccountVersion, version_id)
    if not item: raise HTTPException(404, {"code": "FINANCIAL_ACCOUNT_VERSION_NOT_FOUND"})
    master = db.get(FinancialAccountMaster, item.financial_account_master_id)
    if not master: raise HTTPException(409, {"code": "FINANCIAL_ACCOUNT_MASTER_NOT_FOUND"})
    _authorize(db, request, principal, capability="FINANCIAL_ACCOUNT_APPROVE", roles=OWNER, office_id=principal.office_id)
    item.status = "ACTIVE"; item.approved_by = _actor(request, payload); item.approved_at = datetime.now(timezone.utc); master.status = "ACTIVE"; _audit(db, request, "FINANCIAL_ACCOUNT_VERSION_APPROVED", "FinancialAccountVersion", item.id, _actor(request, payload), {"master_id": master.id, "version_number": item.version_number, "currency": item.currency}); db.commit(); return _mask_account(item)


@router.post("/invoice-revisions/{revision_id}/issue")
def issue_invoice(revision_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "INVOICE_ISSUE")
    revision = db.get(InvoiceRevision, revision_id)
    if not revision: raise HTTPException(404, {"code": "INVOICE_REVISION_NOT_FOUND"})
    invoice, contract, revision, plan_revision, project = _invoice_revision(db, revision.invoice_id, revision.id)
    _authorize(db, request, principal, capability="INVOICE_ISSUE", roles=OWNER, project_id=project.id if project else invoice.project_id, client_account_id=invoice.client_account_id or contract.client_account_id)
    key = str(payload.get("idempotency_key") or "").strip()
    if not key: raise HTTPException(422, {"code": "ISSUE_IDEMPOTENCY_KEY_REQUIRED"})
    prior = db.scalar(select(InvoiceIssueEvent).where(InvoiceIssueEvent.idempotency_key == key))
    if prior: return {"invoice": _row(invoice), "revision": _row(revision), "issue": _row(prior)}
    existing = db.scalar(select(InvoiceIssueEvent).where(InvoiceIssueEvent.invoice_id == invoice.id))
    if existing: raise HTTPException(409, {"code": "INVOICE_ALREADY_ISSUED", "issue_event_id": existing.id})
    _require_issue_project_policy(db, project)
    if revision.status != "ACCEPTED_INTERNAL": raise HTTPException(409, {"code": "INVOICE_ACCEPT_REQUIRED"})
    precheck = _precheck(db, invoice, contract, revision, plan_revision)
    if precheck["result"] != "PASS": raise HTTPException(409, {"code": "INVOICE_ISSUE_PRECHECK_BLOCKED", "precheck": precheck})
    issue_date = revision.invoice_date or date.today()
    issue_event_id = str(uuid4())
    _derive_due_date(revision, event_type="ISSUE", event_id=issue_event_id, event_at=issue_date)
    account = _resolve_account(db, revision.currency or plan_revision.currency, issue_date, payload.get("financial_account_version_id"))
    account_master = db.get(FinancialAccountMaster, account.financial_account_master_id)
    expected_legal_entity = str((revision.contract_project_context_snapshot or {}).get("legal_entity_ref") or "").strip()
    if expected_legal_entity and account_master and account_master.legal_entity_ref != expected_legal_entity:
        raise HTTPException(409, {"code": "FINANCIAL_ACCOUNT_LEGAL_ENTITY_MISMATCH"})
    if not get_settings().synthetic_only and not expected_legal_entity:
        raise HTTPException(409, {"code": "FINANCIAL_ACCOUNT_LEGAL_ENTITY_BINDING_REQUIRED"})
    if not get_settings().synthetic_only and (not account_master or account_master.office_id != (project.office_id if project else None)):
        raise HTTPException(409, {"code": "FINANCIAL_ACCOUNT_OFFICE_BINDING_REQUIRED"})
    signer = _signer_evidence(db, payload, invoice=invoice, revision=revision, project=project, account_master=account_master, issue_at=datetime.now(timezone.utc))
    template = select_template(db, payload.get("template_version_id"), "INVOICE")
    official_ref = _allocate_invoice_ref(db, issue_date, _actor(request, payload), contract=contract, revision=revision)
    artifact = render_artifact(db, artifact_type="INVOICE", context_type="INVOICE_REVISION", context_id=revision.id, payload={"invoice_reference": official_ref, "contract_reference": contract.contract_reference, "client_account_id": contract.client_account_id, "project_id": project.id if project else None, "project_context": revision.contract_project_context_snapshot or {}, "description": revision.description, "currency": revision.currency, "lines": [_row(x) for x in _lines(db, revision.id)], "gross_charge_total": str(revision.gross_charge_total), "payable_total": str(revision.payable_total), "amount_in_words": revision.amount_in_words, "invoice_date": issue_date.isoformat(), "due_date": revision.due_date.isoformat() if revision.due_date else None, "due_date_basis": revision.due_date_basis, "financial_account_version_id": account.id, "source_sample_policy": "REFERENCE_ONLY"}, source_revision_ids=[contract.id, revision.controlling_contract_revision_id, plan_revision.id if plan_revision else revision.id], template_version_id=template.id, actor=_actor(request, payload), correlation_id=_corr(request), project_id=project.id if project else None)
    event = InvoiceIssueEvent(id=issue_event_id, invoice_id=invoice.id, invoice_revision_id=revision.id, official_invoice_ref=official_ref, invoice_date=issue_date, issued_by=_actor(request, payload), idempotency_key=key, template_version_id=template.id, financial_account_version_id=account.id, rendered_artifact_id=artifact.id, source_snapshot={"contract_revision_id": revision.controlling_contract_revision_id, "billing_plan_revision_id": revision.billing_plan_revision_id, "financial_account_version_id": account.id, "financial_account_legal_entity_ref": account_master.legal_entity_ref if account_master else None, "template_version_id": template.id, "artifact_id": artifact.id, "source13_signer_authority": signer})
    db.add(event); db.flush()
    if project:
        db.execute(select(Project).where(Project.id == project.id).with_for_update()).scalar_one()
    if project and invoice.project_invoice_ordinal is None:
        invoice.project_invoice_ordinal = (db.scalar(select(func.max(Invoice.project_invoice_ordinal)).where(Invoice.project_id == project.id)) or 0) + 1
    invoice.invoice_reference = official_ref; invoice.invoice_ref_status = "ALLOCATED"; invoice.status = "ISSUED"; revision.status = "ISSUED"
    for line in _lines(db, revision.id):
        if line.billing_milestone_id and line.affects_payable_total:
            milestone = db.get(BillingMilestone, line.billing_milestone_id); milestone.invoiced_amount = _money(_d(milestone.invoiced_amount or 0) + _line_total(line)); milestone.remaining_invoiceable_amount = _money(max(Decimal("0"), _d(milestone.calculated_amount or 0) - _d(milestone.invoiced_amount or 0)));
    _lineage(db, request, project.id if project else None, "InvoiceIssueEvent", event.id, "RenderedArtifact", artifact.id, "ISSUED_INVOICE_ARTIFACT"); _audit(db, request, "INVOICE_ISSUED", "InvoiceIssueEvent", event.id, _actor(request, payload), {"invoice_id": invoice.id, "official_invoice_ref": official_ref, "template_version_id": template.id, "financial_account_version_id": account.id, "artifact_id": artifact.id}); db.commit()
    return {"invoice": _row(invoice), "revision": _row(revision), "issue": _row(event), "artifact": _row(artifact), "financial_account": _mask_account(account)}


def _allocate_invoice_ref(db: Session, issue_date: date, actor: str, *, contract: Contract, revision: InvoiceRevision) -> str:
    policy = db.scalar(select(InvoiceNumberingPolicy).where(InvoiceNumberingPolicy.policy_key == "INVOICE" ).with_for_update())
    if not get_settings().synthetic_only:
        gate = canonical_numbering_gate(lambda key, default=False: runtime_decision_value(db, key, default))
        if not gate["ready"]:
            raise HTTPException(409, {"code": "LEGACY_FINANCE_RECONCILIATION_REQUIRED_BEFORE_PRODUCTION_NUMBERING", "required_controls": gate["controls"]})
    if not policy:
        policy = InvoiceNumberingPolicy(policy_key="INVOICE", prefix="INV-AMEC", padding=6, next_number=1, version="V1", status="ACTIVE", no_reuse=True, updated_by=actor); db.add(policy); db.flush()
    if policy.status != "ACTIVE": raise HTTPException(409, {"code": "INVOICE_NUMBERING_POLICY_INACTIVE"})
    context = revision.contract_project_context_snapshot or {}
    project_reference_segment = contract.project_opportunity_ref or context.get("project_opportunity_ref") or context.get("project_reference")
    try:
        value = compose_amec_invoice_reference(issue_year=issue_date.year, project_reference_segment=str(project_reference_segment or ""), global_sequence=policy.next_number, sequence_padding=policy.padding)
    except ValueError as exc:
        raise HTTPException(409, {"code": "COMMERCIAL_PROJECT_REFERENCE_REQUIRED"}) from exc
    policy.next_number += 1; policy.updated_by = actor; return value


def _receivable(db: Session, invoice: Invoice, revision: InvoiceRevision | None) -> dict[str, Any]:
    if not revision or invoice.status != "ISSUED": return {"state": "NOT_ISSUED", "issued_payable_amount": None, "verified_paid_amount": "0.00", "resolved_non_cash_amount": "0.00", "financially_resolved_amount": "0.00", "outstanding_amount": None, "overpayment_amount": "0.00", "due_date": None, "communication_state": _communication_state(db, invoice.id)}
    paid = sum((_d(item.allocated_amount) for item in db.scalars(select(InvoicePaymentAllocation).where(InvoicePaymentAllocation.invoice_id == invoice.id, InvoicePaymentAllocation.status == "ALLOCATED")).all()), Decimal("0"))
    resolved_non_cash = sum((_d(item.amount) for item in db.scalars(select(ReceivableResolution).where(ReceivableResolution.invoice_id == invoice.id, ReceivableResolution.status == "ACTIVE")).all()), Decimal("0"))
    payable = _d(revision.payable_total or 0); financially_resolved = paid + resolved_non_cash; outstanding = payable - financially_resolved; over = max(Decimal("0"), -outstanding); now = date.today()
    communication_state = _communication_state(db, invoice.id)
    state = "RESOLVED_NON_CASH" if outstanding <= 0 and resolved_non_cash > 0 else "PAID" if outstanding <= 0 else "PARTIALLY_PAID" if financially_resolved > 0 else "AWAITING_DUE_EVENT" if revision.due_date_status == "PENDING_EVENT" or not revision.due_date else "OVERDUE" if revision.due_date < now else "DUE" if revision.due_date <= now else "NOT_DUE"
    return {"state": state, "resolution_state": "NON_CASH" if resolved_non_cash > 0 else "NONE", "communication_state": communication_state, "issued_payable_amount": str(_money(payable)), "verified_paid_amount": str(_money(paid)), "resolved_non_cash_amount": str(_money(resolved_non_cash)), "financially_resolved_amount": str(_money(financially_resolved)), "outstanding_amount": str(_money(max(Decimal("0"), outstanding))), "overpayment_amount": str(_money(over)), "due_date": revision.due_date.isoformat() if revision.due_date else None, "due_date_basis": revision.due_date_basis, "due_date_status": revision.due_date_status}


def _payment_credit(db: Session, payment: PaymentReceipt) -> dict[str, Any]:
    allocated = sum(
        (_d(item.allocated_amount) for item in db.scalars(
            select(InvoicePaymentAllocation).where(
                InvoicePaymentAllocation.payment_receipt_id == payment.id,
                InvoicePaymentAllocation.status == "ALLOCATED",
            )
        ).all()),
        Decimal("0"),
    )
    amount = _d(payment.amount)
    if payment.verification_status == "REVERSED":
        state = "REVERSED"
        unallocated = Decimal("0")
    elif payment.verification_status != "VERIFIED":
        state = "CLIENT_PREPAYMENT_RECORDED" if not allocated else "PAYMENT_OBSERVED_WITH_ALLOCATIONS"
        unallocated = Decimal("0")
    else:
        unallocated = max(Decimal("0"), amount - allocated)
        state = "UNALLOCATED_CLIENT_CREDIT" if unallocated > 0 else "ALLOCATED_TO_INVOICE"
    return {
        "payment_id": payment.id,
        "client_account_id": payment.client_account_id,
        "contract_id": payment.contract_id,
        "project_id": payment.project_id,
        "currency": payment.currency,
        "received_amount": str(_money(amount)),
        "allocated_amount": str(_money(allocated)),
        "unallocated_balance": str(_money(unallocated)),
        "verification_status": payment.verification_status,
        "state": state,
    }


def _invoice_projection(db: Session, invoice: Invoice) -> dict[str, Any]:
    revision = db.get(InvoiceRevision, invoice.current_revision_id) if invoice.current_revision_id else None
    receivable = _receivable(db, invoice, revision)
    follow_ups = db.scalars(select(ReceivableFollowUp).where(ReceivableFollowUp.invoice_id == invoice.id).order_by(ReceivableFollowUp.created_at.desc())).all()
    latest_follow_up = follow_ups[0] if follow_ups else None
    return {
        "invoice_id": invoice.id,
        "invoice_reference": invoice.invoice_reference,
        "project_invoice_ordinal": invoice.project_invoice_ordinal,
        "contract_id": invoice.contract_id,
        "project_id": invoice.project_id,
        "client_account_id": invoice.client_account_id,
        "status": invoice.status,
        "revision_id": revision.id if revision else None,
        "revision_number": revision.revision_number if revision else None,
        "billing_period": revision.service_period if revision else None,
        "planned_collection_date": revision.planned_collection_date.isoformat() if revision and revision.planned_collection_date else None,
        "invoice_date": revision.invoice_date.isoformat() if revision and revision.invoice_date else None,
        "due_date": revision.due_date.isoformat() if revision and revision.due_date else None,
        "actual_collection_date": revision.actual_collection_date.isoformat() if revision and revision.actual_collection_date else None,
        "actual_collection_date_source": revision.actual_collection_date_source if revision else None,
        "payable_amount": str(_money(_d(revision.payable_total or 0))) if revision and revision.payable_total is not None else None,
        "currency": revision.currency if revision else None,
        "cash_allocated_amount": receivable.get("verified_paid_amount", "0.00"),
        "non_cash_resolved_amount": receivable.get("resolved_non_cash_amount", "0.00"),
        "outstanding_amount": receivable.get("outstanding_amount"),
        "receivable_state": receivable.get("state"),
        "collection_status": "NEED_ACTION" if _d(receivable.get("outstanding_amount") or 0) > 0 else "RESOLVED",
        "follow_up_count": len(follow_ups),
        "latest_follow_up": _row(latest_follow_up),
    }


def _billing_context(db: Session, *, contract_id: str | None, project_id: str | None, client_account_id: str | None) -> dict[str, Any]:
    contract = db.get(Contract, contract_id) if contract_id else None
    project = db.get(Project, project_id) if project_id else None
    client = db.get(ClientAccount, client_account_id) if client_account_id else None
    return {
        "client": {"id": client.id, "name": client.display_name, "reference": client.client_reference} if client else None,
        "project": {"id": project.id, "name": project.project_name, "reference": project.project_code or project.project_number} if project else None,
        "contract": {"id": contract.id, "name": contract.contract_name, "reference": contract.contract_reference} if contract else None,
    }


def _capability_projection(effective: set[str]) -> dict[str, bool]:
    has = effective.__contains__
    return {
        "can_view": has("BILLING_VIEW"),
        "can_manage_plan": has("BILLING_PLAN_MANAGE"),
        "can_approve_plan": has("BILLING_PLAN_APPROVE"),
        "can_review_milestone": has("BILLING_MILESTONE_REVIEW"),
        "can_request_billable_stage": has("BILLING_READINESS_REQUEST"),
        "can_create_invoice": has("INVOICE_CREATE"),
        "can_edit_invoice": has("INVOICE_CALCULATE") or has("INVOICE_REVISION_CREATE"),
        "can_accept_invoice": has("INVOICE_ACCEPT"),
        "can_issue_invoice": has("INVOICE_ISSUE"),
        "can_record_delivery": has("INVOICE_DELIVERY"),
        "can_record_acknowledgment": has("INVOICE_ACKNOWLEDGMENT"),
        "can_record_payment": has("PAYMENT_RECORD"),
        "can_verify_payment": has("PAYMENT_VERIFY"),
        "can_allocate_payment": has("PAYMENT_ALLOCATE"),
        "can_reverse_payment": has("PAYMENT_REVERSE"),
        "can_record_follow_up": has("RECEIVABLE_FOLLOW_UP"),
        "can_resolve_receivable": has("RECEIVABLE_NON_CASH_RESOLVE"),
        "can_manage_financial_account": has("FINANCIAL_ACCOUNT_MANAGE"),
        "can_approve_financial_account": has("FINANCIAL_ACCOUNT_APPROVE"),
        "can_manage_fx_rate": has("BILLING_FX_RATE_MANAGE"),
        "can_edit_expected_exp": has("PROJECT_EXPECTED_EXP_EDIT"),
    }


RESOLVED_OWNER_POLICIES = {
    "FINANCE_SECRETARY_CAPABILITY_MAPPING": "SCOPED_CAPABILITY_ASSIGNMENT_WITHIN_EXISTING_PERSONA_MODEL",
    "GLOBAL_INVOICE_NUMBERING_POLICY": "CONTINUE_RECONCILED_HISTORICAL_AMEC_SEQUENCE_AND_FORMAT",
    "NON_QAR_QAR_CONVERSION_AND_PROVENANCE_POLICY": "GOVERNED_OWNER_EDITABLE_FX_RATE_RECORD",
    "EXPECTED_EXP_PERCENT_DEFINITION_AND_SOURCE": "OWNER_APPROVED_EDITABLE_PROJECT_FINANCE_FIELD",
    "FINANCE_YTD_REPORTING_YEAR_BOUNDARY": "CALENDAR_YEAR",
}


def _policy_projection(db: Session) -> list[dict[str, Any]]:
    """Expose policy truth separately from runtime readiness facts."""
    rows: list[dict[str, Any]] = []
    for key, value in RESOLVED_OWNER_POLICIES.items():
        rows.append({"key": key, "policy_status": "RESOLVED", "effective_value": value})
    return rows


def _milestone_projection(db: Session, item: BillingMilestone) -> dict[str, Any]:
    plan_revision = db.get(BillingPlanRevision, item.billing_plan_revision_id)
    plan = db.get(BillingPlan, plan_revision.billing_plan_id) if plan_revision else None
    contract = db.get(Contract, plan_revision.contract_id) if plan_revision else None
    project = db.get(Project, item.source_snapshot.get("project_id")) if item.source_snapshot.get("project_id") else db.get(Project, plan_revision.project_id) if plan_revision and plan_revision.project_id else None
    client_id = plan_revision.client_account_id if plan_revision else None
    client = db.get(ClientAccount, client_id) if client_id else None
    invoice_rows = db.execute(
        select(InvoiceLineItem, Invoice)
        .join(InvoiceRevision, InvoiceRevision.id == InvoiceLineItem.invoice_revision_id)
        .join(Invoice, Invoice.id == InvoiceRevision.invoice_id)
        .where(InvoiceLineItem.billing_milestone_id == item.id)
        .order_by(Invoice.created_at)
    ).all()
    invoices: list[dict[str, Any]] = []
    actual_collected = Decimal("0")
    for line, invoice in invoice_rows:
        invoice_projection = _invoice_projection(db, invoice)
        invoices.append({
            "invoice_id": invoice.id,
            "invoice_reference": invoice.invoice_reference,
            "status": invoice.status,
            "amount": str(_money(_line_total(line))),
            "currency": line.currency,
        })
        actual_collected += sum(
            (_d(allocation.allocated_amount) for allocation in db.scalars(select(InvoicePaymentAllocation).where(InvoicePaymentAllocation.invoice_id == invoice.id, InvoicePaymentAllocation.billing_milestone_id == item.id, InvoicePaymentAllocation.status == "ALLOCATED")).all()),
            Decimal("0"),
        )
    calculated = _d(item.calculated_amount or 0)
    invoiced = _d(item.invoiced_amount or 0)
    remaining = max(Decimal("0"), _d(item.remaining_invoiceable_amount if item.remaining_invoiceable_amount is not None else calculated - invoiced))
    return {
        "id": item.id,
        "sequence": item.sequence,
        "name": item.name,
        "description": item.description,
        "currency": item.currency,
        "basis_type": item.basis_type,
        "basis_amount": str(_money(_d(item.basis_amount))) if item.basis_amount is not None else None,
        "percentage": str(item.percentage) if item.percentage is not None else None,
        "calculated_amount": str(_money(calculated)) if item.calculated_amount is not None else None,
        "trigger_type": item.trigger_type,
        "trigger_description": item.trigger_description,
        "eligibility_state": item.eligibility_state,
        "status": item.status,
        "billing_mode": plan_revision.billing_mode if plan_revision else None,
        "plan_id": plan.id if plan else None,
        "plan_revision_id": plan_revision.id if plan_revision else None,
        "contract_id": contract.id if contract else None,
        "project_id": project.id if project else None,
        "client_account_id": client_id,
        "context": _billing_context(db, contract_id=contract.id if contract else None, project_id=project.id if project else None, client_account_id=client_id),
        "invoiced_amount": str(_money(invoiced)),
        "actual_collected": str(_money(actual_collected)),
        "remaining_invoiceable": str(_money(remaining)),
        "invoiceable_now": item.eligibility_state == "ELIGIBLE" and remaining > 0,
        "invoices": invoices,
        "unattributed_historical_collection": str(_money(sum((_d(allocation.allocated_amount) for allocation in db.scalars(select(InvoicePaymentAllocation).where(InvoicePaymentAllocation.invoice_id.in_([row[1].id for row in invoice_rows]), InvoicePaymentAllocation.status == "ALLOCATED")).all() if allocation.billing_milestone_id is None), Decimal("0")))),
        "latest_eligibility": _row(db.scalar(select(BillingMilestoneEligibility).where(BillingMilestoneEligibility.billing_milestone_id == item.id).order_by(BillingMilestoneEligibility.evaluated_at.desc()))),
    }


def _payment_projection(db: Session, item: PaymentReceipt) -> dict[str, Any]:
    credit = _payment_credit(db, item)
    eligible_invoices = []
    for invoice in db.scalars(select(Invoice).where(Invoice.client_account_id == item.client_account_id, Invoice.contract_id == item.contract_id, Invoice.status == "ISSUED").order_by(Invoice.created_at)).all():
        if item.project_id and invoice.project_id not in {None, item.project_id}:
            continue
        projection = _invoice_projection(db, invoice)
        if str(projection.get("currency") or "").upper() == str(item.currency).upper() and _d(projection.get("outstanding_amount") or 0) > 0:
            revision = db.get(InvoiceRevision, invoice.current_revision_id) if invoice.current_revision_id else None
            milestone_ids = [line.billing_milestone_id for line in _lines(db, revision.id)] if revision else []
            eligible_invoices.append({"invoice_id": invoice.id, "invoice_reference": invoice.invoice_reference, "project_id": invoice.project_id, "outstanding_amount": projection.get("outstanding_amount"), "currency": projection.get("currency"), "milestone_ids": [value for value in milestone_ids if value]})
    return {
        "payment": _row(item),
        "credit": credit,
        "context": _billing_context(db, contract_id=item.contract_id, project_id=item.project_id, client_account_id=item.client_account_id),
        "evidence": {
            "primary": bool(item.evidence_document_version_id or item.evidence_reference),
            "receipt_voucher": bool(item.receipt_voucher_document_version_id or item.receipt_voucher_evidence_reference),
        },
        "allocations": [{**(_row(allocation) or {}), "milestone": _row(db.get(BillingMilestone, allocation.billing_milestone_id)) if allocation.billing_milestone_id else None} for allocation in db.scalars(select(InvoicePaymentAllocation).where(InvoicePaymentAllocation.payment_receipt_id == item.id).order_by(InvoicePaymentAllocation.allocated_at)).all()],
        "reversals": [_row(event) for event in db.scalars(select(PaymentReversalEvent).where(PaymentReversalEvent.payment_receipt_id == item.id).order_by(PaymentReversalEvent.created_at)).all()],
        "eligible_invoices": eligible_invoices,
    }


@router.get("/capabilities")
def billing_capabilities(
    request: Request,
    project_id: str | None = None,
    client_account_id: str | None = None,
    contract_id: str | None = None,
    invoice_id: str | None = None,
    payment_id: str | None = None,
    db: Session = Depends(get_db),
    role: Role = Depends(current_user_role),
    principal: AuthenticatedPrincipal = Depends(current_principal),
):
    _role(role, VIEW, "BILLING_VIEW")
    if invoice_id:
        invoice = db.get(Invoice, invoice_id)
        if invoice:
            project_id = invoice.project_id or project_id
            client_account_id = invoice.client_account_id or client_account_id
            contract_id = invoice.contract_id
    if payment_id:
        payment = db.get(PaymentReceipt, payment_id)
        if payment:
            project_id = payment.project_id or project_id
            client_account_id = payment.client_account_id or client_account_id
            contract_id = payment.contract_id
    contract = db.get(Contract, contract_id) if contract_id else None
    if contract:
        project_id = contract.project_id or project_id
        client_account_id = contract.client_account_id or client_account_id
    project = db.get(Project, project_id) if project_id else None
    office_id = project.office_id if project else None
    context = BillingAuthorizationContext(office_id=office_id, client_account_id=client_account_id, project_id=project_id)
    if any((project_id, client_account_id, contract_id, invoice_id, payment_id)):
        _authorize_view(db, request, principal, project_id=project_id, client_account_id=client_account_id, contract_id=contract_id)
    elif _view_scope(db, principal).empty:
        raise HTTPException(403, {"code": "SCOPED_FINANCE_CAPABILITY_REQUIRED", "capability": "BILLING_VIEW"})
    effective = effective_billing_capabilities(db, principal, context=context)
    return {
        "role": role.value,
        "capabilities": _capability_projection(effective),
        "effective_capabilities": sorted(effective),
        "authorization_scope": {"office_id": office_id, "client_account_id": client_account_id, "project_id": project_id},
        # Keep the established response contract while making the actual
        # source explicit in the adjacent field; booleans above are never
        # derived from the global Role.
        "authority_source": "SERVER_MUTATION_POLICY",
        "authorization_model": "PERSISTED_SCOPED_CAPABILITY_ASSIGNMENTS",
        "frontend_only_authority_grants": 0,
        "unresolved_owner_decisions": [],
        "resolved_owner_policies": RESOLVED_OWNER_POLICIES,
    }


@router.get("/command-center")
def billing_command_center(request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    scope = _view_scope(db, principal)
    invoices = db.scalars(select(Invoice).where(_scope_clause(Invoice, scope)).order_by(Invoice.created_at.desc())).all()
    invoice_rows: list[dict[str, Any]] = []
    for invoice in invoices:
        projection = _invoice_projection(db, invoice)
        invoice_rows.append({**projection, "context": _billing_context(db, contract_id=invoice.contract_id, project_id=invoice.project_id, client_account_id=invoice.client_account_id)})
    milestones = [_milestone_projection(db, item) for item in db.scalars(select(BillingMilestone).join(BillingPlanRevision).where(_scope_clause(BillingPlanRevision, scope)).order_by(BillingMilestone.sequence)).all()]
    payments = [_payment_projection(db, item) for item in db.scalars(select(PaymentReceipt).where(_scope_clause(PaymentReceipt, scope)).order_by(PaymentReceipt.received_date.desc(), PaymentReceipt.recorded_at.desc())).all()]
    open_receivables = [item for item in invoice_rows if _d(item.get("outstanding_amount") or 0) > 0]
    today = date.today()
    work: list[dict[str, Any]] = []
    for item in milestones:
        if item["invoiceable_now"]:
            work.append({"category": "MILESTONE_READY", "why": "The governed milestone is eligible and has invoiceable balance.", "next_action": "Prepare draft invoice", "authority_needed": "Billing plan/invoice preparation capability", "target": {"entity_type": "BILLING_MILESTONE", "entity_id": item["id"], "route": f"/billing/plans/{item['plan_id']}#milestone-{item['id']}"}, "entity": item})
        elif item["eligibility_state"] != "ELIGIBLE":
            work.append({"category": "MILESTONE_EVIDENCE_REQUIRED", "why": "Trigger evidence has not made this milestone eligible.", "next_action": "Review trigger evidence", "authority_needed": "Milestone review capability", "target": {"entity_type": "BILLING_MILESTONE", "entity_id": item["id"], "route": f"/billing/plans/{item['plan_id']}#milestone-{item['id']}"}, "entity": item})
    for item in invoice_rows:
        if item["status"] in {"DRAFT", "NEEDS_REVALIDATION"}:
            work.append({"category": "INVOICE_REVIEW_REQUIRED", "why": "The invoice remains a human-preparation draft.", "next_action": "Open invoice preflight", "authority_needed": "Invoice preparation capability", "target": {"entity_type": "INVOICE", "entity_id": item["invoice_id"], "route": f"/billing/invoices/{item['invoice_id']}?tab=preflight"}, "entity": item})
        if item["status"] == "ISSUED" and item.get("receivable_state") in {"DUE", "OVERDUE", "PARTIALLY_PAID"}:
            work.append({"category": "RECEIVABLE_OVERDUE" if item.get("receivable_state") == "OVERDUE" else "FOLLOW_UP_DUE", "why": f"Receivable is {str(item.get('receivable_state') or '').replace('_', ' ').lower()} with outstanding exposure.", "next_action": "Review collection action", "authority_needed": "Receivable follow-up capability", "target": {"entity_type": "INVOICE", "entity_id": item["invoice_id"], "route": f"/billing/invoices/{item['invoice_id']}?tab=collections"}, "entity": item})
    for item in payments:
        payment = item["payment"]
        if payment.get("verification_status") == "OBSERVED":
            work.append({"category": "PAYMENT_VERIFICATION_REQUIRED", "why": "Payment evidence is recorded but verification is a separate human control.", "next_action": "Review payment evidence", "authority_needed": "Payment verification capability", "target": {"entity_type": "PAYMENT", "entity_id": payment["id"], "route": f"/billing/payments/{payment['id']}"}, "entity": item})
        if item["credit"].get("state") == "UNALLOCATED_CLIENT_CREDIT":
            work.append({"category": "UNALLOCATED_CLIENT_CREDIT", "why": "Verified payment has remaining credit not allocated to an invoice.", "next_action": "Allocate to an eligible same-scope invoice", "authority_needed": "Payment allocation capability", "target": {"entity_type": "PAYMENT", "entity_id": payment["id"], "route": f"/billing/payments/{payment['id']}"}, "entity": item})
    return {
        "metrics": {
            "ready_to_invoice": sum(item["invoiceable_now"] for item in milestones),
            "draft_review_required": sum(item["status"] in {"DRAFT", "NEEDS_REVALIDATION"} for item in invoice_rows),
            "issued_outstanding": sum(item["status"] == "ISSUED" and _d(item.get("outstanding_amount") or 0) > 0 for item in invoice_rows),
            "overdue": sum(item.get("receivable_state") == "OVERDUE" for item in invoice_rows),
            "payments_to_verify": sum(item["payment"].get("verification_status") == "OBSERVED" for item in payments),
            "unallocated_client_credit": sum(1 for item in payments if item["credit"].get("state") == "UNALLOCATED_CLIENT_CREDIT"),
        },
        "work_items": work,
        "open_receivables": open_receivables,
        "payments": payments,
        "source_of_truth": "CANONICAL_BILLING_EVENTS",
        "system_insights_only": True,
        "ai_assisted": False,
        "unresolved_owner_decisions": [],
        "resolved_owner_policies": RESOLVED_OWNER_POLICIES,
    }


@router.get("/plans")
def list_billing_plans(request: Request, project_id: str | None = None, contract_id: str | None = None, status: str | None = None, billing_mode: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    scope = _view_scope(db, principal)
    query = select(BillingPlan).where(_scope_clause(BillingPlan, scope)).order_by(BillingPlan.created_at.desc())
    if project_id: query = query.where(BillingPlan.project_id == project_id)
    if contract_id: query = query.where(BillingPlan.contract_id == contract_id)
    if status: query = query.where(BillingPlan.status == status.upper())
    if billing_mode: query = query.where(BillingPlan.billing_mode == billing_mode.upper())
    items = []
    for plan in db.scalars(query).all():
        revision = db.get(BillingPlanRevision, plan.current_revision_id) if plan.current_revision_id else None
        milestones = db.scalars(select(BillingMilestone).where(BillingMilestone.billing_plan_revision_id == (revision.id if revision else "")).order_by(BillingMilestone.sequence)).all()
        items.append({"plan": _row(plan), "revision": _row(revision), "milestones": [_milestone_projection(db, item) for item in milestones], "context": _billing_context(db, contract_id=plan.contract_id, project_id=plan.project_id, client_account_id=plan.client_account_id)})
    return {"items": items, "total": len(items), "filters": {"project_id": project_id, "contract_id": contract_id, "status": status, "billing_mode": billing_mode}, "source_of_truth": "CANONICAL_BILLING_PLAN"}


@router.get("/milestones")
def list_billing_milestones(request: Request, project_id: str | None = None, contract_id: str | None = None, plan_id: str | None = None, eligibility: str | None = None, invoiceability: str | None = None, billing_mode: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    scope = _view_scope(db, principal)
    query = select(BillingMilestone).join(BillingPlanRevision, BillingPlanRevision.id == BillingMilestone.billing_plan_revision_id).where(_scope_clause(BillingPlanRevision, scope)).order_by(BillingMilestone.sequence)
    if project_id: query = query.where(BillingPlanRevision.project_id == project_id)
    if contract_id: query = query.where(BillingPlanRevision.contract_id == contract_id)
    if plan_id: query = query.where(BillingPlanRevision.billing_plan_id == plan_id)
    if eligibility: query = query.where(BillingMilestone.eligibility_state == eligibility.upper())
    if billing_mode: query = query.where(BillingPlanRevision.billing_mode == billing_mode.upper())
    items = [_milestone_projection(db, item) for item in db.scalars(query).all()]
    if invoiceability: items = [item for item in items if item["invoiceable_now"] == (invoiceability.upper() in {"READY", "TRUE", "YES"})]
    return {"items": items, "total": len(items), "source_of_truth": "CANONICAL_MILESTONE_ELIGIBILITY_AND_INVOICE_EVENTS"}


@router.get("/payments")
def list_billing_payments(request: Request, project_id: str | None = None, contract_id: str | None = None, verification_status: str | None = None, credit_state: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "PAYMENT_CREDIT_VIEW")
    scope = _view_scope(db, principal)
    query = select(PaymentReceipt).where(_scope_clause(PaymentReceipt, scope)).order_by(PaymentReceipt.received_date.desc(), PaymentReceipt.recorded_at.desc())
    if project_id: query = query.where(PaymentReceipt.project_id == project_id)
    if contract_id: query = query.where(PaymentReceipt.contract_id == contract_id)
    if verification_status: query = query.where(PaymentReceipt.verification_status == verification_status.upper())
    items = [_payment_projection(db, item) for item in db.scalars(query).all()]
    if credit_state: items = [item for item in items if item["credit"]["state"] == credit_state.upper()]
    return {"items": items, "total": len(items), "source_of_truth": "CANONICAL_PAYMENT_RECEIPT_AND_ALLOCATION_EVENTS"}


@router.get("/receivables")
def list_billing_receivables(request: Request, project_id: str | None = None, state: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    scope = _view_scope(db, principal)
    query = select(Invoice).where(Invoice.status == "ISSUED", _scope_clause(Invoice, scope)).order_by(Invoice.created_at.desc())
    if project_id: query = query.where(Invoice.project_id == project_id)
    items = []
    for invoice in db.scalars(query).all():
        row = _invoice_projection(db, invoice)
        if state and row.get("receivable_state") != state.upper(): continue
        row["context"] = _billing_context(db, contract_id=invoice.contract_id, project_id=invoice.project_id, client_account_id=invoice.client_account_id)
        due_date = row.get("due_date")
        days_relative = None
        if due_date:
            days_relative = (date.today() - date.fromisoformat(due_date)).days
        row["days_relative_to_due"] = days_relative
        row["collection_action"] = "FOLLOW_UP" if _d(row.get("outstanding_amount") or 0) > 0 else "NONE"
        items.append(row)
    return {"items": items, "total": len(items), "formal_aging_report": False, "aging_note": "Descriptive date difference only; formal accounting aging policy is not approved.", "policy_status": "RESOLVED"}


@router.get("/reports")
def billing_reports(request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    scope = _view_scope(db, principal)
    invoices = [_invoice_projection(db, invoice) for invoice in db.scalars(select(Invoice).where(_scope_clause(Invoice, scope)).order_by(Invoice.created_at.desc())).all()]
    payments = [_payment_projection(db, item) for item in db.scalars(select(PaymentReceipt).where(_scope_clause(PaymentReceipt, scope)).order_by(PaymentReceipt.received_date.desc())).all()]
    timezone_name, year_start, year_end = _local_year_bounds()
    ytd = None
    ytd_status = "CONFIGURATION_REQUIRED"
    if year_start and year_end:
        issued = db.scalars(select(InvoiceIssueEvent).join(Invoice, Invoice.id == InvoiceIssueEvent.invoice_id).where(_scope_clause(Invoice, scope), InvoiceIssueEvent.issued_at >= year_start, InvoiceIssueEvent.issued_at < year_end)).all()
        allocations = db.scalars(select(InvoicePaymentAllocation).join(Invoice, Invoice.id == InvoicePaymentAllocation.invoice_id).where(_scope_clause(Invoice, scope), InvoicePaymentAllocation.allocated_at >= year_start, InvoicePaymentAllocation.allocated_at < year_end, InvoicePaymentAllocation.status != "REVERSED")).all()
        invoiced_total = Decimal("0")
        for event in issued:
            revision = db.get(InvoiceRevision, event.invoice_revision_id)
            invoiced_total += _d(getattr(revision, "payable_total", 0) if revision else 0)
        ytd = {"policy": "CALENDAR_YEAR", "timezone": timezone_name, "invoiced": str(_money(invoiced_total)), "collected": str(_money(sum((_d(item.allocated_amount) for item in allocations), Decimal("0"))))}
        ytd_status = "READY"
    return {"invoice_report": invoices, "open_receivables": [item for item in invoices if _d(item.get("outstanding_amount") or 0) > 0], "payment_history": payments, "ytd": ytd, "ytd_status": ytd_status, "ytd_policy": "CALENDAR_YEAR", "timezone": timezone_name, "timezone_status": "READY" if year_start else "CONFIGURATION_REQUIRED", "source_of_truth": "CANONICAL_BILLING_READ_MODELS"}


@router.get("/evidence")
def billing_evidence(request: Request, project_id: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    scope = _view_scope(db, principal)
    query = select(Document).where(_scope_clause(Document, scope, client=None, contract=None)).order_by(Document.updated_at.desc())
    if project_id:
        query = query.where(Document.project_id == project_id)
    items = []
    for document in db.scalars(query).all():
        version = db.get(DocumentVersion, document.current_version_id) if document.current_version_id else None
        if not version:
            continue
        items.append({"document_id": document.id, "document_version_id": version.id, "label": document.logical_name, "filename": version.source_filename, "approval_state": str(version.approval_state), "source_reference": version.source_path_or_reference, "mime_type": version.mime_type, "open_path": f"/api/billing/evidence/{version.id}/open"})
    return {"items": items, "total": len(items), "source_of_truth": "CONTENT_LIBRARY_DOCUMENT_VERSION"}


@router.get("/evidence/{version_id}/open")
def open_billing_evidence(version_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    version = db.get(DocumentVersion, version_id)
    document = db.get(Document, version.document_id) if version else None
    if not version or not document:
        raise HTTPException(404, {"code": "BILLING_EVIDENCE_NOT_FOUND"})
    _authorize_view(db, request, principal, project_id=document.project_id)
    if version.synthetic_content is None:
        raise HTTPException(409, {"code": "EVIDENCE_OPEN_REQUIRES_STORAGE_ROUTE", "source_reference": version.source_path_or_reference})
    return Response(content=version.synthetic_content, media_type=version.mime_type or "application/octet-stream", headers={"Content-Disposition": f'inline; filename="{version.source_filename}"', "X-Document-Version": version.id})


@router.get("/supervision-queue")
def supervision_queue(request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    scope = _view_scope(db, principal)
    timezone_name, _, _ = _local_year_bounds()
    items = []
    for plan in db.scalars(select(BillingPlan).where(BillingPlan.billing_mode == "SUPERVISION_MONTHLY", BillingPlan.status == "ACTIVE", _scope_clause(BillingPlan, scope))).all():
        if timezone_name and _business_timezone()[1] is not None:
            items.append({"plan_id": plan.id, "project_id": plan.project_id, "contract_id": plan.contract_id, "status": "READY_FOR_REVIEW", "reason": "Previous service period derived for human review.", "autonomous_invoice_issue": False})
        else:
            items.append({"plan_id": plan.id, "project_id": plan.project_id, "contract_id": plan.contract_id, "status": "CONFIGURATION_REQUIRED", "reason": "A governed business-local timezone is required before deriving the previous service period.", "autonomous_invoice_issue": False})
    return {"items": items, "total": len(items), "business_local_timezone": timezone_name, "business_local_timezone_configuration_required": not bool(timezone_name and _business_timezone()[1]), "policy_status": "RESOLVED", "runtime_configuration_status": "READY" if timezone_name and _business_timezone()[1] else "CONFIGURATION_REQUIRED"}


@router.post("/readiness-requests")
def create_readiness_request(payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER | {Role.PROCESS_CHAMPION, Role.RESPONSIBLE_ENGINEER}, "BILLABLE_STAGE_REQUEST")
    milestone = db.get(BillingMilestone, payload.get("billing_milestone_id"))
    plan_revision = db.get(BillingPlanRevision, payload.get("billing_plan_revision_id"))
    project = db.get(Project, payload.get("project_id"))
    contract = db.get(Contract, payload.get("contract_id"))
    if not milestone or not plan_revision or not project or not contract or milestone.billing_plan_revision_id != plan_revision.id or plan_revision.project_id != project.id or plan_revision.contract_id != contract.id:
        raise HTTPException(409, {"code": "BILLING_READINESS_SCOPE_MISMATCH"})
    _authorize(db, request, principal, capability="BILLING_READINESS_REQUEST", roles=OWNER | {Role.PROCESS_CHAMPION, Role.RESPONSIBLE_ENGINEER}, project_id=project.id, client_account_id=contract.client_account_id)
    evidence_id = payload.get("evidence_document_version_id")
    _validate_document_evidence(db, evidence_id, project, not_found_code="BILLING_READINESS_EVIDENCE_NOT_FOUND", mismatch_code="BILLING_READINESS_EVIDENCE_PROJECT_MISMATCH")
    key = str(payload.get("idempotency_key") or "").strip()
    if not key: raise HTTPException(422, {"code": "BILLING_READINESS_IDEMPOTENCY_KEY_REQUIRED"})
    existing = db.scalar(select(BillingReadinessRequest).where(BillingReadinessRequest.idempotency_key == key))
    if existing: return {"request": _row(existing), "invoice_issue_authority": False}
    item = BillingReadinessRequest(project_id=project.id, contract_id=contract.id, billing_plan_revision_id=plan_revision.id, billing_milestone_id=milestone.id, requested_by=_actor(request, payload), evidence_document_version_id=evidence_id, note=str(payload.get("note") or "").strip() or None, idempotency_key=key, correlation_id=_corr(request))
    db.add(item); db.flush(); _audit(db, request, "BILLING_READINESS_REQUESTED", "BillingReadinessRequest", item.id, _actor(request, payload), {"invoice_issue_authority": False, "milestone_id": milestone.id}); db.commit()
    return {"request": _row(item), "invoice_issue_authority": False, "message": "Submitting this request does not Issue an Invoice and does not grant payment authority."}


@router.get("/readiness-requests")
def list_readiness_requests(request: Request, project_id: str | None = None, milestone_id: str | None = None, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    scope = _view_scope(db, principal)
    query = select(BillingReadinessRequest).where(_scope_clause(BillingReadinessRequest, scope)).order_by(BillingReadinessRequest.requested_at.desc())
    if project_id: query = query.where(BillingReadinessRequest.project_id == project_id)
    if milestone_id: query = query.where(BillingReadinessRequest.billing_milestone_id == milestone_id)
    return {"items": [_row(item) for item in db.scalars(query).all()], "total": db.scalar(select(func.count()).select_from(query.subquery())) or 0}


def _office_invoice_projection(db: Session, office_id: str, *, open_only: bool = False, scope: Any | None = None) -> list[dict[str, Any]]:
    project_ids = select(Project.id).where(Project.office_id == office_id)
    contract_ids = select(Contract.id).where(Contract.project_id.in_(project_ids))
    filters = (Invoice.project_id.in_(project_ids)) | (Invoice.contract_id.in_(contract_ids))
    if scope is not None:
        filters = filters & _scope_clause(Invoice, scope)
    invoices = db.scalars(select(Invoice).where(filters).order_by(Invoice.created_at.desc())).all()
    rows = []
    for invoice in invoices:
        row = _invoice_projection(db, invoice)
        if open_only and _d(row.get("outstanding_amount") or 0) <= 0:
            continue
        contract = db.get(Contract, invoice.contract_id)
        project = db.get(Project, invoice.project_id) if invoice.project_id else None
        client = db.get(ClientAccount, invoice.client_account_id) if invoice.client_account_id else None
        rows.append({**row, "contract_reference": contract.contract_reference if contract else None, "project_reference": project.project_code or project.project_number if project else None, "client_name": client.display_name if client else None})
    return rows


@router.get("/invoices/{invoice_id}/receivable")
def invoice_receivable(invoice_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    invoice, _contract, revision, _plan_revision, _project = _invoice_revision(db, invoice_id)
    _authorize_view(db, request, principal, project_id=invoice.project_id, client_account_id=invoice.client_account_id, contract_id=invoice.contract_id)
    return _receivable(db, invoice, revision)


@router.post("/payments")
def record_payment(payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, PLAN_WRITE, "PAYMENT_RECORD")
    invoice = db.get(Invoice, payload.get("invoice_id")) if payload.get("invoice_id") else None
    contract_id = str(payload.get("contract_id") or (invoice.contract_id if invoice else ""))
    contract, _contract_revision, _context, project = _contract_context(db, contract_id, None)
    client_id = str(payload.get("client_account_id") or (invoice.client_account_id if invoice else contract.client_account_id))
    if client_id != contract.client_account_id: raise HTTPException(403, {"code": "PAYMENT_CLIENT_CONTRACT_MISMATCH"})
    payment_project_id = payload["project_id"] if "project_id" in payload else (invoice.project_id if invoice else project.id if project else None); _scope_project(db, payment_project_id, contract, project)
    _authorize(db, request, principal, capability="PAYMENT_RECORD", roles=PLAN_WRITE, project_id=payment_project_id, client_account_id=client_id, contract_id=contract.id)
    amount = _money(_d(payload.get("amount"), field="amount")); currency = str(payload.get("currency") or contract.currency or "").upper()
    if amount <= 0 or not currency: raise HTTPException(422, {"code": "PAYMENT_AMOUNT_CURRENCY_REQUIRED"})
    evidence_id = payload.get("evidence_document_version_id")
    voucher_id = payload.get("receipt_voucher_document_version_id")
    _validate_document_evidence(db, evidence_id, project, not_found_code="PAYMENT_EVIDENCE_NOT_FOUND", mismatch_code="PAYMENT_EVIDENCE_PROJECT_MISMATCH")
    _validate_document_evidence(db, voucher_id, project, not_found_code="PAYMENT_RECEIPT_VOUCHER_NOT_FOUND", mismatch_code="PAYMENT_RECEIPT_VOUCHER_PROJECT_MISMATCH")
    key = str(payload.get("idempotency_key") or "").strip()
    if not key: raise HTTPException(422, {"code": "PAYMENT_IDEMPOTENCY_KEY_REQUIRED"})
    existing = db.scalar(select(PaymentReceipt).where(PaymentReceipt.idempotency_key == key))
    if existing:
        response = _row(existing)
        response["credit"] = _payment_credit(db, existing)
        return response
    item = PaymentReceipt(client_account_id=client_id, contract_id=contract.id, project_id=payment_project_id, received_date=_date(payload.get("received_date") or date.today().isoformat(), field="received_date"), amount=amount, currency=currency, reference=str(payload.get("reference") or "").strip(), payment_method=str(payload.get("payment_method") or "").strip().upper() or None, evidence_document_version_id=evidence_id, evidence_reference=str(payload.get("evidence_reference") or "").strip() or None, receipt_voucher_document_version_id=voucher_id, receipt_voucher_evidence_reference=str(payload.get("receipt_voucher_evidence_reference") or "").strip() or None, custodian_context_json=payload.get("custodian_context_json") or None, verification_status="OBSERVED", recorded_by=_actor(request, payload), notes=payload.get("notes"), idempotency_key=key)
    if not item.reference: raise HTTPException(422, {"code": "PAYMENT_REFERENCE_REQUIRED"})
    db.add(item); db.flush(); _audit(db, request, "PAYMENT_RECEIPT_RECORDED", "PaymentReceipt", item.id, _actor(request, payload), {"contract_id": contract.id, "project_id": payment_project_id, "amount": str(amount), "currency": currency, "verification_status": item.verification_status}); db.commit(); response = _row(item); response["credit"] = _payment_credit(db, item); return response


@router.get("/payments/{payment_id}/unallocated-credit")
def payment_unallocated_credit(payment_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "PAYMENT_CREDIT_VIEW")
    item = db.get(PaymentReceipt, payment_id)
    if not item:
        raise HTTPException(404, {"code": "PAYMENT_NOT_FOUND"})
    _authorize_view(db, request, principal, project_id=item.project_id, client_account_id=item.client_account_id, contract_id=item.contract_id)
    return _payment_credit(db, item)


@router.get("/payments/{payment_id}")
def get_payment(payment_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "PAYMENT_CREDIT_VIEW")
    item = db.get(PaymentReceipt, payment_id)
    if not item:
        raise HTTPException(404, {"code": "PAYMENT_NOT_FOUND"})
    _authorize_view(db, request, principal, project_id=item.project_id, client_account_id=item.client_account_id, contract_id=item.contract_id)
    return _payment_projection(db, item)


@router.get("/projects/{project_id}/payment-history")
def project_payment_history(project_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, {"code": "PROJECT_NOT_FOUND"})
    _authorize_view(db, request, principal, project_id=project.id)
    payments = db.scalars(select(PaymentReceipt).where(PaymentReceipt.project_id == project_id).order_by(PaymentReceipt.received_date.desc())).all()
    return {"project": _row(project), "items": [_payment_projection(db, item) for item in payments], "total": len(payments), "source_of_truth": "PAYMENT_RECEIPT_VERIFICATION_ALLOCATION_AND_REVERSAL_EVENTS"}


@router.post("/fx-rates")
def create_fx_rate(payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "FX_RATE_MANAGE")
    _authorize(db, request, principal, capability="BILLING_FX_RATE_MANAGE", roles=OWNER)
    currency = str(payload.get("source_currency") or "").strip().upper()
    rate = _d(payload.get("qar_per_source_currency_rate"), field="qar_per_source_currency_rate")
    if not currency or currency == "QAR" or rate <= 0:
        raise HTTPException(422, {"code": "FX_RATE_RECORD_INVALID"})
    version = (db.scalar(select(func.max(BillingFxRateRecord.rate_record_version)).where(BillingFxRateRecord.source_currency == currency)) or 0) + 1
    item = BillingFxRateRecord(source_currency=currency, qar_per_source_currency_rate=rate, rate_effective_date=_date(payload.get("rate_effective_date") or date.today().isoformat(), field="rate_effective_date"), rate_source_reference=str(payload.get("rate_source_reference") or "").strip(), rate_record_version=version, owner_approval_identity=_actor(request, payload), owner_approval_time_utc=datetime.now(timezone.utc), status="ACTIVE")
    if not item.rate_source_reference:
        raise HTTPException(422, {"code": "FX_RATE_SOURCE_REFERENCE_REQUIRED"})
    db.add(item); db.flush(); _audit(db, request, "BILLING_FX_RATE_RECORDED", "BillingFxRateRecord", item.id, _actor(request, payload), {"source_currency": currency, "version": version}); db.commit()
    return _row(item)


@router.post("/projects/{project_id}/expected-exp")
def set_expected_exp(project_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "EXPECTED_EXP_EDIT")
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, {"code": "PROJECT_NOT_FOUND"})
    _authorize(db, request, principal, capability="PROJECT_EXPECTED_EXP_EDIT", roles=OWNER, project_id=project.id, office_id=project.office_id)
    value = _d(payload.get("value_percent"), field="value_percent")
    if value < 0 or value > 100:
        raise HTTPException(422, {"code": "EXPECTED_EXP_PERCENT_OUT_OF_RANGE"})
    version = (db.scalar(select(func.max(ProjectExpectedExpVersion.version)).where(ProjectExpectedExpVersion.project_id == project.id)) or 0) + 1
    item = ProjectExpectedExpVersion(project_id=project.id, value_percent=value, effective_time=datetime.now(timezone.utc), owner_editor_identity=_actor(request, payload), edit_time_utc=datetime.now(timezone.utc), source_or_note=str(payload.get("source_or_note") or "").strip(), version=version, status="ACTIVE")
    if not item.source_or_note:
        raise HTTPException(422, {"code": "EXPECTED_EXP_SOURCE_NOTE_REQUIRED"})
    db.add(item); db.flush(); _audit(db, request, "PROJECT_EXPECTED_EXP_RECORDED", "ProjectExpectedExpVersion", item.id, _actor(request, payload), {"project_id": project.id, "version": version}); db.commit()
    return _row(item)


@router.get("/controls")
def billing_controls(request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "BILLING_VIEW")
    scope = _view_scope(db, principal)
    if scope.empty:
        raise HTTPException(403, {"code": "SCOPED_FINANCE_CAPABILITY_REQUIRED", "capability": "BILLING_VIEW"})
    account_scope = FinancialAccountMaster.office_id.in_(scope.office_ids) if scope.office_ids else false()
    accounts = db.scalars(select(FinancialAccountMaster).where(account_scope).order_by(FinancialAccountMaster.account_name)).all()
    account_ids = [item.id for item in accounts]
    versions = db.scalars(select(FinancialAccountVersion).where(FinancialAccountVersion.financial_account_master_id.in_(account_ids) if account_ids else false()).order_by(FinancialAccountVersion.created_at.desc())).all()
    policy = db.scalar(select(InvoiceNumberingPolicy).where(InvoiceNumberingPolicy.policy_key == "INVOICE"))
    numbering_gate = canonical_numbering_gate(lambda key, default=False: runtime_decision_value(db, key, default))
    fx_rates = db.scalars(select(BillingFxRateRecord).order_by(BillingFxRateRecord.source_currency, BillingFxRateRecord.rate_record_version.desc())).all()
    return {
        "financial_account_masters": [_row(item) for item in accounts],
        "financial_account_versions": [_mask_account(item) for item in versions],
        "invoice_numbering": {"status": "RESOLVED", "policy": _row(policy), "production_fail_closed": not bool(numbering_gate["ready"]), "policy_status": "RESOLVED", "legacy_finance_reconciliation": numbering_gate["controls"]},
        "fx_policy": {"status": "RESOLVED", "policy": RESOLVED_OWNER_POLICIES["NON_QAR_QAR_CONVERSION_AND_PROVENANCE_POLICY"], "records": [_row(rate) for rate in fx_rates]},
        "expected_exp_policy": {"status": "RESOLVED", "policy": RESOLVED_OWNER_POLICIES["EXPECTED_EXP_PERCENT_DEFINITION_AND_SOURCE"]},
        "ytd_policy": {"status": "RESOLVED", "boundary": "CALENDAR_YEAR", "runtime_configuration_status": "CONFIGURATION_REQUIRED"},
        "resolved_owner_policies": _policy_projection(db),
        "unresolved_owner_decisions": [],
        "ai_canonical_write_authority": 0,
        "ai_protected_action_authority": 0,
        "authorization_model": "PERSISTED_SCOPED_CAPABILITY_ASSIGNMENTS",
        "authorization_scope": {
            "project_ids": sorted(scope.project_ids),
            "client_account_ids": sorted(scope.client_account_ids),
            "contract_ids": sorted(scope.contract_ids),
        },
    }


@router.post("/payments/{payment_id}/verify")
def verify_payment(payment_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "PAYMENT_VERIFY")
    item = db.get(PaymentReceipt, payment_id)
    if not item: raise HTTPException(404, {"code": "PAYMENT_NOT_FOUND"})
    _authorize(db, request, principal, capability="PAYMENT_VERIFY", roles=OWNER, project_id=item.project_id, client_account_id=item.client_account_id, contract_id=item.contract_id)
    if item.verification_status == "VERIFIED": return _row(item)
    if item.verification_status == "REVERSED": raise HTTPException(409, {"code": "PAYMENT_REVERSED"})
    _payment_evidence_gate(item)
    item.verification_status = "VERIFIED"; item.verified_by = _actor(request, payload); item.verified_at = datetime.now(timezone.utc); _audit(db, request, "PAYMENT_RECEIPT_VERIFIED", "PaymentReceipt", item.id, _actor(request, payload), {"verification_status": item.verification_status, "payment_method": item.payment_method, "evidence_control": "PASS"}); db.commit(); return _row(item)


@router.post("/payments/{payment_id}/allocate")
def allocate_payment(payment_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "PAYMENT_ALLOCATE")
    payment = db.scalar(select(PaymentReceipt).where(PaymentReceipt.id == payment_id).with_for_update())
    invoice = db.scalar(select(Invoice).where(Invoice.id == payload.get("invoice_id")).with_for_update())
    if not payment or not invoice: raise HTTPException(404, {"code": "PAYMENT_OR_INVOICE_NOT_FOUND"})
    _authorize(db, request, principal, capability="PAYMENT_ALLOCATE", roles=OWNER, project_id=invoice.project_id or payment.project_id, client_account_id=invoice.client_account_id, contract_id=payment.contract_id)
    if payment.verification_status != "VERIFIED": raise HTTPException(409, {"code": "VERIFIED_PAYMENT_REQUIRED"})
    if invoice.status != "ISSUED": raise HTTPException(409, {"code": "ISSUED_INVOICE_REQUIRED"})
    if payment.client_account_id != invoice.client_account_id:
        raise HTTPException(403, {"code": "PAYMENT_INVOICE_CLIENT_SCOPE_DENIED"})
    if payment.contract_id != invoice.contract_id:
        raise HTTPException(403, {"code": "PAYMENT_INVOICE_CONTRACT_SCOPE_DENIED"})
    if payment.project_id and payment.project_id != invoice.project_id:
        raise HTTPException(403, {"code": "PAYMENT_INVOICE_PROJECT_SCOPE_DENIED"})
    key = str(payload.get("idempotency_key") or "").strip()
    if not key: raise HTTPException(422, {"code": "ALLOCATION_IDEMPOTENCY_KEY_REQUIRED"})
    existing = db.scalar(select(InvoicePaymentAllocation).where(InvoicePaymentAllocation.idempotency_key == key))
    if existing: return _row(existing)
    revision = db.get(InvoiceRevision, invoice.current_revision_id)
    if not revision or payment.currency.upper() != str(revision.currency).upper(): raise HTTPException(409, {"code": "PAYMENT_CURRENCY_MISMATCH"})
    attributable_milestones = [line.billing_milestone_id for line in _lines(db, revision.id) if line.billing_milestone_id and line.affects_payable_total]
    attributable_milestones = list(dict.fromkeys(attributable_milestones))
    requested_milestone_id = str(payload.get("billing_milestone_id") or "").strip() or None
    if len(attributable_milestones) > 1 and not requested_milestone_id:
        raise HTTPException(409, {"code": "MILESTONE_ATTRIBUTION_REQUIRED_FOR_MULTI_MILESTONE_INVOICE", "milestone_ids": attributable_milestones})
    milestone_id = requested_milestone_id or (attributable_milestones[0] if len(attributable_milestones) == 1 else None)
    milestone = db.get(BillingMilestone, milestone_id) if milestone_id else None
    if milestone_id and (not milestone or milestone.billing_plan_revision_id != revision.billing_plan_revision_id or milestone_id not in attributable_milestones):
        raise HTTPException(409, {"code": "MILESTONE_ATTRIBUTION_SCOPE_MISMATCH"})
    amount = _money(_d(payload.get("allocated_amount"), field="allocated_amount")); used = sum((_d(x.allocated_amount) for x in db.scalars(select(InvoicePaymentAllocation).where(InvoicePaymentAllocation.payment_receipt_id == payment.id, InvoicePaymentAllocation.status == "ALLOCATED")).all()), Decimal("0")); receivable = _receivable(db, invoice, revision); outstanding = _d(receivable["outstanding_amount"] or 0)
    milestone_attributed = sum((_d(x.allocated_amount) for x in db.scalars(select(InvoicePaymentAllocation).where(InvoicePaymentAllocation.billing_milestone_id == milestone_id, InvoicePaymentAllocation.status == "ALLOCATED")).all()), Decimal("0")) if milestone_id else Decimal("0")
    milestone_invoice_amount = sum((_line_total(line) for line in _lines(db, revision.id) if line.billing_milestone_id == milestone_id and line.affects_payable_total), Decimal("0")) if milestone_id else Decimal("0")
    if amount <= 0 or used + amount > _d(payment.amount) or amount > outstanding: raise HTTPException(409, {"code": "PAYMENT_ALLOCATION_OVER_LIMIT", "unallocated_payment": str(_d(payment.amount) - used), "outstanding": str(outstanding)})
    if milestone_id and milestone_attributed + amount > milestone_invoice_amount:
        raise HTTPException(409, {"code": "MILESTONE_ATTRIBUTION_OVER_LIMIT", "milestone_id": milestone_id, "remaining_attributable": str(milestone_invoice_amount - milestone_attributed)})
    allocation = InvoicePaymentAllocation(payment_receipt_id=payment.id, invoice_id=invoice.id, billing_milestone_id=milestone_id, allocated_amount=amount, currency=payment.currency, allocated_by=_actor(request, payload), idempotency_key=key)
    db.add(allocation)
    db.flush()
    post_allocation_receivable = _receivable(db, invoice, revision)
    if post_allocation_receivable["outstanding_amount"] == "0.00":
        revision.actual_collection_date = payment.received_date
        revision.actual_collection_date_source = "VERIFIED_PAYMENT_ALLOCATION"
    _lineage(db, request, invoice.project_id, "PaymentReceipt", payment.id, "InvoicePaymentAllocation", allocation.id, "VERIFIED_PAYMENT_ALLOCATION")
    _audit(db, request, "PAYMENT_ALLOCATED", "InvoicePaymentAllocation", allocation.id, _actor(request, payload), {"payment_id": payment.id, "invoice_id": invoice.id, "billing_milestone_id": milestone_id, "allocated_amount": str(amount), "currency": payment.currency, "actual_collection_date": revision.actual_collection_date.isoformat() if revision.actual_collection_date else None})
    db.commit()
    return {"allocation": _row(allocation), "receivable": _receivable(db, invoice, revision)}


@router.post("/payments/{payment_id}/reverse")
def reverse_payment(payment_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "PAYMENT_REVERSE")
    payment = db.get(PaymentReceipt, payment_id)
    if not payment:
        raise HTTPException(404, {"code": "PAYMENT_NOT_FOUND"})
    _authorize(db, request, principal, capability="PAYMENT_REVERSE", roles=OWNER, project_id=payment.project_id, client_account_id=payment.client_account_id, contract_id=payment.contract_id)
    key = str(payload.get("idempotency_key") or "").strip()
    reason = str(payload.get("reason") or "").strip()
    if not key:
        raise HTTPException(422, {"code": "PAYMENT_REVERSAL_IDEMPOTENCY_KEY_REQUIRED"})
    if not reason:
        raise HTTPException(422, {"code": "PAYMENT_REVERSAL_REASON_REQUIRED"})
    prior = db.scalar(select(PaymentReversalEvent).where(PaymentReversalEvent.idempotency_key == key))
    if prior:
        return {"reversal": _row(prior), "payment": _row(payment)}
    if payment.verification_status == "REVERSED":
        raise HTTPException(409, {"code": "PAYMENT_ALREADY_REVERSED"})
    evidence_id = payload.get("evidence_document_version_id")
    _validate_document_evidence(db, evidence_id, db.get(Project, payment.project_id) if payment.project_id else None, not_found_code="PAYMENT_REVERSAL_EVIDENCE_NOT_FOUND", mismatch_code="PAYMENT_REVERSAL_EVIDENCE_PROJECT_MISMATCH")
    event = PaymentReversalEvent(payment_receipt_id=payment.id, reason=reason, evidence_document_version_id=evidence_id, effective_at=datetime.fromisoformat(str(payload.get("effective_at") or datetime.now(timezone.utc).isoformat())), reversed_by=_actor(request, payload), idempotency_key=key, status="EFFECTIVE")
    db.add(event)
    db.flush()
    affected = db.scalars(select(InvoicePaymentAllocation).where(InvoicePaymentAllocation.payment_receipt_id == payment.id, InvoicePaymentAllocation.status == "ALLOCATED")).all()
    for allocation in affected:
        allocation.status = "REVERSED"
        allocation.reversal_event_id = event.id
        affected_invoice = db.get(Invoice, allocation.invoice_id)
        affected_revision = db.get(InvoiceRevision, affected_invoice.current_revision_id) if affected_invoice else None
        if affected_revision:
            affected_revision.actual_collection_date = None
            affected_revision.actual_collection_date_source = None
    payment.verification_status = "REVERSED"
    _audit(db, request, "PAYMENT_REVERSED", "PaymentReversalEvent", event.id, _actor(request, payload), {"payment_id": payment.id, "reason": reason, "affected_allocations": len(affected)})
    db.commit()
    return {"reversal": _row(event), "payment": _row(payment), "reversed_allocations": [_row(item) for item in affected]}


@router.post("/invoices/{invoice_id}/resolutions")
def resolve_receivable(invoice_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, OWNER, "RECEIVABLE_NON_CASH_RESOLVE")
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    if not invoice:
        raise HTTPException(404, {"code": "INVOICE_NOT_FOUND"})
    revision = db.get(InvoiceRevision, invoice.current_revision_id)
    if invoice.status != "ISSUED" or not revision:
        raise HTTPException(409, {"code": "ISSUED_INVOICE_REQUIRED"})
    _authorize(db, request, principal, capability="RECEIVABLE_NON_CASH_RESOLVE", roles=OWNER, project_id=invoice.project_id, client_account_id=invoice.client_account_id)
    key = str(payload.get("idempotency_key") or "").strip()
    if not key:
        raise HTTPException(422, {"code": "RECEIVABLE_RESOLUTION_IDEMPOTENCY_KEY_REQUIRED"})
    prior = db.scalar(select(ReceivableResolution).where(ReceivableResolution.idempotency_key == key))
    if prior:
        return {"resolution": _row(prior), "receivable": _receivable(db, invoice, revision)}
    resolution_type = str(payload.get("resolution_type") or "").strip().upper()
    if resolution_type not in NON_CASH_RESOLUTION_TYPES:
        raise HTTPException(422, {"code": "RECEIVABLE_RESOLUTION_TYPE_NOT_SUPPORTED", "allowed": sorted(NON_CASH_RESOLUTION_TYPES)})
    reason = str(payload.get("reason") or "").strip()
    approval_reference = str(payload.get("approval_reference") or "").strip()
    if not reason or not approval_reference:
        raise HTTPException(422, {"code": "RECEIVABLE_RESOLUTION_APPROVAL_AND_REASON_REQUIRED"})
    amount = _money(_d(payload.get("amount"), field="amount"))
    currency = str(payload.get("currency") or revision.currency or "").upper()
    receivable = _receivable(db, invoice, revision)
    outstanding = _d(receivable["outstanding_amount"] or 0)
    if currency != str(revision.currency).upper():
        raise HTTPException(409, {"code": "RECEIVABLE_RESOLUTION_CURRENCY_MISMATCH"})
    if amount <= 0 or amount > outstanding:
        raise HTTPException(409, {"code": "RESOLUTION_AMOUNT_EXCEEDS_OUTSTANDING", "outstanding": str(outstanding)})
    evidence_id = payload.get("evidence_document_version_id")
    _validate_document_evidence(db, evidence_id, db.get(Project, invoice.project_id) if invoice.project_id else None, not_found_code="RECEIVABLE_RESOLUTION_EVIDENCE_NOT_FOUND", mismatch_code="RECEIVABLE_RESOLUTION_EVIDENCE_PROJECT_MISMATCH")
    item = ReceivableResolution(invoice_id=invoice.id, resolution_type=resolution_type, amount=amount, currency=currency, reason=reason, approval_reference=approval_reference, evidence_document_version_id=evidence_id, effective_date=_date(payload.get("effective_date") or date.today().isoformat(), field="effective_date"), resolved_by=_actor(request, payload), status="ACTIVE", idempotency_key=key)
    db.add(item)
    db.flush()
    post_resolution_receivable = _receivable(db, invoice, revision)
    if post_resolution_receivable["outstanding_amount"] == "0.00":
        revision.actual_collection_date = item.effective_date
        revision.actual_collection_date_source = "NON_CASH_RECEIVABLE_RESOLUTION"
    _lineage(db, request, invoice.project_id, "Invoice", invoice.id, "ReceivableResolution", item.id, "RECEIVABLE_NON_CASH_RESOLUTION")
    _audit(db, request, "RECEIVABLE_NON_CASH_RESOLVED", "ReceivableResolution", item.id, _actor(request, payload), {"invoice_id": invoice.id, "resolution_type": resolution_type, "amount": str(amount), "approval_reference": approval_reference})
    db.commit()
    return {"resolution": _row(item), "receivable": _receivable(db, invoice, revision)}


@router.post("/invoices/{invoice_id}/follow-ups")
def record_follow_up(invoice_id: str, payload: dict[str, Any], request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, PLAN_WRITE, "RECEIVABLE_FOLLOW_UP")
    invoice = db.get(Invoice, invoice_id)
    if not invoice: raise HTTPException(404, {"code": "INVOICE_NOT_FOUND"})
    _authorize(db, request, principal, capability="RECEIVABLE_FOLLOW_UP", roles=PLAN_WRITE, project_id=invoice.project_id, client_account_id=invoice.client_account_id)
    item = ReceivableFollowUp(invoice_id=invoice.id, follow_up_date=_date(payload.get("follow_up_date") or date.today().isoformat(), field="follow_up_date"), channel=str(payload.get("channel") or "INTERNAL_NOTE"), contact_party_id=payload.get("contact_party_id"), note=str(payload.get("note") or "").strip(), outcome=payload.get("outcome"), next_follow_up_at=datetime.fromisoformat(payload["next_follow_up_at"]) if payload.get("next_follow_up_at") else None, recorded_by=_actor(request, payload))
    if not item.note: raise HTTPException(422, {"code": "FOLLOW_UP_NOTE_REQUIRED"})
    db.add(item); db.flush(); _audit(db, request, "RECEIVABLE_FOLLOW_UP_RECORDED", "ReceivableFollowUp", item.id, _actor(request, payload), {"invoice_id": invoice.id, "channel": item.channel, "payment_status_unchanged": True}); db.commit(); return _row(item)


@router.get("/invoices/{invoice_id}/download")
def download_invoice(invoice_id: str, request: Request, db: Session = Depends(get_db), role: Role = Depends(current_user_role), principal: AuthenticatedPrincipal = Depends(current_principal)):
    _role(role, VIEW, "INVOICE_EXPORT")
    invoice = db.get(Invoice, invoice_id); issue = db.scalar(select(InvoiceIssueEvent).where(InvoiceIssueEvent.invoice_id == invoice_id)) if invoice else None
    if not invoice: raise HTTPException(404, {"code": "INVOICE_NOT_FOUND"})
    if not issue: raise HTTPException(409, {"code": "ISSUED_INVOICE_ARTIFACT_REQUIRED"})
    _authorize_view(db, request, principal, project_id=invoice.project_id, client_account_id=invoice.client_account_id, contract_id=invoice.contract_id)
    artifact = db.get(RenderedArtifact, issue.rendered_artifact_id)
    return {"invoice_id": invoice.id, "invoice_reference": issue.official_invoice_ref, "artifact": _row(artifact), "download_policy": "EXACT_ISSUED_ARTIFACT"}
