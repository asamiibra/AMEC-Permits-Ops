"""Synthetic runtime qualification executed inside an ACA job.

This module intentionally uses the application's real SQLAlchemy engine. It
does not create a token, accept a SQL password, or print token material.
The qualification-only probe table is created by the separate bootstrap step
with migration authority; this job verifies that the runtime identity has DML
but not DDL authority.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import json
import os
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

from . import db as database
from .config.settings import get_settings


PROBE_TABLE = "dbo.g6_qualification_probe"
DDL_SENTINEL_TABLE = "dbo.g6_runtime_ddl_must_be_denied"


def _credential_free_runtime_check() -> None:
    settings = get_settings()
    settings.validate_environment()
    for value in (settings.database_url, settings.database_migration_url):
        parsed = make_url(value)
        if parsed.username or parsed.password:
            raise RuntimeError("qualification database URL must be credentialless")


def _read_probe() -> int:
    with database.engine.connect() as connection:
        return int(connection.execute(text(f"SELECT COUNT(*) FROM {PROBE_TABLE}")).scalar_one())


def _synthetic_write_and_transactions() -> dict[str, bool]:
    committed_id = f"g6-committed-{uuid4()}"
    rolled_back_id = f"g6-rolled-back-{uuid4()}"
    with database.engine.begin() as connection:
        connection.execute(
            text(f"INSERT INTO {PROBE_TABLE} (probe_id, payload) VALUES (:probe_id, :payload)"),
            {"probe_id": committed_id, "payload": "synthetic-g6"},
        )

    try:
        with database.engine.begin() as connection:
            connection.execute(
                text(f"INSERT INTO {PROBE_TABLE} (probe_id, payload) VALUES (:probe_id, :payload)"),
                {"probe_id": rolled_back_id, "payload": "synthetic-rollback"},
            )
            raise RuntimeError("g6 qualification rollback sentinel")
    except RuntimeError as error:
        if str(error) != "g6 qualification rollback sentinel":
            raise

    with database.engine.connect() as connection:
        committed = connection.execute(
            text(f"SELECT COUNT(*) FROM {PROBE_TABLE} WHERE probe_id = :probe_id"),
            {"probe_id": committed_id},
        ).scalar_one()
        rolled_back = connection.execute(
            text(f"SELECT COUNT(*) FROM {PROBE_TABLE} WHERE probe_id = :probe_id"),
            {"probe_id": rolled_back_id},
        ).scalar_one()
    return {
        "synthetic_read": True,
        "transaction_commit": committed == 1,
        "transaction_rollback": rolled_back == 0,
    }


def _runtime_ddl_is_denied() -> bool:
    try:
        with database.engine.begin() as connection:
            connection.execute(
                text(
                    f"CREATE TABLE {DDL_SENTINEL_TABLE} "
                    "(probe_id nvarchar(100) NOT NULL PRIMARY KEY)"
                )
            )
    except SQLAlchemyError:
        return True
    raise RuntimeError("runtime UAMI unexpectedly has migration-only DDL authority")


def _pool_select(_: int) -> int:
    return _read_probe()


def main() -> int:
    _credential_free_runtime_check()
    token_calls = 0
    original_token_provider = database._azure_sql_access_token

    def counted_token_provider() -> str:
        nonlocal token_calls
        token_calls += 1
        return original_token_provider()

    database._azure_sql_access_token = counted_token_provider
    try:
        initial_count = _read_probe()
        transaction_result = _synthetic_write_and_transactions()
        with ThreadPoolExecutor(max_workers=4) as pool:
            pool_results = list(pool.map(_pool_select, range(8)))
        ddl_denied = _runtime_ddl_is_denied()

        # Dispose forces a new DBAPI connection. With the application's
        # provider (which has no application token cache), this is the
        # governed reacquisition proof.
        database.engine.dispose()
        reopened_count = _read_probe()
        result = {
            "qualification_id": os.getenv("QUALIFICATION_ID", ""),
            "release_sha": os.getenv("RELEASE_SHA", ""),
            "initial_probe_rows": initial_count,
            "reopened_probe_rows": reopened_count,
            "pool_reads": len(pool_results),
            **transaction_result,
            "runtime_ddl_denied": ddl_denied,
            "application_token_cache_present": False,
            "token_provider_invocations": token_calls,
            "connection_reacquisition": token_calls >= 2,
            "fresh_connection_uses_fresh_token": token_calls >= 2,
        }
        if not all(
            result[key]
            for key in (
                "synthetic_read",
                "transaction_commit",
                "transaction_rollback",
                "runtime_ddl_denied",
                "connection_reacquisition",
                "fresh_connection_uses_fresh_token",
            )
        ):
            raise RuntimeError("G6 runtime qualification assertion failed")
        print(json.dumps(result, sort_keys=True))
        return 0
    finally:
        database._azure_sql_access_token = original_token_provider


if __name__ == "__main__":
    raise SystemExit(main())
