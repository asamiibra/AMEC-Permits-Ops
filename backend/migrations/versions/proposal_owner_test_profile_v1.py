"""Add server-owned Proposal Owner-test fixture classification."""

from alembic import op
import sqlalchemy as sa


revision = "proposal_owner_test_profile_v1"
down_revision = "proposal_intelligence_combined_merge_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "fixture_classification" not in {
        item["name"] for item in inspector.get_columns("opportunities")
    }:
        op.add_column(
            "opportunities",
            sa.Column(
                "fixture_classification",
                sa.String(length=40),
                nullable=False,
                server_default="NON_SYNTHETIC",
            ),
        )
    if "ix_opportunities_fixture_classification" not in {
        item["name"] for item in inspector.get_indexes("opportunities")
    }:
        op.create_index(
            "ix_opportunities_fixture_classification",
            "opportunities",
            ["fixture_classification"],
        )


def downgrade() -> None:
    op.drop_index("ix_opportunities_fixture_classification", table_name="opportunities")
    op.drop_column("opportunities", "fixture_classification")
