"""Bind billing financial-account controls to their canonical office scope."""

from alembic import op
import sqlalchemy as sa


revision = "billing_finance_production_hardening_v1"
down_revision = "scoped_finance_capability_assignment_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "financial_account_masters",
        sa.Column("office_id", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "financial_account_masters_office_id_fkey",
        "financial_account_masters",
        "consultancy_offices",
        ["office_id"],
        ["id"],
    )
    op.create_index(
        "ix_financial_account_masters_office_id",
        "financial_account_masters",
        ["office_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_financial_account_masters_office_id", table_name="financial_account_masters")
    op.drop_constraint("financial_account_masters_office_id_fkey", "financial_account_masters", type_="foreignkey")
    op.drop_column("financial_account_masters", "office_id")
