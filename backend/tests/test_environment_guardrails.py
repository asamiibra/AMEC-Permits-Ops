import pytest

from backend.app.config.settings import Settings


def test_production_rejects_synthetic_storage_and_development_auth():
    settings = Settings(app_env="PROD", database_url="postgresql://db", synthetic_only=True)

    with pytest.raises(ValueError, match="SYNTHETIC_ONLY=false"):
        settings.validate_environment()


def test_production_requires_real_storage_configuration():
    settings = Settings(
        app_env="PROD",
        database_url="postgresql://db",
        synthetic_only=False,
        auth_mode="OIDC",
        synology_mode="SYNTHETIC",
    )

    with pytest.raises(ValueError, match="SYNOLOGY_MODE=REAL"):
        settings.validate_environment()


def test_non_production_remains_explicitly_synthetic():
    settings = Settings(app_env="TEST", database_url="sqlite:///test.db", synthetic_only=True)
    settings.validate_environment()
