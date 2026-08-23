"""Dashboard master-content v2 identity, bindings, categories, and rendition metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0029_dashboard_master_content_v2"
down_revision = "0028_master_content_propagation"
branch_labels = None
depends_on = None


def _columns(bind, table):
    return {column["name"] for column in sa.inspect(bind).get_columns(table)}


def upgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())

    if "content_categories" in tables and "source_kind" not in _columns(bind, "content_categories"):
        op.add_column("content_categories", sa.Column("source_kind", sa.String(40), nullable=False, server_default="SYNTHETIC_CONFIGURABLE"))
    if "master_content_items" in tables:
        columns = _columns(bind, "master_content_items")
        if "used_in" not in columns:
            op.add_column("master_content_items", sa.Column("used_in", sa.JSON(), nullable=False, server_default="[]"))
        if "engineering_metadata" not in columns:
            op.add_column("master_content_items", sa.Column("engineering_metadata", sa.JSON(), nullable=False, server_default="{}"))
    if "definition_entries" in tables and "used_in" not in _columns(bind, "definition_entries"):
        op.add_column("definition_entries", sa.Column("used_in", sa.JSON(), nullable=False, server_default="[]"))
    if "definition_revisions" in tables:
        columns = _columns(bind, "definition_revisions")
        if "category" not in columns:
            op.add_column("definition_revisions", sa.Column("category", sa.String(100)))
        if "used_in" not in columns:
            op.add_column("definition_revisions", sa.Column("used_in", sa.JSON(), nullable=False, server_default="[]"))
    if "document_versions" in tables:
        columns = _columns(bind, "document_versions")
        additions = [
            ("rendition_status", sa.String(40), "RENDITION_NOT_AVAILABLE"),
            ("rendition_path_or_reference", sa.String(500), None),
            ("rendition_sha256", sa.String(64), None),
            ("rendition_mime_type", sa.String(100), None),
            ("rendition_file_size", sa.Integer(), None),
        ]
        for name, type_, default in additions:
            if name not in columns:
                kwargs = {"nullable": name != "rendition_status"}
                if default is not None:
                    kwargs["server_default"] = default
                op.add_column("document_versions", sa.Column(name, type_, **kwargs))

    if "master_content_reference_sequences" not in tables:
        op.create_table(
            "master_content_reference_sequences",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("content_type", sa.String(40), nullable=False),
            sa.Column("prefix", sa.String(20), nullable=False),
            sa.Column("padding", sa.Integer(), nullable=False, server_default="4"),
            sa.Column("scope", sa.String(80), nullable=False, server_default="GLOBAL"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("current_value", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("content_type", "scope", name="uq_master_content_reference_sequence"),
        )
    if "master_content_module_bindings" not in tables:
        op.create_table(
            "master_content_module_bindings",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("master_content_id", sa.String(36), sa.ForeignKey("master_content_items.id")),
            sa.Column("definition_id", sa.String(36), sa.ForeignKey("definition_entries.id")),
            sa.Column("module", sa.String(40), nullable=False),
            sa.Column("usage_type", sa.String(50), nullable=False, server_default="AVAILABLE"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", sa.String(200), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("master_content_id IS NOT NULL OR definition_id IS NOT NULL", name="ck_binding_source_present"),
            sa.UniqueConstraint("master_content_id", "module", "usage_type", name="uq_master_content_module_binding"),
            sa.UniqueConstraint("definition_id", "module", "usage_type", name="uq_definition_module_binding"),
        )


def downgrade():
    bind = op.get_bind()
    tables = set(sa.inspect(bind).get_table_names())
    if "master_content_module_bindings" in tables:
        op.drop_table("master_content_module_bindings")
    if "master_content_reference_sequences" in tables:
        op.drop_table("master_content_reference_sequences")
    for table, columns in {
        "document_versions": ["rendition_file_size", "rendition_mime_type", "rendition_sha256", "rendition_path_or_reference", "rendition_status"],
        "definition_entries": ["used_in"],
        "definition_revisions": ["used_in", "category"],
        "master_content_items": ["engineering_metadata", "used_in"],
        "content_categories": ["source_kind"],
    }.items():
        if table in tables:
            existing = _columns(bind, table)
            for column in columns:
                if column in existing:
                    op.drop_column(table, column)
