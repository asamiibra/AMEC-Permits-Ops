"""Explicit Proposal provisional-to-canonical reference metadata."""

import sqlalchemy as sa
from alembic import op


revision = "0023_backend_realign_reference_metadata"
down_revision = "0022_proposalops_master_realignment"
branch_labels = None
depends_on = None


def _add(name: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    if name not in {item["name"] for item in inspector.get_columns("opportunities")}:
        op.add_column("opportunities", column)


def upgrade():
    _add("provisional_reference", sa.Column("provisional_reference", sa.String(100), nullable=True))
    _add("canonical_project_reference", sa.Column("canonical_project_reference", sa.String(100), nullable=True))
    _add("canonicalized_at", sa.Column("canonicalized_at", sa.DateTime(timezone=True), nullable=True))
    _add("canonicalized_by", sa.Column("canonicalized_by", sa.String(200), nullable=True))


def downgrade():
    inspector = sa.inspect(op.get_bind())
    for name in ("canonicalized_by", "canonicalized_at", "canonical_project_reference", "provisional_reference"):
        if name in {item["name"] for item in inspector.get_columns("opportunities")}:
            op.drop_column("opportunities", name)
