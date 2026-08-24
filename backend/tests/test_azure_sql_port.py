from pathlib import Path

import pytest

from backend.app.config.settings import Settings
from backend.app.db import validate_mssql_connection_url
from backend.app.services.phase4 import ALLOWED_DECISIONS


MSSQL_TARGET = (
    "mssql+pyodbc://runtime:secret@proposalops.database.windows.net:1433/"
    "proposalops?driver=ODBC+Driver+18+for+SQL+Server&Encrypt=yes&TrustServerCertificate=no"
)


def test_azure_sql_target_connection_contract_is_encrypted():
    validate_mssql_connection_url(MSSQL_TARGET, require_encryption=True)


@pytest.mark.parametrize(
    "url",
    [
        MSSQL_TARGET.replace("Encrypt=yes", "Encrypt=no"),
        MSSQL_TARGET.replace("TrustServerCertificate=no", "TrustServerCertificate=yes"),
    ],
)
def test_azure_sql_target_rejects_unsafe_tls(url):
    with pytest.raises(ValueError):
        validate_mssql_connection_url(url, require_encryption=True)


def test_settings_accepts_only_secure_mssql_target_for_azure_preprod(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://synthetic.example")
    settings = Settings(
        app_env="AZURE-PREPROD",
        database_url=MSSQL_TARGET,
        frontend_origins="https://synthetic.example",
        synthetic_only=True,
        real_data_allowed=False,
        auth_mode="ENTRA",
        entra_tenant_id="11111111-1111-4111-8111-111111111111",
        entra_api_client_id="22222222-2222-4222-8222-222222222222",
        entra_web_client_id="33333333-3333-4333-8333-333333333333",
        storage_provider="mock",
        synology_mode="SYNTHETIC",
    )
    settings.validate_environment()


def test_phase4_has_exactly_six_review_actions_and_no_advisory_lock():
    assert ALLOWED_DECISIONS == {
        "ACCEPT",
        "CORRECT",
        "DEFER",
        "MARK_OUT_OF_SCOPE",
        "RESOLVE_RELATIONSHIP",
        "REJECT",
    }
    source = Path("backend/app/services/phase4.py").read_text(encoding="utf-8")
    assert "pg_advisory_xact_lock" not in source


def test_active_migration_is_one_azure_sql_root_and_fails_closed_on_downgrade():
    active = sorted(Path("backend/migrations/versions").glob("*.py"))
    assert [path.name for path in active] == ["baseline_phase4_v36_azure_sql.py"]
    source = active[0].read_text(encoding="utf-8")
    assert 'revision = "baseline_phase4_v36_azure_sql"' in source
    assert "down_revision = None" in source
    assert "ON CONFLICT" not in source
    assert "Base.metadata.create_all" not in source
