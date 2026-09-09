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
from .backend_realignment import CAPABILITY_MATRIX as CANONICAL_CAPABILITY_MATRIX
from .backend_realignment import persona_for_role
from .backend_realignment import require_capability as canonical_require_capability
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
    RequirementPolicyVersion,
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
    role: set(CANONICAL_CAPABILITY_MATRIX.get(persona_for_role(role), set()))
    for role in {
        "OWNER_SPONSOR", "SYSTEM_ADMIN", "RESPONSIBLE_ENGINEER", "PERMIT_PREPARER",
        "FINAL_SUBMITTER", "REQUIREMENT_STEWARD", "PROCESS_CHAMPION",
    }
}


def require_capability(role: Any, capability: str) -> None:
    try:
        canonical_require_capability(role, capability)
    except HTTPException as exc:
        if isinstance(exc.detail, dict):
            exc.detail = {"code": "CAPABILITY_DENIED", **exc.detail}
        raise


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
    if transaction.current_policy_version_id:
        policy = db.get(Source18PolicyVersion, transaction.current_policy_version_id)
        if not policy or policy.status != "CURRENT":
            raise HTTPException(409, {"code": "SOURCE18_POLICY_VERSION_NOT_CURRENT"})
    if transaction.official_form_version_id:
        form = db.get(Source18OfficialFormVersion, transaction.official_form_version_id)
        if not form or form.currentness_state != "CURRENT":
            raise HTTPException(409, {"code": "SOURCE18_FORM_VERSION_NOT_CURRENT"})


def staffing_readiness(db: Session, office_id: str, *, at: datetime | None = None) -> dict[str, Any]:
    """Derive live staffing from effective roster state, never policy counters."""
    assessment_time = at or _now()
    policy = db.scalar(select(Source18PolicyVersion).where(
        Source18PolicyVersion.policy_code == "OFFICE_STAFFING",
        Source18PolicyVersion.status == "CURRENT",
    ).order_by(Source18PolicyVersion.created_at.desc()))
    rules = policy.rules_json if policy else {}
    required = rules.get("required_count") if policy else None
    eligible_disciplines = {str(value).upper() for value in (rules.get("eligible_disciplines") or [])}
    eligible_categories = {str(value).upper() for value in (rules.get("eligible_categories") or [])}
    if not policy or required is None or not policy.source_reference:
        raise HTTPException(409, {"code": "STAFFING_POLICY_UNKNOWN_FAIL_CLOSED"})

    memberships = db.scalars(select(Source18RosterMembership).where(Source18RosterMembership.office_id == office_id)).all()
    profiles = {item.id: item for item in db.scalars(select(Source18EngineerProfile).where(Source18EngineerProfile.office_id == office_id)).all()}
    counted: list[dict[str, Any]] = []
    at_risk: list[dict[str, Any]] = []
    expired: list[dict[str, Any]] = []
    pending_additions: list[str] = []
    for membership in memberships:
        profile = profiles.get(membership.engineer_profile_id)
        if membership.status.upper() in {"PENDING", "PENDING_ADD", "ROSTER_ADD_PENDING"}:
            pending_additions.append(membership.engineer_profile_id)
            continue
        if membership.status.upper() != "ACTIVE" or not profile:
            continue
        reasons: list[str] = []
        if membership.valid_from and membership.valid_from > assessment_time.date():
            reasons.append("NOT_YET_EFFECTIVE")
        if membership.valid_until and membership.valid_until < assessment_time.date():
            reasons.append("MEMBERSHIP_EXPIRED")
            expired.append({"engineer_id": profile.id, "reason": "MEMBERSHIP_EXPIRED"})
        if profile.evidence_currentness.upper() != "CURRENT":
            reasons.append("EVIDENCE_NOT_CURRENT")
        if profile.regulatory_profile_state.upper() == "UPDATED_CREDENTIAL_VERIFIED":
            reasons.append("CREDENTIAL_VERIFIED_NOT_REGULATOR_COUNTED")
        if membership.regulator_counted_state.upper() not in {"COUNTED", "CURRENT", "YES"}:
            reasons.append("ROSTER_NOT_REGULATOR_COUNTED")
        if not membership.classified_engineer:
            reasons.append("NOT_CLASSIFIED_ENGINEER")
        if eligible_disciplines and membership.discipline.upper() not in eligible_disciplines:
            reasons.append("DISCIPLINE_NOT_ELIGIBLE")
        if eligible_categories and (profile.grade_category or "").upper() not in eligible_categories:
            reasons.append("CATEGORY_NOT_ELIGIBLE")
        if reasons:
            at_risk.append({"engineer_id": profile.id, "reasons": reasons})
        else:
            counted.append({"engineer_id": profile.id, "discipline": membership.discipline})
    regulator_counted = len(counted)
    required_count = int(required)
    return {
        "required_count": required_count,
        "regulator_counted": regulator_counted,
        "buffer_or_gap": regulator_counted - required_count,
        "at_risk_engineers": at_risk,
        "expired_or_expiring_engineers": expired,
        "pending_replacements": [item["engineer_id"] for item in at_risk if "MEMBERSHIP_EXPIRED" in item["reasons"]],
        "pending_roster_additions": pending_additions,
        "current_regulatory_entitlement": regulator_counted,
        "source_policy_version": policy.version,
        "assessment_time": assessment_time.isoformat(),
        "currentness": "CURRENT",
    }


def enforce_staffing_gate(db: Session, transaction: Source18WorkflowTransaction) -> None:
    if transaction.transaction_type not in {"RESPONSIBLE_ENGINEER_CHANGE", "OFFICE_RENEWAL"}:
        return
    readiness = staffing_readiness(db, transaction.office_id)
    if readiness["regulator_counted"] < readiness["required_count"] and not transaction.remediation_exception:
        raise HTTPException(409, {"code": "STAFFING_DEFICIENT_ORDINARY_PANEL_BLOCKED", "required_count": readiness["required_count"], "regulator_counted": readiness["regulator_counted"]})


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


def packet_hash_payload(packet: Source18PacketRevision) -> dict[str, Any]:
    return {"manifest": packet.manifest_json, "required_signers": packet.required_signers_json}


def refresh_packet_hash(packet: Source18PacketRevision) -> str:
    packet.packet_hash = _hash(packet_hash_payload(packet))
    return packet.packet_hash


def packet_row(packet: Source18PacketRevision) -> dict[str, Any]:
    return {key: value for key, value in packet.__dict__.items() if not key.startswith("_")}


def case_row(case: AuthorityCase) -> dict[str, Any]:
    return {key: value for key, value in case.__dict__.items() if not key.startswith("_")}
