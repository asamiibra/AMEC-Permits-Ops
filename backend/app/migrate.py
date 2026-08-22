from __future__ import annotations

import json
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

from .config.settings import get_settings
from .db import (
    create_database_engine,
    repository_migration_head,
    validate_postgres_tls_url,
    verify_database_migration_head,
)


def _migration_script_location() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "migrations"
    )


def _alembic_config(
    database_url: str,
) -> Config:
    config = Config()

    config.set_main_option(
        "script_location",
        str(_migration_script_location()),
    )

    config.set_main_option(
        "sqlalchemy.url",
        database_url.replace("%", "%%"),
    )

    return config


def run_migrations() -> str:
    settings = get_settings()
    environment = settings.app_env.upper()

    if environment != "AZURE-PREPROD":
        raise RuntimeError(
            "The deployment migration runner is "
            "restricted to AZURE-PREPROD."
        )

    if not settings.synthetic_only:
        raise RuntimeError(
            "AZURE-PREPROD migration execution "
            "requires SYNTHETIC_ONLY=true."
        )

    if settings.real_data_allowed:
        raise RuntimeError(
            "AZURE-PREPROD migration execution "
            "requires REAL_DATA_ALLOWED=false."
        )

    if not settings.database_url.lower().startswith(
        "postgresql+psycopg://"
    ):
        raise RuntimeError(
            "AZURE-PREPROD migrations require "
            "PostgreSQL via postgresql+psycopg://."
        )

    expected_head = repository_migration_head()

    configured_migration_url = getattr(settings, "database_migration_url", "")
    migration_url = configured_migration_url or settings.database_url
    if configured_migration_url:
        validate_postgres_tls_url(migration_url)
    config = _alembic_config(migration_url)

    command.upgrade(
        config,
        "head",
    )

    if configured_migration_url:
        migration_engine = create_database_engine(migration_url)
        try:
            verified_head = verify_database_migration_head(migration_engine)
        finally:
            migration_engine.dispose()
    else:
        verified_head = verify_database_migration_head()

    if verified_head != expected_head:
        raise RuntimeError(
            "Migration verification returned an "
            "unexpected repository head."
        )

    return verified_head


def main() -> int:
    try:
        head = run_migrations()
    except Exception as exc:
        print(
            json.dumps(
                {
                    "event": "proposalops_migration",
                    "status": "FAILED",
                    "error_class": (
                        type(exc).__name__
                    ),
                },
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "event": "proposalops_migration",
                "status": "SUCCEEDED",
                "migration_head": head,
            },
            sort_keys=True,
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
