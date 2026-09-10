"""Source15 current-contract behavior and protected-boundary tests."""

from decimal import Decimal

import pytest

from backend.app.services.current_contract_controls import (
    ChecklistItem,
    CurrentContractControlError,
    TechnicalReportRevision,
    allocate_payment_to_invoices,
    build_invoice_lines,
    build_estate_heir_requirements,
    build_project_operating_index,
    classify_authority_finding,
    contract_finance_context,
    create_technical_report_revision,
    fan_out_correction_work,
    file_verified_document_immediately,
    industrial_area_attachment_variant,
    kroky_provenance_link,
    project_finance_rollup,
    resolve_dynamic_checklist,
    route_responsibility,
    require_canonical_project_for_authority_case,
    sensitive_finance_log_projection,
)


def test_dynamic_checklist_is_contextual_and_partial_filing_is_immediate():
    items = resolve_dynamic_checklist([
        {"key": "title", "label": "Title deed", "responsible_role": "CLIENT"},
        {"key": "industrial-approval", "label": "Industrial approval", "responsible_role": "OFFICE", "when": {"industrial_area": True}},
    ], {"industrial_area": False})
    assert [item.status for item in items] == ["MISSING", "NOT_APPLICABLE"]
    updated = file_verified_document_immediately(items, requirement_key="title", document_version_id="dv-1", document_sha256="a" * 64, verified_by="operator-1")
    assert updated[0].status == "VERIFIED" and updated[1].status == "NOT_APPLICABLE"


def test_responsibility_routing_keeps_client_and_engineering_queues_separate():
    assert route_responsibility("CLIENT")["work_queue"] == "CLIENT_OWNER_FOLLOW_UP"
    assert route_responsibility("ENGINEERING")["work_queue"] == "ENGINEERING_WORK_QUEUE"


def test_governed_amec_authority_case_requires_a_canonical_project():
    assert require_canonical_project_for_authority_case({"engagement_type": "OTHER"}) is None
    assert require_canonical_project_for_authority_case(
        {"engagement_type": "MAINTENANCE_PERMIT"}, journey_project_id="project-1"
    ) == "project-1"
    with pytest.raises(CurrentContractControlError) as missing:
        require_canonical_project_for_authority_case({"contracted_amec": True})
    assert missing.value.code == "CANONICAL_PROJECT_REQUIRED_FOR_GOVERNED_AUTHORITY_CASE"
    with pytest.raises(CurrentContractControlError) as mismatch:
        require_canonical_project_for_authority_case(
            {"engagement_type": "CIVIL_DEFENSE", "project_id": "project-2"},
            journey_project_id="project-1",
        )
    assert mismatch.value.code == "GOVERNED_AUTHORITY_CASE_PROJECT_MISMATCH"


def test_estate_creates_per_heir_evidence_requirements_without_legal_determination():
    rows = build_estate_heir_requirements(deceased_owner_id="owner-1", heirs=[{"heir_id": "h1"}, {"heir_id": "h2"}])
    assert [row.heir_id for row in rows] == ["h1", "h2"]
    assert all(row.legal_determination_by_ai is False for row in rows)
    with pytest.raises(CurrentContractControlError):
        build_estate_heir_requirements(deceased_owner_id="owner-1", heirs=[{"heir_id": "h1"}, {"heir_id": "h1"}])


def test_technical_report_revision_is_immutable_and_links_previous_revision():
    first = create_technical_report_revision(None, report_id="tr-1", project_id="p-1", property_id="prop-1", facts={"scope": "existing"}, drawing_revision_ids=("dr-1",), signature_evidence_id="sig-1")
    second = create_technical_report_revision(first, report_id="tr-2", project_id="p-1", property_id="prop-1", facts={"scope": "revised"}, drawing_revision_ids=("dr-2",), signature_evidence_id="sig-2")
    assert first.revision_number == 1 and second.revision_number == 2 and second.prior_revision_id == "tr-1"
    assert isinstance(first, TechnicalReportRevision)


def test_comment_and_rejection_are_distinct_and_mixed_comments_fan_out():
    comment = classify_authority_finding(finding_kind="COMMENT", engineering_impact="MIXED")
    rejection = classify_authority_finding(finding_kind="REJECTION")
    assert comment["state"] == "COMMENT_RECEIVED" and comment["rejected"] is False
    assert rejection["state"] == "REJECTED" and rejection["comment_received"] is False
    queues = fan_out_correction_work(finding_id="finding-1", correction_class=comment["correction_class"])
    assert {row["work_queue"] for row in queues} == {"OFFICE_OPERATOR_WORK_QUEUE", "ENGINEERING_WORK_QUEUE"}


def test_industrial_variant_and_kroky_require_exact_provenance():
    variant = industrial_area_attachment_variant(industrial_area=True)
    assert variant["variant"] == "INDUSTRIAL_AREA" and "KROKY" in variant["required_categories"]
    assert kroky_provenance_link(kroky_document_version_id="k", croquis_document_version_id="c", provenance={"same_source_record": False, "equivalence_assertion": True, "verified_by": "operator"}) is False
    assert kroky_provenance_link(kroky_document_version_id="k", croquis_document_version_id="c", provenance={"same_source_record": True, "equivalence_assertion": True, "verified_by": "operator"}) is True


def test_fifty_project_operating_index_exposes_next_action_without_folder_reconstruction():
    projects = [{"project_id": f"p-{i}", "requirement_state": "OPEN", "missing_or_invalid_items": ("title",), "responsible_actor": "CLIENT", "next_action": "FOLLOW_UP"} for i in range(50)]
    index = build_project_operating_index(projects)
    assert len(index) == 50 and index["p-49"]["next_action"] == "FOLLOW_UP"


def test_finance_supports_structured_lines_multi_invoice_allocation_and_rollup():
    lines = build_invoice_lines([
        {"description": "Permit coordination", "quantity": "2", "unit_price": "125.50"},
    ])
    assert lines[0].total == Decimal("251.00")
    allocations = allocate_payment_to_invoices(payment_id="pay-1", payment_amount=Decimal("100"), allocations={"inv-1": Decimal("40"), "inv-2": Decimal("60")}, verified=True)
    rollup = project_finance_rollup(project_value=Decimal("200"), invoice_amounts=[Decimal("100"), Decimal("100")], allocated_amounts=[row["amount"] for row in allocations])
    assert rollup["total_receipts"] == Decimal("100.00") and rollup["project_balance"] == Decimal("100")
    with pytest.raises(CurrentContractControlError):
        allocate_payment_to_invoices(payment_id="pay-2", payment_amount=Decimal("100"), allocations={"inv-1": Decimal("100")}, verified=False)


def test_contract_finance_context_and_sensitive_log_projection_are_canonical_and_safe():
    context = contract_finance_context(contract_id="c-1", project_id="p-1", billing_plan_id="bp-1", invoice_ids=("inv-1",), outstanding=Decimal("50"))
    projection = sensitive_finance_log_projection(event="PAYMENT_VERIFIED", safe_identifiers={"payment_id": "pay-1"})
    assert context["open_finance_workspace"] is True and context["duplicates_finance_workspace"] is False
    assert "iban" in projection["sensitive_fields_omitted"] and "payment_evidence_content" in projection["sensitive_fields_omitted"]
