"""Add idempotency key for construction inspection requests."""

import sqlalchemy as sa
from alembic import op


revision = "0051_construction_inspection_idempotency"
down_revision = "0050_construction_post_approval_controls"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("construction_inspections")}
    if "idempotency_key" not in columns:
        op.add_column("construction_inspections", sa.Column("idempotency_key", sa.String(length=200), nullable=True))
    indexes = {index["name"] for index in inspector.get_indexes("construction_inspections")}
    if "ix_construction_inspections_idempotency_key" not in indexes:
        op.create_index("ix_construction_inspections_idempotency_key", "construction_inspections", ["idempotency_key"])
    constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("construction_inspections")}
    if "uq_construction_inspection_idempotency" not in constraints:
        op.create_unique_constraint("uq_construction_inspection_idempotency", "construction_inspections", ["construction_execution_id", "idempotency_key"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("construction_inspections")}
    if "uq_construction_inspection_idempotency" in constraints:
        op.drop_constraint("uq_construction_inspection_idempotency", "construction_inspections", type_="unique")
    indexes = {index["name"] for index in inspector.get_indexes("construction_inspections")}
    if "ix_construction_inspections_idempotency_key" in indexes:
        op.drop_index("ix_construction_inspections_idempotency_key", table_name="construction_inspections")
    columns = {column["name"] for column in inspector.get_columns("construction_inspections")}
    if "idempotency_key" in columns:
        op.drop_column("construction_inspections", "idempotency_key")
