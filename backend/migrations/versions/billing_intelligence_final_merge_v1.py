"""Close the accepted Billing and P07 Intelligence migration branches."""

from alembic import op


revision = "billing_intelligence_final_merge_v1"
down_revision = (
    "governed_signatory_authority_governance_v2",
    "p07_intelligence_foundation_closure",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Intentional graph-only merge. Both parent branches are already applied;
    # this revision must not mutate tables or data.
    pass


def downgrade() -> None:
    pass
