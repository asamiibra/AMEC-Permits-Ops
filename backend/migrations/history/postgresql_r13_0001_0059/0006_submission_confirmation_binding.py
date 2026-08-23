"""Bind submission confirmation evidence to the preparation revision."""

from alembic import op
import sqlalchemy as sa

revision = "0006_confirmation_binding"
down_revision = "0005_week45"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    existing = {column["name"] for column in sa.inspect(bind).get_columns("submission_confirmations")}
    columns = [
        ("preparation_revision_id", sa.String(length=36)),
        ("application_identity_json", sa.JSON()),
        ("confirmed_by", sa.String(length=200)),
        ("status", sa.String(length=40)),
    ]
    for name, column_type in columns:
        if name not in existing:
            op.add_column("submission_confirmations", sa.Column(name, column_type, nullable=True))
    if bind.dialect.name != "sqlite" and not any(fk.get("name") == "fk_submission_confirmation_preparation_revision" for fk in sa.inspect(bind).get_foreign_keys("submission_confirmations")):
        op.create_foreign_key("fk_submission_confirmation_preparation_revision", "submission_confirmations", "preparation_revisions", ["preparation_revision_id"], ["id"])


def downgrade():
    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_submission_confirmation_preparation_revision", "submission_confirmations", type_="foreignkey")
    for column in ["status", "confirmed_by", "application_identity_json", "preparation_revision_id"]:
        op.drop_column("submission_confirmations", column)
