"""Source-18 engineers acceptance committee implementation schema."""

from alembic import op
import sqlalchemy as sa


revision = "source18_committee_implementation_v1"
down_revision = "ai_d2_execution_ledger_v1"
branch_labels = None
depends_on = None


def _common(table: str) -> list[sa.Column]:
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "source18_policy_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("policy_code", sa.String(100), nullable=False),
        sa.Column("version", sa.String(40), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("source_class", sa.String(50), nullable=False),
        sa.Column("source_reference", sa.String(500)),
        sa.Column("effective_from", sa.Date()),
        sa.Column("effective_to", sa.Date()),
        sa.Column("rules_json", sa.JSON(), nullable=False),
        sa.Column("created_by", sa.String(200), nullable=False),
        *_common("source18_policy_versions"),
        sa.UniqueConstraint("policy_code", "version", name="uq_source18_policy_version"),
    )
    op.create_table(
        "source18_office_registrations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("office_id", sa.String(36), sa.ForeignKey("consultancy_offices.id"), nullable=False),
        sa.Column("registration_number", sa.String(120), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("currentness_state", sa.String(30), nullable=False),
        sa.Column("source_policy_version_id", sa.String(36), sa.ForeignKey("source18_policy_versions.id")),
        sa.Column("source_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id")),
        sa.Column("effective_from", sa.Date()),
        sa.Column("effective_to", sa.Date()),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        *_common("source18_office_registrations"),
        sa.UniqueConstraint("office_id", "registration_number", name="uq_source18_office_registration"),
    )
    op.create_table(
        "source18_office_certificates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("office_registration_id", sa.String(36), sa.ForeignKey("source18_office_registrations.id"), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("certificate_number", sa.String(120)),
        sa.Column("source_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id")),
        sa.Column("custody_state", sa.String(50), nullable=False),
        sa.Column("supersedes_id", sa.String(36), sa.ForeignKey("source18_office_certificates.id")),
        sa.Column("effective_from", sa.Date()),
        sa.Column("effective_to", sa.Date()),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        *_common("source18_office_certificates"),
        sa.UniqueConstraint("office_registration_id", "version_number", name="uq_source18_certificate_version"),
    )
    op.create_table(
        "source18_office_documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("office_registration_id", sa.String(36), sa.ForeignKey("source18_office_registrations.id"), nullable=False),
        sa.Column("document_type", sa.String(100), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("source_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id")),
        sa.Column("custody_state", sa.String(50), nullable=False),
        sa.Column("supersedes_id", sa.String(36), sa.ForeignKey("source18_office_documents.id")),
        sa.Column("effective_from", sa.Date()),
        sa.Column("effective_to", sa.Date()),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        *_common("source18_office_documents"),
        sa.UniqueConstraint("office_registration_id", "document_type", "version_number", name="uq_source18_office_document_version"),
    )
    op.create_table(
        "source18_engineer_profiles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("office_id", sa.String(36), sa.ForeignKey("consultancy_offices.id"), nullable=False),
        sa.Column("engineer_ref", sa.String(120), nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("discipline", sa.String(120), nullable=False),
        sa.Column("grade_category", sa.String(120)),
        sa.Column("registration_number", sa.String(120)),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("regulatory_profile_state", sa.String(40), nullable=False),
        sa.Column("raw_pii_json", sa.JSON(), nullable=False),
        sa.Column("current_evidence_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id")),
        sa.Column("current_policy_version_id", sa.String(36), sa.ForeignKey("source18_policy_versions.id")),
        sa.Column("evidence_currentness", sa.String(30), nullable=False),
        sa.Column("effective_from", sa.Date()),
        sa.Column("effective_to", sa.Date()),
        *_common("source18_engineer_profiles"),
        sa.UniqueConstraint("office_id", "engineer_ref", name="uq_source18_engineer_profile"),
    )
    op.create_table(
        "source18_roster_memberships",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("office_id", sa.String(36), sa.ForeignKey("consultancy_offices.id"), nullable=False),
        sa.Column("engineer_profile_id", sa.String(36), sa.ForeignKey("source18_engineer_profiles.id"), nullable=False),
        sa.Column("discipline", sa.String(120), nullable=False),
        sa.Column("regulator_counted_state", sa.String(40), nullable=False),
        sa.Column("classified_engineer", sa.Boolean(), nullable=False),
        sa.Column("inside_qatar", sa.Boolean()),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("source_policy_version_id", sa.String(36), sa.ForeignKey("source18_policy_versions.id")),
        sa.Column("source_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id")),
        sa.Column("valid_from", sa.Date()),
        sa.Column("valid_until", sa.Date()),
        sa.Column("source_order", sa.Integer()),
        *_common("source18_roster_memberships"),
    )
    op.create_table(
        "source18_official_form_versions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("form_code", sa.String(100), nullable=False),
        sa.Column("version", sa.String(60), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("currentness_state", sa.String(30), nullable=False),
        sa.Column("source_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id")),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        *_common("source18_official_form_versions"),
        sa.UniqueConstraint("form_code", "version", name="uq_source18_official_form_version"),
    )
    op.create_table(
        "source18_workflow_transactions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("authority_case_id", sa.String(36), sa.ForeignKey("authority_cases.id"), nullable=False),
        sa.Column("office_id", sa.String(36), sa.ForeignKey("consultancy_offices.id"), nullable=False),
        sa.Column("transaction_type", sa.String(60), nullable=False),
        sa.Column("processing_mode", sa.String(40), nullable=False),
        sa.Column("state", sa.String(60), nullable=False),
        sa.Column("engineer_profile_id", sa.String(36), sa.ForeignKey("source18_engineer_profiles.id")),
        sa.Column("current_policy_version_id", sa.String(36), sa.ForeignKey("source18_policy_versions.id")),
        sa.Column("official_form_version_id", sa.String(36), sa.ForeignKey("source18_official_form_versions.id")),
        sa.Column("requirement_version_id", sa.String(36), sa.ForeignKey("requirement_policy_versions.id")),
        sa.Column("currentness_state", sa.String(30), nullable=False),
        sa.Column("remediation_exception", sa.Boolean(), nullable=False),
        sa.Column("requested_disciplines_json", sa.JSON(), nullable=False),
        sa.Column("current_disciplines_json", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("actor_ref", sa.String(200), nullable=False),
        sa.Column("source_snapshot_json", sa.JSON(), nullable=False),
        sa.Column("last_transition_at", sa.DateTime(timezone=True), nullable=False),
        *_common("source18_workflow_transactions"),
        sa.UniqueConstraint("idempotency_key", name="uq_source18_transaction_idempotency"),
    )
    op.create_table(
        "source18_packet_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("source18_workflow_transactions.id"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("packet_hash", sa.String(64), nullable=False),
        sa.Column("manifest_json", sa.JSON(), nullable=False),
        sa.Column("required_signers_json", sa.JSON(), nullable=False),
        sa.Column("signature_state", sa.String(40), nullable=False),
        sa.Column("stamp_state", sa.String(40), nullable=False),
        sa.Column("custody_state", sa.String(50), nullable=False),
        sa.Column("internal_release_state", sa.String(40), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True)),
        sa.Column("supersedes_id", sa.String(36), sa.ForeignKey("source18_packet_revisions.id")),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("transaction_id", "revision_number", name="uq_source18_packet_revision"),
    )
    op.create_table(
        "source18_submission_cycles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("transaction_id", sa.String(36), sa.ForeignKey("source18_workflow_transactions.id"), nullable=False),
        sa.Column("packet_revision_id", sa.String(36), sa.ForeignKey("source18_packet_revisions.id"), nullable=False),
        sa.Column("cycle_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("external_reference", sa.String(200)),
        sa.Column("external_outcome_json", sa.JSON(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_by", sa.String(200), nullable=False),
        *_common("source18_submission_cycles"),
        sa.UniqueConstraint("transaction_id", "cycle_number", name="uq_source18_submission_cycle"),
    )
    op.create_table(
        "source18_external_comments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("submission_cycle_id", sa.String(36), sa.ForeignKey("source18_submission_cycles.id"), nullable=False),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("source_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id")),
        sa.Column("recorded_by", sa.String(200), nullable=False),
        *_common("source18_external_comments"),
    )
    op.create_table(
        "source18_labor_roster_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("office_id", sa.String(36), sa.ForeignKey("consultancy_offices.id"), nullable=False),
        sa.Column("snapshot_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_version", sa.String(100), nullable=False),
        sa.Column("source_ordering_json", sa.JSON(), nullable=False),
        sa.Column("departed_reconciliation_json", sa.JSON(), nullable=False),
        sa.Column("rows_json", sa.JSON(), nullable=False),
        sa.Column("snapshot_hash", sa.String(64), nullable=False),
        sa.Column("captured_by", sa.String(200), nullable=False),
        sa.UniqueConstraint("office_id", "snapshot_hash", name="uq_source18_roster_snapshot_hash"),
    )


def downgrade() -> None:
    for table in (
        "source18_labor_roster_snapshots",
        "source18_external_comments",
        "source18_submission_cycles",
        "source18_packet_revisions",
        "source18_workflow_transactions",
        "source18_official_form_versions",
        "source18_roster_memberships",
        "source18_engineer_profiles",
        "source18_office_documents",
        "source18_office_certificates",
        "source18_office_registrations",
        "source18_policy_versions",
    ):
        op.drop_table(table)
