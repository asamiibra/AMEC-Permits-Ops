"""Decision-independent controls for the Source10/Source11 current contract.

The helpers in this module are deliberately small and side-effect free.  They
consume already-canonical snapshots and return an explicit decision plus
machine-readable blockers.  A caller may therefore fail closed without
creating a second Project History, CRM, or external-communications system.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any, Mapping


def _text(value: Any) -> str:
    return " ".join(str(value or "").split()).casefold()


def _money(value: Any) -> Decimal | None:
    if value is None:
        return None
    cleaned = "".join(ch for ch in str(value) if ch.isdigit() or ch in ".-")
    if not cleaned:
        return None
    try:
        return Decimal(cleaned)
    except InvalidOperation:
        return None


def _same(left: Any, right: Any) -> bool:
    left_money, right_money = _money(left), _money(right)
    if left_money is not None and right_money is not None:
        return left_money == right_money
    return _text(left) == _text(right)


def commercial_reconciliation(
    proposal_fields: Mapping[str, Any] | None,
    contract_fields: Mapping[str, Any] | None,
    asserted_order: Mapping[str, Any] | None = None,
    *,
    strict: bool = False,
    order_applicable: bool | None = None,
    not_applicable_reason: str | None = None,
    order_source_count: int = 1,
    order_source_state: str | None = None,
) -> dict[str, Any]:
    """Compare the exact accepted proposal with the current Contract.

    An LPO/PO is only compared when its evidence explicitly supplies a
    structured commercial snapshot.  Applicability is explicit: a missing,
    ambiguous, or unstructured applicable order is blocked rather than
    treated as a successful reconciliation.
    """

    proposal = proposal_fields or {}
    contract = contract_fields or {}
    comparisons = {
        "amount": (proposal.get("price") or proposal.get("amount"), contract.get("amount")),
        "currency": (proposal.get("currency"), contract.get("currency")),
        "duration": (proposal.get("duration") or proposal.get("period"), contract.get("duration")),
        "payment_terms": (proposal.get("payment_terms") or proposal.get("payment_condition"), contract.get("payment_terms") or contract.get("payment_condition")),
        "scope": (proposal.get("scope") or proposal.get("scope_of_work"), contract.get("scope") or contract.get("scope_of_work")),
    }
    # Payment/scope wording can be refined in a Contract revision, but the
    # accepted commercial identity (amount, currency, duration) may not drift.
    comparison_items = comparisons if asserted_order is not None or strict else {key: comparisons[key] for key in ("amount", "currency", "duration")}
    mismatches = [key for key, (expected, actual) in comparison_items.items() if expected not in (None, "") and actual not in (None, "") and not _same(expected, actual)]
    missing = [key for key, (expected, actual) in comparison_items.items() if expected not in (None, "") and actual in (None, "")]
    if order_applicable is None:
        order_applicable = asserted_order is not None
    if order_source_state in {"BLOCKED_SUPERSEDED_SOURCE", "BLOCKED_CROSS_CONTRACT_SOURCE", "BLOCKED_UNAUTHORIZED_EXCEPTION"}:
        order_result: dict[str, Any] = {"status": order_source_state, "mismatches": [], "missing": [], "reason": "The asserted PO/LPO source is not eligible for Contract reconciliation."}
    elif order_source_count > 1:
        order_result: dict[str, Any] = {"status": "BLOCKED_AMBIGUOUS_SOURCE", "mismatches": [], "missing": [], "reason": "Multiple applicable PO/LPO assertions require one governed source."}
    elif asserted_order is None and order_applicable:
        order_result = {"status": "BLOCKED_MISSING_SOURCE", "mismatches": [], "missing": [], "reason": "Applicable PO/LPO evidence is missing."}
    elif asserted_order is None:
        reason = (not_applicable_reason or "The active commercial policy explicitly marks PO/LPO comparison not applicable.").strip()
        order_result = {"status": "NOT_APPLICABLE_WITH_REASON", "mismatches": [], "missing": [], "reason": reason}
    elif not isinstance(asserted_order, Mapping) or asserted_order.get("structured") is False or asserted_order.get("_structured") is False:
        order_result = {"status": "BLOCKED_UNSTRUCTURED_SOURCE", "mismatches": [], "missing": [], "reason": "PO/LPO evidence is not a structured commercial assertion."}
    else:
        order_comparison = commercial_reconciliation(proposal, asserted_order, None, strict=True)["proposal_to_contract"]
        order_result = {"status": "PASS" if not order_comparison["mismatches"] and not order_comparison["missing"] else "MISMATCH", **order_comparison}
    order_passes = order_result["status"] == "PASS" or (order_result["status"] == "NOT_APPLICABLE_WITH_REASON" and not order_applicable)
    status = "PASS" if not mismatches and not missing and order_passes else "BLOCKED"
    return {
        "status": status,
        "proposal_to_contract": {"mismatches": mismatches, "missing": missing},
        "order_to_proposal": order_result,
        "fail_closed": status != "PASS" or order_result["status"] != "PASS",
    }


def maker_checker_gate(snapshot: Mapping[str, Any] | None, *, enforce: bool = False) -> dict[str, Any]:
    """Validate explicit preparer/checker separation for a Contract revision."""

    record = dict((snapshot or {}).get("maker_checker") or {})
    if not enforce and not record:
        return {"status": "NOT_ASSERTED", "fail_closed": False, "blockers": []}
    preparer = _text(record.get("preparer"))
    checker = _text(record.get("checker"))
    blockers: list[str] = []
    if not preparer:
        blockers.append("PREPARER_REQUIRED")
    if not checker:
        blockers.append("CHECKER_REQUIRED")
    if preparer and checker and preparer == checker:
        blockers.append("MAKER_CHECKER_MUST_BE_DISTINCT")
    if not record.get("proposal_reconciled"):
        blockers.append("EXPLICIT_PROPOSAL_RECONCILIATION_REQUIRED")
    return {"status": "PASS" if not blockers else "BLOCKED", "fail_closed": bool(blockers), "blockers": blockers, "preparer": record.get("preparer"), "checker": record.get("checker")}


def advance_payment_gate(input_value: Mapping[str, Any] | None, evidence: list[Mapping[str, Any]] | None) -> dict[str, Any]:
    """Fail closed only when the Owner has enabled the activation gate."""

    config = input_value or {}
    required = bool(config.get("required", False))
    if not required:
        return {"status": "NOT_ASSERTED", "required": False, "fail_closed": False, "blockers": []}
    verified = [item for item in evidence or [] if str(item.get("source_role") or "").upper() == "ADVANCE_PAYMENT" and str(item.get("status") or "").upper() in {"VERIFIED", "HUMAN_VERIFIED", "APPROVED"} and bool((item.get("metadata") or {}).get("objective_bank_evidence"))]
    blockers = [] if verified else ["OBJECTIVE_ADVANCE_PAYMENT_EVIDENCE_REQUIRED"]
    return {"status": "PASS" if verified else "BLOCKED", "required": True, "fail_closed": bool(blockers), "blockers": blockers, "verified_evidence_count": len(verified)}


def operations_control_projection(fields: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a single read-only control projection without a new subsystem."""

    data = fields or {}
    required = ("project_reference", "start_date", "expected_end_date", "stage", "blocker", "risk", "next_action", "schedule", "delay_state", "extension_state", "aged_missing_document_state", "invoice_due_state", "earned_not_invoiced_state")
    missing = [key for key in required if data.get(key) in (None, "", {})]
    return {"status": "PASS" if not missing else "INCOMPLETE", "missing": missing, "source_of_record": "CANONICAL_PROJECT_CONTRACT_BILLING_READ_MODEL", "external_send": "HUMAN_CONTROLLED"}


def architecture_first_gate(metadata: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate the optional, explicitly enabled architecture-first gate."""

    data = metadata or {}
    if not data.get("required", False):
        return {"status": "NOT_ASSERTED", "fail_closed": False, "blockers": []}
    blockers = []
    if not data.get("architecture_revision"):
        blockers.append("ARCHITECTURE_REVISION_REQUIRED")
    for discipline in ("structure", "mep", "safety"):
        if not data.get(f"{discipline}_precoordination"):
            blockers.append(f"{discipline.upper()}_PRECOORDINATION_REQUIRED")
    if not data.get("detailed_work_unlock", False):
        blockers.append("DETAILED_WORK_UNLOCK_REQUIRED")
    return {"status": "PASS" if not blockers else "BLOCKED", "fail_closed": bool(blockers), "blockers": blockers}


def project_history_controls(data: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate Source11's separation and evidence-linkage invariants."""

    value = data or {}
    blockers: list[str] = []
    if not value.get("project_id"):
        blockers.append("PROJECT_ID_REQUIRED")
    if not value.get("owner_person_id") or not value.get("owner_company_id") or value.get("owner_person_id") == value.get("owner_company_id"):
        blockers.append("OWNER_PERSON_AND_COMPANY_MUST_BE_DISTINCT")
    if not value.get("operational_contact_role") or not value.get("operational_contact_organization"):
        blockers.append("OPERATIONAL_CONTACT_ROLE_AND_ORGANIZATION_REQUIRED")
    if value.get("contract_period") and value.get("authority_period") and value["contract_period"] == value["authority_period"]:
        blockers.append("CONTRACT_PERIOD_AND_AUTHORITY_PERIOD_MUST_REMAIN_DISTINCT")
    if not value.get("case_history_events"):
        blockers.append("CASE_HISTORY_EVENT_EVIDENCE_REQUIRED")
    if not value.get("technical_report_evidence_links"):
        blockers.append("TECHNICAL_REPORT_EVIDENCE_LINKS_REQUIRED")
    if not value.get("authorization_evidence"):
        blockers.append("AUTHORIZATION_EVIDENCE_REQUIRED")
    if not value.get("missing_document_contact_route"):
        blockers.append("MISSING_DOCUMENT_CONTACT_ROUTE_REQUIRED")
    if not value.get("location_context"):
        blockers.append("LOCATION_CONTEXT_REQUIRED")
    if not value.get("onboarding_cohort"):
        blockers.append("ONBOARDING_COHORT_CONFIGURATION_REQUIRED")
    if value.get("operational_actor_is_engineer") and not value.get("engineering_escalation"):
        blockers.append("NON_ENGINEER_ESCALATION_REQUIRED")
    return {"status": "PASS" if not blockers else "BLOCKED", "fail_closed": bool(blockers), "blockers": blockers, "external_send": "HUMAN_CONTROLLED", "canonical_store": "EXISTING_PROJECT_CASE_DOCUMENT_EVIDENCE_MODELS"}
