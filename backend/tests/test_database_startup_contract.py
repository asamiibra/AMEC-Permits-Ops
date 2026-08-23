from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, text

from backend.app import db as database


@pytest.fixture
def isolated_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
    )

    try:
        yield engine
    finally:
        engine.dispose()


def _install_engine(
    monkeypatch,
    isolated_engine,
) -> None:
    monkeypatch.setattr(
        database,
        "engine",
        isolated_engine,
    )


def _set_environment(
    monkeypatch,
    app_env: str,
) -> None:
    monkeypatch.setattr(
        database,
        "settings",
        SimpleNamespace(
            app_env=app_env,
        ),
    )


def _create_version_table(
    isolated_engine,
    *versions: str,
) -> None:
    with isolated_engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE alembic_version "
                "(version_num VARCHAR(32) "
                "NOT NULL PRIMARY KEY)"
            )
        )

        for version in versions:
            connection.execute(
                text(
                    "INSERT INTO alembic_version "
                    "(version_num) VALUES (:version)"
                ),
                {
                    "version": version,
                },
            )


def test_repository_migration_head_is_current_rebaseline_head():
    assert (
        database.repository_migration_head()
        == "baseline_r13_0059"
    )


def test_database_heads_are_empty_without_version_table(
    monkeypatch,
    isolated_engine,
):
    _install_engine(
        monkeypatch,
        isolated_engine,
    )

    assert (
        database.database_migration_heads()
        == ()
    )


def test_database_heads_read_exact_version(
    monkeypatch,
    isolated_engine,
):
    _install_engine(
        monkeypatch,
        isolated_engine,
    )

    _create_version_table(
        isolated_engine,
        "baseline_r13_0059",
    )

    assert (
        database.database_migration_heads()
        == (
            "baseline_r13_0059",
        )
    )


def test_verify_database_head_accepts_exact_match(
    monkeypatch,
):
    monkeypatch.setattr(
        database,
        "repository_migration_head",
        lambda: "baseline_r13_0059",
    )

    monkeypatch.setattr(
        database,
        "database_migration_heads",
        lambda: (
        "baseline_r13_0059",
        ),
    )

    assert (
        database.verify_database_migration_head()
        == "baseline_r13_0059"
    )


def test_verify_database_head_rejects_missing_version(
    monkeypatch,
):
    monkeypatch.setattr(
        database,
        "repository_migration_head",
        lambda: "baseline_r13_0059",
    )

    monkeypatch.setattr(
        database,
        "database_migration_heads",
        lambda: (),
    )

    with pytest.raises(
        RuntimeError,
        match="expected",
    ):
        database.verify_database_migration_head()


def test_verify_database_head_rejects_stale_version(
    monkeypatch,
):
    monkeypatch.setattr(
        database,
        "repository_migration_head",
        lambda: "baseline_r13_0059",
    )

    monkeypatch.setattr(
        database,
        "database_migration_heads",
        lambda: (
            "0058_source_intake_ledger",
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="0058_source_intake_ledger",
    ):
        database.verify_database_migration_head()


def test_verify_database_head_rejects_multiple_heads(
    monkeypatch,
):
    monkeypatch.setattr(
        database,
        "repository_migration_head",
        lambda: "baseline_r13_0059",
    )

    monkeypatch.setattr(
        database,
        "database_migration_heads",
        lambda: (
            "baseline_r13_0059",
            "synthetic_second_head",
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="synthetic_second_head",
    ):
        database.verify_database_migration_head()


@pytest.mark.parametrize(
    "app_env",
    [
        "AZURE-PREPROD",
        "PROD",
    ],
)
def test_init_db_is_forbidden_outside_dev_and_test(
    monkeypatch,
    app_env,
):
    _set_environment(
        monkeypatch,
        app_env,
    )

    create_all_called = False

    def forbidden_create_all(
        *args,
        **kwargs,
    ):
        nonlocal create_all_called
        create_all_called = True

    monkeypatch.setattr(
        database.Base.metadata,
        "create_all",
        forbidden_create_all,
    )

    with pytest.raises(
        RuntimeError,
        match="restricted to DEV/TEST",
    ):
        database.init_db()

    assert create_all_called is False


def test_prepare_database_for_runtime_uses_local_bootstrap_only_in_test(
    monkeypatch,
):
    _set_environment(
        monkeypatch,
        "TEST",
    )

    calls: list[str] = []

    monkeypatch.setattr(
        database,
        "init_db",
        lambda: calls.append("init"),
    )

    monkeypatch.setattr(
        database,
        "verify_database_migration_head",
        lambda: (
            calls.append("verify")
            or "baseline_r13_0059"
        ),
    )

    result = (
        database.prepare_database_for_runtime()
    )

    assert result == "LOCAL_SCHEMA_BOOTSTRAP"
    assert calls == ["init"]


@pytest.mark.parametrize(
    "app_env",
    [
        "AZURE-PREPROD",
        "PROD",
    ],
)
def test_prepare_database_for_runtime_verifies_nonlocal_without_bootstrap(
    monkeypatch,
    app_env,
):
    _set_environment(
        monkeypatch,
        app_env,
    )

    calls: list[str] = []

    monkeypatch.setattr(
        database,
        "init_db",
        lambda: calls.append("init"),
    )

    monkeypatch.setattr(
        database,
        "verify_database_migration_head",
        lambda: (
            calls.append("verify")
            or "baseline_r13_0059"
        ),
    )

    result = (
        database.prepare_database_for_runtime()
    )

    assert (
        result
        == (
            "MIGRATION_VERIFIED:"
            "baseline_r13_0059"
        )
    )
    assert calls == ["verify"]
