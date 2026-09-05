"""Add governed Content Library draft-apply state to the Azure lineage.

The logical contract originates from the historical Step4 migration, but this
revision deliberately descends from the accepted Azure baseline head.
"""

from alembic import op
import sqlalchemy as sa


revision = "step5_content_library_azure_sql_v1"
down_revision = "baseline_phase4_v36_azure_sql"
branch_labels = None
depends_on = None

SOURCE_STEP4_REVISION = "0059_governed_form_draft_apply"
SOURCE_STEP4_MIGRATION_BLOB = "9a3237016ebdd2c59706545518b646e7e3f3354c"

FORM_INSTANCE_COLUMNS = (
    ("field_provenance_json", sa.JSON(), False, sa.text("'{}'")),
    ("field_citations_json", sa.JSON(), False, sa.text("'{}'")),
    ("field_write_metadata_json", sa.JSON(), False, sa.text("'{}'")),
    ("draft_revision", sa.Integer(), False, sa.text("0")),
    ("last_applied_preview_fingerprint", sa.String(length=128), True, None),
    ("last_applied_by", sa.String(length=200), True, None),
    ("last_applied_at", sa.DateTime(timezone=True), True, None),
)


def upgrade() -> None:
    bind = op.get_bind()
    offline = bool(op.get_context().as_sql)
    inspector = None if offline else sa.inspect(bind)
    existing_columns = (
        set()
        if offline
        else {column["name"] for column in inspector.get_columns("form_instances")}
    )
    for name, column_type, nullable, default in FORM_INSTANCE_COLUMNS:
        if name in existing_columns:
            continue
        op.add_column(
            "form_instances",
            sa.Column(
                name,
                column_type,
                nullable=nullable,
                server_default=default,
            ),
        )
        if default is not None and bind.dialect.name != "sqlite" and not offline:
            op.alter_column("form_instances", name, server_default=None)

    existing_tables = set() if offline else set(inspector.get_table_names())
    if "form_instance_apply_commands" not in existing_tables:
        op.create_table(
            "form_instance_apply_commands",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "form_instance_id",
                sa.String(length=36),
                sa.ForeignKey("form_instances.id"),
                nullable=False,
            ),
            sa.Column("idempotency_key", sa.String(length=200), nullable=False),
            sa.Column("request_fingerprint", sa.String(length=128), nullable=False),
            sa.Column("preview_fingerprint", sa.String(length=128), nullable=False),
            sa.Column("project_id", sa.String(length=36), nullable=False),
            sa.Column("context_type", sa.String(length=50), nullable=False),
            sa.Column("context_id", sa.String(length=36), nullable=False),
            sa.Column("expected_draft_revision", sa.Integer(), nullable=False),
            sa.Column("resulting_draft_revision", sa.Integer(), nullable=False),
            sa.Column(
                "selected_field_keys",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            ),
            sa.Column(
                "applied_field_keys",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'[]'"),
            ),
            sa.Column("actor_id", sa.String(length=200), nullable=False),
            sa.Column(
                "result_json",
                sa.JSON(),
                nullable=False,
                server_default=sa.text("'{}'"),
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "idempotency_key",
                name="uq_form_instance_apply_idempotency",
            ),
        )

    indexes = (
        set()
        if offline
        else {index["name"] for index in inspector.get_indexes("form_instance_apply_commands")}
    )
    if "ix_form_instance_apply_form_instance" not in indexes:
        op.create_index(
            "ix_form_instance_apply_form_instance",
            "form_instance_apply_commands",
            ["form_instance_id"],
            unique=False,
        )
    if "ix_form_instance_apply_commands_project_id" not in indexes:
        op.create_index(
            "ix_form_instance_apply_commands_project_id",
            "form_instance_apply_commands",
            ["project_id"],
            unique=False,
        )


def downgrade() -> None:
    bind = op.get_bind()
    indexes = {
        index["name"]
        for index in sa.inspect(bind).get_indexes("form_instance_apply_commands")
    }
    for name in (
        "ix_form_instance_apply_commands_project_id",
        "ix_form_instance_apply_form_instance",
    ):
        if name in indexes:
            op.drop_index(name, table_name="form_instance_apply_commands")
    if "form_instance_apply_commands" in set(
        sa.inspect(bind).get_table_names()
    ):
        op.drop_table("form_instance_apply_commands")
    for name, _column_type, _nullable, _default in reversed(FORM_INSTANCE_COLUMNS):
        if name in {
            column["name"]
            for column in sa.inspect(bind).get_columns("form_instances")
        }:
            op.drop_column("form_instances", name)
