"""Contract Owner-sketch reconciliation and billing-readiness seam."""

import sqlalchemy as sa
from alembic import op

from backend.app.models import Base


revision = "0045_admin_contract_owner_sketch_reconciliation"
down_revision = "0044_preparation_submission_loop"
branch_labels = None
depends_on = None


def _add(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    if column.name not in {item["name"] for item in sa.inspect(bind).get_columns(table)}:
        op.add_column(table, column)


def upgrade() -> None:
    _add("contracts", sa.Column("payment_condition_text", sa.Text(), nullable=True))
    _add("contracts", sa.Column("contracted_scope_text", sa.Text(), nullable=True))
    _add("contracts", sa.Column("valuation_amount", sa.Numeric(18, 2), nullable=True))
    _add("contracts", sa.Column("valuation_currency", sa.String(20), nullable=True))
    _add("contracts", sa.Column("valuation_basis", sa.String(160), nullable=True))
    _add("contracts", sa.Column("valuation_status", sa.String(50), nullable=False, server_default="UNKNOWN_NON_AUTHORITATIVE"))
    _add("contract_revisions", sa.Column("payment_condition_text", sa.Text(), nullable=True))
    _add("contract_revisions", sa.Column("contracted_scope_text", sa.Text(), nullable=True))
    _add("contract_revisions", sa.Column("valuation_amount", sa.Numeric(18, 2), nullable=True))
    _add("contract_revisions", sa.Column("valuation_currency", sa.String(20), nullable=True))
    _add("contract_revisions", sa.Column("valuation_basis", sa.String(160), nullable=True))
    _add("contract_revisions", sa.Column("valuation_status", sa.String(50), nullable=False, server_default="UNKNOWN_NON_AUTHORITATIVE"))
    _add("contract_admin_evidence", sa.Column("source_role", sa.String(80), nullable=False, server_default="GENERAL"))
    _add("contract_admin_evidence", sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=True))

    for name in (
        "contract_payment_terms",
        "contract_deliverable_commitments",
        "contract_client_input_requirements",
    ):
        Base.metadata.tables[name].create(bind=op.get_bind(), checkfirst=True)


def downgrade() -> None:
    # This migration is additive and intentionally conservative for deployed
    # Contract history.  No existing Contract, Proposal, Project, or Invoice
    # records are removed during rollback.
    pass
