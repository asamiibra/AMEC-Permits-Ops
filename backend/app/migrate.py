from __future__ import annotations

import json
import os
import re
import sys
import time
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Any

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext

from .config.settings import get_settings
from .db import (
    create_database_engine,
    repository_migration_head,
    validate_mssql_connection_url,
    validate_postgres_tls_url,
)


MAX_CONNECTION_ATTEMPTS = 3
MAX_CONNECTION_WAIT_SECONDS = 30
CONNECTION_RETRY_DELAY_SECONDS = 2


class MigrationExecutionError(RuntimeError):
    """Wrap one migration failure with a safe execution phase."""

    def __init__(self, phase: str, cause: BaseException) -> None:
        super().__init__(str(cause))
        self.phase = phase
        self.cause = cause


class MigrationConnectionUnavailable(RuntimeError):
    """Raised when no pre-DDL connection can be acquired."""

    def __init__(self, message: str, *, attempts: int) -> None:
        super().__init__(message)
        self.attempts = attempts


def _migration_script_location() -> Path:
    return Path(__file__).resolve().parents[1] / "migrations"


def _alembic_config(database_url: str) -> Config:
    config = Config()
    config.set_main_option("script_location", str(_migration_script_location()))
    config.set_main_option(
        "sqlalchemy.url",
        database_url.replace("%", "%%"),
    )
    return config


@contextmanager
def _migration_authority_scope(database_url: str):
    had_database_url = "DATABASE_URL" in os.environ
    original_database_url = os.environ.get("DATABASE_URL")
    clear_settings_cache = getattr(get_settings, "cache_clear", None)
    try:
        os.environ["DATABASE_URL"] = database_url
        if clear_settings_cache is not None:
            clear_settings_cache()
        yield
    finally:
        if had_database_url:
            os.environ["DATABASE_URL"] = original_database_url or ""
        else:
            os.environ.pop("DATABASE_URL", None)
        if clear_settings_cache is not None:
            clear_settings_cache()


def _sanitize_text(value: object, *, limit: int = 4000) -> str | None:
    if value is None:
        return None
    text = str(value)
    text = re.sub(
        r"(?i)(?:mssql\+pyodbc|postgresql\+psycopg|postgresql)://[^\s'\"]+",
        "<redacted-database-url>",
        text,
    )
    text = re.sub(
        r"(?i)\b(?:bearer|access_token|identity_header|authorization)\s*[=:]\s*[^\s,;]+",
        "<redacted-token>",
        text,
    )
    text = re.sub(
        r"(?i)(?:password|pwd|secret|token)\s*=\s*[^;\s]+",
        "<redacted-secret>",
        text,
    )
    return text[:limit]


def _native_error_details(error: BaseException) -> tuple[str | None, int | None]:
    original = getattr(error, "orig", error)
    args = getattr(original, "args", ()) or ()
    sqlstate: str | None = None
    native_number: int | None = None
    for value in args:
        match = re.search(r"\b([0-9A-Z]{5})\b", str(value), re.IGNORECASE)
        if match and sqlstate is None:
            sqlstate = match.group(1).upper()
        number_match = re.search(r"\((\d{3,6})\)", str(value))
        if number_match and native_number is None:
            native_number = int(number_match.group(1))
    return sqlstate, native_number


def _diagnostic_payload(
    error: BaseException,
    *,
    phase: str,
    expected_head: str | None,
    connection_attempts: int,
    migration_execution_count: int,
) -> dict[str, Any]:
    cause = error.cause if isinstance(error, MigrationExecutionError) else error
    sqlstate, native_number = _native_error_details(cause)
    return {
        "event": "proposalops_migration",
        "status": "FAILED",
        "error_class": type(cause).__name__,
        "sqlalchemy_error_code": getattr(cause, "code", None),
        "sqlstate": sqlstate,
        "native_error_number": native_number,
        "sanitized_message": _sanitize_text(getattr(cause, "orig", cause)),
        "sanitized_statement": _sanitize_text(getattr(cause, "statement", None)),
        "migration_head_expected": expected_head,
        "migration_phase": phase,
        "connection_attempts": connection_attempts,
        "migration_execution_count": migration_execution_count,
    }


def _verify_head_on_connection(connection, expected_head: str) -> str:
    heads = tuple(sorted(MigrationContext.configure(connection).get_current_heads()))
    if heads != (expected_head,):
        raise RuntimeError(
            "Migration verification returned an unexpected repository head: "
            f"expected ({expected_head!r},), found {heads or 'NONE'}."
        )
    return heads[0]


def _connect_with_bounded_attempts(engine):
    started = time.monotonic()
    last_error: BaseException | None = None
    for attempt in range(1, MAX_CONNECTION_ATTEMPTS + 1):
        connection = None
        try:
            connection = engine.connect()
            connection.exec_driver_sql("SELECT 1")
            rollback = getattr(connection, "rollback", None)
            if rollback is not None:
                rollback()
            if hasattr(connection, "in_transaction"):
                in_transaction = connection.in_transaction
                if callable(in_transaction):
                    in_transaction = in_transaction()
                if in_transaction:
                    raise RuntimeError(
                        "Migration preflight transaction remained active."
                    )
            return connection, attempt
        except Exception as exc:
            last_error = exc
            if connection is not None:
                connection.close()
            if attempt == MAX_CONNECTION_ATTEMPTS:
                break
            if time.monotonic() - started + CONNECTION_RETRY_DELAY_SECONDS > MAX_CONNECTION_WAIT_SECONDS:
                break
            time.sleep(CONNECTION_RETRY_DELAY_SECONDS)
    raise MigrationConnectionUnavailable(
        "AZURE_SQL_CONNECTION_UNAVAILABLE_BEFORE_MIGRATION",
        attempts=attempt,
    ) from last_error


def run_migrations() -> str:
    settings = get_settings()
    environment = settings.app_env.upper()
    if environment != "AZURE-PREPROD":
        raise RuntimeError(
            "The deployment migration runner is restricted to AZURE-PREPROD."
        )
    if not settings.synthetic_only:
        raise RuntimeError(
            "AZURE-PREPROD migration execution requires SYNTHETIC_ONLY=true."
        )
    if settings.real_data_allowed:
        raise RuntimeError(
            "AZURE-PREPROD migration execution requires REAL_DATA_ALLOWED=false."
        )

    database_url = settings.database_url.lower()
    if not (
        database_url.startswith("postgresql+psycopg://")
        or database_url.startswith("mssql+pyodbc://")
    ):
        raise RuntimeError(
            "AZURE-PREPROD migrations require PostgreSQL via "
            "postgresql+psycopg:// or Azure SQL via mssql+pyodbc://."
        )

    expected_head = repository_migration_head()
    configured_migration_url = getattr(settings, "database_migration_url", "")
    migration_url = configured_migration_url or settings.database_url
    if configured_migration_url:
        if migration_url.lower().startswith("mssql+"):
            validate_mssql_connection_url(migration_url, require_encryption=True)
        else:
            validate_postgres_tls_url(migration_url)

    migration_scope = (
        _migration_authority_scope(migration_url)
        if configured_migration_url
        else nullcontext()
    )
    engine = None
    connection = None
    connection_attempts = 0
    with migration_scope:
        engine = create_database_engine(migration_url)
        try:
            try:
                connection, connection_attempts = _connect_with_bounded_attempts(engine)
            except MigrationConnectionUnavailable:
                raise
            except Exception as exc:
                wrapped = MigrationExecutionError("connection_preflight", exc)
                wrapped.expected_head = expected_head
                wrapped.connection_attempts = connection_attempts
                raise wrapped from exc

            config = _alembic_config(migration_url)
            config.attributes["connection"] = connection
            try:
                with connection.begin():
                    command.upgrade(config, "head")
            except Exception as exc:
                wrapped = MigrationExecutionError("alembic_upgrade", exc)
                wrapped.expected_head = expected_head
                wrapped.connection_attempts = connection_attempts
                raise wrapped from exc
            try:
                return _verify_head_on_connection(connection, expected_head)
            except Exception as exc:
                wrapped = MigrationExecutionError("post_upgrade_verification", exc)
                wrapped.expected_head = expected_head
                wrapped.connection_attempts = connection_attempts
                raise wrapped from exc
        finally:
            if connection is not None:
                connection.close()
            if engine is not None:
                engine.dispose()


def main() -> int:
    try:
        head = run_migrations()
    except MigrationConnectionUnavailable as exc:
        payload = {
            "event": "proposalops_migration",
            "status": "FAILED",
            "first_blocker": str(exc),
            "error_class": type(exc).__name__,
            "sqlstate": None,
            "native_error_number": None,
            "sanitized_message": str(exc),
            "sanitized_statement": None,
            "migration_head_expected": None,
            "migration_phase": "connection_preflight",
            "connection_attempts": exc.attempts,
            "migration_execution_count": 0,
        }
        print(json.dumps(payload, sort_keys=True), file=sys.stderr)
        return 1
    except Exception as exc:
        phase = exc.phase if isinstance(exc, MigrationExecutionError) else "preflight"
        payload = _diagnostic_payload(
            exc,
            phase=phase,
            expected_head=getattr(exc, "expected_head", None),
            connection_attempts=getattr(exc, "connection_attempts", 0),
            migration_execution_count=(
                1 if phase in {"alembic_upgrade", "post_upgrade_verification"} else 0
            ),
        )
        print(json.dumps(payload, sort_keys=True), file=sys.stderr)
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
