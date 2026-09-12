"""Billing module schema delta for the reconstructed closure candidate."""

from alembic import op
import sqlalchemy as sa


revision = "billing_module_closure_v8"
down_revision = "source18_committee_implementation_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("invoices", sa.Column("project_invoice_ordinal", sa.Integer(), nullable=True))
    op.create_index(
        "uq_invoice_project_ordinal",
        "invoices",
        ["project_id", "project_invoice_ordinal"],
        unique=True,
        postgresql_where=sa.text("project_id IS NOT NULL AND project_invoice_ordinal IS NOT NULL"),
        mssql_where=sa.text("project_id IS NOT NULL AND project_invoice_ordinal IS NOT NULL"),
    )

    op.add_column("invoice_revisions", sa.Column("service_period", sa.String(length=120), nullable=True))
    op.add_column("invoice_revisions", sa.Column("planned_collection_date", sa.Date(), nullable=True))
    op.add_column("invoice_revisions", sa.Column("actual_collection_date", sa.Date(), nullable=True))
    op.add_column("invoice_revisions", sa.Column("actual_collection_date_source", sa.String(length=80), nullable=True))

    op.add_column("payment_receipts", sa.Column("evidence_reference", sa.String(length=500), nullable=True))
    op.add_column("payment_receipts", sa.Column("receipt_voucher_document_version_id", sa.String(length=36), nullable=True))
    op.add_column("payment_receipts", sa.Column("receipt_voucher_evidence_reference", sa.String(length=500), nullable=True))
    op.add_column("payment_receipts", sa.Column("custodian_context_json", sa.JSON(), nullable=True))
    op.create_index("ix_payment_receipts_receipt_voucher_document_version_id", "payment_receipts", ["receipt_voucher_document_version_id"])
    op.create_foreign_key(
        "payment_receipts_receipt_voucher_document_version_id_fkey",
        "payment_receipts",
        "document_versions",
        ["receipt_voucher_document_version_id"],
        ["id"],
    )

    op.add_column("invoice_payment_allocations", sa.Column("reversal_event_id", sa.String(length=36), nullable=True))
    op.create_index("ix_invoice_payment_allocations_reversal_event_id", "invoice_payment_allocations", ["reversal_event_id"])

    op.create_table(
        "payment_reversal_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("payment_receipt_id", sa.String(length=36), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("evidence_document_version_id", sa.String(length=36), nullable=True),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reversed_by", sa.String(length=200), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["payment_receipt_id"], ["payment_receipts.id"], name="payment_reversal_events_payment_receipt_id_fkey"),
        sa.ForeignKeyConstraint(["evidence_document_version_id"], ["document_versions.id"], name="payment_reversal_events_evidence_document_version_id_fkey"),
        sa.PrimaryKeyConstraint("id", name="payment_reversal_events_pkey"),
        sa.UniqueConstraint("idempotency_key", name="uq_payment_reversal_idempotency"),
    )
    op.create_index("ix_payment_reversal_events_payment_receipt_id", "payment_reversal_events", ["payment_receipt_id"])
    op.create_index("ix_payment_reversal_events_evidence_document_version_id", "payment_reversal_events", ["evidence_document_version_id"])

    op.create_table(
        "receivable_resolutions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("invoice_id", sa.String(length=36), nullable=False),
        sa.Column("resolution_type", sa.String(length=50), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("approval_reference", sa.String(length=300), nullable=False),
        sa.Column("evidence_document_version_id", sa.String(length=36), nullable=True),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("resolved_by", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], name="receivable_resolutions_invoice_id_fkey"),
        sa.ForeignKeyConstraint(["evidence_document_version_id"], ["document_versions.id"], name="receivable_resolutions_evidence_document_version_id_fkey"),
        sa.PrimaryKeyConstraint("id", name="receivable_resolutions_pkey"),
        sa.UniqueConstraint("idempotency_key", name="uq_receivable_resolution_idempotency"),
    )
    op.create_index("ix_receivable_resolutions_invoice_id", "receivable_resolutions", ["invoice_id"])
    op.create_index("ix_receivable_resolutions_evidence_document_version_id", "receivable_resolutions", ["evidence_document_version_id"])
    op.create_index("ix_receivable_resolutions_status", "receivable_resolutions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_receivable_resolutions_status", table_name="receivable_resolutions")
    op.drop_index("ix_receivable_resolutions_evidence_document_version_id", table_name="receivable_resolutions")
    op.drop_index("ix_receivable_resolutions_invoice_id", table_name="receivable_resolutions")
    op.drop_table("receivable_resolutions")
    op.drop_index("ix_payment_reversal_events_evidence_document_version_id", table_name="payment_reversal_events")
    op.drop_index("ix_payment_reversal_events_payment_receipt_id", table_name="payment_reversal_events")
    op.drop_table("payment_reversal_events")
    op.drop_index("ix_invoice_payment_allocations_reversal_event_id", table_name="invoice_payment_allocations")
    op.drop_column("invoice_payment_allocations", "reversal_event_id")
    op.drop_constraint("payment_receipts_receipt_voucher_document_version_id_fkey", "payment_receipts", type_="foreignkey")
    op.drop_index("ix_payment_receipts_receipt_voucher_document_version_id", table_name="payment_receipts")
    op.drop_column("payment_receipts", "custodian_context_json")
    op.drop_column("payment_receipts", "receipt_voucher_evidence_reference")
    op.drop_column("payment_receipts", "receipt_voucher_document_version_id")
    op.drop_column("payment_receipts", "evidence_reference")
    op.drop_column("invoice_revisions", "actual_collection_date_source")
    op.drop_column("invoice_revisions", "actual_collection_date")
    op.drop_column("invoice_revisions", "planned_collection_date")
    op.drop_column("invoice_revisions", "service_period")
    op.drop_index("uq_invoice_project_ordinal", table_name="invoices")
    op.drop_column("invoices", "project_invoice_ordinal")
