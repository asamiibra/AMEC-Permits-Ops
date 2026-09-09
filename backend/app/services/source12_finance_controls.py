"""Source12 Finance controls over the canonical Billing event model.

The module is intentionally side-effect free.  Database routes remain the
system of record for BillingPlan, Invoice, PaymentReceipt and allocation
events; these helpers make the Source12 invariants explicit and testable
without fabricating production finance data.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import date, datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from threading import Lock
from typing import Iterable, Mapping, Sequence
from zoneinfo import ZoneInfo


VISIBLE_PERSONAS = frozenset(
    {"OWNER_SPONSOR", "PROCESS_CHAMPION", "REQUIREMENT_STEWARD", "RESPONSIBLE_ENGINEER", "PERMIT_PREPARER"}
)
FINANCE_CAPABILITIES = frozenset(
    {
        "FINANCE_PREPARE_INVOICE",
        "FINANCE_UPDATE_RECEIVABLE",
        "FINANCE_RECORD_ACKNOWLEDGEMENT_EVIDENCE",
        "FINANCE_RECORD_PAYMENT_EVIDENCE",
        "FINANCE_VERIFY_PAYMENT",
        "FINANCE_ALLOCATE_PAYMENT",
        "INVOICE_ACCEPT",
        "INVOICE_ISSUE",
    }
)
ISSUE_CAPABILITIES = frozenset({"INVOICE_ACCEPT", "INVOICE_ISSUE"})
PAYMENT_CAPABILITIES = frozenset({"FINANCE_VERIFY_PAYMENT", "FINANCE_ALLOCATE_PAYMENT"})
SOURCE12_MANDATORY_V1_FIELDS = frozenset({"invoice_reference", "invoice_date", "project_id", "invoice_total", "currency", "service_period"})
UNIVERSAL_DUE_TERM_DAYS: int | None = None


class Source12ControlError(ValueError):
    """A deterministic, fail-closed Source12 control rejection."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def _money(value: Decimal | int | str | float) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise Source12ControlError("MONEY_INVALID") from exc
    if not result.is_finite():
        raise Source12ControlError("MONEY_INVALID")
    return result.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ScopedCapability:
    user_id: str
    persona: str
    project_ids: frozenset[str]
    capabilities: frozenset[str]
    assignment_reference: str


def authorize_finance_capability(
    grant: ScopedCapability,
    *,
    project_id: str,
    capability: str,
    job_title: str | None = None,
) -> bool:
    """Require user + visible persona + capability + project assignment.

    ``job_title`` is accepted only to make the negative control explicit; it
    is never consulted for authorization.
    """

    del job_title
    if grant.persona not in VISIBLE_PERSONAS:
        raise Source12ControlError("FOURTH_GLOBAL_PERSONA_NOT_ALLOWED")
    if capability not in FINANCE_CAPABILITIES:
        raise Source12ControlError("FINANCE_CAPABILITY_NOT_RECOGNIZED")
    if capability not in grant.capabilities or project_id not in grant.project_ids:
        raise Source12ControlError("SCOPED_FINANCE_CAPABILITY_REQUIRED")
    return True


def request_design_billable_stage(*, persona: str, project_id: str, milestone_id: str, evidence_ref: str) -> dict[str, str | bool]:
    """Create a billable-readiness request without issue/payment authority."""

    if persona not in {"RESPONSIBLE_ENGINEER", "PERMIT_PREPARER", "PROCESS_CHAMPION"}:
        raise Source12ControlError("DESIGN_BILLABLE_REQUEST_PERSONA_REQUIRED")
    if not project_id or not milestone_id or not evidence_ref:
        raise Source12ControlError("BILLABLE_STAGE_EVIDENCE_REQUIRED")
    return {
        "project_id": project_id,
        "milestone_id": milestone_id,
        "evidence_ref": evidence_ref,
        "billing_eligible": True,
        "invoice_issue_authority": False,
        "payment_authority": False,
    }


def supervision_monthly_queue(*, active_project_ids: Iterable[str], service_year: int, service_month: int, already_eligible: Iterable[str] = ()) -> list[dict[str, str | bool]]:
    """Return prior-month work eligibility; never creates or issues invoices."""

    period = structured_service_period(service_year, service_month, "SUPERVISION")
    eligible = set(already_eligible)
    return [
        {"project_id": project_id, "service_period": period, "billing_eligible": True, "invoice_issued": False}
        for project_id in sorted(set(active_project_ids))
        if project_id not in eligible
    ]


def structured_service_period(year: int, month: int, service_type: str) -> str:
    if not 1 <= int(month) <= 12:
        raise Source12ControlError("SERVICE_PERIOD_MONTH_INVALID")
    value = str(service_type).strip().upper().replace(" ", "_")
    if not value:
        raise Source12ControlError("SERVICE_PERIOD_TYPE_REQUIRED")
    return f"{int(year):04d}-{int(month):02d} {value}"


@dataclass
class CollisionSafeNumberAllocator:
    historical_refs: set[str] = field(default_factory=set)
    historical_reconciled: bool = False
    prefix: str = "INV-AMEC"
    padding: int = 6
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def reserve(self, *, year: int, synthetic: bool = True) -> str:
        """Reserve only synthetic references until historical reconciliation."""

        if not synthetic and not self.historical_reconciled:
            raise Source12ControlError("LEGACY_FINANCE_RECONCILIATION_REQUIRED_BEFORE_PRODUCTION_NUMBERING")
        with self._lock:
            n = 1
            while True:
                candidate = f"{self.prefix}-{int(year)}-{n:0{self.padding}d}"
                if candidate not in self.historical_refs:
                    self.historical_refs.add(candidate)
                    return candidate
                n += 1


@dataclass
class ProjectOrdinalAllocator:
    ordinals: dict[str, int] = field(default_factory=dict)
    _lock: Lock = field(default_factory=Lock, init=False, repr=False)

    def reserve(self, project_id: str) -> int:
        with self._lock:
            value = self.ordinals.get(project_id, 0) + 1
            self.ordinals[project_id] = value
            return value


@dataclass(frozen=True)
class InvoiceState:
    invoice_id: str
    project_id: str
    global_invoice_ref: str
    project_invoice_ordinal: int
    status: str = "DRAFT"
    service_period: str | None = None
    delivery_evidence: tuple[str, ...] = ()
    acknowledgement_evidence: tuple[str, ...] = ()
    payment_allocation_ids: tuple[str, ...] = ()


INVOICE_TRANSITIONS: Mapping[str, frozenset[str]] = {
    "DUE": frozenset({"PLANNED", "DRAFT"}),
    "PLANNED": frozenset({"DRAFT"}),
    "DRAFT": frozenset({"READY_FOR_SIGNATURE", "CANCELLED"}),
    "READY_FOR_SIGNATURE": frozenset({"ACCEPTED", "CANCELLED"}),
    "ACCEPTED": frozenset({"ISSUED", "CANCELLED"}),
    "ISSUED": frozenset({"DELIVERED", "PARTIALLY_PAID", "PAID", "VOIDED"}),
    "DELIVERED": frozenset({"ACKNOWLEDGED", "PARTIALLY_PAID", "PAID", "VOIDED"}),
    "ACKNOWLEDGED": frozenset({"PARTIALLY_PAID", "PAID", "VOIDED"}),
    "PARTIALLY_PAID": frozenset({"PAID", "VOIDED"}),
    "PAID": frozenset({"CLOSED"}),
    "CLOSED": frozenset(),
    "CANCELLED": frozenset(),
    "VOIDED": frozenset(),
}


def transition_invoice(invoice: InvoiceState, target: str) -> InvoiceState:
    target = target.upper()
    if target not in INVOICE_TRANSITIONS.get(invoice.status.upper(), frozenset()):
        raise Source12ControlError("INVOICE_STATE_TRANSITION_NOT_ALLOWED")
    return replace(invoice, status=target)


def clone_previous_invoice(previous: InvoiceState, *, new_invoice_id: str, new_global_ref: str, new_project_ordinal: int, service_period: str) -> InvoiceState:
    if not new_invoice_id or not new_global_ref or new_project_ordinal <= 0:
        raise Source12ControlError("CLONE_NEW_IDENTITY_REQUIRED")
    return InvoiceState(
        invoice_id=new_invoice_id,
        project_id=previous.project_id,
        global_invoice_ref=new_global_ref,
        project_invoice_ordinal=new_project_ordinal,
        status="DRAFT",
        service_period=service_period,
    )


def invoice_report(invoices: Sequence[InvoiceState]) -> list[InvoiceState]:
    """Complete immutable history projection."""

    return list(invoices)


def open_invoice_queue(invoices: Sequence[InvoiceState]) -> list[InvoiceState]:
    """Receivable work queue projection; paid/closed invoices remain in history."""

    return [invoice for invoice in invoices if invoice.status.upper() not in {"PAID", "CLOSED", "CANCELLED", "VOIDED"}]


def validate_billing_milestone_source(source_contract_payment_term: Mapping[str, object] | None) -> bool:
    if not source_contract_payment_term or source_contract_payment_term.get("verified") is not True:
        raise Source12ControlError("BILLING_MILESTONE_CONTRACT_TERM_REQUIRED")
    return True


def assert_synthetic_fixture(values: Mapping[str, object]) -> bool:
    for value in values.values():
        text = str(value).upper()
        if text.startswith(("QA", "IBAN", "SWIFT")) and "SYNTHETIC" not in text and "SYNTHETIC://" not in text:
            raise Source12ControlError("REAL_FINANCE_VALUE_NOT_ALLOWED")
    return True


@dataclass(frozen=True)
class PaymentEvidence:
    payment_id: str
    project_id: str
    amount: Decimal
    currency: str
    method: str
    evidence_ref: str
    verification_status: str = "OBSERVED"


@dataclass(frozen=True)
class PaymentAllocation:
    allocation_id: str
    payment_id: str
    invoice_id: str
    project_id: str
    amount: Decimal
    milestone_id: str | None = None
    status: str = "ALLOCATED"
    effective_at: datetime | None = None


def rollup_finance(*, project_value: Decimal | int | str, invoice_total: Decimal | int | str, payments: Sequence[PaymentEvidence], allocations: Sequence[PaymentAllocation], invoice_id: str, project_id: str, milestone_id: str | None = None) -> dict[str, Decimal]:
    """Calculate all totals only from verified receipts and valid allocations."""

    verified = {p.payment_id for p in payments if p.verification_status == "VERIFIED" and p.project_id == project_id}
    valid = [a for a in allocations if a.status == "ALLOCATED" and a.payment_id in verified and a.project_id == project_id]
    invoice_paid = sum((a.amount for a in valid if a.invoice_id == invoice_id), Decimal("0.00"))
    project_receipts = sum((a.amount for a in valid), Decimal("0.00"))
    milestone_collected = sum((a.amount for a in valid if milestone_id and a.milestone_id == milestone_id), Decimal("0.00"))
    return {
        "invoice_outstanding": _money(max(Decimal("0"), _money(invoice_total) - invoice_paid)),
        "project_total_receipts": _money(project_receipts),
        "project_balance": _money(_money(project_value) - project_receipts),
        "milestone_actual_collected": _money(milestone_collected),
    }


@dataclass(frozen=True)
class FXRateRecord:
    source_currency: str
    qar_per_source_currency_rate: Decimal
    rate_effective_date: date
    rate_source_reference: str
    rate_record_version: str
    owner_approval_identity: str
    owner_approval_time_utc: datetime
    status: str = "APPROVED"


def qar_amount(*, contract_value: Decimal | int | str, contract_currency: str, fx_record: FXRateRecord | None = None) -> Decimal:
    currency = contract_currency.upper()
    value = _money(contract_value)
    if currency == "QAR":
        return value
    if fx_record is None or fx_record.status != "APPROVED" or fx_record.source_currency.upper() != currency:
        raise Source12ControlError("FX_RATE_RECORD_REQUIRED")
    if fx_record.qar_per_source_currency_rate <= 0 or not all(
        (fx_record.rate_source_reference, fx_record.rate_record_version, fx_record.owner_approval_identity, fx_record.owner_approval_time_utc)
    ):
        raise Source12ControlError("FX_RATE_RECORD_REQUIRED")
    return _money(value * fx_record.qar_per_source_currency_rate)


@dataclass(frozen=True)
class ExpectedExpRecord:
    value_percent: Decimal
    effective_at: datetime
    edited_by: str
    edited_at: datetime
    source_note: str
    version: int


def validate_expected_exp(record: ExpectedExpRecord) -> bool:
    if not (Decimal("0") <= record.value_percent <= Decimal("100")):
        raise Source12ControlError("EXPECTED_EXP_PERCENT_INVALID")
    if not all((record.edited_by, record.source_note)) or record.version < 1:
        raise Source12ControlError("EXPECTED_EXP_PROVENANCE_REQUIRED")
    return True


def calendar_ytd(*, events: Sequence[tuple[str, Decimal, datetime]], year: int, timezone_name: str) -> dict[str, Decimal]:
    tz = ZoneInfo(timezone_name)
    invoiced = sum((amount for kind, amount, at in events if kind == "INVOICE_ISSUED" and at.astimezone(tz).year == year), Decimal("0"))
    collected = sum((amount for kind, amount, at in events if kind == "PAYMENT_ALLOCATED" and at.astimezone(tz).year == year), Decimal("0"))
    return {"invoiced": _money(invoiced), "collected": _money(collected)}


def reconcile_legacy_finance_capability(records: Sequence[dict[str, object]]) -> dict[str, object]:
    """Synthetic-only capability proof; real-data execution is deliberately absent."""

    identities: dict[str, str] = {}
    exceptions: list[str] = []
    for record in records:
        identity = str(record.get("global_invoice_ref") or "")
        provenance = str(record.get("source_ref") or "")
        if not identity or not provenance:
            exceptions.append("PROVENANCE_REQUIRED")
            continue
        fingerprint = str(record.get("content_fingerprint") or "")
        if identity in identities and identities[identity] != fingerprint:
            exceptions.append(f"CONFLICTING_INVOICE_IDENTITY:{identity}")
        identities[identity] = fingerprint
    return {
        "capability": "PASS" if not exceptions else "BLOCKED",
        "real_data_execution": 0,
        "owner_real_data_acceptance": "NOT_EXECUTED",
        "exceptions": sorted(set(exceptions)),
        "preserves_historical_identities": True,
    }


def source12_v26_falsification(*, traceability_count: int, orphan_count: int, numeric_enum_diffs: int = 0, state_collapse_violations: int = 0, ripple_conflicts: int = 0) -> dict[str, object]:
    return {
        "requirement_count": traceability_count,
        "requirement_orphans": orphan_count,
        "numeric_enum_diffs_unresolved": numeric_enum_diffs,
        "state_collapse_violations": state_collapse_violations,
        "ripple_conflicts": ripple_conflicts,
        "pass": traceability_count == 188 and orphan_count == numeric_enum_diffs == state_collapse_violations == ripple_conflicts == 0,
    }
