from types import SimpleNamespace

import pytest

from backend.app import bootstrap_production
from scripts.azure import canonical_bootstrap_sql


def test_production_bootstrap_rejects_non_prod(monkeypatch):
    monkeypatch.setattr(bootstrap_production, "get_settings", lambda: SimpleNamespace(app_env="AZURE-PREPROD"))
    with pytest.raises(RuntimeError, match="APP_ENV=PROD"):
        bootstrap_production.run_production_bootstrap()


def test_canonical_sql_bootstrap_requires_explicit_production_guard():
    with pytest.raises(ValueError, match="production-authorized"):
        canonical_bootstrap_sql.bootstrap(
            environment="PROD",
            server="sql.example",
            database="proposalops",
            api_name="api-uami",
            worker_name="worker-uami",
            migration_name="migration-uami",
        )


def test_canonical_sql_bootstrap_reads_back_exact_roles(monkeypatch):
    class Cursor:
        def execute(self, *_args):
            return None

        def fetchall(self):
            return [
                SimpleNamespace(principal_name="api-uami", role_name="db_datareader"),
                SimpleNamespace(principal_name="api-uami", role_name="db_datawriter"),
                SimpleNamespace(principal_name="worker-uami", role_name="db_datareader"),
                SimpleNamespace(principal_name="worker-uami", role_name="db_datawriter"),
                SimpleNamespace(principal_name="migration-uami", role_name="db_datareader"),
                SimpleNamespace(principal_name="migration-uami", role_name="db_datawriter"),
                SimpleNamespace(principal_name="migration-uami", role_name="db_ddladmin"),
            ]

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def cursor(self):
            return Cursor()

        def commit(self):
            return None

    monkeypatch.setattr(canonical_bootstrap_sql, "_connection", lambda *_args: Connection())
    result = canonical_bootstrap_sql.bootstrap(
        environment="PROD",
        server="sql.example",
        database="proposalops",
        api_name="api-uami",
        worker_name="worker-uami",
        migration_name="migration-uami",
        production_authorized=True,
    )
    assert len(result) == 7
