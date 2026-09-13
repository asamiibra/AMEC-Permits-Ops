"""Bind Proposal output artifacts to durable DocumentVersion records."""

from alembic import op
import sqlalchemy as sa


revision = "proposal_production_hardening_v1"
down_revision = "17c6ebd99c4a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "proposal_output_artifacts",
        sa.Column("document_version_id", sa.String(36), nullable=True),
    )
    op.create_foreign_key(
        "fk_proposal_output_artifacts_document_version",
        "proposal_output_artifacts",
        "document_versions",
        ["document_version_id"],
        ["id"],
    )
    op.create_index(
        "ix_proposal_output_artifacts_document_version_id",
        "proposal_output_artifacts",
        ["document_version_id"],
    )
    for table, name, column, foreign_table in (
        ("proposal_client_responses", "client_account_id", "client_account_id", "client_accounts"),
        ("proposal_client_responses", "client_contact_id", "client_contact_id", "client_contacts"),
        ("proposal_client_responses", "evidence_document_version_id", "evidence_document_version_id", "document_versions"),
        ("proposal_acceptance_verifications", "evidence_sha256", "evidence_sha256", None),
        ("proposal_distribution_events", "delivery_status", "delivery_status", None),
        ("proposal_distribution_events", "receipt_reference", "receipt_reference", None),
        ("proposal_lpo_reconciliations", "comparator_version", "comparator_version", None),
        ("proposal_staleness_events", "revalidation_revision_id", "revalidation_revision_id", "proposal_revisions"),
        ("proposal_staleness_events", "revalidated_by", "revalidated_by", None),
        ("proposal_staleness_events", "revalidated_at", "revalidated_at", None),
        ("proposal_staleness_events", "revalidation_result", "revalidation_result", None),
    ):
        types = {
            "client_account_id": sa.String(36),
            "client_contact_id": sa.String(36),
            "evidence_document_version_id": sa.String(36),
            "evidence_sha256": sa.String(64),
            "delivery_status": sa.String(40),
            "receipt_reference": sa.String(600),
            "comparator_version": sa.String(40),
            "revalidation_revision_id": sa.String(36),
            "revalidated_by": sa.String(200),
            "revalidated_at": sa.DateTime(timezone=True),
            "revalidation_result": sa.String(40),
        }
        op.add_column(table, sa.Column(column, types[column], nullable=True))
        if foreign_table:
            op.create_foreign_key(f"fk_{table}_{column}", table, foreign_table, [column], ["id"])


def downgrade() -> None:
    # Existing synthetic rows remain valid without the optional binding. A
    # downgrade never deletes Proposal output history or document bytes.
    for table, column, foreign_table in (
        ("proposal_staleness_events", "revalidation_result", None),
        ("proposal_staleness_events", "revalidated_at", None),
        ("proposal_staleness_events", "revalidated_by", None),
        ("proposal_staleness_events", "revalidation_revision_id", "proposal_revisions"),
        ("proposal_lpo_reconciliations", "comparator_version", None),
        ("proposal_distribution_events", "receipt_reference", None),
        ("proposal_distribution_events", "delivery_status", None),
        ("proposal_acceptance_verifications", "evidence_sha256", None),
        ("proposal_client_responses", "evidence_document_version_id", "document_versions"),
        ("proposal_client_responses", "client_contact_id", "client_contacts"),
        ("proposal_client_responses", "client_account_id", "client_accounts"),
    ):
        if foreign_table:
            op.drop_constraint(f"fk_{table}_{column}", table, type_="foreignkey")
        op.drop_column(table, column)
    op.drop_index(
        "ix_proposal_output_artifacts_document_version_id",
        table_name="proposal_output_artifacts",
    )
    op.drop_constraint(
        "fk_proposal_output_artifacts_document_version",
        "proposal_output_artifacts",
        type_="foreignkey",
    )
    op.drop_column("proposal_output_artifacts", "document_version_id")
