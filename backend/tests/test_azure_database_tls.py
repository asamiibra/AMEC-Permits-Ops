import os
from types import SimpleNamespace

import pytest

from backend.app.config import settings as settings_module
from backend.app.db import validate_postgres_tls_url
from backend.app import migrate


RUNTIME_DATABASE_URL = "postgresql+psycopg://runtime:p@localhost/app"
MIGRATION_DATABASE_URL = "postgresql+psycopg://migration:p@localhost/app"
MIGRATION_HEAD = "0059_entra_user_identity"


def _install_cached_settings(monkeypatch, migration_url=MIGRATION_DATABASE_URL):
    cache = {}

    def fake_get_settings():
        if "settings" not in cache:
            cache["settings"] = SimpleNamespace(
                app_env="AZURE-PREPROD",
                synthetic_only=True,
                real_data_allowed=False,
                database_url=os.environ["DATABASE_URL"],
                database_migration_url=migration_url,
            )
        return cache["settings"]

    fake_get_settings.cache_clear = cache.clear
    monkeypatch.setenv("DATABASE_URL", RUNTIME_DATABASE_URL)
    monkeypatch.setattr(migrate, "get_settings", fake_get_settings)
    return cache


def _stub_migration_verification(monkeypatch):
    class FakeEngine:
        def dispose(self):
            return None

    monkeypatch.setattr(
        migrate,
        "repository_migration_head",
        lambda: MIGRATION_HEAD,
    )
    monkeypatch.setattr(
        migrate,
        "create_database_engine",
        lambda database_url: FakeEngine(),
    )
    monkeypatch.setattr(
        migrate,
        "verify_database_migration_head",
        lambda *_: MIGRATION_HEAD,
    )


def test_local_postgres_is_not_subject_to_azure_certificate_rule():
    validate_postgres_tls_url("postgresql+psycopg://u:p@localhost/app")


def test_azure_verify_full_requires_root():
    validate_postgres_tls_url("postgresql+psycopg://u:p@db.postgres.database.azure.com/app?sslmode=verify-full&sslrootcert=/ca.pem")


def test_azure_verify_ca_accepts_environment_root():
    validate_postgres_tls_url("postgresql+psycopg://u:p@db.postgres.database.azure.com/app?sslmode=verify-ca", environ={"PGSSLROOTCERT": "/ca.pem"})


def test_migration_runner_validates_admin_tls_before_upgrade(monkeypatch):
    settings = type(
        "Settings",
        (),
        {
            "app_env": "AZURE-PREPROD",
            "synthetic_only": True,
            "real_data_allowed": False,
            "database_url": "postgresql+psycopg://runtime:p@db.postgres.database.azure.com/app?sslmode=verify-full&sslrootcert=/ca.pem",
            "database_migration_url": "postgresql+psycopg://admin:p@db.postgres.database.azure.com/app?sslmode=require",
        },
    )()
    monkeypatch.setattr(migrate, "get_settings", lambda: settings)
    monkeypatch.setattr(migrate, "repository_migration_head", lambda: "0059_entra_user_identity")
    monkeypatch.setattr(
        migrate.command,
        "upgrade",
        lambda *_: pytest.fail("migration must not run with unverified TLS"),
    )
    with pytest.raises(ValueError):
        migrate.run_migrations()


def test_migration_authority_wins_over_poison_runtime_url(monkeypatch):
    class FakeSettings:
        def __init__(self):
            self.app_env = "AZURE-PREPROD"
            self.synthetic_only = True
            self.real_data_allowed = False
            self.database_url = os.environ["DATABASE_URL"]
            self.database_migration_url = MIGRATION_DATABASE_URL

        def validate_environment(self):
            return None

    monkeypatch.setenv("DATABASE_URL", RUNTIME_DATABASE_URL)
    monkeypatch.setattr(settings_module, "Settings", FakeSettings)
    settings_module.get_settings.cache_clear()
    _stub_migration_verification(monkeypatch)
    observed_database_urls = []

    def upgrade(_config, _revision):
        observed_database_urls.append(
            settings_module.get_settings().database_url
        )

    monkeypatch.setattr(migrate.command, "upgrade", upgrade)

    try:
        assert migrate.run_migrations() == MIGRATION_HEAD
        assert observed_database_urls == [MIGRATION_DATABASE_URL]
        assert os.environ["DATABASE_URL"] == RUNTIME_DATABASE_URL
        assert settings_module.get_settings().database_url == RUNTIME_DATABASE_URL
    finally:
        settings_module.get_settings.cache_clear()


def test_migration_authority_scope_restores_after_success(monkeypatch):
    _install_cached_settings(monkeypatch)
    _stub_migration_verification(monkeypatch)
    monkeypatch.setattr(migrate.command, "upgrade", lambda *_: None)

    assert migrate.run_migrations() == MIGRATION_HEAD
    assert os.environ["DATABASE_URL"] == RUNTIME_DATABASE_URL
    assert migrate.get_settings().database_url == RUNTIME_DATABASE_URL


def test_migration_authority_scope_restores_after_failure(monkeypatch):
    _install_cached_settings(monkeypatch)
    _stub_migration_verification(monkeypatch)

    def fail_upgrade(*_):
        raise RuntimeError("synthetic migration failure")

    monkeypatch.setattr(migrate.command, "upgrade", fail_upgrade)

    with pytest.raises(RuntimeError, match="synthetic migration failure"):
        migrate.run_migrations()
    assert os.environ["DATABASE_URL"] == RUNTIME_DATABASE_URL
    assert migrate.get_settings().database_url == RUNTIME_DATABASE_URL


def test_migration_runner_without_migration_url_preserves_fallback(monkeypatch):
    _install_cached_settings(monkeypatch, migration_url="")
    _stub_migration_verification(monkeypatch)
    observed_database_urls = []

    def upgrade(_config, _revision):
        observed_database_urls.append(
            migrate.get_settings().database_url
        )

    monkeypatch.setattr(migrate.command, "upgrade", upgrade)

    assert migrate.run_migrations() == MIGRATION_HEAD
    assert observed_database_urls == [RUNTIME_DATABASE_URL]
    assert os.environ["DATABASE_URL"] == RUNTIME_DATABASE_URL


@pytest.mark.parametrize("query", ["", "sslmode=require", "sslmode=disable", "sslmode=prefer"])
def test_azure_rejects_unverified_tls(query):
    with pytest.raises(ValueError):
        validate_postgres_tls_url(f"postgresql+psycopg://u:p@db.postgres.database.azure.com/app?{query}")
