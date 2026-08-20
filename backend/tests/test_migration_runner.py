from types import SimpleNamespace

import pytest

from backend.app import migrate


def _settings(
    *,
    app_env: str = "AZURE-PREPROD",
    database_url: str = (
        "postgresql+psycopg://user:pass@db/"
        "proposalops"
    ),
    synthetic_only: bool = True,
    real_data_allowed: bool = False,
):
    return SimpleNamespace(
        app_env=app_env,
        database_url=database_url,
        synthetic_only=synthetic_only,
        real_data_allowed=real_data_allowed,
    )


def test_alembic_config_is_programmatic_and_packaged():
    config = migrate._alembic_config(
        "postgresql+psycopg://u:p@db/app"
    )

    assert config.config_file_name is None
    assert config.get_main_option(
        "script_location"
    ).endswith("backend/migrations")


def test_alembic_config_escapes_percent_signs():
    config = migrate._alembic_config(
        "postgresql+psycopg://u:p%25@db/app"
    )

    assert (
        config.get_main_option(
            "sqlalchemy.url"
        )
        == (
            "postgresql+psycopg://"
            "u:p%25@db/app"
        )
    )


@pytest.mark.parametrize(
    "app_env",
    [
        "DEV",
        "TEST",
        "PROD",
    ],
)
def test_runner_rejects_non_preprod_environment(
    monkeypatch,
    app_env,
):
    monkeypatch.setattr(
        migrate,
        "get_settings",
        lambda: _settings(
            app_env=app_env
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="restricted",
    ):
        migrate.run_migrations()


def test_runner_requires_synthetic_only(
    monkeypatch,
):
    monkeypatch.setattr(
        migrate,
        "get_settings",
        lambda: _settings(
            synthetic_only=False
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="SYNTHETIC_ONLY",
    ):
        migrate.run_migrations()


def test_runner_rejects_real_data_allowed(
    monkeypatch,
):
    monkeypatch.setattr(
        migrate,
        "get_settings",
        lambda: _settings(
            real_data_allowed=True
        ),
    )

    with pytest.raises(
        RuntimeError,
        match="REAL_DATA_ALLOWED",
    ):
        migrate.run_migrations()


def test_runner_requires_psycopg_postgresql(
    monkeypatch,
):
    monkeypatch.setattr(
        migrate,
        "get_settings",
        lambda: _settings(
            database_url="sqlite:///unsafe.db"
        ),
    )

    with pytest.raises(
        RuntimeError,
        match=r"postgresql\+psycopg",
    ):
        migrate.run_migrations()


def test_runner_upgrades_head_then_verifies(
    monkeypatch,
):
    calls: list[str] = []

    monkeypatch.setattr(
        migrate,
        "get_settings",
        lambda: _settings(),
    )

    monkeypatch.setattr(
        migrate,
        "repository_migration_head",
        lambda: (
            calls.append("expected")
            or "0059_entra_user_identity"
        ),
    )

    def upgrade(config, revision):
        assert config.config_file_name is None
        assert revision == "head"
        calls.append("upgrade")

    monkeypatch.setattr(
        migrate.command,
        "upgrade",
        upgrade,
    )

    monkeypatch.setattr(
        migrate,
        "verify_database_migration_head",
        lambda: (
            calls.append("verify")
            or "0059_entra_user_identity"
        ),
    )

    assert (
        migrate.run_migrations()
        == "0059_entra_user_identity"
    )

    assert calls == [
        "expected",
        "upgrade",
        "verify",
    ]


def test_runner_rejects_unexpected_verified_head(
    monkeypatch,
):
    monkeypatch.setattr(
        migrate,
        "get_settings",
        lambda: _settings(),
    )

    monkeypatch.setattr(
        migrate,
        "repository_migration_head",
        lambda: "0059_entra_user_identity",
    )

    monkeypatch.setattr(
        migrate.command,
        "upgrade",
        lambda config, revision: None,
    )

    monkeypatch.setattr(
        migrate,
        "verify_database_migration_head",
        lambda: "synthetic_wrong_head",
    )

    with pytest.raises(
        RuntimeError,
        match="unexpected",
    ):
        migrate.run_migrations()


def test_main_success_is_structured(
    monkeypatch,
    capsys,
):
    monkeypatch.setattr(
        migrate,
        "run_migrations",
        lambda: "0059_entra_user_identity",
    )

    assert migrate.main() == 0

    output = capsys.readouterr()

    assert '"status": "SUCCEEDED"' in output.out
    assert "0059_entra_user_identity" in output.out
    assert output.err == ""


def test_main_failure_is_nonzero_and_redacted(
    monkeypatch,
    capsys,
):
    secret = "postgresql://user:secret@db/app"

    def fail():
        raise RuntimeError(secret)

    monkeypatch.setattr(
        migrate,
        "run_migrations",
        fail,
    )

    assert migrate.main() == 1

    output = capsys.readouterr()

    assert '"status": "FAILED"' in output.err
    assert "RuntimeError" in output.err
    assert secret not in output.err
