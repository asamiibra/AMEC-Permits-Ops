"""Merge the legacy R13 stamp with the active ProposalOps migration head."""

revision = "proposalops_legacy_0058_merge"
down_revision = ("0058_source_intake_ledger", "proposal_billing_contract_convergence_v1")
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
