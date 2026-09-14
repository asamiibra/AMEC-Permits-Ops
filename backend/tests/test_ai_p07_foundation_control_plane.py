from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.models import (
    AIExecutionLedger,
    AIWorkProduct,
    AIWorkProductDependency,
    AssertionStatus,
    Base,
    ContextDependency,
    IntelligenceInvalidation,
    IntelligenceReviewDecision,
    Role,
)
from backend.app.services.intelligence_contracts import IntelligenceContractError, create_ai_work_product
from backend.app.services.intelligence_foundation import (
    P07_CONTEXT_CHANGED,
    P07_RESERVATION_FENCE,
    P07_STALE_REPLAY,
    ReadOnlyToolRuntime,
    ToolContract,
    bind_work_product_dependencies,
    dependency_current,
    finalize_current_work_product,
    invalidate_dependency,
    promote_verified_assertion_from_decision,
    record_module_review_decision,
    replay_work_product,
    reservation_expired,
)


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'p07.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        session.rollback()
    engine.dispose()


def _ledger(db: Session, suffix: str = "1") -> AIExecutionLedger:
    ledger = AIExecutionLedger(
        idempotency_key=f"p07-ledger-{suffix}", correlation_id="p07-corr", auth_mode="TEST",
        purpose="p07", execution_mode="TEST", scope_type="PROJECT", scope_id="p07-project",
        target_entity_type="PROJECT", target_entity_id="p07-project", architecture_version="1",
        policy_version="p07", context_fingerprint="a" * 64, request_fingerprint="b" * 64,
        provider="NONE", provider_region="NONE", deployment_name="NONE", model_name="NONE",
        model_version="NONE", status="RECORDED", input_token_upper_bound=0,
        input_rate_usd_per_1m=0, output_rate_usd_per_1m=0, pricing_source_reference="test",
        reserved_cost_usd=0, citation_count=0, synthetic_only=True,
    )
    db.add(ledger)
    db.flush()
    return ledger


def _product(db: Session, *, key: str, dependency_id: str = "candidate-1") -> AIWorkProduct:
    ledger = _ledger(db, key)
    snapshot = __import__("backend.app.models", fromlist=["ContextSnapshot"]).ContextSnapshot(
        idempotency_key=f"snapshot-{key}", correlation_id="p07-corr", owning_module="proposal",
        scope_type="PROJECT", scope_id="p07-project", actor_persona="ENGINEERING",
        skill_id="skill", skill_version="1", skill_manifest_hash="c" * 64,
        context_schema_version="1", policy_version="p07", authorization_context_hash="d" * 64,
        context_hash="e" * 64, synthetic_only=True,
    )
    db.add(snapshot)
    db.flush()
    dep = ContextDependency(
        context_snapshot_id=snapshot.id, dependency_type="CANDIDATE_ASSERTION",
        dependency_id=dependency_id, dependency_version_or_hash="f" * 64,
        required=True, trust_state="CANDIDATE", currentness_state_at_capture="CURRENT",
        metadata_json={"source_key": "candidate"},
    )
    db.add(dep)
    db.flush()
    product = create_ai_work_product(db, {
        "idempotency_key": key, "correlation_id": "p07-corr", "execution_ledger_id": ledger.id,
        "context_snapshot_id": snapshot.id, "owning_module": "proposal", "skill_id": "skill",
        "skill_version": "1", "skill_manifest_hash": "c" * 64, "scope_type": "PROJECT",
        "scope_id": "p07-project", "target_entity_type": "PROJECT", "target_entity_id": "p07-project",
        "output_class": "ANALYSIS", "structured_output_json": {"candidate": True},
        "data_classification": "INTERNAL", "contains_sensitive_data": False,
    })
    return product


def test_selective_idempotent_invalidation_and_stale_replay_guard(db):
    first = _product(db, key="product-1")
    second = _product(db, key="product-2", dependency_id="candidate-2")
    bind_work_product_dependencies(db, first)
    bind_work_product_dependencies(db, second)
    assert invalidate_dependency(db, dependency_type="CANDIDATE_ASSERTION", dependency_id="candidate-1", source_event_id="event-1") == 1
    assert invalidate_dependency(db, dependency_type="CANDIDATE_ASSERTION", dependency_id="candidate-1", source_event_id="event-1") == 1
    assert first.state == "STALE"
    assert second.state == "CURRENT"
    assert db.scalar(select(IntelligenceInvalidation).where(IntelligenceInvalidation.work_product_id == first.id)).source_event_id == "event-1"
    with pytest.raises(IntelligenceContractError, match=P07_STALE_REPLAY):
        replay_work_product(db, idempotency_key="product-1")


def test_finalization_fence_records_context_change_and_preserves_history(db):
    product = _product(db, key="product-fence")
    bind_work_product_dependencies(db, product)
    dependency = db.scalar(select(ContextDependency).where(ContextDependency.context_snapshot_id == product.context_snapshot_id))
    dependency.currentness_state_at_capture = "STALE"
    with pytest.raises(IntelligenceContractError, match=P07_CONTEXT_CHANGED):
        finalize_current_work_product(db, work_product=product)
    assert product.state == "STALE"
    assert product.invalidation_count == 1
    assert db.scalar(select(IntelligenceInvalidation).where(IntelligenceInvalidation.work_product_id == product.id)) is not None


def test_lease_expiry_and_late_worker_fence(db):
    ledger = _ledger(db, "lease")
    ledger.status = "RESERVED"
    ledger.reservation_owner_token = "owner-a"
    ledger.reservation_generation = 1
    ledger.reservation_lease_expires_at = ledger.started_at - timedelta(seconds=1)
    assert reservation_expired(ledger)
    with pytest.raises(IntelligenceContractError, match=P07_RESERVATION_FENCE):
        from backend.app.services.intelligence_foundation import assert_reservation_fence
        assert_reservation_fence(ledger, owner_token="late-worker", generation=1)


def test_review_ledger_uses_authenticated_human_and_is_only_promotion_path(db):
    principal = AuthenticatedPrincipal(auth_mode="TEST", role=Role.SYSTEM_ADMIN, user_id="human-1")
    decision = record_module_review_decision(
        db, principal=principal, owning_module="proposal", review_subject_type="WORK_PRODUCT",
        review_subject_id="wp-1", decision="ACCEPT", idempotency_key="review-1", correlation_id="p07-corr",
        authorizing_capability="READ_ALL", precondition_version="source-v1",
    )
    assert decision.reviewer_user_id == "human-1"
    assert db.scalar(select(IntelligenceReviewDecision).where(IntelligenceReviewDecision.id == decision.id)) is not None
    with pytest.raises(IntelligenceContractError, match="INTELLIGENCE_REVIEW_CAPABILITY_DENIED"):
        record_module_review_decision(
            db, principal=AuthenticatedPrincipal(auth_mode="TEST", role=Role.RESPONSIBLE_ENGINEER, user_id="human-2"),
            owning_module="proposal", review_subject_type="WORK_PRODUCT", review_subject_id="wp-2",
            decision="ACCEPT", idempotency_key="review-2", correlation_id="p07-corr",
            authorizing_capability="MASTER_FORM_WRITE", precondition_version="source-v1",
        )


def test_tool_runtime_is_server_owned_bounded_and_read_only(db):
    runtime = ReadOnlyToolRuntime()
    runtime.register(ToolContract(
        tool_id="project.lookup", version="1", input_schema={"type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}, "additionalProperties": False},
        output_schema={"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}, "additionalProperties": False},
        allowed_modules=("proposal",), data_classification_ceiling="INTERNAL",
    ), lambda request: {"name": request["id"]})
    principal = AuthenticatedPrincipal(auth_mode="TEST", role=Role.SYSTEM_ADMIN, user_id="human-1")
    assert runtime.invoke(db, principal=principal, tool_id="project.lookup", version="1", request={"id": "p07"}, owning_module="proposal", skill_id="skill", correlation_id="p07-corr", idempotency_key="tool-1")["name"] == "p07"
    with pytest.raises(IntelligenceContractError, match="AI_TOOL_INPUT_SCHEMA_INVALID"):
        runtime.invoke(db, principal=principal, tool_id="project.lookup", version="1", request={"id": "p07", "extra": True}, owning_module="proposal", skill_id="skill", correlation_id="p07-corr", idempotency_key="tool-2")
    with pytest.raises(IntelligenceContractError, match="AI_TOOL_NOT_REGISTERED"):
        runtime.invoke(db, principal=principal, tool_id="project.mutate", version="1", request={}, owning_module="proposal", skill_id="skill", correlation_id="p07-corr", idempotency_key="tool-3")
    with pytest.raises(IntelligenceContractError, match="AI_TOOL_MUTATION_FORBIDDEN"):
        runtime.register(ToolContract(tool_id="project.mutate", version="1", input_schema={}, output_schema={}, read_only=False), lambda _: {})
