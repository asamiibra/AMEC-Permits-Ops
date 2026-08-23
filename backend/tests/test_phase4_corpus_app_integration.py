from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select

from backend.app.db import SessionLocal, engine
from backend.app.models import (
    AssertionStatus,
    AuditEvent,
    Phase4ClassificationEnvelope,
    Phase4ClassifierCorrectionEvent,
    Phase4ProjectionReceipt,
    Phase4ReviewDecision,
    Phase4SourceChangeEvent,
    Finding,
    NotificationEvent,
    WorkflowTask,
    VerifiedAssertion,
)
from backend.app.schemas.phase4 import ProjectionRequest, ReviewDecisionIn
from backend.app.services.phase4 import ALLOWED_DECISIONS, execute_projection, record_review_decision


def _token(label: str) -> str:
    return f"phase4-test-{label}-{uuid4().hex}"


def test_phase4_contract_artifacts_are_complete():
    root = "contracts/amec/phase4"
    with open(f"{root}/AMEC_PHASE4_PHASE3C_ASSERTION_MAPPING_v1.json", encoding="utf-8") as handle:
        mapping = json.load(handle)
    with open(f"{root}/AMEC_PHASE4_PRIMARY_ACCEPTANCE_CHECKS_v1.json", encoding="utf-8") as handle:
        checks = json.load(handle)
    assert len(mapping["rows"]) == 419
    assert len(checks["checks"]) == 250
    assert all(item.get("result") == "PASS" for item in checks["checks"])
    with open(f"{root}/AMEC_PHASE4_V35R1_REVALIDATION_v1.json", encoding="utf-8") as handle:
        revalidation = json.load(handle)
    assert len(revalidation["golden_paths"]) == 20
    assert all(item["final_result"] == "PASS" and item["exact_executable_test_nodes"] and item["command"] and item["raw_final_sha_log_reference"] for item in revalidation["golden_paths"])
    assert revalidation["primary_checks"]["pip_047_executable_six_action_proof"] is True
    assert revalidation["primary_checks"]["gov_044_executable_golden_path_proof"] is True


def test_phase4_end_to_end_review_projection_and_idempotency(client):
    event_id = _token("event")
    source = {
        "event_id": event_id,
        "scan_id_or_observation_group": _token("scan"),
        "source_surface": "APP_UPLOAD",
        "source_artifact_id_or_locator": "fixture://amec/phase4/source-001",
        "source_version_token": "v1",
        "event_type": "NEW_VERSION",
        "origin": "CONTROLLED_SYNTHETIC",
        "correlation_id": _token("corr"),
        "observed_at": "2026-08-23T00:00:00Z",
        "content_identity_proof": {"sha256": hashlib.sha256(b"synthetic-phase4").hexdigest()},
    }
    response = client.post("/api/phase4/source-events", json=source, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert response.status_code == 200, response.text
    root_event_id = response.json()["id"]
    assert client.post("/api/phase4/source-events", json=source).json()["id"] == root_event_id

    evidence = {
        "root_event_id": root_event_id,
        "source_artifact_id": source["source_artifact_id_or_locator"],
        "source_version_token": "v1",
        "source_surface": source["source_surface"],
        "evidence_envelope_sha256": hashlib.sha256(b"evidence-envelope").hexdigest(),
        "runtime_sha256": hashlib.sha256(b"deterministic-parser-v1").hexdigest(),
        "capability_id": "PHASE4_SOURCE_REVIEW",
        "handler_parser_identity": "fixture-parser-v1",
        "evidence_json": {"document_type": "APPLICATION_FORM", "fields": {"plot": "SYNTHETIC-001"}},
    }
    response = client.post("/api/phase4/evidence-envelopes", json=evidence)
    assert response.status_code == 200, response.text

    classification = {
        "envelope_id": _token("classification"),
        "root_event_id": root_event_id,
        "source_mode": "RULES_ONLY",
        "module_truth_contract_sha": "d18ebed191b8f2633d5984ff57ab25803fe19beeb9c73999946abffddb974f2c",
        "corpus_app_contract_sha": "387a741b2531afb54398fadbe8aac0d73e2a1ba9aab619e48d5dd5b5d7289908",
        "axes_json": {"document_type": "APPLICATION_FORM", "discipline": "ENGINEERING", "source_mode": "RULES_ONLY", "scope": {"scope_type": "PROJECT", "scope_id": "synthetic-project-001"}, "relationship_resolution": {"source_entity_id": "synthetic-source-001", "candidate_entity_id": "synthetic-project-001", "relationship_type": "PROJECT_DOCUMENT", "resolution": "BOUND_TO_PROJECT"}},
    }
    response = client.post("/api/phase4/classification-envelopes", json=classification)
    assert response.status_code == 200, response.text
    classification_id = response.json()["id"]
    queue = client.get("/api/phase4/review-queue?scope_type=PROJECT&scope_id=synthetic-project-001", headers={"X-Dev-Role": "PROCESS_CHAMPION"})
    assert queue.status_code == 200 and any(item["id"] == classification_id for item in queue.json()["items"])

    decision = {
        "decision_id": _token("decision"),
        "classification_envelope_id": classification_id,
        "decision": "ACCEPT",
        "actor_id": "synthetic-owner-reviewer",
        "capability": "PHASE4_REVIEW_DECISION",
        "scope_type": "PROJECT",
        "scope_id": "synthetic-project-001",
        "idempotency_key": _token("decision-key"),
    }
    response = client.post("/api/phase4/review-decisions", json=decision, headers={"X-Dev-Role": "PROCESS_CHAMPION"})
    assert response.status_code == 200, response.text

    with SessionLocal() as db:
        assertion = db.scalar(select(VerifiedAssertion).where(VerifiedAssertion.status == AssertionStatus.CURRENT))
    assert assertion is not None, "seeded synthetic environment must expose a current VerifiedAssertion"

    promotion = {"review_decision_id": response.json()["id"], "verified_assertion_id": assertion.id, "idempotency_key": _token("promotion")}
    denied = client.post(f"/api/phase4/verified-assertions/{assertion.id}/promote", json=promotion, headers={"X-Dev-Role": "ENGINEERING"})
    assert denied.status_code == 403
    promoted = client.post(f"/api/phase4/verified-assertions/{assertion.id}/promote", json=promotion, headers={"X-Dev-Role": "OWNER_SPONSOR"})
    assert promoted.status_code == 200, promoted.text

    projection = {
        "projection_id": _token("projection"),
        "verified_assertion_id": assertion.id,
        "target_domain": "PROPOSALOPS",
        "target_entity_type": "WORKSPACE_FIELD_REVIEW",
        "target_entity_id": "synthetic-project-001",
        "operation": "CREATE_REVIEW_WORK",
        "precondition_version": "assertion-v1",
        "idempotency_key": _token("projection-key"),
        "root_event_id": root_event_id,
        "correlation_id": _token("projection-correlation"),
    }
    planned = client.post("/api/phase4/projection-plans", json=projection, headers={"X-Dev-Role": "OWNER_SPONSOR"})
    assert planned.status_code == 200, planned.text
    projected = client.post("/api/phase4/projections", json=projection, headers={"X-Dev-Role": "OWNER_SPONSOR"})
    assert projected.status_code == 200, projected.text
    receipt = projected.json()
    assert receipt["result"] == "PROJECTED_REVIEW_REQUIRED"
    assert len(receipt["work_ids_json"]) == 1
    assert len(receipt["notification_ids_json"]) == 1
    assert len(receipt["audit_ids_json"]) == 1
    repeat = client.post("/api/phase4/projections", json=projection, headers={"X-Dev-Role": "OWNER_SPONSOR"})
    assert repeat.status_code == 200 and repeat.json()["id"] == receipt["id"]

    protected = {**projection, "projection_id": _token("protected"), "idempotency_key": _token("protected-key"), "operation": "SUBMIT"}
    response = client.post("/api/phase4/projection-plans", json=protected, headers={"X-Dev-Role": "OWNER_SPONSOR"})
    assert response.status_code == 403


def test_be_p4_v35_executable_golden_paths_source_and_negative_states(client):
    """Execute the source/negative golden paths; the catalog cannot self-certify them."""
    paths = [
        ("GP-01", {"source_surface": "APP_UPLOAD", "event_type": "NEW_VERSION"}),
        ("GP-03", {"source_surface": "APP_UPLOAD", "event_type": "MODIFIED_CANDIDATE"}),
        ("GP-04", {"source_surface": "APP_UPLOAD", "event_type": "MOVE_RENAME_CANDIDATE"}),
        ("GP-05", {"source_surface": "APP_UPLOAD", "event_type": "MISSING_CANDIDATE"}),
        ("GP-06", {"source_surface": "APP_UPLOAD", "event_type": "CONTENT_CHANGED", "extra_axes": {"contradictions": [{"axis": "discipline", "values": ["ENGINEERING", "CIVIL"]}]}}),
        ("GP-07", {"source_surface": "APP_UPLOAD", "event_type": "MISSING_CANDIDATE", "extra_axes": {"unsupported_capability_state": "SECRET_EXCLUDE"}}),
        ("GP-08", {"source_surface": "APP_UPLOAD", "event_type": "NEW_VERSION", "extra_axes": {"unsupported_capability_state": "UNSUPPORTED_CAPABILITY"}}),
    ]
    for golden_path_id, options in paths:
        envelope_id = _review_fixture(client, **options)
        with SessionLocal() as db:
            envelope = db.get(Phase4ClassificationEnvelope, envelope_id)
            event = db.execute(select(Phase4SourceChangeEvent).where(Phase4SourceChangeEvent.id == envelope.root_event_id)).scalar_one()
            assert event.source_surface == "APP_UPLOAD", golden_path_id
            assert event.event_type == options["event_type"], golden_path_id
            assert envelope is not None and envelope.axes_json, golden_path_id
    secret_id = _review_fixture(client, source_surface="APP_UPLOAD", event_type="MISSING_CANDIDATE", extra_axes={"unsupported_capability_state": "SECRET_EXCLUDE"})
    assert _post_review(client, _review_payload(secret_id, "MARK_OUT_OF_SCOPE")).status_code == 200


def test_be_p4_v35_gp03_modified_source_creates_new_version_candidate(client):
    """GP-03 uses one source artifact with two distinct source versions."""
    artifact = "fixture://amec/phase4/modified-source-candidate"
    first_id = _review_fixture(
        client,
        source_surface="APP_UPLOAD",
        event_type="NEW_VERSION",
        source_artifact_id=artifact,
        source_version_token="v1",
    )
    second_id = _review_fixture(
        client,
        source_surface="APP_UPLOAD",
        event_type="MODIFIED_CANDIDATE",
        source_artifact_id=artifact,
        source_version_token="v2",
    )
    with SessionLocal() as db:
        first = db.get(Phase4ClassificationEnvelope, first_id)
        second = db.get(Phase4ClassificationEnvelope, second_id)
        first_event = db.get(Phase4SourceChangeEvent, first.root_event_id)
        second_event = db.get(Phase4SourceChangeEvent, second.root_event_id)
        assert first_event.source_artifact_id_or_locator == second_event.source_artifact_id_or_locator == artifact
        assert first_event.source_version_token == "v1"
        assert second_event.source_version_token == "v2"
        assert first_event.id != second_event.id


def test_be_p4_v35_gp06_contradictory_evidence_is_deferred(client):
    """GP-06 persists a contradiction and exercises a real defer decision."""
    envelope_id = _review_fixture(
        client,
        source_surface="APP_UPLOAD",
        event_type="CONTENT_CHANGED",
        extra_axes={"contradictions": [{"axis": "discipline", "values": ["ENGINEERING", "CIVIL"]}]},
    )
    response = _post_review(client, _review_payload(envelope_id, "DEFER"))
    assert response.status_code == 200, response.text
    with SessionLocal() as db:
        decision = db.get(Phase4ReviewDecision, response.json()["id"])
        envelope = db.get(Phase4ClassificationEnvelope, envelope_id)
        assert envelope.axes_json["contradictions"]
        assert decision.decision == "DEFER"


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="Phase4 concurrency proof requires PostgreSQL")
def test_phase4_postgresql_projection_retry_is_serialized():
    with SessionLocal() as db:
        assertion = db.scalar(select(VerifiedAssertion).where(VerifiedAssertion.status == AssertionStatus.CURRENT))
    assert assertion is not None
    request = ProjectionRequest(
        projection_id=_token("concurrent-projection"),
        verified_assertion_id=assertion.id,
        target_domain="PROPOSALOPS",
        target_entity_type="CONCURRENT_RETRY",
        target_entity_id=_token("target"),
        operation="CREATE_REVIEW_WORK",
        precondition_version="assertion-v1",
        idempotency_key=_token("concurrent-key"),
        correlation_id=_token("concurrent-correlation"),
    )

    def invoke() -> str:
        with SessionLocal() as db:
            item = execute_projection(db, request, "OWNER_SPONSOR")
            db.commit()
            return item.id

    with ThreadPoolExecutor(max_workers=2) as pool:
        result_ids = list(pool.map(lambda _: invoke(), range(2)))
    assert result_ids[0] == result_ids[1]


def _review_fixture(client, *, scope_id: str = "synthetic-project-001", include_scope: bool = True, include_relationship: bool = True, source_surface: str = "CONTROLLED_SYNTHETIC_FIXTURE", event_type: str = "NEW_VERSION", source_artifact_id: str | None = None, source_version_token: str = "v1", extra_axes: dict | None = None) -> str:
    event_id = _token("review-event")
    source = {
        "event_id": event_id,
        "scan_id_or_observation_group": _token("review-scan"),
        "source_surface": source_surface,
        "source_artifact_id_or_locator": source_artifact_id or f"fixture://amec/phase4/{event_id}",
        "source_version_token": source_version_token,
        "event_type": event_type,
        "origin": "CONTROLLED_SYNTHETIC",
        "correlation_id": _token("review-correlation"),
        "observed_at": "2026-08-23T00:00:00Z",
        "content_identity_proof": {"sha256": hashlib.sha256(event_id.encode()).hexdigest()},
    }
    event = client.post("/api/phase4/source-events", json=source, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert event.status_code == 200, event.text
    axes = {
        "document_type": "APPLICATION_FORM",
        "discipline": "ENGINEERING",
        "source_precedence": "accepted Phase3C Module Truth rules",
        "classification_proposal": {"document_type": "APPLICATION_FORM", "discipline": "ENGINEERING"},
    }
    if include_scope:
        axes["scope"] = {"scope_type": "PROJECT", "scope_id": scope_id}
    if include_relationship:
        axes["relationship_resolution"] = {"source_entity_id": "synthetic-source-001", "candidate_entity_id": scope_id, "relationship_type": "PROJECT_DOCUMENT", "resolution": "BOUND_TO_PROJECT"}
    if extra_axes:
        axes.update(extra_axes)
    classification = {
        "envelope_id": _token("review-classification"),
        "root_event_id": event.json()["id"],
        "source_mode": "RULES_ONLY",
        "module_truth_contract_sha": "d18ebed191b8f2633d5984ff57ab25803fe19beeb9c73999946abffddb974f2c",
        "corpus_app_contract_sha": "387a741b2531afb54398fadbe8aac0d73e2a1ba9aab619e48d5dd5b5d7289908",
        "axes_json": axes,
    }
    response = client.post("/api/phase4/classification-envelopes", json=classification, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _review_payload(envelope_id: str, decision: str, *, key: str | None = None, record_version: int = 1) -> dict:
    return {
        "decision_id": _token(f"{decision.lower()}-decision"),
        "classification_envelope_id": envelope_id,
        "decision": decision,
        "actor_id": "synthetic-owner-reviewer",
        "capability": "PHASE4_RESOLVE_RELATIONSHIP" if decision == "RESOLVE_RELATIONSHIP" else "PHASE4_REVIEW_DECISION",
        "scope_type": "PROJECT",
        "scope_id": "synthetic-project-001",
        "record_version": record_version,
        "idempotency_key": key or _token(f"{decision.lower()}-key"),
        "corrections_json": [{
            "source_entity_id": "synthetic-source-001",
            "candidate_entity_id": "synthetic-project-001",
            "relationship_type": "PROJECT_DOCUMENT",
            "resolution": "BOUND_TO_PROJECT",
        }] if decision == "RESOLVE_RELATIONSHIP" else ([{"axis": "discipline", "old_value": "ENGINEERING", "new_value": "CIVIL", "reason": "Synthetic correction requires human review.", "evidence_ids": []}] if decision == "CORRECT" else []),
    }


def _post_review(client, payload: dict, role: str = "SYSTEM_ADMIN"):
    return client.post("/api/phase4/review-decisions", json=payload, headers={"X-Dev-Role": role})


def test_be_p4_rd_001_exact_allowlist_is_six_actions():
    assert ALLOWED_DECISIONS == {"ACCEPT", "CORRECT", "DEFER", "MARK_OUT_OF_SCOPE", "RESOLVE_RELATIONSHIP", "REJECT"}


@pytest.mark.parametrize("decision", ["ACCEPT", "CORRECT", "DEFER", "MARK_OUT_OF_SCOPE", "RESOLVE_RELATIONSHIP", "REJECT"])
def test_be_p4_rd_002_to_007_each_contract_action_is_accepted(client, decision):
    envelope_id = _review_fixture(client)
    response = _post_review(client, _review_payload(envelope_id, decision))
    assert response.status_code == 200, response.text
    assert response.json()["decision"] == decision


def test_be_p4_rd_008_unknown_decision_is_rejected(client):
    response = _post_review(client, _review_payload(_review_fixture(client), "NOT_A_PHASE4_DECISION"))
    assert response.status_code == 422


def test_be_p4_rd_009_ordinary_review_capability_mismatch_is_rejected(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "ACCEPT")
    payload["capability"] = "PHASE4_RESOLVE_RELATIONSHIP"
    response = _post_review(client, payload)
    assert response.status_code == 403


def test_be_p4_rd_010_relationship_capability_mismatch_is_rejected(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "RESOLVE_RELATIONSHIP")
    payload["capability"] = "PHASE4_REVIEW_DECISION"
    response = _post_review(client, payload)
    assert response.status_code == 403


def test_be_p4_rd_011_cross_project_review_is_rejected(client):
    envelope_id = _review_fixture(client, scope_id="project-a")
    response = _post_review(client, _review_payload(envelope_id, "ACCEPT"))
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "REVIEW_SCOPE_MISMATCH"


def test_be_p4_rd_012_cross_entity_relationship_is_rejected(client):
    envelope_id = _review_fixture(client, scope_id="entity-a")
    payload = _review_payload(envelope_id, "RESOLVE_RELATIONSHIP")
    payload["scope_type"] = "ENTITY"
    payload["scope_id"] = "entity-b"
    response = _post_review(client, payload)
    assert response.status_code == 403


def test_be_p4_rd_013_stale_review_version_is_rejected(client):
    envelope_id = _review_fixture(client)
    response = _post_review(client, _review_payload(envelope_id, "DEFER", record_version=2))
    assert response.status_code == 409


def test_be_p4_rd_014_duplicate_retry_is_idempotent(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "ACCEPT", key=_token("same-review-key"))
    first = _post_review(client, payload)
    second = _post_review(client, payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_be_p4_rd_015_correct_keeps_original_envelope_identity(client):
    envelope_id = _review_fixture(client)
    with SessionLocal() as db:
        before = db.get(Phase4ClassificationEnvelope, envelope_id)
        snapshot = (before.envelope_id, before.root_event_id, before.immutable_result_hash, before.axes_json)
    payload = _review_payload(envelope_id, "CORRECT")
    payload["corrections_json"] = [{"axis": "discipline", "old_value": "ENGINEERING", "new_value": "CIVIL", "reason": "synthetic correction", "evidence_ids": []}]
    assert _post_review(client, payload).status_code == 200
    with SessionLocal() as db:
        after = db.get(Phase4ClassificationEnvelope, envelope_id)
        assert (after.envelope_id, after.root_event_id, after.immutable_result_hash, after.axes_json) == snapshot


def test_be_p4_rd_016_correct_creates_immutable_correction_event(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "CORRECT")
    payload["corrections_json"] = [{"axis": "document_type", "old_value": "APPLICATION_FORM", "new_value": "FORM", "reason": "synthetic correction", "evidence_ids": ["synthetic://evidence/correction"]}]
    assert _post_review(client, payload).status_code == 200
    with SessionLocal() as db:
        correction = db.scalar(select(Phase4ClassifierCorrectionEvent).where(Phase4ClassifierCorrectionEvent.classification_envelope_id == envelope_id))
        assert correction is not None
        assert correction.new_value_json == "FORM"


def test_be_p4_rd_017_out_of_scope_remains_distinct_from_reject(client):
    out_scope = _post_review(client, _review_payload(_review_fixture(client), "MARK_OUT_OF_SCOPE"))
    rejected = _post_review(client, _review_payload(_review_fixture(client), "REJECT"))
    assert out_scope.json()["decision"] == "MARK_OUT_OF_SCOPE"
    assert rejected.json()["decision"] == "REJECT"


def test_be_p4_rd_018_out_of_scope_does_not_create_verified_assertion(client):
    envelope_id = _review_fixture(client)
    with SessionLocal() as db:
        before = len(list(db.scalars(select(VerifiedAssertion))))
    assert _post_review(client, _review_payload(envelope_id, "MARK_OUT_OF_SCOPE")).status_code == 200
    with SessionLocal() as db:
        assert len(list(db.scalars(select(VerifiedAssertion)))) == before


def test_be_p4_rd_019_out_of_scope_does_not_execute_projection(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "MARK_OUT_OF_SCOPE")
    with SessionLocal() as db:
        before = tuple(len(list(db.scalars(select(model)))) for model in (Phase4ProjectionReceipt, WorkflowTask, Finding, NotificationEvent))
    assert _post_review(client, payload).status_code == 200
    with SessionLocal() as db:
        envelope = db.get(Phase4ClassificationEnvelope, envelope_id)
        assert envelope is not None
        assert db.scalar(select(Phase4ProjectionReceipt).where(Phase4ProjectionReceipt.root_event_id == envelope.root_event_id)) is None
        after = tuple(len(list(db.scalars(select(model)))) for model in (Phase4ProjectionReceipt, WorkflowTask, Finding, NotificationEvent))
        assert after == before


def test_be_p4_rd_020_relationship_requires_dedicated_capability(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "RESOLVE_RELATIONSHIP")
    payload["capability"] = "PHASE4_REVIEW_DECISION"
    response = _post_review(client, payload)
    assert response.status_code == 403


def test_be_p4_rd_021_relationship_payload_is_bound(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "RESOLVE_RELATIONSHIP")
    payload["corrections_json"] = []
    response = _post_review(client, payload)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "RELATIONSHIP_RESOLUTION_CANDIDATE_MISMATCH"


def test_be_p4_rd_022_relationship_is_version_checked(client):
    envelope_id = _review_fixture(client)
    response = _post_review(client, _review_payload(envelope_id, "RESOLVE_RELATIONSHIP", record_version=9))
    assert response.status_code == 409


def test_be_p4_rd_023_relationship_does_not_execute_protected_action(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "RESOLVE_RELATIONSHIP")
    with SessionLocal() as db:
        before = tuple(len(list(db.scalars(select(model)))) for model in (Phase4ProjectionReceipt, WorkflowTask, Finding, NotificationEvent))
    response = _post_review(client, payload)
    assert response.status_code == 200
    with SessionLocal() as db:
        envelope = db.get(Phase4ClassificationEnvelope, envelope_id)
        assert envelope is not None
        assert db.scalar(select(Phase4ProjectionReceipt).where(Phase4ProjectionReceipt.root_event_id == envelope.root_event_id)) is None
        after = tuple(len(list(db.scalars(select(model)))) for model in (Phase4ProjectionReceipt, WorkflowTask, Finding, NotificationEvent))
        assert after == before


@pytest.mark.parametrize("decision", ["ACCEPT", "CORRECT", "DEFER", "MARK_OUT_OF_SCOPE", "RESOLVE_RELATIONSHIP", "REJECT"])
def test_be_p4_rd_024_each_decision_is_auditable(client, decision):
    envelope_id = _review_fixture(client)
    response = _post_review(client, _review_payload(envelope_id, decision))
    assert response.status_code == 200
    with SessionLocal() as db:
        event = db.scalar(select(AuditEvent).where(AuditEvent.entity_id == envelope_id, AuditEvent.event_type == f"PHASE4_REVIEW_DECISION_{decision}"))
        assert event is not None


def test_be_p4_rd_025_decision_retains_actor_project_entity_lineage(client):
    envelope_id = _review_fixture(client)
    response = _post_review(client, _review_payload(envelope_id, "ACCEPT"))
    assert response.status_code == 200
    with SessionLocal() as db:
        decision = db.get(Phase4ReviewDecision, response.json()["id"])
        assert decision.actor_id == "local-phase4-role:SYSTEM_ADMIN"
        assert decision.scope_type == "PROJECT"
        assert decision.scope_id == "synthetic-project-001"


def test_be_p4_v35_026_missing_server_scope_rejects_review_decision(client):
    envelope_id = _review_fixture(client, include_scope=False)
    response = _post_review(client, _review_payload(envelope_id, "ACCEPT"))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "REVIEW_SCOPE_NOT_BOUND"


def test_be_p4_v35_027_scoped_queue_excludes_wrong_project(client):
    envelope_id = _review_fixture(client, scope_id="project-a")
    missing = client.get("/api/phase4/review-queue", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    wrong = client.get("/api/phase4/review-queue?scope_type=PROJECT&scope_id=project-b", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    right = client.get("/api/phase4/review-queue?scope_type=PROJECT&scope_id=project-a", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert missing.status_code == 422
    assert wrong.status_code == 200 and not any(item["id"] == envelope_id for item in wrong.json()["items"])
    assert right.status_code == 200 and any(item["id"] == envelope_id for item in right.json()["items"])


def test_be_p4_v35_028_client_actor_spoof_is_not_persisted_or_audited(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "ACCEPT")
    payload["actor_id"] = "someone-else"
    response = _post_review(client, payload)
    assert response.status_code == 200
    with SessionLocal() as db:
        decision = db.get(Phase4ReviewDecision, response.json()["id"])
        event = db.scalar(select(AuditEvent).where(AuditEvent.entity_id == envelope_id, AuditEvent.event_type == "PHASE4_REVIEW_DECISION_ACCEPT").order_by(AuditEvent.occurred_at.desc()))
        assert decision.actor_id == "local-phase4-role:SYSTEM_ADMIN"
        assert event is not None and event.actor_id == "local-phase4-role:SYSTEM_ADMIN"
        assert decision.actor_id != "someone-else"


def test_be_p4_v35_029_same_idempotency_key_changed_payload_rejects(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "ACCEPT", key=_token("collision"))
    assert _post_review(client, payload).status_code == 200
    changed = {**payload, "decision_id": _token("changed"), "decision": "REJECT"}
    response = _post_review(client, changed)
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "IDEMPOTENCY_KEY_REUSE_MISMATCH"


def test_be_p4_v35_030_same_idempotency_key_identical_payload_replays(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "ACCEPT", key=_token("replay"))
    first = _post_review(client, payload)
    second = _post_review(client, payload)
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


@pytest.mark.skipif(engine.dialect.name != "postgresql", reason="V3.5 envelope concurrency proof requires PostgreSQL")
def test_be_p4_v35_031_concurrent_different_decisions_same_version_exactly_one_wins(client):
    envelope_id = _review_fixture(client)
    first = ReviewDecisionIn(**_review_payload(envelope_id, "ACCEPT", key=_token("concurrent-a")))
    second = ReviewDecisionIn(**_review_payload(envelope_id, "DEFER", key=_token("concurrent-b")))

    def invoke(payload: ReviewDecisionIn):
        with SessionLocal() as db:
            try:
                item = record_review_decision(db, payload, "SYSTEM_ADMIN")
                db.commit()
                return ("PASS", item.id)
            except HTTPException as exc:
                db.rollback()
                return ("FAIL", exc.status_code, exc.detail)

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(invoke, [first, second]))
    assert sum(outcome[0] == "PASS" for outcome in outcomes) == 1
    assert sum(outcome[0] == "FAIL" and outcome[1] == 409 for outcome in outcomes) == 1
    with SessionLocal() as db:
        envelope = db.get(Phase4ClassificationEnvelope, envelope_id)
        decisions = list(db.scalars(select(Phase4ReviewDecision).where(Phase4ReviewDecision.classification_envelope_id == envelope_id)))
        assert envelope is not None and envelope.record_version == 2
        assert len(decisions) == 1


def test_be_p4_v35_032_successful_decision_advances_record_version_once(client):
    envelope_id = _review_fixture(client)
    response = _post_review(client, _review_payload(envelope_id, "DEFER"))
    assert response.status_code == 200
    with SessionLocal() as db:
        envelope = db.get(Phase4ClassificationEnvelope, envelope_id)
        assert envelope is not None and envelope.record_version == 2
        assert response.json()["record_version"] == 1


def test_be_p4_v35_033_correct_empty_corrections_rejected(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "CORRECT")
    payload["corrections_json"] = []
    response = _post_review(client, payload)
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "CORRECTION_REQUIRED"


def test_be_p4_v35_034_correct_validates_axis_old_new_reason_and_evidence(client):
    envelope_id = _review_fixture(client)
    invalid_cases = [
        {"axis": "not_an_axis", "old_value": "ENGINEERING", "new_value": "CIVIL", "reason": "x", "evidence_ids": []},
        {"axis": "discipline", "old_value": "WRONG", "new_value": "CIVIL", "reason": "x", "evidence_ids": []},
        {"axis": "discipline", "old_value": "ENGINEERING", "new_value": "ENGINEERING", "reason": "x", "evidence_ids": []},
        {"axis": "discipline", "old_value": "ENGINEERING", "new_value": "CIVIL", "reason": "", "evidence_ids": []},
        {"axis": "discipline", "old_value": "ENGINEERING", "new_value": "CIVIL", "reason": "x"},
    ]
    for correction in invalid_cases:
        payload = _review_payload(envelope_id, "CORRECT")
        payload["corrections_json"] = [correction]
        response = _post_review(client, payload)
        assert response.status_code in {409, 422}


def test_be_p4_v35_035_relationship_missing_server_candidate_rejected(client):
    envelope_id = _review_fixture(client, include_relationship=False)
    response = _post_review(client, _review_payload(envelope_id, "RESOLVE_RELATIONSHIP"))
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "RELATIONSHIP_SERVER_CANDIDATE_NOT_BOUND"


def test_be_p4_v35_036_relationship_arbitrary_client_candidate_rejected(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "RESOLVE_RELATIONSHIP")
    payload["corrections_json"][0]["candidate_entity_id"] = "client-invented-candidate"
    response = _post_review(client, payload)
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "RELATIONSHIP_RESOLUTION_CANDIDATE_MISMATCH"


def test_be_p4_v35_037_relationship_exact_server_candidate_accepted(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "RESOLVE_RELATIONSHIP")
    response = _post_review(client, payload)
    assert response.status_code == 200
    assert response.json()["decision"] == "RESOLVE_RELATIONSHIP"


def test_be_p4_v35_038_out_of_scope_actual_lineage_has_zero_projection_effect(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "MARK_OUT_OF_SCOPE")
    with SessionLocal() as db:
        envelope = db.get(Phase4ClassificationEnvelope, envelope_id)
        before = len(list(db.scalars(select(Phase4ProjectionReceipt).where(Phase4ProjectionReceipt.root_event_id == envelope.root_event_id))))
    assert _post_review(client, payload).status_code == 200
    with SessionLocal() as db:
        assert len(list(db.scalars(select(Phase4ProjectionReceipt).where(Phase4ProjectionReceipt.root_event_id == envelope.root_event_id)))) == before


def test_be_p4_v35_039_relationship_actual_lineage_has_zero_protected_effect(client):
    envelope_id = _review_fixture(client)
    payload = _review_payload(envelope_id, "RESOLVE_RELATIONSHIP")
    with SessionLocal() as db:
        envelope = db.get(Phase4ClassificationEnvelope, envelope_id)
        before = tuple(len(list(db.scalars(select(model)))) for model in (Phase4ProjectionReceipt, WorkflowTask, Finding, NotificationEvent))
    assert _post_review(client, payload).status_code == 200
    with SessionLocal() as db:
        after = tuple(len(list(db.scalars(select(model)))) for model in (Phase4ProjectionReceipt, WorkflowTask, Finding, NotificationEvent))
        assert after == before
        assert db.scalar(select(Phase4ProjectionReceipt).where(Phase4ProjectionReceipt.root_event_id == envelope.root_event_id)) is None


def test_be_p4_v35_040_review_queue_requires_and_enforces_scope(client):
    envelope_id = _review_fixture(client, scope_id="project-scoped")
    assert client.get("/api/phase4/review-queue", headers={"X-Dev-Role": "SYSTEM_ADMIN"}).status_code == 422
    wrong = client.get("/api/phase4/review-queue?scope_type=ENTITY&scope_id=project-scoped", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert wrong.status_code == 200 and not any(item["id"] == envelope_id for item in wrong.json()["items"])


def test_be_p4_v34_exact_primary_matrix_semantics():
    root = "contracts/amec/phase4"
    with open(f"{root}/AMEC_PHASE4_PRIMARY_ACCEPTANCE_CHECKS_v1.json", encoding="utf-8") as handle:
        checks = json.load(handle)["checks"]
    with open(f"{root}/AMEC_PHASE4_DOMAIN_INTEGRATION_COVERAGE_v1.json", encoding="utf-8") as handle:
        coverage = json.load(handle)
    by_id = {item["check_id"]: item for item in checks}
    pip = dict(line.split("|", 1) for line in """
PIP-001|immutable event ID
PIP-002|source/version identity bound
PIP-003|event type enum enforced
PIP-004|origin enum enforced
PIP-005|correlation ID present
PIP-006|path not logical identity
PIP-007|same-event replay idempotent
PIP-008|missing+new path not sufficient move proof
PIP-009|ProposalOps-origin loop guard
PIP-010|unchanged event has no duplicate downstream side effects
PIP-011|DETECTED state
PIP-012|WAITING_FOR_STABILITY state
PIP-013|READY_FOR_INTAKE state
PIP-014|repeated observation policy for external-style events
PIP-015|one arbitrary sleep rejected
PIP-016|app-upload atomic/durable completion policy
PIP-017|immutable source-version token
PIP-018|superseded observation cannot become current accidentally
PIP-019|SourceIntakeBatch reuse
PIP-020|SourceIntakeItem reuse
PIP-021|source intake service reuse
PIP-022|APP_UPLOAD mode
PIP-023|SYNOLOGY_EXTERNAL_EVIDENCE mode without SMB authority
PIP-024|evidence-envelope hash binding
PIP-025|runtime/handler/parser provenance binding
PIP-026|legacy source-intake regression
PIP-027|modified source creates new version candidate
PIP-028|missing source retains history
PIP-029|envelope schema validation
PIP-030|source/version binding
PIP-031|runtime identity binding
PIP-032|handler/parser identity binding
PIP-033|bounded evidence/provenance only
PIP-034|unsupported capability explicit
PIP-035|parser output not business authority
PIP-036|raw source does not cross merely because evidence exists
PIP-037|immutable envelope identity
PIP-038|immutable result hash
PIP-039|classifier/rules/taxonomy identities
PIP-040|Module Truth SHA binding
PIP-041|Corpus→App contract SHA binding
PIP-042|all required axes represented
PIP-043|per-axis evidence/rule IDs
PIP-044|per-axis confidence/review state
PIP-045|deterministic fixture/stub only
PIP-046|direct canonical mutation denied
PIP-047|all six review actions represented
PIP-048|review decision immutable/auditable
PIP-049|review capability server-authorized
PIP-050|project/entity isolation
PIP-051|stale review version rejected
PIP-052|original ClassificationEnvelope immutable after correction
PIP-053|correction event immutable
PIP-054|correction preserves evidence/version identities
PIP-055|correction does not mutate rules automatically
PIP-056|consequential/ambiguous accept-all prohibited
PIP-057|exactly one reuse strategy selected
PIP-058|one authoritative promotion path
PIP-059|legacy assertion compatibility
PIP-060|source/evidence lineage
PIP-061|review decision binding
PIP-062|authority rule/snapshot
PIP-063|explicit supersession
PIP-064|retry/idempotency
PIP-065|AUTO_ACCEPTED_LOW_RISK cannot bypass policy
PIP-066|classifier output cannot directly become VerifiedAssertion without policy/review
PIP-067|ProjectionPlan exists
PIP-068|ProjectionReceipt exists
PIP-069|target domain/entity explicit
PIP-070|target precondition/version explicit
PIP-071|deterministic idempotency key
PIP-072|same projection retry no duplicate business record
PIP-073|concurrent projection no duplicate business record
PIP-074|concurrent projection no duplicate Work/Issue/Notification/Audit
PIP-075|stale target version rejects blind overwrite
PIP-076|protected human actions denied
PIP-077|unresolved Owner decision cannot invent projection
PIP-078|Master Content governance respected
PIP-079|Finance authority respected
PIP-080|full root-event→projection→side-effect audit lineage reconstructed
""".strip().splitlines())
    gov = dict(line.split("|", 1) for line in """
GOV-001|Owner Phase4 authorization certificate hash/content valid
GOV-002|Phase4-specific Step3A4C supersession active and scoped only to non-deployment Phase4
GOV-003|Step3A4C remains false/deferred; no deployment-readiness acceptance inferred
GOV-004|Phase3C independent acceptance certificate hash/content valid
GOV-005|Phase3C accepted SHA equals 44968e3d43571ceb1df8493da683ff9e51a146d9 and equals Phase4 parent
GOV-006|accepted Phase3C parent/tree/rebaseline ancestry exact
GOV-007|Module Truth schema SHA matches accepted Phase3C
GOV-008|Module Truth contract SHA matches accepted Phase3C
GOV-009|Phase3C input manifest SHA matches
GOV-010|Phase3C classifier handoff SHA matches
GOV-011|Phase3C coverage matrix SHA matches
GOV-012|Phase3C governance validation SHA matches
GOV-013|Phase3C supplementary semantic validation SHA matches
GOV-014|Phase3C reference-integrity SHA matches and its zero-mismatch counters hold
GOV-015|Phase3C Owner-decision applicability + Section19 + source-state + deferred + freeze identities match
GOV-016|Phase3C 419 assertion arithmetic matches 30+123+250+16
GOV-017|Phase3C 300/300 + 149/149 + 87/87 acceptance/closure evidence bound
GOV-018|Phase3C 253/253 Owner edge bijection + 66 projection edges + 10 exact Domain25 sets hold
GOV-019|Stage1R base/completion/handoff identities match; Stage1R-B not required/no rerun
GOV-020|Phase4 branch zero-delta from exact accepted Phase3C SHA
GOV-021|inherited active versions directory contains only baseline_r13_0059.py
GOV-022|inherited active baseline blob equals 8d6112a26b195eba45a5db8fa453cd530bb2c1e7
GOV-023|active Alembic root/head = 1/1 and root/head = baseline_r13_0059
GOV-024|historical 0001–0059 remain archive-only and unchanged
GOV-025|no role-provision/Step3A4C/deployment repair bundled into Phase4 migration
GOV-026|reuse decision matrix complete before implementation
GOV-027|accepted source-intake service/models and VerifiedAssertion foundation inspected by exact accepted-parent bytes
GOV-028|no duplicate intake/parser/work/truth/document/audit store created
GOV-029|legacy source-intake behavior regression-preserved but cannot bypass new VerifiedAssertion authority
GOV-030|every one of 419 Phase3C assertions mapped exactly once as primary disposition
GOV-031|all 120 domain×integration-dimension cells complete
GOV-032|exactly four Master Content libraries and Checklist=Form preserved
GOV-033|10 truth domains + source precedence + authority separations preserved
GOV-034|all 16 protected human authorities denied through automated projection
GOV-035|all 10 OWNER_DECISION_PENDING policies remain unguessed
GOV-036|DSM actions zero / NAS Task Scheduler zero
GOV-037|SMB connections zero / new AMEC source reads and bytes zero
GOV-038|secret required/used false and SECRET_EXCLUDE enforced
GOV-039|raw AMEC content/values/local absolute binding paths not committed
GOV-040|no cloud LLM on real AMEC content; unsupported capability routes to review
GOV-041|full backend regression passes
GOV-042|full frontend regression passes
GOV-043|frontend production build passes
GOV-044|targeted Phase4 tests and 20 golden paths pass
GOV-045|disposable PostgreSQL 16 PG-01..PG-30 all pass
GOV-046|VERIFIED_LOCAL claim evidence-consistent
GOV-047|VERIFIED_POSTGRESQL claim evidence-consistent
GOV-048|VERIFIED_BROWSER=false / VERIFIED_DEPLOYED=false
GOV-049|deterministic serialization/reference integrity/freeze SHA recomputation all pass
GOV-050|Phase5/live shadow/writeback/Azure/Entra/deployment execution count = 0
""".strip().splitlines())
    assert set(pip) == {f"PIP-{index:03d}" for index in range(1, 81)}
    assert set(gov) == {f"GOV-{index:03d}" for index in range(1, 51)}
    for check_id, assertion in {**pip, **gov}.items():
        check = by_id[check_id]
        assert check["assertion"] == assertion
        assert check["category"] in {"PIPELINE_BEHAVIOR", "GOVERNANCE_PROVENANCE_SAFETY"}
        assert check["evidence"] and check["basis_refs"] and check["basis_state"]
        assert check["result"] == "PASS"
    domains = ["M1", "M2", "M3", "M4", "M5", "M6", "M7", "FINANCE", "MASTER_CONTENT", "REPORTS"]
    dimensions = ["input evidence types", "classification axes", "review policy", "VerifiedAssertion types", "projection targets", "projection preconditions", "source precedence", "currentness/version semantics", "idempotency", "conflict behavior", "Work/Issue/Notification/Audit effects", "protected human gates"]
    assert {(cell["domain"], cell["integration_dimension"]) for cell in coverage["cells"]} == {(domain, dimension) for domain in domains for dimension in dimensions}
    assert all(cell["evidence"] and cell["basis_refs"] and cell["basis_state"] for cell in coverage["cells"])
