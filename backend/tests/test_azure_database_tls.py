import pytest

from backend.app.db import validate_postgres_tls_url


def test_local_postgres_is_not_subject_to_azure_certificate_rule():
    validate_postgres_tls_url("postgresql+psycopg://u:p@localhost/app")


def test_azure_verify_full_requires_root():
    validate_postgres_tls_url("postgresql+psycopg://u:p@db.postgres.database.azure.com/app?sslmode=verify-full&sslrootcert=/ca.pem")


def test_azure_verify_ca_accepts_environment_root():
    validate_postgres_tls_url("postgresql+psycopg://u:p@db.postgres.database.azure.com/app?sslmode=verify-ca", environ={"PGSSLROOTCERT": "/ca.pem"})


@pytest.mark.parametrize("query", ["", "sslmode=require", "sslmode=disable", "sslmode=prefer"])
def test_azure_rejects_unverified_tls(query):
    with pytest.raises(ValueError):
        validate_postgres_tls_url(f"postgresql+psycopg://u:p@db.postgres.database.azure.com/app?{query}")
