"""Week 1–8 integrity reconciliation: fixture, governance, and config identity."""

from alembic import op
import sqlalchemy as sa

revision = "0010_week1_8_integrity_reconciliation"
down_revision = "0009_week9_attachment_grid"
branch_labels = None
depends_on = None


def _tables(bind):
    return set(sa.inspect(bind).get_table_names())


def _columns(bind, table):
    return {column["name"] for column in sa.inspect(bind).get_columns(table)} if table in _tables(bind) else set()


def _add(table, column):
    bind = op.get_bind()
    if column.name not in _columns(bind, table):
        op.add_column(table, column)


def upgrade():
    bind = op.get_bind()
    tables = _tables(bind)
    if "legacy_fixture_aliases" not in tables:
        op.create_table(
            "legacy_fixture_aliases",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("legacy_id", sa.String(160), nullable=False, unique=True),
            sa.Column("canonical_id", sa.String(160), nullable=False),
            sa.Column("purpose", sa.String(200), nullable=False),
            sa.Column("temporary", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("remove_by", sa.Date()),
            sa.Column("classification", sa.String(40), nullable=False, server_default="LEGACY_UNIT_TEST_ONLY"),
        )
    if "delivery_authority_statuses" not in tables:
        op.create_table(
            "delivery_authority_statuses",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("track", sa.String(40), nullable=False, unique=True),
            sa.Column("status", sa.String(40), nullable=False),
            sa.Column("basis_artifact", sa.String(300), nullable=False),
            sa.Column("basis_version", sa.String(80)),
            sa.Column("approved_by", sa.String(200)),
            sa.Column("approved_at", sa.DateTime(timezone=True)),
            sa.Column("evidence_reference", sa.String(500)),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "configuration_artifacts" not in tables:
        op.create_table(
            "configuration_artifacts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("stable_id", sa.String(160), nullable=False, unique=True),
            sa.Column("artifact_type", sa.String(100), nullable=False),
            sa.Column("version", sa.String(80), nullable=False),
            sa.Column("checksum", sa.String(64), nullable=False),
            sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
            sa.Column("effective_to", sa.DateTime(timezone=True)),
            sa.Column("status", sa.String(40), nullable=False),
            sa.Column("source_basis", sa.String(300), nullable=False),
            sa.Column("semantic_payload_json", sa.JSON(), nullable=False),
        )
    if "configuration_bundles" not in tables:
        op.create_table(
            "configuration_bundles",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("bundle_id", sa.String(160), nullable=False, unique=True),
            sa.Column("scenario_id", sa.String(36), sa.ForeignKey("scenario_configs.id")),
            sa.Column("bundle_version", sa.String(80), nullable=False),
            sa.Column("artifact_ids_json", sa.JSON(), nullable=False),
            sa.Column("checksum", sa.String(64), nullable=False),
            sa.Column("effective_from", sa.DateTime(timezone=True), nullable=False),
            sa.Column("effective_to", sa.DateTime(timezone=True)),
            sa.Column("status", sa.String(40), nullable=False),
            sa.Column("source_basis", sa.String(300), nullable=False),
        )
    for table, columns in {
        "synthetic_fixture_sets": [
            sa.Column("source_manifest_path", sa.String(300), nullable=True), sa.Column("imported_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("synthetic_only", sa.Boolean(), nullable=True), sa.Column("golden_path_authority", sa.Boolean(), nullable=True),
        ],
        "applicable_rule_sets": [sa.Column("configuration_bundle_id", sa.String(36), nullable=True), sa.Column("configuration_checksum", sa.String(64), nullable=True)],
        "package_readiness_evaluations": [sa.Column("configuration_bundle_id", sa.String(36), nullable=True)],
        "packages": [sa.Column("configuration_bundle_id", sa.String(36), nullable=True)],
        "rendered_forms": [sa.Column("configuration_bundle_id", sa.String(36), nullable=True)],
        "excel_projections": [sa.Column("configuration_bundle_id", sa.String(36), nullable=True), sa.Column("target_rendering_rule_id", sa.String(36), nullable=True)],
        "preparation_revisions": [sa.Column("configuration_bundle_id", sa.String(36), nullable=True)],
        "portal_intended_states": [sa.Column("configuration_bundle_id", sa.String(36), nullable=True)],
        "authority_precheck_runs": [sa.Column("configuration_bundle_id", sa.String(36), nullable=True)],
        "finding_codes": [sa.Column("checksum", sa.String(64), nullable=True)],
        "findings": [sa.Column("finding_code_version", sa.String(40), nullable=True), sa.Column("finding_code_checksum", sa.String(64), nullable=True)],
    }.items():
        for column in columns:
            _add(table, column)


def downgrade():
    bind = op.get_bind()
    for table, columns in {
        "findings": ["finding_code_version", "finding_code_checksum"], "finding_codes": ["checksum"],
        "authority_precheck_runs": ["configuration_bundle_id"], "portal_intended_states": ["configuration_bundle_id"],
        "preparation_revisions": ["configuration_bundle_id"], "excel_projections": ["configuration_bundle_id", "target_rendering_rule_id"],
        "rendered_forms": ["configuration_bundle_id"], "packages": ["configuration_bundle_id"],
        "package_readiness_evaluations": ["configuration_bundle_id"], "applicable_rule_sets": ["configuration_bundle_id", "configuration_checksum"],
        "synthetic_fixture_sets": ["source_manifest_path", "imported_at", "synthetic_only", "golden_path_authority"],
    }.items():
        for column in columns:
            if column in _columns(bind, table):
                op.drop_column(table, column)
    for table in ["configuration_bundles", "configuration_artifacts", "delivery_authority_statuses", "legacy_fixture_aliases"]:
        if table in _tables(bind):
            op.drop_table(table)
