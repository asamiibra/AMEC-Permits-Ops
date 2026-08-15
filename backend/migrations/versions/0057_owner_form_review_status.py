"""Add the compact Owner Form review overlay."""

from alembic import op
import sqlalchemy as sa


revision = "0057_owner_form_review_status"
down_revision = "0056_storage_operation_journal"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("master_content_items")}
    if "needs_review" not in columns:
        op.add_column("master_content_items", sa.Column("needs_review", sa.Boolean(), nullable=False, server_default=sa.false()))
        op.alter_column("master_content_items", "needs_review", server_default=None)
    if "review_note" not in columns:
        op.add_column("master_content_items", sa.Column("review_note", sa.String(length=500), nullable=True))
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("master_content_items")}
    if "ix_master_content_items_needs_review" not in indexes:
        op.create_index("ix_master_content_items_needs_review", "master_content_items", ["needs_review"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("master_content_items")}
    if "ix_master_content_items_needs_review" in indexes:
        op.drop_index("ix_master_content_items_needs_review", table_name="master_content_items")
    columns = {column["name"] for column in sa.inspect(bind).get_columns("master_content_items")}
    if "review_note" in columns:
        op.drop_column("master_content_items", "review_note")
    if "needs_review" in columns:
        op.drop_column("master_content_items", "needs_review")
