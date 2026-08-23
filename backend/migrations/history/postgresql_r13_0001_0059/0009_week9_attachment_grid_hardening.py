"""Week 9 attachment and repeating-grid hardening."""

import sqlalchemy as sa
from alembic import op
from backend.app.models import Base

revision = "0009_week9_attachment_grid"
down_revision = "0008_week8_lineage"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    existing = {table: {column["name"] for column in inspector.get_columns(table)} for table in ["attachment_manifests", "portal_grid_row_intents"]}
    additions = {
        "attachment_manifests": [
            sa.Column("preparation_revision_id", sa.String(36), nullable=True),
            sa.Column("scenario_id", sa.String(36), nullable=True),
            sa.Column("manifest_version", sa.String(40), nullable=False, server_default="WEEK4-BASE-1.0"),
            sa.Column("generated_by", sa.String(200), nullable=False, server_default="permitops-system"),
            sa.Column("status", sa.String(30), nullable=False, server_default="DRAFT"),
        ],
        "portal_grid_row_intents": [
            sa.Column("grid_code", sa.String(100), nullable=False, server_default="BUILDING_FLOOR_UNIT"),
            sa.Column("parent_canonical_row_id", sa.String(160), nullable=True),
            sa.Column("business_key", sa.String(300), nullable=True),
            sa.Column("source_entity_version", sa.String(160), nullable=True),
            sa.Column("intended_sequence", sa.Integer(), nullable=True),
            sa.Column("row_hash", sa.String(64), nullable=True),
        ],
    }
    for table, columns in additions.items():
        for column in columns:
            if column.name not in existing[table]:
                op.add_column(table, column)
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    bind = op.get_bind()
    for table in [
        "portal_derived_field_reconciliations", "grid_persistence_evidence", "grid_field_diffs",
        "grid_row_reconciliation_results", "grid_reconciliation_runs", "portal_grid_row_observations",
        "portal_structure_fingerprints", "attachment_reconciliation_results", "attachment_persistence_evidence",
        "attachment_association_intents", "attachment_manifest_items", "attachment_category_rules",
    ]:
        bind.exec_driver_sql(f"DROP TABLE IF EXISTS {table}")
    for table, columns in {
        "portal_grid_row_intents": ["row_hash", "intended_sequence", "source_entity_version", "business_key", "parent_canonical_row_id", "grid_code"],
        "attachment_manifests": ["status", "generated_by", "manifest_version", "scenario_id", "preparation_revision_id"],
    }.items():
        for column in columns:
            bind.exec_driver_sql(f"ALTER TABLE {table} DROP COLUMN IF EXISTS {column}")
