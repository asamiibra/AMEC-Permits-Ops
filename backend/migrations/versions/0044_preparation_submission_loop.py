"""Case-specific Preparation + Submission Loop runtime companions."""

from alembic import op
import sqlalchemy as sa

from backend.app.models import Base


revision = "0044_preparation_submission_loop"
down_revision = "0043_project_engineering_approved_design_baseline"
branch_labels = None
depends_on = None


TABLES = (
    "authority_case_create_requests",
    "authority_case_policy_bindings",
    "requirement_instances",
    "case_evidence_selections",
    "physical_evidence_items",
    "submission_packages",
    "submission_package_items",
    "submission_precheck_runs",
    "submission_precheck_checks",
    "submission_attempts",
    "external_submission_snapshots",
    "authority_submission_cycles",
    "authority_case_findings",
    "authority_finding_responses",
    "authority_case_outcomes",
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("preparation_revisions")}
    columns = (
        ("authority_case_id", sa.Column("authority_case_id", sa.String(36), sa.ForeignKey("authority_cases.id", name="fk_preparation_revisions_authority_case"), nullable=True)),
        ("authority_revision_number", sa.Column("authority_revision_number", sa.Integer(), nullable=True)),
        ("authority_policy_version_id", sa.Column("authority_policy_version_id", sa.String(36), sa.ForeignKey("requirement_policy_versions.id", name="fk_preparation_revisions_authority_policy"), nullable=True)),
        ("authority_approved_design_baseline_id", sa.Column("authority_approved_design_baseline_id", sa.String(36), sa.ForeignKey("approved_design_baselines.id", name="fk_preparation_revisions_authority_baseline"), nullable=True)),
        ("authority_state", sa.Column("authority_state", sa.String(40), nullable=True)),
        ("authority_snapshot_hash", sa.Column("authority_snapshot_hash", sa.String(64), nullable=True)),
        ("authority_snapshot_json", sa.Column("authority_snapshot_json", sa.JSON(), nullable=False, server_default="{}")),
        ("authority_locked_at", sa.Column("authority_locked_at", sa.DateTime(timezone=True), nullable=True)),
        ("authority_supersedes_revision_id", sa.Column("authority_supersedes_revision_id", sa.String(36), nullable=True)),
    )
    if bind.dialect.name == "sqlite":
        missing = [column for name, column in columns if name not in existing]
        if missing:
            with op.batch_alter_table("preparation_revisions", recreate="always") as batch:
                for column in missing:
                    batch.add_column(column)
    else:
        for name, column in columns:
            if name not in existing:
                op.add_column("preparation_revisions", column)
    op.create_index("ix_preparation_revisions_authority_case_id", "preparation_revisions", ["authority_case_id"], if_not_exists=True)
    op.create_index("ix_preparation_revisions_authority_policy_version_id", "preparation_revisions", ["authority_policy_version_id"], if_not_exists=True)
    op.create_index("ix_preparation_revisions_authority_approved_design_baseline_id", "preparation_revisions", ["authority_approved_design_baseline_id"], if_not_exists=True)
    op.create_index("ix_preparation_revisions_authority_state", "preparation_revisions", ["authority_state"], if_not_exists=True)
    for name in TABLES:
        Base.metadata.tables[name].create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=op.get_bind(), checkfirst=True)
    for index_name in ("ix_preparation_revisions_authority_state", "ix_preparation_revisions_authority_approved_design_baseline_id", "ix_preparation_revisions_authority_policy_version_id", "ix_preparation_revisions_authority_case_id"):
        op.drop_index(index_name, table_name="preparation_revisions", if_exists=True)
    names = ("authority_supersedes_revision_id", "authority_locked_at", "authority_snapshot_json", "authority_snapshot_hash", "authority_state", "authority_approved_design_baseline_id", "authority_policy_version_id", "authority_revision_number", "authority_case_id")
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("preparation_revisions", recreate="always") as batch:
            for name in names:
                batch.drop_column(name)
    else:
        for name in names:
            op.drop_column("preparation_revisions", name)
