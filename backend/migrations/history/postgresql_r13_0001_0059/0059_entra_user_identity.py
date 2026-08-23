"""Add stable Microsoft Entra identity binding to ProposalOps users."""

from alembic import op
import sqlalchemy as sa


revision = "0059_entra_user_identity"
down_revision = "0058_source_intake_ledger"
branch_labels = None
depends_on = None


INDEX_NAME = "ix_users_entra_object_id"


def _user_columns() -> set[str]:
    bind = op.get_bind()
    return {
        column["name"]
        for column in sa.inspect(bind).get_columns("users")
    }


def _user_indexes() -> set[str]:
    bind = op.get_bind()
    return {
        index["name"]
        for index in sa.inspect(bind).get_indexes("users")
        if index.get("name")
    }


def upgrade() -> None:
    if "entra_object_id" not in _user_columns():
        op.add_column(
            "users",
            sa.Column(
                "entra_object_id",
                sa.String(length=36),
                nullable=True,
            ),
        )

    if INDEX_NAME not in _user_indexes():
        op.create_index(
            INDEX_NAME,
            "users",
            ["entra_object_id"],
            unique=True,
        )


def downgrade() -> None:
    if INDEX_NAME in _user_indexes():
        op.drop_index(
            INDEX_NAME,
            table_name="users",
        )

    if "entra_object_id" in _user_columns():
        op.drop_column(
            "users",
            "entra_object_id",
        )
