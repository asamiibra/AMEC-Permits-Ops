"""Durable Owner source staging before Proposal promotion."""
from alembic import op
import sqlalchemy as sa

revision = "proposal_source_staging_v1"
down_revision = "proposal_generation_attempts_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("proposal_source_staging_sessions",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("session_key", sa.String(160), nullable=False),
        sa.Column("source_project_identity", sa.String(200), nullable=False), sa.Column("project_number", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="READY"), sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("source_project_identity", "session_key", name="uq_proposal_source_staging_identity"))
    op.create_index("ix_proposal_source_staging_sessions_source_project_identity", "proposal_source_staging_sessions", ["source_project_identity"])
    op.create_index("ix_proposal_source_staging_sessions_project_number", "proposal_source_staging_sessions", ["project_number"])
    op.create_index("ix_proposal_source_staging_sessions_status", "proposal_source_staging_sessions", ["status"])
    op.create_table("proposal_source_staged_files",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("session_id", sa.String(36), sa.ForeignKey("proposal_source_staging_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False), sa.Column("filename", sa.String(300), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False), sa.Column("logical_category", sa.String(60), nullable=False), sa.Column("verified", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("session_id", "sha256", name="uq_proposal_source_staged_file_hash"))
    op.create_index("ix_proposal_source_staged_files_session_id", "proposal_source_staged_files", ["session_id"])
    op.create_index("ix_proposal_source_staged_files_document_version_id", "proposal_source_staged_files", ["document_version_id"])
    op.create_index("ix_proposal_source_staged_files_sha256", "proposal_source_staged_files", ["sha256"])


def downgrade() -> None:
    op.drop_table("proposal_source_staged_files")
    op.drop_table("proposal_source_staging_sessions")
