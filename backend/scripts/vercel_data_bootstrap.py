"""Safely migrate and seed the dedicated synthetic Vercel database at deploy time."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from datetime import datetime, timezone

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
    Contract,
    Opportunity,
    PermitApplication,
    Project,
    Quotation,
    SyntheticFixtureSet,
    WorkflowTask,
)
from backend.app.seed.cli import ensure_primary_proposal_sources, ensure_proposals_contracts_demo_state, seed  # noqa: E402
from backend.app.seed.persona_issues_notifications import seed_persona_issues_notifications  # noqa: E402
from backend.app.services.permit_workflow import ensure_project_sources_task  # noqa: E402


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


def reconcile_proposalops_fixture(db, projects: list[Project], applications: list[PermitApplication]) -> bool:
    """Repair only deterministic ProposalOps links in the known fixture.

    This is intentionally narrow and idempotent: it does not reset business
    records or invent sources, it only reconciles the existing synthetic
    opportunity/contract/permit chain to the canonical first project.
    """
    project = next((item for item in projects if item.project_number == CANONICAL_PROJECT_IDS[0]), None)
    application = next((item for item in applications if item.external_request_number == CANONICAL_APPLICATION_IDS[0]), None)
    opportunity = db.scalar(select(Opportunity).where(Opportunity.opportunity_reference == "SYN-OPP-0001"))
    if not project or not application or not opportunity:
        return False
    changed = False
    if opportunity.project_id != project.id:
        opportunity.project_id = project.id
        changed = True
    if opportunity.reference_state != "CANONICAL":
        opportunity.reference_state = "CANONICAL"
        changed = True
    if not opportunity.provisional_reference:
        opportunity.provisional_reference = opportunity.opportunity_reference
        changed = True
    if opportunity.canonical_project_reference != project.project_number:
        opportunity.canonical_project_reference = project.project_number
        changed = True
    if not opportunity.canonicalized_at:
        opportunity.canonicalized_at = datetime.now(timezone.utc)
        changed = True
    if not opportunity.canonicalized_by:
        opportunity.canonicalized_by = "owner@amec.synthetic"
        changed = True
    if not opportunity.proposal_fields_json:
        opportunity.proposal_fields_json = {
            "price": "QAR 125,000",
            "sow": "Building advisory and permit coordination",
            "period": "12 weeks",
            "exclusions": "Authority fees",
        }
        changed = True
    quotation = db.scalar(select(Quotation).where(Quotation.opportunity_id == opportunity.id).order_by(Quotation.created_at))
    contract = db.scalar(select(Contract).where(Contract.quotation_id == quotation.id).order_by(Contract.created_at)) if quotation else None
    if contract and contract.project_id != project.id:
        contract.project_id = project.id
        changed = True
    if contract and opportunity.status not in {"CONTRACT_HANDOVER", "CONTRACTED", "CLOSED"}:
        opportunity.status = "CONTRACT_HANDOVER"
        changed = True
    if contract and application.controlling_contract_id != contract.id:
        application.controlling_contract_id = contract.id
        changed = True
    return changed


def main() -> None:
    settings = get_settings()
    if settings.app_env.upper() != "TEST" or not settings.synthetic_only:
        raise RuntimeError("Synthetic Vercel bootstrap requires APP_ENV=TEST and SYNTHETIC_ONLY=true")
    if engine.dialect.name != "postgresql":
        raise RuntimeError("Synthetic Vercel bootstrap requires PostgreSQL; refusing SQLite or fallback state")

    with engine.connect() as connection:
        connection.exec_driver_sql("select 1")

    # Migrate before querying ORM models.  The bootstrap itself may be the
    # first deployed process to introduce a new model column (for example the
    # Contract → Permit controlling link), so model inspection cannot precede
    # the schema gate.
    migration_action = ensure_current_schema()

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
            changed = reconcile_proposalops_fixture(db, projects, applications)
            changed = seed_persona_issues_notifications(db) or changed
            for project in projects:
                application = next((item for item in applications if item.project_id == project.id), None)
                if application and not db.scalar(select(WorkflowTask).where(WorkflowTask.context_type == "PERMIT_WORKSPACE", WorkflowTask.context_id == project.id, WorkflowTask.task_type == "CONFIRM_PROJECT_SOURCES")):
                    ensure_project_sources_task(db, project, application)
                    changed = True
            if changed:
                db.commit()
            ensure_primary_proposal_sources()
            ensure_proposals_contracts_demo_state()
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
