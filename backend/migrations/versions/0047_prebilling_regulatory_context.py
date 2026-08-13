"""Pre-billing case party, representation, contact, and subject context."""

import sqlalchemy as sa
from alembic import op

from backend.app.models import Base


revision = "0047_prebilling_regulatory_context"
down_revision = "0046_engineering_drawing_review_reconciliation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for name in (
        "authority_case_subjects",
        "party_role_assignments",
        "authorization_grants",
        "contact_points",
        "case_party_snapshots",
    ):
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)
    columns = {item["name"] for item in sa.inspect(bind).get_columns("preparation_revisions")}
    if "case_party_snapshot_id" not in columns:
        column = sa.Column("case_party_snapshot_id", sa.String(36), sa.ForeignKey("case_party_snapshots.id"), nullable=True)
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("preparation_revisions", recreate="always") as batch:
                batch.add_column(column)
        else:
            op.add_column("preparation_revisions", column)
    op.create_index("ix_preparation_revisions_case_party_snapshot_id", "preparation_revisions", ["case_party_snapshot_id"], if_not_exists=True)


def downgrade() -> None:
    # The evidence tables are additive and are intentionally retained during
    # downgrade; no destructive rollback is used for upstream certification.
    pass
