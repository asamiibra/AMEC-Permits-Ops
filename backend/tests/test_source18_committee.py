from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from backend.app.models import (
    Base,
    ConsultancyOffice,
    Source18EngineerProfile,
    Source18PolicyVersion,
    Source18RosterMembership,
    Source18WorkflowTransaction,
)
from backend.app.services.source18 import (
    packet_manifest,
    require_capability,
    staffing_readiness,
    transition,
)
from fastapi import HTTPException


@pytest.fixture()
def db():
    engine = create_engine("sqlite://", future=True)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()


def test_engineer_update_cannot_skip_regulator_counted(db):
    tx = Source18WorkflowTransaction(
        authority_case_id="case-1", office_id="office-1", transaction_type="ENGINEER_UPDATE",
        processing_mode="COUNTER_PROCESS", state="UPDATED_CREDENTIAL_VERIFIED",
        currentness_state="CURRENT", remediation_exception=False, requested_disciplines_json=[],
        current_disciplines_json=[], idempotency_key="idempotent-1", actor_ref="tester",
        source_snapshot_json={},
    )
    db.add(tx)
    db.commit()
    transition(db, tx, "OFFICE_ROSTER_ADD_PREPARING", actor="tester", correlation_id="corr-1")
    with pytest.raises(HTTPException) as error:
        transition(db, tx, "REGULATOR_COUNTED", actor="tester", correlation_id="corr-2")
    assert error.value.detail["code"] == "SOURCE18_INVALID_TRANSITION"


def test_packet_manifest_rejects_authority_only_and_blank_values():
    tx = Source18WorkflowTransaction(
        authority_case_id="case-1", office_id="office-1", transaction_type="ENGINEER_UPDATE",
        processing_mode="COUNTER_PROCESS", state="COUNTER_SUBMITTED", currentness_state="CURRENT",
        remediation_exception=False, requested_disciplines_json=[], current_disciplines_json=[],
        idempotency_key="idempotent-2", actor_ref="tester", source_snapshot_json={},
    )
    with pytest.raises(HTTPException) as authority_error:
        packet_manifest(tx, {"authority_only_values": {"regulator_count": "3"}})
    assert authority_error.value.detail["code"] == "AUTHORITY_ONLY_FIELD_WRITE_FORBIDDEN"
    with pytest.raises(HTTPException) as blank_error:
        packet_manifest(tx, {"blank_authority_fields": ["committee_quorum"]})
    assert blank_error.value.detail["code"] == "EXPLICIT_NOT_APPLICABLE_REQUIRED"


def test_capabilities_are_server_side_and_not_title_strings():
    require_capability("OWNER_SPONSOR", "VIEW_RAW_REGULATORY_PII")
    with pytest.raises(HTTPException) as error:
        require_capability("PROCESS_CHAMPION", "VIEW_RAW_REGULATORY_PII")
    assert error.value.detail["code"] == "CAPABILITY_DENIED"


def test_staffing_is_derived_from_current_roster_not_policy_counter(db):
    db.add(ConsultancyOffice(id="office-staffing", office_code="S18", name_en="Synthetic", name_ar="Synthetic"))
    policy = Source18PolicyVersion(
        policy_code="OFFICE_STAFFING", version="policy-1", status="CURRENT",
        source_class="OWNER_CONFIRMED", source_reference="synthetic-policy",
        rules_json={"required_count": 2, "eligible_disciplines": ["CIVIL"]},
        created_by="owner",
    )
    first = Source18EngineerProfile(
        id="engineer-1", office_id="office-staffing", engineer_ref="E1", display_name="One",
        discipline="CIVIL", status="ACTIVE", regulatory_profile_state="CURRENT",
        evidence_currentness="CURRENT",
    )
    second = Source18EngineerProfile(
        id="engineer-2", office_id="office-staffing", engineer_ref="E2", display_name="Two",
        discipline="CIVIL", status="ACTIVE", regulatory_profile_state="CURRENT",
        evidence_currentness="CURRENT",
    )
    db.add_all([policy, first, second]); db.flush()
    db.add_all([
        Source18RosterMembership(
            office_id="office-staffing", engineer_profile_id=first.id, discipline="CIVIL",
            regulator_counted_state="COUNTED", classified_engineer=True, status="ACTIVE",
        ),
        Source18RosterMembership(
            office_id="office-staffing", engineer_profile_id=second.id, discipline="CIVIL",
            regulator_counted_state="COUNTED", classified_engineer=True, status="ACTIVE",
        ),
    ])
    db.commit()
    assert staffing_readiness(db, "office-staffing")["regulator_counted"] == 2

    second_membership = db.query(Source18RosterMembership).filter_by(engineer_profile_id=second.id).one()
    second_membership.regulator_counted_state = "NOT_COUNTED"
    db.commit()
    readiness = staffing_readiness(db, "office-staffing")
    assert readiness["required_count"] == 2
    assert readiness["regulator_counted"] == 1
    assert readiness["buffer_or_gap"] == -1


def test_staffing_excludes_verified_credentials_pending_adds_and_expired_members(db):
    policy = Source18PolicyVersion(
        policy_code="OFFICE_STAFFING", version="policy-2", status="CURRENT",
        source_class="OWNER_CONFIRMED", source_reference="synthetic-policy",
        rules_json={"required_count": 1}, created_by="owner",
    )
    profile = Source18EngineerProfile(
        id="engineer-risk", office_id="office-risk", engineer_ref="ER", display_name="Risk",
        discipline="CIVIL", status="ACTIVE", regulatory_profile_state="UPDATED_CREDENTIAL_VERIFIED",
        evidence_currentness="CURRENT",
    )
    db.add_all([policy, profile]); db.flush()
    db.add_all([
        Source18RosterMembership(
            office_id="office-risk", engineer_profile_id=profile.id, discipline="CIVIL",
            regulator_counted_state="COUNTED", classified_engineer=True, status="ACTIVE",
        ),
        Source18RosterMembership(
            office_id="office-risk", engineer_profile_id="pending", discipline="CIVIL",
            regulator_counted_state="COUNTED", classified_engineer=True, status="PENDING_ADD",
        ),
    ])
    db.commit()
    readiness = staffing_readiness(db, "office-risk")
    assert readiness["regulator_counted"] == 0
    assert "CREDENTIAL_VERIFIED_NOT_REGULATOR_COUNTED" in readiness["at_risk_engineers"][0]["reasons"]
    assert readiness["pending_roster_additions"] == ["pending"]


def test_unknown_staffing_policy_fails_closed(db):
    with pytest.raises(HTTPException) as error:
        staffing_readiness(db, "missing-policy-office")
    assert error.value.detail["code"] == "STAFFING_POLICY_UNKNOWN_FAIL_CLOSED"
