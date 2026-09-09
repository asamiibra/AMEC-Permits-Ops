import json
from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import HTTPException

from backend.app.ai import orchestration
from backend.app.ai.contracts import AIContextItem, AIContextManifest, AIContextScope, AIExecutionMode, AIPurpose, AITargetEntityType
from backend.app.ai.provider import AIProviderRequest, AIProviderResult, AIProviderUsage, AzureOpenAIResponsesProvider
from backend.app.ai.structured_output import PROVIDER_JSON_SCHEMA, validate_draft
from backend.app.api.dependencies import AuthenticatedPrincipal
from backend.app.config.settings import Settings
from backend.app.db import SessionLocal
from backend.app.models import AIExecutionLedger, Role
from backend.app.services.governed_retrieval import RetrievalCitation


def _settings() -> Settings:
    return Settings(
        app_env="TEST", synthetic_only=True, real_data_allowed=False, ai_feature_enabled=True,
        ai_external_inference_enabled=True, ai_d4_commissioning_id="d4-test-commissioning",
        ai_uami_client_id="11111111-1111-4111-8111-111111111111",
        ai_uami_principal_id="22222222-2222-4222-8222-222222222222",
        ai_azure_tenant_id="33333333-3333-4333-8333-333333333333",
        ai_d3_synthetic_project_ids="project-1", ai_input_price_usd_per_1m_tokens=1,
        ai_output_price_usd_per_1m_tokens=1, ai_pricing_source_reference="test-price-reference",
        ai_max_input_token_upper_bound=24000, ai_max_output_tokens=6000,
        ai_max_requests_per_user_per_minute=3, ai_max_requests_per_user_per_hour=20,
        ai_max_requests_per_project_per_hour=20, ai_max_requests_global_per_hour=60,
        ai_max_estimated_cost_usd_per_request=0.25, ai_max_estimated_cost_usd_per_day=5.0,
        ai_azure_openai_endpoint="https://proposalops.openai.azure.com",
    )


def _manifest() -> AIContextManifest:
    items = tuple(
        AIContextItem(
            canonical_domain="MASTER_CONTENT", canonical_entity_type="MasterContentItem", canonical_entity_id=f"content-{index}",
            content=f"Synthetic engineering evidence {index}.", verification_state="VERIFIED_CURRENT",
            citation=RetrievalCitation(canonical_domain="MASTER_CONTENT", canonical_entity_type="MasterContentItem", canonical_entity_id=f"content-{index}", locator=f"DocumentVersion:{index}"),
        ) for index in (1, 2)
    )
    return AIContextManifest(purpose=AIPurpose.ENGINEERING_TECHNICAL_DRAFT, execution_mode=AIExecutionMode.INTERACTIVE, scope=AIContextScope(project_id="project-1", target_entity_type=AITargetEntityType.PROJECT, target_entity_id="project-1"), policy={"purpose_id": AIPurpose.ENGINEERING_TECHNICAL_DRAFT, "required_capabilities": ("ENGINEERING_PROJECT_READ",)}, retrieval_contract_version="1.0", items=items, manifest_fingerprint="f" * 64)


def _payload():
    return {"draft_title": "Synthetic methodology", "sections": [{"heading": "Scope", "body": "The supplied engineering evidence defines the review scope.", "citation_keys": ["CIT-001"]}, {"heading": "Approach", "body": "Use the supplied evidence as the starting point for human review.", "citation_keys": ["CIT-002"]}], "assumptions": [{"statement": "The evidence is the complete commissioning sample.", "basis": "SOURCE_GROUNDED", "citation_keys": ["CIT-001"]}], "open_questions": ["Which discipline owner confirms the final methodology?"], "limitations": ["This is not professional approval."], "source_coverage_note": "Two synthetic governed items were supplied.", "draft_only": True}


def test_provider_request_is_exact_v1_responses_without_tools_or_redirects():
    captured = {}

    class Response:
        status_code = 200
        def json(self):
            return {"id": "resp-1", "status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": json.dumps(_payload())}]}], "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}}

    class Client:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def post(self, url, **kwargs):
            captured["url"] = url; captured["request"] = kwargs; return Response()

    provider = AzureOpenAIResponsesProvider(_settings(), token_provider=lambda _: "memory-token", http_client_factory=Client)
    result = provider.execute_structured(AIProviderRequest(provider_input="static-input", max_output_tokens=6000))
    assert result.response_id == "resp-1"
    assert captured["url"].endswith("/openai/v1/responses")
    assert captured["client"]["follow_redirects"] is False
    body = captured["request"]["json"]
    assert body["model"] == "d3-gpt54mini-20260317"
    assert body["store"] is False
    assert body["tools"] == []
    assert "previous_response_id" not in body and "conversation" not in body
    assert body["text"]["format"]["strict"] is True


def test_structured_output_rejects_missing_section_citation():
    payload = _payload()
    payload["sections"][0]["citation_keys"] = []
    with pytest.raises(Exception):
        validate_draft(payload)


def test_d3_provider_phase_has_no_active_request_session(monkeypatch):
    settings = _settings()
    manifest = _manifest()
    request_db = SessionLocal()
    observed = {}

    class FakeProvider:
        def execute_structured(self, request: AIProviderRequest):
            observed["transaction"] = request_db.in_transaction()
            return AIProviderResult("resp-test", _payload(), AIProviderUsage(10, 20, 30))

    monkeypatch.setattr(orchestration, "build_context_manifest", lambda *args, **kwargs: manifest)
    principal = AuthenticatedPrincipal(auth_mode="DEV_HEADER", role=Role.SYSTEM_ADMIN)
    try:
        result = orchestration.execute_technical_methodology(request_db, principal, settings=settings, project_id="project-1", client_request_id=str(uuid4()), correlation_id="correlation-test", provider=FakeProvider())
        assert result["status"] == "DRAFT_ONLY"
        assert observed["transaction"] is False
    finally:
        request_db.close()


def test_d3_insufficient_context_never_calls_provider(monkeypatch):
    settings = _settings()
    manifest = _manifest().model_copy(update={"items": (_manifest().items[0],)})
    monkeypatch.setattr(orchestration, "build_context_manifest", lambda *args, **kwargs: manifest)
    called = {"value": False}

    class FakeProvider:
        def execute_structured(self, request):
            called["value"] = True
            raise AssertionError("provider must not be called")

    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as error:
            orchestration.execute_technical_methodology(db, AuthenticatedPrincipal(auth_mode="DEV_HEADER", role=Role.SYSTEM_ADMIN), settings=settings, project_id="project-1", client_request_id=str(uuid4()), correlation_id="correlation-test", provider=FakeProvider())
        assert error.value.detail == {"code": "AI_D3_INSUFFICIENT_GOVERNED_CONTEXT"}
        assert called["value"] is False
    finally:
        db.close()


def test_feature_enabled_external_inference_disabled_stops_before_retrieval_ledger_or_provider(monkeypatch):
    settings = Settings(app_env="TEST", synthetic_only=True, ai_feature_enabled=True, ai_external_inference_enabled=False)
    monkeypatch.setattr(orchestration, "build_context_manifest", lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("retrieval must not run")))

    class ForbiddenProvider:
        def execute_structured(self, request):
            raise AssertionError("provider must not run")

    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as error:
            orchestration.execute_technical_methodology(
                db, AuthenticatedPrincipal(auth_mode="DEV_HEADER", role=Role.SYSTEM_ADMIN),
                settings=settings, project_id="project-1", client_request_id=str(uuid4()),
                correlation_id="two-gate-test", provider=ForbiddenProvider(),
            )
        assert error.value.detail == {"code": "AI_EXTERNAL_INFERENCE_DISABLED"}
    finally:
        db.close()
