"""Case-specific Preparation + Submission Loop runtime companions."""

import sqlalchemy as sa
from alembic import op

revision = "0044_preparation_submission_loop"
down_revision = "0043_project_engineering_approved_design_baseline"
branch_labels = None
depends_on = None

TABLES = (
    "authority_case_create_requests", "authority_case_policy_bindings", "requirement_instances",
    "case_evidence_selections", "physical_evidence_items", "submission_packages", "submission_package_items",
    "submission_precheck_runs", "submission_precheck_checks", "submission_attempts", "external_submission_snapshots",
    "authority_submission_cycles", "authority_case_findings", "authority_finding_responses", "authority_case_outcomes",
)

def upgrade() -> None:
    # HISTORICAL_MIGRATION_REPAIR_EXCEPTION: 0044 predates Completion and must
    # not inherit the later SubmissionPackageItem As-Built pin.

    op.execute(sa.text('CREATE TABLE IF NOT EXISTS authority_case_create_requests (\n\tid VARCHAR(36) NOT NULL, \n\tidempotency_key VARCHAR(200) NOT NULL, \n\tauthority_case_id VARCHAR(36) NOT NULL, \n\trequested_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_authority_case_create_idempotency UNIQUE (idempotency_key), \n\tUNIQUE (authority_case_id), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id)\n)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS authority_case_policy_bindings (\n\tid VARCHAR(36) NOT NULL, \n\tauthority_case_id VARCHAR(36) NOT NULL, \n\tpolicy_version_id VARCHAR(36) NOT NULL, \n\tresolution_state VARCHAR(30) NOT NULL, \n\tresolved_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tresolved_by VARCHAR(200) NOT NULL, \n\tresolution_facts JSON NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_authority_case_policy_binding_case UNIQUE (authority_case_id), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id), \n\tFOREIGN KEY(policy_version_id) REFERENCES requirement_policy_versions (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_authority_case_policy_binding_policy ON authority_case_policy_bindings (policy_version_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS requirement_instances (\n\tid VARCHAR(36) NOT NULL, \n\tauthority_case_id VARCHAR(36) NOT NULL, \n\tpolicy_version_id VARCHAR(36) NOT NULL, \n\tpolicy_item_id VARCHAR(36) NOT NULL, \n\trequirement_definition_id VARCHAR(36) NOT NULL, \n\tgroup_id VARCHAR(36), \n\tlifecycle_phase_id VARCHAR(36), \n\tpurpose VARCHAR(50) NOT NULL, \n\tapplicability VARCHAR(30) NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\tdependency_state VARCHAR(30) NOT NULL, \n\treason TEXT NOT NULL, \n\tsource_snapshot JSON NOT NULL, \n\tevaluated_at TIMESTAMP WITH TIME ZONE, \n\tevaluated_by VARCHAR(200), \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_requirement_instance_case_policy_item UNIQUE (authority_case_id, policy_item_id), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id), \n\tFOREIGN KEY(policy_version_id) REFERENCES requirement_policy_versions (id), \n\tFOREIGN KEY(policy_item_id) REFERENCES requirement_policy_items (id), \n\tFOREIGN KEY(requirement_definition_id) REFERENCES requirement_definitions (id), \n\tFOREIGN KEY(group_id) REFERENCES requirement_groups (id), \n\tFOREIGN KEY(lifecycle_phase_id) REFERENCES regulatory_lifecycle_phases (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_requirement_instance_case_status ON requirement_instances (authority_case_id, status)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_requirement_instances_lifecycle_phase_id ON requirement_instances (lifecycle_phase_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_requirement_instances_group_id ON requirement_instances (group_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS case_evidence_selections (\n\tid VARCHAR(36) NOT NULL, \n\tauthority_case_id VARCHAR(36) NOT NULL, \n\trequirement_instance_id VARCHAR(36) NOT NULL, \n\tdocument_version_id VARCHAR(36), \n\tform_instance_id VARCHAR(36), \n\tapproved_design_baseline_id VARCHAR(36), \n\tevidence_kind VARCHAR(50) NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\treason TEXT NOT NULL, \n\tdetails_json JSON NOT NULL, \n\tselected_by VARCHAR(200) NOT NULL, \n\tselected_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id), \n\tFOREIGN KEY(requirement_instance_id) REFERENCES requirement_instances (id), \n\tFOREIGN KEY(document_version_id) REFERENCES document_versions (id), \n\tFOREIGN KEY(form_instance_id) REFERENCES form_instances (id), \n\tFOREIGN KEY(approved_design_baseline_id) REFERENCES approved_design_baselines (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_case_evidence_selections_form_instance_id ON case_evidence_selections (form_instance_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_case_evidence_selection_instance ON case_evidence_selections (requirement_instance_id, status)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_case_evidence_selections_document_version_id ON case_evidence_selections (document_version_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_case_evidence_selection_case ON case_evidence_selections (authority_case_id, document_version_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_case_evidence_selections_approved_design_baseline_id ON case_evidence_selections (approved_design_baseline_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS physical_evidence_items (\n\tid VARCHAR(36) NOT NULL, \n\tauthority_case_id VARCHAR(36) NOT NULL, \n\trequirement_instance_id VARCHAR(36), \n\titem_type VARCHAR(60) NOT NULL, \n\tdescription TEXT NOT NULL, \n\tquantity INTEGER NOT NULL, \n\tstatus VARCHAR(50) NOT NULL, \n\tlocation VARCHAR(240), \n\tcustodian VARCHAR(200), \n\tverified_by VARCHAR(200), \n\tverified_at TIMESTAMP WITH TIME ZONE, \n\tnotes TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id), \n\tFOREIGN KEY(requirement_instance_id) REFERENCES requirement_instances (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_physical_evidence_case_status ON physical_evidence_items (authority_case_id, status)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_physical_evidence_requirement ON physical_evidence_items (requirement_instance_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_physical_evidence_items_requirement_instance_id ON physical_evidence_items (requirement_instance_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS submission_packages (\n\tid VARCHAR(36) NOT NULL, \n\tauthority_case_id VARCHAR(36) NOT NULL, \n\tpreparation_revision_id VARCHAR(36) NOT NULL, \n\tstate VARCHAR(30) NOT NULL, \n\tmanifest_hash VARCHAR(64), \n\tmanifest_json JSON NOT NULL, \n\tlocked_at TIMESTAMP WITH TIME ZONE, \n\tcreated_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_submission_package_preparation UNIQUE (preparation_revision_id), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id), \n\tFOREIGN KEY(preparation_revision_id) REFERENCES preparation_revisions (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_submission_package_case_state ON submission_packages (authority_case_id, state)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS submission_package_items (\n\tid VARCHAR(36) NOT NULL, \n\tpackage_id VARCHAR(36) NOT NULL, \n\titem_type VARCHAR(50) NOT NULL, \n\trequirement_instance_id VARCHAR(36), \n\tevidence_selection_id VARCHAR(36), \n\tdocument_version_id VARCHAR(36), \n\tform_instance_id VARCHAR(36), \n\tbaseline_id VARCHAR(36), \n\tbaseline_member_id VARCHAR(36), \n\tphysical_evidence_item_id VARCHAR(36), \n\tdisplay_order INTEGER NOT NULL, \n\tsection VARCHAR(120), \n\tsubmission_filename VARCHAR(300), \n\tlabel VARCHAR(300), \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_submission_package_item_order UNIQUE (package_id, display_order), \n\tFOREIGN KEY(package_id) REFERENCES submission_packages (id), \n\tFOREIGN KEY(requirement_instance_id) REFERENCES requirement_instances (id), \n\tFOREIGN KEY(evidence_selection_id) REFERENCES case_evidence_selections (id), \n\tFOREIGN KEY(document_version_id) REFERENCES document_versions (id), \n\tFOREIGN KEY(form_instance_id) REFERENCES form_instances (id), \n\tFOREIGN KEY(baseline_id) REFERENCES approved_design_baselines (id), \n\tFOREIGN KEY(baseline_member_id) REFERENCES approved_design_baseline_members (id), \n\tFOREIGN KEY(physical_evidence_item_id) REFERENCES physical_evidence_items (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_submission_package_items_form_instance_id ON submission_package_items (form_instance_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_submission_package_items_requirement_instance_id ON submission_package_items (requirement_instance_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_submission_package_items_physical_evidence_item_id ON submission_package_items (physical_evidence_item_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_submission_package_items_document_version_id ON submission_package_items (document_version_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_submission_package_items_baseline_id ON submission_package_items (baseline_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_submission_package_items_evidence_selection_id ON submission_package_items (evidence_selection_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_submission_package_items_baseline_member_id ON submission_package_items (baseline_member_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_submission_package_item_package ON submission_package_items (package_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS submission_precheck_runs (\n\tid VARCHAR(36) NOT NULL, \n\tauthority_case_id VARCHAR(36) NOT NULL, \n\tpreparation_revision_id VARCHAR(36) NOT NULL, \n\tsubmission_package_id VARCHAR(36) NOT NULL, \n\tpolicy_version_id VARCHAR(36), \n\tpackage_hash VARCHAR(64) NOT NULL, \n\tresult VARCHAR(30) NOT NULL, \n\tdigital_readiness VARCHAR(30) NOT NULL, \n\tphysical_readiness VARCHAR(30) NOT NULL, \n\tevaluated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tevaluated_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id), \n\tFOREIGN KEY(preparation_revision_id) REFERENCES preparation_revisions (id), \n\tFOREIGN KEY(submission_package_id) REFERENCES submission_packages (id), \n\tFOREIGN KEY(policy_version_id) REFERENCES requirement_policy_versions (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_submission_precheck_runs_policy_version_id ON submission_precheck_runs (policy_version_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_submission_precheck_case_result ON submission_precheck_runs (authority_case_id, result)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS submission_precheck_checks (\n\tid VARCHAR(36) NOT NULL, \n\tprecheck_run_id VARCHAR(36) NOT NULL, \n\tcode VARCHAR(100) NOT NULL, \n\tcategory VARCHAR(50) NOT NULL, \n\tresult VARCHAR(30) NOT NULL, \n\tmessage TEXT NOT NULL, \n\tblocking BOOLEAN NOT NULL, \n\tsource_type VARCHAR(80), \n\tsource_id VARCHAR(36), \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(precheck_run_id) REFERENCES submission_precheck_runs (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_submission_precheck_check_run ON submission_precheck_checks (precheck_run_id, blocking, result)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS submission_attempts (\n\tid VARCHAR(36) NOT NULL, \n\tauthority_case_id VARCHAR(36) NOT NULL, \n\tpreparation_revision_id VARCHAR(36) NOT NULL, \n\tsubmission_package_id VARCHAR(36) NOT NULL, \n\tprecheck_run_id VARCHAR(36) NOT NULL, \n\tchannel_code VARCHAR(60) NOT NULL, \n\tattempt_number INTEGER NOT NULL, \n\tidempotency_key VARCHAR(200) NOT NULL, \n\tstate VARCHAR(40) NOT NULL, \n\tauthorized_by VARCHAR(200) NOT NULL, \n\tauthorized_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_submission_attempt_idempotency UNIQUE (idempotency_key), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id), \n\tFOREIGN KEY(preparation_revision_id) REFERENCES preparation_revisions (id), \n\tFOREIGN KEY(submission_package_id) REFERENCES submission_packages (id), \n\tFOREIGN KEY(precheck_run_id) REFERENCES submission_precheck_runs (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_submission_attempt_case_state ON submission_attempts (authority_case_id, state)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS external_submission_snapshots (\n\tid VARCHAR(36) NOT NULL, \n\tsubmission_attempt_id VARCHAR(36) NOT NULL, \n\tauthority_case_id VARCHAR(36) NOT NULL, \n\tchannel_code VARCHAR(60) NOT NULL, \n\tpackage_hash VARCHAR(64) NOT NULL, \n\texternal_reference VARCHAR(240), \n\texternal_status VARCHAR(40) NOT NULL, \n\texternal_submitted_at TIMESTAMP WITH TIME ZONE, \n\tconfirmation_source VARCHAR(40) NOT NULL, \n\tevidence_document_version_id VARCHAR(36), \n\tconfirmed_by VARCHAR(200) NOT NULL, \n\tconfirmed_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tnotes TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_external_snapshot_attempt UNIQUE (submission_attempt_id), \n\tFOREIGN KEY(submission_attempt_id) REFERENCES submission_attempts (id), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id), \n\tFOREIGN KEY(evidence_document_version_id) REFERENCES document_versions (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_external_submission_snapshots_evidence_document_version_id ON external_submission_snapshots (evidence_document_version_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_external_snapshot_case ON external_submission_snapshots (authority_case_id, external_status)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS authority_submission_cycles (\n\tid VARCHAR(36) NOT NULL, \n\tauthority_case_id VARCHAR(36) NOT NULL, \n\tcycle_number INTEGER NOT NULL, \n\tpreparation_revision_id VARCHAR(36) NOT NULL, \n\tsubmission_package_id VARCHAR(36) NOT NULL, \n\texternal_submission_snapshot_id VARCHAR(36) NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_authority_submission_cycle_number UNIQUE (authority_case_id, cycle_number), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id), \n\tFOREIGN KEY(preparation_revision_id) REFERENCES preparation_revisions (id), \n\tFOREIGN KEY(submission_package_id) REFERENCES submission_packages (id), \n\tFOREIGN KEY(external_submission_snapshot_id) REFERENCES external_submission_snapshots (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_authority_submission_cycle_case_status ON authority_submission_cycles (authority_case_id, status)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS authority_case_findings (\n\tid VARCHAR(36) NOT NULL, \n\tauthority_case_id VARCHAR(36) NOT NULL, \n\tsubmission_cycle_id VARCHAR(36), \n\tsource_document_version_id VARCHAR(36), \n\texternal_finding_id VARCHAR(160), \n\tcategory VARCHAR(50) NOT NULL, \n\ttitle VARCHAR(300) NOT NULL, \n\traw_text TEXT NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\tseverity VARCHAR(30) NOT NULL, \n\treceived_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcaptured_by VARCHAR(200) NOT NULL, \n\tengineering_impact VARCHAR(30) NOT NULL, \n\taffected_requirement_instance_id VARCHAR(36), \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id), \n\tFOREIGN KEY(submission_cycle_id) REFERENCES authority_submission_cycles (id), \n\tFOREIGN KEY(source_document_version_id) REFERENCES document_versions (id), \n\tFOREIGN KEY(affected_requirement_instance_id) REFERENCES requirement_instances (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_authority_case_findings_source_document_version_id ON authority_case_findings (source_document_version_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_authority_case_findings_submission_cycle_id ON authority_case_findings (submission_cycle_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_authority_case_finding_cycle ON authority_case_findings (submission_cycle_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_authority_case_findings_affected_requirement_instance_id ON authority_case_findings (affected_requirement_instance_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_authority_case_finding_case_status ON authority_case_findings (authority_case_id, status)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS authority_finding_responses (\n\tid VARCHAR(36) NOT NULL, \n\tfinding_id VARCHAR(36) NOT NULL, \n\tresponse_text TEXT NOT NULL, \n\tsupporting_evidence_json JSON NOT NULL, \n\taffected_requirement_instance_id VARCHAR(36), \n\taffected_baseline_id VARCHAR(36), \n\tstatus VARCHAR(40) NOT NULL, \n\tprepared_by VARCHAR(200) NOT NULL, \n\treviewed_by VARCHAR(200), \n\treviewed_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(finding_id) REFERENCES authority_case_findings (id), \n\tFOREIGN KEY(affected_requirement_instance_id) REFERENCES requirement_instances (id), \n\tFOREIGN KEY(affected_baseline_id) REFERENCES approved_design_baselines (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_authority_finding_response_finding ON authority_finding_responses (finding_id, status)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS authority_case_outcomes (\n\tid VARCHAR(36) NOT NULL, \n\tauthority_case_id VARCHAR(36) NOT NULL, \n\tsubmission_cycle_id VARCHAR(36), \n\toutcome_type VARCHAR(40) NOT NULL, \n\tstatus VARCHAR(30) NOT NULL, \n\texternal_identifier VARCHAR(240), \n\tsource_document_version_id VARCHAR(36), \n\tevidence_snapshot_json JSON NOT NULL, \n\tissued_at TIMESTAMP WITH TIME ZONE, \n\tverified_by VARCHAR(200) NOT NULL, \n\tverified_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(authority_case_id) REFERENCES authority_cases (id), \n\tFOREIGN KEY(submission_cycle_id) REFERENCES authority_submission_cycles (id), \n\tFOREIGN KEY(source_document_version_id) REFERENCES document_versions (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_authority_case_outcomes_source_document_version_id ON authority_case_outcomes (source_document_version_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_authority_case_outcome_case ON authority_case_outcomes (authority_case_id, outcome_type)'))

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = {column["name"] for column in inspector.get_columns("preparation_revisions")}
    columns = (
        ("authority_case_id", sa.Column("authority_case_id", sa.String(36), sa.ForeignKey("authority_cases.id", name="fk_preparation_revisions_authority_case"), nullable=True)),
        ("authority_revision_number", sa.Column("authority_revision_number", sa.Integer(), nullable=True)),
        ("authority_policy_version_id", sa.Column("authority_policy_version_id", sa.String(36), sa.ForeignKey("requirement_policy_versions.id", name="fk_preparation_revisions_authority_policy"), nullable=True)),
        ("authority_approved_design_baseline_id", sa.Column("authority_approved_design_baseline_id", sa.String(36), sa.ForeignKey("approved_design_baselines.id", name="fk_preparation_revisions_authority_baseline"), nullable=True)),
        ("authority_state", sa.Column("authority_state", sa.String(40), nullable=True)),
        ("authority_snapshot_hash", sa.Column("authority_snapshot_hash", sa.String(64), nullable=True)),
        ("authority_snapshot_json", sa.Column("authority_snapshot_json", sa.JSON(), nullable=False, server_default="{}")),
        ("authority_locked_at", sa.Column("authority_locked_at", sa.DateTime(timezone=True), nullable=True)),
        ("authority_supersedes_revision_id", sa.Column("authority_supersedes_revision_id", sa.String(36), nullable=True)),
    )
    if bind.dialect.name == "sqlite":
        missing = [column for name, column in columns if name not in existing]
        if missing:
            with op.batch_alter_table("preparation_revisions", recreate="always") as batch:
                for column in missing:
                    batch.add_column(column)
    else:
        for name, column in columns:
            if name not in existing:
                op.add_column("preparation_revisions", column)
    for index_name, column_name in (
        ("ix_preparation_revisions_authority_case_id", "authority_case_id"),
        ("ix_preparation_revisions_authority_policy_version_id", "authority_policy_version_id"),
        ("ix_preparation_revisions_authority_approved_design_baseline_id", "authority_approved_design_baseline_id"),
        ("ix_preparation_revisions_authority_state", "authority_state"),
    ):
        op.create_index(index_name, "preparation_revisions", [column_name], if_not_exists=True)

def downgrade() -> None:
    for name in reversed(TABLES):
        op.drop_table(name, if_exists=True)
    for index_name in ("ix_preparation_revisions_authority_state", "ix_preparation_revisions_authority_approved_design_baseline_id", "ix_preparation_revisions_authority_policy_version_id", "ix_preparation_revisions_authority_case_id"):
        op.drop_index(index_name, table_name="preparation_revisions", if_exists=True)
    names = ("authority_supersedes_revision_id", "authority_locked_at", "authority_snapshot_json", "authority_snapshot_hash", "authority_state", "authority_approved_design_baseline_id", "authority_policy_version_id", "authority_revision_number", "authority_case_id")
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("preparation_revisions", recreate="always") as batch:
            for name in names:
                batch.drop_column(name)
    else:
        for name in names:
            op.drop_column("preparation_revisions", name)
