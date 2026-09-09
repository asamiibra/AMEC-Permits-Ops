from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pytest

from app.models import Base, Source18WorkflowTransaction
from app.services.source18 import packet_manifest, require_capability, transition
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
