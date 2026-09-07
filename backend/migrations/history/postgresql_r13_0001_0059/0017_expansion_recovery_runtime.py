"""E2 shared runtime and E3/E4 synthetic recovery controls."""

import sqlalchemy as sa
from alembic import op
from backend.app.models import Base

revision = "0017_expansion_recovery_runtime"
down_revision = "0016_stage1_v2_6_expansion_foundation"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())

    def add_missing(table, columns):
        missing = [column for column in columns if column.name not in {item["name"] for item in inspector.get_columns(table)}]
        if missing:
            with op.batch_alter_table(table) as batch:
                for column in missing:
                    batch.add_column(column)

    add_missing("quotation_revisions", [
        sa.Column("rendered_artifact_id", sa.String(36), sa.ForeignKey("rendered_artifacts.id", name="fk_quotation_revision_rendered_artifact"), nullable=True),
        sa.Column("render_input_hash", sa.String(64), nullable=True),
    ])
    add_missing("checklist_items", [
        sa.Column("current_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id", name="fk_checklist_current_document_version"), nullable=True),
        sa.Column("applicability", sa.String(50), nullable=False, server_default="APPLICABLE"),
        sa.Column("validity_status", sa.String(50), nullable=False, server_default="UNKNOWN_REVIEW_REQUIRED"),
        sa.Column("owner_role", sa.String(100), nullable=False, server_default="ADMIN_PROJECT_COORDINATOR"),
    ])
    add_missing("communication_drafts", [
        sa.Column("policy_state", sa.String(50), nullable=False, server_default="HUMAN_SEND"),
        sa.Column("reviewed_by", sa.String(200), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
    ])
    add_missing("rendered_artifacts", [
        sa.Column("render_input_hash", sa.String(64), nullable=True),
        sa.Column("source_revision_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("rendered_values", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("language", sa.String(10), nullable=False, server_default="EN"),
        sa.Column("synthetic_only", sa.Boolean(), nullable=False, server_default=sa.true()),
    ])
    add_missing("assistant_capability_definitions", [
        sa.Column("execution_authority", sa.String(50), nullable=False, server_default="PROTOTYPE_DEV_ONLY"),
        sa.Column("enabled_in_prototype", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("enabled_in_production", sa.Boolean(), nullable=False, server_default=sa.false()),
    ])
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    bind = op.get_bind()
    for table in [
        "quotation_releases", "project_status_projections", "admin_document_comments", "system_blocks",
        "contract_execution_evidence", "client_responses", "quotation_field_observations", "execution_authority_configs",
    ]:
        op.drop_table(table)
    for table, column in [
        ("assistant_capability_definitions", "enabled_in_production"),
        ("assistant_capability_definitions", "enabled_in_prototype"),
        ("assistant_capability_definitions", "execution_authority"),
        ("rendered_artifacts", "synthetic_only"), ("rendered_artifacts", "language"),
        ("rendered_artifacts", "rendered_values"), ("rendered_artifacts", "source_revision_ids"),
        ("rendered_artifacts", "render_input_hash"),
        ("communication_drafts", "reviewed_at"), ("communication_drafts", "reviewed_by"), ("communication_drafts", "policy_state"),
        ("quotation_revisions", "render_input_hash"), ("quotation_revisions", "rendered_artifact_id"),
        ("checklist_items", "owner_role"), ("checklist_items", "validity_status"),
        ("checklist_items", "applicability"), ("checklist_items", "current_document_version_id"),
    ]:
        with op.batch_alter_table(table) as batch:
            batch.drop_column(column)
