"""Add durable Proposal generation identity and retry state."""
from alembic import op
import sqlalchemy as sa

revision = "proposal_generation_attempts_v1"
down_revision = "proposal_source_decisions_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proposal_generation_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("manifest_hash", sa.String(64), nullable=False),
        sa.Column("generation_kind", sa.String(80), nullable=False, server_default="DOCUMENT_CHANGE_PLAN"),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
        sa.Column("provider_execution_id", sa.String(200)),
        sa.Column("failure_code", sa.String(160)),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("proposal_id", "manifest_hash", "generation_kind", name="uq_proposal_generation_identity"),
    )
    op.create_index("ix_proposal_generation_attempts_proposal_id", "proposal_generation_attempts", ["proposal_id"])
    op.create_index("ix_proposal_generation_attempts_manifest_hash", "proposal_generation_attempts", ["manifest_hash"])
    op.create_index("ix_proposal_generation_attempts_status", "proposal_generation_attempts", ["status"])
    op.create_index("ix_proposal_generation_status", "proposal_generation_attempts", ["proposal_id", "status"])


def downgrade() -> None:
    op.drop_table("proposal_generation_attempts")
