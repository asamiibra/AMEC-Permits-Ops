"""Provision the least-privilege PostgreSQL runtime role."""

from __future__ import annotations

import os
from urllib.parse import unquote, urlsplit

import psycopg
from psycopg import sql


def _parts(url: str) -> tuple[str, str, str, int, str, str]:
    dsn = url.replace("postgresql+psycopg://", "postgresql://", 1)
    parsed = urlsplit(dsn)
    if parsed.scheme != "postgresql" or not parsed.hostname or not parsed.username:
        raise RuntimeError("PostgreSQL URL with username is required")
    database = parsed.path.lstrip("/")
    if not database:
        raise RuntimeError("PostgreSQL database is required")
    try:
        port = parsed.port or 5432
    except ValueError as exc:
        raise RuntimeError("PostgreSQL port is invalid") from exc
    return (
        unquote(parsed.username),
        unquote(parsed.password or ""),
        parsed.hostname.lower(),
        port,
        database,
        dsn,
    )


def provision_roles(environ: dict[str, str] | None = None) -> None:
    env = environ or os.environ
    migration_url = env.get("DATABASE_MIGRATION_URL", "")
    runtime_url = env.get("DATABASE_URL", "")
    if not migration_url or not runtime_url:
        raise RuntimeError("DATABASE_MIGRATION_URL and DATABASE_URL are required")
    admin_user, _, admin_host, admin_port, database, admin_dsn = _parts(migration_url)
    runtime_user, runtime_password, runtime_host, runtime_port, runtime_database, _ = _parts(runtime_url)
    if (
        runtime_host != admin_host
        or runtime_port != admin_port
        or runtime_database != database
    ):
        raise RuntimeError("migration and runtime database targets must match")
    if admin_user == runtime_user:
        raise RuntimeError("migration and runtime PostgreSQL users must differ")
    if not runtime_password:
        raise RuntimeError("runtime PostgreSQL password is required")

    with psycopg.connect(admin_dsn) as connection:
        with connection.cursor() as cursor:
            role = sql.Identifier(runtime_user)
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (runtime_user,))
            if cursor.fetchone() is None:
                cursor.execute(sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(role), (runtime_password,))
            else:
                cursor.execute(sql.SQL("ALTER ROLE {} LOGIN PASSWORD %s NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS").format(role), (runtime_password,))
            cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(database), role))
            cursor.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(role))
            cursor.execute(sql.SQL("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {}").format(role))
            cursor.execute(sql.SQL("GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO {}").format(role))
            cursor.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {}").format(role))
            cursor.execute(sql.SQL("ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO {}").format(role))
        connection.commit()


if __name__ == "__main__":
    provision_roles()
    print("proposalops_db_roles=PROVISIONED")
