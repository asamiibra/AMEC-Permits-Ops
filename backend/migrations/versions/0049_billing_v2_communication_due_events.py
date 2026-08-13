"""Separate invoice delivery/acknowledgment and event-based due dates."""

import sqlalchemy as sa
from alembic import op

from backend.app.models import Base


revision = "0049_billing_v2_communication_due_events"
down_revision = "0048_billing_invoice_full"
branch_labels = None
depends_on = None


def _add_columns(table: str, columns: list[sa.Column]) -> None:
    bind = op.get_bind()
    existing = {item["name"] for item in sa.inspect(bind).get_columns(table)}
    missing = [column for column in columns if column.name not in existing]
    if not missing:
        return
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table, recreate="always") as batch:
            for column in missing:
                batch.add_column(column)
    else:
        for column in missing:
            op.add_column(table, column)


def upgrade() -> None:
    bind = op.get_bind()
    for table in ("invoice_delivery_events", "invoice_acknowledgments"):
        Base.metadata.tables[table].create(bind=bind, checkfirst=True)
    _add_columns("invoice_revisions", [
        sa.Column("due_date_offset_days", sa.Integer(), nullable=True),
        sa.Column("due_date_fixed_date", sa.Date(), nullable=True),
        sa.Column("due_date_status", sa.String(40), nullable=False, server_default="NOT_CONFIGURED"),
        sa.Column("due_date_source_event_type", sa.String(80), nullable=True),
        sa.Column("due_date_source_event_id", sa.String(36), nullable=True),
        sa.Column("due_date_derived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contract_project_context_snapshot", sa.JSON(), nullable=False, server_default="{}"),
    ])
    _add_columns("billing_plan_revisions", [
        sa.Column("contract_project_context_snapshot", sa.JSON(), nullable=False, server_default="{}"),
    ])
    _add_columns("contracts", [
        sa.Column("agreement_type", sa.String(80), nullable=False, server_default="AMEC_PROFESSIONAL_SERVICES"),
    ])
    _add_columns("contract_revisions", [
        sa.Column("agreement_type", sa.String(80), nullable=False, server_default="AMEC_PROFESSIONAL_SERVICES"),
    ])


def downgrade() -> None:
    # Communication and due-date evidence is additive and must not be
    # destructively removed from an environment that may contain issued data.
    pass
