"""Add idempotency key for construction inspection requests."""

import sqlalchemy as sa
from alembic import op


revision = "0051_construction_inspection_idempotency"
down_revision = "0050_construction_post_approval_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("construction_inspections", sa.Column("idempotency_key", sa.String(length=200), nullable=True))
    op.create_index("ix_construction_inspections_idempotency_key", "construction_inspections", ["idempotency_key"])
    op.create_unique_constraint("uq_construction_inspection_idempotency", "construction_inspections", ["construction_execution_id", "idempotency_key"])


def downgrade() -> None:
    op.drop_constraint("uq_construction_inspection_idempotency", "construction_inspections", type_="unique")
    op.drop_index("ix_construction_inspections_idempotency_key", table_name="construction_inspections")
    op.drop_column("construction_inspections", "idempotency_key")
