"""Fail-closed controls for the current Source14 contract decisions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import re


CLIENT_DELAY_THRESHOLD_DAYS = 30
CLIENT_DELAY_THRESHOLD_UNIT = "CALENDAR_DAYS"
CLIENT_DELAY_THRESHOLD_EFFECTIVE_DATE = date(2026, 9, 9)
_INVOICE_REFERENCE_SEGMENT = re.compile(r"^[A-Z0-9][A-Z0-9_-]*$")


class Source14ControlError(ValueError):
    """A current-contract control rejected incomplete or unsafe input."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ClientBlockingDelayEvent:
    """A governed, evidenced delay event; no date is inferred by this model."""

    event_id: str
    project_id: str
    blocked_since: date | None
    evidence_ref: str | None
    responsibility_attributed: bool
    follow_up_recorded: bool


def compose_amec_invoice_reference(*, issue_year: int, project_reference_segment: str, global_sequence: int, sequence_padding: int = 6) -> str:
    """Compose the current standard reference without resetting the sequence."""

    segment = str(project_reference_segment or "").strip().upper()
    if int(issue_year) < 1 or len(str(int(issue_year))) != 4:
        raise Source14ControlError("INVOICE_ISSUE_YEAR_INVALID")
    if not _INVOICE_REFERENCE_SEGMENT.fullmatch(segment):
        raise Source14ControlError("INVOICE_PROJECT_REFERENCE_SEGMENT_REQUIRED")
    if int(global_sequence) <= 0 or int(sequence_padding) < 1:
        raise Source14ControlError("INVOICE_GLOBAL_SEQUENCE_INVALID")
    return f"INV-AMEC-{int(issue_year)}-{segment}-{int(global_sequence):0{int(sequence_padding)}d}"


def evaluate_client_delay_commercial_handover_eligibility(
    event: ClientBlockingDelayEvent,
    *,
    as_of: date,
    human_authorized: bool = False,
) -> dict[str, object]:
    """Evaluate eligibility while preserving the human-action boundary.

    The result is a read-only decision projection. It never issues an invoice,
    creates or accepts a handover, closes a project, or executes another
    protected action. A missing ``blocked_since`` is rejected rather than
    inferred from a message, follow-up, or unrelated project date.
    """

    if not event.event_id or not event.project_id:
        raise Source14ControlError("CLIENT_DELAY_EVENT_IDENTITY_REQUIRED")
    if event.blocked_since is None:
        raise Source14ControlError("CLIENT_DELAY_START_DATE_REQUIRED")
    if not event.evidence_ref:
        raise Source14ControlError("CLIENT_DELAY_EVIDENCE_REQUIRED")
    if not event.responsibility_attributed:
        raise Source14ControlError("CLIENT_DELAY_RESPONSIBILITY_ATTRIBUTION_REQUIRED")
    if not event.follow_up_recorded:
        raise Source14ControlError("CLIENT_DELAY_FOLLOW_UP_REQUIRED")
    if event.blocked_since > as_of:
        raise Source14ControlError("CLIENT_DELAY_START_DATE_IN_FUTURE")

    elapsed_calendar_days = (as_of - event.blocked_since).days
    effective = as_of >= CLIENT_DELAY_THRESHOLD_EFFECTIVE_DATE
    threshold_reached = elapsed_calendar_days >= CLIENT_DELAY_THRESHOLD_DAYS
    eligible = effective and threshold_reached
    return {
        "event_id": event.event_id,
        "project_id": event.project_id,
        "blocked_since": event.blocked_since.isoformat(),
        "evidence_ref": event.evidence_ref,
        "responsibility_attributed": event.responsibility_attributed,
        "follow_up_recorded": event.follow_up_recorded,
        "threshold": CLIENT_DELAY_THRESHOLD_DAYS,
        "threshold_unit": CLIENT_DELAY_THRESHOLD_UNIT,
        "threshold_effective_date": CLIENT_DELAY_THRESHOLD_EFFECTIVE_DATE.isoformat(),
        "elapsed_calendar_days": elapsed_calendar_days,
        "threshold_reached": threshold_reached,
        "eligible_for_human_authorized_workflow": eligible,
        "human_authorization_required": eligible,
        "human_authorization_present": bool(human_authorized),
        "allowed_effects": [
            "EXPOSE_OR_ESCALATE_COMMERCIAL_WORK_ITEM",
            "PREPARE_HANDOVER_PACKAGE",
            "ROUTE_INVOICE_FOLLOWUP",
        ] if eligible else [],
        "autonomous_protected_actions_executed": [],
        "invoice_issued": False,
        "handover_letter_issued": False,
        "handover_accepted": False,
        "service_engagement_or_project_closed": False,
    }
