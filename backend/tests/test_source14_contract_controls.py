"""Source14 current-contract decision controls."""

from datetime import date

import pytest

from backend.app.services.commercial_contract_controls import (
    ClientBlockingDelayEvent,
    CommercialContractControlError,
    compose_amec_invoice_reference,
    evaluate_client_delay_commercial_handover_eligibility,
)


def _event(**overrides):
    values = {
        "event_id": "delay-1",
        "project_id": "project-1",
        "blocked_since": date(2026, 8, 10),
        "evidence_ref": "synthetic://delay-evidence-1",
        "responsibility_attributed": True,
        "follow_up_recorded": True,
    }
    values.update(overrides)
    return ClientBlockingDelayEvent(**values)


def test_30_calendar_days_only_exposes_human_authorized_eligibility():
    result = evaluate_client_delay_commercial_handover_eligibility(_event(), as_of=date(2026, 9, 9))
    assert result["elapsed_calendar_days"] == 30
    assert result["eligible_for_human_authorized_workflow"] is True
    assert result["human_authorization_required"] is True
    assert result["invoice_issued"] is False
    assert result["handover_letter_issued"] is False
    assert result["handover_accepted"] is False
    assert result["service_engagement_or_project_closed"] is False


def test_29_calendar_days_is_not_eligible():
    result = evaluate_client_delay_commercial_handover_eligibility(_event(), as_of=date(2026, 9, 8))
    assert result["elapsed_calendar_days"] == 29
    assert result["eligible_for_human_authorized_workflow"] is False
    assert result["allowed_effects"] == []


@pytest.mark.parametrize(
    "field,code",
    [
        ("blocked_since", "CLIENT_DELAY_START_DATE_REQUIRED"),
        ("evidence_ref", "CLIENT_DELAY_EVIDENCE_REQUIRED"),
        ("responsibility_attributed", "CLIENT_DELAY_RESPONSIBILITY_ATTRIBUTION_REQUIRED"),
        ("follow_up_recorded", "CLIENT_DELAY_FOLLOW_UP_REQUIRED"),
    ],
)
def test_delay_event_requirements_fail_closed(field, code):
    with pytest.raises(CommercialContractControlError) as exc:
        evaluate_client_delay_commercial_handover_eligibility(_event(**{field: None if field in {"blocked_since", "evidence_ref"} else False}), as_of=date(2026, 9, 9))
    assert exc.value.code == code


def test_human_authorization_is_recorded_but_does_not_execute_protected_actions():
    result = evaluate_client_delay_commercial_handover_eligibility(_event(), as_of=date(2026, 9, 9), human_authorized=True)
    assert result["human_authorization_present"] is True
    assert result["autonomous_protected_actions_executed"] == []
    assert result["invoice_issued"] is False
    assert result["handover_accepted"] is False


def test_invoice_reference_preserves_commercial_segment_and_global_sequence():
    assert compose_amec_invoice_reference(issue_year=2026, project_reference_segment="P457", global_sequence=394) == "INV-AMEC-2026-P457-000394"


def test_invoice_reference_rejects_missing_or_unsafe_commercial_segment():
    with pytest.raises(CommercialContractControlError) as exc:
        compose_amec_invoice_reference(issue_year=2026, project_reference_segment="", global_sequence=1)
    assert exc.value.code == "INVOICE_PROJECT_REFERENCE_SEGMENT_REQUIRED"
    with pytest.raises(CommercialContractControlError) as exc:
        compose_amec_invoice_reference(issue_year=2026, project_reference_segment="P/457", global_sequence=1)
    assert exc.value.code == "INVOICE_PROJECT_REFERENCE_SEGMENT_REQUIRED"
