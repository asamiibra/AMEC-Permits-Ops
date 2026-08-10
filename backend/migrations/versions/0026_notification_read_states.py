"""Store notification acknowledgement per synthetic principal/persona."""

import sqlalchemy as sa
from alembic import op


revision = "0026_notification_read_states"
down_revision = "0025_permit_workflow_stage_confirmation"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "notification_read_states" not in inspector.get_table_names():
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
    existing_indexes = {item["name"] for item in sa.inspect(op.get_bind()).get_indexes("notification_read_states")}
    for name, columns in {
        "ix_notification_read_states_notification_event_id": ["notification_event_id"],
        "ix_notification_read_states_persona": ["persona"],
        "ix_notification_read_states_principal_key": ["principal_key"],
    }.items():
        if name not in existing_indexes:
            op.create_index(name, "notification_read_states", columns)


def downgrade():
    op.drop_index("ix_notification_read_states_principal_key", table_name="notification_read_states")
    op.drop_index("ix_notification_read_states_persona", table_name="notification_read_states")
    op.drop_index("ix_notification_read_states_notification_event_id", table_name="notification_read_states")
    op.drop_table("notification_read_states")
