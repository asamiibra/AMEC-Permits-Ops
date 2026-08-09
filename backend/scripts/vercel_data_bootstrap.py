"""Safely migrate and seed the dedicated synthetic Vercel database at deploy time."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import func, inspect, select


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
os.chdir(REPO_ROOT)
sys.path.insert(0, str(REPO_ROOT))

from backend.app.config.settings import get_settings  # noqa: E402
from backend.app.db import SessionLocal, engine  # noqa: E402
from backend.app.fixtures.canonical import (  # noqa: E402
    CANONICAL_APPLICATION_IDS,
    CANONICAL_FIXTURE_ID,
    CANONICAL_FIXTURE_MANIFEST_HASH,
    CANONICAL_PROJECT_IDS,
)
from backend.app.models import (  # noqa: E402
    Base,
    AuditEvent,
    PermitApplication,
    Project,
    SyntheticFixtureSet,
)
from backend.app.seed.cli import seed  # noqa: E402


def alembic_config() -> Config:
    config = Config(str(REPO_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "migrations"))
    config.set_main_option("prepend_sys_path", str(REPO_ROOT))
    return config


def migration_versions() -> list[str]:
    inspector = inspect(engine)
    if "alembic_version" not in inspector.get_table_names():
        return []
    with engine.connect() as connection:
        return list(connection.exec_driver_sql("select version_num from alembic_version").scalars())


def table_counts() -> dict[str, int]:
    inspector = inspect(engine)
    counts: dict[str, int] = {}
    with engine.connect() as connection:
        for table_name in inspector.get_table_names():
            table = Base.metadata.tables.get(table_name)
            if table is not None:
                counts[table_name] = int(connection.execute(select(func.count()).select_from(table)).scalar_one())
    return counts


def ensure_current_schema() -> str:
    config = alembic_config()
    inspector = inspect(engine)
    versions = migration_versions()
    if versions:
        command.upgrade(config, "head")
        return "upgrade_head"

    expected_tables = set(Base.metadata.tables) - {"alembic_version"}
    existing_tables = set(inspector.get_table_names()) - {"alembic_version"}
    if expected_tables.issubset(existing_tables):
        command.stamp(config, "head")
        return "stamp_head_existing_current_schema"

    command.upgrade(config, "head")
    return "upgrade_head"


def main() -> None:
    settings = get_settings()
    if settings.app_env.upper() != "TEST" or not settings.synthetic_only:
        raise RuntimeError("Synthetic Vercel bootstrap requires APP_ENV=TEST and SYNTHETIC_ONLY=true")
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Synthetic Vercel bootstrap requires PostgreSQL; refusing SQLite or fallback state")

    with engine.connect() as connection:
        connection.exec_driver_sql("select 1")

    with SessionLocal() as db:
        fixture_rows = list(db.scalars(select(SyntheticFixtureSet).where(SyntheticFixtureSet.fixture_set_id == CANONICAL_FIXTURE_ID)).all())
        projects = list(db.scalars(select(Project).where(Project.project_number.in_(CANONICAL_PROJECT_IDS))).all())
        applications = list(db.scalars(select(PermitApplication).where(PermitApplication.external_request_number.in_(CANONICAL_APPLICATION_IDS))).all())
        if len(fixture_rows) > 1:
            raise RuntimeError("Multiple canonical synthetic fixture rows found; refusing to continue")
        if fixture_rows:
            fixture = fixture_rows[0]
            if fixture.manifest_sha256 != CANONICAL_FIXTURE_MANIFEST_HASH or len(projects) != len(CANONICAL_PROJECT_IDS) or len(applications) != len(CANONICAL_APPLICATION_IDS):
                raise RuntimeError("Canonical synthetic fixture is partial or inconsistent; refusing an automatic reset")
            migration_action = ensure_current_schema()
            print(f"synthetic_bootstrap=noop fixture={CANONICAL_FIXTURE_ID} migration={migration_action}")
            return

    counts_before = table_counts()
    nonempty_tables = {name: count for name, count in counts_before.items() if count}
    audit_only = set(nonempty_tables) == {AuditEvent.__tablename__}
    if audit_only:
        with SessionLocal() as db:
            audit_events = list(db.scalars(select(AuditEvent)).all())
            audit_only = bool(audit_events) and all(event.actor_type == "DEV_USER" and event.event_type == "ROLE_FILTER_APPLIED" for event in audit_events)
    if nonempty_tables and not audit_only:
        raise RuntimeError(f"Non-empty database without canonical fixture; refusing reset tables={sorted(nonempty_tables)}")

    migration_action = ensure_current_schema()
    seed()

    with SessionLocal() as db:
        fixture = db.scalar(select(SyntheticFixtureSet).where(SyntheticFixtureSet.fixture_set_id == CANONICAL_FIXTURE_ID))
        projects = list(db.scalars(select(Project).where(Project.project_number.in_(CANONICAL_PROJECT_IDS))).all())
        applications = list(db.scalars(select(PermitApplication).where(PermitApplication.external_request_number.in_(CANONICAL_APPLICATION_IDS))).all())
        if not fixture or fixture.manifest_sha256 != CANONICAL_FIXTURE_MANIFEST_HASH or len(projects) != len(CANONICAL_PROJECT_IDS) or len(applications) != len(CANONICAL_APPLICATION_IDS):
            raise RuntimeError("Canonical synthetic bootstrap verification failed")
    print(f"synthetic_bootstrap=seeded fixture={CANONICAL_FIXTURE_ID} migration={migration_action} projects={len(projects)} applications={len(applications)}")


if __name__ == "__main__":
    main()
