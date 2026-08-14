"""Add Completion / As-Built technical handoff core."""

import sqlalchemy as sa
from alembic import op

from backend.app.models import Base


revision = "0052_completion_asbuilt_core"
down_revision = "0051_construction_inspection_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in (
        "building_assets",
        "building_snapshots",
        "construction_completion_contexts",
        "completion_case_links",
        "as_built_baselines",
        "as_built_baseline_members",
        "as_built_comparison_runs",
        "as_built_variances",
    ):
        Base.metadata.tables[table].create(bind=bind, checkfirst=True)
    inspector = sa.inspect(bind)
    if "as_built_baseline_id" not in {column["name"] for column in inspector.get_columns("submission_package_items")}:
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("submission_package_items") as batch:
                batch.add_column(sa.Column("as_built_baseline_id", sa.String(length=36), nullable=True))
                batch.create_foreign_key("fk_submission_package_item_as_built_baseline", "as_built_baselines", ["as_built_baseline_id"], ["id"])
        else:
            op.add_column("submission_package_items", sa.Column("as_built_baseline_id", sa.String(length=36), nullable=True))
            op.create_foreign_key("fk_submission_package_item_as_built_baseline", "submission_package_items", "as_built_baselines", ["as_built_baseline_id"], ["id"])


def downgrade() -> None:
    # Completion evidence is an audit boundary. Preserve it during ordinary
    # downgrades; any destructive archival requires an explicit operator action.
    pass
