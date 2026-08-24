from pathlib import Path
import os
from urllib.parse import parse_qs, urlsplit

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from .config.settings import get_settings
from .models import Base


settings = get_settings()

MSSQL_SQLALCHEMY_SCHEME = "mssql+pyodbc"
POSTGRES_CONNECT_TIMEOUT_SECONDS = 10
POSTGRES_POOL_RECYCLE_SECONDS = 1_800


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
    return create_engine(database_url, future=True, **_engine_options(database_url))

engine = create_database_engine(settings.database_url)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


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
