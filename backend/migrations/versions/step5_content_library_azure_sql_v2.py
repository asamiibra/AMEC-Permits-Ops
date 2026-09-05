"""Add governed Content Library draft-apply state on Azure SQL safely.

The v1 integration migration is retained only as historical provenance.  This
revision uses deterministic SQL Server DEFAULT-constraint discovery and
cleanup so temporary backfill defaults never become permanent schema state.
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "step5_content_library_azure_sql_v2"
down_revision = "baseline_phase4_v36_azure_sql"
branch_labels = None
depends_on = None

SOURCE_STEP4_REVISION = "0059_governed_form_draft_apply"
SOURCE_STEP4_MIGRATION_BLOB = "9a3237016ebdd2c59706545518b646e7e3f3354c"
SUPERSEDES_FAILED_INTEGRATION_REVISION = "step5_content_library_azure_sql_v1"

FORM_INSTANCE_COLUMNS = (
    ("field_provenance_json", sa.JSON(), sa.text("'{}'")),
    ("field_citations_json", sa.JSON(), sa.text("'{}'")),
    ("field_write_metadata_json", sa.JSON(), sa.text("'{}'")),
    ("draft_revision", sa.Integer(), sa.text("0")),
    ("last_applied_preview_fingerprint", sa.String(length=128), None),
    ("last_applied_by", sa.String(length=200), None),
    ("last_applied_at", sa.DateTime(timezone=True), None),
)

_MSSQL_DEFAULT_QUERY = sa.text(
    """
    SELECT dc.name
    FROM sys.default_constraints AS dc
    JOIN sys.tables AS t ON t.object_id = dc.parent_object_id
    JOIN sys.schemas AS s ON s.schema_id = t.schema_id
    JOIN sys.columns AS c
      ON c.object_id = dc.parent_object_id
     AND c.column_id = dc.parent_column_id
    WHERE s.name = :schema_name
      AND t.name = :table_name
      AND c.name = :column_name
    """
)


def _schema(bind: sa.Connection) -> str | None:
    return "dbo" if bind.dialect.name == "mssql" else None


def _existing_step5_state(bind: sa.Connection) -> tuple[set[str], bool]:
    inspector = sa.inspect(bind)
    schema = _schema(bind)
    tables = set(inspector.get_table_names(schema=schema))
    columns = {
        column["name"]
        for column in inspector.get_columns("form_instances", schema=schema)
    } if "form_instances" in tables else set()
    candidate_columns = {name for name, _type, _default in FORM_INSTANCE_COLUMNS}
    return columns & candidate_columns, "form_instance_apply_commands" in tables


def _mssql_default_constraints(
    bind: sa.Connection,
    column_name: str,
) -> list[str]:
    rows = bind.execute(
        _MSSQL_DEFAULT_QUERY,
        {
            "schema_name": "dbo",
            "table_name": "form_instances",
            "column_name": column_name,
        },
    ).scalars().all()
    return [str(name) for name in rows]


def _drop_mssql_temporary_default(bind: sa.Connection, column_name: str) -> None:
    constraints = _mssql_default_constraints(bind, column_name)
    if len(constraints) != 1:
        raise RuntimeError(
            "STEP5_MSSQL_DEFAULT_CONSTRAINT_COUNT_INVALID "
            f"column={column_name!r} count={len(constraints)}"
        )

    preparer = bind.dialect.identifier_preparer
    table_name = preparer.quote_schema("dbo") + "." + preparer.quote("form_instances")
    constraint_name = preparer.quote(constraints[0])
    bind.exec_driver_sql(
        f"ALTER TABLE {table_name} DROP CONSTRAINT {constraint_name}"
    )

    remaining = _mssql_default_constraints(bind, column_name)
    if remaining:
        raise RuntimeError(
            "STEP5_MSSQL_DEFAULT_CONSTRAINT_REMAINS "
            f"column={column_name!r} count={len(remaining)}"
        )


def _add_form_instance_columns(bind: sa.Connection) -> None:
    inspector = sa.inspect(bind)
    schema = _schema(bind)
    existing = {
        column["name"]
        for column in inspector.get_columns("form_instances", schema=schema)
    }
    for name, column_type, default in FORM_INSTANCE_COLUMNS:
        if name in existing:
            continue
        op.add_column(
            "form_instances",
            sa.Column(
                name,
                column_type,
                nullable=default is None,
                server_default=default,
            ),
            schema=schema,
        )
        if default is None:
            continue
        if bind.dialect.name == "mssql":
            _drop_mssql_temporary_default(bind, name)
        elif bind.dialect.name != "sqlite":
            op.alter_column(
                "form_instances",
                name,
                server_default=None,
                schema=schema,
            )


def _create_apply_commands(bind: sa.Connection) -> None:
    schema = _schema(bind)
    foreign_key_target = (
        "dbo.form_instances.id" if schema is not None else "form_instances.id"
    )
    if "form_instance_apply_commands" not in set(
        sa.inspect(bind).get_table_names(schema=schema)
    ):
        op.create_table(
            "form_instance_apply_commands",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column(
                "form_instance_id",
                sa.String(length=36),
                sa.ForeignKey(foreign_key_target),
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
            schema=schema,
        )


def _create_indexes(bind: sa.Connection) -> None:
    schema = _schema(bind)
    indexes = {
        index["name"]
        for index in sa.inspect(bind).get_indexes(
            "form_instance_apply_commands",
            schema=schema,
        )
    }
    if "ix_form_instance_apply_form_instance" not in indexes:
        op.create_index(
            "ix_form_instance_apply_form_instance",
            "form_instance_apply_commands",
            ["form_instance_id"],
            unique=False,
            schema=schema,
        )
    if "ix_form_instance_apply_commands_project_id" not in indexes:
        op.create_index(
            "ix_form_instance_apply_commands_project_id",
            "form_instance_apply_commands",
            ["project_id"],
            unique=False,
            schema=schema,
        )


def upgrade() -> None:
    bind = op.get_bind()
    existing_columns, apply_table_present = _existing_step5_state(bind)
    if existing_columns or apply_table_present:
        raise RuntimeError(
            "STEP5_PREEXISTING_PARTIAL_SCHEMA_STATE "
            f"columns={sorted(existing_columns)!r} "
            f"apply_table={apply_table_present}"
        )
    _add_form_instance_columns(bind)
    _create_apply_commands(bind)
    _create_indexes(bind)


def downgrade() -> None:
    bind = op.get_bind()
    schema = _schema(bind)
    indexes = {
        index["name"]
        for index in sa.inspect(bind).get_indexes(
            "form_instance_apply_commands",
            schema=schema,
        )
    }
    for name in (
        "ix_form_instance_apply_commands_project_id",
        "ix_form_instance_apply_form_instance",
    ):
        if name in indexes:
            op.drop_index(name, table_name="form_instance_apply_commands", schema=schema)
    if "form_instance_apply_commands" in set(
        sa.inspect(bind).get_table_names(schema=schema)
    ):
        op.drop_table("form_instance_apply_commands", schema=schema)
    for name, _column_type, _default in reversed(FORM_INSTANCE_COLUMNS):
        if name in {
            column["name"]
            for column in sa.inspect(bind).get_columns("form_instances", schema=schema)
        }:
            op.drop_column("form_instances", name, schema=schema)
