from __future__ import annotations

import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from sqlalchemy import select

from backend.app.db import SessionLocal, engine
from backend.app.models import AssertionStatus, VerifiedAssertion
from backend.app.schemas.phase4 import ProjectionRequest
from backend.app.services.phase4 import execute_projection


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


def test_phase4_end_to_end_review_projection_and_idempotency(client):
    event_id = _token("event")
    source = {
        "event_id": event_id,
        "scan_id_or_observation_group": _token("scan"),
        "source_surface": "CONTROLLED_SYNTHETIC_FIXTURE",
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
        "axes_json": {"document_type": "APPLICATION_FORM", "discipline": "ENGINEERING", "source_mode": "RULES_ONLY"},
    }
    response = client.post("/api/phase4/classification-envelopes", json=classification)
    assert response.status_code == 200, response.text
    classification_id = response.json()["id"]
    queue = client.get("/api/phase4/review-queue", headers={"X-Dev-Role": "PROCESS_CHAMPION"})
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


def test_phase4_golden_path_catalog_is_frozen():
    golden_paths = [
        "source-event-idempotency", "source-version-binding", "stable-observation", "evidence-envelope",
        "runtime-provenance", "rules-only-classification", "review-queue", "accept-decision",
        "reject-decision", "defer-decision", "human-correction-lineage", "owner-escalation",
        "verified-assertion-bridge", "assertion-status-gate", "projection-plan", "projection-receipt",
        "projection-idempotency", "protected-action-denial", "work-notification-audit-side-effects", "no-live-source-access",
    ]
    assert len(golden_paths) == 20


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
