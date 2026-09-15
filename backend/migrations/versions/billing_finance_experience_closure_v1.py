"""Close Billing Finance projections and milestone-attributed allocations."""

from alembic import op
import sqlalchemy as sa


revision = "billing_finance_experience_closure_v1"
down_revision = "billing_finance_experience_v1"
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

    if "billing_milestone_id" not in columns("invoice_payment_allocations"):
        op.add_column("invoice_payment_allocations", sa.Column("billing_milestone_id", sa.String(length=36), nullable=True))
    if "ix_invoice_payment_allocations_billing_milestone_id" not in indexes("invoice_payment_allocations"):
        op.create_index("ix_invoice_payment_allocations_billing_milestone_id", "invoice_payment_allocations", ["billing_milestone_id"])
    if "fk_invoice_payment_allocations_billing_milestone_id" not in foreign_keys("invoice_payment_allocations"):
        op.create_foreign_key("fk_invoice_payment_allocations_billing_milestone_id", "invoice_payment_allocations", "billing_milestones", ["billing_milestone_id"], ["id"])

    if "billing_fx_rate_records" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "billing_fx_rate_records",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("source_currency", sa.String(length=20), nullable=False),
            sa.Column("qar_per_source_currency_rate", sa.Numeric(18, 8), nullable=False),
            sa.Column("rate_effective_date", sa.Date(), nullable=False),
            sa.Column("rate_source_reference", sa.String(length=300), nullable=False),
            sa.Column("rate_record_version", sa.Integer(), nullable=False),
            sa.Column("owner_approval_identity", sa.String(length=200), nullable=False),
            sa.Column("owner_approval_time_utc", sa.DateTime(timezone=True), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("source_currency", "rate_record_version", name="uq_billing_fx_rate_version"),
        )
    for name, column_names in (
        ("ix_billing_fx_rate_records_source_currency", ["source_currency"]),
        ("ix_billing_fx_rate_records_status", ["status"]),
    ):
        if name not in indexes("billing_fx_rate_records"):
            op.create_index(name, "billing_fx_rate_records", column_names)

    if "project_expected_exp_versions" not in sa.inspect(bind).get_table_names():
        op.create_table(
            "project_expected_exp_versions",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("value_percent", sa.Numeric(9, 4), nullable=False),
            sa.Column("effective_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("owner_editor_identity", sa.String(length=200), nullable=False),
            sa.Column("edit_time_utc", sa.DateTime(timezone=True), nullable=False),
            sa.Column("source_or_note", sa.Text(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
            sa.UniqueConstraint("project_id", "version", name="uq_project_expected_exp_version"),
        )
    for name, column_names in (
        ("ix_project_expected_exp_versions_project_id", ["project_id"]),
        ("ix_project_expected_exp_versions_status", ["status"]),
    ):
        if name not in indexes("project_expected_exp_versions"):
            op.create_index(name, "project_expected_exp_versions", column_names)


def downgrade() -> None:
    op.drop_index("ix_project_expected_exp_versions_status", table_name="project_expected_exp_versions")
    op.drop_index("ix_project_expected_exp_versions_project_id", table_name="project_expected_exp_versions")
    op.drop_table("project_expected_exp_versions")
    op.drop_index("ix_billing_fx_rate_records_status", table_name="billing_fx_rate_records")
    op.drop_index("ix_billing_fx_rate_records_source_currency", table_name="billing_fx_rate_records")
    op.drop_table("billing_fx_rate_records")
    op.drop_constraint("fk_invoice_payment_allocations_billing_milestone_id", "invoice_payment_allocations", type_="foreignkey")
    op.drop_index("ix_invoice_payment_allocations_billing_milestone_id", table_name="invoice_payment_allocations")
    op.drop_column("invoice_payment_allocations", "billing_milestone_id")
