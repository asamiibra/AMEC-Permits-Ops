"""Dashboard V2 Waves B+C governance companions and release lifecycle."""

from alembic import op
import sqlalchemy as sa

from backend.app.models import Base


revision = "0041_dashboard_v2_waves_b_c"
down_revision = "0040_form_automation_runtime"
branch_labels = None
depends_on = None


def _add(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if column.name not in {row["name"] for row in inspector.get_columns(table)}:
        if bind.dialect.name == "sqlite":
            # SQLite cannot ALTER an existing table to add a column carrying
            # a foreign-key constraint.  Batch mode keeps this migration
            # reversible on the repository's SQLite smoke-test databases.
            with op.batch_alter_table(table, recreate="always") as batch:
                batch.add_column(column)
        else:
            op.add_column(table, column)


def upgrade() -> None:
    _add("requirement_policy_lineage", sa.Column("source_role", sa.String(40), nullable=False, server_default="PRIMARY"))
    _add("requirement_policy_lineage", sa.Column("governance_status", sa.String(30), nullable=False, server_default="DRAFT"))
    _add("requirement_policy_lineage", sa.Column("governance_note", sa.Text(), nullable=True))
    _add("requirement_policy_lineage", sa.Column("confirmed_by", sa.String(200), nullable=True))
    _add("requirement_policy_lineage", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))
    _add("technical_rule_lineage", sa.Column("source_role", sa.String(40), nullable=False, server_default="PRIMARY"))
    _add("technical_rule_lineage", sa.Column("governance_status", sa.String(30), nullable=False, server_default="DRAFT"))
    _add("technical_rule_lineage", sa.Column("governance_note", sa.Text(), nullable=True))
    _add("technical_rule_lineage", sa.Column("confirmed_by", sa.String(200), nullable=True))
    _add("technical_rule_lineage", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True))

    for column in (
        sa.Column("master_content_item_id", sa.String(36), sa.ForeignKey("master_content_items.id", name="fk_form_mapping_releases_master_content_item_id"), nullable=True),
        sa.Column("source_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id", name="fk_form_mapping_releases_source_document_version_id"), nullable=True),
        sa.Column("normalized_rendition_ref", sa.String(500), nullable=True),
        sa.Column("normalized_rendition_hash", sa.String(128), nullable=True),
        sa.Column("semantic_contract_version", sa.String(40), nullable=True),
        sa.Column("renderer_type", sa.String(50), nullable=True),
        sa.Column("renderer_version", sa.String(60), nullable=True),
        sa.Column("mapping_checksum", sa.String(128), nullable=True),
        sa.Column("reviewed_by", sa.String(200), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_by", sa.String(200), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("retired_by", sa.String(200), nullable=True),
        sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("invalidation_reason", sa.Text(), nullable=True),
    ):
        _add("form_mapping_releases", column)
    _add("form_qa_runs", sa.Column("mapping_release_id", sa.String(36), sa.ForeignKey("form_mapping_releases.id", name="fk_form_qa_runs_mapping_release_id"), nullable=True))
    _add("form_qa_runs", sa.Column("qa_type", sa.String(50), nullable=False, server_default="STRUCTURAL_MAPPING"))
    _add("form_qa_runs", sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True))

    existing_tables = set(sa.inspect(op.get_bind()).get_table_names())
    for name in ("master_content_applicability", "automation_readiness_assessments", "form_mapping_release_qa_gates"):
        # The repository's earliest migration uses Base.metadata.create_all,
        # so fresh databases may already contain these tables.  Only create
        # the table when upgrading a real 0040 database that predates them.
        if name not in existing_tables:
            Base.metadata.tables[name].create(bind=op.get_bind())


def downgrade() -> None:
    for name in ("form_mapping_release_qa_gates", "automation_readiness_assessments", "master_content_applicability"):
        Base.metadata.tables[name].drop(bind=op.get_bind(), checkfirst=True)
    for table, columns in {
        "form_qa_runs": ("executed_at", "qa_type", "mapping_release_id"),
        "form_mapping_releases": ("invalidation_reason", "retired_at", "retired_by", "released_at", "released_by", "reviewed_at", "reviewed_by", "mapping_checksum", "renderer_version", "renderer_type", "semantic_contract_version", "normalized_rendition_hash", "normalized_rendition_ref", "source_document_version_id", "master_content_item_id"),
        "technical_rule_lineage": ("confirmed_at", "confirmed_by", "governance_note", "governance_status", "source_role"),
        "requirement_policy_lineage": ("confirmed_at", "confirmed_by", "governance_note", "governance_status", "source_role"),
    }.items():
        inspector = sa.inspect(op.get_bind())
        existing = {row["name"] for row in inspector.get_columns(table)}
        present = [column for column in columns if column in existing]
        if present:
            if op.get_bind().dialect.name != "sqlite":
                # PostgreSQL can remove these columns in place.  Batch
                # recreation would attempt to drop the parent table's primary
                # key index while existing runtime tables still reference it.
                if table == "form_mapping_releases":
                    # These are the only new FK constraints introduced by
                    # this migration on the parent release table.
                    for constraint in ("fk_form_mapping_releases_master_content_item_id", "fk_form_mapping_releases_source_document_version_id"):
                        if constraint in {row["name"] for row in sa.inspect(op.get_bind()).get_foreign_keys(table)}:
                            op.drop_constraint(constraint, table, type_="foreignkey")
                if table == "form_qa_runs" and "mapping_release_id" in present:
                    if "fk_form_qa_runs_mapping_release_id" in {row["name"] for row in sa.inspect(op.get_bind()).get_foreign_keys(table)}:
                        op.drop_constraint("fk_form_qa_runs_mapping_release_id", table, type_="foreignkey")
                for column in present:
                    op.drop_column(table, column)
                continue
            reflected = sa.Table(table, sa.MetaData(), autoload_with=op.get_bind())
            # SQLite batch recreation copies the reflected indexes as well as
            # the columns.  Remove indexes that depend on columns being
            # removed, otherwise the recreated table fails while creating an
            # index for a column that no longer exists.
            for index in list(reflected.indexes):
                if any(column.name in present for column in index.columns):
                    reflected.indexes.remove(index)
            with op.batch_alter_table(table, recreate="always", copy_from=reflected) as batch:
                for column in present:
                    batch.drop_column(column)
