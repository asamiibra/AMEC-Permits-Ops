"""E2 shared template, capability, lineage, and unified-work metadata."""

import sqlalchemy as sa
from alembic import op
from backend.app.models import Base

revision = "0018_e2_shared_runtime_contracts"
down_revision = "0017_expansion_recovery_runtime"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())

    def add_missing(table, columns):
        existing = {item["name"] for item in inspector.get_columns(table)}
        missing = [column for column in columns if column.name not in existing]
        if missing:
            with op.batch_alter_table(table) as batch:
                for column in missing:
                    batch.add_column(column)

    add_missing("communication_drafts", [
        sa.Column("source_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("source_revision_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("body_hash", sa.String(64), nullable=True),
        sa.Column("stale_reason", sa.Text(), nullable=True),
    ])
    add_missing("assistant_capability_definitions", [
        sa.Column("allowed_source_classes", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("ai_mode", sa.String(40), nullable=False, server_default="DRAFT"),
        sa.Column("capability_version", sa.String(40), nullable=False, server_default="E2-1.0"),
        sa.Column("capability_status", sa.String(40), nullable=False, server_default="ACTIVE"),
        sa.Column("enabled_in_dev", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enabled_in_test", sa.Boolean(), nullable=False, server_default=sa.true()),
    ])
    add_missing("workflow_tasks", [
        sa.Column("assistant_id", sa.String(80), nullable=True),
        sa.Column("task_family", sa.String(50), nullable=True),
        sa.Column("context_type", sa.String(80), nullable=True),
        sa.Column("context_id", sa.String(36), nullable=True),
        sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("next_action_code", sa.String(100), nullable=True),
        sa.Column("deep_link", sa.String(300), nullable=True),
        sa.Column("evidence_summary", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    ])
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    # E2 metadata is intentionally additive; retaining it makes rollback safe
    # for databases that were created from the current model metadata.
    pass
