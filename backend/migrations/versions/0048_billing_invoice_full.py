"""Billing plans, milestones, invoices, accounts, payments, and receivables."""

import sqlalchemy as sa
from alembic import op

from backend.app.models import Base


revision = "0048_billing_invoice_full"
down_revision = "0047_prebilling_regulatory_context"
branch_labels = None
depends_on = None


def _add_columns(table: str, columns: list[sa.Column]) -> None:
    bind = op.get_bind()
    existing = {item["name"] for item in sa.inspect(bind).get_columns(table)}
    missing = [column for column in columns if column.name not in existing]
    if not missing:
        return
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table, recreate="always") as batch:
            for column in missing:
                batch.add_column(column)
    else:
        for column in missing:
            op.add_column(table, column)


def upgrade() -> None:
    bind = op.get_bind()
    for table in (
        "billing_plans", "billing_plan_revisions", "billing_milestones", "billing_milestone_eligibilities",
        "invoice_line_items", "invoice_references", "invoice_approval_records", "invoice_accept_records",
        "invoice_issue_events", "invoice_numbering_policies", "financial_account_masters", "financial_account_versions",
        "payment_receipts", "invoice_payment_allocations", "receivable_follow_ups",
    ):
        Base.metadata.tables[table].create(bind=bind, checkfirst=True)
    _add_columns("invoices", [
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("client_account_id", sa.String(36), sa.ForeignKey("client_accounts.id"), nullable=True),
        sa.Column("billing_plan_id", sa.String(36), sa.ForeignKey("billing_plans.id"), nullable=True),
        sa.Column("invoice_ref_status", sa.String(40), nullable=False, server_default="NOT_ALLOCATED"),
    ])
    _add_columns("invoice_revisions", [
        sa.Column("billing_plan_revision_id", sa.String(36), sa.ForeignKey("billing_plan_revisions.id"), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("due_date_basis", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(20), nullable=True),
        sa.Column("gross_charge_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("adjustment_total", sa.Numeric(18, 2), nullable=True, server_default="0"),
        sa.Column("payable_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("amount_in_words", sa.Text(), nullable=True),
        sa.Column("accepted_by", sa.String(200), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    ])


def downgrade() -> None:
    # Additive finance history is retained; no issued or payment records are
    # destructively removed by downgrade.
    pass
