"""Deterministic policy controls for the Source15 current-contract seams.

These helpers operate on canonical-domain records and return immutable
projections. They do not create a second checklist, regulatory repository, or
Finance source of truth, and they never perform external or protected actions.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, Iterable, Mapping


class CurrentContractControlError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


GOVERNED_AMEC_AUTHORITY_ENGAGEMENTS = frozenset({
    "AMEC_CIVIL_DEFENSE",
    "AMEC_MAINTENANCE_PERMIT",
    "CIVIL_DEFENSE",
    "MAINTENANCE_PERMIT",
})

# G0.12 owner decision: every contracted AMEC Civil Defense / Maintenance
# Permit engagement is rooted in a canonical Project before an AuthorityCase
# is created. This does not make every Project workflow stage mandatory.
CIVIL_DEFENSE_AUTHORITY_CASE_PROJECT_MODEL = "CANONICAL_PROJECT_REQUIRED"


def require_canonical_project_for_authority_case(
    payload: Mapping[str, Any], *, journey_project_id: str | None = None
) -> str | None:
    """Require a canonical Project for governed AMEC authority engagements.

    Generic shared-domain foundation cases may remain project-agnostic.  An
    explicitly contracted AMEC Civil Defense / Maintenance Permit engagement
    may not: its project identity must come from the request or its governed
    journey, and a supplied journey project must agree with the request.
    """

    engagement_values = {
        str(payload.get(key) or "").strip().upper()
        for key in ("engagement_type", "engagement_kind", "service_type_code", "service_type", "transaction_type")
    }
    governed = bool(
        payload.get("contracted_amec")
        or payload.get("amec_contracted")
        or payload.get("governed_amec_engagement")
        or engagement_values & GOVERNED_AMEC_AUTHORITY_ENGAGEMENTS
    )
    if not governed:
        return None
    project_id = str(payload.get("project_id") or journey_project_id or "").strip()
    if not project_id:
        raise CurrentContractControlError("CANONICAL_PROJECT_REQUIRED_FOR_GOVERNED_AUTHORITY_CASE")
    if journey_project_id and project_id != str(journey_project_id):
        raise CurrentContractControlError("GOVERNED_AUTHORITY_CASE_PROJECT_MISMATCH")
    return project_id


@dataclass(frozen=True)
class ChecklistItem:
    key: str
    label: str
    responsible_role: str
    applicable: bool
    status: str = "MISSING"
    evidence_document_version_id: str | None = None
    evidence_sha256: str | None = None
    verified_by: str | None = None


def _applies(definition: Mapping[str, Any], context: Mapping[str, Any]) -> bool:
    predicate = definition.get("when")
    if predicate is None:
        return True
    if callable(predicate):
        return bool(predicate(context))
    if isinstance(predicate, Mapping):
        return all(context.get(key) == value for key, value in predicate.items())
    raise CurrentContractControlError("CHECKLIST_APPLICABILITY_RULE_INVALID")


def resolve_dynamic_checklist(definitions: Iterable[Mapping[str, Any]], context: Mapping[str, Any]) -> tuple[ChecklistItem, ...]:
    """Resolve authority/transaction/party/property/project conditions."""

    items = []
    seen: set[str] = set()
    for definition in definitions:
        key = str(definition.get("key") or "").strip()
        if not key or key in seen:
            raise CurrentContractControlError("CHECKLIST_REQUIREMENT_KEY_INVALID_OR_DUPLICATE")
        seen.add(key)
        role = str(definition.get("responsible_role") or "OFFICE")
        items.append(ChecklistItem(key=key, label=str(definition.get("label") or key), responsible_role=role, applicable=_applies(definition, context), status="MISSING" if _applies(definition, context) else "NOT_APPLICABLE"))
    return tuple(items)


def file_verified_document_immediately(items: Iterable[ChecklistItem], *, requirement_key: str, document_version_id: str, document_sha256: str, verified_by: str) -> tuple[ChecklistItem, ...]:
    """Commit one verified DocumentVersion without waiting for package completion."""

    if not document_version_id or not document_sha256 or not verified_by:
        raise CurrentContractControlError("VERIFIED_DOCUMENT_ID_HASH_AND_ACTOR_REQUIRED")
    rows = list(items)
    matches = [index for index, item in enumerate(rows) if item.key == requirement_key]
    if len(matches) != 1:
        raise CurrentContractControlError("CHECKLIST_REQUIREMENT_NOT_FOUND")
    index = matches[0]
    item = rows[index]
    if not item.applicable:
        raise CurrentContractControlError("NOT_APPLICABLE_REQUIREMENT_CANNOT_RECEIVE_EVIDENCE")
    rows[index] = replace(item, status="VERIFIED", evidence_document_version_id=document_version_id, evidence_sha256=document_sha256, verified_by=verified_by)
    return tuple(rows)


def route_responsibility(responsible_role: str) -> dict[str, str]:
    role = str(responsible_role or "").upper()
    queues = {"CLIENT": "CLIENT_OWNER_FOLLOW_UP", "OWNER": "CLIENT_OWNER_FOLLOW_UP", "ENGINEERING": "ENGINEERING_WORK_QUEUE", "OFFICE": "OFFICE_OPERATOR_WORK_QUEUE", "AUTHORITY": "AUTHORITY_FOLLOW_UP"}
    if role not in queues:
        raise CurrentContractControlError("RESPONSIBILITY_ROLE_UNSUPPORTED")
    return {"responsible_role": role, "work_queue": queues[role]}


def build_invoice_lines(lines: Iterable[Mapping[str, Any]]) -> tuple[InvoiceLine, ...]:
    """Validate the quantity/unit-price invoice structure before persistence."""

    result = []
    for line in lines:
        description = str(line.get("description") or "").strip()
        quantity = Decimal(line.get("quantity", "0"))
        unit_price = Decimal(line.get("unit_price", "0"))
        if not description or quantity <= 0 or unit_price < 0:
            raise CurrentContractControlError("INVOICE_LINE_QUANTITY_UNIT_PRICE_INVALID")
        result.append(InvoiceLine(description=description, quantity=quantity, unit_price=unit_price))
    if not result:
        raise CurrentContractControlError("INVOICE_LINE_REQUIRED")
    return tuple(result)


@dataclass(frozen=True)
class HeirEvidenceRequirement:
    heir_id: str
    identity_document_required: bool = True
    contact_required: bool = True
    representation_evidence_required: bool = True
    legal_determination_by_ai: bool = False


def build_estate_heir_requirements(*, deceased_owner_id: str, heirs: Iterable[Mapping[str, Any]]) -> tuple[HeirEvidenceRequirement, ...]:
    """Create per-heir evidence requirements; legal status remains human-owned."""

    if not deceased_owner_id:
        raise CurrentContractControlError("DECEASED_OWNER_ID_REQUIRED")
    rows = tuple(HeirEvidenceRequirement(heir_id=str(item.get("heir_id") or "")) for item in heirs)
    if not rows or any(not row.heir_id for row in rows) or len({row.heir_id for row in rows}) != len(rows):
        raise CurrentContractControlError("UNIQUE_HEIR_IDENTITIES_REQUIRED")
    return rows


@dataclass(frozen=True)
class TechnicalReportRevision:
    report_id: str
    revision_number: int
    project_id: str
    property_id: str
    facts: Mapping[str, Any]
    drawing_revision_ids: tuple[str, ...]
    signature_evidence_id: str | None
    prior_revision_id: str | None = None


def create_technical_report_revision(previous: TechnicalReportRevision | None, *, report_id: str, project_id: str, property_id: str, facts: Mapping[str, Any], drawing_revision_ids: Iterable[str], signature_evidence_id: str | None) -> TechnicalReportRevision:
    if not report_id or not project_id or not property_id:
        raise CurrentContractControlError("TECHNICAL_REPORT_CANONICAL_CONTEXT_REQUIRED")
    if not signature_evidence_id:
        raise CurrentContractControlError("TECHNICAL_REPORT_HUMAN_SIGNATURE_EVIDENCE_REQUIRED")
    revision_number = previous.revision_number + 1 if previous else 1
    return TechnicalReportRevision(report_id=report_id, revision_number=revision_number, project_id=project_id, property_id=property_id, facts=dict(facts), drawing_revision_ids=tuple(drawing_revision_ids), signature_evidence_id=signature_evidence_id, prior_revision_id=previous.report_id if previous else None)


def classify_authority_finding(*, finding_kind: str, engineering_impact: str = "UNKNOWN") -> dict[str, Any]:
    kind = str(finding_kind or "").upper()
    if kind not in {"COMMENT", "REJECTION"}:
        raise CurrentContractControlError("AUTHORITY_FINDING_KIND_REQUIRED")
    if kind == "REJECTION":
        return {"state": "REJECTED", "comment_received": False, "rejected": True, "correction_class": None}
    impact = str(engineering_impact or "UNKNOWN").upper()
    correction_class = {"DOCUMENT": "DOCUMENT_CORRECTION", "ENGINEERING": "ENGINEERING_CORRECTION", "MIXED": "MIXED_CORRECTION"}.get(impact, "MIXED_CORRECTION")
    return {"state": "COMMENT_RECEIVED", "comment_received": True, "rejected": False, "correction_class": correction_class}


def fan_out_correction_work(*, finding_id: str, correction_class: str) -> tuple[dict[str, str], ...]:
    if correction_class not in {"DOCUMENT_CORRECTION", "ENGINEERING_CORRECTION", "MIXED_CORRECTION"}:
        raise CurrentContractControlError("CORRECTION_CLASS_INVALID")
    queues = {"DOCUMENT_CORRECTION": ("OFFICE_OPERATOR_WORK_QUEUE",), "ENGINEERING_CORRECTION": ("ENGINEERING_WORK_QUEUE",), "MIXED_CORRECTION": ("OFFICE_OPERATOR_WORK_QUEUE", "ENGINEERING_WORK_QUEUE")}[correction_class]
    return tuple({"finding_id": finding_id, "work_queue": queue, "revision_required": "true"} for queue in queues)


def industrial_area_attachment_variant(*, industrial_area: bool) -> dict[str, Any]:
    return {"variant": "INDUSTRIAL_AREA" if industrial_area else "GENERAL_MUNICIPALITY", "conditional": industrial_area, "required_categories": ["LEASE", "KROKY", "INDUSTRIAL_AREA_APPROVAL", "OWNER_ID", "ENGINEERING_AUTHORIZATION", "UTILITIES", "SITE_PHOTOS"] if industrial_area else ["TITLE_OR_TENURE", "OWNER_ID", "ENGINEERING_AUTHORIZATION"]}


def kroky_provenance_link(*, kroky_document_version_id: str, croquis_document_version_id: str, provenance: Mapping[str, Any]) -> bool:
    """Name similarity is insufficient; exact provenance is required."""

    return bool(kroky_document_version_id and croquis_document_version_id and provenance.get("same_source_record") is True and provenance.get("equivalence_assertion") is True and provenance.get("verified_by"))


def build_project_operating_index(projects: Iterable[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for project in projects:
        project_id = str(project.get("project_id") or "")
        if not project_id or project_id in index:
            raise CurrentContractControlError("PROJECT_OPERATING_INDEX_ID_INVALID_OR_DUPLICATE")
        index[project_id] = {"project_id": project_id, "requirement_state": project.get("requirement_state", "UNKNOWN"), "missing_or_invalid_items": tuple(project.get("missing_or_invalid_items", ())), "responsible_actor": project.get("responsible_actor", "UNASSIGNED"), "next_action": project.get("next_action", "REVIEW"), "engineering_work": tuple(project.get("engineering_work", ())), "client_owner_work": tuple(project.get("client_owner_work", ())), "office_work": tuple(project.get("office_work", ())) }
    return index


@dataclass(frozen=True)
class InvoiceLine:
    description: str
    quantity: Decimal
    unit_price: Decimal

    @property
    def total(self) -> Decimal:
        return (self.quantity * self.unit_price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def allocate_payment_to_invoices(*, payment_id: str, payment_amount: Decimal, allocations: Mapping[str, Decimal], verified: bool) -> tuple[dict[str, Any], ...]:
    if not payment_id or not verified:
        raise CurrentContractControlError("VERIFIED_PAYMENT_REQUIRED_BEFORE_ALLOCATION")
    if any(Decimal(amount) <= 0 for amount in allocations.values()):
        raise CurrentContractControlError("PAYMENT_ALLOCATION_AMOUNT_INVALID")
    total = sum((Decimal(amount) for amount in allocations.values()), Decimal("0"))
    if total > Decimal(payment_amount):
        raise CurrentContractControlError("PAYMENT_ALLOCATION_EXCEEDS_RECEIPT")
    return tuple({"payment_id": payment_id, "invoice_id": invoice_id, "amount": Decimal(amount).quantize(Decimal("0.01")), "verified": True} for invoice_id, amount in allocations.items())


def project_finance_rollup(*, project_value: Decimal, invoice_amounts: Iterable[Decimal], allocated_amounts: Iterable[Decimal]) -> dict[str, Decimal]:
    total_invoiced = sum((Decimal(value) for value in invoice_amounts), Decimal("0"))
    total_receipts = sum((Decimal(value) for value in allocated_amounts), Decimal("0"))
    return {"project_value": Decimal(project_value), "total_invoiced": total_invoiced, "total_receipts": total_receipts, "outstanding": total_invoiced - total_receipts, "project_balance": Decimal(project_value) - total_receipts}


def contract_finance_context(*, contract_id: str, project_id: str, billing_plan_id: str, invoice_ids: Iterable[str], outstanding: Decimal) -> dict[str, Any]:
    if not contract_id or not project_id or not billing_plan_id:
        raise CurrentContractControlError("CONTRACT_FINANCE_CONTEXT_REQUIRED")
    return {"contract_id": contract_id, "project_id": project_id, "billing_plan_id": billing_plan_id, "invoice_ids": tuple(invoice_ids), "outstanding": Decimal(outstanding), "open_finance_workspace": True, "duplicates_finance_workspace": False}


def sensitive_finance_log_projection(*, event: str, safe_identifiers: Mapping[str, Any]) -> dict[str, Any]:
    """Return ordinary-log fields without bank, IBAN, amount, or evidence content."""

    return {"event": event, "identifiers": dict(safe_identifiers), "sensitive_fields_omitted": ["bank_details", "iban", "account_information", "invoice_amount", "payment_evidence_content"]}
