"""Persist explicit scoped Finance capability assignments."""

from alembic import op
import sqlalchemy as sa


revision = "scoped_finance_capability_assignment_v1"
down_revision = "billing_finance_experience_closure_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    table_name = "scoped_capability_assignments"
    if table_name not in sa.inspect(bind).get_table_names():
        op.create_table(
            "scoped_capability_assignments",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("user_id", sa.String(length=36), nullable=False),
            sa.Column("capability_code", sa.String(length=120), nullable=False),
            sa.Column("office_id", sa.String(length=36), nullable=True),
            sa.Column("client_account_id", sa.String(length=36), nullable=True),
            sa.Column("project_id", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
            sa.Column("effective_to", sa.DateTime(timezone=True), nullable=True),
            sa.Column("assignment_reference", sa.String(length=200), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("evidence_reference", sa.String(length=300), nullable=True),
            sa.Column("granted_by", sa.String(length=36), nullable=False),
            sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_by", sa.String(length=36), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint("office_id IS NOT NULL OR client_account_id IS NOT NULL OR project_id IS NOT NULL", name="ck_scoped_assignment_non_empty_scope"),
            sa.CheckConstraint("effective_to IS NULL OR effective_to >= effective_from", name="ck_scoped_assignment_effective_interval"),
            sa.CheckConstraint("status IN ('ACTIVE', 'REVOKED', 'EXPIRED')", name="ck_scoped_assignment_status"),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
            sa.ForeignKeyConstraint(["office_id"], ["consultancy_offices.id"]),
            sa.ForeignKeyConstraint(["client_account_id"], ["client_accounts.id"]),
            sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        )
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes(table_name) if index["name"]}
    for name, column_names in (
        ("ix_scoped_capability_assignments_user_id", ["user_id"]),
        ("ix_scoped_capability_assignments_user_capability", ["user_id", "capability_code"]),
        ("ix_scoped_capability_assignments_project_status", ["project_id", "status"]),
        ("ix_scoped_capability_assignments_client_status", ["client_account_id", "status"]),
        ("ix_scoped_capability_assignments_office_id", ["office_id"]),
    ):
        if name not in indexes:
            op.create_index(name, table_name, column_names)


def downgrade() -> None:
    op.drop_index("ix_scoped_capability_assignments_office_id", table_name="scoped_capability_assignments")
    op.drop_index("ix_scoped_capability_assignments_client_status", table_name="scoped_capability_assignments")
    op.drop_index("ix_scoped_capability_assignments_project_status", table_name="scoped_capability_assignments")
    op.drop_index("ix_scoped_capability_assignments_user_capability", table_name="scoped_capability_assignments")
    op.drop_index("ix_scoped_capability_assignments_user_id", table_name="scoped_capability_assignments")
    op.drop_table("scoped_capability_assignments")
