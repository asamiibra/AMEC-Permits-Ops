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
    indexes = {index["name"] for index in inspector.get_indexes("construction_inspections")}
    constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("construction_inspections")}
    missing_column = "idempotency_key" not in columns
    missing_index = "ix_construction_inspections_idempotency_key" not in indexes
    missing_constraint = "uq_construction_inspection_idempotency" not in constraints
    if bind.dialect.name == "sqlite":
        if missing_column or missing_index or missing_constraint:
            with op.batch_alter_table("construction_inspections", recreate="always") as batch:
                if missing_column:
                    batch.add_column(sa.Column("idempotency_key", sa.String(length=200), nullable=True))
                if missing_constraint:
                    batch.create_unique_constraint(
                        "uq_construction_inspection_idempotency",
                        ["construction_execution_id", "idempotency_key"],
                    )
                if missing_index:
                    batch.create_index("ix_construction_inspections_idempotency_key", ["idempotency_key"])
        return
    if missing_column:
        op.add_column("construction_inspections", sa.Column("idempotency_key", sa.String(length=200), nullable=True))
    if missing_index:
        op.create_index("ix_construction_inspections_idempotency_key", "construction_inspections", ["idempotency_key"])
    if missing_constraint:
        op.create_unique_constraint("uq_construction_inspection_idempotency", "construction_inspections", ["construction_execution_id", "idempotency_key"])


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("construction_inspections")}
    indexes = {index["name"] for index in inspector.get_indexes("construction_inspections")}
    columns = {column["name"] for column in inspector.get_columns("construction_inspections")}
    if bind.dialect.name == "sqlite":
        if "idempotency_key" in columns or "ix_construction_inspections_idempotency_key" in indexes or "uq_construction_inspection_idempotency" in constraints:
            with op.batch_alter_table("construction_inspections", recreate="always") as batch:
                if "uq_construction_inspection_idempotency" in constraints:
                    batch.drop_constraint("uq_construction_inspection_idempotency", type_="unique")
                if "ix_construction_inspections_idempotency_key" in indexes:
                    batch.drop_index("ix_construction_inspections_idempotency_key")
                if "idempotency_key" in columns:
                    batch.drop_column("idempotency_key")
        return
    if "uq_construction_inspection_idempotency" in constraints:
        op.drop_constraint("uq_construction_inspection_idempotency", "construction_inspections", type_="unique")
    if "ix_construction_inspections_idempotency_key" in indexes:
        op.drop_index("ix_construction_inspections_idempotency_key", table_name="construction_inspections")
    if "idempotency_key" in columns:
        op.drop_column("construction_inspections", "idempotency_key")
