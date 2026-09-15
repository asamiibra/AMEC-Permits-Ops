"""Add the bounded read-model/workflow support for Billing UX v1.

This migration adds only fields needed to represent structured Billing mode,
structured service periods, safe invoice cloning, and the append-only request
for human Billing readiness review. It does not alter historical V10 data or
grant any financial authority.
"""

from alembic import op
import sqlalchemy as sa


revision = "billing_finance_experience_v1"
down_revision = "17c6ebd99c4a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    def columns(table_name: str) -> set[str]:
        return {column["name"] for column in sa.inspect(bind).get_columns(table_name)}

    def indexes(table_name: str) -> set[str]:
        return {index["name"] for index in sa.inspect(bind).get_indexes(table_name) if index["name"]}

    def foreign_keys(table_name: str) -> set[str]:
        return {key["name"] for key in sa.inspect(bind).get_foreign_keys(table_name) if key["name"]}

    for table_name, column in (
        ("billing_plans", sa.Column("billing_mode", sa.String(length=40), nullable=False, server_default="MILESTONE_EVENT")),
        ("billing_plan_revisions", sa.Column("billing_mode", sa.String(length=40), nullable=False, server_default="MILESTONE_EVENT")),
        ("invoice_revisions", sa.Column("service_period_start", sa.Date(), nullable=True)),
        ("invoice_revisions", sa.Column("service_period_end", sa.Date(), nullable=True)),
        ("invoice_revisions", sa.Column("service_period_label", sa.String(length=120), nullable=True)),
        ("invoices", sa.Column("source_clone_id", sa.String(length=36), nullable=True)),
        ("invoices", sa.Column("clone_idempotency_key", sa.String(length=200), nullable=True)),
    ):
        if column.name not in columns(table_name):
            op.add_column(table_name, column)

    for name, table_name, column_names, unique, where in (
        ("ix_invoices_source_clone_id", "invoices", ["source_clone_id"], False, None),
        ("ix_invoices_clone_idempotency_key", "invoices", ["clone_idempotency_key"], True, "clone_idempotency_key IS NOT NULL"),
    ):
        if name not in indexes(table_name):
            op.create_index(name, table_name, column_names, unique=unique, mssql_where=sa.text(where) if where else None)
    if "fk_invoices_source_clone_id" not in foreign_keys("invoices"):
        op.create_foreign_key("fk_invoices_source_clone_id", "invoices", "invoices", ["source_clone_id"], ["id"])

    table_name = "billing_readiness_requests"
    if table_name not in sa.inspect(bind).get_table_names():
        op.create_table(
            table_name,
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("contract_id", sa.String(length=36), nullable=False),
            sa.Column("billing_plan_revision_id", sa.String(length=36), nullable=False),
            sa.Column("billing_milestone_id", sa.String(length=36), nullable=False),
            sa.Column("requested_by", sa.String(length=200), nullable=False),
            sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("evidence_document_version_id", sa.String(length=36), nullable=True),
            sa.Column("note", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=40), nullable=False, server_default="REQUESTED"),
            sa.Column("idempotency_key", sa.String(length=200), nullable=False),
            sa.Column("correlation_id", sa.String(length=100), nullable=False),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.ForeignKeyConstraint(["contract_id"], ["contracts.id"]),
            sa.ForeignKeyConstraint(["billing_plan_revision_id"], ["billing_plan_revisions.id"]),
            sa.ForeignKeyConstraint(["billing_milestone_id"], ["billing_milestones.id"]),
            sa.ForeignKeyConstraint(["evidence_document_version_id"], ["document_versions.id"]),
            sa.UniqueConstraint("idempotency_key", name="uq_billing_readiness_request_idempotency"),
        )
    for name, column_names in (
        ("ix_billing_readiness_requests_project_id", ["project_id"]),
        ("ix_billing_readiness_requests_contract_id", ["contract_id"]),
        ("ix_billing_readiness_requests_billing_plan_revision_id", ["billing_plan_revision_id"]),
        ("ix_billing_readiness_requests_billing_milestone_id", ["billing_milestone_id"]),
        ("ix_billing_readiness_requests_status", ["status"]),
        ("ix_billing_readiness_requests_correlation_id", ["correlation_id"]),
    ):
        if name not in indexes(table_name):
            op.create_index(name, table_name, column_names)


def downgrade() -> None:
    op.drop_index("ix_billing_readiness_requests_correlation_id", table_name="billing_readiness_requests")
    op.drop_index("ix_billing_readiness_requests_status", table_name="billing_readiness_requests")
    op.drop_index("ix_billing_readiness_requests_billing_milestone_id", table_name="billing_readiness_requests")
    op.drop_index("ix_billing_readiness_requests_billing_plan_revision_id", table_name="billing_readiness_requests")
    op.drop_index("ix_billing_readiness_requests_contract_id", table_name="billing_readiness_requests")
    op.drop_index("ix_billing_readiness_requests_project_id", table_name="billing_readiness_requests")
    op.drop_table("billing_readiness_requests")
    op.drop_constraint("fk_invoices_source_clone_id", "invoices", type_="foreignkey")
    op.drop_index("ix_invoices_clone_idempotency_key", table_name="invoices")
    op.drop_index("ix_invoices_source_clone_id", table_name="invoices")
    op.drop_column("invoices", "clone_idempotency_key")
    op.drop_column("invoices", "source_clone_id")
    op.drop_column("invoice_revisions", "service_period_label")
    op.drop_column("invoice_revisions", "service_period_end")
    op.drop_column("invoice_revisions", "service_period_start")
    op.drop_column("billing_plan_revisions", "billing_mode")
    op.drop_column("billing_plans", "billing_mode")
