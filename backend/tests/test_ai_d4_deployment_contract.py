import pytest

from backend.app.ai.contracts import AI_ARCHITECTURE
from backend.app.config.settings import Settings


def test_d4_current_runtime_contract_is_pinned_to_global_standard():
    assert AI_ARCHITECTURE.architecture_version == "AI-D4-SYNTHETIC-RUNTIME-1.0"
    assert AI_ARCHITECTURE.provider == "AZURE_OPENAI_FOUNDRY"
    assert AI_ARCHITECTURE.model == "gpt-5.1"
    assert AI_ARCHITECTURE.model_version == "2025-11-13"
    assert AI_ARCHITECTURE.deployment_type == "GlobalStandard"
    assert AI_ARCHITECTURE.resource_region == "uaenorth"
    assert AI_ARCHITECTURE.processing_boundary == "GLOBAL_AZURE"
    assert AI_ARCHITECTURE.model_router_allowed is False
    assert AI_ARCHITECTURE.fallback_models == ()
    assert AI_ARCHITECTURE.provider_managed_memory_allowed is False
    assert AI_ARCHITECTURE.provider_managed_threads_allowed is False
    assert AI_ARCHITECTURE.real_content_allowed is False
    assert AI_ARCHITECTURE.external_invocation_enabled is True
    assert AI_ARCHITECTURE.canonical_write_authority == "ZERO"
    assert AI_ARCHITECTURE.protected_action_authority == "ZERO"


def _preprod_settings(**overrides):
    values = {
        "app_env": "AZURE-PREPROD",
        "frontend_origins": "https://proposalops-ui-preview.example",
        "synthetic_only": True,
        "real_data_allowed": False,
        "auth_mode": "ENTRA",
        "entra_tenant_id": "2a82f16d-87fa-4036-97a9-17d94060eddd",
        "entra_api_client_id": "11111111-1111-1111-1111-111111111111",
        "entra_web_client_id": "22222222-2222-2222-2222-222222222222",
        "database_url": "mssql+pyodbc://sql.example/permitops?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no",
        "azure_sql_auth_mode": "MANAGED_IDENTITY_ACCESS_TOKEN",
        "azure_sql_uami_client_id": "33333333-3333-3333-3333-333333333333",
        "azure_sql_uami_principal_id": "44444444-4444-4444-4444-444444444444",
        "synology_mode": "SYNTHETIC",
        "storage_provider": "mock",
        "ai_enabled": True,
        "ai_real_content_allowed": False,
        "ai_azure_openai_endpoint": "https://proposalops.openai.azure.com",
        "ai_uami_client_id": "55555555-5555-5555-5555-555555555555",
        "ai_uami_principal_id": "66666666-6666-6666-6666-666666666666",
        "ai_azure_tenant_id": "2a82f16d-87fa-4036-97a9-17d94060eddd",
        "ai_input_price_usd_per_1m_tokens": 1,
        "ai_output_price_usd_per_1m_tokens": 1,
        "ai_pricing_source_reference": "official-test-reference",
        "ai_d3_synthetic_project_ids": "STEP5B-SYN-20260905",
    }
    values.update(overrides)
    return Settings(**values)


def test_d4_preprod_settings_accept_exact_global_standard_boundary(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://proposalops-ui-preview.example")
    settings = _preprod_settings()
    settings.validate_environment()


@pytest.mark.parametrize(
    "overrides",
    [
        {"ai_azure_openai_deployment_type": "Standard"},
        {"ai_azure_openai_processing_boundary": "UAE_NORTH_REGIONAL"},
        {"ai_real_content_allowed": True},
    ],
)
def test_d4_preprod_settings_reject_non_d4_boundary(monkeypatch, overrides):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://proposalops-ui-preview.example")
    settings = _preprod_settings(**overrides)
    with pytest.raises(ValueError):
        settings.validate_environment()
