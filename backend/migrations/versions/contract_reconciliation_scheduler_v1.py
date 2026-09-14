"""Add the durable contract reconciliation scheduler cursor."""

from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa


revision = "contract_reconciliation_scheduler_v1"
down_revision = "17c6ebd99c4a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "contract_reconciliation_scheduler_state",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("last_contract_id", sa.String(length=36), nullable=True),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("lease_owner", sa.String(length=100), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name="contract_reconciliation_scheduler_state_pkey"),
    )
    op.create_index(
        "ix_contract_reconciliation_scheduler_state_last_contract_id",
        "contract_reconciliation_scheduler_state",
        ["last_contract_id"],
    )
    op.bulk_insert(
        sa.table(
            "contract_reconciliation_scheduler_state",
            sa.column("id", sa.String(length=80)),
            sa.column("cycle_number", sa.Integer()),
            sa.column("updated_at", sa.DateTime(timezone=True)),
        ),
        [{
            "id": "contract-exceptions",
            "cycle_number": 0,
            "updated_at": datetime.now(timezone.utc),
        }],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contract_reconciliation_scheduler_state_last_contract_id",
        table_name="contract_reconciliation_scheduler_state",
    )
    op.drop_table("contract_reconciliation_scheduler_state")
