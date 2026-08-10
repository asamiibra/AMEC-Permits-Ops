from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
from .config.settings import get_settings
from .models import Base

settings = get_settings()
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    # The local synthetic database is intentionally long-lived between runs,
    # while the expansion models evolve additively.  Keep that developer DB
    # bootable without requiring a destructive reset; production migrations
    # remain the deployment responsibility.
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            inspector = inspect(connection)
            for table_model in Base.metadata.tables.values():
                table = table_model.name
                columns = {column.name: column for column in table_model.columns}
                existing = {column["name"] for column in inspector.get_columns(table)}
                for name, column in columns.items():
                    if name not in existing:
                        sql_type = column.type.compile(dialect=engine.dialect)
                        connection.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))
            if "opportunities" in inspector.get_table_names():
                connection.execute(text("UPDATE opportunities SET reference_state = 'PROVISIONAL' WHERE reference_state IS NULL"))
                connection.execute(text("UPDATE opportunities SET proposal_fields_json = '{}' WHERE proposal_fields_json IS NULL"))


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
