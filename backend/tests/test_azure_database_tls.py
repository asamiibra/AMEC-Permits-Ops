import pytest

from backend.app.db import validate_postgres_tls_url
from backend.app import migrate


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


@pytest.mark.parametrize("query", ["", "sslmode=require", "sslmode=disable", "sslmode=prefer"])
def test_azure_rejects_unverified_tls(query):
    with pytest.raises(ValueError):
        validate_postgres_tls_url(f"postgresql+psycopg://u:p@db.postgres.database.azure.com/app?{query}")
