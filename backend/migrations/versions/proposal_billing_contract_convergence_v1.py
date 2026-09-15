"""Converge Proposal production, Billing, and Contract migration lineages."""

from alembic import op

revision = "proposal_billing_contract_convergence_v1"
down_revision = (
    "proposal_owner_test_profile_v1",
    "billing_intelligence_final_merge_v1",
    "contract_reconciliation_scheduler_v1",
)
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Graph-only forward merge. The parent revisions carry all schema changes.
    pass


def downgrade() -> None:
    # The convergence revision is intentionally not a history rewrite.
    pass
