"""Add Completion / As-Built technical handoff core with frozen DDL."""

import sqlalchemy as sa
from alembic import op

revision = "0052_completion_asbuilt_core"
down_revision = "0051_construction_inspection_idempotency"
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Completion-era DDL is frozen here; it must not be reconstructed from the
    # current ORM in a future migration run.

    op.execute(sa.text('CREATE TABLE IF NOT EXISTS building_assets (\n\tid VARCHAR(36) NOT NULL, \n\tproject_id VARCHAR(36) NOT NULL, \n\tproperty_id VARCHAR(36), \n\tasset_ref VARCHAR(120) NOT NULL, \n\tname VARCHAR(240) NOT NULL, \n\tbuilding_type VARCHAR(100), \n\tstatus VARCHAR(30) NOT NULL, \n\tcreated_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_building_asset_ref UNIQUE (project_id, asset_ref), \n\tFOREIGN KEY(project_id) REFERENCES projects (id), \n\tFOREIGN KEY(property_id) REFERENCES properties (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_building_assets_property_id ON building_assets (property_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_building_assets_project_id ON building_assets (project_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_building_asset_project_status ON building_assets (project_id, status)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS building_snapshots (\n\tid VARCHAR(36) NOT NULL, \n\tproject_id VARCHAR(36) NOT NULL, \n\tbuilding_asset_id VARCHAR(36) NOT NULL, \n\tsnapshot_type VARCHAR(30) NOT NULL, \n\tversion_number INTEGER NOT NULL, \n\tsnapshot_ref VARCHAR(120) NOT NULL, \n\tvalues_json JSON NOT NULL, \n\tverified_assertion_ids JSON NOT NULL, \n\tsource_document_version_ids JSON NOT NULL, \n\tstatus VARCHAR(30) NOT NULL, \n\tsnapshot_hash VARCHAR(64) NOT NULL, \n\tsupersedes_id VARCHAR(36), \n\tcreated_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_building_snapshot_version UNIQUE (building_asset_id, snapshot_type, version_number), \n\tFOREIGN KEY(project_id) REFERENCES projects (id), \n\tFOREIGN KEY(building_asset_id) REFERENCES building_assets (id), \n\tFOREIGN KEY(supersedes_id) REFERENCES building_snapshots (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_building_snapshots_project_id ON building_snapshots (project_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_building_snapshot_project_type ON building_snapshots (project_id, snapshot_type, status)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_building_snapshots_building_asset_id ON building_snapshots (building_asset_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS construction_completion_contexts (\n\tid VARCHAR(36) NOT NULL, \n\tproject_id VARCHAR(36) NOT NULL, \n\tconstruction_execution_id VARCHAR(36) NOT NULL, \n\tauthority_approved_design_snapshot_id VARCHAR(36), \n\tconstruction_design_snapshot_id VARCHAR(36), \n\twork_state VARCHAR(40) NOT NULL, \n\topen_issue_ids JSON NOT NULL, \n\topen_obligation_ids JSON NOT NULL, \n\tinspection_ids JSON NOT NULL, \n\tmaterial_test_ids JSON NOT NULL, \n\tphysical_evidence_ids JSON NOT NULL, \n\tparty_snapshot JSON NOT NULL, \n\tsource_snapshot_json JSON NOT NULL, \n\tcontext_hash VARCHAR(64) NOT NULL, \n\tstatus VARCHAR(30) NOT NULL, \n\tcreated_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_completion_context_execution UNIQUE (construction_execution_id), \n\tFOREIGN KEY(project_id) REFERENCES projects (id), \n\tFOREIGN KEY(construction_execution_id) REFERENCES construction_executions (id), \n\tFOREIGN KEY(authority_approved_design_snapshot_id) REFERENCES authority_approved_design_snapshots (id), \n\tFOREIGN KEY(construction_design_snapshot_id) REFERENCES construction_design_snapshots (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_construction_completion_contexts_construction_design_31a6 ON construction_completion_contexts (construction_design_snapshot_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_construction_completion_contexts_construction_execution_id ON construction_completion_contexts (construction_execution_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_construction_completion_contexts_authority_approved__fa83 ON construction_completion_contexts (authority_approved_design_snapshot_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_completion_context_project ON construction_completion_contexts (project_id, status)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_construction_completion_contexts_project_id ON construction_completion_contexts (project_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS completion_case_links (\n\tid VARCHAR(36) NOT NULL, \n\tproject_id VARCHAR(36) NOT NULL, \n\tconstruction_execution_id VARCHAR(36) NOT NULL, \n\tconstruction_completion_context_id VARCHAR(36) NOT NULL, \n\tauthority_case_id VARCHAR(36) NOT NULL, \n\tsubject_type VARCHAR(50) NOT NULL, \n\tsubject_id VARCHAR(36) NOT NULL, \n\tidempotency_key VARCHAR(200) NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\tstarted_by VARCHAR(200) NOT NULL, \n\tstarted_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_completion_case_link_idempotency UNIQUE (idempotency_key), \n\tCONSTRAINT uq_completion_case_link_case UNIQUE (authority_case_id), \n\tFOREIGN KEY(project_id) REFERENCES projects (id), \n\tFOREIGN KEY(construction_execution_id) REFERENCES construction_executions (id), \n\tFOREIGN KEY(construction_completion_context_id) REFERENCES construction_completion_contexts (id), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_completion_case_links_construction_execution_id ON completion_case_links (construction_execution_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_completion_case_links_construction_completion_context_id ON completion_case_links (construction_completion_context_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_completion_case_links_project_id ON completion_case_links (project_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_completion_case_links_authority_case_id ON completion_case_links (authority_case_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_completion_case_links_subject_id ON completion_case_links (subject_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_completion_case_link_project ON completion_case_links (project_id, status)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS as_built_baselines (\n\tid VARCHAR(36) NOT NULL, \n\tproject_id VARCHAR(36) NOT NULL, \n\tconstruction_execution_id VARCHAR(36) NOT NULL, \n\tauthority_case_id VARCHAR(36), \n\tsource_construction_design_snapshot_id VARCHAR(36), \n\tbaseline_ref VARCHAR(120) NOT NULL, \n\tversion_number INTEGER NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\tscope_json JSON NOT NULL, \n\tmanifest_hash VARCHAR(64) NOT NULL, \n\tcreated_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tapproved_by VARCHAR(200), \n\tapproved_at TIMESTAMP WITH TIME ZONE, \n\tsupersedes_baseline_id VARCHAR(36), \n\timmutable_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_as_built_baseline_ref UNIQUE (project_id, construction_execution_id, baseline_ref), \n\tCONSTRAINT uq_as_built_baseline_version UNIQUE (project_id, construction_execution_id, version_number), \n\tFOREIGN KEY(project_id) REFERENCES projects (id), \n\tFOREIGN KEY(construction_execution_id) REFERENCES construction_executions (id), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id), \n\tFOREIGN KEY(source_construction_design_snapshot_id) REFERENCES construction_design_snapshots (id), \n\tFOREIGN KEY(supersedes_baseline_id) REFERENCES as_built_baselines (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_baselines_source_construction_design_snapshot_id ON as_built_baselines (source_construction_design_snapshot_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_baselines_supersedes_baseline_id ON as_built_baselines (supersedes_baseline_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_baselines_authority_case_id ON as_built_baselines (authority_case_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_baseline_scope ON as_built_baselines (project_id, construction_execution_id, status)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_baselines_project_id ON as_built_baselines (project_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_baselines_construction_execution_id ON as_built_baselines (construction_execution_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS as_built_baseline_members (\n\tid VARCHAR(36) NOT NULL, \n\tproject_id VARCHAR(36) NOT NULL, \n\tbaseline_id VARCHAR(36) NOT NULL, \n\tengineering_revision_id VARCHAR(36), \n\trendition_id VARCHAR(36), \n\tdocument_version_id VARCHAR(36), \n\tbuilding_snapshot_id VARCHAR(36), \n\tmember_role VARCHAR(80) NOT NULL, \n\tpinned_hash VARCHAR(64) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_as_built_baseline_member UNIQUE (baseline_id, engineering_revision_id, rendition_id, building_snapshot_id), \n\tFOREIGN KEY(project_id) REFERENCES projects (id), \n\tFOREIGN KEY(baseline_id) REFERENCES as_built_baselines (id) ON DELETE CASCADE, \n\tFOREIGN KEY(engineering_revision_id) REFERENCES engineering_deliverable_revisions (id), \n\tFOREIGN KEY(rendition_id) REFERENCES engineering_renditions (id), \n\tFOREIGN KEY(document_version_id) REFERENCES document_versions (id), \n\tFOREIGN KEY(building_snapshot_id) REFERENCES building_snapshots (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_baseline_members_engineering_revision_id ON as_built_baseline_members (engineering_revision_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_baseline_members_project_id ON as_built_baseline_members (project_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_baseline_members_building_snapshot_id ON as_built_baseline_members (building_snapshot_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_baseline_members_rendition_id ON as_built_baseline_members (rendition_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_baseline_members_document_version_id ON as_built_baseline_members (document_version_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_baseline_member_baseline ON as_built_baseline_members (baseline_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS as_built_comparison_runs (\n\tid VARCHAR(36) NOT NULL, \n\tproject_id VARCHAR(36) NOT NULL, \n\tbaseline_id VARCHAR(36) NOT NULL, \n\tconstruction_design_snapshot_id VARCHAR(36), \n\tauthority_approved_building_snapshot_ids JSON NOT NULL, \n\tas_built_building_snapshot_ids JSON NOT NULL, \n\treference_fingerprint VARCHAR(64) NOT NULL, \n\trule_version VARCHAR(40) NOT NULL, \n\tresult VARCHAR(30) NOT NULL, \n\tdifference_count INTEGER NOT NULL, \n\tcreated_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_as_built_comparison_run UNIQUE (baseline_id, reference_fingerprint, rule_version), \n\tFOREIGN KEY(project_id) REFERENCES projects (id), \n\tFOREIGN KEY(baseline_id) REFERENCES as_built_baselines (id), \n\tFOREIGN KEY(construction_design_snapshot_id) REFERENCES construction_design_snapshots (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_comparison_runs_baseline_id ON as_built_comparison_runs (baseline_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_comparison_project ON as_built_comparison_runs (project_id, result)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_comparison_runs_project_id ON as_built_comparison_runs (project_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_comparison_runs_construction_design_snapshot_id ON as_built_comparison_runs (construction_design_snapshot_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS as_built_variances (\n\tid VARCHAR(36) NOT NULL, \n\tproject_id VARCHAR(36) NOT NULL, \n\tcomparison_run_id VARCHAR(36) NOT NULL, \n\tbuilding_asset_id VARCHAR(36), \n\tengineering_revision_id VARCHAR(36), \n\tfield_key VARCHAR(160) NOT NULL, \n\tcategory VARCHAR(80) NOT NULL, \n\tapproved_value_json JSON, \n\tas_built_value_json JSON, \n\tdelta_json JSON NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\tprofessional_disposition VARCHAR(60), \n\trequires_design_change BOOLEAN NOT NULL, \n\trequires_authority_modification BOOLEAN NOT NULL, \n\tdesign_change_request_id VARCHAR(36), \n\tdisposition_reason TEXT, \n\tdispositioned_by VARCHAR(200), \n\tdispositioned_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_as_built_variance_field UNIQUE (comparison_run_id, building_asset_id, field_key), \n\tFOREIGN KEY(project_id) REFERENCES projects (id), \n\tFOREIGN KEY(comparison_run_id) REFERENCES as_built_comparison_runs (id) ON DELETE CASCADE, \n\tFOREIGN KEY(building_asset_id) REFERENCES building_assets (id), \n\tFOREIGN KEY(engineering_revision_id) REFERENCES engineering_deliverable_revisions (id), \n\tFOREIGN KEY(design_change_request_id) REFERENCES design_change_requests (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_variances_project_id ON as_built_variances (project_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_variances_design_change_request_id ON as_built_variances (design_change_request_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_variance_project_status ON as_built_variances (project_id, status)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_variances_building_asset_id ON as_built_variances (building_asset_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_variances_engineering_revision_id ON as_built_variances (engineering_revision_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_as_built_variances_comparison_run_id ON as_built_variances (comparison_run_id)'))

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {column["name"] for column in inspector.get_columns("submission_package_items")}
    foreign_key_details = inspector.get_foreign_keys("submission_package_items")
    has_as_built_foreign_key = any(
        foreign_key.get("referred_table") == "as_built_baselines"
        and foreign_key.get("constrained_columns") == ["as_built_baseline_id"]
        and foreign_key.get("referred_columns") == ["id"]
        for foreign_key in foreign_key_details
    )
    indexes = {index["name"] for index in inspector.get_indexes("submission_package_items")}
    if bind.dialect.name == "sqlite":
        if "as_built_baseline_id" not in columns or not has_as_built_foreign_key or "ix_submission_package_items_as_built_baseline_id" not in indexes:
            with op.batch_alter_table("submission_package_items", recreate="always") as batch:
                if "as_built_baseline_id" not in columns:
                    batch.add_column(sa.Column("as_built_baseline_id", sa.String(length=36), nullable=True))
                if not has_as_built_foreign_key:
                    batch.create_foreign_key("submission_package_items_as_built_baseline_id_fkey", "as_built_baselines", ["as_built_baseline_id"], ["id"])
                if "ix_submission_package_items_as_built_baseline_id" not in indexes:
                    batch.create_index("ix_submission_package_items_as_built_baseline_id", ["as_built_baseline_id"])
        return
    if "as_built_baseline_id" not in columns:
        op.add_column("submission_package_items", sa.Column("as_built_baseline_id", sa.String(length=36), nullable=True))
    if not has_as_built_foreign_key:
        op.create_foreign_key("submission_package_items_as_built_baseline_id_fkey", "submission_package_items", "as_built_baselines", ["as_built_baseline_id"], ["id"])
    if "ix_submission_package_items_as_built_baseline_id" not in indexes:
        op.create_index("ix_submission_package_items_as_built_baseline_id", "submission_package_items", ["as_built_baseline_id"])
    if bind.dialect.name == "postgresql":
        for table_name, constraint_name, columns, referred_table in (
            ("submission_package_items", "submission_package_items_as_built_baseline_id_fkey", ["as_built_baseline_id"], "as_built_baselines"),
            ("building_assets", "building_assets_property_id_fkey", ["property_id"], "properties"),
            ("as_built_variances", "as_built_variances_design_change_request_id_fkey", ["design_change_request_id"], "design_change_requests"),
            ("as_built_baseline_members", "as_built_baseline_members_rendition_id_fkey", ["rendition_id"], "engineering_renditions"),
            ("as_built_baseline_members", "as_built_baseline_members_engineering_revision_id_fkey", ["engineering_revision_id"], "engineering_deliverable_revisions"),
            ("as_built_variances", "as_built_variances_engineering_revision_id_fkey", ["engineering_revision_id"], "engineering_deliverable_revisions"),
            ("as_built_baselines", "as_built_baselines_authority_case_id_fkey", ["authority_case_id"], "authority_cases"),
            ("completion_case_links", "completion_case_links_authority_case_id_fkey", ["authority_case_id"], "authority_cases"),
        ):
            exists = bind.execute(sa.text(
                "SELECT 1 FROM pg_constraint WHERE conname = :constraint_name"
            ), {"constraint_name": constraint_name}).scalar()
            if not exists:
                op.create_foreign_key(
                    constraint_name, table_name, referred_table, columns, ["id"]
                )

def downgrade() -> None:
    # Completion evidence is an audit boundary. Preserve it during ordinary
    # downgrades; any destructive archival requires an explicit operator action.
    op.execute(sa.text(
        "ALTER TABLE submission_package_items "
        "DROP CONSTRAINT IF EXISTS submission_package_items_as_built_baseline_id_fkey"
    ))
    op.execute(sa.text(
        "ALTER TABLE building_assets "
        "DROP CONSTRAINT IF EXISTS building_assets_property_id_fkey"
    ))
    op.execute(sa.text(
        "ALTER TABLE as_built_variances "
        "DROP CONSTRAINT IF EXISTS as_built_variances_design_change_request_id_fkey"
    ))
    op.execute(sa.text(
        "ALTER TABLE as_built_baseline_members "
        "DROP CONSTRAINT IF EXISTS as_built_baseline_members_rendition_id_fkey"
    ))
    op.execute(sa.text(
        "ALTER TABLE as_built_baseline_members "
        "DROP CONSTRAINT IF EXISTS as_built_baseline_members_engineering_revision_id_fkey"
    ))
    op.execute(sa.text(
        "ALTER TABLE as_built_variances "
        "DROP CONSTRAINT IF EXISTS as_built_variances_engineering_revision_id_fkey"
    ))
    op.execute(sa.text(
        "ALTER TABLE as_built_baselines "
        "DROP CONSTRAINT IF EXISTS as_built_baselines_authority_case_id_fkey"
    ))
    op.execute(sa.text(
        "ALTER TABLE completion_case_links "
        "DROP CONSTRAINT IF EXISTS completion_case_links_authority_case_id_fkey"
    ))
