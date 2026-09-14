"""Add server-owned Proposal Owner-test fixture classification."""

from alembic import op
import sqlalchemy as sa


revision = "proposal_owner_test_profile_v1"
down_revision = "proposal_intelligence_combined_merge_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "opportunities",
        sa.Column(
            "fixture_classification",
            sa.String(length=40),
            nullable=False,
            server_default="NON_SYNTHETIC",
        ),
    )
    op.create_index(
        "ix_opportunities_fixture_classification",
        "opportunities",
        ["fixture_classification"],
    )


def downgrade() -> None:
    op.drop_index("ix_opportunities_fixture_classification", table_name="opportunities")
    op.drop_column("opportunities", "fixture_classification")
