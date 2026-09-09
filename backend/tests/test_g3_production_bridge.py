from __future__ import annotations

import os

import pytest

from backend.app import bootstrap_production
from backend.app.auth.bridge import BridgeAuthenticationError, validate_bridge_claims
from backend.app.config.settings import Settings
from backend.app import migrate
from backend.app.observability import SensitiveDataFilter


MSSQL_URL = (
    "mssql+pyodbc://sql.example/proposalops?driver=ODBC+Driver+18+for+SQL+Server"
    "&Encrypt=yes&TrustServerCertificate=no"
)
MIGRATION_URL = (
    "mssql+pyodbc://migration.example/proposalops?driver=ODBC+Driver+18+for+SQL+Server"
    "&Encrypt=yes&TrustServerCertificate=no"
)


def _prod(**overrides) -> Settings:
    values = {
        "app_env": "PROD",
        "database_url": MSSQL_URL,
        "database_migration_url": MIGRATION_URL,
        "frontend_origins": "https://app.example",
        "synthetic_only": False,
        "real_data_allowed": False,
        "auth_mode": "ENTRA",
        "entra_tenant_id": "11111111-1111-4111-8111-111111111111",
        "entra_api_client_id": "22222222-2222-4222-8222-222222222222",
        "entra_web_client_id": "33333333-3333-4333-8333-333333333333",
        "entra_required_scope": "access_as_user",
        "azure_sql_auth_mode": "MANAGED_IDENTITY_ACCESS_TOKEN",
        "azure_sql_uami_client_id": "44444444-4444-4444-8444-444444444444",
        "azure_sql_uami_principal_id": "55555555-5555-4555-8555-555555555555",
        "source_intake_mode": "BRIDGE",
        "synology_mode": "BRIDGE",
        "bridge_tenant_id": "66666666-6666-4666-8666-666666666666",
        "bridge_client_id": "77777777-7777-4777-8777-777777777777",
        "bridge_audience": "22222222-2222-4222-8222-222222222222",
        "bridge_required_role": "proposalops.source-intake",
        "storage_provider": "smb",
        "smb_server": "managed-artifacts.example",
        "smb_share": "ProposalOpsManaged",
        "smb_username": "proposalops-managed",
        "smb_password": "managed-only-test-secret",
    }
    values.update(overrides)
    return Settings(**values)


def test_prod_bridge_without_authoritative_dsm_credentials_passes():
    _prod().validate_environment()


def test_prod_bridge_rejects_direct_dsm_switch():
    with pytest.raises(ValueError, match="AZURE_DIRECT_SYNOLOGY_SMB=false"):
        _prod(azure_direct_synology_smb=True).validate_environment()


def test_prod_bridge_rejects_synology_credentials():
    with pytest.raises(ValueError, match="SYNOLOGY_ENDPOINT"):
        _prod(synology_endpoint="https://dsm.example").validate_environment()


def test_prod_bridge_rejects_external_source_smb_credentials():
    with pytest.raises(ValueError, match="SMB_EXTERNAL_SERVER"):
        _prod(smb_external_server="dsm.example").validate_environment()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("auth_mode", "DEV_HEADER", "AUTH_MODE=ENTRA"),
        ("auth_mode", "OIDC", "AUTH_MODE=ENTRA"),
        ("entra_tenant_id", "not-a-guid", "ENTRA_TENANT_ID"),
        ("entra_api_client_id", "33333333-3333-4333-8333-333333333333", "separate Entra"),
        ("entra_required_scope", "wrong.scope", "access_as_user"),
        ("source_intake_mode", "DIRECT", "SOURCE_INTAKE_MODE=BRIDGE"),
        ("azure_sql_auth_mode", "DIRECT_ODBC_MSI", "MANAGED_IDENTITY_ACCESS_TOKEN"),
        ("database_url", "sqlite:///proposalops.db", r"mssql\+pyodbc"),
        ("database_migration_url", "", "DATABASE_MIGRATION_URL"),
        ("database_url", MSSQL_URL.replace("Encrypt=yes", "Encrypt=no"), "Encrypt=yes"),
        ("database_url", MSSQL_URL.replace("sql.example", "user:password@sql.example"), "forbids URL credentials"),
    ],
)
def test_prod_guardrails_reject_invalid_contract(field, value, message):
    with pytest.raises(ValueError, match=message):
        _prod(**{field: value}).validate_environment()


def test_bridge_machine_claims_require_exact_identity_and_role():
    settings = _prod()
    claims = {
        "tid": settings.bridge_tenant_id,
        "azp": settings.bridge_client_id,
        "oid": "88888888-8888-4888-8888-888888888888",
        "aud": settings.bridge_audience,
        "ver": "2.0",
        "roles": [settings.bridge_required_role],
    }
    identity = validate_bridge_claims(claims, settings)
    assert identity.client_id == settings.bridge_client_id
    with pytest.raises(BridgeAuthenticationError):
        validate_bridge_claims({**claims, "azp": settings.entra_web_client_id}, settings)
    with pytest.raises(BridgeAuthenticationError):
        validate_bridge_claims({**claims, "roles": []}, settings)


def test_production_bootstrap_is_real_data_false_and_zero_contact(monkeypatch):
    settings = _prod()
    calls = {"head": 0}
    monkeypatch.setattr(bootstrap_production, "get_settings", lambda: settings)

    def verify_head():
        calls["head"] += 1

    monkeypatch.setattr(bootstrap_production, "verify_database_migration_head", verify_head)
    assert bootstrap_production.run_production_bootstrap() == "PRODUCTION_BOOTSTRAP_ZERO_SYNTHETIC_PASS"
    assert bootstrap_production.run_production_bootstrap() == "PRODUCTION_BOOTSTRAP_ZERO_SYNTHETIC_PASS"
    assert calls["head"] == 2


def test_production_bootstrap_rejects_real_data_authority(monkeypatch):
    monkeypatch.setattr(bootstrap_production, "get_settings", lambda: _prod(real_data_allowed=True))
    with pytest.raises(RuntimeError, match="REAL_DATA_ALLOWED=false"):
        bootstrap_production.run_production_bootstrap()


def test_log_redaction_removes_sentinel_secrets_and_keeps_safe_diagnostics():
    import logging

    record = logging.LogRecord(
        "test",
        logging.ERROR,
        __file__,
        1,
        "failed SQLSTATE=%s url=%s Authorization: Bearer %s",
        ("42000", "mssql+pyodbc://user:secret@db/app", "sentinel-token"),
        None,
    )
    SensitiveDataFilter().filter(record)
    retained = record.getMessage()
    assert "42000" in retained
    assert "secret" not in retained
    assert "sentinel-token" not in retained
    assert "mssql+pyodbc://" not in retained
    assert record.exc_info is None


def test_api_security_headers_and_cors_are_explicit(client):
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Permissions-Policy"] == "camera=(), microphone=(), geolocation=()"
    assert response.headers["Content-Security-Policy"].startswith("default-src 'none'")
    preflight = client.options(
        "/api/office",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,x-correlation-id",
        },
    )
    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "*" not in preflight.headers["access-control-allow-headers"]


def test_governed_migration_scope_is_the_only_prod_alembic_authority(monkeypatch):
    monkeypatch.delenv("PROPOSALOPS_GOVERNED_MIGRATION_RUNNER", raising=False)
    with migrate._migration_authority_scope(MIGRATION_URL):
        assert os.environ["PROPOSALOPS_GOVERNED_MIGRATION_RUNNER"] == "1"
    assert "PROPOSALOPS_GOVERNED_MIGRATION_RUNNER" not in os.environ
