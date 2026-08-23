"""Add transactional BD Proposal owner-session records."""

import sqlalchemy as sa
from alembic import op


revision = "0032_bd_proposal_owner_session"
down_revision = "0031_durable_synthetic_master_content_bytes"
branch_labels = None
depends_on = None


def upgrade():
    # Earlier AMEC migrations use Base.metadata.create_all as a compatibility
    # bridge.  On a brand-new database that bridge has already materialized
    # these model tables before this additive migration runs; on an existing
    # deployed 0031 database none of them exist.  Treat the complete set as
    # idempotent so both upgrade paths remain valid.
    existing = set(sa.inspect(op.get_bind()).get_table_names())
    required = {"proposal_source_evidence", "proposal_accepted_revisions", "proposal_output_artifacts", "proposal_owner_settings"}
    if required.issubset(existing):
        return
    op.create_table(
        "proposal_source_evidence",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("source_type", sa.String(40), nullable=False),
        sa.Column("source_filename", sa.String(300), nullable=False),
        sa.Column("source_reference", sa.String(600), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("source_revision", sa.String(80)),
        sa.Column("provenance", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("conflict_key", sa.String(120)),
        sa.Column("status", sa.String(40), nullable=False, server_default="CURRENT"),
        sa.Column("verification_state", sa.String(40), nullable=False, server_default="READ_BACK_VERIFIED"),
        sa.Column("supersedes_id", sa.String(36)),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("proposal_id", "source_type", "content_hash", name="uq_proposal_source_hash"),
    )
    op.create_index("ix_proposal_source_evidence_proposal_id", "proposal_source_evidence", ["proposal_id"])
    op.create_index("ix_proposal_source_evidence_source_type", "proposal_source_evidence", ["source_type"])
    op.create_index("ix_proposal_source_evidence_content_hash", "proposal_source_evidence", ["content_hash"])
    op.create_index("ix_proposal_source_evidence_conflict_key", "proposal_source_evidence", ["conflict_key"])

    op.create_table(
        "proposal_accepted_revisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("revision_number", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("validation_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("template_ref", sa.String(100)),
        sa.Column("template_version_id", sa.String(36)),
        sa.Column("template_version", sa.String(40)),
        sa.Column("template_hash", sa.String(64)),
        sa.Column("checklist_ref", sa.String(100)),
        sa.Column("checklist_version_id", sa.String(36)),
        sa.Column("checklist_version", sa.String(40)),
        sa.Column("checklist_hash", sa.String(64)),
        sa.Column("definition_refs", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("accepted_by", sa.String(200), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="ACCEPTED"),
        sa.Column("supersedes_revision_id", sa.String(36)),
        sa.UniqueConstraint("proposal_id", "revision_number", name="uq_proposal_accepted_revision"),
    )
    op.create_index("ix_proposal_accepted_revisions_proposal_id", "proposal_accepted_revisions", ["proposal_id"])
    op.create_index("ix_proposal_accepted_revisions_content_hash", "proposal_accepted_revisions", ["content_hash"])

    op.create_table(
        "proposal_output_artifacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("revision_id", sa.String(36), sa.ForeignKey("proposal_accepted_revisions.id"), nullable=False),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("artifact_type", sa.String(40), nullable=False),
        sa.Column("filename", sa.String(300), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("storage_reference", sa.String(600), nullable=False),
        sa.Column("lineage", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("synthetic_only", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("revision_id", "artifact_type", name="uq_proposal_output_type"),
    )
    op.create_index("ix_proposal_output_artifacts_revision_id", "proposal_output_artifacts", ["revision_id"])
    op.create_index("ix_proposal_output_artifacts_proposal_id", "proposal_output_artifacts", ["proposal_id"])
    op.create_index("ix_proposal_output_artifacts_content_hash", "proposal_output_artifacts", ["content_hash"])

    op.create_table(
        "proposal_owner_settings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("setting_key", sa.String(120), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("status", sa.String(40), nullable=False, server_default="SAFE_DEFAULT"),
        sa.Column("updated_by", sa.String(200), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("setting_key", name="uq_proposal_owner_setting_key"),
    )


def downgrade():
    op.drop_table("proposal_owner_settings")
    op.drop_index("ix_proposal_output_artifacts_content_hash", table_name="proposal_output_artifacts")
    op.drop_index("ix_proposal_output_artifacts_proposal_id", table_name="proposal_output_artifacts")
    op.drop_index("ix_proposal_output_artifacts_revision_id", table_name="proposal_output_artifacts")
    op.drop_table("proposal_output_artifacts")
    op.drop_index("ix_proposal_accepted_revisions_content_hash", table_name="proposal_accepted_revisions")
    op.drop_index("ix_proposal_accepted_revisions_proposal_id", table_name="proposal_accepted_revisions")
    op.drop_table("proposal_accepted_revisions")
    op.drop_index("ix_proposal_source_evidence_conflict_key", table_name="proposal_source_evidence")
    op.drop_index("ix_proposal_source_evidence_content_hash", table_name="proposal_source_evidence")
    op.drop_index("ix_proposal_source_evidence_source_type", table_name="proposal_source_evidence")
    op.drop_index("ix_proposal_source_evidence_proposal_id", table_name="proposal_source_evidence")
    op.drop_table("proposal_source_evidence")
