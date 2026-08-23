"""Persistent Dashboard Master Content Inputs & Go-Live checklist."""

import sqlalchemy as sa
from alembic import op

revision = "0030_dashboard_master_content_inputs"
down_revision = "0029_dashboard_master_content_v2"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if "dashboard_input_items" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "dashboard_input_items",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("context_key", sa.String(80), nullable=False, server_default="DASHBOARD_MASTER_CONTENT"),
            sa.Column("input_key", sa.String(120), nullable=False),
            sa.Column("group_name", sa.String(50), nullable=False),
            sa.Column("title", sa.String(240), nullable=False),
            sa.Column("why_needed", sa.Text(), nullable=False),
            sa.Column("requested_input", sa.Text(), nullable=False),
            sa.Column("current_value_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.Column("status", sa.String(40), nullable=False, server_default="NEEDS_CONFIRMATION"),
            sa.Column("blocking_level", sa.String(40), nullable=False, server_default="BUSINESS"),
            sa.Column("owner_role", sa.String(80), nullable=False, server_default="OWNER"),
            sa.Column("linked_route", sa.String(240)),
            sa.Column("notes", sa.Text()),
            sa.Column("confirmed_by", sa.String(120)),
            sa.Column("confirmed_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("context_key", "input_key", name="uq_dashboard_input_context_key"),
        )
        op.create_index("ix_dashboard_input_items_context_key", "dashboard_input_items", ["context_key"])
        op.create_index("ix_dashboard_input_items_input_key", "dashboard_input_items", ["input_key"])
        op.create_index("ix_dashboard_input_items_status", "dashboard_input_items", ["status"])


def downgrade():
    op.drop_index("ix_dashboard_input_items_status", table_name="dashboard_input_items")
    op.drop_index("ix_dashboard_input_items_input_key", table_name="dashboard_input_items")
    op.drop_index("ix_dashboard_input_items_context_key", table_name="dashboard_input_items")
    op.drop_table("dashboard_input_items")
