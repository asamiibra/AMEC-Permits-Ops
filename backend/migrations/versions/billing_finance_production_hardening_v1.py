"""Bind billing financial-account controls to their canonical office scope."""

from alembic import op
import sqlalchemy as sa


revision = "billing_finance_production_hardening_v1"
down_revision = "scoped_finance_capability_assignment_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("financial_account_masters")}
    if "office_id" not in columns:
        op.add_column("financial_account_masters", sa.Column("office_id", sa.String(length=36), nullable=True))
    foreign_keys = {key["name"] for key in inspector.get_foreign_keys("financial_account_masters") if key["name"]}
    if "financial_account_masters_office_id_fkey" not in foreign_keys:
        op.create_foreign_key(
            "financial_account_masters_office_id_fkey",
            "financial_account_masters",
            "consultancy_offices",
            ["office_id"],
            ["id"],
        )
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("financial_account_masters") if index["name"]}
    if "ix_financial_account_masters_office_id" not in indexes:
        op.create_index("ix_financial_account_masters_office_id", "financial_account_masters", ["office_id"])


def downgrade() -> None:
    op.drop_index("ix_financial_account_masters_office_id", table_name="financial_account_masters")
    op.drop_constraint("financial_account_masters_office_id_fkey", "financial_account_masters", type_="foreignkey")
    op.drop_column("financial_account_masters", "office_id")
