"""Persist Source18 current regulatory state and packet/custody lineage."""

from alembic import op
import sqlalchemy as sa


revision = "source18_regulatory_current_state_v1"
down_revision = "ai_d2_execution_ledger_v1"
branch_labels = None
depends_on = None


AUTHORITY_CASE_COLUMNS = (
    sa.Column("transaction_type", sa.String(length=100), nullable=True),
    sa.Column("processing_mode", sa.String(length=30), nullable=True),
    sa.Column("project_required", sa.Boolean(), nullable=True),
    sa.Column("currentness_control_implemented", sa.Boolean(), nullable=True),
    sa.Column("current_authority_policy_verified", sa.String(length=30), nullable=True),
    sa.Column("current_official_form_verified", sa.String(length=30), nullable=True),
    sa.Column("live_action_eligibility", sa.String(length=40), nullable=True),
    sa.Column("g5_blocking_currentness_gap", sa.Boolean(), nullable=True),
    sa.Column("official_form_version_id", sa.String(length=36), nullable=True),
    sa.Column("official_form_publisher", sa.String(length=240), nullable=True),
    sa.Column("official_form_number", sa.String(length=120), nullable=True),
    sa.Column("official_form_revision", sa.String(length=80), nullable=True),
    sa.Column("official_form_retrieved_at", sa.DateTime(timezone=True), nullable=True),
    sa.Column("field_authority_schema_json", sa.JSON(), nullable=True),
    sa.Column("packaging_requirements_json", sa.JSON(), nullable=True),
    sa.Column("case_owner", sa.String(length=200), nullable=True),
    sa.Column("task_executor", sa.String(length=200), nullable=True),
    sa.Column("required_signer", sa.String(length=200), nullable=True),
    sa.Column("internal_reviewer", sa.String(length=200), nullable=True),
    sa.Column("first_blocker", sa.String(length=240), nullable=True),
    sa.Column("next_accountable_action", sa.String(length=500), nullable=True),
)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("authority_cases")}
    for column in AUTHORITY_CASE_COLUMNS:
        if column.name not in existing:
            op.add_column("authority_cases", column)
    op.create_index("ix_authority_case_transaction_type", "authority_cases", ["transaction_type"], unique=False)
    op.create_index("ix_authority_case_official_form", "authority_cases", ["official_form_version_id"], unique=False)

    op.create_table(
        "regulatory_state_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("authority_case_id", sa.String(length=36), nullable=True),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("subject_type", sa.String(length=80), nullable=False),
        sa.Column("subject_id", sa.String(length=160), nullable=False),
        sa.Column("state_type", sa.String(length=100), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("is_current", sa.Boolean(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("source_document_version_id", sa.String(length=36), nullable=True),
        sa.Column("source_reference", sa.String(length=500), nullable=True),
        sa.Column("state_json", sa.JSON(), nullable=False),
        sa.Column("supersedes_id", sa.String(length=36), nullable=True),
        sa.Column("accepted_by", sa.String(length=200), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("synthetic_only", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["authority_case_id"], ["authority_cases.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["source_document_version_id"], ["document_versions.id"]),
    )
    op.create_index("ix_regulatory_state_subject", "regulatory_state_versions", ["subject_type", "subject_id", "state_type"])
    op.create_index("ix_regulatory_state_case", "regulatory_state_versions", ["authority_case_id", "state_type"])
    op.create_index("ix_regulatory_state_versions_subject_id", "regulatory_state_versions", ["subject_id"])
    op.create_index("ix_regulatory_state_versions_authority_case_id", "regulatory_state_versions", ["authority_case_id"])
    op.create_index("ix_regulatory_state_versions_project_id", "regulatory_state_versions", ["project_id"])
    op.create_index("ix_regulatory_state_versions_source_document_version_id", "regulatory_state_versions", ["source_document_version_id"])
    op.create_index("ix_regulatory_state_versions_supersedes_id", "regulatory_state_versions", ["supersedes_id"])

    op.create_table(
        "committee_packet_revisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("authority_case_id", sa.String(length=36), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("supersedes_id", sa.String(length=36), nullable=True),
        sa.Column("official_form_version_id", sa.String(length=36), nullable=True),
        sa.Column("form_binding_json", sa.JSON(), nullable=False),
        sa.Column("field_values_json", sa.JSON(), nullable=False),
        sa.Column("authority_only_fields_json", sa.JSON(), nullable=False),
        sa.Column("validation_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("owner_release_by", sa.String(length=200), nullable=True),
        sa.Column("owner_release_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signed_return_document_version_id", sa.String(length=36), nullable=True),
        sa.Column("signed_return_verified_by", sa.String(length=200), nullable=True),
        sa.Column("signed_return_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submission_cycle_id", sa.String(length=36), nullable=True),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("authority_case_id", "revision_number", name="uq_committee_packet_revision"),
        sa.ForeignKeyConstraint(["authority_case_id"], ["authority_cases.id"]),
        sa.ForeignKeyConstraint(["official_form_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["signed_return_document_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["submission_cycle_id"], ["authority_submission_cycles.id"]),
        sa.ForeignKeyConstraint(["supersedes_id"], ["committee_packet_revisions.id"]),
    )
    for name, columns in {
        "ix_committee_packet_revisions_authority_case_id": ["authority_case_id"],
        "ix_committee_packet_revisions_supersedes_id": ["supersedes_id"],
        "ix_committee_packet_revisions_official_form_version_id": ["official_form_version_id"],
        "ix_committee_packet_revisions_signed_return_document_version_id": ["signed_return_document_version_id"],
        "ix_committee_packet_revisions_submission_cycle_id": ["submission_cycle_id"],
    }.items():
        op.create_index(name, "committee_packet_revisions", columns)

    op.create_table(
        "physical_original_custody_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("authority_case_id", sa.String(length=36), nullable=False),
        sa.Column("document_version_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("custodian", sa.String(length=200), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence_document_version_id", sa.String(length=36), nullable=True),
        sa.Column("evidence_reference", sa.String(length=500), nullable=False),
        sa.Column("created_by", sa.String(length=200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["authority_case_id"], ["authority_cases.id"]),
        sa.ForeignKeyConstraint(["document_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["evidence_document_version_id"], ["document_versions.id"]),
    )
    op.create_index("ix_physical_original_case_document", "physical_original_custody_events", ["authority_case_id", "document_version_id", "event_at"])
    op.create_index("ix_physical_original_custody_events_authority_case_id", "physical_original_custody_events", ["authority_case_id"])
    op.create_index("ix_physical_original_custody_events_document_version_id", "physical_original_custody_events", ["document_version_id"])
    op.create_index("ix_physical_original_custody_events_evidence_document_version_id", "physical_original_custody_events", ["evidence_document_version_id"])


def downgrade() -> None:
    for name in (
        "ix_physical_original_custody_events_evidence_document_version_id",
        "ix_physical_original_custody_events_document_version_id",
        "ix_physical_original_custody_events_authority_case_id",
        "ix_physical_original_case_document",
    ):
        op.drop_index(name, table_name="physical_original_custody_events")
    op.drop_table("physical_original_custody_events")
    for name in (
        "ix_committee_packet_revisions_submission_cycle_id",
        "ix_committee_packet_revisions_signed_return_document_version_id",
        "ix_committee_packet_revisions_official_form_version_id",
        "ix_committee_packet_revisions_supersedes_id",
        "ix_committee_packet_revisions_authority_case_id",
    ):
        op.drop_index(name, table_name="committee_packet_revisions")
    op.drop_table("committee_packet_revisions")
    for name in (
        "ix_regulatory_state_versions_supersedes_id",
        "ix_regulatory_state_versions_source_document_version_id",
        "ix_regulatory_state_versions_project_id",
        "ix_regulatory_state_versions_authority_case_id",
        "ix_regulatory_state_versions_subject_id",
        "ix_regulatory_state_case",
        "ix_regulatory_state_subject",
    ):
        op.drop_index(name, table_name="regulatory_state_versions")
    op.drop_table("regulatory_state_versions")
    op.drop_index("ix_authority_case_official_form", table_name="authority_cases")
    op.drop_index("ix_authority_case_transaction_type", table_name="authority_cases")
    for column in reversed(AUTHORITY_CASE_COLUMNS):
        op.drop_column("authority_cases", column.name)
