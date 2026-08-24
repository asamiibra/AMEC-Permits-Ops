from pathlib import Path
import re
import tomllib

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


def _azure_preprod_settings(database_url: str) -> Settings:
    return Settings(
        app_env="AZURE-PREPROD",
        database_url=database_url,
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


def test_azure_preprod_secure_mssql_accepted(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://synthetic.example")
    _azure_preprod_settings(MSSQL_TARGET).validate_environment()


def test_azure_preprod_postgresql_rejected(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://synthetic.example")
    with pytest.raises(ValueError, match="mssql\\+pyodbc"):
        _azure_preprod_settings(
            "postgresql+psycopg://runtime:secret@db.example/proposalops"
        ).validate_environment()


def test_azure_preprod_sqlite_rejected(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://synthetic.example")
    with pytest.raises(ValueError, match="mssql\\+pyodbc"):
        _azure_preprod_settings("sqlite:///synthetic.db").validate_environment()


def test_azure_preprod_encrypt_no_rejected(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://synthetic.example")
    with pytest.raises(ValueError, match="Encrypt=yes"):
        _azure_preprod_settings(
            MSSQL_TARGET.replace("Encrypt=yes", "Encrypt=no")
        ).validate_environment()


def test_azure_preprod_trust_server_certificate_yes_rejected(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGINS", "https://synthetic.example")
    with pytest.raises(ValueError, match="TrustServerCertificate=no"):
        _azure_preprod_settings(
            MSSQL_TARGET.replace(
                "TrustServerCertificate=no", "TrustServerCertificate=yes"
            )
        ).validate_environment()


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


def test_sqlserver_driver_dependency_metadata_consistent():
    root = Path(__file__).resolve().parents[2]
    pyproject = tomllib.loads((root / "backend/pyproject.toml").read_text(encoding="utf-8"))
    project_dependencies = pyproject["project"]["dependencies"]
    pyproject_matches = [item for item in project_dependencies if item.startswith("pyodbc")]
    assert len(pyproject_matches) == 1
    assert pyproject_matches[0] == "pyodbc==5.3.0"

    def requirement_matches(path: Path) -> list[str]:
        return re.findall(r"^pyodbc==([^\s\\]+)", path.read_text(encoding="utf-8"), re.MULTILINE)

    requirements_matches = requirement_matches(root / "backend/requirements.txt")
    runtime_matches = requirement_matches(root / "backend/requirements-runtime.txt")
    lock_matches = requirement_matches(root / "backend/requirements-runtime.lock")
    assert requirements_matches == ["5.3.0"]
    assert runtime_matches == ["5.3.0"]
    assert lock_matches == ["5.3.0"]

    dockerfile = (root / "backend/Dockerfile").read_text(encoding="utf-8")
    assert "COPY backend/requirements-runtime.lock /tmp/requirements-runtime.lock" in dockerfile
    assert "--require-hashes -r /tmp/requirements-runtime.lock" in dockerfile
    print("PYPROJECT_PYODBC_DECLARATION_COUNT=1")
    print("PYPROJECT_PYODBC_EXACT=pyodbc==5.3.0")
    print("REQUIREMENTS_TXT_PYODBC_DECLARATION_COUNT=1")
    print("REQUIREMENTS_TXT_PYODBC_EXACT=pyodbc==5.3.0")
    print("RUNTIME_TXT_PYODBC_DECLARATION_COUNT=1")
    print("RUNTIME_TXT_PYODBC_EXACT=pyodbc==5.3.0")
    print("RUNTIME_LOCK_PYODBC_VERSION=5.3.0")
    print("SQLSERVER_DRIVER_DEPENDENCY_METADATA_PARITY=PASS")
