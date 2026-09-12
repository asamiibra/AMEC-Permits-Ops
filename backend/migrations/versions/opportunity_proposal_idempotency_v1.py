"""Add durable idempotency identity to canonical Proposal creation."""

from alembic import op
import sqlalchemy as sa


revision = "opportunity_proposal_idempotency_v1"
down_revision = "opportunity_commercial_controls_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("opportunities", sa.Column("idempotency_key", sa.String(length=200), nullable=True))
    op.create_index("ix_opportunities_idempotency_key", "opportunities", ["idempotency_key"], unique=True, mssql_where=sa.text("idempotency_key IS NOT NULL"))


def downgrade() -> None:
    op.drop_index("ix_opportunities_idempotency_key", table_name="opportunities")
    op.drop_column("opportunities", "idempotency_key")
