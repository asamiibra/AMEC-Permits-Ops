"""Domain-neutral commercial contract controls shared by billing workflows."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import re


CLIENT_DELAY_THRESHOLD_DAYS = 30
CLIENT_DELAY_THRESHOLD_UNIT = "CALENDAR_DAYS"
CLIENT_DELAY_THRESHOLD_EFFECTIVE_DATE = date(2026, 9, 9)
_INVOICE_REFERENCE_SEGMENT = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")


class CommercialContractControlError(ValueError):
    """A commercial control rejected incomplete or unsafe input."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ClientBlockingDelayEvent:
    """A governed, evidenced delay event; no date is inferred."""

    event_id: str
    project_id: str
    client_delay_started_at: date | None
    delay_reason: str | None
    responsible_external_party: str | None
    affected_service_project: str | None
    supporting_evidence: str | None
    recorded_by: str | None
    recorded_at: date | datetime | None


def compose_amec_invoice_reference(*, issue_year: int, project_reference_segment: str, global_sequence: int, sequence_padding: int = 6) -> str:
    """Compose the AMEC reference without resetting the global sequence."""

    segment = str(project_reference_segment or "").strip().upper()
    if int(issue_year) < 1 or len(str(int(issue_year))) != 4:
        raise CommercialContractControlError("INVOICE_ISSUE_YEAR_INVALID")
    if not _INVOICE_REFERENCE_SEGMENT.fullmatch(segment):
        raise CommercialContractControlError("INVOICE_PROJECT_REFERENCE_SEGMENT_REQUIRED")
    if int(global_sequence) <= 0 or int(sequence_padding) < 1:
        raise CommercialContractControlError("INVOICE_GLOBAL_SEQUENCE_INVALID")
    return f"INV-AMEC-{int(issue_year)}-{segment}-{int(global_sequence):0{int(sequence_padding)}d}"


def evaluate_client_delay_commercial_handover_eligibility(event: ClientBlockingDelayEvent, *, as_of: date, human_authorized: bool = False) -> dict[str, object]:
    """Return an eligibility projection without executing protected actions."""

    if not event.event_id or not event.project_id:
        raise CommercialContractControlError("CLIENT_DELAY_EVENT_IDENTITY_REQUIRED")
    if event.client_delay_started_at is None:
        raise CommercialContractControlError("CLIENT_DELAY_START_DATE_REQUIRED")
    if not event.delay_reason:
        raise CommercialContractControlError("CLIENT_DELAY_REASON_REQUIRED")
    if not event.responsible_external_party:
        raise CommercialContractControlError("CLIENT_DELAY_RESPONSIBLE_EXTERNAL_PARTY_REQUIRED")
    if not event.affected_service_project:
        raise CommercialContractControlError("CLIENT_DELAY_AFFECTED_SERVICE_PROJECT_REQUIRED")
    if not event.supporting_evidence:
        raise CommercialContractControlError("CLIENT_DELAY_EVIDENCE_REQUIRED")
    if not event.recorded_by:
        raise CommercialContractControlError("CLIENT_DELAY_RECORDED_BY_REQUIRED")
    if event.recorded_at is None:
        raise CommercialContractControlError("CLIENT_DELAY_RECORDED_AT_REQUIRED")
    if event.client_delay_started_at > as_of:
        raise CommercialContractControlError("CLIENT_DELAY_START_DATE_IN_FUTURE")

    elapsed_calendar_days = (as_of - event.client_delay_started_at).days
    effective = as_of >= CLIENT_DELAY_THRESHOLD_EFFECTIVE_DATE
    threshold_reached = elapsed_calendar_days >= CLIENT_DELAY_THRESHOLD_DAYS
    eligible = effective and threshold_reached
    return {
        "event_id": event.event_id,
        "project_id": event.project_id,
        "client_delay_started_at": event.client_delay_started_at.isoformat(),
        "delay_reason": event.delay_reason,
        "responsible_external_party": event.responsible_external_party,
        "affected_service_project": event.affected_service_project,
        "supporting_evidence": event.supporting_evidence,
        "recorded_by": event.recorded_by,
        "recorded_at": event.recorded_at.isoformat(),
        "threshold": CLIENT_DELAY_THRESHOLD_DAYS,
        "threshold_unit": CLIENT_DELAY_THRESHOLD_UNIT,
        "threshold_effective_date": CLIENT_DELAY_THRESHOLD_EFFECTIVE_DATE.isoformat(),
        "elapsed_calendar_days": elapsed_calendar_days,
        "threshold_reached": threshold_reached,
        "client_delay_commercial_handover_eligible": eligible,
        "eligible_for_human_authorized_workflow": eligible,
        "human_authorization_required": eligible,
        "human_authorization_present": bool(human_authorized),
        "policy_option": "B",
        "protected_human_action_required": True,
        "ai_autonomous_handover_authority": False,
        "ai_autonomous_invoice_issue_authority": False,
        "allowed_effects": [
            "EXPOSE_OR_ESCALATE_COMMERCIAL_WORK_ITEM",
            "PREPARE_HANDOVER_PACKAGE",
            "ROUTE_INVOICE_FOLLOWUP",
        ] if eligible else [],
        "autonomous_protected_actions_executed": [],
        "invoice_issued": False,
        "handover_letter_issued": False,
        "handover_accepted": False,
        "handover_ready": False,
        "handover_delivered": False,
        "client_receipt": False,
        "service_engagement_or_project_closed": False,
        "contract_closed": False,
        "financial_settlement": False,
    }
