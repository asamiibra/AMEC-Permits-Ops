"""Add shared persona projection metadata to findings and events."""

import sqlalchemy as sa
from alembic import op


revision = "0024_persona_issues_notifications"
down_revision = "0023_backend_realign_reference_metadata"
branch_labels = None
depends_on = None


def _columns(table: str) -> set[str]:
    return {item["name"] for item in sa.inspect(op.get_bind()).get_columns(table)}


def _add(table: str, name: str, column: sa.Column) -> None:
    if name not in _columns(table):
        op.add_column(table, column)


def upgrade():
    _add("findings", "domain", sa.Column("domain", sa.String(50), nullable=True))
    _add("findings", "proposal_id", sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=True))
    _add("findings", "contract_id", sa.Column("contract_id", sa.String(36), sa.ForeignKey("contracts.id"), nullable=True))
    _add("findings", "permit_id", sa.Column("permit_id", sa.String(36), sa.ForeignKey("permit_applications.id"), nullable=True))
    _add("findings", "owner_persona", sa.Column("owner_persona", sa.String(40), nullable=True))
    _add("findings", "deep_link", sa.Column("deep_link", sa.String(300), nullable=True))
    _add("notification_events", "domain", sa.Column("domain", sa.String(50), nullable=True))
    _add("notification_events", "proposal_id", sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=True))
    _add("notification_events", "contract_id", sa.Column("contract_id", sa.String(36), sa.ForeignKey("contracts.id"), nullable=True))
    _add("notification_events", "permit_id", sa.Column("permit_id", sa.String(36), sa.ForeignKey("permit_applications.id"), nullable=True))
    _add("notification_events", "severity", sa.Column("severity", sa.String(30), nullable=True))
    _add("notification_events", "audience", sa.Column("audience", sa.JSON(), nullable=False, server_default="[]"))
    _add("notification_events", "actor", sa.Column("actor", sa.String(200), nullable=True))
    _add("notification_events", "deep_link", sa.Column("deep_link", sa.String(300), nullable=True))
    _add("notification_events", "acknowledged_at", sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True))
    # Existing Week 7 rows are linked to both records; new domain events may
    # intentionally be awareness-only, so the two foreign keys become nullable.
    inspector = sa.inspect(op.get_bind())
    for table, column in (("notification_events", "finding_id"), ("notification_events", "workflow_task_id")):
        if column in {item["name"] for item in inspector.get_columns(table)}:
            # Batch mode is required for SQLite and is also valid for the
            # deployed PostgreSQL schema.
            with op.batch_alter_table(table) as batch:
                batch.alter_column(column, nullable=True)


def downgrade():
    # This migration is additive. Keeping the nullable columns on downgrade is
    # safer for synthetic deployments than attempting to reconstruct events.
    pass
