"""Deterministic Source-18 workflow rules and projections."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..audit.service import audit
from ..models import (
    AuthorityCase,
    ConsultancyOffice,
    Source18EngineerProfile,
    Source18ExternalComment,
    Source18OfficialFormVersion,
    Source18PacketRevision,
    Source18PolicyVersion,
    Source18RosterMembership,
    Source18SubmissionCycle,
    Source18WorkflowTransaction,
)


TRANSACTION_MODES = {
    "ENGINEER_UPDATE": "COUNTER_PROCESS",
    "RESPONSIBLE_ENGINEER_CHANGE": "COMMITTEE_PANEL",
    "OFFICE_RENEWAL": "COMMITTEE_PANEL",
}

ENGINEER_STATES = [
    "SPONSORSHIP_TRANSFER_PENDING",
    "AMEC_SPONSORSHIP_CONFIRMED",
    "ENGINEER_DATA_UPDATE_PREPARING",
    "COUNTER_SUBMITTED",
    "REGULATORY_EMPLOYER_UPDATED",
    "UPDATED_CREDENTIAL_VERIFIED",
    "OFFICE_ROSTER_ADD_PREPARING",
    "ROSTER_ADD_SUBMITTED",
    "REGULATOR_COUNTED",
]
RE_STATES = [
    "CHANGE_PROPOSED",
    "ELIGIBILITY_CHECKED",
    "OWNER_AUTHORIZATION_PREPARED",
    "UNDERTAKING_SIGNED",
    "PACKET_PREPARED",
    "OWNER_INTERNAL_RELEASE_APPROVED",
    "SIGNED_AND_STAMPED",
    "SUBMITTED",
    "PANEL_PENDING",
    "APPROVED",
    "RETURNED",
    "REJECTED",
]
RENEWAL_STATES = [
    "RENEWAL_DUE",
    "EVIDENCE_REFRESH",
    "STAFFING_COMPLIANCE_CHECK",
    "PACKET_PREPARATION",
    "OWNER_DECLARATION",
    "OWNER_INTERNAL_RELEASE_APPROVED",
    "SIGNED_AND_STAMPED",
    "SUBMITTED",
    "PANEL_PENDING",
    "RETURNED",
    "APPROVED",
    "REJECTED",
    "NEW_CERTIFICATE_AND_DOCUMENT_CAPTURED",
    "OLD_ORIGINAL_SUPERSEDED",
]

CAPABILITIES = {
    "OWNER_SPONSOR": {
        "VIEW_REGULATORY_CASE", "EDIT_REGULATORY_CASE", "VIEW_RAW_REGULATORY_PII",
        "EDIT_REGULATORY_PII", "PREPARE_PACKET", "VERIFY_PACKET", "OWNER_INTERNAL_PACKET_RELEASE",
        "CAPTURE_SIGNATURE_EVIDENCE", "CAPTURE_STAMP_EVIDENCE", "AUTHORIZE_EXTERNAL_SUBMISSION",
        "CAPTURE_EXTERNAL_OUTCOME", "MANAGE_RESPONSIBLE_ENGINEER_CHANGE", "MANAGE_OFFICE_RENEWAL",
        "MANAGE_ROSTER_UPDATE", "MANAGE_REGULATORY_POLICY",
    },
    "SYSTEM_ADMIN": {"*"},
    "RESPONSIBLE_ENGINEER": {"VIEW_REGULATORY_CASE", "EDIT_REGULATORY_CASE", "PREPARE_PACKET", "VERIFY_PACKET", "MANAGE_ROSTER_UPDATE"},
    "PERMIT_PREPARER": {"VIEW_REGULATORY_CASE", "EDIT_REGULATORY_CASE", "PREPARE_PACKET", "VERIFY_PACKET"},
    "FINAL_SUBMITTER": {"VIEW_REGULATORY_CASE", "VERIFY_PACKET", "AUTHORIZE_EXTERNAL_SUBMISSION", "CAPTURE_EXTERNAL_OUTCOME"},
    "REQUIREMENT_STEWARD": {"VIEW_REGULATORY_CASE", "MANAGE_REGULATORY_POLICY"},
    "PROCESS_CHAMPION": {"VIEW_REGULATORY_CASE"},
}


def require_capability(role: Any, capability: str) -> None:
    role_name = getattr(role, "value", role)
    if capability not in CAPABILITIES.get(str(role_name), set()) and "*" not in CAPABILITIES.get(str(role_name), set()):
        raise HTTPException(403, {"code": "CAPABILITY_DENIED", "capability": capability})


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hash(payload: Any) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()).hexdigest()


def transaction_states(transaction_type: str) -> list[str]:
    try:
        return {
            "ENGINEER_UPDATE": ENGINEER_STATES,
            "RESPONSIBLE_ENGINEER_CHANGE": RE_STATES,
            "OFFICE_RENEWAL": RENEWAL_STATES,
        }[transaction_type]
    except KeyError as exc:
        raise HTTPException(422, {"code": "SOURCE18_TRANSACTION_TYPE_UNSUPPORTED"}) from exc


def validate_source_currentness(db: Session, transaction: Source18WorkflowTransaction) -> None:
    if transaction.currentness_state != "CURRENT":
        raise HTTPException(409, {"code": "SOURCE18_SOURCE_NOT_CURRENT", "currentness_state": transaction.currentness_state})
    if transaction.official_form_version_id:
        form = db.get(Source18OfficialFormVersion, transaction.official_form_version_id)
        if not form or form.currentness_state != "CURRENT":
            raise HTTPException(409, {"code": "SOURCE18_FORM_VERSION_NOT_CURRENT"})


def enforce_staffing_gate(db: Session, transaction: Source18WorkflowTransaction) -> None:
    if transaction.transaction_type not in {"RESPONSIBLE_ENGINEER_CHANGE", "OFFICE_RENEWAL"}:
        return
    policy = db.get(Source18PolicyVersion, transaction.current_policy_version_id) if transaction.current_policy_version_id else None
    rules = policy.rules_json if policy else {}
    required = int(rules.get("required_count", 0)) if rules.get("required_count") is not None else None
    counted = int(rules.get("regulator_counted", 0)) if rules.get("regulator_counted") is not None else None
    if not policy or policy.status != "CURRENT" or required is None or counted is None:
        raise HTTPException(409, {"code": "STAFFING_POLICY_UNKNOWN_FAIL_CLOSED"})
    if counted < required and not transaction.remediation_exception:
        raise HTTPException(409, {"code": "STAFFING_DEFICIENT_ORDINARY_PANEL_BLOCKED", "required_count": required, "regulator_counted": counted})


def transition(db: Session, transaction: Source18WorkflowTransaction, next_state: str, *, actor: str, correlation_id: str) -> Source18WorkflowTransaction:
    states = transaction_states(transaction.transaction_type)
    if next_state not in states:
        raise HTTPException(422, {"code": "SOURCE18_STATE_UNSUPPORTED", "state": next_state})
    current_index = states.index(transaction.state)
    next_index = states.index(next_state)
    if next_index != current_index + 1:
        allowed = transaction.state == "PANEL_PENDING" and next_state in {"APPROVED", "RETURNED", "REJECTED"}
        if not allowed:
            raise HTTPException(409, {"code": "SOURCE18_INVALID_TRANSITION", "from": transaction.state, "to": next_state})
    if transaction.processing_mode != TRANSACTION_MODES[transaction.transaction_type]:
        raise HTTPException(409, {"code": "SOURCE18_PROCESSING_MODE_MISMATCH"})
    validate_source_currentness(db, transaction)
    enforce_staffing_gate(db, transaction)
    before = {"state": transaction.state}
    transaction.state = next_state
    transaction.last_transition_at = _now()
    audit(db, correlation_id=correlation_id, event_type="SOURCE18_TRANSACTION_TRANSITIONED", entity_type="Source18WorkflowTransaction", entity_id=transaction.id, actor_id=actor, before=before, after={"state": next_state})
    db.commit()
    db.refresh(transaction)
    return transaction


def packet_manifest(transaction: Source18WorkflowTransaction, payload: dict[str, Any]) -> dict[str, Any]:
    authority_only = payload.get("authority_only_values") or {}
    if authority_only:
        raise HTTPException(422, {"code": "AUTHORITY_ONLY_FIELD_WRITE_FORBIDDEN", "fields": sorted(authority_only)})
    if payload.get("blank_authority_fields"):
        raise HTTPException(422, {"code": "EXPLICIT_NOT_APPLICABLE_REQUIRED", "fields": payload["blank_authority_fields"]})
    na_fields = payload.get("not_applicable_fields") or []
    return {
        "authority_case_id": transaction.authority_case_id,
        "transaction_type": transaction.transaction_type,
        "processing_mode": transaction.processing_mode,
        "official_form_version_id": transaction.official_form_version_id,
        "requirement_version_id": transaction.requirement_version_id,
        "source_policy_version_id": transaction.current_policy_version_id,
        "not_applicable_fields": sorted(set(str(value) for value in na_fields)),
        "field_authority": payload.get("field_authority") or {},
    }


def packet_row(packet: Source18PacketRevision) -> dict[str, Any]:
    return {key: value for key, value in packet.__dict__.items() if not key.startswith("_")}


def case_row(case: AuthorityCase) -> dict[str, Any]:
    return {key: value for key, value in case.__dict__.items() if not key.startswith("_")}

