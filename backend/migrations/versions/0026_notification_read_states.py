"""Store notification acknowledgement per synthetic principal/persona."""

import sqlalchemy as sa
from alembic import op


revision = "0026_notification_read_states"
down_revision = "0025_permit_workflow_stage_confirmation"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "notification_read_states",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("notification_event_id", sa.String(length=36), nullable=False),
        sa.Column("persona", sa.String(length=40), nullable=False),
        sa.Column("principal_key", sa.String(length=160), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["notification_event_id"], ["notification_events.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("notification_event_id", "persona", "principal_key", name="uq_notification_read_state_scope"),
    )
    op.create_index("ix_notification_read_states_notification_event_id", "notification_read_states", ["notification_event_id"])
    op.create_index("ix_notification_read_states_persona", "notification_read_states", ["persona"])
    op.create_index("ix_notification_read_states_principal_key", "notification_read_states", ["principal_key"])


def downgrade():
    op.drop_index("ix_notification_read_states_principal_key", table_name="notification_read_states")
    op.drop_index("ix_notification_read_states_persona", table_name="notification_read_states")
    op.drop_index("ix_notification_read_states_notification_event_id", table_name="notification_read_states")
    op.drop_table("notification_read_states")
