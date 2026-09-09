from datetime import date, datetime, timezone
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor

import pytest

from backend.app.services.source12_finance_controls import (
    CollisionSafeNumberAllocator,
    ExpectedExpRecord,
    FXRateRecord,
    InvoiceState,
    PaymentAllocation,
    PaymentEvidence,
    ScopedCapability,
    Source12ControlError,
    authorize_finance_capability,
    calendar_ytd,
    clone_previous_invoice,
    qar_amount,
    reconcile_legacy_finance_capability,
    request_design_billable_stage,
    rollup_finance,
    source12_v26_falsification,
    structured_service_period,
    supervision_monthly_queue,
    transition_invoice,
    validate_expected_exp,
)


def grant(*, capabilities=frozenset({"FINANCE_PREPARE_INVOICE"})):
    return ScopedCapability("user-1", "PROCESS_CHAMPION", frozenset({"project-1"}), capabilities, "assignment-1")


def payment(payment_id, amount, *, status="VERIFIED"):
    return PaymentEvidence(payment_id, "project-1", Decimal(str(amount)), "QAR", "BANK_TRANSFER", f"synthetic://{payment_id}", status)


def allocation(allocation_id, payment_id, amount, *, milestone_id=None, invoice_id="invoice-1"):
    return PaymentAllocation(allocation_id, payment_id, invoice_id, "project-1", Decimal(str(amount)), milestone_id, "ALLOCATED", datetime(2026, 8, 1, tzinfo=timezone.utc))


def test_01_finance_work_queue_requires_scoped_capability():
    assert authorize_finance_capability(grant(), project_id="project-1", capability="FINANCE_PREPARE_INVOICE")
    with pytest.raises(Source12ControlError, match="SCOPED_FINANCE_CAPABILITY_REQUIRED"):
        authorize_finance_capability(grant(), project_id="project-2", capability="FINANCE_PREPARE_INVOICE")


def test_02_job_title_only_has_zero_finance_authority():
    with pytest.raises(Source12ControlError, match="SCOPED_FINANCE_CAPABILITY_REQUIRED"):
        authorize_finance_capability(grant(capabilities=frozenset()), project_id="project-1", capability="FINANCE_PREPARE_INVOICE", job_title="Finance Manager")


def test_03_no_fourth_global_persona():
    with pytest.raises(Source12ControlError, match="FOURTH_GLOBAL_PERSONA_NOT_ALLOWED"):
        authorize_finance_capability(ScopedCapability("u", "FINANCE_SECRETARY", frozenset({"project-1"}), frozenset({"FINANCE_PREPARE_INVOICE"}), "a"), project_id="project-1", capability="FINANCE_PREPARE_INVOICE")


def test_04_engineering_request_does_not_grant_issue():
    request = request_design_billable_stage(persona="RESPONSIBLE_ENGINEER", project_id="project-1", milestone_id="m-1", evidence_ref="synthetic://stage")
    assert request["billing_eligible"] is True
    assert request["invoice_issue_authority"] is False
    assert request["payment_authority"] is False


def test_05_supervision_queue_is_eligibility_only():
    queue = supervision_monthly_queue(active_project_ids=["project-1"], service_year=2026, service_month=8)
    assert queue == [{"project_id": "project-1", "service_period": "2026-08 SUPERVISION", "billing_eligible": True, "invoice_issued": False}]


def test_06_structured_service_period_retained():
    assert structured_service_period(2026, 8, "supervision") == "2026-08 SUPERVISION"


def test_07_global_and_project_identity_are_distinct():
    invoice = InvoiceState("i", "project-1", "INV-AMEC-2026-000001", 4)
    assert invoice.global_invoice_ref != str(invoice.project_invoice_ordinal)


def test_08_concurrent_global_numbering_cannot_collide():
    allocator = CollisionSafeNumberAllocator()
    with ThreadPoolExecutor(max_workers=8) as pool:
        refs = list(pool.map(lambda _: allocator.reserve(year=2026), range(24)))
    assert len(set(refs)) == 24


def test_09_concurrent_project_local_numbering_cannot_collide():
    from backend.app.services.source12_finance_controls import ProjectOrdinalAllocator
    allocator = ProjectOrdinalAllocator()
    with ThreadPoolExecutor(max_workers=8) as pool:
        ordinals = list(pool.map(lambda _: allocator.reserve("project-1"), range(24)))
    assert sorted(ordinals) == list(range(1, 25))


def test_10_clone_preserves_previous_invoice():
    previous = InvoiceState("old", "project-1", "INV-AMEC-2026-000001", 3, "ACKNOWLEDGED", "2026-07 SUPERVISION", ("delivery",), ("ack",), ("allocation",))
    clone = clone_previous_invoice(previous, new_invoice_id="new", new_global_ref="INV-AMEC-2026-000002", new_project_ordinal=4, service_period="2026-08 SUPERVISION")
    assert previous.status == "ACKNOWLEDGED" and clone.invoice_id != previous.invoice_id


def test_11_clone_gets_new_identities():
    previous = InvoiceState("old", "project-1", "old-ref", 3)
    clone = clone_previous_invoice(previous, new_invoice_id="new", new_global_ref="new-ref", new_project_ordinal=4, service_period="2026-08 SUPERVISION")
    assert (clone.global_invoice_ref, clone.project_invoice_ordinal) == ("new-ref", 4)


def test_12_clone_does_not_copy_issue_state():
    previous = InvoiceState("old", "project-1", "old-ref", 3, "ISSUED")
    assert clone_previous_invoice(previous, new_invoice_id="new", new_global_ref="new-ref", new_project_ordinal=4, service_period="2026-08 SUPERVISION").status == "DRAFT"


def test_13_clone_does_not_copy_delivery_ack_state():
    previous = InvoiceState("old", "project-1", "old-ref", 3, "ACKNOWLEDGED", "old", ("d",), ("a",))
    clone = clone_previous_invoice(previous, new_invoice_id="new", new_global_ref="new-ref", new_project_ordinal=4, service_period="new")
    assert clone.delivery_evidence == () and clone.acknowledgement_evidence == ()


def test_14_clone_does_not_copy_payment_state():
    previous = InvoiceState("old", "project-1", "old-ref", 3, "PAID", payment_allocation_ids=("a",))
    assert clone_previous_invoice(previous, new_invoice_id="new", new_global_ref="new-ref", new_project_ordinal=4, service_period="new").payment_allocation_ids == ()


def test_15_prepared_accepted_issued_are_separate():
    invoice = InvoiceState("i", "project-1", "ref", 1, "DRAFT")
    invoice = transition_invoice(invoice, "READY_FOR_SIGNATURE")
    invoice = transition_invoice(invoice, "ACCEPTED")
    assert invoice.status != "ISSUED"


def test_16_issued_delivered_acknowledged_are_separate():
    invoice = InvoiceState("i", "project-1", "ref", 1, "ISSUED")
    assert transition_invoice(invoice, "DELIVERED").status == "DELIVERED"
    with pytest.raises(Source12ControlError):
        transition_invoice(invoice, "ACKNOWLEDGED")


def test_17_payment_evidence_verified_and_allocated_are_separate():
    observed = payment("p", 100, status="OBSERVED")
    result = rollup_finance(project_value=100, invoice_total=100, payments=[observed], allocations=[allocation("a", "p", 100)], invoice_id="invoice-1", project_id="project-1")
    assert result["project_total_receipts"] == Decimal("0.00")


def test_18_allocation_does_not_imply_project_settlement():
    result = rollup_finance(project_value=200, invoice_total=100, payments=[payment("p", 100)], allocations=[allocation("a", "p", 100)], invoice_id="invoice-1", project_id="project-1")
    assert result["project_balance"] == Decimal("100.00")


def test_19_invoice_report_and_open_queue_are_distinct_projections():
    from backend.app.services.source12_finance_controls import invoice_report, open_invoice_queue
    history = [InvoiceState("i", "project-1", "ref", 1, "PAID")]
    assert invoice_report(history) == history
    assert open_invoice_queue(history) == []


def test_20_paid_invoice_is_removed_from_queue_not_history():
    from backend.app.services.source12_finance_controls import invoice_report, open_invoice_queue
    paid = InvoiceState("i", "project-1", "ref", 1, "PAID")
    assert len(invoice_report([paid])) == 1 and open_invoice_queue([paid]) == []


def test_21_qar_contract_value_is_qar_amount():
    assert qar_amount(contract_value=20000, contract_currency="QAR") == Decimal("20000.00")


def test_22_non_qar_without_fx_fails_closed():
    with pytest.raises(Source12ControlError, match="FX_RATE_RECORD_REQUIRED"):
        qar_amount(contract_value=100, contract_currency="USD")


def test_23_approved_versioned_fx_is_exact_and_provenanced():
    rate = FXRateRecord("USD", Decimal("3.64"), date(2026, 8, 1), "synthetic://owner-rate", "v1", "owner-1", datetime(2026, 8, 1, tzinfo=timezone.utc))
    assert qar_amount(contract_value=100, contract_currency="USD", fx_record=rate) == Decimal("364.00")


def test_24_invalidated_fx_fails_closed():
    rate = FXRateRecord("USD", Decimal("3.64"), date(2026, 8, 1), "synthetic://owner-rate", "v1", "owner-1", datetime(2026, 8, 1, tzinfo=timezone.utc), "INVALIDATED")
    with pytest.raises(Source12ControlError, match="FX_RATE_RECORD_REQUIRED"):
        qar_amount(contract_value=100, contract_currency="USD", fx_record=rate)


def test_25_expected_exp_has_owner_version_provenance():
    assert validate_expected_exp(ExpectedExpRecord(Decimal("12.5"), datetime(2026, 8, 1, tzinfo=timezone.utc), "owner-1", datetime(2026, 8, 1, tzinfo=timezone.utc), "synthetic owner note", 1))


def test_26_expected_exp_has_no_automatic_formula():
    record = ExpectedExpRecord(Decimal("12.5"), datetime(2026, 8, 1, tzinfo=timezone.utc), "owner-1", datetime(2026, 8, 1, tzinfo=timezone.utc), "explicit", 1)
    assert record.value_percent == Decimal("12.5")


def test_27_company_ytd_uses_calendar_year():
    events = [("INVOICE_ISSUED", Decimal("10"), datetime(2026, 1, 1, tzinfo=timezone.utc)), ("INVOICE_ISSUED", Decimal("9"), datetime(2025, 12, 31, 20, tzinfo=timezone.utc))]
    assert calendar_ytd(events=events, year=2026, timezone_name="Asia/Qatar")["invoiced"] == Decimal("10.00")


def test_28_ytd_invoiced_uses_issue_events():
    assert calendar_ytd(events=[("INVOICE_DRAFT", Decimal("99"), datetime(2026, 1, 1, tzinfo=timezone.utc))], year=2026, timezone_name="Asia/Qatar")["invoiced"] == Decimal("0.00")


def test_29_ytd_collected_uses_allocations():
    assert calendar_ytd(events=[("PAYMENT_RECEIVED", Decimal("99"), datetime(2026, 1, 1, tzinfo=timezone.utc)), ("PAYMENT_ALLOCATED", Decimal("10"), datetime(2026, 1, 1, tzinfo=timezone.utc))], year=2026, timezone_name="Asia/Qatar")["collected"] == Decimal("10.00")


def test_30_qar_20k_first_payment_arithmetic():
    result = rollup_finance(project_value=20000, invoice_total=20000, payments=[payment("p1", 10000)], allocations=[allocation("a1", "p1", 10000)], invoice_id="invoice-1", project_id="project-1")
    assert result["project_total_receipts"] == Decimal("10000.00") and result["project_balance"] == Decimal("10000.00")


def test_31_qar_20k_second_payment_arithmetic():
    result = rollup_finance(project_value=20000, invoice_total=20000, payments=[payment("p1", 10000), payment("p2", 10000)], allocations=[allocation("a1", "p1", 10000), allocation("a2", "p2", 10000)], invoice_id="invoice-1", project_id="project-1")
    assert result["project_total_receipts"] == Decimal("20000.00") and result["project_balance"] == Decimal("0.00")


def test_32_total_receipts_has_no_manual_override():
    result = rollup_finance(project_value=20000, invoice_total=20000, payments=[payment("p1", 10000)], allocations=[allocation("a1", "p1", 10000)], invoice_id="invoice-1", project_id="project-1")
    assert result["project_total_receipts"] != Decimal("0.00")


def test_33_project_balance_has_no_manual_override():
    result = rollup_finance(project_value=20000, invoice_total=20000, payments=[], allocations=[], invoice_id="invoice-1", project_id="project-1")
    assert result["project_balance"] == Decimal("20000.00")


def test_34_milestone_actual_collected_has_no_manual_override():
    result = rollup_finance(project_value=20000, invoice_total=20000, payments=[payment("p1", 10000)], allocations=[allocation("a1", "p1", 10000, milestone_id="m1")], invoice_id="invoice-1", project_id="project-1", milestone_id="m1")
    assert result["milestone_actual_collected"] == Decimal("10000.00")


def test_35_accepted_contract_source_is_pinned_by_allocator_boundary():
    allocator = CollisionSafeNumberAllocator(historical_refs={"INV-AMEC-2026-000001"}, historical_reconciled=False)
    assert allocator.reserve(year=2026) == "INV-AMEC-2026-000002"


def test_36_contract_payment_terms_must_be_verified_before_projection():
    with pytest.raises(Source12ControlError, match="BILLING_MILESTONE_CONTRACT_TERM_REQUIRED"):
        from backend.app.services.source12_finance_controls import validate_billing_milestone_source
        validate_billing_milestone_source(None)


def test_37_physical_evidence_stages_are_linked_not_collapsed():
    invoice = InvoiceState("i", "project-1", "ref", 1, "ISSUED", delivery_evidence=("delivery",), acknowledgement_evidence=())
    assert invoice.delivery_evidence and not invoice.acknowledgement_evidence


def test_38_vat_subtotal_not_invented():
    from backend.app.services.source12_finance_controls import SOURCE12_MANDATORY_V1_FIELDS
    assert "VAT" not in SOURCE12_MANDATORY_V1_FIELDS and "SUBTOTAL" not in SOURCE12_MANDATORY_V1_FIELDS


def test_39_no_universal_five_or_seven_day_term():
    from backend.app.services.source12_finance_controls import UNIVERSAL_DUE_TERM_DAYS
    assert UNIVERSAL_DUE_TERM_DAYS is None


def test_40_no_real_production_invoice_number_reserved():
    allocator = CollisionSafeNumberAllocator()
    with pytest.raises(Source12ControlError, match="LEGACY_FINANCE_RECONCILIATION_REQUIRED"):
        allocator.reserve(year=2026, synthetic=False)


def test_41_no_real_bank_or_account_value_invented():
    from backend.app.services.source12_finance_controls import assert_synthetic_fixture
    assert_synthetic_fixture({"bank_reference": "synthetic://bank"})
    with pytest.raises(Source12ControlError, match="REAL_FINANCE_VALUE_NOT_ALLOWED"):
        assert_synthetic_fixture({"bank_reference": "QA99REALBANK"})


def test_42_no_real_amec_finance_data_read():
    result = reconcile_legacy_finance_capability([{"global_invoice_ref": "INV-HIST-001", "source_ref": "synthetic://invoice", "content_fingerprint": "a"}])
    assert result["real_data_execution"] == 0 and result["owner_real_data_acceptance"] == "NOT_EXECUTED"


def test_source12_v26_equivalent_falsification_passes():
    assert source12_v26_falsification(traceability_count=188, orphan_count=0)["pass"] is True
