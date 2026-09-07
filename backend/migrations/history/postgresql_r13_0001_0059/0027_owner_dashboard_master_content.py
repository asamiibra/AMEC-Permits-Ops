"""Owner dashboard master content and structured definitions."""

import sqlalchemy as sa
from alembic import op

revision = "0027_owner_dashboard_master_content"
down_revision = "0026_notification_read_states"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "content_categories" not in tables:
        op.create_table(
            "content_categories",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("code", sa.String(80), nullable=False),
            sa.Column("label", sa.String(160), nullable=False),
            sa.Column("description", sa.Text),
            sa.Column("allowed_content_types", sa.JSON(), nullable=False),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
            sa.UniqueConstraint("code", name="uq_content_category_code"),
        )
    if "master_content_items" not in tables:
        op.create_table(
            "master_content_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("ref", sa.String(100), nullable=False),
            sa.Column("content_type", sa.String(40), nullable=False),
            sa.Column("title", sa.String(240), nullable=False),
            sa.Column("category_id", sa.String(36), sa.ForeignKey("content_categories.id")),
            sa.Column("description", sa.Text),
            sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
            sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id"), nullable=False, unique=True),
            sa.Column("current_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id")),
            sa.Column("created_by", sa.String(200), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("content_type", "ref", name="uq_master_content_type_ref"),
        )
    if "definition_entries" not in tables:
        op.create_table(
            "definition_entries",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("ref", sa.String(100)),
            sa.Column("term", sa.String(240), nullable=False),
            sa.Column("category", sa.String(100)),
            sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
            # The revision pointer is added before the revision table exists;
            # the ORM relation remains authoritative and SQLite/PostgreSQL can
            # safely carry the nullable pointer without a cyclic DDL order.
            sa.Column("current_revision_id", sa.String(36)),
            sa.Column("created_by", sa.String(200), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("term", name="uq_definition_term"),
        )
    if "definition_revisions" not in tables:
        op.create_table(
            "definition_revisions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("definition_id", sa.String(36), sa.ForeignKey("definition_entries.id"), nullable=False),
            sa.Column("revision_number", sa.Integer(), nullable=False),
            sa.Column("term", sa.String(240), nullable=False),
            sa.Column("description", sa.Text(), nullable=False),
            sa.Column("aliases", sa.JSON(), nullable=False),
            sa.Column("notes", sa.Text()),
            sa.Column("changed_by", sa.String(200), nullable=False),
            sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("change_reason", sa.String(500)),
            sa.Column("status", sa.String(30), nullable=False, server_default="CURRENT"),
            sa.UniqueConstraint("definition_id", "revision_number", name="uq_definition_revision_number"),
        )
    if "master_content_idempotency" not in tables:
        op.create_table(
            "master_content_idempotency",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("idempotency_key", sa.String(200), nullable=False),
            sa.Column("master_content_id", sa.String(36), sa.ForeignKey("master_content_items.id"), nullable=False),
            sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False),
            sa.Column("result_json", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("idempotency_key", name="uq_master_content_idempotency_key"),
        )
    if "master_content_change_events" not in tables:
        op.create_table(
            "master_content_change_events",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("master_content_id", sa.String(36), sa.ForeignKey("master_content_items.id"), nullable=False),
            sa.Column("previous_version_id", sa.String(36)),
            sa.Column("new_version_id", sa.String(36), nullable=False),
            sa.Column("change_type", sa.String(80), nullable=False),
            sa.Column("status", sa.String(40), nullable=False, server_default="APPLIED"),
            sa.Column("correlation_id", sa.String(100), nullable=False),
            sa.Column("actor_or_system", sa.String(200), nullable=False),
            sa.Column("metadata_json", sa.JSON(), nullable=False),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "documents" in tables:
        with op.batch_alter_table("documents") as batch:
            batch.alter_column("project_id", existing_type=sa.String(36), nullable=True)


def downgrade():
    op.drop_table("master_content_idempotency")
    op.drop_table("master_content_change_events")
    op.drop_table("master_content_items")
    op.drop_table("definition_revisions")
    op.drop_table("definition_entries")
    op.drop_table("content_categories")
