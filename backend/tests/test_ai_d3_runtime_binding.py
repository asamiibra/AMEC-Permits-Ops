from backend.app.ai.runtime_binding import AIRuntimeBinding
from backend.app.config.settings import Settings


def test_runtime_binding_is_distinct_from_historical_d0_target() -> None:
    settings = Settings(
        ai_azure_openai_endpoint="https://proposalopsd3real20260908.openai.azure.com",
        ai_azure_openai_deployment="d3-gpt54mini-20260317",
        ai_azure_openai_expected_model="gpt-5.4-mini",
        ai_azure_openai_expected_version="2026-03-17",
        ai_azure_openai_region="eastus",
        ai_azure_openai_deployment_type="DataZoneStandard",
    )
    binding = AIRuntimeBinding.from_settings(settings)

    binding.validate()
    assert binding.provider == "AZURE_OPENAI_RESPONSES"
    assert binding.model == "gpt-5.4-mini"
    assert binding.version == "2026-03-17"
    assert binding.region == "eastus"
    assert binding.deployment_type == "DataZoneStandard"


def test_runtime_binding_allows_production_global_mode_when_real_content_is_off() -> None:
    settings = Settings(
        synthetic_only=False,
        ai_azure_openai_endpoint="https://proposalopsd3real20260908.openai.azure.com",
        ai_azure_openai_deployment="d3-gpt54mini-20260317",
        ai_azure_openai_expected_model="gpt-5.4-mini",
        ai_azure_openai_expected_version="2026-03-17",
        ai_azure_openai_region="eastus",
        ai_azure_openai_deployment_type="DataZoneStandard",
    )
    binding = AIRuntimeBinding.from_settings(settings)

    binding.validate()
    assert binding.synthetic_only is False
    assert binding.real_content_allowed is False
