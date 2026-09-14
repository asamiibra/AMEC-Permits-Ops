from sqlalchemy import func, select

from backend.app.db import SessionLocal
from backend.app.models import OwnerDecision, OwnerDecisionHistory
from backend.app.services.owner_decisions import AUTHORITATIVE_SEVERITY_MATRIX, BLOCKING_LEVELS, CONDITIONAL_SEVERITY_KEYS, conditional_severity_evaluation, ensure_register


def test_owner_decision_register_is_canonical_and_truthful(client):
    response = client.get("/api/owner-decisions")
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] == 50
    assert payload["duplicate_key_count"] == 0
    assert {len(group["items"]) for group in payload["groups"]} == {3, 8, 11, 12, 16}
    assert payload["go_live"]["overall"] == "BLOCKED"
    assert payload["truth_tokens"]["OWNER_DECISION_CANONICAL_COUNT_50"] is True
    assert payload["truth_tokens"]["SAFE_DEFAULT_FALSE_CONFIRMATION_ZERO"] is True
    assert payload["truth_tokens"]["OWNER_DECISION_RUNTIME_MISMATCH_ZERO"] is True
    assert payload["truth_tokens"]["OWNER_DECISION_INVALID_BLOCKING_LEVEL_ZERO"] is True
    assert all(item["blocking_level"] in BLOCKING_LEVELS for item in payload["items"])
    assert {item["key"] for item in payload["items"] if item["blocking_level"] == "P0_GO_LIVE_BLOCKER"} >= {
        "OFFICIAL_PROPOSAL_TEMPLATE",
        "OFFICIAL_PROPOSAL_CHECKLIST",
        "PROPOSAL_ACCEPT_REQUIRED_FIELDS",
        "PROPOSAL_ACCEPT_AUTHORITY",
        "PROPOSAL_TO_CONTRACT_POLICY",
    }
    assert next(item for item in payload["items"] if item["key"] == "PROPOSAL_OUTPUT_FORMAT_POLICY")["proposed_default"] == "PDF"
    actual = {item["key"]: item["blocking_level"] for item in payload["items"]}
    assert set(actual) == set(AUTHORITATIVE_SEVERITY_MATRIX) | CONDITIONAL_SEVERITY_KEYS
    assert {key: actual[key] for key in AUTHORITATIVE_SEVERITY_MATRIX} == AUTHORITATIVE_SEVERITY_MATRIX
    assert {actual[key] for key in CONDITIONAL_SEVERITY_KEYS} == {"P0_GO_LIVE_BLOCKER"}
    assert payload["truth_tokens"]["OWNER_DECISION_UNCONDITIONAL_SEVERITY_MISMATCH_COUNT"] == 0
    assert payload["truth_tokens"]["OWNER_DECISION_CONDITIONAL_SEVERITY_RULES"] == "PASS"
    assert payload["truth_tokens"]["OWNER_DECISION_RUNTIME_MISMATCH_COUNT"] == 0
    assert payload["truth_tokens"]["OWNER_DECISION_CONTRADICTION_COUNT"] == 0
    assert payload["owner_action_required"]
    assert any(row["key"] == "CONTRACT_REQUIRED_FIELDS" for row in payload["owner_action_required"])
    assert any(row["key"] == "FULL_OWNER_LIFECYCLE_E2E" for row in payload["software_readiness"])
    assert all(row["status"] != "READY" for row in payload["content_readiness"])


def test_owner_decision_conditional_matrix_covers_dependency_states():
    values = {spec["key"]: spec["default"] for spec in __import__("backend.app.services.owner_decisions", fromlist=["DECISION_SPECS"]).DECISION_SPECS}
    result = conditional_severity_evaluation(values)
    assert result["status"] == "PASS"
    assert result["current"]["OFFICIAL_CONTRACT_TEMPLATE"]["level"] == "P0_GO_LIVE_BLOCKER"
    assert result["scenarios"]["upload_only"]["official_template_not_applicable"] is True
    assert result["scenarios"]["authority_gate_absent"]["authority_review_requires_explicit_applicability"] is True
    assert result["scenarios"]["activation_artifact_dependency"]["artifact_strategy_p1_without_activation_dependency"] is True


def test_owner_decision_spec_reconciliation_preserves_history():
    with SessionLocal() as db:
        item = db.scalar(select(OwnerDecision).where(OwnerDecision.decision_key == "PROPOSAL_OUTPUT_FORMAT_POLICY"))
        item.blocking_level = "P2_SAFE_DEFAULT"
        item.proposed_default_json = ["PDF", "DOCX"]
        db.commit()
        ensure_register(db)
        db.commit()
        refreshed = db.scalar(select(OwnerDecision).where(OwnerDecision.decision_key == "PROPOSAL_OUTPUT_FORMAT_POLICY"))
        history = db.scalars(select(OwnerDecisionHistory).where(OwnerDecisionHistory.decision_key == "PROPOSAL_OUTPUT_FORMAT_POLICY", OwnerDecisionHistory.event_type == "SPEC_RECONCILED")).all()
        assert refreshed.blocking_level == "P2_SAFE_DEFAULT_AVAILABLE"
        assert refreshed.proposed_default_json == "PDF"
        assert history
        assert history[-1].before_json["status"] == refreshed.status


def test_owner_decision_authority_and_technical_fact_protection(client):
    assert client.post("/api/owner-decisions/PROPOSAL_TO_CONTRACT_POLICY/actions", headers={"X-Dev-Role": "RESPONSIBLE_ENGINEER"}, json={"action": "confirm_default"}).status_code == 403
    assert client.post("/api/owner-decisions/REAL_SYNOLOGY_CONNECTION/actions", headers={"X-Dev-Role": "OWNER_SPONSOR"}, json={"action": "confirm_default"}).status_code == 409


def test_owner_decision_history_runtime_readback_and_apply_failure(client):
    confirmed = client.post("/api/owner-decisions/MASTER_CATEGORY_SEMANTICS/actions", headers={"X-Dev-Role": "OWNER_SPONSOR"}, json={"action": "confirm_default", "notes": "Synthetic test confirmation"})
    assert confirmed.status_code == 200
    assert confirmed.json()["runtime"]["apply_state"] == "APPLIED"
    assert confirmed.json()["status"] == "OWNER_CONFIRMED_WITH_NOTES"
    failed = client.post("/api/owner-decisions/PROPOSAL_REFERENCE_POLICY/actions", headers={"X-Dev-Role": "OWNER_SPONSOR", "X-Test-Force-Apply-Failure": "true"}, json={"action": "confirm_default"})
    assert failed.status_code == 200
    assert failed.json()["runtime"]["apply_state"] == "APPLY_FAILED"
    assert failed.json()["runtime"]["value"] is None
    reopened = client.post("/api/owner-decisions/MASTER_CATEGORY_SEMANTICS/actions", headers={"X-Dev-Role": "OWNER_SPONSOR"}, json={"action": "reopen", "notes": "Reopened for review"})
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "REOPENED"
    with SessionLocal() as db:
        assert db.scalar(select(func.count(OwnerDecisionHistory.id)).where(OwnerDecisionHistory.decision_key == "MASTER_CATEGORY_SEMANTICS")) >= 3
