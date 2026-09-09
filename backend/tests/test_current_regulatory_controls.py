"""Executable proofs for the Source16-18 current-contract controls."""

from datetime import date, datetime
from decimal import Decimal

import pytest

from backend.app.services import current_regulatory_controls as controls


def test_unverified_current_policy_and_form_fail_closed():
    entitlement = controls.resolve_regulatory_service_entitlement(
        service_type="COMMITTEE_RENEWAL",
        policy_version_id="policy-1",
        source_reference="source18:T1:R2",
        verified_current=False,
        permitted=True,
    )
    assert entitlement.state == "UNKNOWN"
    with pytest.raises(controls.CurrentRegulatoryControlError, match="VERIFIED_CURRENT_FORM_VERSION_REQUIRED"):
        controls.bind_verified_form_version(
            form_version_id="form-1", form_identity="FORM-X", version="1",
            sha256="a" * 64, policy_source="source18:T1:R3", verified_current=False,
        )


def test_project_required_and_non_project_authority_subject_lanes():
    office = controls.bind_authority_case_subject(subject_type="office", subject_id="office-1")
    engineer = controls.bind_authority_case_subject(subject_type="engineer", subject_id="eng-1")
    assert office.subject_type == "OFFICE" and engineer.subject_type == "ENGINEER"
    with pytest.raises(controls.CurrentRegulatoryControlError, match="CANONICAL_PROJECT_REQUIRED"):
        controls.bind_authority_case_subject(subject_type="PROJECT", subject_id="p-1", project_required=True)
    assert controls.resolve_processing_mode("committee_panel") == "COMMITTEE_PANEL"
    with pytest.raises(controls.CurrentRegulatoryControlError):
        controls.resolve_processing_mode("AUTOMATIC_APPROVAL")


def test_office_engineer_versions_roster_staffing_and_removal_are_distinct():
    office = controls.create_office_registration_version(
        None, registration_id="office-reg", certificate_document_version_id="dv-office",
        certificate_sha256="b" * 64, classification="CONSULTANT",
        disciplines=("CIVIL", "ELECTRICAL"), effective_from=date(2026, 1, 1),
    )
    engineer = controls.create_engineer_credential_version(
        None, engineer_id="eng-1", credential_id="cred-1", registration_number="REG-1",
        discipline="CIVIL", grade="A", employer_party_id="party-1",
        certificate_document_version_id="dv-eng", valid_from=date(2026, 1, 1), valid_to=None,
    )
    membership = controls.add_roster_membership(
        engineer=engineer, regulator_reference="roster-1", status="CONFIRMED",
        effective_from=date(2026, 1, 1),
    )
    staffing = controls.evaluate_staffing(
        requirements=(controls.StaffingRequirement("CIVIL", 1, policy_version_id="policy-1"),),
        memberships=(membership,), as_of=date(2026, 9, 10),
    )
    assert office.version == 1 and engineer.version == 1
    assert staffing["state"] == "COMPLIANT" and staffing["employee_count_used"] is False
    assert controls.evaluate_discipline_removal(
        current_state="ACTIVE", replacement_roster_confirmed=False, remediation_path=False,
    )["allowed"] is False
    assert controls.evaluate_discipline_removal(
        current_state="DEFICIENT", replacement_roster_confirmed=False, remediation_path=True,
    )["allowed"] is True


def test_signer_resolution_packet_revision_field_authority_and_custody():
    binding = controls.bind_verified_form_version(
        form_version_id="form-1", form_identity="FORM-X", version="2",
        sha256="c" * 64, policy_source="source18:T1:R4", verified_current=True,
    )
    designation = controls.ResponsibleEngineerDesignation(
        designation_id="designation-1", engineer_id="eng-1", regulator_reference="reg-1",
        effective_from=date(2026, 1, 1),
    )
    signer = controls.resolve_transaction_signer(
        transaction_type="RENEWAL", responsible_engineer=designation,
        management_signatory_id=None, owner_authorization_id=None, as_of=date(2026, 9, 10),
    )
    assert signer["signer_type"] == "RESPONSIBLE_ENGINEER" and signer["human_only"] is True
    packet = controls.create_committee_packet_revision(
        None, packet_id="packet-1", case_id="case-1", form_binding=binding,
        required_fields={"authority_field": "N/A", "applicant_field": "ok"},
    )
    revised = controls.create_committee_packet_revision(
        packet, packet_id="packet-2", case_id="case-1", form_binding=binding,
        required_fields={"authority_field": "N/A", "applicant_field": "corrected"},
    )
    result = controls.validate_form_field_completion(
        revised.required_fields, required=("authority_field", "applicant_field"),
        authority_only=("authority_field",),
    )
    assert revised.revision == 2 and revised.supersedes_packet_id == "packet-1"
    assert result["valid"] is True and result["explicit_na_accepted"] == ["authority_field"]
    events = (
        controls.PhysicalOriginalCustodyEvent("doc-1", "RECEIVED_ORIGINAL", "amec", datetime(2026, 1, 1), "ev-1"),
        controls.PhysicalOriginalCustodyEvent("doc-2", "RECEIVED_ORIGINAL", "amec", datetime(2026, 1, 2), "ev-2"),
    )
    assert controls.validate_single_active_original(events)["valid"] is False
    assert controls.link_independent_case_outcomes(
        case_ids=("case-1", "case-2"), outcomes={"case-1": "APPROVED", "case-2": "PENDING"},
    )["merged_outcome"] is False


def test_billing_refinements_preserve_state_separation_and_evidence_boundaries():
    request = controls.BillingRequest(
        request_id="req-1", project_id="p-1", milestone_id="m-2", requested_amount=Decimal("100"),
        trigger_evidence_ref="ev-m2", requested_by="operator-1",
    )
    verified = controls.verify_billing_request(
        request=request,
        contract_milestones={"m-1": {"amount": "50", "satisfied": True}, "m-2": {"amount": "100", "predecessors": ("m-1",)}},
        prior_milestones=("m-1",),
    )
    assert verified["verified"] is True and verified["prior_collection_does_not_block"] is True
    assert controls.compare_collection_schedule(
        controls.CollectionSchedule(date(2026, 9, 1), date(2026, 9, 5), date(2026, 9, 8))
    )["dates_are_distinct"] is True
    assert controls.build_same_project_next_invoice_context(
        project_id="p-1", previous_invoice_project_id="p-1", previous_invoice_id="inv-1", next_project_sequence=2,
    )["unrelated_project_copy"] is False
    assert controls.required_channel_evidence("WHATSAPP") == "ACKNOWLEDGMENT_OR_RESPONSE_SCREENSHOT"
    assert controls.required_payment_evidence("CHEQUE") == "CHEQUE_IMAGE_AND_AMEC_RECEIPT"
    reversed_payment = controls.reverse_payment_allocation(
        allocation_id="alloc-1", allocated_amount=Decimal("10"), dependent_effects={"invoice": Decimal("10")},
        reason="duplicate allocation", authorized_by="finance-1", evidence_ref="ev-reversal",
    )
    assert reversed_payment["history_preserved"] is True
    non_cash = controls.resolve_non_cash_receivable(
        invoice_id="inv-1", resolution="WRITTEN_OFF", amount=Decimal("10"), reason="approved exception",
        approved_by="finance-1", effective_date=date(2026, 9, 10), evidence_ref="ev-writeoff",
    )
    assert non_cash["paid"] is False and non_cash["original_invoice_preserved"] is True
    closure = controls.billing_closure_state(
        financially_resolved=True, delivery_evidence_complete=True, collection_evidence_complete=False,
        project_complete=True,
    )
    assert closure["billing_complete"] is False and closure["project_complete"] is True


def test_source18_controls_do_not_hardcode_historical_numeric_policy():
    text = controls.__file__
    source = open(text, encoding="utf-8").read()
    assert "F-ECOC-08" not in source
    assert "Issue 01" not in source
    assert "2/2016" not in source
