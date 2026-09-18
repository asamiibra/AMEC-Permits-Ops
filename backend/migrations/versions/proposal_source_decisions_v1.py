"""Separate mutable Owner source decisions from immutable DocumentVersion evidence."""
from alembic import op
import sqlalchemy as sa

revision = "proposal_source_decisions_v1"
down_revision = "proposal_source_scan_closure_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proposal_source_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_project_identity", sa.String(200), nullable=False),
        sa.Column("logical_source_identity", sa.String(700), nullable=False),
        sa.Column("logical_category", sa.String(60)),
        sa.Column("category_origin", sa.String(30), nullable=False, server_default="AUTO"),
        sa.Column("included_in_proposal", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("inclusion_origin", sa.String(30), nullable=False, server_default="DEFAULT"),
        sa.Column("decision_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("updated_by", sa.String(200)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_project_identity", "logical_source_identity", name="uq_proposal_source_decision_identity"),
    )
    op.create_index("ix_proposal_source_decisions_source_project_identity", "proposal_source_decisions", ["source_project_identity"])
    op.create_index("ix_proposal_source_decisions_logical_source_identity", "proposal_source_decisions", ["logical_source_identity"])


def downgrade() -> None:
    op.drop_table("proposal_source_decisions")
