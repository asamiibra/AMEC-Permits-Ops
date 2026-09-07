from __future__ import annotations

import time

from backend.app.schemas.classifier_v2 import ClassifierV2Request
from backend.app.services import classifier_v2
from backend.app.services.classifier_v2 import classify_document


def request(**overrides) -> ClassifierV2Request:
    values = {
        "fixture_id": f"test-{time.time_ns()}",
        "source_artifact_id": "synthetic-artifact://phase5/test",
        "source_version_token": "v1",
        "source_mode": "NEW_UNKNOWN_SOURCE",
        "scope_type": "PROJECT",
        "scope_id": "synthetic-project-001",
        "correlation_id": "phase5-test-correlation",
        "evidence_ids": ["synthetic-evidence://phase5/test/01"],
    }
    values.update(overrides)
    return ClassifierV2Request(**values)


def test_classifier_v2_preserves_the_four_locked_l0_modes():
    for mode in ("EXISTING_KNOWN_SOURCE", "NEW_UNKNOWN_SOURCE", "MODIFIED_KNOWN_SOURCE", "MOVE_RENAME_CANDIDATE"):
        result = classify_document(request(source_mode=mode, candidate_entity_id="synthetic-project-001"))
        assert result["source_mode"] == mode
        assert result["l0_prior_state"] == mode
        assert result["review_required"] is True
        assert result["auto_promotion_allowed"] is False


def test_classifier_v2_secret_and_out_of_scope_are_hard_gates():
    secret = classify_document(request(secret_exclude=True))
    out_of_scope = classify_document(request(out_of_scope=True))
    for result, state in ((secret, "SECRET_EXCLUDE"), (out_of_scope, "OUT_OF_SCOPE")):
        assert result["hard_gate"]["state"] == state
        assert result["hard_gate"]["deeper_processing"] is False
        assert result["hard_gate"]["llm_allowed"] is False
        assert result["projection_allowed"] is False
        assert result["llm"]["external_call_count"] == 0


def test_classifier_v2_material_contradiction_routes_to_review():
    result = classify_document(request(contradiction_families=["DISCIPLINE_CONFLICT", "CURRENTNESS_CONFLICT"]))
    assert result["classification_proposal"]["disposition"] == "NEEDS_REVIEW"
    assert result["scope"]["value"] == "AMBIGUOUS_REVIEW"
    assert len(result["rule_evaluations"]) == 5


def test_classifier_v2_rejects_non_synthetic_evidence_reference():
    try:
        classify_document(request(evidence_ids=["file:///not-allowed"]))
    except ValueError as exc:
        assert "sanitized" in str(exc)
    else:
        raise AssertionError("raw evidence reference was accepted")


def test_hard_gates_short_circuit_before_l2_and_l5(monkeypatch):
    def fail(*_args, **_kwargs):
        raise AssertionError("deeper classifier lane was invoked for hard gate")

    monkeypatch.setattr(classifier_v2, "evaluate_l2", fail)
    monkeypatch.setattr(classifier_v2, "evaluate_l5", fail)
    for values, state in (({"out_of_scope": True}, "OUT_OF_SCOPE"), ({"secret_exclude": True}, "SECRET_EXCLUDE")):
        result = classify_document(request(**values))
        assert result["hard_gate"]["state"] == state
        assert result["executed_layers"] == ["L0", "L1"]
        assert result["deeper_rule_evaluation_count"] == 0
        assert result["l5_call_count"] == 0
        assert result["projection_count"] == 0
        if state == "SECRET_EXCLUDE":
            assert result["preview_count"] == 0
            assert result["training_count"] == 0


def test_replay_identity_and_payload_are_stable_without_wall_clock(monkeypatch):
    payload = request(fixture_id="stable-replay", correlation_id="stable-correlation")
    first_identity = classifier_v2.logical_replay_identity(payload)
    first_time = classifier_v2.stable_observed_at(payload)
    first_result_hash = __import__("hashlib").sha256(str(classify_document(payload)).encode()).hexdigest()
    monkeypatch.setattr(classifier_v2, "datetime", __import__("datetime").datetime)
    second_identity = classifier_v2.logical_replay_identity(payload)
    second_time = classifier_v2.stable_observed_at(payload)
    second_result_hash = __import__("hashlib").sha256(str(classify_document(payload)).encode()).hexdigest()
    assert first_identity == second_identity
    assert first_time == second_time
    assert first_result_hash == second_result_hash


def test_phase5_health_and_classify_api(client):
    health = client.get("/api/phase5/health", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert health.status_code == 200, health.text
    assert health.json()["llm_real_content_mode"] == "DISABLED"
    payload = request().model_dump()
    response = client.post("/api/phase5/classify", json=payload, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["classification_envelope"]["status"] == "PENDING_REVIEW"
    assert body["shadow_state"] == "REVIEW_COMPARE_ONLY"
    queue = client.get("/api/phase5/review-queue?scope_type=PROJECT&scope_id=synthetic-project-001", headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert queue.status_code == 200, queue.text
    assert any(item["id"] == body["classification_envelope"]["id"] for item in queue.json()["items"])


def test_phase5_review_api_delegates_to_phase4_seam(client):
    payload = request().model_dump()
    created = client.post("/api/phase5/classify", json=payload, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert created.status_code == 200, created.text
    envelope = created.json()["classification_envelope"]
    decision = client.post("/api/phase5/review-decisions", json={
        "decision_id": f"phase5-decision-{time.time_ns()}",
        "classification_envelope_id": envelope["id"],
        "decision": "ACCEPT",
        "actor_id": "synthetic-ui-input",
        "capability": "PHASE4_REVIEW_DECISION",
        "scope_type": "PROJECT",
        "scope_id": "synthetic-project-001",
        "record_version": envelope["record_version"],
        "idempotency_key": f"phase5-key-{time.time_ns()}",
        "corrections_json": [],
    }, headers={"X-Dev-Role": "SYSTEM_ADMIN"})
    assert decision.status_code == 200, decision.text
    assert decision.json()["decision"] == "ACCEPT"
    assert decision.json()["history_policy"] == "APPEND_ONLY"
