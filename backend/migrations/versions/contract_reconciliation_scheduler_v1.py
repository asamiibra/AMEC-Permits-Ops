"""Add the durable contract reconciliation scheduler cursor."""

from alembic import op
import sqlalchemy as sa


revision = "contract_reconciliation_scheduler_v1"
down_revision = "17c6ebd99c4a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_name = "contract_reconciliation_scheduler_state"
    if table_name not in inspector.get_table_names():
        op.create_table(
            table_name,
            sa.Column("id", sa.String(length=80), nullable=False),
            sa.Column("last_contract_id", sa.String(length=36), nullable=True),
            sa.Column("cycle_number", sa.Integer(), nullable=False),
            sa.Column("lease_owner", sa.String(length=100), nullable=True),
            sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint("id", name="contract_reconciliation_scheduler_state_pkey"),
        )
    index_name = "ix_contract_reconciliation_scheduler_state_last_contract_id"
    if index_name not in {index["name"] for index in inspector.get_indexes(table_name)}:
        op.create_index(index_name, table_name, ["last_contract_id"])
    op.execute(
        sa.text(
            "IF NOT EXISTS (SELECT 1 FROM contract_reconciliation_scheduler_state "
            "WHERE id = 'contract-exceptions') "
            "INSERT INTO contract_reconciliation_scheduler_state "
            "(id, cycle_number, updated_at) VALUES "
            "('contract-exceptions', 0, SYSUTCDATETIME())"
        )
    )


def downgrade() -> None:
    op.drop_index(
        "ix_contract_reconciliation_scheduler_state_last_contract_id",
        table_name="contract_reconciliation_scheduler_state",
    )
    op.drop_table("contract_reconciliation_scheduler_state")
