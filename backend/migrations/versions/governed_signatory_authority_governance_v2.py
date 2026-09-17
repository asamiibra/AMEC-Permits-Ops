"""Govern the signatory authority approval lifecycle."""

from alembic import op
import sqlalchemy as sa


revision = "governed_signatory_authority_governance_v2"
down_revision = "governed_signatory_authority_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text(
        "IF EXISTS (SELECT 1 FROM sys.check_constraints "
        "WHERE name = 'ck_signatory_authority_status' "
        "AND parent_object_id = OBJECT_ID('governed_signatory_authorities')) "
        "ALTER TABLE governed_signatory_authorities DROP CONSTRAINT ck_signatory_authority_status"
    ))
    with op.batch_alter_table("governed_signatory_authorities") as batch:
        batch.alter_column("approved_by", existing_type=sa.String(length=36), nullable=True)
        batch.alter_column("approved_at", existing_type=sa.DateTime(timezone=True), nullable=True)
        batch.create_check_constraint(
            "ck_signatory_authority_status",
            "status IN ('PENDING_APPROVAL', 'ACTIVE', 'REVOKED', 'EXPIRED', 'SUPERSEDED')",
        )


def downgrade() -> None:
    with op.batch_alter_table("governed_signatory_authorities") as batch:
        batch.drop_constraint("ck_signatory_authority_status", type_="check")
        batch.create_check_constraint(
            "ck_signatory_authority_status",
            "status IN ('ACTIVE', 'REVOKED', 'EXPIRED', 'SUPERSEDED')",
        )
        batch.alter_column("approved_by", existing_type=sa.String(length=36), nullable=False)
        batch.alter_column("approved_at", existing_type=sa.DateTime(timezone=True), nullable=False)
