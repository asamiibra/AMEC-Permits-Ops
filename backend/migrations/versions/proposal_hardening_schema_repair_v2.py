"""Repair a Proposal response evidence column omitted by the first hardening step."""

from alembic import op
import sqlalchemy as sa


revision = "proposal_hardening_schema_repair_v2"
down_revision = "proposal_owner_test_profile_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "evidence_sha256" not in {
        item["name"] for item in inspector.get_columns("proposal_client_responses")
    }:
        op.add_column(
            "proposal_client_responses",
            sa.Column("evidence_sha256", sa.String(64), nullable=True),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "evidence_sha256" in {
        item["name"] for item in inspector.get_columns("proposal_client_responses")
    }:
        op.drop_column("proposal_client_responses", "evidence_sha256")
