"""Add reusable governed human signatory authority evidence."""

from alembic import op
import sqlalchemy as sa


revision = "governed_signatory_authority_v1"
down_revision = "billing_finance_production_hardening_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    table_name = "governed_signatory_authorities"
    if table_name not in sa.inspect(bind).get_table_names():
        op.create_table(
            "governed_signatory_authorities",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("office_id", sa.String(length=36), nullable=False),
            sa.Column("legal_entity_ref", sa.String(length=160), nullable=False),
            sa.Column("capacity", sa.String(length=120), nullable=False),
            sa.Column("authority_type", sa.String(length=120), nullable=False),
            sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
            sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column("owner_authorization_reference", sa.String(length=240), nullable=False),
            sa.Column("authority_evidence_document_version_id", sa.String(length=36), nullable=True),
            sa.Column("authority_evidence_reference", sa.String(length=500), nullable=True),
            sa.Column("created_by", sa.String(length=36), nullable=False),
            sa.Column("approved_by", sa.String(length=36), nullable=False),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_by", sa.String(length=36), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("superseded_by_id", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_signatory_authority_effective_interval"),
            sa.CheckConstraint("status IN ('ACTIVE', 'REVOKED', 'EXPIRED', 'SUPERSEDED')", name="ck_signatory_authority_status"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["office_id"], ["consultancy_offices.id"]),
            sa.ForeignKeyConstraint(["authority_evidence_document_version_id"], ["document_versions.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes(table_name) if index["name"]}
    for name, column_names in (
        ("ix_governed_signatory_authorities_user_id", ["user_id"]),
        ("ix_governed_signatory_authorities_office_id", ["office_id"]),
        # PostgreSQL limits identifiers to 63 bytes.
        ("ix_signatory_authority_evidence_docver", ["authority_evidence_document_version_id"]),
        ("ix_signatory_authority_user_status", ["user_id", "status"]),
        ("ix_signatory_authority_entity_status", ["legal_entity_ref", "status"]),
    ):
        if name not in indexes:
            op.create_index(name, table_name, column_names)


def downgrade() -> None:
    op.drop_index("ix_signatory_authority_entity_status", table_name="governed_signatory_authorities")
    op.drop_index("ix_signatory_authority_user_status", table_name="governed_signatory_authorities")
    op.drop_index("ix_signatory_authority_evidence_docver", table_name="governed_signatory_authorities")
    op.drop_index("ix_governed_signatory_authorities_office_id", table_name="governed_signatory_authorities")
    op.drop_index("ix_governed_signatory_authorities_user_id", table_name="governed_signatory_authorities")
    op.drop_table("governed_signatory_authorities")
