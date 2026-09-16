"""Compatibility bridge for databases stamped by the retired R13 lineage.

The hosted synthetic Vercel database was last stamped at
``0058_source_intake_ledger``.  The active migration location was later
rebaselined, so Alembic could no longer resolve that revision and deployment
bootstrap stopped before applying current migrations.  This no-op bridge
connects the legacy stamp to the active baseline without replaying historical
DDL (the legacy database already contains that schema).
"""

revision = "0058_source_intake_ledger"
down_revision = "baseline_phase4_v36_azure_sql"
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
