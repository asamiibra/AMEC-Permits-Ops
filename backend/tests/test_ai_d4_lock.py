import pytest

from backend.app.config.settings import Settings


def _d4_settings(**overrides):
    values = {
        "app_env": "TEST", "synthetic_only": True, "real_data_allowed": False,
        "ai_feature_enabled": True, "ai_external_inference_enabled": True,
        "ai_d4_commissioning_id": "d4-commissioning-test",
        "ai_azure_openai_endpoint": "https://proposalops.openai.azure.com",
        "ai_azure_openai_deployment": "d3-gpt54mini-20260317",
        "ai_azure_openai_expected_model": "gpt-5.4-mini",
        "ai_azure_openai_expected_version": "2026-03-17",
        "ai_azure_openai_region": "eastus", "ai_azure_openai_deployment_type": "DataZoneStandard",
        "ai_uami_client_id": "11111111-1111-4111-8111-111111111111",
        "ai_uami_principal_id": "22222222-2222-4222-8222-222222222222",
        "ai_azure_tenant_id": "33333333-3333-4333-8333-333333333333",
        "ai_d3_synthetic_project_ids": "synthetic-project",
        "ai_max_input_token_upper_bound": 24000, "ai_max_output_tokens": 6000,
        "ai_max_requests_per_user_per_minute": 3, "ai_max_requests_per_user_per_hour": 20,
        "ai_max_requests_per_project_per_hour": 20, "ai_max_requests_global_per_hour": 60,
        "ai_max_estimated_cost_usd_per_request": 0.25, "ai_max_estimated_cost_usd_per_day": 5.0,
        "ai_input_price_usd_per_1m_tokens": 0.825, "ai_output_price_usd_per_1m_tokens": 1.0,
        "ai_pricing_source_reference": "authoritative-test-reference",
    }
    values.update(overrides)
    return Settings(**values)


def test_pre_d4_feature_gate_has_zero_budget_defaults():
    settings = Settings(app_env="TEST", synthetic_only=True, ai_feature_enabled=True)
    assert settings.ai_feature_enabled is True
    assert settings.ai_external_inference_enabled is False
    assert settings.ai_d4_commissioning_id == ""
    assert settings.ai_max_estimated_cost_usd_per_request == 0
    assert settings.ai_max_estimated_cost_usd_per_day == 0
    assert settings.ai_input_price_usd_per_1m_tokens == 0
    assert settings.ai_output_price_usd_per_1m_tokens == 0


def test_d4_lock_accepts_exact_commissioned_binding():
    _d4_settings().validate_environment()


@pytest.mark.parametrize(
    "override, message",
    [
        ({"ai_external_inference_enabled": True, "ai_feature_enabled": False}, "AI_FEATURE_ENABLED"),
        ({"ai_d4_commissioning_id": ""}, "AI_D4_COMMISSIONING_ID"),
        ({"ai_azure_openai_expected_model": "gpt-5.1"}, "AI_AZURE_OPENAI_EXPECTED_MODEL"),
        ({"ai_input_price_usd_per_1m_tokens": 0}, "AI_INPUT_PRICE_USD_PER_1M_TOKENS"),
        ({"ai_max_estimated_cost_usd_per_day": 0}, "AI_MAX_ESTIMATED_COST_USD_PER_DAY"),
    ],
)
def test_d4_lock_rejects_incomplete_or_wrong_binding(override, message):
    with pytest.raises(ValueError, match=message):
        _d4_settings(**override).validate_environment()
