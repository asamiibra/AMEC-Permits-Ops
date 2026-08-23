"""E3/E4 contract rendering and admin-comment traceability metadata."""

import sqlalchemy as sa
from alembic import op

revision = "0019_e3_e4_traceability"
down_revision = "0018_e2_shared_runtime_contracts"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())

    def add_missing(table, columns):
        existing = {item["name"] for item in inspector.get_columns(table)}
        missing = [column for column in columns if column.name not in existing]
        if missing:
            with op.batch_alter_table(table) as batch:
                for column in missing:
                    batch.add_column(column)

    add_missing("contract_revisions", [
        sa.Column("rendered_artifact_id", sa.String(36), sa.ForeignKey("rendered_artifacts.id", name="fk_contract_revision_rendered_artifact"), nullable=True),
        sa.Column("template_version_id", sa.String(36), sa.ForeignKey("template_versions.id", name="fk_contract_revision_template_version"), nullable=True),
        sa.Column("render_input_hash", sa.String(64), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("commercial_terms_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    ])
    add_missing("admin_document_comments", [
        sa.Column("source_type", sa.String(60), nullable=False, server_default="ADMIN_DOCUMENT_REVIEW"),
    ])


def downgrade():
    pass
