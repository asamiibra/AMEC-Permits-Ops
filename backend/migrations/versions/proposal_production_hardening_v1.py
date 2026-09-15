"""Bind Proposal output artifacts to durable DocumentVersion records."""

from alembic import op
import sqlalchemy as sa


revision = "proposal_production_hardening_v1"
down_revision = "17c6ebd99c4a"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return any(item["name"] == column for item in sa.inspect(bind).get_columns(table))


def _has_index(table: str, name: str) -> bool:
    bind = op.get_bind()
    return any(item["name"] == name for item in sa.inspect(bind).get_indexes(table))


def _has_foreign_key(
    table: str,
    name: str,
    column: str,
    foreign_table: str,
) -> bool:
    bind = op.get_bind()
    for item in sa.inspect(bind).get_foreign_keys(table):
        if item.get("name") == name:
            return True
        if (
            item.get("referred_table") == foreign_table
            and item.get("constrained_columns") == [column]
            and item.get("referred_columns") == ["id"]
        ):
            return True
    return False


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if not _has_column(table, column.name):
        op.add_column(table, column)


def _create_foreign_key_if_missing(
    name: str,
    table: str,
    column: str,
    foreign_table: str,
) -> None:
    if not _has_foreign_key(table, name, column, foreign_table):
        op.create_foreign_key(name, table, foreign_table, [column], ["id"])


def upgrade() -> None:
    _add_column_if_missing(
        "proposal_output_artifacts",
        sa.Column("document_version_id", sa.String(36), nullable=True),
    )
    _create_foreign_key_if_missing(
        "fk_proposal_output_artifacts_document_version",
        "proposal_output_artifacts",
        "document_version_id",
        "document_versions",
    )
    if not _has_index("proposal_output_artifacts", "ix_proposal_output_artifacts_document_version_id"):
        op.create_index(
            "ix_proposal_output_artifacts_document_version_id",
            "proposal_output_artifacts",
            ["document_version_id"],
        )
    for table, name, column, foreign_table in (
        ("proposal_client_responses", "client_account_id", "client_account_id", "client_accounts"),
        ("proposal_client_responses", "client_contact_id", "client_contact_id", "client_contacts"),
        ("proposal_client_responses", "evidence_document_version_id", "evidence_document_version_id", "document_versions"),
        ("proposal_service_eligibility", "evidence_sha256", "evidence_sha256", None),
        ("proposal_service_eligibility", "scope_confirmation_id", "scope_confirmation_id", "proposal_scope_confirmations"),
        ("proposal_service_eligibility", "scope_revision_hash", "scope_revision_hash", None),
        ("proposal_service_eligibility", "authority_snapshot", "authority_snapshot", None),
        ("proposal_service_eligibility", "policy_version", "policy_version", None),
        ("proposal_service_eligibility", "as_of", "as_of", None),
        ("proposal_acceptance_verifications", "evidence_sha256", "evidence_sha256", None),
        ("proposal_distribution_events", "delivery_status", "delivery_status", None),
        ("proposal_distribution_events", "receipt_reference", "receipt_reference", None),
        ("proposal_distribution_events", "output_artifact_id", "output_artifact_id", "proposal_output_artifacts"),
        ("proposal_distribution_events", "output_artifact_hash", "output_artifact_hash", None),
        ("proposal_distribution_events", "evidence_sha256", "evidence_sha256", None),
        ("proposal_lpo_reconciliations", "comparator_version", "comparator_version", None),
        ("proposal_lpo_reconciliations", "source_sha256", "source_sha256", None),
        ("proposal_lpo_reconciliations", "mapping_version", "mapping_version", None),
        ("proposal_lpo_reconciliations", "mapped_fields", "mapped_fields", None),
        ("proposal_lpo_reconciliations", "mapper_identity", "mapper_identity", None),
        ("proposal_lpo_reconciliations", "mapped_at", "mapped_at", None),
        ("proposal_lpo_reconciliations", "accepted_revision_hash", "accepted_revision_hash", None),
        ("proposal_staleness_events", "revalidation_revision_id", "revalidation_revision_id", "proposal_revisions"),
        ("proposal_staleness_events", "revalidation_accepted_revision_id", "revalidation_accepted_revision_id", "proposal_accepted_revisions"),
        ("proposal_staleness_events", "revalidated_by", "revalidated_by", None),
        ("proposal_staleness_events", "revalidated_at", "revalidated_at", None),
        ("proposal_staleness_events", "revalidation_result", "revalidation_result", None),
    ):
        types = {
            "client_account_id": sa.String(36),
            "client_contact_id": sa.String(36),
            "evidence_document_version_id": sa.String(36),
            "evidence_sha256": sa.String(64),
            "scope_confirmation_id": sa.String(36),
            "scope_revision_hash": sa.String(64),
            "authority_snapshot": sa.JSON(),
            "policy_version": sa.String(100),
            "as_of": sa.DateTime(timezone=True),
            "delivery_status": sa.String(40),
            "receipt_reference": sa.String(600),
            "output_artifact_id": sa.String(36),
            "output_artifact_hash": sa.String(64),
            "comparator_version": sa.String(40),
            "source_sha256": sa.String(64),
            "mapping_version": sa.String(80),
            "mapped_fields": sa.JSON(),
            "mapper_identity": sa.String(200),
            "mapped_at": sa.DateTime(timezone=True),
            "accepted_revision_hash": sa.String(64),
            "revalidation_revision_id": sa.String(36),
            "revalidation_accepted_revision_id": sa.String(36),
            "revalidated_by": sa.String(200),
            "revalidated_at": sa.DateTime(timezone=True),
            "revalidation_result": sa.String(40),
        }
        _add_column_if_missing(table, sa.Column(column, types[column], nullable=True))
        if foreign_table:
            _create_foreign_key_if_missing(
                f"fk_{table}_{column}",
                table,
                column,
                foreign_table,
            )


def downgrade() -> None:
    # Existing synthetic rows remain valid without the optional binding. A
    # downgrade never deletes Proposal output history or document bytes.
    for table, column, foreign_table in (
        ("proposal_lpo_reconciliations", "accepted_revision_hash", None),
        ("proposal_lpo_reconciliations", "mapped_at", None),
        ("proposal_lpo_reconciliations", "mapper_identity", None),
        ("proposal_lpo_reconciliations", "mapped_fields", None),
        ("proposal_lpo_reconciliations", "mapping_version", None),
        ("proposal_lpo_reconciliations", "source_sha256", None),
        ("proposal_staleness_events", "revalidation_result", None),
        ("proposal_staleness_events", "revalidated_at", None),
        ("proposal_staleness_events", "revalidated_by", None),
        ("proposal_staleness_events", "revalidation_revision_id", "proposal_revisions"),
        ("proposal_staleness_events", "revalidation_accepted_revision_id", "proposal_accepted_revisions"),
        ("proposal_lpo_reconciliations", "comparator_version", None),
        ("proposal_distribution_events", "receipt_reference", None),
        ("proposal_distribution_events", "delivery_status", None),
        ("proposal_distribution_events", "evidence_sha256", None),
        ("proposal_distribution_events", "output_artifact_hash", None),
        ("proposal_distribution_events", "output_artifact_id", "proposal_output_artifacts"),
        ("proposal_acceptance_verifications", "evidence_sha256", None),
        ("proposal_service_eligibility", "as_of", None),
        ("proposal_service_eligibility", "policy_version", None),
        ("proposal_service_eligibility", "authority_snapshot", None),
        ("proposal_service_eligibility", "scope_revision_hash", None),
        ("proposal_service_eligibility", "scope_confirmation_id", "proposal_scope_confirmations"),
        ("proposal_service_eligibility", "evidence_sha256", None),
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
