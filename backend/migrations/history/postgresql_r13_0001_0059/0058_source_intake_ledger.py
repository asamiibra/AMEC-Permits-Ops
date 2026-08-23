"""Add the durable hidden source-intake batch/item ledger."""

from alembic import op
import sqlalchemy as sa

revision = "0058_source_intake_ledger"
down_revision = "0057_owner_form_review_status"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The legacy zero migration creates the complete metadata snapshot on
    # SQLite. In that path these tables already exist; the guarded migration
    # keeps SQLite and PostgreSQL upgrade paths convergent.
    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    if {"source_intake_batches", "source_intake_items"}.issubset(existing_tables):
        return
    op.create_table(
        "source_intake_batches",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("source_kind", sa.String(length=40), nullable=False),
        sa.Column("source_display_name", sa.String(length=300), nullable=False),
        sa.Column("source_archive_hash", sa.String(length=64), nullable=False),
        sa.Column("source_location_reference", sa.String(length=700), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_by", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("item_count_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("empty_folder_count_observed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("manifest_version", sa.String(length=40)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("error_summary", sa.Text()),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_archive_hash", "source_location_reference", name="uq_source_intake_batch_source"),
    )
    op.create_index("ix_source_intake_batches_source_archive_hash", "source_intake_batches", ["source_archive_hash"])
    op.create_index("ix_source_intake_batches_status", "source_intake_batches", ["status"])
    op.create_table(
        "source_intake_items",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("batch_id", sa.String(length=36), sa.ForeignKey("source_intake_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("source_ordinal", sa.Integer(), nullable=False),
        sa.Column("original_relative_path", sa.String(length=700), nullable=False),
        sa.Column("original_filename", sa.String(length=300)),
        sa.Column("normalized_safe_path", sa.String(length=700), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sha256", sa.String(length=64)),
        sa.Column("media_type", sa.String(length=120)),
        sa.Column("source_mtime", sa.String(length=80)),
        sa.Column("source_locator", sa.String(length=900)),
        sa.Column("disposition", sa.String(length=50)),
        sa.Column("disposition_reason", sa.Text()),
        sa.Column("duplicate_group", sa.String(length=120)),
        sa.Column("promotion_status", sa.String(length=40), nullable=False, server_default="NOT_STARTED"),
        sa.Column("target_master_content_id", sa.String(length=36), sa.ForeignKey("master_content_items.id")),
        sa.Column("target_document_version_id", sa.String(length=36), sa.ForeignKey("document_versions.id")),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("batch_id", "source_ordinal", "original_relative_path", name="uq_source_intake_item_identity"),
    )
    for name, cols in (("batch_id", ["batch_id"]), ("disposition", ["disposition"]), ("sha256", ["sha256"]), ("duplicate_group", ["duplicate_group"]), ("promotion_status", ["promotion_status"]), ("target_master_content_id", ["target_master_content_id"]), ("target_document_version_id", ["target_document_version_id"])):
        op.create_index(f"ix_source_intake_items_{name}", "source_intake_items", cols)
    op.create_index("ix_source_intake_item_batch_disposition", "source_intake_items", ["batch_id", "disposition"])


def downgrade() -> None:
    op.drop_index("ix_source_intake_item_batch_disposition", table_name="source_intake_items")
    for name in ("target_document_version_id", "target_master_content_id", "promotion_status", "duplicate_group", "sha256", "disposition", "batch_id"):
        op.drop_index(f"ix_source_intake_items_{name}", table_name="source_intake_items")
    op.drop_table("source_intake_items")
    op.drop_index("ix_source_intake_batches_status", table_name="source_intake_batches")
    op.drop_index("ix_source_intake_batches_source_archive_hash", table_name="source_intake_batches")
    op.drop_table("source_intake_batches")
