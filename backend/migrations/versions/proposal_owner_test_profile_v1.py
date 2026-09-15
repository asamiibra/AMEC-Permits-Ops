"""Add server-owned Proposal Owner-test fixture classification."""

from alembic import op
import sqlalchemy as sa


revision = "proposal_owner_test_profile_v1"
down_revision = "proposal_intelligence_combined_merge_v1"
branch_labels = None
depends_on = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    return any(item["name"] == column for item in sa.inspect(bind).get_columns(table))


def _has_index(table: str, name: str) -> bool:
    bind = op.get_bind()
    return any(item["name"] == name for item in sa.inspect(bind).get_indexes(table))


def upgrade() -> None:
    if not _has_column("opportunities", "fixture_classification"):
        op.add_column(
            "opportunities",
            sa.Column(
                "fixture_classification",
                sa.String(length=40),
                nullable=False,
                server_default="NON_SYNTHETIC",
            ),
        )
    if not _has_index("opportunities", "ix_opportunities_fixture_classification"):
        op.create_index(
            "ix_opportunities_fixture_classification",
            "opportunities",
            ["fixture_classification"],
        )


def downgrade() -> None:
    op.drop_index("ix_opportunities_fixture_classification", table_name="opportunities")
    op.drop_column("opportunities", "fixture_classification")
