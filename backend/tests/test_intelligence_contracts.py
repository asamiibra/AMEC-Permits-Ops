from __future__ import annotations

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session

from backend.app.models import Base
from backend.app.models.ai_entities import AIExecutionLedger
from backend.app.models.intelligence_entities import (
    AIWorkProduct,
    CandidateAssertion,
    ContextDependency,
    ContextSnapshot,
    IntelligenceCitation,
)
from backend.app.services.intelligence_contracts import (
    IntelligenceContractError,
    build_skill_manifest,
    create_ai_work_product,
    create_candidate_assertion,
    create_context_snapshot,
    manifest_hash_for,
    record_context_dependency,
    record_intelligence_citation,
    stable_hash,
)


@pytest.fixture
def db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'intelligence.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
        session.rollback()
    engine.dispose()


def _ledger(db: Session) -> AIExecutionLedger:
    ledger = AIExecutionLedger(
        idempotency_key="ledger-1",
        correlation_id="corr-1",
        auth_mode="TEST",
        purpose="contract-test",
        execution_mode="TEST",
        scope_type="PROJECT",
        scope_id="project-1",
        target_entity_type="PROJECT",
        target_entity_id="project-1",
        architecture_version="1",
        policy_version="1",
        context_fingerprint="a" * 64,
        request_fingerprint="b" * 64,
        provider="NONE",
        provider_region="NONE",
        deployment_name="NONE",
        model_name="NONE",
        model_version="NONE",
        status="RECORDED",
        input_token_upper_bound=0,
        input_rate_usd_per_1m=0,
        output_rate_usd_per_1m=0,
        pricing_source_reference="test",
        reserved_cost_usd=0,
        citation_count=0,
        synthetic_only=True,
    )
    db.add(ledger)
    db.flush()
    return ledger


def _snapshot(db: Session) -> ContextSnapshot:
    snapshot = create_context_snapshot(db, {
        "idempotency_key": "context-1",
        "correlation_id": "corr-1",
        "owning_module": "proposal",
        "scope_type": "PROJECT",
        "scope_id": "project-1",
        "actor_persona": "ENGINEER",
        "skill_id": "proposal.skill",
        "skill_version": "1.0",
        "skill_manifest_hash": "c" * 64,
        "context_schema_version": "1",
        "policy_version": "1",
        "authorization_context_hash": "d" * 64,
        "synthetic_only": True,
    })
    return snapshot


def _candidate_payload(value="10"):
    return {
        "idempotency_key": "candidate-1",
        "correlation_id": "corr-1",
        "scope_type": "PROJECT",
        "scope_id": "project-1",
        "subject_type": "PROJECT",
        "subject_id": "project-1",
        "assertion_code": "plot.area",
        "value_json": {"value": value},
        "producer_kind": "RULE",
        "producer_version": "1",
        "producer_hash": "e" * 64,
        "data_classification": "INTERNAL",
        "contains_sensitive_data": False,
    }


def test_schema_contracts_and_indexes():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    inspector = inspect(engine)
    assert {column["name"] for column in inspector.get_columns("candidate_assertions")} >= {
        "idempotency_key", "value_hash", "status", "promoted_verified_assertion_id"
    }
    assert any(index["name"] == "ix_context_dependency_type_id" for index in inspector.get_indexes("context_dependencies"))
    assert any(index["name"] == "ix_ai_ledger_scope_started" for index in inspector.get_indexes("ai_execution_ledger"))
    assert any(
        constraint["name"] == "uq_intelligence_citation_ordinal"
        for constraint in inspector.get_unique_constraints("intelligence_citations")
    )
    engine.dispose()


def test_candidate_is_candidate_only_and_idempotent(db):
    first = create_candidate_assertion(db, _candidate_payload())
    second = create_candidate_assertion(db, _candidate_payload())
    assert first.id == second.id
    assert first.status == "CURRENT"
    assert first.promoted_verified_assertion_id is None
    with pytest.raises(IntelligenceContractError, match="INTELLIGENCE_IDEMPOTENCY_KEY_REUSE_MISMATCH"):
        create_candidate_assertion(db, {**_candidate_payload(), "value_json": {"value": "11"}})
    with pytest.raises(IntelligenceContractError, match="INTELLIGENCE_PROMOTION_REQUIRES_EXPLICIT_REFERENCE"):
        create_candidate_assertion(db, {**_candidate_payload(), "idempotency_key": "candidate-2", "status": "PROMOTED"})


def test_context_hash_is_stable_and_dependencies_are_metadata_only(db):
    one = _snapshot(db)
    two = create_context_snapshot(db, {
        "idempotency_key": "context-1",
        "correlation_id": "corr-1",
        "owning_module": "proposal",
        "scope_type": "PROJECT",
        "scope_id": "project-1",
        "actor_persona": "ENGINEER",
        "skill_id": "proposal.skill",
        "skill_version": "1.0",
        "skill_manifest_hash": "c" * 64,
        "context_schema_version": "1",
        "policy_version": "1",
        "authorization_context_hash": "d" * 64,
        "synthetic_only": True,
    })
    assert one.id == two.id
    assert stable_hash({"b": 2, "a": 1}) == stable_hash({"a": 1, "b": 2})
    dependency_payload = {
        "context_snapshot_id": one.id,
        "dependency_type": "DOCUMENT_VERSION",
        "dependency_id": "document-version-1",
        "dependency_version_or_hash": "f" * 64,
        "required": True,
        "trust_state": "VERIFIED",
        "currentness_state_at_capture": "CURRENT",
        "metadata_json": {"page": 2},
    }
    first = record_context_dependency(db, dependency_payload)
    second = record_context_dependency(db, dependency_payload)
    assert first.id == second.id
    assert one.dependency_count == 1
    with pytest.raises(IntelligenceContractError, match="INTELLIGENCE_DEPENDENCY_RAW_CONTENT_FORBIDDEN"):
        record_context_dependency(db, {**dependency_payload, "dependency_id": "bad", "metadata_json": {"raw": "bytes"}})


def test_work_product_output_classes_and_citations(db):
    ledger = _ledger(db)
    snapshot = _snapshot(db)
    payload = {
        "idempotency_key": "work-1",
        "correlation_id": "corr-1",
        "execution_ledger_id": ledger.id,
        "context_snapshot_id": snapshot.id,
        "owning_module": "proposal",
        "skill_id": "proposal.skill",
        "skill_version": "1.0",
        "skill_manifest_hash": "c" * 64,
        "scope_type": "PROJECT",
        "scope_id": "project-1",
        "target_entity_type": "PROJECT",
        "target_entity_id": "project-1",
        "output_class": "ANALYSIS",
        "structured_output_json": {"finding": "candidate"},
        "data_classification": "INTERNAL",
        "contains_sensitive_data": False,
    }
    product = create_ai_work_product(db, payload)
    assert product.output_hash == stable_hash(payload["structured_output_json"])
    assert create_ai_work_product(db, payload).id == product.id
    citation = record_intelligence_citation(db, {
        "work_product_id": product.id,
        "ordinal": 1,
        "source_type": "DOCUMENT_VERSION",
        "source_id": "document-version-1",
        "source_version_or_hash": "f" * 64,
        "locator_json": {"page": 2},
    })
    assert record_intelligence_citation(db, {
        "work_product_id": product.id,
        "ordinal": 1,
        "source_type": "DOCUMENT_VERSION",
        "source_id": "document-version-1",
        "source_version_or_hash": "f" * 64,
        "locator_json": {"page": 2},
    }).id == citation.id
    with pytest.raises(IntelligenceContractError, match="INTELLIGENCE_IDEMPOTENCY_KEY_REUSE_MISMATCH"):
        record_intelligence_citation(db, {
            "work_product_id": product.id, "ordinal": 1, "source_type": "DOCUMENT_VERSION",
            "source_id": "other", "source_version_or_hash": "f" * 64, "locator_json": {"page": 2},
        })
    with pytest.raises(IntelligenceContractError, match="INTELLIGENCE_OUTPUT_CLASS_UNSUPPORTED"):
        create_ai_work_product(db, {**payload, "idempotency_key": "work-2", "output_class": "APPROVED"})
    with pytest.raises(IntelligenceContractError, match="INTELLIGENCE_PROTECTED_SIDE_EFFECT_FORBIDDEN"):
        create_ai_work_product(db, {**payload, "idempotency_key": "work-3", "approved": True})


def test_skill_manifest_is_deterministic_and_has_no_authority():
    values = {
        "skill_id": "proposal.skill", "version": "1.0", "owning_module": "proposal",
        "input_schema_version": "1", "output_schema_version": "1",
        "allowed_scope_types": ["PROJECT"], "allowed_context_types": ["DOCUMENT_VERSION"],
        "input_trust_floor": "VERIFIED", "allowed_tools": [], "model_policy": {"provider": "NONE"},
        "output_class": "ANALYSIS", "review_trigger": "ALWAYS", "dependency_capture": {"required": True},
        "invalidation": {"on": ["DOCUMENT_VERSION"]}, "eval_pack_version": "1",
    }
    manifest = build_skill_manifest(**values)
    assert manifest.manifest_hash == manifest_hash_for(manifest)
    assert build_skill_manifest(**values).manifest_hash == manifest.manifest_hash
    with pytest.raises(ValidationError, match="INTELLIGENCE_CANONICAL_WRITE_AUTHORITY_FORBIDDEN"):
        build_skill_manifest(**{**values, "canonical_or_protected_authority": "CANONICAL"})
