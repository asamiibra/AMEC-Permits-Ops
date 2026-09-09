"""Canonical, fail-closed controls for the Source16-18 contract refinements.

These are deterministic policy projections over the existing Project, Party,
DocumentVersion, AuthorityCase, Billing and Audit domains.  They deliberately
do not create a second regulatory repository, HR module, checklist store or
external integration.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Mapping


class CurrentRegulatoryControlError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class RegulatoryServiceEntitlement:
    service_type: str
    state: str
    policy_version_id: str | None
    source_reference: str | None
    reason: str


def resolve_regulatory_service_entitlement(*, service_type: str, policy_version_id: str | None, source_reference: str | None, verified_current: bool, permitted: bool | None) -> RegulatoryServiceEntitlement:
    """Return UNKNOWN and block the action when current policy is unverified."""

    if not verified_current or not policy_version_id or not source_reference:
        return RegulatoryServiceEntitlement(service_type, "UNKNOWN", policy_version_id, source_reference, "CURRENT_POLICY_OR_SOURCE_NOT_VERIFIED")
    if permitted is None:
        return RegulatoryServiceEntitlement(service_type, "UNKNOWN", policy_version_id, source_reference, "SERVICE_APPLICABILITY_UNRESOLVED")
    return RegulatoryServiceEntitlement(service_type, "ALLOWED" if permitted else "NOT_ENTITLED", policy_version_id, source_reference, "VERIFIED_CURRENT_POLICY")


@dataclass(frozen=True)
class VerifiedFormVersionBinding:
    form_version_id: str
    form_identity: str
    version: str
    sha256: str
    policy_source: str


def bind_verified_form_version(*, form_version_id: str, form_identity: str, version: str, sha256: str, policy_source: str, verified_current: bool) -> VerifiedFormVersionBinding:
    if not all(str(value or "").strip() for value in (form_version_id, form_identity, version, sha256, policy_source)) or not verified_current:
        raise CurrentRegulatoryControlError("VERIFIED_CURRENT_FORM_VERSION_REQUIRED")
    return VerifiedFormVersionBinding(form_version_id, form_identity, version, sha256, policy_source)


SUPPORTED_CASE_SUBJECT_TYPES = frozenset({"PROJECT", "PROPERTY", "OFFICE", "ENGINEER"})


@dataclass(frozen=True)
class AuthorityCaseSubjectBinding:
    subject_type: str
    subject_id: str
    project_id: str | None
    project_required: bool


def bind_authority_case_subject(*, subject_type: str, subject_id: str, project_id: str | None = None, project_required: bool = False) -> AuthorityCaseSubjectBinding:
    kind = str(subject_type or "").upper()
    if kind not in SUPPORTED_CASE_SUBJECT_TYPES or not str(subject_id or "").strip():
        raise CurrentRegulatoryControlError("CANONICAL_AUTHORITY_CASE_SUBJECT_REQUIRED")
    if project_required and not project_id:
        raise CurrentRegulatoryControlError("CANONICAL_PROJECT_REQUIRED_FOR_AUTHORITY_CASE")
    return AuthorityCaseSubjectBinding(kind, str(subject_id), project_id, project_required)


def resolve_processing_mode(mode: str) -> str:
    value = str(mode or "").upper()
    if value not in {"COUNTER_PROCESS", "COMMITTEE_PANEL"}:
        raise CurrentRegulatoryControlError("PROCESSING_MODE_REQUIRED")
    return value


@dataclass(frozen=True)
class OfficeRegistrationVersion:
    registration_id: str
    version: int
    certificate_document_version_id: str
    certificate_sha256: str
    classification: str
    disciplines: tuple[str, ...]
    effective_from: date
    effective_to: date | None = None


def create_office_registration_version(previous: OfficeRegistrationVersion | None, *, registration_id: str, certificate_document_version_id: str, certificate_sha256: str, classification: str, disciplines: Iterable[str], effective_from: date) -> OfficeRegistrationVersion:
    if not registration_id or not certificate_document_version_id or not certificate_sha256 or not classification:
        raise CurrentRegulatoryControlError("OFFICE_REGISTRATION_VERSION_FIELDS_REQUIRED")
    normalized_disciplines = tuple(sorted({str(item).strip().upper() for item in disciplines if str(item).strip()}))
    if not normalized_disciplines:
        raise CurrentRegulatoryControlError("OFFICE_REGULATORY_DISCIPLINE_REQUIRED")
    return OfficeRegistrationVersion(registration_id, (previous.version + 1) if previous else 1, certificate_document_version_id, certificate_sha256, classification, normalized_disciplines, effective_from, None)


@dataclass(frozen=True)
class EngineerCredentialVersion:
    engineer_id: str
    credential_id: str
    version: int
    registration_number: str
    discipline: str
    grade: str
    employer_party_id: str
    certificate_document_version_id: str
    valid_from: date
    valid_to: date | None


def create_engineer_credential_version(previous: EngineerCredentialVersion | None, *, engineer_id: str, credential_id: str, registration_number: str, discipline: str, grade: str, employer_party_id: str, certificate_document_version_id: str, valid_from: date, valid_to: date | None) -> EngineerCredentialVersion:
    fields = (engineer_id, credential_id, registration_number, discipline, grade, employer_party_id, certificate_document_version_id)
    if not all(str(value or "").strip() for value in fields):
        raise CurrentRegulatoryControlError("ENGINEER_CREDENTIAL_VERSION_FIELDS_REQUIRED")
    if valid_to and valid_to < valid_from:
        raise CurrentRegulatoryControlError("ENGINEER_CREDENTIAL_VALIDITY_RANGE_INVALID")
    return EngineerCredentialVersion(engineer_id, credential_id, (previous.version + 1) if previous else 1, registration_number, discipline.upper(), grade, employer_party_id, certificate_document_version_id, valid_from, valid_to)


@dataclass(frozen=True)
class RegulatorRosterMembership:
    engineer_id: str
    discipline: str
    credential_version: int
    regulator_reference: str
    status: str
    effective_from: date
    effective_to: date | None = None


def add_roster_membership(*, engineer: EngineerCredentialVersion, regulator_reference: str, status: str, effective_from: date) -> RegulatorRosterMembership:
    if status.upper() not in {"CONFIRMED", "PENDING", "REMOVED"} or not regulator_reference:
        raise CurrentRegulatoryControlError("REGULATOR_ROSTER_STATUS_AND_REFERENCE_REQUIRED")
    return RegulatorRosterMembership(engineer.engineer_id, engineer.discipline, engineer.version, regulator_reference, status.upper(), effective_from)


@dataclass(frozen=True)
class StaffingRequirement:
    discipline: str
    required_count: int
    required_grade: str | None = None
    policy_version_id: str | None = None


def evaluate_staffing(*, requirements: Iterable[StaffingRequirement], memberships: Iterable[RegulatorRosterMembership], as_of: date) -> dict[str, Any]:
    active = [item for item in memberships if item.status == "CONFIRMED" and item.effective_from <= as_of and (item.effective_to is None or item.effective_to >= as_of)]
    by_discipline: dict[str, int] = {}
    for item in active:
        by_discipline[item.discipline] = by_discipline.get(item.discipline, 0) + 1
    rows = []
    for requirement in requirements:
        actual = by_discipline.get(requirement.discipline.upper(), 0)
        rows.append({"discipline": requirement.discipline.upper(), "required": requirement.required_count, "regulator_counted": actual, "surplus_or_shortage": actual - requirement.required_count, "state": "BUFFERED" if actual > requirement.required_count else "AT_MINIMUM" if actual == requirement.required_count else "DEFICIENT", "policy_version_id": requirement.policy_version_id})
    return {"state": "COMPLIANT" if all(row["state"] != "DEFICIENT" for row in rows) else "DEFICIENT", "disciplines": rows, "employee_count_used": False}


def evaluate_discipline_removal(*, current_state: str, replacement_roster_confirmed: bool, remediation_path: bool = False) -> dict[str, Any]:
    state = str(current_state or "").upper()
    if state not in {"ACTIVE", "DEFICIENT", "REMOVED"}:
        raise CurrentRegulatoryControlError("DISCIPLINE_STATE_REQUIRED")
    if state == "REMOVED" and not remediation_path:
        return {"allowed": False, "state": "REMOVED", "reason": "ELIGIBLE_REGISTRATION_EVENT_REQUIRED"}
    return {"allowed": bool(replacement_roster_confirmed or remediation_path), "state": state, "reason": "CONFIRMED_REPLACEMENT_OR_REMEDIATION" if replacement_roster_confirmed or remediation_path else "CONFIRMED_ROSTER_OR_REMEDIATION_REQUIRED"}


@dataclass(frozen=True)
class ResponsibleEngineerDesignation:
    designation_id: str
    engineer_id: str
    regulator_reference: str
    effective_from: date
    effective_to: date | None = None
    status: str = "ACTIVE"


def resolve_transaction_signer(*, transaction_type: str, responsible_engineer: ResponsibleEngineerDesignation | None, management_signatory_id: str | None, owner_authorization_id: str | None, as_of: date) -> dict[str, Any]:
    if responsible_engineer and responsible_engineer.status == "ACTIVE" and responsible_engineer.effective_from <= as_of and (responsible_engineer.effective_to is None or responsible_engineer.effective_to >= as_of):
        return {"signer_type": "RESPONSIBLE_ENGINEER", "signer_id": responsible_engineer.engineer_id, "authority_reference": responsible_engineer.regulator_reference, "human_only": True}
    if management_signatory_id and owner_authorization_id:
        return {"signer_type": "MANAGEMENT_AUTHORIZED_SIGNATORY", "signer_id": management_signatory_id, "authority_reference": owner_authorization_id, "human_only": True}
    return {"signer_type": "UNRESOLVED", "signer_id": None, "authority_reference": None, "human_only": True, "blocked": True}


@dataclass(frozen=True)
class CommitteePacketRevision:
    packet_id: str
    revision: int
    case_id: str
    form_binding: VerifiedFormVersionBinding
    required_fields: Mapping[str, Any]
    signature_evidence_id: str | None = None
    submitted_at: datetime | None = None
    supersedes_packet_id: str | None = None
    status: str = "DRAFT"


def create_committee_packet_revision(previous: CommitteePacketRevision | None, *, packet_id: str, case_id: str, form_binding: VerifiedFormVersionBinding, required_fields: Mapping[str, Any]) -> CommitteePacketRevision:
    if not packet_id or not case_id or not required_fields:
        raise CurrentRegulatoryControlError("COMMITTEE_PACKET_FIELDS_REQUIRED")
    return CommitteePacketRevision(packet_id, (previous.revision + 1) if previous else 1, case_id, form_binding, dict(required_fields), supersedes_packet_id=previous.packet_id if previous else None)


def validate_form_field_completion(fields: Mapping[str, Any], *, required: Iterable[str], authority_only: Iterable[str] = ()) -> dict[str, Any]:
    required_keys = {str(key) for key in required}
    missing = sorted(key for key in required_keys if key not in fields or fields[key] in (None, ""))
    authority_edits = sorted(key for key in authority_only if key in fields and fields[key] not in (None, "", "N/A", "NA", "—", "-"))
    return {"valid": not missing and not authority_edits, "missing": missing, "authority_only_edits": authority_edits, "explicit_na_accepted": [key for key in required_keys if fields.get(key) in {"N/A", "NA", "—", "-"}]}


@dataclass(frozen=True)
class PhysicalOriginalCustodyEvent:
    document_version_id: str
    event_type: str
    custodian: str
    event_at: datetime
    evidence_ref: str


def validate_single_active_original(events: Iterable[PhysicalOriginalCustodyEvent]) -> dict[str, Any]:
    active = [event for event in events if event.event_type in {"RECEIVED_ORIGINAL", "HELD_ORIGINAL"}]
    surrendered = {event.document_version_id for event in events if event.event_type in {"SURRENDERED_ORIGINAL", "RETURNED_ORIGINAL", "REPLACED_ORIGINAL"}}
    current = [event for event in active if event.document_version_id not in surrendered]
    return {"valid": len(current) <= 1, "active_original_document_version_id": current[0].document_version_id if len(current) == 1 else None, "active_original_count": len(current)}


def link_independent_case_outcomes(*, case_ids: Iterable[str], outcomes: Mapping[str, str]) -> dict[str, Any]:
    ids = tuple(case_ids)
    if not ids or len(set(ids)) != len(ids) or set(outcomes) != set(ids):
        raise CurrentRegulatoryControlError("LINKED_CASE_OUTCOMES_MUST_REMAIN_INDEPENDENT")
    return {"linked": True, "case_ids": ids, "outcomes": dict(outcomes), "merged_outcome": False}


@dataclass(frozen=True)
class BillingRequest:
    request_id: str
    project_id: str
    milestone_id: str
    requested_amount: Decimal
    trigger_evidence_ref: str
    requested_by: str


def verify_billing_request(*, request: BillingRequest, contract_milestones: Mapping[str, Mapping[str, Any]], prior_milestones: Iterable[str], explicit_exception: str | None = None) -> dict[str, Any]:
    milestone = contract_milestones.get(request.milestone_id)
    if not milestone:
        return {"verified": False, "code": "BILLING_MILESTONE_NOT_IN_CONTRACT"}
    expected = Decimal(str(milestone.get("amount", "0")))
    prior = set(prior_milestones)
    sequence_ok = all(bool(contract_milestones[item].get("satisfied")) for item in milestone.get("predecessors", ()) if item in contract_milestones)
    if not sequence_ok and not explicit_exception:
        return {"verified": False, "code": "BILLING_MILESTONE_SEQUENCE_REQUIRES_GOVERNED_EXCEPTION"}
    return {"verified": request.requested_amount == expected and bool(request.trigger_evidence_ref) and bool(request.requested_by), "milestone_id": request.milestone_id, "sequence_checked": True, "prior_collection_does_not_block": True, "explicit_exception": explicit_exception}


@dataclass(frozen=True)
class CollectionSchedule:
    planned_collection_date: date | None
    invoice_due_date: date | None
    actual_collection_date: date | None


def compare_collection_schedule(schedule: CollectionSchedule) -> dict[str, Any]:
    return {"forecast": schedule.planned_collection_date.isoformat() if schedule.planned_collection_date else None, "due": schedule.invoice_due_date.isoformat() if schedule.invoice_due_date else None, "actual": schedule.actual_collection_date.isoformat() if schedule.actual_collection_date else None, "dates_are_distinct": True}


CHANNEL_EVIDENCE = {"EMAIL": "SENT_EMAIL_PROOF", "WHATSAPP": "ACKNOWLEDGMENT_OR_RESPONSE_SCREENSHOT", "MESSENGER": "SIGNED_OR_RECEIVED_INVOICE_PROOF", "IN_PERSON": "SIGNED_OR_RECEIVED_INVOICE_PROOF", "COURIER": "DELIVERY_RECEIPT"}
PAYMENT_EVIDENCE = {"BANK_TRANSFER": "TRANSFER_PROOF", "CHEQUE": "CHEQUE_IMAGE_AND_AMEC_RECEIPT", "ALTERNATE_CUSTODIAN": "SIGNED_RECEIPT_OR_TRANSFER_CONFIRMATION"}


def required_channel_evidence(channel: str) -> str:
    try:
        return CHANNEL_EVIDENCE[str(channel).upper()]
    except KeyError as exc:
        raise CurrentRegulatoryControlError("DELIVERY_CHANNEL_EVIDENCE_POLICY_REQUIRED") from exc


def required_payment_evidence(payment_method: str) -> str:
    try:
        return PAYMENT_EVIDENCE[str(payment_method).upper()]
    except KeyError as exc:
        raise CurrentRegulatoryControlError("PAYMENT_METHOD_EVIDENCE_POLICY_REQUIRED") from exc


def reverse_payment_allocation(*, allocation_id: str, allocated_amount: Decimal, dependent_effects: Mapping[str, Decimal], reason: str, authorized_by: str, evidence_ref: str) -> dict[str, Any]:
    if not all(str(value or "").strip() for value in (allocation_id, reason, authorized_by, evidence_ref)) or Decimal(allocated_amount) <= 0:
        raise CurrentRegulatoryControlError("GOVERNED_PAYMENT_REVERSAL_EVIDENCE_REQUIRED")
    return {"allocation_id": allocation_id, "status": "REVERSED", "reversed_amount": Decimal(allocated_amount), "dependent_effects_reversed": {key: -Decimal(value) for key, value in dependent_effects.items()}, "history_preserved": True, "authorized_by": authorized_by, "reason": reason, "evidence_ref": evidence_ref}


def resolve_non_cash_receivable(*, invoice_id: str, resolution: str, amount: Decimal, reason: str, approved_by: str, effective_date: date, evidence_ref: str) -> dict[str, Any]:
    if resolution.upper() not in {"WAIVED", "WRITTEN_OFF", "NON_COLLECTIBLE", "COMMERCIAL_RELEASE"}:
        raise CurrentRegulatoryControlError("NON_CASH_RECEIVABLE_RESOLUTION_INVALID")
    if not invoice_id or Decimal(amount) <= 0 or not reason or not approved_by or not evidence_ref:
        raise CurrentRegulatoryControlError("NON_CASH_RECEIVABLE_HUMAN_EVIDENCE_REQUIRED")
    return {"invoice_id": invoice_id, "resolution": resolution.upper(), "amount": Decimal(amount), "paid": False, "original_invoice_preserved": True, "original_outstanding_preserved": True, "approved_by": approved_by, "effective_date": effective_date.isoformat(), "reason": reason, "evidence_ref": evidence_ref}


def billing_closure_state(*, financially_resolved: bool, delivery_evidence_complete: bool, collection_evidence_complete: bool, project_complete: bool) -> dict[str, Any]:
    return {"billing_complete": bool(financially_resolved and delivery_evidence_complete and collection_evidence_complete), "financially_resolved": bool(financially_resolved), "delivery_evidence_complete": bool(delivery_evidence_complete), "collection_evidence_complete": bool(collection_evidence_complete), "project_complete": bool(project_complete), "project_completion_is_separate": True}


def build_same_project_next_invoice_context(*, project_id: str, previous_invoice_project_id: str, previous_invoice_id: str, next_project_sequence: int) -> dict[str, Any]:
    if not project_id or not previous_invoice_id or project_id != previous_invoice_project_id or next_project_sequence < 1:
        raise CurrentRegulatoryControlError("SAME_PROJECT_PREVIOUS_INVOICE_REQUIRED")
    return {"project_id": project_id, "previous_invoice_id": previous_invoice_id, "project_sequence": next_project_sequence, "unrelated_project_copy": False}


def pii_access_projection(*, purpose: str, capability: str, least_necessary: bool, synthetic_only: bool) -> dict[str, Any]:
    return {"purpose": purpose, "capability": capability, "least_necessary": bool(least_necessary), "synthetic_only": bool(synthetic_only), "raw_pii_exposed": False}
