"""Dashboard Owner Session v3 classification delta.

Adds an explicit Engineering Source Type without changing existing categories,
references, versions, or historical consumer snapshots.
"""

from alembic import op
import sqlalchemy as sa

revision = "0033_dashboard_owner_session_v3"
down_revision = "0032_bd_proposal_owner_session"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("master_content_items")}
    if "source_type_code" not in columns:
        op.add_column("master_content_items", sa.Column("source_type_code", sa.String(length=80), nullable=True))
        op.create_index("ix_master_content_items_source_type_code", "master_content_items", ["source_type_code"])


def downgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("master_content_items")}
    if "source_type_code" in columns:
        op.drop_index("ix_master_content_items_source_type_code", table_name="master_content_items")
        op.drop_column("master_content_items", "source_type_code")
