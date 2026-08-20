from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from .config.settings import get_settings
from .models import Base


settings = get_settings()

connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=connect_args,
    future=True,
)

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


def database_migration_heads() -> tuple[str, ...]:
    with engine.connect() as connection:
        context = MigrationContext.configure(
            connection
        )

        return tuple(
            sorted(
                context.get_current_heads()
            )
        )


def verify_database_migration_head() -> str:
    expected = repository_migration_head()
    current = database_migration_heads()

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
