import base64
import binascii
import json
from pathlib import Path
import os
import re
import struct
import urllib.parse
import urllib.request
from urllib.parse import parse_qs, urlsplit
from uuid import UUID

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from .config.settings import get_settings
from .models import Base


settings = get_settings()

MSSQL_SQLALCHEMY_SCHEME = "mssql+pyodbc"
POSTGRES_CONNECT_TIMEOUT_SECONDS = 10
POSTGRES_POOL_RECYCLE_SECONDS = 1_800
SQL_COPT_SS_ACCESS_TOKEN = 1256
AZURE_SQL_RESOURCE = "https://database.windows.net/"
AZURE_IDENTITY_API_VERSION = "2019-08-01"


def validate_postgres_tls_url(database_url: str, *, environ: dict[str, str] | None = None) -> None:
    parsed = urlsplit(database_url)
    if not parsed.hostname or not parsed.hostname.lower().endswith(".postgres.database.azure.com"):
        return
    query = parse_qs(parsed.query, keep_blank_values=True)
    sslmode = (query.get("sslmode", [""])[0] or "").lower()
    if sslmode not in {"verify-full", "verify-ca"}:
        raise ValueError("Azure PostgreSQL requires sslmode=verify-full or sslmode=verify-ca")
    environment = environ if environ is not None else os.environ
    root_cert = query.get("sslrootcert", [""])[0] or environment.get("PGSSLROOTCERT", "")
    if not root_cert:
        raise ValueError("Azure PostgreSQL requires sslrootcert or PGSSLROOTCERT")


def validate_mssql_connection_url(database_url: str, *, require_encryption: bool = False) -> None:
    """Validate the SQL Server connection contract without inspecting secrets."""
    parsed = urlsplit(database_url)
    if not parsed.scheme.lower().startswith("mssql+"):
        return
    query = {key.lower(): value[-1] for key, value in parse_qs(parsed.query, keep_blank_values=True).items()}
    if require_encryption or (parsed.hostname or "").lower().endswith(".database.windows.net"):
        if query.get("encrypt", "").lower() != "yes":
            raise ValueError("Azure SQL requires Encrypt=yes")
        if query.get("trustservercertificate", "").lower() != "no":
            raise ValueError("Azure SQL requires TrustServerCertificate=no")


def _engine_options(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    if database_url.lower().startswith(MSSQL_SQLALCHEMY_SCHEME):
        validate_mssql_connection_url(database_url)
        return {
            "connect_args": {"timeout": POSTGRES_CONNECT_TIMEOUT_SECONDS},
            "pool_pre_ping": True,
            "pool_recycle": POSTGRES_POOL_RECYCLE_SECONDS,
        }
    validate_postgres_tls_url(database_url)
    return {
        "connect_args": {"connect_timeout": POSTGRES_CONNECT_TIMEOUT_SECONDS},
        "pool_pre_ping": True,
        "pool_recycle": POSTGRES_POOL_RECYCLE_SECONDS,
    }


def create_database_engine(database_url: str):
    active_engine = create_engine(database_url, future=True, **_engine_options(database_url))
    if (
        database_url.lower().startswith(MSSQL_SQLALCHEMY_SCHEME)
        and get_settings().azure_sql_auth_mode.upper()
        == "MANAGED_IDENTITY_ACCESS_TOKEN"
    ):
        event.listen(active_engine, "do_connect", _inject_azure_sql_access_token)
    return active_engine


def _token_claims(token: str) -> dict[str, str | None]:
    parts = token.split(".")
    if len(parts) != 3:
        return {"aud": None, "oid": None, "tid": None}
    encoded_body = parts[1] + ("=" * (-len(parts[1]) % 4))
    try:
        claims = json.loads(
            base64.urlsafe_b64decode(encoded_body.encode("ascii")).decode("utf-8")
        )
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error):
        return {"aud": None, "oid": None, "tid": None}
    if not isinstance(claims, dict):
        return {"aud": None, "oid": None, "tid": None}
    return {
        "aud": claims.get("aud"),
        "oid": claims.get("oid"),
        "tid": claims.get("tid"),
    }


def _is_azure_sql_audience(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme.lower() == "https"
        and parsed.hostname is not None
        and parsed.hostname.lower() == "database.windows.net"
        and port is None
        and parsed.username is None
        and parsed.password is None
        and parsed.path in {"", "/"}
        and not parsed.query
        and not parsed.fragment
    )


def _guid_equal(left: object, right: object) -> bool:
    try:
        return UUID(str(left)) == UUID(str(right))
    except (ValueError, AttributeError, TypeError):
        return False


def _validate_azure_sql_token_claims(
    claims: dict[str, object],
    *,
    principal_id: str,
    tenant_id: str,
) -> None:
    if (
        not _is_azure_sql_audience(claims.get("aud"))
        or not _guid_equal(claims.get("oid"), principal_id)
        or not _guid_equal(claims.get("tid"), tenant_id)
    ):
        raise RuntimeError("ACA managed-identity token claims mismatch")


def _remove_sqlalchemy_trusted_connection(connection_args: object) -> str:
    if not isinstance(connection_args, list) or len(connection_args) != 1:
        raise RuntimeError(
            "Azure SQL token authentication requires exactly one ODBC connection string"
        )
    connection_string = connection_args[0]
    if not isinstance(connection_string, str):
        raise RuntimeError(
            "Azure SQL token authentication requires an ODBC connection string"
        )

    # SQLAlchemy's mssql+pyodbc dialect adds this credential when no URL
    # username/password is present. Remove that generated setting only; all
    # other connection-string settings remain byte-for-byte untouched.
    cleaned = ";".join(
        segment
        for segment in connection_string.split(";")
        if not re.fullmatch(
            r"\s*trusted_connection\s*=\s*yes\s*",
            segment,
            flags=re.IGNORECASE,
        )
    )
    forbidden = ("uid=", "pwd=", "authentication=", "trusted_connection=")
    if any(item in cleaned.lower() for item in forbidden):
        raise RuntimeError(
            "Azure SQL token authentication forbids credential-bearing ODBC settings"
        )
    connection_args[0] = cleaned
    return cleaned


def _azure_sql_access_token() -> str:
    endpoint = os.getenv("IDENTITY_ENDPOINT")
    identity_header = os.getenv("IDENTITY_HEADER")
    client_id = get_settings().azure_sql_uami_client_id
    principal_id = get_settings().azure_sql_uami_principal_id
    tenant_id = get_settings().entra_tenant_id
    if not endpoint or not identity_header:
        raise RuntimeError(
            "AZURE-PREPROD requires IDENTITY_ENDPOINT and IDENTITY_HEADER"
        )

    query = urllib.parse.urlencode(
        {
            "resource": AZURE_SQL_RESOURCE,
            "api-version": AZURE_IDENTITY_API_VERSION,
            "client_id": client_id,
        }
    )
    request = urllib.request.Request(
        endpoint + "?" + query,
        headers={"X-IDENTITY-HEADER": identity_header},
    )
    with urllib.request.urlopen(request, timeout=POSTGRES_CONNECT_TIMEOUT_SECONDS) as response:
        if response.status != 200:
            raise RuntimeError(
                f"ACA managed-identity token endpoint returned HTTP {response.status}"
            )
        body = json.loads(response.read().decode("utf-8"))

    token = body.get("access_token")
    claims = _token_claims(token) if isinstance(token, str) else {}
    if not isinstance(token, str) or not _guid_equal(body.get("client_id"), client_id):
        raise RuntimeError("ACA managed-identity token claims mismatch")
    _validate_azure_sql_token_claims(
        claims,
        principal_id=principal_id,
        tenant_id=tenant_id,
    )
    return token


def _inject_azure_sql_access_token(dialect, connection_record, connection_args, connection_kwargs):
    del dialect, connection_record
    _remove_sqlalchemy_trusted_connection(connection_args)
    token_bytes = _azure_sql_access_token().encode("utf-16-le")
    packed_token = struct.pack("<I", len(token_bytes)) + token_bytes
    existing_attrs = connection_kwargs.get("attrs_before")
    if existing_attrs is None:
        existing_attrs = {}
    if not isinstance(existing_attrs, dict):
        raise RuntimeError("Azure SQL token authentication requires attrs_before mapping")
    attrs_before = dict(existing_attrs)
    attrs_before[SQL_COPT_SS_ACCESS_TOKEN] = packed_token
    connection_kwargs["attrs_before"] = attrs_before

def _migration_script_location() -> Path:
    return (
        Path(__file__).resolve().parents[1]
        / "migrations"
    )


def repository_migration_head() -> str:
    config = Config()
    config.set_main_option(
        "script_location",
        str(_migration_script_location()),
    )

    try:
        script = ScriptDirectory.from_config(
            config
        )
        heads = tuple(
            sorted(script.get_heads())
        )
    except Exception as exc:
        raise RuntimeError(
            "Unable to load the repository "
            "Alembic migration graph"
        ) from exc

    if len(heads) != 1:
        raise RuntimeError(
            "ProposalOps requires exactly one "
            "repository Alembic head; found "
            f"{heads or 'NONE'}"
        )

    return heads[0]


def database_migration_heads(database_engine=None) -> tuple[str, ...]:
    active_engine = database_engine or engine
    with active_engine.connect() as connection:
        context = MigrationContext.configure(
            connection
        )

        return tuple(
            sorted(
                context.get_current_heads()
            )
        )


def verify_database_migration_head(database_engine=None) -> str:
    expected = repository_migration_head()
    current = (
        database_migration_heads()
        if database_engine is None
        else database_migration_heads(database_engine)
    )

    if current != (expected,):
        raise RuntimeError(
            "Database migration state is not "
            "ready for application startup: "
            f"expected ({expected!r},), "
            f"found {current or 'NONE'}. "
            "Run the dedicated Alembic migration "
            "step before starting the API."
        )

    return expected


def init_db() -> None:
    environment = settings.app_env.upper()

    if environment not in {
        "DEV",
        "TEST",
    }:
        raise RuntimeError(
            "init_db is restricted to DEV/TEST. "
            "Non-local environments must use "
            "Alembic migrations before API startup."
        )

    Base.metadata.create_all(bind=engine)

    # The local synthetic database is intentionally long-lived between runs,
    # while the expansion models evolve additively. Keep that developer DB
    # bootable without requiring a destructive reset. This compatibility path
    # is local-only; deployment schema changes belong to Alembic.
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            inspector = inspect(connection)

            for table_model in (
                Base.metadata.tables.values()
            ):
                table = table_model.name

                columns = {
                    column.name: column
                    for column
                    in table_model.columns
                }

                existing = {
                    column["name"]
                    for column
                    in inspector.get_columns(
                        table
                    )
                }

                for name, column in (
                    columns.items()
                ):
                    if name in existing:
                        continue

                    sql_type = (
                        column.type.compile(
                            dialect=engine.dialect
                        )
                    )

                    connection.execute(
                        text(
                            f"ALTER TABLE {table} "
                            f"ADD COLUMN {name} "
                            f"{sql_type}"
                        )
                    )

            if (
                "opportunities"
                in inspector.get_table_names()
            ):
                connection.execute(
                    text(
                        "UPDATE opportunities "
                        "SET reference_state = "
                        "'PROVISIONAL' "
                        "WHERE reference_state "
                        "IS NULL"
                    )
                )

                connection.execute(
                    text(
                        "UPDATE opportunities "
                        "SET proposal_fields_json "
                        "= '{}' "
                        "WHERE proposal_fields_json "
                        "IS NULL"
                    )
                )


def prepare_database_for_runtime() -> str:
    environment = settings.app_env.upper()

    if environment in {
        "DEV",
        "TEST",
    }:
        init_db()

        return "LOCAL_SCHEMA_BOOTSTRAP"

    if environment in {
        "AZURE-PREPROD",
        "PROD",
    }:
        head = verify_database_migration_head()

        return (
            f"MIGRATION_VERIFIED:{head}"
        )

    raise RuntimeError(
        "Unsupported application environment "
        f"for database startup: {environment}"
    )


def get_db():
    db: Session = SessionLocal()

    try:
        yield db
    finally:
        db.close()


engine = create_database_engine(settings.database_url)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)
