import base64
import json
from uuid import uuid4

import pytest

from backend.app.ai.identity import acquire_foundry_project_token
from backend.app.ai.provider import AIProviderRequest, FoundryProjectInstantResponsesProvider
from backend.app.ai.contracts import AI_SYNTHETIC_COMMISSIONING
from backend.app.config.settings import Settings
from backend.app.ai.errors import AIError


def _payload():
    return {
        "draft_title": "Synthetic methodology",
        "sections": [
            {"heading": "Scope", "body": "Evidence defines the review scope.", "citation_keys": ["CIT-001"]},
            {"heading": "Approach", "body": "Use evidence for human review.", "citation_keys": ["CIT-002"]},
        ],
        "assumptions": [{"statement": "The sample is complete.", "basis": "SOURCE_GROUNDED", "citation_keys": ["CIT-001"]}],
        "open_questions": ["Which owner confirms the final methodology?"],
        "limitations": ["This is not professional approval."],
        "source_coverage_note": "Synthetic evidence only.",
        "draft_only": True,
    }


def _settings(**overrides):
    values = {
        "app_env": "TEST",
        "synthetic_only": True,
        "real_data_allowed": False,
        "ai_enabled": True,
        "ai_provider_mode": "FOUNDRY_PROJECT_INSTANT_SYNTHETIC",
        "ai_d3_synthetic_project_ids": "project-1",
        "ai_input_price_usd_per_1m_tokens": 1,
        "ai_output_price_usd_per_1m_tokens": 1,
        "ai_pricing_source_reference": "test-price-reference",
        "ai_foundry_project_endpoint": "https://resource.services.ai.azure.com/api/projects/project-1",
        "ai_foundry_project_region": "westus3",
        "ai_instant_model_id": "gpt-5-mini-2025-08-07",
        "ai_instant_model_version": "2025-08-07",
        "ai_uami_client_id": "82c84649-7009-4cdd-bcb4-25f4c9d9d413",
        "ai_uami_principal_id": "a3e42c81-271a-4409-acdc-3e0881c7e1b5",
        "ai_azure_tenant_id": "2a82f16d-87fa-4036-97a9-17d94060eddd",
    }
    values.update(overrides)
    return Settings(**values)


def _jwt(payload):
    def part(value):
        return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip("=")
    return f"{part({'alg': 'none'})}.{part(payload)}.signature"


def test_commissioning_contract_is_explicit_and_fail_closed():
    assert AI_SYNTHETIC_COMMISSIONING.commissioning_version == "AI-D3-SYNTHETIC-INSTANT-1.0"
    assert AI_SYNTHETIC_COMMISSIONING.provider == "MICROSOFT_FOUNDRY"
    assert AI_SYNTHETIC_COMMISSIONING.tools == ()
    assert AI_SYNTHETIC_COMMISSIONING.store is False
    assert AI_SYNTHETIC_COMMISSIONING.production_allowed is False


def test_foundry_provider_uses_exact_project_endpoint_and_request_contract():
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {
                "id": "resp-1",
                "status": "completed",
                "model": "gpt-5-mini-2025-08-07",
                "output": [
                    {"type": "reasoning", "summary": [{"type": "summary_text", "text": "must not escape"}]},
                    {"type": "message", "content": [{"type": "output_text", "text": json.dumps(_payload())}]},
                ],
                "usage": {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30},
            }

    class Client:
        def __init__(self, **kwargs):
            captured["client"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, **kwargs):
            captured["url"] = url
            captured["request"] = kwargs
            return Response()

    result = FoundryProjectInstantResponsesProvider(_settings(), token_provider=lambda _: "foundry-token", http_client_factory=Client).execute_structured(AIProviderRequest("synthetic-input", 6000))
    assert result.provider == "MICROSOFT_FOUNDRY"
    assert result.model_name == "gpt-5-mini"
    assert result.model_version == "2025-08-07"
    assert result.access_mode == "INSTANT"
    assert captured["url"] == "https://resource.services.ai.azure.com/api/projects/project-1/openai/v1/responses"
    assert captured["client"]["follow_redirects"] is False
    body = captured["request"]["json"]
    assert body["model"] == "gpt-5-mini"
    assert body["store"] is False
    assert body["tools"] == []
    assert body["text"]["format"]["strict"] is True


@pytest.mark.parametrize(
    "endpoint",
    [
        "https://resource.services.ai.azure.com/api/projects/project-1/extra",
        "https://resource.services.ai.azure.com/api/projects/project-1?x=1",
        "https://resource.cognitiveservices.azure.com/api/projects/project-1",
    ],
)
def test_foundry_provider_rejects_non_project_endpoints(endpoint):
    with pytest.raises(AIError) as error:
        FoundryProjectInstantResponsesProvider(_settings(ai_foundry_project_endpoint=endpoint), token_provider=lambda _: "unused").execute_structured(AIProviderRequest("input", 6000))
    assert error.value.code == "AI_PROVIDER_REQUEST_REJECTED"


def test_foundry_identity_requests_ai_azure_com_and_validates_claims(monkeypatch):
    settings = _settings()
    monkeypatch.setenv("IDENTITY_ENDPOINT", "http://identity.local/token")
    monkeypatch.setenv("IDENTITY_HEADER", "identity-header")
    captured = {}

    class Response:
        status_code = 200

        def json(self):
            return {"access_token": _jwt({"oid": settings.ai_uami_principal_id, "tid": settings.ai_azure_tenant_id, "aud": "https://ai.azure.com"})}

    def fake_get(url, **kwargs):
        captured["url"] = url
        captured["kwargs"] = kwargs
        return Response()

    monkeypatch.setattr("backend.app.ai.identity.httpx.get", fake_get)
    assert acquire_foundry_project_token(settings) == Response().json()["access_token"]
    assert "resource=https%3A%2F%2Fai.azure.com" in captured["url"]
    assert captured["kwargs"]["follow_redirects"] is False


def test_foundry_identity_rejects_cognitive_services_audience(monkeypatch):
    settings = _settings()
    monkeypatch.setenv("IDENTITY_ENDPOINT", "http://identity.local/token")
    monkeypatch.setenv("IDENTITY_HEADER", "identity-header")

    class Response:
        status_code = 200

        def json(self):
            return {"access_token": _jwt({"oid": settings.ai_uami_principal_id, "tid": settings.ai_azure_tenant_id, "aud": "https://cognitiveservices.azure.com"})}

    monkeypatch.setattr("backend.app.ai.identity.httpx.get", lambda *args, **kwargs: Response())
    with pytest.raises(AIError) as error:
        acquire_foundry_project_token(settings)
    assert error.value.code == "AI_PROVIDER_IDENTITY_TOKEN_MISMATCH"


def test_preprod_foundry_settings_are_validated_and_prod_is_forbidden(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://preprod.example.com")
    preprod = _settings(app_env="AZURE-PREPROD", frontend_origins="https://preprod.example.com", auth_mode="ENTRA", entra_tenant_id="2a82f16d-87fa-4036-97a9-17d94060eddd", entra_api_client_id=str(uuid4()), entra_web_client_id=str(uuid4()), database_url="mssql+pyodbc://sql.database.windows.net:1433/db?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no", azure_sql_auth_mode="MANAGED_IDENTITY_ACCESS_TOKEN", azure_sql_uami_client_id=str(uuid4()), azure_sql_uami_principal_id=str(uuid4()))
    preprod.validate_environment()
    with pytest.raises(ValueError, match="PROD forbids"):
        _settings(app_env="PROD", synthetic_only=False, real_data_allowed=True, ai_provider_mode="FOUNDRY_PROJECT_INSTANT_SYNTHETIC").validate_environment()
