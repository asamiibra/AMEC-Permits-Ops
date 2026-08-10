"""Governed master-content dependencies and cross-module propagation ledger."""

import sqlalchemy as sa
from alembic import op

revision = "0028_master_content_propagation"
down_revision = "0027_owner_dashboard_master_content"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "master_content_dependencies" not in tables:
        op.create_table(
            "master_content_dependencies",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("master_content_id", sa.String(36), sa.ForeignKey("master_content_items.id"), nullable=False),
            sa.Column("bound_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False),
            sa.Column("expected_current_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False),
            sa.Column("downstream_type", sa.String(100), nullable=False),
            sa.Column("downstream_id", sa.String(160), nullable=False),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id")),
            sa.Column("dependency_kind", sa.String(80), nullable=False),
            sa.Column("policy", sa.String(80), nullable=False, server_default="REVALIDATE_ON_CURRENT_CHANGE"),
            sa.Column("status", sa.String(40), nullable=False, server_default="CURRENT"),
            sa.Column("created_by", sa.String(200), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("master_content_id", "downstream_type", "downstream_id", "dependency_kind", name="uq_master_content_dependency"),
        )
    if "master_content_change_events" in tables:
        if bind.dialect.name == "sqlite":
            # SQLite cannot alter nullability and Alembic batch rebuilds see
            # the event delivery FK as a cycle. Rebuild the small event table
            # explicitly with foreign-key checks disabled for the operation.
            op.execute("PRAGMA foreign_keys=OFF")
            op.execute("""CREATE TABLE master_content_change_events_new (
                id VARCHAR(36) NOT NULL PRIMARY KEY,
                master_content_id VARCHAR(36),
                definition_id VARCHAR(36),
                previous_version_id VARCHAR(36),
                new_version_id VARCHAR(36) NOT NULL,
                change_type VARCHAR(80) NOT NULL,
                status VARCHAR(40) NOT NULL,
                correlation_id VARCHAR(100) NOT NULL,
                actor_or_system VARCHAR(200) NOT NULL,
                metadata_json JSON NOT NULL,
                occurred_at DATETIME NOT NULL,
                event_type VARCHAR(100) NOT NULL DEFAULT 'MASTER_CONTENT_VERSION_PROMOTED',
                content_type VARCHAR(40),
                business_ref VARCHAR(100),
                category_snapshot JSON NOT NULL DEFAULT '{}',
                change_kind VARCHAR(40),
                change_reason VARCHAR(500),
                materiality VARCHAR(30) NOT NULL DEFAULT 'MATERIAL',
                source_hash VARCHAR(64),
                FOREIGN KEY(master_content_id) REFERENCES master_content_items(id),
                FOREIGN KEY(definition_id) REFERENCES definition_entries(id)
            )""")
            op.execute("""INSERT INTO master_content_change_events_new
                (id, master_content_id, previous_version_id, new_version_id,
                 change_type, status, correlation_id, actor_or_system,
                 metadata_json, occurred_at)
                SELECT id, master_content_id, previous_version_id, new_version_id,
                 change_type, status, correlation_id, actor_or_system,
                 metadata_json, occurred_at
                FROM master_content_change_events""")
            op.drop_table("master_content_change_events")
            op.rename_table("master_content_change_events_new", "master_content_change_events")
            op.execute("PRAGMA foreign_keys=ON")
        else:
            op.alter_column("master_content_change_events", "master_content_id", existing_type=sa.String(36), nullable=True)
            existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("master_content_change_events")}
            for column in [
                sa.Column("definition_id", sa.String(36), sa.ForeignKey("definition_entries.id"), nullable=True),
                sa.Column("event_type", sa.String(100), nullable=False, server_default="MASTER_CONTENT_VERSION_PROMOTED"),
                sa.Column("content_type", sa.String(40), nullable=True),
                sa.Column("business_ref", sa.String(100), nullable=True),
                sa.Column("category_snapshot", sa.JSON(), nullable=False, server_default="{}"),
                sa.Column("change_kind", sa.String(40), nullable=True),
                sa.Column("change_reason", sa.String(500), nullable=True),
                sa.Column("materiality", sa.String(30), nullable=False, server_default="MATERIAL"),
                sa.Column("source_hash", sa.String(64), nullable=True),
            ]:
                if column.name not in existing_columns:
                    op.add_column("master_content_change_events", column)
    # Create the incoming-FK delivery ledger only after the SQLite batch
    # rebuild above; otherwise Alembic detects the incoming FK as a cycle.
    if "master_content_event_deliveries" not in tables:
        op.create_table(
            "master_content_event_deliveries",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("event_id", sa.String(36), sa.ForeignKey("master_content_change_events.id"), nullable=False),
            sa.Column("delivery_type", sa.String(60), nullable=False),
            sa.Column("target_type", sa.String(100), nullable=False),
            sa.Column("target_id", sa.String(160), nullable=False),
            sa.Column("recipient_role", sa.String(80), nullable=False, server_default="-"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("event_id", "delivery_type", "target_type", "target_id", "recipient_role", name="uq_master_content_event_delivery"),
        )


def downgrade():
    op.drop_table("master_content_event_deliveries")
    op.drop_table("master_content_dependencies")
    with op.batch_alter_table("master_content_change_events") as batch:
        for name in ["source_hash", "materiality", "change_reason", "change_kind", "category_snapshot", "business_ref", "content_type", "event_type", "definition_id"]:
            batch.drop_column(name)
