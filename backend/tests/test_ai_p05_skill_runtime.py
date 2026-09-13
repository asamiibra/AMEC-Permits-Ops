from __future__ import annotations

import json
import threading
import time

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from backend.app.ai.provider import AIProviderResult, AIProviderUsage
from backend.app.ai.gateway import ModelGateway
from backend.app.ai.skill_registry import COMPATIBILITY_SKILL, SkillRegistry
from backend.app.ai.skill_runtime import RuntimeDependencies, SkillExecutionRequest, SkillRuntime
from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.config.settings import Settings
from backend.app.models import AIExecutionLedger, AIWorkProduct, ConsultancyOffice, Project, Role, User
from backend.app.models import Base, ContextDependency, ContextSnapshot, IntelligenceCitation


def _settings() -> Settings:
    return Settings(
        app_env="TEST",
        synthetic_only=True,
        real_data_allowed=False,
        ai_feature_enabled=True,
        ai_external_inference_enabled=True,
        ai_d4_commissioning_id="p05-test-commissioning",
        ai_azure_openai_endpoint="https://proposalops.openai.azure.com",
        ai_azure_openai_region="eastus",
        ai_azure_openai_deployment_type="DataZoneStandard",
        ai_max_context_items=8,
        ai_max_context_utf8_bytes=16384,
        ai_max_input_token_upper_bound=24000,
        ai_max_output_tokens=6000,
        ai_max_requests_per_user_per_minute=20,
        ai_max_requests_per_user_per_hour=100,
        ai_max_requests_per_project_per_hour=100,
        ai_max_requests_global_per_hour=100,
        ai_max_estimated_cost_usd_per_request=1,
        ai_max_estimated_cost_usd_per_day=10,
        ai_input_price_usd_per_1m_tokens=1,
        ai_output_price_usd_per_1m_tokens=1,
        ai_pricing_source_reference="p05-test-price",
    )


def _payload():
    return {
        "draft_title": "Synthetic methodology",
        "sections": [
            {"heading": "Scope", "body": "Review the governed projection.", "citation_keys": ["CIT-001"]},
            {"heading": "Approach", "body": "Use only the supplied context.", "citation_keys": ["CIT-001"]},
        ],
        "assumptions": [],
        "open_questions": [],
        "limitations": ["Human review remains required."],
        "source_coverage_note": "One synthetic governed projection.",
        "draft_only": True,
    }


class FakeProvider:
    def __init__(self, payload=None, error=None):
        self.calls = 0
        self.payload = payload or _payload()
        self.error = error

    def execute_structured(self, request):
        self.calls += 1
        if self.error:
            raise self.error
        return AIProviderResult("p05-response", self.payload, AIProviderUsage(10, 20, 30))


@pytest.fixture
def runtime_db(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'p05-runtime.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        office = ConsultancyOffice(id="p05-office", office_code="P05", name_en="P05", name_ar="P05")
        project = Project(
            id="p05-project",
            project_number="P05-001",
            project_name="Synthetic P05 Project",
            office_id=office.id,
            workstream="PERMIT",
            status="ACTIVE",
            municipality="Doha",
            permit_type="BUILDING",
            project_code="SYNTHETIC-P05",
        )
        user = User(id="p05-user", email="p05@example.test", display_name="P05", role=Role.SYSTEM_ADMIN, office_id=office.id, active=True)
        db.add_all([office, project, user])
        db.commit()
    yield factory
    engine.dispose()


def _request(**overrides):
    values = {
        "idempotency_key": "p05-request-1",
        "correlation_id": "p05-correlation",
        "skill_id": COMPATIBILITY_SKILL.manifest.skill_id,
        "skill_version": COMPATIBILITY_SKILL.manifest.version,
        "skill_manifest_hash": COMPATIBILITY_SKILL.manifest.manifest_hash,
        "purpose": "ENGINEERING_TECHNICAL_DRAFT",
        "execution_mode": "INTERACTIVE",
        "scope_type": "PROJECT",
        "scope_id": "p05-project",
        "project_id": "p05-project",
        "target_entity_type": "PROJECT",
        "target_entity_id": "p05-project",
        "context_schema_version": "p05-context-v1",
        "policy_version": "ENGINEERING_TECHNICAL_DRAFT-1.0",
        "sources": ({"key": "project", "context_type": "DOMAIN_ENTITY_REVISION", "selector": {"entity_type": "PROJECT", "entity_id": "p05-project"}},),
    }
    values.update(overrides)
    return SkillExecutionRequest(**values)


def _principal():
    return AuthenticatedPrincipal(auth_mode="DEV_HEADER", role=Role.SYSTEM_ADMIN, user_id="p05-user", office_id="p05-office")


def _runtime(factory):
    return SkillRuntime(dependencies=RuntimeDependencies(session_factory=factory))


def test_registry_exact_identity_and_fail_closed_conflicts():
    registry = SkillRegistry((COMPATIBILITY_SKILL,))
    assert registry.resolve(*COMPATIBILITY_SKILL.identity) == COMPATIBILITY_SKILL
    with pytest.raises(Exception, match="AI_SKILL_MANIFEST_HASH_MISMATCH"):
        registry.resolve(COMPATIBILITY_SKILL.manifest.skill_id, COMPATIBILITY_SKILL.manifest.version, "0" * 64)


def test_gateway_forwards_server_registered_schema_without_client_schema():
    captured = {}

    class Provider:
        def execute_structured(self, request):
            captured["request"] = request
            return AIProviderResult("response", _payload(), AIProviderUsage(1, 1, 2))

    ModelGateway(_settings(), provider=Provider()).execute(
        COMPATIBILITY_SKILL,
        provider_input="bounded-p04-projection",
        max_output_tokens=100,
    )
    assert captured["request"].schema_name == "technical_methodology_draft"
    assert captured["request"].response_schema is not None
    assert captured["request"].tools == ()


def test_success_persists_exact_snapshot_product_citations_and_replays(runtime_db):
    provider = FakeProvider()
    runtime = _runtime(runtime_db)
    with runtime_db() as db:
        first = runtime.execute(db, _principal(), _request(), settings=_settings(), provider=provider)
        second = runtime.execute(db, _principal(), _request(), settings=_settings(), provider=provider)
        assert first["status"] == "SUCCEEDED"
        assert second["replayed"] is True
        assert provider.calls == 1
        assert db.scalar(select(func.count()).select_from(AIExecutionLedger)) == 1
        assert db.scalar(select(func.count()).select_from(AIWorkProduct)) == 1
        product = db.scalar(select(AIWorkProduct))
        assert product.context_snapshot_id == first["context_snapshot_id"]
        assert product.skill_manifest_hash == COMPATIBILITY_SKILL.manifest.manifest_hash
        assert product.citation_count == 1
        assert db.scalar(select(func.count()).select_from(IntelligenceCitation)) == 1
        assert db.scalar(select(ContextSnapshot).where(ContextSnapshot.id == product.context_snapshot_id)) is not None
        assert db.scalar(select(ContextDependency).where(ContextDependency.context_snapshot_id == product.context_snapshot_id)) is not None


def test_mutated_same_key_is_conflict_and_failed_retry_requires_new_key(runtime_db):
    runtime = _runtime(runtime_db)
    with runtime_db() as db:
        runtime.execute(db, _principal(), _request(), settings=_settings(), provider=FakeProvider())
        with pytest.raises(Exception, match="AI_IDEMPOTENCY_CONFLICT"):
            runtime.execute(db, _principal(), _request(context_schema_version="p05-context-v2"), settings=_settings(), provider=FakeProvider())
    failing = FakeProvider(error=Exception("timeout"))
    with runtime_db() as db:
        with pytest.raises(Exception, match="AI_PROVIDER_RESPONSE_INVALID"):
            runtime.execute(db, _principal(), _request(idempotency_key="p05-failed"), settings=_settings(), provider=failing)
        assert db.scalar(select(AIWorkProduct).where(AIWorkProduct.idempotency_key == "work-product:p05-failed")) is None
        with pytest.raises(Exception, match="AI_REQUEST_RETRY_REQUIRES_NEW_KEY"):
            runtime.execute(db, _principal(), _request(idempotency_key="p05-failed"), settings=_settings(), provider=FakeProvider())


def test_gateway_gates_and_strict_output_fail_before_work_product(runtime_db):
    runtime = _runtime(runtime_db)
    disabled = _settings().model_copy(update={"ai_external_inference_enabled": False})
    with runtime_db() as db:
        with pytest.raises(Exception, match="AI_EXTERNAL_INFERENCE_DISABLED"):
            runtime.execute(db, _principal(), _request(idempotency_key="p05-disabled"), settings=disabled, provider=FakeProvider())
    bad = dict(_payload())
    bad["unexpected"] = "not allowed"
    with runtime_db() as db:
        with pytest.raises(Exception, match="AI_STRUCTURED_OUTPUT_VALIDATION_FAILED"):
            runtime.execute(db, _principal(), _request(idempotency_key="p05-bad-output"), settings=_settings(), provider=FakeProvider(payload=bad))
        assert db.scalar(select(AIWorkProduct).where(AIWorkProduct.idempotency_key == "work-product:p05-bad-output")) is None


def test_unknown_citation_and_real_content_are_rejected(runtime_db):
    bad = _payload()
    bad["sections"][0]["citation_keys"] = ["CIT-999"]
    runtime = _runtime(runtime_db)
    with runtime_db() as db:
        with pytest.raises(Exception, match="AI_CITATION_VALIDATION_FAILED"):
            runtime.execute(db, _principal(), _request(idempotency_key="p05-citation"), settings=_settings(), provider=FakeProvider(payload=bad))
    real_settings = _settings().model_copy(update={"real_data_allowed": True})
    with runtime_db() as db:
        with pytest.raises(Exception, match="AI_REAL_CONTENT_NOT_AUTHORIZED"):
            runtime.execute(db, _principal(), _request(idempotency_key="p05-real"), settings=real_settings, provider=FakeProvider())


def test_same_key_race_executes_provider_once_and_creates_one_product(runtime_db, monkeypatch):
    import backend.app.ai.skill_runtime as skill_runtime_module

    with runtime_db() as db:
        compiled = skill_runtime_module.compile_context(
            db,
            {
                "correlation_id": "p05-race-context",
                "actor_user_id": "p05-user",
                "scope_type": "PROJECT",
                "scope_id": "p05-project",
                "project_id": "p05-project",
                "context_schema_version": "p05-context-v1",
                "policy_version": "ENGINEERING_TECHNICAL_DRAFT-1.0",
                "skill_manifest": COMPATIBILITY_SKILL.manifest,
                "sources": [{"key": "project", "context_type": "DOMAIN_ENTITY_REVISION", "selector": {"entity_type": "PROJECT", "entity_id": "p05-project"}}],
            },
        )
        db.commit()

    monkeypatch.setattr(skill_runtime_module, "compile_context", lambda *args, **kwargs: compiled)
    provider = FakeProvider()
    original_execute = provider.execute_structured

    def delayed_execute(request):
        result = original_execute(request)
        time.sleep(0.2)
        return result

    provider.execute_structured = delayed_execute
    runtime = _runtime(runtime_db)
    outcomes = []

    def run_one():
        try:
            with runtime_db() as db:
                outcomes.append(runtime.execute(db, _principal(), _request(idempotency_key="p05-race"), settings=_settings(), provider=provider))
        except Exception as exc:
            outcomes.append(exc)

    threads = [threading.Thread(target=run_one) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert provider.calls == 1
    assert sum(isinstance(outcome, dict) and outcome["status"] == "SUCCEEDED" for outcome in outcomes) == 1
    assert any("AI_REQUEST_IN_PROGRESS" in str(outcome) for outcome in outcomes if isinstance(outcome, Exception))
    with runtime_db() as db:
        assert db.scalar(select(func.count()).select_from(AIExecutionLedger)) == 1
        assert db.scalar(select(func.count()).select_from(AIWorkProduct)) == 1
