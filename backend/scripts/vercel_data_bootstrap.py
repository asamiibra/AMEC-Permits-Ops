"""Safely migrate and seed the dedicated synthetic Vercel database at deploy time."""

from __future__ import annotations

import os
import sys
import copy
from pathlib import Path
from datetime import datetime, timezone

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, func, inspect, select, text


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
from backend.app.services.master_content import reconcile_owner_demo_dataset  # noqa: E402
from backend.app.services.dashboard_inputs import ensure_dashboard_input_registry  # noqa: E402


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


def reconcile_legacy_model_columns() -> int:
    """Add missing nullable ORM columns on the retired R13 schema."""
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names()) - {"alembic_version"}
    repaired = 0
    for table in Base.metadata.sorted_tables:
        if table.name not in table_names:
            continue
        existing = {column["name"] for column in inspector.get_columns(table.name)}
        for model_column in table.columns:
            if model_column.name in existing:
                continue
            candidate = Column(
                model_column.name,
                copy.copy(model_column.type),
                nullable=True,
            )
            try:
                with engine.begin() as connection:
                    operations = Operations(MigrationContext.configure(connection))
                    operations.add_column(table.name, candidate)
                existing.add(model_column.name)
                repaired += 1
            except Exception as exc:
                print(
                    "legacy_column_repair_skipped "
                    f"table={table.name} column={model_column.name} "
                    f"reason={type(exc).__name__}",
                    file=sys.stderr,
                )
    return repaired


def ensure_current_schema() -> str:
    config = alembic_config()
    inspector = inspect(engine)
    versions = migration_versions()
    if versions:
        # The hosted synthetic database predates the active rebaseline and
        # carries the retired R13 stamp.  Its schema was already materialized
        # by the historical migration set, so replaying the active graph can
        # duplicate objects that are present but no longer represented by the
        # repository's migration IDs.  Reconcile any genuinely missing ORM
        # tables, then stamp the active head without touching existing data.
        if set(versions) & {"0058_source_intake_ledger", "0059_entra_user_identity"}:
            Base.metadata.create_all(bind=engine, checkfirst=True)
            repaired_columns = reconcile_legacy_model_columns()
            # Alembic cannot run ``stamp`` while the current database row
            # names a revision that is intentionally absent from the active
            # graph. Resolve the repository head independently and replace
            # only the version marker in one transaction.
            from alembic.script import ScriptDirectory

            heads = tuple(sorted(ScriptDirectory.from_config(config).get_heads()))
            if len(heads) != 1:
                raise RuntimeError(f"Expected one active migration head, found {heads or 'NONE'}")
            with engine.begin() as connection:
                connection.execute(text("delete from alembic_version"))
                connection.execute(
                    text("insert into alembic_version (version_num) values (:version)"),
                    {"version": heads[0]},
                )
            print(f"legacy_schema_repair columns={repaired_columns}")
            return "stamp_head_legacy_r13"
        # Alembic is the sole schema authority for a versioned database.  Do
        # not pre-create ORM tables here: doing so can race the migration that
        # owns the table and leave a deployment stuck on DuplicateTable after
        # an otherwise successful legacy upgrade.
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
    repaired_columns = reconcile_legacy_model_columns()
    if repaired_columns:
        print(f"legacy_schema_repair columns={repaired_columns}")

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
            owner_demo = reconcile_owner_demo_dataset(db)
            ensure_dashboard_input_registry(db)
            db.commit()
            print(f"synthetic_bootstrap=noop fixture={CANONICAL_FIXTURE_ID} migration={migration_action} owner_demo={owner_demo}")
            return

    counts_before = table_counts()
    schema_seed_tables = {"master_content_reference_sequences"}
    nonempty_tables = {
        name: count
        for name, count in counts_before.items()
        if count and name not in schema_seed_tables
    }
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
        owner_demo = reconcile_owner_demo_dataset(db)
        ensure_dashboard_input_registry(db)
        db.commit()
    print(f"synthetic_bootstrap=seeded fixture={CANONICAL_FIXTURE_ID} migration={migration_action} projects={len(projects)} applications={len(applications)} owner_demo={owner_demo}")


if __name__ == "__main__":
    main()
