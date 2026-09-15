"""Join the Proposal hardening and shared Intelligence migration chains."""

from alembic import op  # noqa: F401


revision = "proposal_intelligence_combined_merge_v1"
down_revision = ("proposal_production_hardening_v1", "p08_proposal_intelligence")
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The two parent revisions own their schema operations. This revision is
    # an explicit graph join only; it intentionally performs no fake changes.
    pass


def downgrade() -> None:
    pass
