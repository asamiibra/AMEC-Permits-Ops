from types import SimpleNamespace

import pytest

from backend.app import migrate


EXPECTED_HEAD = "step5_content_library_azure_sql_v2"


def _settings(
    *,
    app_env: str = "AZURE-PREPROD",
    database_url: str = "postgresql+psycopg://user:pass@db/proposalops",
    synthetic_only: bool = True,
    real_data_allowed: bool = False,
):
    return SimpleNamespace(
        app_env=app_env,
        database_url=database_url,
        database_migration_url="",
        synthetic_only=synthetic_only,
        real_data_allowed=real_data_allowed,
    )


class _FakeConnection:
    def __init__(self):
        self.statements = []
        self.closed = False

    def exec_driver_sql(self, statement):
        self.statements.append(statement)

    def close(self):
        self.closed = True


class _FakeEngine:
    def __init__(self, connection=None, failures=0):
        self.connection = connection or _FakeConnection()
        self.failures = failures
        self.connect_calls = 0
        self.disposed = False

    def connect(self):
        self.connect_calls += 1
        if self.connect_calls <= self.failures:
            raise RuntimeError("transient connection failure")
        return self.connection

    def dispose(self):
        self.disposed = True


class _FakeMigrationContext:
    def get_current_heads(self):
        return (EXPECTED_HEAD,)


class _FakeMigrationContextType:
    @classmethod
    def configure(cls, connection):
        cls.connection = connection
        return _FakeMigrationContext()


def _install_fake_database(monkeypatch, *, engine, expected_head=EXPECTED_HEAD):
    monkeypatch.setattr(migrate, "get_settings", lambda: _settings())
    monkeypatch.setattr(
        migrate,
        "repository_migration_head",
        lambda: expected_head,
    )
    monkeypatch.setattr(
        migrate,
        "create_database_engine",
        lambda database_url: engine,
    )
    monkeypatch.setattr(migrate, "MigrationContext", _FakeMigrationContextType)


def test_alembic_config_is_programmatic_and_packaged():
    config = migrate._alembic_config("postgresql+psycopg://u:p@db/app")

    assert config.config_file_name is None
    assert config.get_main_option("script_location").endswith("backend/migrations")


def test_alembic_config_escapes_percent_signs():
    config = migrate._alembic_config("postgresql+psycopg://u:p%25@db/app")

    assert config.get_main_option("sqlalchemy.url") == "postgresql+psycopg://u:p%25@db/app"


@pytest.mark.parametrize("app_env", ["DEV", "TEST", "PROD"])
def test_runner_rejects_non_preprod_environment(monkeypatch, app_env):
    monkeypatch.setattr(migrate, "get_settings", lambda: _settings(app_env=app_env))

    with pytest.raises(RuntimeError, match="restricted"):
        migrate.run_migrations()


def test_runner_requires_synthetic_only(monkeypatch):
    monkeypatch.setattr(
        migrate,
        "get_settings",
        lambda: _settings(synthetic_only=False),
    )

    with pytest.raises(RuntimeError, match="SYNTHETIC_ONLY"):
        migrate.run_migrations()


def test_runner_rejects_real_data_allowed(monkeypatch):
    monkeypatch.setattr(
        migrate,
        "get_settings",
        lambda: _settings(real_data_allowed=True),
    )

    with pytest.raises(RuntimeError, match="REAL_DATA_ALLOWED"):
        migrate.run_migrations()


def test_runner_requires_supported_database_url(monkeypatch):
    monkeypatch.setattr(
        migrate,
        "get_settings",
        lambda: _settings(database_url="sqlite:///unsafe.db"),
    )

    with pytest.raises(RuntimeError, match=r"postgresql\+psycopg"):
        migrate.run_migrations()


def test_runner_uses_one_connection_for_upgrade_and_verification(monkeypatch):
    connection = _FakeConnection()
    engine = _FakeEngine(connection=connection)
    _install_fake_database(monkeypatch, engine=engine)
    calls = []

    def upgrade(config, revision):
        assert config.config_file_name is None
        assert revision == "head"
        assert config.attributes["connection"] is connection
        calls.append("upgrade")

    monkeypatch.setattr(migrate.command, "upgrade", upgrade)

    assert migrate.run_migrations() == EXPECTED_HEAD
    assert calls == ["upgrade"]
    assert engine.connect_calls == 1
    assert connection.statements == ["SELECT 1"]
    assert connection.closed
    assert engine.disposed


def test_runner_bounds_connection_acquisition_and_closes_failed_connections(monkeypatch):
    connection = _FakeConnection()
    engine = _FakeEngine(connection=connection, failures=2)
    _install_fake_database(monkeypatch, engine=engine)
    monkeypatch.setattr(migrate.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(migrate.command, "upgrade", lambda *_: None)

    assert migrate.run_migrations() == EXPECTED_HEAD
    assert engine.connect_calls == 3
    assert connection.closed


def test_connection_failure_reports_zero_migration_execution(monkeypatch, capsys):
    engine = _FakeEngine(failures=3)
    _install_fake_database(monkeypatch, engine=engine)
    monkeypatch.setattr(migrate.time, "sleep", lambda _seconds: None)

    assert migrate.main() == 1
    output = capsys.readouterr()

    assert '"first_blocker": "AZURE_SQL_CONNECTION_UNAVAILABLE_BEFORE_MIGRATION"' in output.err
    assert '"migration_execution_count": 0' in output.err
    assert '"connection_attempts": 3' in output.err


def test_main_success_is_structured(monkeypatch, capsys):
    monkeypatch.setattr(migrate, "run_migrations", lambda: EXPECTED_HEAD)

    assert migrate.main() == 0
    output = capsys.readouterr()

    assert '"status": "SUCCEEDED"' in output.out
    assert EXPECTED_HEAD in output.out
    assert output.err == ""


def test_main_failure_is_nonzero_and_redacted(monkeypatch, capsys):
    secret = "postgresql://user:secret@db/app"

    def fail():
        raise RuntimeError(secret)

    monkeypatch.setattr(migrate, "run_migrations", fail)

    assert migrate.main() == 1
    output = capsys.readouterr()

    assert '"status": "FAILED"' in output.err
    assert "RuntimeError" in output.err
    assert secret not in output.err
    assert "<redacted-database-url>" in output.err


def test_diagnostics_include_sqlstate_native_number_and_sanitized_statement():
    class Original:
        args = ("42000", "native failure (2627)")

    class DatabaseError(Exception):
        orig = Original()
        statement = "ALTER TABLE dbo.form_instances ADD secret=token=abc"
        code = "f405"

    payload = migrate._diagnostic_payload(
        DatabaseError(),
        phase="alembic_upgrade",
        expected_head=EXPECTED_HEAD,
        connection_attempts=1,
        migration_execution_count=1,
    )

    assert payload["sqlstate"] == "42000"
    assert payload["native_error_number"] == 2627
    assert payload["sqlalchemy_error_code"] == "f405"
    assert "token=abc" not in payload["sanitized_statement"]
