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
    if bind.dialect.name == "postgresql":
        for table_name, constraint_name, columns, referred_table in (
            ("authority_case_subjects", "authority_case_subjects_authority_case_id_fkey", ["authority_case_id"], "authority_cases"),
            ("authorization_grants", "authorization_grants_authority_case_id_fkey", ["authority_case_id"], "authority_cases"),
            ("authorization_grants", "authorization_grants_grantor_party_id_fkey", ["grantor_party_id"], "parties"),
            ("authorization_grants", "authorization_grants_grantee_party_id_fkey", ["grantee_party_id"], "parties"),
            ("contact_points", "contact_points_authority_case_id_fkey", ["authority_case_id"], "authority_cases"),
            ("contact_points", "contact_points_party_id_fkey", ["party_id"], "parties"),
            ("case_party_snapshots", "case_party_snapshots_authority_case_id_fkey", ["authority_case_id"], "authority_cases"),
            ("case_party_snapshots", "case_party_snapshots_preparation_revision_id_fkey", ["preparation_revision_id"], "preparation_revisions"),
            ("party_role_assignments", "party_role_assignments_authority_case_id_fkey", ["authority_case_id"], "authority_cases"),
            ("party_role_assignments", "party_role_assignments_party_id_fkey", ["party_id"], "parties"),
            ("preparation_revisions", "preparation_revisions_case_party_snapshot_id_fkey", ["case_party_snapshot_id"], "case_party_snapshots"),
        ):
            exists = bind.execute(sa.text(
                "SELECT 1 FROM pg_constraint WHERE conname = :constraint_name"
            ), {"constraint_name": constraint_name}).scalar()
            if not exists:
                op.create_foreign_key(
                    constraint_name, table_name, referred_table, columns, ["id"]
                )


def downgrade() -> None:
    # The evidence tables are additive and are intentionally retained during
    # downgrade; no destructive rollback is used for upstream certification.
    for table_name, constraint_name in (
        ("authorization_grants", "authorization_grants_authority_case_id_fkey"),
        ("authorization_grants", "authorization_grants_grantor_party_id_fkey"),
        ("authorization_grants", "authorization_grants_grantee_party_id_fkey"),
        ("authority_case_subjects", "authority_case_subjects_authority_case_id_fkey"),
        ("contact_points", "contact_points_authority_case_id_fkey"),
        ("contact_points", "contact_points_party_id_fkey"),
        ("case_party_snapshots", "case_party_snapshots_authority_case_id_fkey"),
        ("case_party_snapshots", "case_party_snapshots_preparation_revision_id_fkey"),
        ("party_role_assignments", "party_role_assignments_authority_case_id_fkey"),
        ("party_role_assignments", "party_role_assignments_party_id_fkey"),
        ("preparation_revisions", "preparation_revisions_case_party_snapshot_id_fkey"),
    ):
        op.execute(sa.text(
            f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}"
        ))
