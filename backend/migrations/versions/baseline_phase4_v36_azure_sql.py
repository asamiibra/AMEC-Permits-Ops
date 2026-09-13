"""Frozen Azure SQL logical baseline derived from accepted PostgreSQL provenance."""

from alembic import op
import sqlalchemy as sa

revision = "baseline_phase4_v36_azure_sql"
down_revision = None
branch_labels = None
depends_on = None

REFERENCE_SCHEMA_CONTRACT_SHA256 = '1f75d13fbac7b42585504df2da7c48a2bf6c22def49fedff64a13954dfa540e1'
REFERENCE_CONTROL_DATA_SHA256 = 'b423173037fb3b16a4d0a158faa8321397e926c2721b6a4c5b12c501b2b0f27f'

def upgrade() -> None:
    # Explicit operations are emitted from reference ordinal positions.
    # The reference package, not live ORM declaration order, is authoritative.
    op.create_table('acceptance_corpus_definitions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('version', sa.String(30), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'READY_FOR_REVIEW', 'APPROVED', name='acceptancecorpusstatus'), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('sampling_rule', sa.Text(), nullable=False),
        sa.Column('minimum_cases', sa.Integer(), nullable=False),
        sa.Column('required_case_types_json', sa.JSON(), nullable=False),
        sa.Column('adjudication_required', sa.Boolean(), nullable=False),
        sa.Column('owner', sa.String(200), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='acceptance_corpus_definitions_pkey'),
    )
    op.create_table('acceptance_metrics',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('rehearsal_run_id', sa.String(36), nullable=False),
        sa.Column('metric', sa.String(120), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('sample_size', sa.Integer(), nullable=False),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.Column('approved_threshold', sa.Float(), nullable=True),
        sa.Column('threshold_status', sa.String(40), nullable=False),
        sa.Column('result', sa.String(40), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='acceptance_metrics_pkey'),
    )
    op.create_table('acceptance_rehearsal_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('fixture_set', sa.String(160), nullable=False),
        sa.Column('fixture_version', sa.String(40), nullable=False),
        sa.Column('fixture_manifest_hash', sa.String(64), nullable=False),
        sa.Column('configuration_bundle_versions', sa.JSON(), nullable=False),
        sa.Column('project_ids', sa.JSON(), nullable=False),
        sa.Column('application_ids', sa.JSON(), nullable=False),
        sa.Column('operator_identities', sa.JSON(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result', sa.String(50), nullable=False),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.Column('operator_assistance_required', sa.Boolean(), nullable=False),
        sa.Column('correlation_ids', sa.JSON(), nullable=False),
        sa.Column('audit_hash', sa.String(64), nullable=False),
        sa.Column('result_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='acceptance_rehearsal_runs_pkey'),
    )
    op.create_table('accounting_handoffs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('assigned_role', sa.String(80), nullable=False),
        sa.Column('assigned_user_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('workflow_task_id', sa.String(36), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='accounting_handoffs_pkey'),
    )
    op.create_table('adjudication_cases',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('dataset_id', sa.String(120), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'IN_REVIEW', 'DISPUTED', 'ADJUDICATED', name='adjudicationstatus'), nullable=False),
        sa.Column('steward_user_id', sa.String(36), nullable=False),
        sa.Column('responsible_engineer_user_id', sa.String(36), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('expected_class', sa.String(100), nullable=True),
        sa.Column('ambiguity', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='adjudication_cases_pkey'),
        sa.UniqueConstraint('document_version_id', name='adjudication_cases_document_version_id_key'),
    )
    op.create_table('adjudication_histories',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('case_id', sa.String(36), nullable=False),
        sa.Column('action', sa.String(80), nullable=False),
        sa.Column('actor_id', sa.String(200), nullable=False),
        sa.Column('before_json', sa.JSON(), nullable=True),
        sa.Column('after_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='adjudication_histories_pkey'),
    )
    op.create_table('admin_document_comments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('comment_number', sa.String(50), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('reviewed_artifact_id', sa.String(36), nullable=True),
        sa.Column('source_type', sa.String(60), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('owner_role', sa.String(100), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('resolution_evidence', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='admin_document_comments_pkey'),
    )
    op.create_table('applicable_rule_sets',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('scenario_version', sa.String(40), nullable=False),
        sa.Column('requirement_config_version', sa.String(40), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evaluated_by_system_version', sa.String(80), nullable=False),
        sa.Column('input_snapshot_hash', sa.String(64), nullable=False),
        sa.Column('result_hash', sa.String(64), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('configuration_bundle_id', sa.String(36), nullable=True),
        sa.Column('configuration_checksum', sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint('id', name='applicable_rule_sets_pkey'),
    )
    op.create_table('approval_applicability_evaluations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('approval_id', sa.String(36), nullable=False),
        sa.Column('prior_entity_id', sa.String(160), nullable=False),
        sa.Column('current_entity_id', sa.String(160), nullable=False),
        sa.Column('same_hash_or_scope', sa.Boolean(), nullable=False),
        sa.Column('material_change', sa.Boolean(), nullable=False),
        sa.Column('result', sa.String(60), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='approval_applicability_evaluations_pkey'),
    )
    op.create_table('approval_dependencies',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('dependency_type', sa.String(100), nullable=False),
        sa.Column('authority_or_owner', sa.String(200), nullable=False),
        sa.Column('reference_number', sa.String(100), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('evidence_document_id', sa.String(36), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='approval_dependencies_pkey'),
    )
    op.create_table('approvals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('approval_type', sa.String(80), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('decided_by', sa.String(200), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('role_at_decision', sa.String(100), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('evidence_refs', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='approvals_pkey'),
    )
    op.create_table('approved_design_baseline_members',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('baseline_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('revision_id', sa.String(36), nullable=False),
        sa.Column('rendition_id', sa.String(36), nullable=False),
        sa.Column('member_role', sa.String(80), nullable=False),
        sa.Column('pinned_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='approved_design_baseline_members_pkey'),
        sa.UniqueConstraint('baseline_id', 'revision_id', 'rendition_id', name='uq_approved_design_baseline_member'),
    )
    op.create_table('approved_design_baselines',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('baseline_ref', sa.String(120), nullable=False),
        sa.Column('purpose', sa.String(80), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('manifest_hash', sa.String(64), nullable=True),
        sa.Column('manifest_json', sa.JSON(), nullable=False),
        sa.Column('validation_json', sa.JSON(), nullable=False),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('approval_credential_reference', sa.String(240), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('supersedes_baseline_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='approved_design_baselines_pkey'),
        sa.UniqueConstraint('project_id', 'purpose', 'baseline_ref', name='uq_approved_design_baseline_ref'),
    )
    op.create_table('as_built_baseline_members',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('baseline_id', sa.String(36), nullable=False),
        sa.Column('engineering_revision_id', sa.String(36), nullable=True),
        sa.Column('rendition_id', sa.String(36), nullable=True),
        sa.Column('document_version_id', sa.String(36), nullable=True),
        sa.Column('building_snapshot_id', sa.String(36), nullable=True),
        sa.Column('member_role', sa.String(80), nullable=False),
        sa.Column('pinned_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='as_built_baseline_members_pkey'),
    )
    op.create_table('as_built_baselines',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=True),
        sa.Column('source_construction_design_snapshot_id', sa.String(36), nullable=True),
        sa.Column('baseline_ref', sa.String(120), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('scope_json', sa.JSON(), nullable=False),
        sa.Column('manifest_hash', sa.String(64), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('supersedes_baseline_id', sa.String(36), nullable=True),
        sa.Column('immutable_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='as_built_baselines_pkey'),
        sa.UniqueConstraint('project_id', 'construction_execution_id', 'baseline_ref', name='uq_as_built_baseline_ref'),
        sa.UniqueConstraint('project_id', 'construction_execution_id', 'version_number', name='uq_as_built_baseline_version'),
    )
    op.create_table('as_built_comparison_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('baseline_id', sa.String(36), nullable=False),
        sa.Column('construction_design_snapshot_id', sa.String(36), nullable=True),
        sa.Column('authority_approved_building_snapshot_ids', sa.JSON(), nullable=False),
        sa.Column('as_built_building_snapshot_ids', sa.JSON(), nullable=False),
        sa.Column('reference_fingerprint', sa.String(64), nullable=False),
        sa.Column('rule_version', sa.String(40), nullable=False),
        sa.Column('result', sa.String(30), nullable=False),
        sa.Column('difference_count', sa.Integer(), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='as_built_comparison_runs_pkey'),
        sa.UniqueConstraint('baseline_id', 'reference_fingerprint', 'rule_version', name='uq_as_built_comparison_run'),
    )
    op.create_table('as_built_variances',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('comparison_run_id', sa.String(36), nullable=False),
        sa.Column('building_asset_id', sa.String(36), nullable=True),
        sa.Column('engineering_revision_id', sa.String(36), nullable=True),
        sa.Column('field_key', sa.String(160), nullable=False),
        sa.Column('category', sa.String(80), nullable=False),
        sa.Column('approved_value_json', sa.JSON(), nullable=True),
        sa.Column('as_built_value_json', sa.JSON(), nullable=True),
        sa.Column('delta_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('professional_disposition', sa.String(60), nullable=True),
        sa.Column('requires_design_change', sa.Boolean(), nullable=False),
        sa.Column('requires_authority_modification', sa.Boolean(), nullable=False),
        sa.Column('design_change_request_id', sa.String(36), nullable=True),
        sa.Column('disposition_reason', sa.Text(), nullable=True),
        sa.Column('dispositioned_by', sa.String(200), nullable=True),
        sa.Column('dispositioned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='as_built_variances_pkey'),
    )
    op.create_table('assistant_capability_definitions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('assistant_id', sa.String(80), nullable=False),
        sa.Column('capability_id', sa.String(100), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('requirement_ids', sa.JSON(), nullable=False),
        sa.Column('input_types', sa.JSON(), nullable=False),
        sa.Column('output_types', sa.JSON(), nullable=False),
        sa.Column('required_human_authority', sa.String(120), nullable=False),
        sa.Column('external_action_policy', sa.String(100), nullable=False),
        sa.Column('stage2_disposition', sa.String(40), nullable=False),
        sa.Column('execution_authority', sa.String(50), nullable=False),
        sa.Column('enabled_in_prototype', sa.Boolean(), nullable=False),
        sa.Column('enabled_in_production', sa.Boolean(), nullable=False),
        sa.Column('allowed_source_classes', sa.JSON(), nullable=False),
        sa.Column('ai_mode', sa.String(40), nullable=False),
        sa.Column('capability_version', sa.String(40), nullable=False),
        sa.Column('capability_status', sa.String(40), nullable=False),
        sa.Column('enabled_in_dev', sa.Boolean(), nullable=False),
        sa.Column('enabled_in_test', sa.Boolean(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='assistant_capability_definitions_pkey'),
        sa.UniqueConstraint('capability_id', name='assistant_capability_definitions_capability_id_key'),
    )
    op.create_table('assistant_handoffs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('from_assistant_id', sa.String(80), nullable=False),
        sa.Column('to_assistant_id', sa.String(80), nullable=False),
        sa.Column('context_type', sa.String(80), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('opportunity_id', sa.String(36), nullable=True),
        sa.Column('source_revision_ids', sa.JSON(), nullable=False),
        sa.Column('workflow_task_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('accepted_by', sa.String(200), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='assistant_handoffs_pkey'),
    )
    op.create_table('attachment_association_intents',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('attachment_manifest_item_id', sa.String(36), nullable=True),
        sa.Column('category_code', sa.String(120), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('operation_type', sa.String(40), nullable=False),
        sa.Column('replaces_association_id', sa.String(36), nullable=True),
        sa.Column('idempotency_key', sa.String(300), nullable=False),
        sa.Column('intended_portal_filename', sa.String(300), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='attachment_association_intents_pkey'),
        sa.UniqueConstraint('idempotency_key', name='attachment_association_intents_idempotency_key_key'),
    )
    op.create_table('attachment_category_configs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('category_code', sa.String(100), nullable=False),
        sa.Column('label_en', sa.String(200), nullable=False),
        sa.Column('label_ar', sa.String(200), nullable=True),
        sa.Column('required_state', sa.String(50), nullable=False),
        sa.Column('applicability_json', sa.JSON(), nullable=False),
        sa.Column('allowed_document_types', sa.JSON(), nullable=False),
        sa.Column('multiple_files_allowed', sa.Boolean(), nullable=False),
        sa.Column('language_requirement', sa.String(50), nullable=True),
        sa.Column('max_size_mb', sa.Integer(), nullable=True),
        sa.Column('allowed_formats_json', sa.JSON(), nullable=False),
        sa.Column('portal_order', sa.Integer(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='attachment_category_configs_pkey'),
    )
    op.create_table('attachment_category_rules',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('scenario_version', sa.String(40), nullable=False),
        sa.Column('category_code', sa.String(120), nullable=False),
        sa.Column('portal_label_en', sa.String(240), nullable=False),
        sa.Column('portal_label_ar', sa.String(240), nullable=True),
        sa.Column('portal_order', sa.Integer(), nullable=False),
        sa.Column('requirement_state', sa.String(40), nullable=False),
        sa.Column('applicability_expression_json', sa.JSON(), nullable=False),
        sa.Column('allowed_document_types', sa.JSON(), nullable=False),
        sa.Column('min_files', sa.Integer(), nullable=False),
        sa.Column('max_files', sa.Integer(), nullable=True),
        sa.Column('multiple_files_allowed', sa.Boolean(), nullable=False),
        sa.Column('allowed_languages', sa.JSON(), nullable=False),
        sa.Column('required_language_combination', sa.String(30), nullable=True),
        sa.Column('allowed_mime_types', sa.JSON(), nullable=False),
        sa.Column('allowed_extensions', sa.JSON(), nullable=False),
        sa.Column('max_file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('revision_policy', sa.String(50), nullable=False),
        sa.Column('reuse_policy', sa.String(60), nullable=False),
        sa.Column('replacement_policy', sa.String(60), nullable=False),
        sa.Column('evidence_policy', sa.String(60), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rule_version', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='attachment_category_rules_pkey'),
    )
    op.create_table('attachment_manifest_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('attachment_manifest_id', sa.String(36), nullable=False),
        sa.Column('category_code', sa.String(120), nullable=False),
        sa.Column('category_rule_version', sa.String(40), nullable=False),
        sa.Column('requirement_state', sa.String(40), nullable=False),
        sa.Column('document_id', sa.String(36), nullable=True),
        sa.Column('document_version_id', sa.String(36), nullable=True),
        sa.Column('file_sha256', sa.String(64), nullable=True),
        sa.Column('logical_name', sa.String(240), nullable=True),
        sa.Column('revision_label', sa.String(80), nullable=True),
        sa.Column('language', sa.String(30), nullable=True),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('file_size_bytes', sa.Integer(), nullable=True),
        sa.Column('intended_portal_filename', sa.String(300), nullable=True),
        sa.Column('sequence_in_category', sa.Integer(), nullable=False),
        sa.Column('reuse_group_id', sa.String(80), nullable=True),
        sa.Column('source_reason', sa.Text(), nullable=False),
        sa.Column('validity_state', sa.String(50), nullable=False),
        sa.Column('approval_state', sa.String(40), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='attachment_manifest_items_pkey'),
    )
    op.create_table('attachment_manifests',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('package_id', sa.String(36), nullable=False),
        sa.Column('scenario_version', sa.String(40), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('items', sa.JSON(), nullable=False),
        sa.Column('manifest_hash', sa.String(64), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('scenario_id', sa.String(36), nullable=True),
        sa.Column('manifest_version', sa.String(40), nullable=False),
        sa.Column('generated_by', sa.String(200), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='attachment_manifests_pkey'),
        sa.UniqueConstraint('package_id', name='attachment_manifests_package_id_key'),
    )
    op.create_table('attachment_persistence_evidence',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('category_code', sa.String(120), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('expected_filename', sa.String(300), nullable=False),
        sa.Column('expected_size', sa.Integer(), nullable=True),
        sa.Column('observed_filename', sa.String(300), nullable=True),
        sa.Column('observed_size', sa.Integer(), nullable=True),
        sa.Column('observed_category_code', sa.String(120), nullable=True),
        sa.Column('capture_method', sa.String(40), nullable=False),
        sa.Column('pre_save_state_hash', sa.String(64), nullable=True),
        sa.Column('post_save_state_hash', sa.String(64), nullable=True),
        sa.Column('reopened_state_hash', sa.String(64), nullable=True),
        sa.Column('result', sa.String(50), nullable=False),
        sa.Column('evidence_artifact_id', sa.String(300), nullable=True),
        sa.Column('verified_by', sa.String(200), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='attachment_persistence_evidence_pkey'),
    )
    op.create_table('attachment_reconciliation_results',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('manifest_item_id', sa.String(36), nullable=True),
        sa.Column('category_code', sa.String(120), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=True),
        sa.Column('expected', sa.JSON(), nullable=False),
        sa.Column('observed', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('evidence_id', sa.String(300), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='attachment_reconciliation_results_pkey'),
    )
    op.create_table('attended_auth_sessions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=True),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('user_role', sa.String(80), nullable=False),
        sa.Column('environment', sa.String(40), nullable=False),
        sa.Column('adapter_id', sa.String(100), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('auth_mode', sa.String(60), nullable=False),
        sa.Column('mfa_mode', sa.String(60), nullable=False),
        sa.Column('mfa_required', sa.Boolean(), nullable=False),
        sa.Column('challenge_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('challenge_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_by_user_id', sa.String(36), nullable=True),
        sa.Column('session_reference_hash', sa.String(64), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id', name='attended_auth_sessions_pkey'),
    )
    op.create_table('attended_sessions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('mfa_mode', sa.String(50), nullable=False),
        sa.Column('session_started', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attendance_required', sa.Boolean(), nullable=False),
        sa.Column('human_attendance_confirmed', sa.Boolean(), nullable=False),
        sa.Column('session_established', sa.Boolean(), nullable=False),
        sa.Column('session_expired', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='attended_sessions_pkey'),
    )
    op.create_table('audit_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.Column('actor_type', sa.String(50), nullable=False),
        sa.Column('actor_id', sa.String(36), nullable=True),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('entity_id', sa.String(100), nullable=False),
        sa.Column('before_json', sa.JSON(), nullable=True),
        sa.Column('after_json', sa.JSON(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='audit_events_pkey'),
    )
    op.create_table('authority_approval_validities',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('approval_dependency_id', sa.String(36), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_document_version_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='authority_approval_validities_pkey'),
        sa.UniqueConstraint('approval_dependency_id', name='authority_approval_validities_approval_dependency_id_key'),
    )
    op.create_table('authority_approved_design_snapshots',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=True),
        sa.Column('authority_outcome_id', sa.String(36), nullable=True),
        sa.Column('submission_cycle_id', sa.String(36), nullable=True),
        sa.Column('external_submission_snapshot_id', sa.String(36), nullable=True),
        sa.Column('submission_package_id', sa.String(36), nullable=True),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('approved_design_baseline_id', sa.String(36), nullable=False),
        sa.Column('authority_decision_reference', sa.String(240), nullable=True),
        sa.Column('external_approval_reference', sa.String(240), nullable=True),
        sa.Column('authority_state', sa.String(40), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_until', sa.Date(), nullable=True),
        sa.Column('source_document_version_ids', sa.JSON(), nullable=False),
        sa.Column('baseline_member_snapshot', sa.JSON(), nullable=False),
        sa.Column('source_lineage_json', sa.JSON(), nullable=False),
        sa.Column('snapshot_hash', sa.String(64), nullable=False),
        sa.Column('captured_by', sa.String(200), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_approved_design_snapshots_pkey'),
    )
    op.create_table('authority_case_create_requests',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('requested_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_case_create_requests_pkey'),
        sa.UniqueConstraint('authority_case_id', name='authority_case_create_requests_authority_case_id_key'),
        sa.UniqueConstraint('idempotency_key', name='uq_authority_case_create_idempotency'),
    )
    op.create_table('authority_case_findings',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('submission_cycle_id', sa.String(36), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('external_finding_id', sa.String(160), nullable=True),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('captured_by', sa.String(200), nullable=False),
        sa.Column('engineering_impact', sa.String(30), nullable=False),
        sa.Column('affected_requirement_instance_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_case_findings_pkey'),
    )
    op.create_table('authority_case_identifiers',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('identifier_type', sa.String(60), nullable=False),
        sa.Column('value', sa.String(240), nullable=False),
        sa.Column('issued_by', sa.String(200), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_case_identifiers_pkey'),
        sa.UniqueConstraint('authority_case_id', 'identifier_type', 'value', name='uq_authority_case_identifier'),
    )
    op.create_table('authority_case_outcomes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('submission_cycle_id', sa.String(36), nullable=True),
        sa.Column('outcome_type', sa.String(40), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('external_identifier', sa.String(240), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('evidence_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by', sa.String(200), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_case_outcomes_pkey'),
    )
    op.create_table('authority_case_policy_bindings',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('policy_version_id', sa.String(36), nullable=False),
        sa.Column('resolution_state', sa.String(30), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_by', sa.String(200), nullable=False),
        sa.Column('resolution_facts', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_case_policy_bindings_pkey'),
        sa.UniqueConstraint('authority_case_id', name='uq_authority_case_policy_binding_case'),
    )
    op.create_table('authority_case_subjects',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('subject_type', sa.String(50), nullable=False),
        sa.Column('subject_id', sa.String(36), nullable=False),
        sa.Column('subject_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_case_subjects_pkey'),
        sa.UniqueConstraint('authority_case_id', name='uq_authority_case_subject_case'),
    )
    op.create_table('authority_case_work_periods',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('period_type', sa.String(50), nullable=False),
        sa.Column('starts_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_case_work_periods_pkey'),
    )
    op.create_table('authority_cases',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('case_reference', sa.String(100), nullable=False),
        sa.Column('regulatory_journey_id', sa.String(36), nullable=True),
        sa.Column('external_body_id', sa.String(36), nullable=False),
        sa.Column('service_type_id', sa.String(36), nullable=False),
        sa.Column('jurisdiction_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('subject_type', sa.String(50), nullable=True),
        sa.Column('subject_id', sa.String(36), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_cases_pkey'),
        sa.UniqueConstraint('case_reference', name='uq_authority_case_reference'),
    )
    op.create_table('authority_comment_observations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('submission_cycle_id', sa.String(36), nullable=True),
        sa.Column('monitoring_run_id', sa.String(36), nullable=False),
        sa.Column('external_comment_id', sa.String(160), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('language', sa.String(30), nullable=False),
        sa.Column('authority_reference', sa.String(160), nullable=True),
        sa.Column('section_object_reference', sa.String(200), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_artifact_id', sa.String(300), nullable=True),
        sa.Column('source_hash', sa.String(64), nullable=False),
        sa.Column('normalized_key', sa.String(240), nullable=True),
        sa.PrimaryKeyConstraint('id', name='authority_comment_observations_pkey'),
    )
    op.create_table('authority_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('source_channel', sa.String(60), nullable=False),
        sa.Column('source_type', sa.String(60), nullable=False),
        sa.Column('external_reference', sa.String(300), nullable=True),
        sa.Column('external_event_id', sa.String(160), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('raw_evidence_artifact_id', sa.String(300), nullable=True),
        sa.Column('payload_hash', sa.String(64), nullable=False),
        sa.Column('normalized_key', sa.String(200), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('linked_authority_event_id', sa.String(36), nullable=True),
        sa.Column('raw_payload', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_events_pkey'),
    )
    op.create_table('authority_finding_responses',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('finding_id', sa.String(36), nullable=False),
        sa.Column('response_text', sa.Text(), nullable=False),
        sa.Column('supporting_evidence_json', sa.JSON(), nullable=False),
        sa.Column('affected_requirement_instance_id', sa.String(36), nullable=True),
        sa.Column('affected_baseline_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('prepared_by', sa.String(200), nullable=False),
        sa.Column('reviewed_by', sa.String(200), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_finding_responses_pkey'),
    )
    op.create_table('authority_outcomes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('outcome_type', sa.String(60), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('decision_payload', sa.JSON(), nullable=False),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_outcomes_pkey'),
    )
    op.create_table('authority_precheck_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('precheck_run_id', sa.String(36), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('code', sa.String(100), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_precheck_items_pkey'),
    )
    op.create_table('authority_precheck_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('run_reference', sa.String(150), nullable=False),
        sa.Column('run_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('raw_evidence_artifact_id', sa.String(300), nullable=True),
        sa.Column('result_hash', sa.String(64), nullable=False),
        sa.Column('configuration_bundle_id', sa.String(36), nullable=True),
        sa.Column('clearance_result', sa.String(60), nullable=True),
        sa.Column('invalidated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invalidated_reason', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='authority_precheck_runs_pkey'),
    )
    op.create_table('authority_state_comparisons',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('monitoring_run_id', sa.String(36), nullable=False),
        sa.Column('prior_snapshot_id', sa.String(36), nullable=True),
        sa.Column('current_snapshot_id', sa.String(36), nullable=True),
        sa.Column('status_changed', sa.Boolean(), nullable=False),
        sa.Column('prior_status', sa.String(80), nullable=True),
        sa.Column('current_status', sa.String(80), nullable=True),
        sa.Column('repetition_changed', sa.Boolean(), nullable=False),
        sa.Column('prior_repetition', sa.Integer(), nullable=True),
        sa.Column('current_repetition', sa.Integer(), nullable=True),
        sa.Column('new_comment_ids', sa.JSON(), nullable=False),
        sa.Column('removed_comment_ids', sa.JSON(), nullable=False),
        sa.Column('changed_comment_ids', sa.JSON(), nullable=False),
        sa.Column('materiality', sa.String(40), nullable=False),
        sa.Column('result', sa.String(40), nullable=False),
        sa.Column('reasons', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_state_comparisons_pkey'),
    )
    op.create_table('authority_status_observations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('submission_cycle_id', sa.String(36), nullable=True),
        sa.Column('monitoring_run_id', sa.String(36), nullable=False),
        sa.Column('raw_status', sa.String(80), nullable=False),
        sa.Column('normalized_status', sa.String(80), nullable=False),
        sa.Column('authority_reference', sa.String(160), nullable=True),
        sa.Column('repetition_number', sa.Integer(), nullable=True),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_artifact_id', sa.String(300), nullable=True),
        sa.Column('source_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_status_observations_pkey'),
    )
    op.create_table('authority_submission_cycles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('cycle_number', sa.Integer(), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('submission_package_id', sa.String(36), nullable=False),
        sa.Column('external_submission_snapshot_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authority_submission_cycles_pkey'),
        sa.UniqueConstraint('authority_case_id', 'cycle_number', name='uq_authority_submission_cycle_number'),
    )
    op.create_table('authorization_grants',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('grantor_party_id', sa.String(36), nullable=False),
        sa.Column('grantee_party_id', sa.String(36), nullable=False),
        sa.Column('authorization_type', sa.String(80), nullable=False),
        sa.Column('scope', sa.Text(), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('evidence_document_version_id', sa.String(36), nullable=True),
        sa.Column('verified_by', sa.String(200), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='authorization_grants_pkey'),
    )
    op.create_table('authorizations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('principal_party_id', sa.String(36), nullable=False),
        sa.Column('representative_party_id', sa.String(36), nullable=False),
        sa.Column('authorization_type', sa.String(100), nullable=False),
        sa.Column('scope', sa.Text(), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('evidence_document_version_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='authorizations_pkey'),
    )
    op.create_table('automation_readiness_assessments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('profile_id', sa.String(36), nullable=False),
        sa.Column('master_content_item_id', sa.String(36), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=False),
        sa.Column('mapping_release_id', sa.String(36), nullable=True),
        sa.Column('state', sa.String(40), nullable=False),
        sa.Column('blocking_reasons', sa.JSON(), nullable=False),
        sa.Column('evidence_json', sa.JSON(), nullable=False),
        sa.Column('evaluated_by', sa.String(200), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('provenance_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='automation_readiness_assessments_pkey'),
    )
    op.create_table('billing_milestone_eligibilities',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('billing_milestone_id', sa.String(36), nullable=False),
        sa.Column('state', sa.String(40), nullable=False),
        sa.Column('evaluated_by', sa.String(200), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('trigger_evidence', sa.JSON(), nullable=False),
        sa.Column('policy_version', sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint('id', name='billing_milestone_eligibilities_pkey'),
    )
    op.create_table('billing_milestones',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('billing_plan_revision_id', sa.String(36), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('source_contract_payment_term_id', sa.String(36), nullable=True),
        sa.Column('basis_type', sa.String(50), nullable=False),
        sa.Column('basis_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('percentage', sa.Numeric(12, 6), nullable=True),
        sa.Column('calculated_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('currency', sa.String(20), nullable=False),
        sa.Column('trigger_type', sa.String(80), nullable=False),
        sa.Column('trigger_description', sa.Text(), nullable=True),
        sa.Column('due_days', sa.Integer(), nullable=True),
        sa.Column('eligibility_state', sa.String(40), nullable=False),
        sa.Column('invoiced_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('remaining_invoiceable_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('source_snapshot', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='billing_milestones_pkey'),
        sa.UniqueConstraint('billing_plan_revision_id', 'sequence', name='uq_billing_milestone_sequence'),
    )
    op.create_table('billing_plan_revisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('billing_plan_id', sa.String(36), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('client_account_id', sa.String(36), nullable=False),
        sa.Column('contract_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('currency', sa.String(20), nullable=False),
        sa.Column('valuation_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('valuation_currency', sa.String(20), nullable=True),
        sa.Column('valuation_status', sa.String(50), nullable=False),
        sa.Column('contract_project_context_snapshot', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('supersedes_revision_id', sa.String(36), nullable=True),
        sa.Column('source_snapshot', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='billing_plan_revisions_pkey'),
        sa.UniqueConstraint('billing_plan_id', 'revision_number', name='uq_billing_plan_revision_number'),
    )
    op.create_table('billing_plans',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('client_account_id', sa.String(36), nullable=False),
        sa.Column('currency', sa.String(20), nullable=False),
        sa.Column('automation_mode', sa.String(40), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('current_revision_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('activated_by', sa.String(200), nullable=True),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='billing_plans_pkey'),
        sa.UniqueConstraint('contract_id', 'contract_revision_id', name='uq_billing_plan_contract_revision'),
    )
    op.create_table('building_assets',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('property_id', sa.String(36), nullable=True),
        sa.Column('asset_ref', sa.String(120), nullable=False),
        sa.Column('name', sa.String(240), nullable=False),
        sa.Column('building_type', sa.String(100), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='building_assets_pkey'),
        sa.UniqueConstraint('project_id', 'asset_ref', name='uq_building_asset_ref'),
    )
    op.create_table('building_snapshots',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('building_asset_id', sa.String(36), nullable=False),
        sa.Column('snapshot_type', sa.String(30), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('snapshot_ref', sa.String(120), nullable=False),
        sa.Column('values_json', sa.JSON(), nullable=False),
        sa.Column('verified_assertion_ids', sa.JSON(), nullable=False),
        sa.Column('source_document_version_ids', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('snapshot_hash', sa.String(64), nullable=False),
        sa.Column('supersedes_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='building_snapshots_pkey'),
        sa.UniqueConstraint('building_asset_id', 'snapshot_type', 'version_number', name='uq_building_snapshot_version'),
    )
    op.create_table('business_baselines',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('applications_per_month', sa.Float(), nullable=False),
        sa.Column('applications_per_year', sa.Float(), nullable=False),
        sa.Column('manual_entry_minutes', sa.Float(), nullable=False),
        sa.Column('upload_minutes', sa.Float(), nullable=False),
        sa.Column('status_check_minutes', sa.Float(), nullable=False),
        sa.Column('return_rate', sa.Float(), nullable=False),
        sa.Column('average_submission_cycles', sa.Float(), nullable=False),
        sa.Column('rework_hours_per_return', sa.Float(), nullable=False),
        sa.Column('delay_days_per_return', sa.Float(), nullable=False),
        sa.Column('loaded_hourly_rate_qar', sa.Float(), nullable=False),
        sa.Column('optional_delay_value_per_day', sa.Float(), nullable=True),
        sa.Column('standing_classification_impact_status', sa.String(50), nullable=False),
        sa.Column('source', sa.String(200), nullable=False),
        sa.Column('measurement_period', sa.String(100), nullable=False),
        sa.Column('confidence', sa.String(30), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='business_baselines_pkey'),
    )
    op.create_table('business_case',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('values_json', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='business_case_pkey'),
    )
    op.create_table('business_kpi_targets',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('baseline', sa.Float(), nullable=True),
        sa.Column('target', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(50), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('owner', sa.String(200), nullable=False),
        sa.Column('measurement_method', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='business_kpi_targets_pkey'),
    )
    op.create_table('capability_invocation_records',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('assistant_id', sa.String(80), nullable=False),
        sa.Column('capability_id', sa.String(100), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('caller', sa.String(200), nullable=False),
        sa.Column('caller_role', sa.String(100), nullable=False),
        sa.Column('policy_decision', sa.String(60), nullable=False),
        sa.Column('result_type', sa.String(60), nullable=False),
        sa.Column('output_envelope', sa.JSON(), nullable=False),
        sa.Column('source_revision_ids', sa.JSON(), nullable=False),
        sa.Column('evidence_refs', sa.JSON(), nullable=False),
        sa.Column('human_review_required', sa.Boolean(), nullable=False),
        sa.Column('deterministic_gate_result', sa.String(60), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='capability_invocation_records_pkey'),
    )
    op.create_table('case_evidence_selections',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('requirement_instance_id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=True),
        sa.Column('form_instance_id', sa.String(36), nullable=True),
        sa.Column('approved_design_baseline_id', sa.String(36), nullable=True),
        sa.Column('evidence_kind', sa.String(50), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('details_json', sa.JSON(), nullable=False),
        sa.Column('selected_by', sa.String(200), nullable=False),
        sa.Column('selected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='case_evidence_selections_pkey'),
    )
    op.create_table('case_party_snapshots',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('snapshot_number', sa.Integer(), nullable=False),
        sa.Column('snapshot_json', sa.JSON(), nullable=False),
        sa.Column('snapshot_hash', sa.String(64), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('captured_by', sa.String(200), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='case_party_snapshots_pkey'),
    )
    op.create_table('checklist_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('context_type', sa.String(80), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('requirement_code', sa.String(100), nullable=False),
        sa.Column('title', sa.String(250), nullable=False),
        sa.Column('required_condition', sa.Text(), nullable=False),
        sa.Column('required_document_type', sa.String(100), nullable=True),
        sa.Column('validity_policy_ref', sa.String(100), nullable=True),
        sa.Column('current_document_version_id', sa.String(36), nullable=True),
        sa.Column('applicability', sa.String(50), nullable=False),
        sa.Column('validity_status', sa.String(50), nullable=False),
        sa.Column('owner_role', sa.String(100), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='checklist_items_pkey'),
    )
    op.create_table('client_accounts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('client_reference', sa.String(100), nullable=False),
        sa.Column('legal_name', sa.String(250), nullable=False),
        sa.Column('display_name', sa.String(250), nullable=False),
        sa.Column('client_type', sa.String(50), nullable=False),
        sa.Column('canonical_party_id', sa.String(36), nullable=True),
        sa.Column('commercial_registration_number', sa.String(100), nullable=True),
        sa.Column('data_classification', sa.String(40), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='client_accounts_pkey'),
        sa.UniqueConstraint('client_reference', name='client_accounts_client_reference_key'),
    )
    op.create_table('client_contacts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('client_account_id', sa.String(36), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('phone', sa.String(80), nullable=True),
        sa.Column('role_title', sa.String(120), nullable=True),
        sa.Column('language_preference', sa.String(10), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='client_contacts_pkey'),
    )
    op.create_table('client_responses',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('opportunity_id', sa.String(36), nullable=False),
        sa.Column('quotation_revision_id', sa.String(36), nullable=False),
        sa.Column('response_type', sa.String(50), nullable=False),
        sa.Column('evidence_artifact_id', sa.String(36), nullable=True),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='client_responses_pkey'),
    )
    op.create_table('commercial_terms',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('quotation_revision_id', sa.String(36), nullable=False),
        sa.Column('term_type', sa.String(40), nullable=False),
        sa.Column('value_text', sa.Text(), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('evidence_artifact_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='commercial_terms_pkey'),
    )
    op.create_table('communication_approvals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('communication_draft_id', sa.String(36), nullable=False),
        sa.Column('approval_id', sa.String(36), nullable=False),
        sa.Column('approval_type', sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint('id', name='communication_approvals_pkey'),
        sa.UniqueConstraint('approval_id', name='communication_approvals_approval_id_key'),
    )
    op.create_table('communication_deliveries',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('communication_draft_id', sa.String(36), nullable=False),
        sa.Column('delivery_channel', sa.String(50), nullable=False),
        sa.Column('delivery_status', sa.String(50), nullable=False),
        sa.Column('external_message_id', sa.String(200), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence_artifact_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='communication_deliveries_pkey'),
    )
    op.create_table('communication_drafts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('communication_type', sa.String(80), nullable=False),
        sa.Column('context_type', sa.String(80), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('recipient_contact_id', sa.String(36), nullable=True),
        sa.Column('template_version_id', sa.String(36), nullable=True),
        sa.Column('subject', sa.String(250), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('policy_state', sa.String(50), nullable=False),
        sa.Column('reviewed_by', sa.String(200), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_snapshot', sa.JSON(), nullable=False),
        sa.Column('source_revision_ids', sa.JSON(), nullable=False),
        sa.Column('body_hash', sa.String(64), nullable=True),
        sa.Column('stale_reason', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='communication_drafts_pkey'),
    )
    op.create_table('completion_case_links',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('construction_completion_context_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('subject_type', sa.String(50), nullable=False),
        sa.Column('subject_id', sa.String(36), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('started_by', sa.String(200), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='completion_case_links_pkey'),
        sa.UniqueConstraint('authority_case_id', name='uq_completion_case_link_case'),
        sa.UniqueConstraint('idempotency_key', name='uq_completion_case_link_idempotency'),
    )
    op.create_table('configuration_artifacts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('stable_id', sa.String(160), nullable=False),
        sa.Column('artifact_type', sa.String(100), nullable=False),
        sa.Column('version', sa.String(80), nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('source_basis', sa.String(300), nullable=False),
        sa.Column('semantic_payload_json', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='configuration_artifacts_pkey'),
        sa.UniqueConstraint('stable_id', name='configuration_artifacts_stable_id_key'),
    )
    op.create_table('configuration_bundles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('bundle_id', sa.String(160), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=True),
        sa.Column('bundle_version', sa.String(80), nullable=False),
        sa.Column('artifact_ids_json', sa.JSON(), nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('source_basis', sa.String(300), nullable=False),
        sa.PrimaryKeyConstraint('id', name='configuration_bundles_pkey'),
        sa.UniqueConstraint('bundle_id', name='configuration_bundles_bundle_id_key'),
    )
    op.create_table('configuration_change_impact_policies',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('config_type', sa.String(80), nullable=False),
        sa.Column('change_severity', sa.String(30), nullable=False),
        sa.Column('active_revision_policy', sa.String(60), nullable=False),
        sa.Column('requires_re_evaluation', sa.Boolean(), nullable=False),
        sa.Column('requires_new_revision', sa.Boolean(), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='configuration_change_impact_policies_pkey'),
    )
    op.create_table('conflicts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('field_definition_id', sa.String(36), nullable=False),
        sa.Column('observation_ids_json', sa.JSON(), nullable=False),
        sa.Column('severity', sa.Enum('CRITICAL', 'MAJOR', 'MINOR', 'ADVISORY', name='conflictseverity'), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'RESOLVED', 'ACCEPTED', 'BLOCKED', name='conflictstatus'), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('resolver', sa.String(200), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='conflicts_pkey'),
    )
    op.create_table('construction_authority_notifications',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=True),
        sa.Column('obligation_instance_id', sa.String(36), nullable=True),
        sa.Column('work_control_event_id', sa.String(36), nullable=True),
        sa.Column('notification_type', sa.String(80), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('channel_code', sa.String(60), nullable=False),
        sa.Column('recipient_snapshot', sa.JSON(), nullable=False),
        sa.Column('payload_snapshot', sa.JSON(), nullable=False),
        sa.Column('external_reference', sa.String(240), nullable=True),
        sa.Column('evidence_document_version_id', sa.String(36), nullable=True),
        sa.Column('prepared_by', sa.String(200), nullable=False),
        sa.Column('prepared_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sent_by', sa.String(200), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='construction_authority_notifications_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_construction_authority_notification_idempotency'),
    )
    op.create_table('construction_completion_contexts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('authority_approved_design_snapshot_id', sa.String(36), nullable=True),
        sa.Column('construction_design_snapshot_id', sa.String(36), nullable=True),
        sa.Column('work_state', sa.String(40), nullable=False),
        sa.Column('open_issue_ids', sa.JSON(), nullable=False),
        sa.Column('open_obligation_ids', sa.JSON(), nullable=False),
        sa.Column('inspection_ids', sa.JSON(), nullable=False),
        sa.Column('material_test_ids', sa.JSON(), nullable=False),
        sa.Column('physical_evidence_ids', sa.JSON(), nullable=False),
        sa.Column('party_snapshot', sa.JSON(), nullable=False),
        sa.Column('source_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('context_hash', sa.String(64), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='construction_completion_contexts_pkey'),
        sa.UniqueConstraint('construction_execution_id', name='uq_completion_context_execution'),
    )
    op.create_table('construction_correspondence',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=True),
        sa.Column('direction', sa.String(20), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('sender_party_id', sa.String(36), nullable=True),
        sa.Column('recipient_party_id', sa.String(36), nullable=True),
        sa.Column('subject', sa.String(300), nullable=False),
        sa.Column('reference', sa.String(160), nullable=True),
        sa.Column('document_version_id', sa.String(36), nullable=True),
        sa.Column('external_reference', sa.String(240), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='construction_correspondence_pkey'),
    )
    op.create_table('construction_design_snapshots',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('authority_approved_design_snapshot_id', sa.String(36), nullable=False),
        sa.Column('approved_design_baseline_id', sa.String(36), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('snapshot_ref', sa.String(120), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('member_revision_ids', sa.JSON(), nullable=False),
        sa.Column('member_rendition_ids', sa.JSON(), nullable=False),
        sa.Column('document_version_ids', sa.JSON(), nullable=False),
        sa.Column('snapshot_hash', sa.String(64), nullable=False),
        sa.Column('supersedes_id', sa.String(36), nullable=True),
        sa.Column('promoted_by', sa.String(200), nullable=False),
        sa.Column('promoted_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='construction_design_snapshots_pkey'),
        sa.UniqueConstraint('construction_execution_id', 'version_number', name='uq_construction_design_snapshot_version'),
    )
    op.create_table('construction_evidence_links',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('evidence_type', sa.String(60), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=True),
        sa.Column('physical_evidence_item_id', sa.String(36), nullable=True),
        sa.Column('material_test_id', sa.String(36), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('captured_by', sa.String(200), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='construction_evidence_links_pkey'),
    )
    op.create_table('construction_executions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=True),
        sa.Column('contract_revision_id', sa.String(36), nullable=True),
        sa.Column('authority_case_id', sa.String(36), nullable=True),
        sa.Column('execution_ref', sa.String(120), nullable=False),
        sa.Column('title', sa.String(240), nullable=False),
        sa.Column('scope_description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('work_state', sa.String(40), nullable=False),
        sa.Column('current_authority_snapshot_id', sa.String(36), nullable=True),
        sa.Column('current_design_snapshot_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='construction_executions_pkey'),
        sa.UniqueConstraint('project_id', 'execution_ref', name='uq_construction_execution_ref'),
    )
    op.create_table('construction_inspections',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=True),
        sa.Column('inspection_kind', sa.String(30), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('requested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('inspector_party_id', sa.String(36), nullable=True),
        sa.Column('authority_reference', sa.String(240), nullable=True),
        sa.Column('outcome', sa.String(40), nullable=True),
        sa.Column('findings_json', sa.JSON(), nullable=False),
        sa.Column('evidence_document_version_ids', sa.JSON(), nullable=False),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='construction_inspections_pkey'),
    )
    op.create_table('construction_issues',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('issue_ref', sa.String(120), nullable=False),
        sa.Column('category', sa.String(80), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('affected_scope', sa.String(240), nullable=True),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('observed_by', sa.String(200), nullable=False),
        sa.Column('authority_case_finding_id', sa.String(36), nullable=True),
        sa.Column('design_change_request_id', sa.String(36), nullable=True),
        sa.Column('requirement_instance_id', sa.String(36), nullable=True),
        sa.Column('evidence_document_version_ids', sa.JSON(), nullable=False),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.Column('resolved_by', sa.String(200), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='construction_issues_pkey'),
    )
    op.create_table('construction_obligation_definitions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=True),
        sa.Column('requirement_definition_id', sa.String(36), nullable=True),
        sa.Column('policy_version_id', sa.String(36), nullable=True),
        sa.Column('code', sa.String(120), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('title', sa.String(240), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('trigger_type', sa.String(60), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('required_role_codes', sa.JSON(), nullable=False),
        sa.Column('due_rule_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='construction_obligation_definitions_pkey'),
        sa.UniqueConstraint('project_id', 'code', 'version', name='uq_construction_obligation_definition'),
    )
    op.create_table('construction_obligation_instances',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('definition_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('trigger_event_type', sa.String(60), nullable=True),
        sa.Column('trigger_event_id', sa.String(36), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completion_evidence_document_version_ids', sa.JSON(), nullable=False),
        sa.Column('instance_snapshot', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='construction_obligation_instances_pkey'),
    )
    op.create_table('construction_obligation_participants',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('obligation_instance_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('party_id', sa.String(36), nullable=False),
        sa.Column('role_code', sa.String(80), nullable=False),
        sa.Column('responsibility', sa.Text(), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('assigned_by', sa.String(200), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='construction_obligation_participants_pkey'),
        sa.UniqueConstraint('obligation_instance_id', 'party_id', 'role_code', name='uq_construction_obligation_participant'),
    )
    op.create_table('construction_party_assignments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('party_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=True),
        sa.Column('party_role_assignment_id', sa.String(36), nullable=True),
        sa.Column('professional_credential_id', sa.String(36), nullable=True),
        sa.Column('role_code', sa.String(80), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('credential_snapshot', sa.JSON(), nullable=False),
        sa.Column('assigned_by', sa.String(200), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='construction_party_assignments_pkey'),
    )
    op.create_table('construction_start_authorizations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('project_activation_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('authority_approved_design_snapshot_id', sa.String(36), nullable=False),
        sa.Column('construction_design_snapshot_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('intended_start_date', sa.Date(), nullable=True),
        sa.Column('readiness_snapshot', sa.JSON(), nullable=False),
        sa.Column('party_snapshot', sa.JSON(), nullable=False),
        sa.Column('authorization_snapshot', sa.JSON(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.Column('authorized_by', sa.String(200), nullable=False),
        sa.Column('authorized_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='construction_start_authorizations_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_construction_start_authorization_idempotency'),
    )
    op.create_table('construction_start_readiness',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('result', sa.String(40), nullable=False),
        sa.Column('blockers_json', sa.JSON(), nullable=False),
        sa.Column('checks_json', sa.JSON(), nullable=False),
        sa.Column('evaluation_fingerprint', sa.String(64), nullable=False),
        sa.Column('evaluated_by', sa.String(200), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='construction_start_readiness_pkey'),
    )
    op.create_table('construction_work_control_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('construction_execution_id', sa.String(36), nullable=False),
        sa.Column('start_authorization_id', sa.String(36), nullable=True),
        sa.Column('event_type', sa.String(30), nullable=False),
        sa.Column('prior_state', sa.String(40), nullable=False),
        sa.Column('new_state', sa.String(40), nullable=False),
        sa.Column('event_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_type', sa.String(80), nullable=False),
        sa.Column('source_id', sa.String(160), nullable=True),
        sa.Column('evidence_document_version_id', sa.String(36), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='construction_work_control_events_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_construction_work_control_event_idempotency'),
    )
    op.create_table('consultancy_offices',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('office_code', sa.String(50), nullable=False),
        sa.Column('name_en', sa.String(200), nullable=False),
        sa.Column('name_ar', sa.String(200), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='consultancy_offices_pkey'),
        sa.UniqueConstraint('office_code', name='consultancy_offices_office_code_key'),
    )
    op.create_table('contact_points',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('party_id', sa.String(36), nullable=True),
        sa.Column('purpose', sa.String(60), nullable=False),
        sa.Column('channel', sa.String(30), nullable=False),
        sa.Column('value', sa.String(300), nullable=False),
        sa.Column('verified', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_until', sa.Date(), nullable=True),
        sa.Column('maintained_by', sa.String(200), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='contact_points_pkey'),
    )
    op.create_table('content_categories',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(80), nullable=False),
        sa.Column('label', sa.String(160), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('allowed_content_types', sa.JSON(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('source_kind', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='content_categories_pkey'),
        sa.UniqueConstraint('code', name='uq_content_category_code'),
    )
    op.create_table('contract_admin_evidence',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=True),
        sa.Column('evidence_type', sa.String(100), nullable=False),
        sa.Column('source_role', sa.String(80), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=True),
        sa.Column('source_reference', sa.String(600), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='contract_admin_evidence_pkey'),
    )
    op.create_table('contract_admin_inputs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('input_key', sa.String(120), nullable=False),
        sa.Column('value_json', sa.JSON(), nullable=False),
        sa.Column('entered_by', sa.String(200), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='contract_admin_inputs_pkey'),
        sa.UniqueConstraint('contract_id', 'input_key', name='uq_contract_admin_input_key'),
    )
    op.create_table('contract_administrative_closures',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('service_closure_ids_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('closed_by', sa.String(200), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_json', sa.JSON(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='contract_administrative_closures_pkey'),
        sa.UniqueConstraint('contract_id', name='uq_contract_admin_closure_contract'),
    )
    op.create_table('contract_approvals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('approval_id', sa.String(36), nullable=False),
        sa.Column('approval_type', sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint('id', name='contract_approvals_pkey'),
        sa.UniqueConstraint('approval_id', name='contract_approvals_approval_id_key'),
    )
    op.create_table('contract_client_input_requirements',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('input_code', sa.String(100), nullable=True),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('required', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('source_type', sa.String(80), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('human_verified_by', sa.String(200), nullable=True),
        sa.Column('human_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='contract_client_input_requirements_pkey'),
        sa.UniqueConstraint('contract_revision_id', 'sequence', name='uq_contract_client_input_revision_sequence'),
    )
    op.create_table('contract_deliverable_commitments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('commitment_ref', sa.String(100), nullable=True),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('due_trigger_description', sa.Text(), nullable=True),
        sa.Column('source_scope_item_id', sa.String(36), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('human_verified_by', sa.String(200), nullable=True),
        sa.Column('human_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='contract_deliverable_commitments_pkey'),
        sa.UniqueConstraint('contract_revision_id', 'sequence', name='uq_contract_deliverable_revision_sequence'),
    )
    op.create_table('contract_execution_evidence',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('evidence_artifact_id', sa.String(36), nullable=False),
        sa.Column('execution_status', sa.String(50), nullable=False),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='contract_execution_evidence_pkey'),
    )
    op.create_table('contract_milestones',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('milestone_reference', sa.String(100), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('payment_condition', sa.Text(), nullable=True),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('amount_value', sa.String(80), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='contract_milestones_pkey'),
    )
    op.create_table('contract_payment_terms',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('label', sa.String(160), nullable=False),
        sa.Column('term_text', sa.Text(), nullable=False),
        sa.Column('basis_type', sa.String(60), nullable=True),
        sa.Column('percentage', sa.Numeric(12, 6), nullable=True),
        sa.Column('fixed_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('currency', sa.String(20), nullable=True),
        sa.Column('trigger_type', sa.String(80), nullable=True),
        sa.Column('trigger_description', sa.Text(), nullable=True),
        sa.Column('due_days', sa.Integer(), nullable=True),
        sa.Column('source_clause', sa.String(200), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('candidate_source', sa.String(40), nullable=False),
        sa.Column('human_verified_by', sa.String(200), nullable=True),
        sa.Column('human_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='contract_payment_terms_pkey'),
        sa.UniqueConstraint('contract_revision_id', 'sequence', name='uq_contract_payment_term_revision_sequence'),
    )
    op.create_table('contract_reference_sequences',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('sequence_key', sa.String(60), nullable=False),
        sa.Column('next_number', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='contract_reference_sequences_pkey'),
        sa.UniqueConstraint('sequence_key', name='contract_reference_sequences_sequence_key_key'),
    )
    op.create_table('contract_revisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('controlling_quotation_revision_id', sa.String(36), nullable=False),
        sa.Column('rendered_artifact_id', sa.String(36), nullable=True),
        sa.Column('template_version_id', sa.String(36), nullable=True),
        sa.Column('render_input_hash', sa.String(64), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('commercial_terms_snapshot', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('supersedes_revision_id', sa.String(36), nullable=True),
        sa.Column('accepted_proposal_revision_id', sa.String(36), nullable=True),
        sa.Column('agreement_type', sa.String(80), nullable=False),
        sa.Column('source_snapshot', sa.JSON(), nullable=False),
        sa.Column('contract_name', sa.String(250), nullable=True),
        sa.Column('stage', sa.String(50), nullable=False),
        sa.Column('amount_value', sa.String(100), nullable=True),
        sa.Column('currency', sa.String(20), nullable=True),
        sa.Column('duration', sa.String(120), nullable=True),
        sa.Column('expected_close_date', sa.Date(), nullable=True),
        sa.Column('actual_close_date', sa.Date(), nullable=True),
        sa.Column('payment_condition_text', sa.Text(), nullable=True),
        sa.Column('contracted_scope_text', sa.Text(), nullable=True),
        sa.Column('valuation_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('valuation_currency', sa.String(20), nullable=True),
        sa.Column('valuation_basis', sa.String(160), nullable=True),
        sa.Column('valuation_status', sa.String(50), nullable=False),
        sa.Column('admin_input_snapshot', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='contract_revisions_pkey'),
        sa.UniqueConstraint('contract_id', 'revision_number', name='uq_contract_revision_number'),
    )
    op.create_table('contract_template_snapshots',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('master_content_id', sa.String(36), nullable=False),
        sa.Column('master_content_ref', sa.String(100), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('captured_by', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='contract_template_snapshots_pkey'),
    )
    op.create_table('contracts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('client_account_id', sa.String(36), nullable=False),
        sa.Column('quotation_id', sa.String(36), nullable=False),
        sa.Column('contract_reference', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('current_revision_id', sa.String(36), nullable=True),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('contract_name', sa.String(250), nullable=True),
        sa.Column('proposal_id', sa.String(36), nullable=True),
        sa.Column('accepted_proposal_revision_id', sa.String(36), nullable=True),
        sa.Column('project_opportunity_ref', sa.String(120), nullable=True),
        sa.Column('agreement_type', sa.String(80), nullable=False),
        sa.Column('stage', sa.String(50), nullable=False),
        sa.Column('amount_value', sa.String(100), nullable=True),
        sa.Column('currency', sa.String(20), nullable=True),
        sa.Column('duration', sa.String(120), nullable=True),
        sa.Column('expected_close_date', sa.Date(), nullable=True),
        sa.Column('actual_close_date', sa.Date(), nullable=True),
        sa.Column('close_date_meaning', sa.String(120), nullable=True),
        sa.Column('payment_condition_text', sa.Text(), nullable=True),
        sa.Column('contracted_scope_text', sa.Text(), nullable=True),
        sa.Column('valuation_amount', sa.Numeric(18, 2), nullable=True),
        sa.Column('valuation_currency', sa.String(20), nullable=True),
        sa.Column('valuation_basis', sa.String(160), nullable=True),
        sa.Column('valuation_status', sa.String(50), nullable=False),
        sa.Column('authority_state', sa.String(50), nullable=False),
        sa.Column('last_activity_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('field_provenance', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='contracts_pkey'),
        sa.UniqueConstraint('contract_reference', name='contracts_contract_reference_key'),
    )
    op.create_table('control_definitions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('control_code', sa.String(120), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('source_fields', sa.JSON(), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('finding_code_on_fail', sa.String(120), nullable=True),
        sa.Column('verifier_role', sa.String(100), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='control_definitions_pkey'),
        sa.UniqueConstraint('control_code', name='control_definitions_control_code_key'),
    )
    op.create_table('control_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('control_definition_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('package_id', sa.String(36), nullable=True),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('input_hash', sa.String(64), nullable=False),
        sa.Column('result', sa.String(40), nullable=False),
        sa.Column('evidence_refs', sa.JSON(), nullable=False),
        sa.Column('run_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id', name='control_runs_pkey'),
    )
    op.create_table('corpus_case_results',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('corpus_run_id', sa.String(36), nullable=False),
        sa.Column('corpus_case_id', sa.String(36), nullable=False),
        sa.Column('document_classification_agreement', sa.Boolean(), nullable=False),
        sa.Column('critical_candidate_agreement', sa.Boolean(), nullable=False),
        sa.Column('verified_final_agreement', sa.Boolean(), nullable=False),
        sa.Column('false_accept', sa.Boolean(), nullable=False),
        sa.Column('degraded_keyed_entry', sa.Boolean(), nullable=False),
        sa.Column('human_correction', sa.Boolean(), nullable=False),
        sa.Column('evidence_quality', sa.String(40), nullable=False),
        sa.Column('timing_seconds', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='corpus_case_results_pkey'),
    )
    op.create_table('corpus_cases',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('corpus_run_id', sa.String(36), nullable=False),
        sa.Column('case_key', sa.String(160), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('expected_class', sa.String(100), nullable=True),
        sa.Column('expected_fields', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='corpus_cases_pkey'),
    )
    op.create_table('corpus_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('fixture_set', sa.String(160), nullable=False),
        sa.Column('fixture_version', sa.String(40), nullable=False),
        sa.Column('corpus_version', sa.String(40), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('label', sa.String(160), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metrics_json', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='corpus_runs_pkey'),
    )
    op.create_table('dashboard_input_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('context_key', sa.String(80), nullable=False),
        sa.Column('input_key', sa.String(120), nullable=False),
        sa.Column('group_name', sa.String(50), nullable=False),
        sa.Column('title', sa.String(240), nullable=False),
        sa.Column('why_needed', sa.Text(), nullable=False),
        sa.Column('requested_input', sa.Text(), nullable=False),
        sa.Column('current_value_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('blocking_level', sa.String(40), nullable=False),
        sa.Column('owner_role', sa.String(80), nullable=False),
        sa.Column('linked_route', sa.String(240), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('confirmed_by', sa.String(120), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='dashboard_input_items_pkey'),
        sa.UniqueConstraint('context_key', 'input_key', name='uq_dashboard_input_context_key'),
    )
    op.create_table('definition_entries',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('ref', sa.String(100), nullable=True),
        sa.Column('term', sa.String(240), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('used_in', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('current_revision_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='definition_entries_pkey'),
        sa.UniqueConstraint('term', name='uq_definition_term'),
    )
    op.create_table('definition_revisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('definition_id', sa.String(36), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('term', sa.String(240), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('category', sa.String(100), nullable=True),
        sa.Column('used_in', sa.JSON(), nullable=False),
        sa.Column('aliases', sa.JSON(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('changed_by', sa.String(200), nullable=False),
        sa.Column('changed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('change_reason', sa.String(500), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='definition_revisions_pkey'),
        sa.UniqueConstraint('definition_id', 'revision_number', name='uq_definition_revision_number'),
    )
    op.create_table('delivery_authority_statuses',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('track', sa.String(40), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('basis_artifact', sa.String(300), nullable=False),
        sa.Column('basis_version', sa.String(80), nullable=True),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence_reference', sa.String(500), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='delivery_authority_statuses_pkey'),
        sa.UniqueConstraint('track', name='delivery_authority_statuses_track_key'),
    )
    op.create_table('delivery_scenarios',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_code', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('delivery_location_model', sa.String(200), nullable=False),
        sa.Column('real_data_location', sa.String(300), nullable=False),
        sa.Column('remote_raw_access', sa.String(80), nullable=False),
        sa.Column('external_ai_route', sa.String(200), nullable=False),
        sa.Column('test_environment', sa.String(200), nullable=False),
        sa.Column('commercial_range_min_qar', sa.Float(), nullable=True),
        sa.Column('commercial_range_max_qar', sa.Float(), nullable=True),
        sa.Column('schedule_weeks', sa.Integer(), nullable=True),
        sa.Column('status', sa.Enum('CANDIDATE', 'SELECTED_DEMO', 'REJECTED', name='deliverystatus'), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='delivery_scenarios_pkey'),
        sa.UniqueConstraint('scenario_code', name='delivery_scenarios_scenario_code_key'),
    )
    op.create_table('design_change_requests',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('change_ref', sa.String(120), nullable=False),
        sa.Column('from_baseline_id', sa.String(36), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('regulatory_impact', sa.String(30), nullable=False),
        sa.Column('commercial_impact', sa.String(30), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('linked_revision_ids', sa.JSON(), nullable=False),
        sa.Column('next_baseline_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('approved_to_proceed_by', sa.String(200), nullable=True),
        sa.Column('implemented_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='design_change_requests_pkey'),
        sa.UniqueConstraint('project_id', 'change_ref', name='uq_design_change_ref'),
    )
    op.create_table('discovery_decisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('key', sa.String(100), nullable=False),
        sa.Column('status', sa.Enum('CONFIRMED', 'PROVISIONAL', 'UNKNOWN', 'BLOCKED', name='decisionstatus'), nullable=False),
        sa.Column('value_json', sa.JSON(), nullable=True),
        sa.Column('owner', sa.String(200), nullable=True),
        sa.Column('evidence_reference', sa.String(300), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='discovery_decisions_pkey'),
        sa.UniqueConstraint('key', name='discovery_decisions_key_key'),
    )
    op.create_table('document_classifications',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('predicted_type', sa.String(100), nullable=False),
        sa.Column('classification_method', sa.String(100), nullable=False),
        sa.Column('model_or_rule_version', sa.String(100), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('final_type', sa.String(100), nullable=True),
        sa.Column('review_status', sa.Enum('PENDING', 'AUTO_ACCEPTED_LOW_RISK', 'HUMAN_CONFIRMED', 'HUMAN_CORRECTED', name='classificationreviewstatus'), nullable=False),
        sa.Column('reviewed_by', sa.String(36), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='document_classifications_pkey'),
    )
    op.create_table('document_requests',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('checklist_item_id', sa.String(36), nullable=False),
        sa.Column('client_account_id', sa.String(36), nullable=False),
        sa.Column('requested_from_contact_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('communication_draft_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='document_requests_pkey'),
    )
    op.create_table('document_validities',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('validity_status', sa.String(50), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('rule_version', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='document_validities_pkey'),
        sa.UniqueConstraint('document_version_id', name='document_validities_document_version_id_key'),
    )
    op.create_table('document_versions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('document_id', sa.String(36), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('source_filename', sa.String(300), nullable=False),
        sa.Column('source_path_or_reference', sa.String(500), nullable=False),
        sa.Column('sha256', sa.String(64), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(30), nullable=False),
        sa.Column('revision_label', sa.String(50), nullable=True),
        sa.Column('document_date', sa.Date(), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('approval_state', sa.Enum('WORKING', 'REVIEWED', 'APPROVED', 'SUPERSEDED', 'SUBMITTED', name='documentapprovalstate'), nullable=False),
        sa.Column('source_system', sa.String(100), nullable=False),
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('superseded_by', sa.String(36), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('synthetic_content', sa.LargeBinary(), nullable=True),
        sa.Column('rendition_status', sa.String(40), nullable=False),
        sa.Column('rendition_path_or_reference', sa.String(500), nullable=True),
        sa.Column('rendition_sha256', sa.String(64), nullable=True),
        sa.Column('rendition_mime_type', sa.String(100), nullable=True),
        sa.Column('rendition_file_size', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='document_versions_pkey'),
    )
    op.create_table('documents',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('document_type', sa.Enum('TITLE_DEED', 'OWNER_QID', 'COMMERCIAL_REGISTRATION', 'AUTHORIZATION', 'SURVEY_PLAN', 'COORDINATE_REPORT', 'DRAWING_SET', 'NOC', 'APPLICATION_FORM', 'OTHER', name='documenttype'), nullable=False),
        sa.Column('logical_name', sa.String(240), nullable=False),
        sa.Column('language', sa.String(30), nullable=False),
        sa.Column('source_system', sa.String(100), nullable=False),
        sa.Column('current_version_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='documents_pkey'),
    )
    op.create_table('drawing_metadata_controls',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('control_code', sa.String(100), nullable=False),
        sa.Column('field_definition_id', sa.String(36), nullable=False),
        sa.Column('drawing_source', sa.String(100), nullable=False),
        sa.Column('canonical_field_code', sa.String(120), nullable=False),
        sa.Column('comparison_type', sa.String(50), nullable=False),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='drawing_metadata_controls_pkey'),
    )
    op.create_table('drawing_review_cycles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('discipline', sa.String(100), nullable=False),
        sa.Column('cycle_number', sa.Integer(), nullable=False),
        sa.Column('input_drawing_version_id', sa.String(36), nullable=False),
        sa.Column('review_run_id', sa.String(36), nullable=False),
        sa.Column('output_drawing_version_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('material_change_reason', sa.Text(), nullable=True),
        sa.Column('invalidated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='drawing_review_cycles_pkey'),
    )
    op.create_table('engineering_ai_comment_artifacts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('review_id', sa.String(36), nullable=False),
        sa.Column('revision_id', sa.String(36), nullable=False),
        sa.Column('drawing_document_version_id', sa.String(36), nullable=False),
        sa.Column('artifact_type', sa.String(80), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('draft_text', sa.Text(), nullable=False),
        sa.Column('model_name', sa.String(120), nullable=False),
        sa.Column('model_version', sa.String(80), nullable=False),
        sa.Column('prompt_version', sa.String(80), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('generated_by', sa.String(200), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_ai_comment_artifacts_pkey'),
    )
    op.create_table('engineering_authority_finding_links',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('review_id', sa.String(36), nullable=False),
        sa.Column('revision_id', sa.String(36), nullable=False),
        sa.Column('review_category_id', sa.String(36), nullable=True),
        sa.Column('authority_finding_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_authority_finding_links_pkey'),
        sa.UniqueConstraint('authority_finding_id', 'revision_id', name='uq_engineering_authority_finding_revision_link'),
    )
    op.create_table('engineering_calculation_records',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('revision_id', sa.String(36), nullable=False),
        sa.Column('technical_rule_set_version_id', sa.String(36), nullable=False),
        sa.Column('input_values_json', sa.JSON(), nullable=False),
        sa.Column('normalized_units_json', sa.JSON(), nullable=False),
        sa.Column('result_json', sa.JSON(), nullable=False),
        sa.Column('result_hash', sa.String(64), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_calculation_records_pkey'),
    )
    op.create_table('engineering_category_assignments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('work_package_id', sa.String(36), nullable=True),
        sa.Column('review_category_id', sa.String(36), nullable=False),
        sa.Column('assignee_actor', sa.String(200), nullable=False),
        sa.Column('team', sa.String(120), nullable=True),
        sa.Column('responsibility', sa.String(120), nullable=False),
        sa.Column('capability', sa.String(100), nullable=False),
        sa.Column('effective_state', sa.String(40), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_category_assignments_pkey'),
    )
    op.create_table('engineering_comments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('engineering_review_run_id', sa.String(36), nullable=False),
        sa.Column('drawing_document_version_id', sa.String(36), nullable=False),
        sa.Column('comment_number', sa.Integer(), nullable=False),
        sa.Column('stable_comment_number', sa.String(60), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('proposed_text', sa.Text(), nullable=False),
        sa.Column('location_reference', sa.String(200), nullable=True),
        sa.Column('issue_text', sa.Text(), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('regulation_version_id', sa.String(36), nullable=True),
        sa.Column('regulation_evidence_reference', sa.String(300), nullable=True),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('uncertainty_state', sa.String(50), nullable=False),
        sa.Column('evidence_reference', sa.String(300), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('engineer_disposition', sa.String(60), nullable=False),
        sa.Column('engineer_notes', sa.Text(), nullable=True),
        sa.Column('closure_state', sa.String(50), nullable=False),
        sa.Column('required_action', sa.Text(), nullable=True),
        sa.Column('supersedes_comment_id', sa.String(36), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('correction_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('re_reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence_snapshot', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_comments_pkey'),
    )
    op.create_table('engineering_deliverable_revisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('deliverable_id', sa.String(36), nullable=False),
        sa.Column('revision_code', sa.String(40), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(240), nullable=False),
        sa.Column('issue_purpose', sa.String(100), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('approval_status', sa.String(40), nullable=False),
        sa.Column('prepared_by', sa.String(200), nullable=False),
        sa.Column('supersedes_revision_id', sa.String(36), nullable=True),
        sa.Column('immutable_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('idempotency_key', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_deliverable_revisions_pkey'),
        sa.UniqueConstraint('deliverable_id', 'revision_code', name='uq_engineering_deliverable_revision'),
        sa.UniqueConstraint('deliverable_id', 'sequence', name='uq_engineering_deliverable_revision_sequence'),
    )
    op.create_table('engineering_deliverables',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('work_package_id', sa.String(36), nullable=False),
        sa.Column('deliverable_ref', sa.String(120), nullable=False),
        sa.Column('title', sa.String(240), nullable=False),
        sa.Column('discipline', sa.String(80), nullable=False),
        sa.Column('deliverable_type', sa.String(80), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('current_revision_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_deliverables_pkey'),
        sa.UniqueConstraint('work_package_id', 'deliverable_ref', name='uq_engineering_deliverable_ref'),
    )
    op.create_table('engineering_internal_review_comments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('review_id', sa.String(36), nullable=False),
        sa.Column('revision_id', sa.String(36), nullable=False),
        sa.Column('drawing_document_version_id', sa.String(36), nullable=False),
        sa.Column('comment_text', sa.Text(), nullable=False),
        sa.Column('location_reference', sa.String(200), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_internal_review_comments_pkey'),
    )
    op.create_table('engineering_material_tests',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('revision_id', sa.String(36), nullable=True),
        sa.Column('material_code', sa.String(120), nullable=False),
        sa.Column('test_type', sa.String(120), nullable=False),
        sa.Column('result_json', sa.JSON(), nullable=False),
        sa.Column('certificate_document_version_id', sa.String(36), nullable=True),
        sa.Column('laboratory_party_id', sa.String(36), nullable=True),
        sa.Column('accreditation_evidence_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('accepted_by', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_material_tests_pkey'),
    )
    op.create_table('engineering_professional_approvals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('revision_id', sa.String(36), nullable=False),
        sa.Column('approval_type', sa.String(60), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('approver_actor', sa.String(200), nullable=False),
        sa.Column('approver_party_id', sa.String(36), nullable=True),
        sa.Column('professional_credential_id', sa.String(36), nullable=True),
        sa.Column('credential_reference', sa.String(240), nullable=False),
        sa.Column('pinned_rendition_ids', sa.JSON(), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('withdrawn_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='engineering_professional_approvals_pkey'),
        sa.UniqueConstraint('revision_id', 'approval_type', name='uq_engineering_professional_approval'),
    )
    op.create_table('engineering_project_members',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('actor_id', sa.String(200), nullable=False),
        sa.Column('capability', sa.String(80), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('added_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_project_members_pkey'),
        sa.UniqueConstraint('project_id', 'actor_id', name='uq_engineering_project_member'),
    )
    op.create_table('engineering_renditions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('revision_id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('rendition_kind', sa.String(30), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('renderer_type', sa.String(80), nullable=True),
        sa.Column('renderer_version', sa.String(80), nullable=True),
        sa.Column('source_rendition_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_renditions_pkey'),
        sa.UniqueConstraint('revision_id', 'rendition_kind', name='uq_engineering_rendition_kind'),
    )
    op.create_table('engineering_review_categories',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(100), nullable=False),
        sa.Column('name', sa.String(180), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('discipline', sa.String(100), nullable=True),
        sa.Column('stage_class', sa.String(100), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('source_kind', sa.String(50), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_review_categories_pkey'),
        sa.UniqueConstraint('code', name='uq_engineering_review_category_code'),
    )
    op.create_table('engineering_review_findings',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('review_id', sa.String(36), nullable=False),
        sa.Column('finding_ref', sa.String(80), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('response', sa.Text(), nullable=True),
        sa.Column('disposition_by', sa.String(200), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='engineering_review_findings_pkey'),
    )
    op.create_table('engineering_review_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('engineering_review_id', sa.String(36), nullable=False),
        sa.Column('drawing_document_version_id', sa.String(36), nullable=False),
        sa.Column('review_scope_id', sa.String(36), nullable=True),
        sa.Column('regulation_applicability_snapshot', sa.JSON(), nullable=False),
        sa.Column('pinned_drawing_hash', sa.String(64), nullable=True),
        sa.Column('pinned_revision_label', sa.String(50), nullable=True),
        sa.Column('model_config_version', sa.String(80), nullable=True),
        sa.Column('prompt_bundle_version', sa.String(80), nullable=True),
        sa.Column('evidence_recipe', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_review_runs_pkey'),
    )
    op.create_table('engineering_review_scopes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('engineering_review_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('scope_code', sa.String(100), nullable=False),
        sa.Column('discipline', sa.String(100), nullable=False),
        sa.Column('supported_drawing_types', sa.JSON(), nullable=False),
        sa.Column('selected_regulation_version_ids', sa.JSON(), nullable=False),
        sa.Column('applicability_basis', sa.Text(), nullable=False),
        sa.Column('review_objectives', sa.JSON(), nullable=False),
        sa.Column('excluded_topics', sa.JSON(), nullable=False),
        sa.Column('authorized_engineer_role', sa.String(100), nullable=False),
        sa.Column('stage2_disposition', sa.String(40), nullable=False),
        sa.Column('evidence_class', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('synthetic_only', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_review_scopes_pkey'),
        sa.UniqueConstraint('scope_code', name='engineering_review_scopes_scope_code_key'),
    )
    op.create_table('engineering_reviews',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('discipline', sa.String(100), nullable=False),
        sa.Column('drawing_document_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('authorized_engineer_user_id', sa.String(36), nullable=True),
        sa.Column('current_scope_id', sa.String(36), nullable=True),
        sa.Column('current_drawing_version_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_reviews_pkey'),
    )
    op.create_table('engineering_technical_checks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('revision_id', sa.String(36), nullable=False),
        sa.Column('technical_rule_set_version_id', sa.String(36), nullable=False),
        sa.Column('technical_rule_id', sa.String(36), nullable=True),
        sa.Column('result', sa.String(20), nullable=False),
        sa.Column('inputs_json', sa.JSON(), nullable=False),
        sa.Column('calculated_values_json', sa.JSON(), nullable=False),
        sa.Column('rule_version', sa.String(40), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('evaluated_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_technical_checks_pkey'),
    )
    op.create_table('engineering_work_packages',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('package_ref', sa.String(120), nullable=False),
        sa.Column('title', sa.String(240), nullable=False),
        sa.Column('discipline', sa.String(80), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('owner_actor', sa.String(200), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='engineering_work_packages_pkey'),
        sa.UniqueConstraint('project_id', 'package_ref', name='uq_engineering_work_package_ref'),
    )
    op.create_table('evidence_artifacts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('evidence_type', sa.String(80), nullable=False),
        sa.Column('source_reference', sa.String(300), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('synthetic_only', sa.Boolean(), nullable=False),
        sa.Column('label', sa.String(150), nullable=False),
        sa.PrimaryKeyConstraint('id', name='evidence_artifacts_pkey'),
    )
    op.create_table('excel_project_rows',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('workbook_identity', sa.String(300), nullable=False),
        sa.Column('sheet_name', sa.String(120), nullable=False),
        sa.Column('row_number', sa.Integer(), nullable=False),
        sa.Column('row_key', sa.String(150), nullable=False),
        sa.Column('ownership_matrix_json', sa.JSON(), nullable=False),
        sa.Column('human_cells_fingerprint', sa.String(64), nullable=True),
        sa.Column('projection_sheet', sa.String(120), nullable=False),
        sa.Column('read_policy', sa.String(200), nullable=False),
        sa.Column('write_policy', sa.String(200), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='excel_project_rows_pkey'),
        sa.UniqueConstraint('project_id', name='excel_project_rows_project_id_key'),
        sa.UniqueConstraint('workbook_identity', 'sheet_name', 'row_key', name='uq_excel_project_row_identity'),
    )
    op.create_table('excel_projection_rules',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('sheet_name', sa.String(120), nullable=False),
        sa.Column('row_key_rule', sa.String(200), nullable=False),
        sa.Column('target_column', sa.String(120), nullable=False),
        sa.Column('ownership', sa.String(40), nullable=False),
        sa.Column('source_field', sa.String(120), nullable=False),
        sa.Column('rendering_rule_id', sa.String(36), nullable=True),
        sa.Column('write_allowed', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='excel_projection_rules_pkey'),
        sa.UniqueConstraint('scenario_id', 'sheet_name', 'target_column', name='uq_excel_projection_rule'),
    )
    op.create_table('excel_projections',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('workbook_ref', sa.String(300), nullable=False),
        sa.Column('sheet', sa.String(120), nullable=False),
        sa.Column('row_key', sa.String(150), nullable=False),
        sa.Column('target_column', sa.String(120), nullable=False),
        sa.Column('ownership', sa.String(40), nullable=False),
        sa.Column('rendered_value', sa.Text(), nullable=True),
        sa.Column('source_verified_assertion_id', sa.String(36), nullable=True),
        sa.Column('rendering_rule_version', sa.String(40), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('configuration_bundle_id', sa.String(36), nullable=True),
        sa.Column('target_rendering_rule_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='excel_projections_pkey'),
    )
    op.create_table('execution_authority_configs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority', sa.String(50), nullable=False),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.Column('production_enabled', sa.Boolean(), nullable=False),
        sa.Column('external_actions_enabled', sa.Boolean(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='execution_authority_configs_pkey'),
        sa.UniqueConstraint('authority', name='execution_authority_configs_authority_key'),
    )
    op.create_table('expansion_fixture_resources',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('fixture_version', sa.String(40), nullable=False),
        sa.Column('resource_path', sa.String(300), nullable=False),
        sa.Column('source_family', sa.String(80), nullable=False),
        sa.Column('scenario', sa.String(100), nullable=False),
        sa.Column('synthetic_label', sa.String(150), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='expansion_fixture_resources_pkey'),
    )
    op.create_table('external_bodies',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(80), nullable=False),
        sa.Column('name_en', sa.String(240), nullable=False),
        sa.Column('name_ar', sa.String(240), nullable=True),
        sa.Column('body_type', sa.String(80), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('jurisdiction_id', sa.String(36), nullable=True),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('provenance_json', sa.JSON(), nullable=False),
        sa.Column('verification_state', sa.String(40), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='external_bodies_pkey'),
        sa.UniqueConstraint('code', name='uq_external_body_code'),
    )
    op.create_table('external_body_units',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('external_body_id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(80), nullable=False),
        sa.Column('name_en', sa.String(240), nullable=False),
        sa.Column('name_ar', sa.String(240), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='external_body_units_pkey'),
        sa.UniqueConstraint('external_body_id', 'code', name='uq_external_body_unit_code'),
    )
    op.create_table('external_interaction_profiles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('external_body_id', sa.String(36), nullable=False),
        sa.Column('channel_code', sa.String(60), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('read_only', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='external_interaction_profiles_pkey'),
        sa.UniqueConstraint('external_body_id', 'channel_code', name='uq_external_interaction_channel'),
    )
    op.create_table('external_mutation_observations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('monitoring_run_id', sa.String(36), nullable=False),
        sa.Column('prior_snapshot_id', sa.String(36), nullable=True),
        sa.Column('current_snapshot_id', sa.String(36), nullable=True),
        sa.Column('changed_paths', sa.JSON(), nullable=False),
        sa.Column('prior_values', sa.JSON(), nullable=False),
        sa.Column('observed_values', sa.JSON(), nullable=False),
        sa.Column('impact', sa.String(40), nullable=False),
        sa.Column('evidence_artifact_id', sa.String(300), nullable=True),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('authorship', sa.String(60), nullable=False),
        sa.PrimaryKeyConstraint('id', name='external_mutation_observations_pkey'),
    )
    op.create_table('external_submission_snapshots',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('submission_attempt_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('channel_code', sa.String(60), nullable=False),
        sa.Column('package_hash', sa.String(64), nullable=False),
        sa.Column('external_reference', sa.String(240), nullable=True),
        sa.Column('external_status', sa.String(40), nullable=False),
        sa.Column('external_submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confirmation_source', sa.String(40), nullable=False),
        sa.Column('evidence_document_version_id', sa.String(36), nullable=True),
        sa.Column('confirmed_by', sa.String(200), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='external_submission_snapshots_pkey'),
        sa.UniqueConstraint('submission_attempt_id', name='uq_external_snapshot_attempt'),
    )
    op.create_table('external_system_links',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('system_type', sa.Enum('SYNOLOGY', 'EXCEL', 'MUNICIPALITY', name='systemtype'), nullable=False),
        sa.Column('external_reference', sa.String(300), nullable=False),
        sa.Column('display_reference', sa.String(300), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='external_system_links_pkey'),
    )
    op.create_table('extraction_spike_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('dataset_name', sa.String(200), nullable=False),
        sa.Column('dataset_type', sa.Enum('SYNTHETIC', 'APPROVED_REAL_TEST', name='datasettype'), nullable=False),
        sa.Column('environment', sa.String(20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('document_count', sa.Integer(), nullable=False),
        sa.Column('extractor_config_version', sa.String(100), nullable=False),
        sa.Column('classifier_config_version', sa.String(100), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('metrics_json', sa.JSON(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='extraction_spike_runs_pkey'),
    )
    op.create_table('field_authority_rules',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('field_definition_id', sa.String(36), nullable=False),
        sa.Column('purpose', sa.String(100), nullable=False),
        sa.Column('primary_source_type', sa.String(100), nullable=False),
        sa.Column('fallback_source_type', sa.String(100), nullable=True),
        sa.Column('conflict_behavior', sa.String(50), nullable=False),
        sa.Column('human_verifier_role', sa.String(100), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('PROVISIONAL', 'CONFIRMED', 'NEEDS_DECISION', name='configstatus'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='field_authority_rules_pkey'),
    )
    op.create_table('field_definitions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('field_code', sa.String(120), nullable=False),
        sa.Column('name_en', sa.String(200), nullable=False),
        sa.Column('name_ar', sa.String(200), nullable=True),
        sa.Column('data_type', sa.Enum('STRING', 'IDENTIFIER', 'NUMBER', 'DATE', 'BOOLEAN', 'CODE', name='datatype'), nullable=False),
        sa.Column('unit', sa.String(30), nullable=True),
        sa.Column('criticality', sa.Enum('CRITICAL', 'MAJOR', 'NORMAL', 'ADVISORY', name='criticality'), nullable=False),
        sa.Column('normalization_rule', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='field_definitions_pkey'),
        sa.UniqueConstraint('field_code', name='field_definitions_field_code_key'),
    )
    op.create_table('field_matrix_coverage',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(120), nullable=False),
        sa.Column('field_set_version', sa.String(80), nullable=False),
        sa.Column('total_fields', sa.Integer(), nullable=False),
        sa.Column('critical_fields', sa.Integer(), nullable=False),
        sa.Column('complete_fields', sa.Integer(), nullable=False),
        sa.Column('incomplete_fields', sa.Integer(), nullable=False),
        sa.Column('blocked_external', sa.Integer(), nullable=False),
        sa.Column('unknown', sa.Integer(), nullable=False),
        sa.Column('target_coverage', sa.JSON(), nullable=False),
        sa.Column('result', sa.String(40), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='field_matrix_coverage_pkey'),
    )
    op.create_table('field_observations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('field_definition_id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('raw_value', sa.Text(), nullable=False),
        sa.Column('normalized_candidate_value', sa.Text(), nullable=True),
        sa.Column('structured_value_json', sa.JSON(), nullable=True),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('bounding_box_json', sa.JSON(), nullable=True),
        sa.Column('source_region_text', sa.Text(), nullable=True),
        sa.Column('extraction_method', sa.Enum('RULE', 'OCR_RULE', 'MODEL', 'MANUAL_KEYED', 'IMPORT', name='extractionmethod'), nullable=False),
        sa.Column('extractor_version', sa.String(100), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id', name='field_observations_pkey'),
    )
    op.create_table('finance_evidence',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('evidence_type', sa.String(60), nullable=False),
        sa.Column('status', sa.String(60), nullable=False),
        sa.Column('source', sa.String(60), nullable=False),
        sa.Column('evidence_reference', sa.String(300), nullable=False),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='finance_evidence_pkey'),
    )
    op.create_table('financial_account_masters',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('legal_entity_party_id', sa.String(36), nullable=True),
        sa.Column('legal_entity_ref', sa.String(160), nullable=False),
        sa.Column('account_name', sa.String(200), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='financial_account_masters_pkey'),
    )
    op.create_table('financial_account_versions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('financial_account_master_id', sa.String(36), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('bank_name', sa.String(160), nullable=False),
        sa.Column('account_name', sa.String(200), nullable=False),
        sa.Column('account_reference', sa.String(200), nullable=False),
        sa.Column('currency', sa.String(20), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=False),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('payment_instruction_metadata', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='financial_account_versions_pkey'),
        sa.UniqueConstraint('financial_account_master_id', 'version_number', name='uq_financial_account_version'),
    )
    op.create_table('financial_settlement_contexts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('readiness_state', sa.String(40), nullable=False),
        sa.Column('snapshot_json', sa.JSON(), nullable=False),
        sa.Column('snapshot_hash', sa.String(64), nullable=False),
        sa.Column('unsupported_conditions_json', sa.JSON(), nullable=False),
        sa.Column('assessed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assessed_by', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='financial_settlement_contexts_pkey'),
        sa.UniqueConstraint('contract_id', 'project_id', name='uq_financial_settlement_context_scope'),
    )
    op.create_table('financial_settlement_records',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('snapshot_hash', sa.String(64), nullable=False),
        sa.Column('settled_by', sa.String(200), nullable=False),
        sa.Column('settled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('basis', sa.Text(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='financial_settlement_records_pkey'),
        sa.UniqueConstraint('contract_id', 'project_id', name='uq_financial_settlement_record_scope'),
    )
    op.create_table('finding_closure_evaluations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('finding_id', sa.String(36), nullable=False),
        sa.Column('resolution_id', sa.String(36), nullable=False),
        sa.Column('finding_code_version', sa.String(40), nullable=False),
        sa.Column('required_evidence', sa.JSON(), nullable=False),
        sa.Column('provided_evidence', sa.JSON(), nullable=False),
        sa.Column('required_verifier_role', sa.String(100), nullable=False),
        sa.Column('verifier', sa.String(200), nullable=True),
        sa.Column('result', sa.String(60), nullable=False),
        sa.Column('blockers', sa.JSON(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='finding_closure_evaluations_pkey'),
    )
    op.create_table('finding_codes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(120), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('title_en', sa.String(240), nullable=False),
        sa.Column('title_ar', sa.String(240), nullable=False),
        sa.Column('description_en', sa.Text(), nullable=False),
        sa.Column('description_ar', sa.Text(), nullable=False),
        sa.Column('source_classes_allowed', sa.JSON(), nullable=False),
        sa.Column('discipline', sa.String(80), nullable=False),
        sa.Column('default_severity', sa.String(30), nullable=False),
        sa.Column('blocking_default', sa.Boolean(), nullable=False),
        sa.Column('required_owner_role', sa.String(80), nullable=False),
        sa.Column('default_sla_hours', sa.Integer(), nullable=False),
        sa.Column('closure_evidence_policy', sa.String(60), nullable=False),
        sa.Column('internal_preflight_control_code', sa.String(120), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('checksum', sa.String(64), nullable=True),
        sa.Column('finding_class', sa.String(60), nullable=False),
        sa.Column('typical_root_cause_category', sa.String(100), nullable=False),
        sa.Column('closure_verifier_role', sa.String(100), nullable=False),
        sa.Column('allowed_dispositions', sa.JSON(), nullable=False),
        sa.Column('resubmission_gate_effect', sa.String(60), nullable=False),
        sa.Column('precheck_gate_effect', sa.String(60), nullable=False),
        sa.Column('recurrence_key_strategy', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id', name='finding_codes_pkey'),
        sa.UniqueConstraint('code', name='finding_codes_code_key'),
    )
    op.create_table('finding_disputes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('finding_id', sa.String(36), nullable=False),
        sa.Column('raised_by', sa.String(200), nullable=False),
        sa.Column('raised_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('evidence_artifact_ids', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('reviewed_by', sa.String(200), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decision', sa.String(80), nullable=True),
        sa.Column('resubmission_effect', sa.String(50), nullable=False),
        sa.PrimaryKeyConstraint('id', name='finding_disputes_pkey'),
    )
    op.create_table('finding_history_links',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('current_finding_id', sa.String(36), nullable=False),
        sa.Column('prior_finding_id', sa.String(36), nullable=False),
        sa.Column('relationship_type', sa.String(60), nullable=False),
        sa.Column('finding_code', sa.String(120), nullable=False),
        sa.Column('affected_object_key', sa.String(200), nullable=True),
        sa.Column('submission_cycle_id', sa.String(36), nullable=True),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('linked_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('linked_by', sa.String(200), nullable=False),
        sa.Column('confidence_mode', sa.String(60), nullable=False),
        sa.PrimaryKeyConstraint('id', name='finding_history_links_pkey'),
    )
    op.create_table('finding_prevention_controls',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('finding_code_id', sa.String(36), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('control_code', sa.String(120), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence_requirement', sa.String(120), nullable=True),
        sa.Column('owner_role', sa.String(80), nullable=False),
        sa.Column('required_before_gate', sa.String(100), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='finding_prevention_controls_pkey'),
    )
    op.create_table('finding_recurrence_analysis_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('run_id', sa.String(36), nullable=False),
        sa.Column('finding_code', sa.String(120), nullable=False),
        sa.Column('recurrence_key', sa.String(300), nullable=False),
        sa.Column('root_cause_category', sa.String(100), nullable=False),
        sa.Column('discipline', sa.String(80), nullable=False),
        sa.Column('affected_object_key', sa.String(200), nullable=True),
        sa.Column('occurrence_count', sa.Integer(), nullable=False),
        sa.Column('submission_cycle_count', sa.Integer(), nullable=False),
        sa.Column('preparation_revision_count', sa.Integer(), nullable=False),
        sa.Column('prior_approval_count', sa.Integer(), nullable=False),
        sa.Column('recurrence_after_closure_count', sa.Integer(), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('related_finding_ids', sa.JSON(), nullable=False),
        sa.Column('classification', sa.String(60), nullable=False),
        sa.Column('result', sa.String(60), nullable=False),
        sa.PrimaryKeyConstraint('id', name='finding_recurrence_analysis_items_pkey'),
    )
    op.create_table('finding_recurrence_analysis_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=True),
        sa.Column('fixture_evidence_set_version', sa.String(100), nullable=False),
        sa.Column('from_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('to_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finding_count', sa.Integer(), nullable=False),
        sa.Column('closed_count', sa.Integer(), nullable=False),
        sa.Column('recurring_count', sa.Integer(), nullable=False),
        sa.Column('recurrence_after_closure_count', sa.Integer(), nullable=False),
        sa.Column('possible_recurrence_review_count', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.Column('result_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='finding_recurrence_analysis_runs_pkey'),
    )
    op.create_table('finding_reopen_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('finding_id', sa.String(36), nullable=False),
        sa.Column('prior_resolution_id', sa.String(36), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('source_authority_event_id', sa.String(36), nullable=True),
        sa.Column('reopened_by', sa.String(200), nullable=False),
        sa.Column('reopened_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='finding_reopen_events_pkey'),
    )
    op.create_table('finding_resolution_evidence',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('finding_resolution_id', sa.String(36), nullable=False),
        sa.Column('evidence_artifact_id', sa.String(300), nullable=False),
        sa.Column('evidence_type', sa.String(80), nullable=False),
        sa.Column('source_entity_type', sa.String(100), nullable=True),
        sa.Column('source_entity_id', sa.String(160), nullable=True),
        sa.Column('source_version_or_hash', sa.String(160), nullable=True),
        sa.Column('added_by', sa.String(200), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='finding_resolution_evidence_pkey'),
    )
    op.create_table('finding_resolutions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('finding_id', sa.String(36), nullable=False),
        sa.Column('resolution_version', sa.Integer(), nullable=False),
        sa.Column('disposition', sa.String(60), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('correction_type', sa.String(100), nullable=False),
        sa.Column('correction_summary', sa.Text(), nullable=False),
        sa.Column('root_cause_category', sa.String(100), nullable=False),
        sa.Column('corrected_entity_type', sa.String(100), nullable=True),
        sa.Column('corrected_entity_id', sa.String(160), nullable=True),
        sa.Column('corrected_version_or_hash', sa.String(160), nullable=True),
        sa.Column('required_evidence_policy', sa.String(100), nullable=False),
        sa.Column('closure_criteria_version', sa.String(40), nullable=False),
        sa.Column('proposed_by', sa.String(200), nullable=False),
        sa.Column('proposed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified_by', sa.String(200), nullable=True),
        sa.Column('verifier_role', sa.String(100), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verification_result', sa.String(50), nullable=True),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('prior_resolution_id', sa.String(36), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id', name='finding_resolutions_pkey'),
    )
    op.create_table('finding_routing_rules',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(100), nullable=False),
        sa.Column('finding_code_id', sa.String(36), nullable=True),
        sa.Column('discipline', sa.String(80), nullable=True),
        sa.Column('source_type', sa.String(60), nullable=True),
        sa.Column('severity', sa.String(30), nullable=True),
        sa.Column('owner_role', sa.String(80), nullable=False),
        sa.Column('preferred_user_id', sa.String(36), nullable=True),
        sa.Column('escalation_role', sa.String(80), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='finding_routing_rules_pkey'),
    )
    op.create_table('finding_sla_policies',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(100), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('source_type', sa.String(60), nullable=True),
        sa.Column('acknowledgment_hours', sa.Integer(), nullable=False),
        sa.Column('assignment_hours', sa.Integer(), nullable=False),
        sa.Column('target_action_hours', sa.Integer(), nullable=False),
        sa.Column('escalation_hours', sa.Integer(), nullable=False),
        sa.Column('business_calendar_mode', sa.String(60), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('policy_label', sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint('id', name='finding_sla_policies_pkey'),
    )
    op.create_table('findings',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('authority_precheck_run_id', sa.String(36), nullable=True),
        sa.Column('submission_cycle_id', sa.String(36), nullable=True),
        sa.Column('authority_event_id', sa.String(36), nullable=True),
        sa.Column('finding_code_id', sa.String(36), nullable=True),
        sa.Column('source_type', sa.String(60), nullable=False),
        sa.Column('source_reference', sa.String(300), nullable=False),
        sa.Column('external_finding_id', sa.String(160), nullable=True),
        sa.Column('source_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('captured_by', sa.String(200), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('raw_text', sa.Text(), nullable=False),
        sa.Column('normalized_summary', sa.Text(), nullable=False),
        sa.Column('language', sa.String(30), nullable=False),
        sa.Column('translated_summary', sa.Text(), nullable=True),
        sa.Column('discipline', sa.String(80), nullable=False),
        sa.Column('affected_object_type', sa.String(80), nullable=True),
        sa.Column('affected_object_id', sa.String(160), nullable=True),
        sa.Column('requirement_code', sa.String(120), nullable=True),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('assignee_user_id', sa.String(36), nullable=True),
        sa.Column('assignee_role', sa.String(80), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence_artifact_id', sa.String(300), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.Column('finding_code_version', sa.String(40), nullable=True),
        sa.Column('finding_code_checksum', sa.String(64), nullable=True),
        sa.Column('domain', sa.String(50), nullable=True),
        sa.Column('proposal_id', sa.String(36), nullable=True),
        sa.Column('contract_id', sa.String(36), nullable=True),
        sa.Column('permit_id', sa.String(36), nullable=True),
        sa.Column('owner_persona', sa.String(40), nullable=True),
        sa.Column('deep_link', sa.String(300), nullable=True),
        sa.PrimaryKeyConstraint('id', name='findings_pkey'),
    )
    op.create_table('form_automation_profiles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('master_content_item_id', sa.String(36), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=False),
        sa.Column('renderer_type', sa.String(50), nullable=False),
        sa.Column('automation_status', sa.String(40), nullable=False),
        sa.Column('semantic_contract_version', sa.String(40), nullable=False),
        sa.Column('working_rendition_ref', sa.String(500), nullable=True),
        sa.Column('writer_policy_json', sa.JSON(), nullable=False),
        sa.Column('source_version_state', sa.String(40), nullable=False),
        sa.Column('managed_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='form_automation_profiles_pkey'),
        sa.UniqueConstraint('master_content_item_id', name='uq_form_automation_profile_item'),
    )
    op.create_table('form_instances',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('master_content_item_id', sa.String(36), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=False),
        sa.Column('profile_id', sa.String(36), nullable=False),
        sa.Column('mapping_release_id', sa.String(36), nullable=True),
        sa.Column('context_type', sa.String(50), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('resolved_values', sa.JSON(), nullable=False),
        sa.Column('resolved_assertion_ids', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('invalidation_reason', sa.Text(), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='form_instances_pkey'),
    )
    op.create_table('form_mapping_release_qa_gates',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('mapping_release_id', sa.String(36), nullable=False),
        sa.Column('qa_run_id', sa.String(36), nullable=False),
        sa.Column('qa_type', sa.String(50), nullable=False),
        sa.Column('required', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='form_mapping_release_qa_gates_pkey'),
        sa.UniqueConstraint('mapping_release_id', 'qa_run_id', 'qa_type', name='uq_form_mapping_release_qa_gate'),
    )
    op.create_table('form_mapping_releases',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('profile_id', sa.String(36), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('mapping_json', sa.JSON(), nullable=False),
        sa.Column('master_content_item_id', sa.String(36), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('normalized_rendition_ref', sa.String(500), nullable=True),
        sa.Column('normalized_rendition_hash', sa.String(128), nullable=True),
        sa.Column('semantic_contract_version', sa.String(40), nullable=True),
        sa.Column('renderer_type', sa.String(50), nullable=True),
        sa.Column('renderer_version', sa.String(60), nullable=True),
        sa.Column('mapping_checksum', sa.String(128), nullable=True),
        sa.Column('reviewed_by', sa.String(200), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('released_by', sa.String(200), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('retired_by', sa.String(200), nullable=True),
        sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('invalidation_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='form_mapping_releases_pkey'),
        sa.UniqueConstraint('profile_id', 'version', name='uq_form_mapping_release_version'),
    )
    op.create_table('form_mapping_rules',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('mapping_release_id', sa.String(36), nullable=False),
        sa.Column('logical_field_key', sa.String(200), nullable=False),
        sa.Column('target_key', sa.String(200), nullable=False),
        sa.Column('transform_type', sa.String(50), nullable=False),
        sa.Column('target_writer', sa.String(40), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('rect_json', sa.JSON(), nullable=False),
        sa.Column('capacity', sa.Integer(), nullable=True),
        sa.Column('configuration_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='form_mapping_rules_pkey'),
        sa.UniqueConstraint('mapping_release_id', 'logical_field_key', 'target_key', name='uq_form_mapping_rule_target'),
    )
    op.create_table('form_qa_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('generated_artifact_id', sa.String(36), nullable=False),
        sa.Column('mapping_release_id', sa.String(36), nullable=True),
        sa.Column('qa_type', sa.String(50), nullable=False),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('result', sa.String(30), nullable=False),
        sa.Column('checks_json', sa.JSON(), nullable=False),
        sa.Column('synthetic_only', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='form_qa_runs_pkey'),
    )
    op.create_table('form_signature_requirements',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('form_instance_id', sa.String(36), nullable=False),
        sa.Column('logical_field_key', sa.String(200), nullable=False),
        sa.Column('signer_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='form_signature_requirements_pkey'),
    )
    op.create_table('form_template_versions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('template_id', sa.String(36), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('source_field_mapping_version', sa.String(40), nullable=False),
        sa.Column('mapping_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='form_template_versions_pkey'),
    )
    op.create_table('form_templates',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('template_code', sa.String(120), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='form_templates_pkey'),
        sa.UniqueConstraint('template_code', name='form_templates_template_code_key'),
    )
    op.create_table('form_validation_results',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('generated_artifact_id', sa.String(36), nullable=False),
        sa.Column('validation_type', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('result_json', sa.JSON(), nullable=False),
        sa.Column('validated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('validated_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='form_validation_results_pkey'),
    )
    op.create_table('g10_evidence_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('criterion_id', sa.String(100), nullable=False),
        sa.Column('category', sa.String(80), nullable=False),
        sa.Column('requirement', sa.Text(), nullable=False),
        sa.Column('evidence_path', sa.String(400), nullable=False),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('owner', sa.String(200), nullable=False),
        sa.Column('blocker', sa.Text(), nullable=True),
        sa.Column('next_action', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='g10_evidence_items_pkey'),
    )
    op.create_table('generated_artifacts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('form_instance_id', sa.String(36), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=False),
        sa.Column('profile_id', sa.String(36), nullable=False),
        sa.Column('mapping_release_id', sa.String(36), nullable=True),
        sa.Column('renderer_version', sa.String(60), nullable=False),
        sa.Column('artifact_type', sa.String(50), nullable=False),
        sa.Column('source_path_or_reference', sa.String(500), nullable=True),
        sa.Column('generated_payload', sa.JSON(), nullable=False),
        sa.Column('content_hash', sa.String(128), nullable=False),
        sa.Column('resolved_assertion_ids', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='generated_artifacts_pkey'),
    )
    op.create_table('gold_document_labels',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('expected_class', sa.String(100), nullable=False),
        sa.Column('adjudicated_by', sa.String(200), nullable=False),
        sa.Column('adjudicated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='gold_document_labels_pkey'),
    )
    op.create_table('gold_field_labels',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('field_definition_id', sa.String(36), nullable=False),
        sa.Column('expected_semantic_value', sa.JSON(), nullable=False),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('source_region', sa.Text(), nullable=True),
        sa.Column('adjudicated_by', sa.String(200), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='gold_field_labels_pkey'),
    )
    op.create_table('grid_field_diffs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('row_result_id', sa.String(36), nullable=False),
        sa.Column('field_code', sa.String(120), nullable=False),
        sa.Column('expected', sa.JSON(), nullable=False),
        sa.Column('observed', sa.JSON(), nullable=False),
        sa.Column('normalized_expected', sa.JSON(), nullable=False),
        sa.Column('normalized_observed', sa.JSON(), nullable=False),
        sa.Column('tolerance_rule_version', sa.String(40), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='grid_field_diffs_pkey'),
    )
    op.create_table('grid_persistence_evidence',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('grid_code', sa.String(100), nullable=False),
        sa.Column('intended_state_hash', sa.String(64), nullable=False),
        sa.Column('post_save_snapshot_id', sa.String(36), nullable=True),
        sa.Column('reopened_snapshot_id', sa.String(36), nullable=True),
        sa.Column('result', sa.String(50), nullable=False),
        sa.Column('evidence_artifact_id', sa.String(300), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='grid_persistence_evidence_pkey'),
    )
    op.create_table('grid_reconciliation_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('portal_snapshot_id', sa.String(36), nullable=False),
        sa.Column('grid_code', sa.String(100), nullable=False),
        sa.Column('intended_row_count', sa.Integer(), nullable=False),
        sa.Column('observed_row_count', sa.Integer(), nullable=False),
        sa.Column('matched_count', sa.Integer(), nullable=False),
        sa.Column('missing_count', sa.Integer(), nullable=False),
        sa.Column('extra_count', sa.Integer(), nullable=False),
        sa.Column('mismatch_count', sa.Integer(), nullable=False),
        sa.Column('ambiguous_count', sa.Integer(), nullable=False),
        sa.Column('result', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='grid_reconciliation_runs_pkey'),
    )
    op.create_table('grid_row_reconciliation_results',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('run_id', sa.String(36), nullable=False),
        sa.Column('canonical_row_id', sa.String(160), nullable=True),
        sa.Column('portal_row_id', sa.String(160), nullable=True),
        sa.Column('business_key', sa.String(300), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('field_diffs', sa.JSON(), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='grid_row_reconciliation_results_pkey'),
    )
    op.create_table('handover_acceptances',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('handover_package_revision_id', sa.String(36), nullable=False),
        sa.Column('acceptance_status', sa.String(40), nullable=False),
        sa.Column('signed_form_document_version_id', sa.String(36), nullable=True),
        sa.Column('signature_packet_id', sa.String(36), nullable=True),
        sa.Column('participant_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('punch_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('accepted_by_party_id', sa.String(36), nullable=True),
        sa.Column('evidence_reference', sa.String(300), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='handover_acceptances_pkey'),
        sa.UniqueConstraint('idempotency_key', name='handover_acceptances_idempotency_key_key'),
        sa.UniqueConstraint('handover_package_revision_id', name='uq_handover_acceptance_revision'),
    )
    op.create_table('handover_distribution_requirements',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('handover_package_revision_id', sa.String(36), nullable=False),
        sa.Column('recipient_party_id', sa.String(36), nullable=True),
        sa.Column('recipient_role', sa.String(80), nullable=False),
        sa.Column('medium', sa.String(50), nullable=False),
        sa.Column('copy_type', sa.String(50), nullable=False),
        sa.Column('copy_count', sa.Integer(), nullable=False),
        sa.Column('item_ids_json', sa.JSON(), nullable=False),
        sa.Column('acknowledgement_required', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='handover_distribution_requirements_pkey'),
    )
    op.create_table('handover_distributions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('handover_package_revision_id', sa.String(36), nullable=False),
        sa.Column('distribution_requirement_id', sa.String(36), nullable=True),
        sa.Column('recipient_party_id', sa.String(36), nullable=True),
        sa.Column('recipient_role', sa.String(80), nullable=False),
        sa.Column('medium', sa.String(50), nullable=False),
        sa.Column('copy_type', sa.String(50), nullable=False),
        sa.Column('copy_count', sa.Integer(), nullable=False),
        sa.Column('delivery_reference', sa.String(240), nullable=True),
        sa.Column('evidence_document_version_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('delivered_by', sa.String(200), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='handover_distributions_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_handover_distribution_idempotency'),
    )
    op.create_table('handover_package_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('handover_package_revision_id', sa.String(36), nullable=False),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('item_type', sa.String(80), nullable=False),
        sa.Column('discipline', sa.String(100), nullable=True),
        sa.Column('label', sa.String(240), nullable=False),
        sa.Column('required', sa.Boolean(), nullable=False),
        sa.Column('required_renditions_json', sa.JSON(), nullable=False),
        sa.Column('available_renditions_json', sa.JSON(), nullable=False),
        sa.Column('source_type', sa.String(80), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=True),
        sa.Column('rendered_artifact_id', sa.String(36), nullable=True),
        sa.Column('engineering_revision_id', sa.String(36), nullable=True),
        sa.Column('engineering_rendition_id', sa.String(36), nullable=True),
        sa.Column('as_built_baseline_id', sa.String(36), nullable=True),
        sa.Column('authority_case_id', sa.String(36), nullable=True),
        sa.Column('form_instance_id', sa.String(36), nullable=True),
        sa.Column('source_ref', sa.String(240), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='handover_package_items_pkey'),
        sa.UniqueConstraint('handover_package_revision_id', 'display_order', name='uq_handover_item_order'),
    )
    op.create_table('handover_package_revisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('handover_package_id', sa.String(36), nullable=False),
        sa.Column('service_engagement_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('policy_version_id', sa.String(36), nullable=True),
        sa.Column('authority_case_outcome_id', sa.String(36), nullable=True),
        sa.Column('approved_design_baseline_id', sa.String(36), nullable=True),
        sa.Column('as_built_baseline_id', sa.String(36), nullable=True),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('manifest_hash', sa.String(64), nullable=False),
        sa.Column('participant_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('punch_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('distribution_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('locked_by', sa.String(200), nullable=True),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='handover_package_revisions_pkey'),
        sa.UniqueConstraint('handover_package_id', 'revision_number', name='uq_handover_package_revision_number'),
    )
    op.create_table('handover_packages',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('service_engagement_id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('package_ref', sa.String(120), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('current_revision_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='handover_packages_pkey'),
        sa.UniqueConstraint('service_engagement_id', 'package_ref', name='uq_handover_package_ref'),
    )
    op.create_table('handover_participants',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('handover_package_revision_id', sa.String(36), nullable=False),
        sa.Column('party_id', sa.String(36), nullable=True),
        sa.Column('participant_ref', sa.String(200), nullable=False),
        sa.Column('participant_role', sa.String(80), nullable=False),
        sa.Column('authority_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('required_signer', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='handover_participants_pkey'),
        sa.UniqueConstraint('handover_package_revision_id', 'participant_ref', 'participant_role', name='uq_handover_participant'),
    )
    op.create_table('handover_policy_versions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('policy_code', sa.String(100), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('required_renditions_json', sa.JSON(), nullable=False),
        sa.Column('distribution_rules_json', sa.JSON(), nullable=False),
        sa.Column('acceptance_rules_json', sa.JSON(), nullable=False),
        sa.Column('closeout_rules_json', sa.JSON(), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='handover_policy_versions_pkey'),
        sa.UniqueConstraint('policy_code', 'version', name='uq_handover_policy_version'),
    )
    op.create_table('handover_punch_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('handover_package_revision_id', sa.String(36), nullable=False),
        sa.Column('package_item_id', sa.String(36), nullable=True),
        sa.Column('category', sa.String(80), nullable=False),
        sa.Column('remark', sa.Text(), nullable=False),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('owner_ref', sa.String(200), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('resolution_evidence_document_version_id', sa.String(36), nullable=True),
        sa.Column('resolved_by', sa.String(200), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='handover_punch_items_pkey'),
    )
    op.create_table('handover_readiness',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('handover_package_revision_id', sa.String(36), nullable=False),
        sa.Column('state', sa.String(40), nullable=False),
        sa.Column('digital_ready', sa.Boolean(), nullable=False),
        sa.Column('physical_ready', sa.Boolean(), nullable=False),
        sa.Column('checks_json', sa.JSON(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evaluated_by', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='handover_readiness_pkey'),
        sa.UniqueConstraint('handover_package_revision_id', name='uq_handover_readiness_revision'),
    )
    op.create_table('handover_receipts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('distribution_id', sa.String(36), nullable=False),
        sa.Column('received_by_party_id', sa.String(36), nullable=True),
        sa.Column('received_by_ref', sa.String(200), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_document_version_id', sa.String(36), nullable=True),
        sa.Column('verification_status', sa.String(30), nullable=False),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='handover_receipts_pkey'),
        sa.UniqueConstraint('distribution_id', name='uq_handover_receipt_distribution'),
        sa.UniqueConstraint('idempotency_key', name='uq_handover_receipt_idempotency'),
    )
    op.create_table('handover_release_authorizations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('handover_package_revision_id', sa.String(36), nullable=False),
        sa.Column('readiness_id', sa.String(36), nullable=False),
        sa.Column('authorized_by', sa.String(200), nullable=False),
        sa.Column('authorized_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('delivery_plan_json', sa.JSON(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='handover_release_authorizations_pkey'),
        sa.UniqueConstraint('handover_package_revision_id', name='uq_handover_release_revision'),
    )
    op.create_table('human_monitoring_captures',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('submission_cycle_id', sa.String(36), nullable=True),
        sa.Column('captured_by', sa.String(200), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(80), nullable=False),
        sa.Column('repetition_number', sa.Integer(), nullable=True),
        sa.Column('comments', sa.JSON(), nullable=False),
        sa.Column('evidence_artifact_ids', sa.JSON(), nullable=False),
        sa.Column('verification_mode', sa.String(50), nullable=False),
        sa.Column('evidence_class', sa.String(60), nullable=False),
        sa.PrimaryKeyConstraint('id', name='human_monitoring_captures_pkey'),
    )
    op.create_table('human_portal_verifications',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('verifier', sa.String(200), nullable=False),
        sa.Column('verifier_role', sa.String(100), nullable=False),
        sa.Column('verification_scope', sa.JSON(), nullable=False),
        sa.Column('evidence_artifact_id', sa.String(300), nullable=False),
        sa.Column('result', sa.String(40), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='human_portal_verifications_pkey'),
    )
    op.create_table('human_takeover_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('session_reference', sa.String(100), nullable=True),
        sa.Column('initiated_by', sa.String(200), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('prior_state_hash', sa.String(64), nullable=True),
        sa.Column('reread_required', sa.Boolean(), nullable=False),
        sa.Column('reconciliation_result', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id', name='human_takeover_events_pkey'),
    )
    op.create_table('incident_impact_assessments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('incident_id', sa.String(36), nullable=False),
        sa.Column('source_type', sa.String(100), nullable=False),
        sa.Column('source_id', sa.String(160), nullable=False),
        sa.Column('affected_entities', sa.JSON(), nullable=False),
        sa.Column('lineage_edge_count', sa.Integer(), nullable=False),
        sa.Column('result', sa.String(40), nullable=False),
        sa.Column('assessed_by', sa.String(200), nullable=False),
        sa.Column('assessed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.Column('result_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='incident_impact_assessments_pkey'),
    )
    op.create_table('integrity_incidents',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('incident_type', sa.String(120), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('application_id', sa.String(36), nullable=True),
        sa.Column('source_entity_type', sa.String(100), nullable=True),
        sa.Column('source_entity_id', sa.String(160), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_refs', sa.JSON(), nullable=False),
        sa.Column('notifications', sa.JSON(), nullable=False),
        sa.Column('root_cause_category', sa.String(120), nullable=True),
        sa.Column('corrective_action', sa.Text(), nullable=True),
        sa.Column('residual_risk', sa.Text(), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id', name='integrity_incidents_pkey'),
    )
    op.create_table('invoice_accept_records',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_revision_id', sa.String(36), nullable=False),
        sa.Column('accepted_by', sa.String(200), nullable=False),
        sa.Column('accepted_role', sa.String(80), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.Column('precheck_snapshot', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoice_accept_records_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_invoice_accept_idempotency'),
        sa.UniqueConstraint('invoice_revision_id', name='uq_invoice_accept_revision'),
    )
    op.create_table('invoice_acknowledgments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('issued_revision_id', sa.String(36), nullable=False),
        sa.Column('acknowledgment_reference', sa.String(200), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoice_acknowledgments_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_invoice_acknowledgment_idempotency'),
    )
    op.create_table('invoice_approval_records',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_revision_id', sa.String(36), nullable=False),
        sa.Column('approval_type', sa.String(80), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('approval_reference', sa.String(200), nullable=True),
        sa.Column('approving_party_or_body', sa.String(200), nullable=True),
        sa.Column('decision_date', sa.Date(), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('verified_by', sa.String(200), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoice_approval_records_pkey'),
    )
    op.create_table('invoice_approvals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_revision_id', sa.String(36), nullable=False),
        sa.Column('approval_id', sa.String(36), nullable=False),
        sa.Column('approval_type', sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoice_approvals_pkey'),
        sa.UniqueConstraint('approval_id', name='invoice_approvals_approval_id_key'),
    )
    op.create_table('invoice_delivery_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('issued_revision_id', sa.String(36), nullable=False),
        sa.Column('issue_event_id', sa.String(36), nullable=False),
        sa.Column('channel', sa.String(40), nullable=False),
        sa.Column('recipient_snapshot', sa.JSON(), nullable=False),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('delivery_reference', sa.String(200), nullable=True),
        sa.Column('evidence_document_version_id', sa.String(36), nullable=True),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoice_delivery_events_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_invoice_delivery_idempotency'),
    )
    op.create_table('invoice_issue_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('invoice_revision_id', sa.String(36), nullable=False),
        sa.Column('official_invoice_ref', sa.String(100), nullable=False),
        sa.Column('invoice_date', sa.Date(), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('issued_by', sa.String(200), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.Column('template_version_id', sa.String(36), nullable=False),
        sa.Column('financial_account_version_id', sa.String(36), nullable=False),
        sa.Column('rendered_artifact_id', sa.String(36), nullable=False),
        sa.Column('source_snapshot', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoice_issue_events_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_invoice_issue_idempotency'),
        sa.UniqueConstraint('invoice_id', name='uq_invoice_issue_invoice'),
        sa.UniqueConstraint('official_invoice_ref', name='uq_invoice_issue_reference'),
    )
    op.create_table('invoice_line_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_revision_id', sa.String(36), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('line_role', sa.String(30), nullable=False),
        sa.Column('item_code', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 6), nullable=True),
        sa.Column('unit', sa.String(40), nullable=True),
        sa.Column('unit_price', sa.Numeric(18, 6), nullable=True),
        sa.Column('currency', sa.String(20), nullable=False),
        sa.Column('calculated_line_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('billing_milestone_id', sa.String(36), nullable=True),
        sa.Column('affects_payable_total', sa.Boolean(), nullable=False),
        sa.Column('source_reference', sa.String(300), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoice_line_items_pkey'),
        sa.UniqueConstraint('invoice_revision_id', 'sequence', name='uq_invoice_line_sequence'),
    )
    op.create_table('invoice_milestones',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('contract_milestone_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoice_milestones_pkey'),
    )
    op.create_table('invoice_numbering_policies',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('policy_key', sa.String(80), nullable=False),
        sa.Column('prefix', sa.String(60), nullable=False),
        sa.Column('padding', sa.Integer(), nullable=False),
        sa.Column('next_number', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('no_reuse', sa.Boolean(), nullable=False),
        sa.Column('updated_by', sa.String(200), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoice_numbering_policies_pkey'),
        sa.UniqueConstraint('policy_key', name='invoice_numbering_policies_policy_key_key'),
    )
    op.create_table('invoice_payment_allocations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('payment_receipt_id', sa.String(36), nullable=False),
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('allocated_amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('currency', sa.String(20), nullable=False),
        sa.Column('allocated_by', sa.String(200), nullable=False),
        sa.Column('allocated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoice_payment_allocations_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_invoice_payment_allocation_idempotency'),
    )
    op.create_table('invoice_references',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_revision_id', sa.String(36), nullable=False),
        sa.Column('reference_type', sa.String(80), nullable=False),
        sa.Column('value', sa.String(300), nullable=False),
        sa.Column('issuer_or_source', sa.String(200), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('verified_by', sa.String(200), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoice_references_pkey'),
    )
    op.create_table('invoice_requirement_decisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('milestone_id', sa.String(36), nullable=True),
        sa.Column('decision', sa.String(40), nullable=False),
        sa.Column('decision_source', sa.String(50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('decided_by', sa.String(200), nullable=True),
        sa.Column('rule_id', sa.String(120), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoice_requirement_decisions_pkey'),
    )
    op.create_table('invoice_revisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('controlling_contract_revision_id', sa.String(36), nullable=False),
        sa.Column('billing_plan_revision_id', sa.String(36), nullable=True),
        sa.Column('controlling_milestone_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('supersedes_revision_id', sa.String(36), nullable=True),
        sa.Column('template_version_id', sa.String(36), nullable=True),
        sa.Column('rendered_artifact_id', sa.String(36), nullable=True),
        sa.Column('render_input_hash', sa.String(64), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.Column('source_snapshot', sa.JSON(), nullable=False),
        sa.Column('stale_reason', sa.Text(), nullable=True),
        sa.Column('invoice_date', sa.Date(), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('due_date_basis', sa.String(100), nullable=True),
        sa.Column('due_date_offset_days', sa.Integer(), nullable=True),
        sa.Column('due_date_fixed_date', sa.Date(), nullable=True),
        sa.Column('due_date_status', sa.String(40), nullable=False),
        sa.Column('due_date_source_event_type', sa.String(80), nullable=True),
        sa.Column('due_date_source_event_id', sa.String(36), nullable=True),
        sa.Column('due_date_derived_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('contract_project_context_snapshot', sa.JSON(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('currency', sa.String(20), nullable=True),
        sa.Column('gross_charge_total', sa.Numeric(18, 2), nullable=True),
        sa.Column('adjustment_total', sa.Numeric(18, 2), nullable=True),
        sa.Column('payable_total', sa.Numeric(18, 2), nullable=True),
        sa.Column('amount_in_words', sa.Text(), nullable=True),
        sa.Column('accepted_by', sa.String(200), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoice_revisions_pkey'),
        sa.UniqueConstraint('invoice_id', 'revision_number', name='uq_invoice_revision_number'),
    )
    op.create_table('invoices',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('client_account_id', sa.String(36), nullable=True),
        sa.Column('billing_plan_id', sa.String(36), nullable=True),
        sa.Column('invoice_reference', sa.String(100), nullable=False),
        sa.Column('invoice_ref_status', sa.String(40), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('current_revision_id', sa.String(36), nullable=True),
        sa.Column('requirement_decision_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='invoices_pkey'),
        sa.UniqueConstraint('invoice_reference', name='invoices_invoice_reference_key'),
    )
    op.create_table('jurisdictions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(100), nullable=False),
        sa.Column('country_code', sa.String(8), nullable=False),
        sa.Column('name_en', sa.String(240), nullable=False),
        sa.Column('name_ar', sa.String(240), nullable=True),
        sa.Column('level', sa.String(40), nullable=False),
        sa.Column('parent_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('coverage_json', sa.JSON(), nullable=False),
        sa.Column('provenance_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='jurisdictions_pkey'),
        sa.UniqueConstraint('code', name='uq_jurisdiction_code'),
    )
    op.create_table('kill_switch_readiness',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('environment', sa.String(40), nullable=False),
        sa.Column('mode', sa.String(40), nullable=False),
        sa.Column('write_kill_switch', sa.String(60), nullable=False),
        sa.Column('tested', sa.Boolean(), nullable=False),
        sa.Column('retained_capabilities', sa.JSON(), nullable=False),
        sa.Column('disabled_capabilities', sa.JSON(), nullable=False),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.Column('result_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='kill_switch_readiness_pkey'),
    )
    op.create_table('legacy_fixture_aliases',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('legacy_id', sa.String(160), nullable=False),
        sa.Column('canonical_id', sa.String(160), nullable=False),
        sa.Column('purpose', sa.String(200), nullable=False),
        sa.Column('temporary', sa.Boolean(), nullable=False),
        sa.Column('remove_by', sa.Date(), nullable=True),
        sa.Column('classification', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='legacy_fixture_aliases_pkey'),
        sa.UniqueConstraint('legacy_id', name='legacy_fixture_aliases_legacy_id_key'),
    )
    op.create_table('lineage_edges',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('upstream_type', sa.String(100), nullable=False),
        sa.Column('upstream_id', sa.String(160), nullable=False),
        sa.Column('upstream_version_or_hash', sa.String(160), nullable=True),
        sa.Column('downstream_type', sa.String(100), nullable=False),
        sa.Column('downstream_id', sa.String(160), nullable=False),
        sa.Column('downstream_version_or_hash', sa.String(160), nullable=True),
        sa.Column('dependency_kind', sa.String(60), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id', name='lineage_edges_pkey'),
    )
    op.create_table('master_content_applicability',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('master_content_item_id', sa.String(36), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=False),
        sa.Column('external_body_id', sa.String(36), nullable=False),
        sa.Column('jurisdiction_id', sa.String(36), nullable=True),
        sa.Column('service_type_id', sa.String(36), nullable=False),
        sa.Column('lifecycle_phase_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('confirmed_by', sa.String(200), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('supersedes_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='master_content_applicability_pkey'),
    )
    op.create_table('master_content_change_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('master_content_id', sa.String(36), nullable=True),
        sa.Column('definition_id', sa.String(36), nullable=True),
        sa.Column('previous_version_id', sa.String(36), nullable=True),
        sa.Column('new_version_id', sa.String(36), nullable=False),
        sa.Column('change_type', sa.String(80), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.Column('actor_or_system', sa.String(200), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('content_type', sa.String(40), nullable=True),
        sa.Column('business_ref', sa.String(100), nullable=True),
        sa.Column('category_snapshot', sa.JSON(), nullable=False),
        sa.Column('change_kind', sa.String(40), nullable=True),
        sa.Column('change_reason', sa.String(500), nullable=True),
        sa.Column('materiality', sa.String(30), nullable=False),
        sa.Column('source_hash', sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint('id', name='master_content_change_events_pkey'),
    )
    op.create_table('master_content_dependencies',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('master_content_id', sa.String(36), nullable=False),
        sa.Column('bound_document_version_id', sa.String(36), nullable=False),
        sa.Column('expected_current_version_id', sa.String(36), nullable=False),
        sa.Column('downstream_type', sa.String(100), nullable=False),
        sa.Column('downstream_id', sa.String(160), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('dependency_kind', sa.String(80), nullable=False),
        sa.Column('policy', sa.String(80), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='master_content_dependencies_pkey'),
        sa.UniqueConstraint('master_content_id', 'downstream_type', 'downstream_id', 'dependency_kind', name='uq_master_content_dependency'),
    )
    op.create_table('master_content_event_deliveries',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('event_id', sa.String(36), nullable=False),
        sa.Column('delivery_type', sa.String(60), nullable=False),
        sa.Column('target_type', sa.String(100), nullable=False),
        sa.Column('target_id', sa.String(160), nullable=False),
        sa.Column('recipient_role', sa.String(80), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='master_content_event_deliveries_pkey'),
        sa.UniqueConstraint('event_id', 'delivery_type', 'target_type', 'target_id', 'recipient_role', name='uq_master_content_event_delivery'),
    )
    op.create_table('master_content_governance_profiles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('master_content_item_id', sa.String(36), nullable=False),
        sa.Column('content_ownership_class', sa.String(40), nullable=False),
        sa.Column('artifact_kind', sa.String(60), nullable=False),
        sa.Column('publisher_name', sa.String(240), nullable=True),
        sa.Column('publisher_unit', sa.String(240), nullable=True),
        sa.Column('jurisdiction_text', sa.String(240), nullable=True),
        sa.Column('official_form_no', sa.String(120), nullable=True),
        sa.Column('official_issue_no', sa.String(80), nullable=True),
        sa.Column('official_issue_date', sa.Date(), nullable=True),
        sa.Column('language_profile', sa.String(30), nullable=False),
        sa.Column('sensitivity_class', sa.String(40), nullable=False),
        sa.Column('contains_pii', sa.Boolean(), nullable=False),
        sa.Column('contains_signature', sa.Boolean(), nullable=False),
        sa.Column('contains_stamp', sa.Boolean(), nullable=False),
        sa.Column('contains_financial_data', sa.Boolean(), nullable=False),
        sa.Column('contains_project_specific_data', sa.Boolean(), nullable=False),
        sa.Column('restricted_reference_sample', sa.Boolean(), nullable=False),
        sa.Column('currentness_status', sa.String(40), nullable=False),
        sa.Column('currentness_verified_by', sa.String(200), nullable=True),
        sa.Column('currentness_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('currentness_verification_note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='master_content_governance_profiles_pkey'),
        sa.UniqueConstraint('master_content_item_id', name='uq_master_content_governance_item'),
    )
    op.create_table('master_content_idempotency',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.Column('master_content_id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('result_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='master_content_idempotency_pkey'),
        sa.UniqueConstraint('idempotency_key', name='master_content_idempotency_idempotency_key_key'),
    )
    op.create_table('master_content_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('ref', sa.String(100), nullable=False),
        sa.Column('content_type', sa.String(40), nullable=False),
        sa.Column('title', sa.String(240), nullable=False),
        sa.Column('category_id', sa.String(36), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('used_in', sa.JSON(), nullable=False),
        sa.Column('engineering_metadata', sa.JSON(), nullable=False),
        sa.Column('source_type_code', sa.String(80), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('needs_review', sa.Boolean(), nullable=False),
        sa.Column('review_note', sa.String(500), nullable=True),
        sa.Column('document_id', sa.String(36), nullable=False),
        sa.Column('current_document_version_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='master_content_items_pkey'),
        sa.UniqueConstraint('document_id', name='master_content_items_document_id_key'),
        sa.UniqueConstraint('content_type', 'ref', name='uq_master_content_type_ref'),
    )
    op.create_table('master_content_module_bindings',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('master_content_id', sa.String(36), nullable=True),
        sa.Column('definition_id', sa.String(36), nullable=True),
        sa.Column('module', sa.String(40), nullable=False),
        sa.Column('usage_type', sa.String(50), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='master_content_module_bindings_pkey'),
        sa.CheckConstraint(sa.text('master_content_id IS NOT NULL OR definition_id IS NOT NULL'), name='ck_binding_source_present'),
    )
    op.create_table('master_content_quality_flags',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('master_content_item_id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=True),
        sa.Column('code', sa.String(80), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('evidence_note', sa.Text(), nullable=True),
        sa.Column('recommended_next_action', sa.Text(), nullable=True),
        sa.Column('raised_by', sa.String(200), nullable=False),
        sa.Column('raised_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_by', sa.String(200), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='master_content_quality_flags_pkey'),
    )
    op.create_table('master_content_readiness_assessments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('master_content_item_id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evaluator_version', sa.String(30), nullable=False),
        sa.Column('state', sa.String(30), nullable=False),
        sa.Column('blocking_reasons', sa.JSON(), nullable=False),
        sa.Column('warnings', sa.JSON(), nullable=False),
        sa.Column('dimensions', sa.JSON(), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='master_content_readiness_assessments_pkey'),
    )
    op.create_table('master_content_reference_sequences',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('content_type', sa.String(40), nullable=False),
        sa.Column('prefix', sa.String(20), nullable=False),
        sa.Column('padding', sa.Integer(), nullable=False),
        sa.Column('scope', sa.String(80), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('current_value', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='master_content_reference_sequences_pkey'),
        sa.UniqueConstraint('content_type', 'scope', name='uq_master_content_reference_sequence'),
    )
    op.create_table('master_content_source_provenance',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('obtained_from', sa.String(240), nullable=False),
        sa.Column('obtained_by', sa.String(200), nullable=False),
        sa.Column('obtained_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_reference', sa.String(500), nullable=True),
        sa.Column('ingest_batch', sa.String(160), nullable=True),
        sa.Column('provenance_note', sa.Text(), nullable=True),
        sa.Column('evidence_reference', sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint('id', name='master_content_source_provenance_pkey'),
    )
    op.create_table('master_content_source_sections',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('master_content_item_id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('section_key', sa.String(120), nullable=False),
        sa.Column('label', sa.String(240), nullable=False),
        sa.Column('locator_type', sa.String(40), nullable=False),
        sa.Column('page_start', sa.Integer(), nullable=True),
        sa.Column('page_end', sa.Integer(), nullable=True),
        sa.Column('locator_payload', sa.JSON(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='master_content_source_sections_pkey'),
    )
    op.create_table('material_change_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('source_type', sa.String(100), nullable=False),
        sa.Column('source_id', sa.String(160), nullable=False),
        sa.Column('previous_version_or_hash', sa.String(160), nullable=True),
        sa.Column('new_version_or_hash', sa.String(160), nullable=True),
        sa.Column('change_type', sa.String(100), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actor_or_system', sa.String(200), nullable=False),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('material', sa.Boolean(), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='material_change_events_pkey'),
    )
    op.create_table('mfa_challenge_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('auth_session_id', sa.String(36), nullable=False),
        sa.Column('challenge_type', sa.String(60), nullable=False),
        sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_by_user_id', sa.String(36), nullable=True),
        sa.Column('result', sa.String(30), nullable=False),
        sa.Column('external_reference_hash', sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint('id', name='mfa_challenge_events_pkey'),
    )
    op.create_table('minimum_package_definitions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('required_field_codes', sa.JSON(), nullable=False),
        sa.Column('required_document_rules', sa.JSON(), nullable=False),
        sa.Column('required_attachment_rules', sa.JSON(), nullable=False),
        sa.Column('required_dependency_rules', sa.JSON(), nullable=False),
        sa.Column('required_drawing_controls', sa.JSON(), nullable=False),
        sa.Column('required_human_gates', sa.JSON(), nullable=False),
        sa.Column('unresolved_conflict_policy', sa.String(120), nullable=False),
        sa.Column('package_approver_role', sa.String(100), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='minimum_package_definitions_pkey'),
    )
    op.create_table('ministry_inquiries',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('question_code', sa.String(100), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('NOT_ASKED', 'ASKED', 'ANSWERED', 'NO_RESPONSE', 'NOT_APPLICABLE', name='inquirystatus'), nullable=False),
        sa.Column('client_owner', sa.String(200), nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response_text', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='ministry_inquiries_pkey'),
        sa.UniqueConstraint('question_code', name='ministry_inquiries_question_code_key'),
    )
    op.create_table('monitoring_checks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('monitoring_run_id', sa.String(36), nullable=False),
        sa.Column('operation', sa.String(60), nullable=False),
        sa.Column('prior_fingerprint', sa.String(64), nullable=True),
        sa.Column('current_fingerprint', sa.String(64), nullable=True),
        sa.Column('comparison_result', sa.String(50), nullable=False),
        sa.Column('checked_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_artifact_id', sa.String(300), nullable=True),
        sa.Column('status_code', sa.String(50), nullable=True),
        sa.Column('repetition_number', sa.Integer(), nullable=True),
        sa.Column('comment_count', sa.Integer(), nullable=True),
        sa.Column('normalized_state_hash', sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint('id', name='monitoring_checks_pkey'),
    )
    op.create_table('monitoring_execution_decisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('monitoring_policy_id', sa.String(36), nullable=False),
        sa.Column('run_id', sa.String(36), nullable=True),
        sa.Column('operation', sa.String(60), nullable=False),
        sa.Column('decision', sa.String(40), nullable=False),
        sa.Column('reason_code', sa.String(100), nullable=False),
        sa.Column('policy_version', sa.String(40), nullable=False),
        sa.Column('adapter_version', sa.String(50), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='monitoring_execution_decisions_pkey'),
    )
    op.create_table('monitoring_policies',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=True),
        sa.Column('application_id', sa.String(36), nullable=True),
        sa.Column('environment', sa.String(40), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('evidence_class', sa.String(60), nullable=False),
        sa.Column('operations_allowed', sa.JSON(), nullable=False),
        sa.Column('cadence_mode', sa.String(40), nullable=False),
        sa.Column('cadence_value', sa.Integer(), nullable=True),
        sa.Column('business_hours_policy', sa.JSON(), nullable=True),
        sa.Column('jitter_policy', sa.JSON(), nullable=True),
        sa.Column('max_failures_before_pause', sa.Integer(), nullable=False),
        sa.Column('adapter_id', sa.String(100), nullable=False),
        sa.Column('adapter_version', sa.String(50), nullable=False),
        sa.Column('portal_contract_version', sa.String(50), nullable=False),
        sa.Column('fallback_mode', sa.String(50), nullable=False),
        sa.Column('notification_policy_id', sa.String(100), nullable=True),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('failure_count', sa.Integer(), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='monitoring_policies_pkey'),
    )
    op.create_table('monitoring_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('submission_cycle_id', sa.String(36), nullable=True),
        sa.Column('monitoring_policy_id', sa.String(36), nullable=False),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('environment', sa.String(40), nullable=False),
        sa.Column('adapter_id', sa.String(100), nullable=False),
        sa.Column('adapter_version', sa.String(50), nullable=False),
        sa.Column('portal_contract_version', sa.String(50), nullable=False),
        sa.Column('prior_snapshot_id', sa.String(36), nullable=True),
        sa.Column('new_snapshot_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('result', sa.String(50), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('retry_class', sa.String(60), nullable=True),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='monitoring_runs_pkey'),
    )
    op.create_table('monitoring_state_snapshots',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('monitoring_run_id', sa.String(36), nullable=False),
        sa.Column('capture_method', sa.String(50), nullable=False),
        sa.Column('trusted', sa.Boolean(), nullable=False),
        sa.Column('application_identity', sa.JSON(), nullable=False),
        sa.Column('state', sa.JSON(), nullable=False),
        sa.Column('raw_evidence', sa.JSON(), nullable=False),
        sa.Column('contract_fingerprint', sa.String(64), nullable=False),
        sa.Column('state_hash', sa.String(64), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='monitoring_state_snapshots_pkey'),
    )
    op.create_table('municipality_configs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('tabs_json', sa.JSON(), nullable=False),
        sa.Column('fields_json', sa.JSON(), nullable=False),
        sa.Column('dropdowns_json', sa.JSON(), nullable=False),
        sa.Column('grids_json', sa.JSON(), nullable=False),
        sa.Column('attachments_json', sa.JSON(), nullable=False),
        sa.Column('operations_json', sa.JSON(), nullable=False),
        sa.Column('mfa_mode', sa.String(50), nullable=False),
        sa.Column('attended_session_required', sa.Boolean(), nullable=False),
        sa.Column('session_notes', sa.Text(), nullable=False),
        sa.Column('precheck_json', sa.JSON(), nullable=False),
        sa.Column('submission_confirmation_json', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='municipality_configs_pkey'),
    )
    op.create_table('municipality_drafts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('state_json', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='municipality_drafts_pkey'),
        sa.UniqueConstraint('application_id', name='municipality_drafts_application_id_key'),
    )
    op.create_table('municipality_operation_decisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('operation', sa.String(80), nullable=False),
        sa.Column('selected_mode', sa.Enum('ASSISTED', 'MOCK', 'API', 'BROWSER', 'NOT_SUPPORTED', name='selectedmode'), nullable=False),
        sa.Column('authorization_status', sa.String(40), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('fallback', sa.Text(), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=False),
        sa.Column('decision_owner', sa.String(200), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='municipality_operation_decisions_pkey'),
        sa.UniqueConstraint('operation', name='municipality_operation_decisions_operation_key'),
    )
    op.create_table('municipality_preparation_exceptions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('exception_type', sa.String(80), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('expected', sa.JSON(), nullable=False),
        sa.Column('observed', sa.JSON(), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('owner', sa.String(200), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='municipality_preparation_exceptions_pkey'),
    )
    op.create_table('notification_delivery_attempts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('notification_event_id', sa.String(36), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(40), nullable=False),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('result', sa.String(30), nullable=False),
        sa.Column('failure_code', sa.String(100), nullable=True),
        sa.Column('external_reference', sa.String(200), nullable=True),
        sa.PrimaryKeyConstraint('id', name='notification_delivery_attempts_pkey'),
    )
    op.create_table('notification_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('finding_id', sa.String(36), nullable=True),
        sa.Column('workflow_task_id', sa.String(36), nullable=True),
        sa.Column('recipient_user_id', sa.String(36), nullable=True),
        sa.Column('recipient_role', sa.String(80), nullable=False),
        sa.Column('channel', sa.String(40), nullable=False),
        sa.Column('event_type', sa.String(80), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('subject', sa.String(300), nullable=False),
        sa.Column('body_preview', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('attempted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('failure_code', sa.String(100), nullable=True),
        sa.Column('external_message_reference', sa.String(200), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.Column('domain', sa.String(50), nullable=True),
        sa.Column('proposal_id', sa.String(36), nullable=True),
        sa.Column('contract_id', sa.String(36), nullable=True),
        sa.Column('permit_id', sa.String(36), nullable=True),
        sa.Column('severity', sa.String(30), nullable=True),
        sa.Column('audience', sa.JSON(), nullable=False),
        sa.Column('actor', sa.String(200), nullable=True),
        sa.Column('deep_link', sa.String(300), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='notification_events_pkey'),
    )
    op.create_table('notification_read_states',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('notification_event_id', sa.String(36), nullable=False),
        sa.Column('persona', sa.String(40), nullable=False),
        sa.Column('principal_key', sa.String(160), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='notification_read_states_pkey'),
    )
    op.create_table('office_credentials',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('office_id', sa.String(36), nullable=False),
        sa.Column('credential_type', sa.String(100), nullable=False),
        sa.Column('holder', sa.String(200), nullable=False),
        sa.Column('registration_number', sa.String(120), nullable=False),
        sa.Column('authority', sa.String(200), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('evidence_document_version_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='office_credentials_pkey'),
    )
    op.create_table('operator_exercise_evidence',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('case_id', sa.String(100), nullable=False),
        sa.Column('user_role', sa.String(100), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('fields_count', sa.Integer(), nullable=False),
        sa.Column('grid_rows_count', sa.Integer(), nullable=False),
        sa.Column('attachments_count', sa.Integer(), nullable=False),
        sa.Column('manual_corrections', sa.Integer(), nullable=False),
        sa.Column('portal_mismatches', sa.Integer(), nullable=False),
        sa.Column('time_to_prepare_seconds', sa.Float(), nullable=True),
        sa.Column('time_to_verify_seconds', sa.Float(), nullable=True),
        sa.Column('exceptions', sa.JSON(), nullable=False),
        sa.Column('friction_note', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='operator_exercise_evidence_pkey'),
    )
    op.create_table('operator_task_timings',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_role', sa.String(80), nullable=False),
        sa.Column('scenario_variant', sa.String(100), nullable=False),
        sa.Column('task_type', sa.String(100), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('correction_count', sa.Integer(), nullable=False),
        sa.Column('navigation_count', sa.Integer(), nullable=True),
        sa.Column('evidence_views', sa.Integer(), nullable=True),
        sa.Column('source', sa.String(60), nullable=False),
        sa.PrimaryKeyConstraint('id', name='operator_task_timings_pkey'),
    )
    op.create_table('opportunities',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('office_id', sa.String(36), nullable=False),
        sa.Column('client_account_id', sa.String(36), nullable=True),
        sa.Column('opportunity_reference', sa.String(100), nullable=False),
        sa.Column('title', sa.String(250), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_owner_user_id', sa.String(36), nullable=True),
        sa.Column('stage2_capability_scope', sa.String(100), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('reference_state', sa.String(30), nullable=False),
        sa.Column('proposal_fields_json', sa.JSON(), nullable=False),
        sa.Column('provisional_reference', sa.String(100), nullable=True),
        sa.Column('canonical_project_reference', sa.String(100), nullable=True),
        sa.Column('canonicalized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('canonicalized_by', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='opportunities_pkey'),
        sa.UniqueConstraint('opportunity_reference', name='opportunities_opportunity_reference_key'),
    )
    op.create_table('owner_decision_aliases',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('legacy_key', sa.String(160), nullable=False),
        sa.Column('canonical_key', sa.String(120), nullable=False),
        sa.Column('source_module', sa.String(100), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('migrated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='owner_decision_aliases_pkey'),
        sa.UniqueConstraint('legacy_key', name='uq_owner_decision_legacy_key'),
    )
    op.create_table('owner_decision_history',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('decision_id', sa.String(36), nullable=False),
        sa.Column('decision_key', sa.String(120), nullable=False),
        sa.Column('event_type', sa.String(60), nullable=False),
        sa.Column('before_json', sa.JSON(), nullable=True),
        sa.Column('after_json', sa.JSON(), nullable=True),
        sa.Column('actor_id', sa.String(200), nullable=True),
        sa.Column('actor_role', sa.String(80), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='owner_decision_history_pkey'),
    )
    op.create_table('owner_decisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('decision_key', sa.String(120), nullable=False),
        sa.Column('group_name', sa.String(80), nullable=False),
        sa.Column('title', sa.String(240), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('why', sa.Text(), nullable=False),
        sa.Column('decision_type', sa.String(60), nullable=False),
        sa.Column('blocking_level', sa.String(50), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('proposed_default_json', sa.JSON(), nullable=True),
        sa.Column('effective_value_json', sa.JSON(), nullable=True),
        sa.Column('options_json', sa.JSON(), nullable=False),
        sa.Column('affected_modules_json', sa.JSON(), nullable=False),
        sa.Column('owner_notes', sa.Text(), nullable=True),
        sa.Column('confirmed_by', sa.String(200), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('supersedes_decision_id', sa.String(36), nullable=True),
        sa.Column('system_fact_source', sa.String(300), nullable=True),
        sa.Column('current_system_state_json', sa.JSON(), nullable=False),
        sa.Column('runtime_value_json', sa.JSON(), nullable=True),
        sa.Column('apply_state', sa.String(40), nullable=False),
        sa.Column('runtime_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('legacy_keys_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='owner_decisions_pkey'),
        sa.UniqueConstraint('decision_key', name='uq_owner_decision_key'),
    )
    op.create_table('package_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('package_id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('document_type', sa.String(100), nullable=False),
        sa.Column('attachment_category_code', sa.String(120), nullable=False),
        sa.Column('file_sha256', sa.String(64), nullable=False),
        sa.Column('revision', sa.String(80), nullable=True),
        sa.Column('approval_state', sa.String(40), nullable=False),
        sa.Column('validity_state', sa.String(40), nullable=False),
        sa.Column('source_reason', sa.Text(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='package_items_pkey'),
    )
    op.create_table('package_readiness_evaluations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('minimum_package_definition_version', sa.String(40), nullable=False),
        sa.Column('applicable_rule_set_id', sa.String(36), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('overall_status', sa.String(50), nullable=False),
        sa.Column('blocker_count', sa.Integer(), nullable=False),
        sa.Column('warning_count', sa.Integer(), nullable=False),
        sa.Column('result_hash', sa.String(64), nullable=False),
        sa.Column('configuration_bundle_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='package_readiness_evaluations_pkey'),
    )
    op.create_table('packages',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('package_definition_version', sa.String(40), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('manifest_hash', sa.String(64), nullable=True),
        sa.Column('source_truth_hash', sa.String(64), nullable=False),
        sa.Column('configuration_bundle_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='packages_pkey'),
    )
    op.create_table('parties',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('party_type', sa.String(30), nullable=False),
        sa.Column('name_ar', sa.String(300), nullable=True),
        sa.Column('name_en', sa.String(300), nullable=True),
        sa.Column('identifier_type', sa.String(30), nullable=True),
        sa.Column('identifier_value', sa.String(100), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='parties_pkey'),
    )
    op.create_table('party_role_assignments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('party_id', sa.String(36), nullable=False),
        sa.Column('role_code', sa.String(80), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('source_kind', sa.String(50), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('assigned_by', sa.String(200), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='party_role_assignments_pkey'),
    )
    op.create_table('payment_receipts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('client_account_id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('received_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(18, 2), nullable=False),
        sa.Column('currency', sa.String(20), nullable=False),
        sa.Column('reference', sa.String(200), nullable=False),
        sa.Column('payment_method', sa.String(80), nullable=True),
        sa.Column('evidence_document_version_id', sa.String(36), nullable=True),
        sa.Column('verification_status', sa.String(40), nullable=False),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('verified_by', sa.String(200), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='payment_receipts_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_payment_receipt_idempotency'),
    )
    op.create_table('permit_applications',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('authority', sa.String(150), nullable=False),
        sa.Column('municipality', sa.String(100), nullable=False),
        sa.Column('permit_type', sa.String(100), nullable=False),
        sa.Column('external_request_number', sa.String(100), nullable=False),
        sa.Column('application_status', sa.Enum('DRAFT', 'PREPARING', 'SUBMITTED', 'UNDER_REVIEW', 'RETURNED', 'APPROVED', name='applicationstatus'), nullable=False),
        sa.Column('repetition_count', sa.Integer(), nullable=False),
        sa.Column('last_status_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('controlling_contract_id', sa.String(36), nullable=True),
        sa.Column('workflow_stage', sa.String(60), nullable=True),
        sa.Column('project_sources_confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('project_sources_confirmed_by', sa.String(120), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='permit_applications_pkey'),
        sa.UniqueConstraint('external_request_number', name='permit_applications_external_request_number_key'),
    )
    op.create_table('phase0_decisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('decision', sa.Enum('GO', 'GO_WITH_FALLBACK', 'GO_WITH_REDUCED_DEPTH', 'PAUSE', 'NO_GO', name='phase0decisiontype'), nullable=False),
        sa.Column('decision_date', sa.Date(), nullable=False),
        sa.Column('recommended_by', sa.String(200), nullable=False),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('summary', sa.Text(), nullable=False),
        sa.Column('conditions_json', sa.JSON(), nullable=False),
        sa.Column('blockers_json', sa.JSON(), nullable=False),
        sa.Column('fallbacks_json', sa.JSON(), nullable=False),
        sa.Column('evidence_refs_json', sa.JSON(), nullable=False),
        sa.Column('commercial_effect', sa.Text(), nullable=False),
        sa.Column('next_action', sa.Text(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='phase0_decisions_pkey'),
    )
    op.create_table('phase_baselines',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('phase', sa.Enum('PHASE_0', 'STAGE_2', name='phase'), nullable=False),
        sa.Column('version', sa.String(30), nullable=False),
        sa.Column('status', sa.Enum('WORKING', 'READY_FOR_REVIEW', 'APPROVED', 'APPROVED_WITH_CONDITIONS', 'PAUSED', 'NO_GO', 'SUPERSEDED', name='baselinestatus'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='phase_baselines_pkey'),
    )
    op.create_table('physical_evidence_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('requirement_instance_id', sa.String(36), nullable=True),
        sa.Column('item_type', sa.String(60), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('location', sa.String(240), nullable=True),
        sa.Column('custodian', sa.String(200), nullable=True),
        sa.Column('verified_by', sa.String(200), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='physical_evidence_items_pkey'),
    )
    op.create_table('pilot_cohorts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('super_user_id', sa.String(36), nullable=False),
        sa.Column('preparer_user_ids_json', sa.JSON(), nullable=False),
        sa.Column('process_champion_id', sa.String(36), nullable=False),
        sa.Column('requirement_steward_id', sa.String(36), nullable=False),
        sa.Column('responsible_engineer_id', sa.String(36), nullable=False),
        sa.Column('final_submitter_id', sa.String(36), nullable=False),
        sa.Column('status', sa.Enum('PROPOSED', 'CONFIRMED', name='pilotstatus'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pilot_cohorts_pkey'),
    )
    op.create_table('pilot_workflow_approvals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('user_id', sa.String(36), nullable=False),
        sa.Column('role', sa.String(100), nullable=False),
        sa.Column('scenario_variant', sa.String(100), nullable=False),
        sa.Column('workflow_version', sa.String(40), nullable=False),
        sa.Column('rehearsal_run_id', sa.String(36), nullable=True),
        sa.Column('result', sa.String(60), nullable=False),
        sa.Column('blockers', sa.JSON(), nullable=False),
        sa.Column('comments', sa.Text(), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.Column('client_approved', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='pilot_workflow_approvals_pkey'),
    )
    op.create_table('portal_contract_validation_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('adapter_id', sa.String(100), nullable=False),
        sa.Column('adapter_version', sa.String(50), nullable=False),
        sa.Column('contract_version', sa.String(50), nullable=False),
        sa.Column('environment', sa.String(40), nullable=False),
        sa.Column('test_fixture_version', sa.String(80), nullable=False),
        sa.Column('operations_tested', sa.JSON(), nullable=False),
        sa.Column('pass_count', sa.Integer(), nullable=False),
        sa.Column('fail_count', sa.Integer(), nullable=False),
        sa.Column('result', sa.String(30), nullable=False),
        sa.Column('reviewed_by', sa.String(200), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='portal_contract_validation_runs_pkey'),
    )
    op.create_table('portal_derived_field_reconciliations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('portal_field_code', sa.String(120), nullable=False),
        sa.Column('semantic_field_code', sa.String(120), nullable=False),
        sa.Column('purpose', sa.String(100), nullable=False),
        sa.Column('expected_office_value', sa.JSON(), nullable=False),
        sa.Column('observed_portal_value', sa.JSON(), nullable=False),
        sa.Column('source_mode', sa.String(40), nullable=False),
        sa.Column('field_authority_rule_version', sa.String(40), nullable=True),
        sa.Column('target_rendering_rule_version', sa.String(40), nullable=True),
        sa.Column('result', sa.String(60), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='portal_derived_field_reconciliations_pkey'),
    )
    op.create_table('portal_drift_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('monitoring_run_id', sa.String(36), nullable=True),
        sa.Column('adapter_id', sa.String(100), nullable=False),
        sa.Column('adapter_version', sa.String(50), nullable=False),
        sa.Column('operation', sa.String(60), nullable=False),
        sa.Column('drift_type', sa.String(60), nullable=False),
        sa.Column('expected_fingerprint', sa.String(64), nullable=False),
        sa.Column('observed_fingerprint', sa.String(64), nullable=False),
        sa.Column('evidence_artifact_id', sa.String(300), nullable=True),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('revalidated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('revalidated_by', sa.String(200), nullable=True),
        sa.PrimaryKeyConstraint('id', name='portal_drift_events_pkey'),
    )
    op.create_table('portal_grid_row_intents',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('row_type', sa.String(50), nullable=False),
        sa.Column('canonical_row_id', sa.String(120), nullable=False),
        sa.Column('target_values', sa.JSON(), nullable=False),
        sa.Column('rendering_rule_versions', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('grid_code', sa.String(100), nullable=False),
        sa.Column('parent_canonical_row_id', sa.String(160), nullable=True),
        sa.Column('business_key', sa.String(300), nullable=True),
        sa.Column('source_entity_version', sa.String(160), nullable=True),
        sa.Column('intended_sequence', sa.Integer(), nullable=True),
        sa.Column('row_hash', sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint('id', name='portal_grid_row_intents_pkey'),
    )
    op.create_table('portal_grid_row_observations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('portal_snapshot_id', sa.String(36), nullable=False),
        sa.Column('grid_code', sa.String(100), nullable=False),
        sa.Column('portal_row_id', sa.String(160), nullable=True),
        sa.Column('observed_sequence', sa.Integer(), nullable=False),
        sa.Column('observed_values', sa.JSON(), nullable=False),
        sa.Column('observed_business_key', sa.String(300), nullable=True),
        sa.Column('row_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='portal_grid_row_observations_pkey'),
    )
    op.create_table('portal_intended_states',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('application_identity', sa.JSON(), nullable=False),
        sa.Column('fields', sa.JSON(), nullable=False),
        sa.Column('repeating_rows', sa.JSON(), nullable=False),
        sa.Column('attachments', sa.JSON(), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('state_hash', sa.String(64), nullable=False),
        sa.Column('configuration_bundle_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='portal_intended_states_pkey'),
        sa.UniqueConstraint('preparation_revision_id', name='portal_intended_states_preparation_revision_id_key'),
    )
    op.create_table('portal_read_contracts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('adapter_id', sa.String(100), nullable=False),
        sa.Column('adapter_version', sa.String(50), nullable=False),
        sa.Column('contract_version', sa.String(50), nullable=False),
        sa.Column('operation', sa.String(60), nullable=False),
        sa.Column('expected_route_or_section', sa.String(200), nullable=False),
        sa.Column('expected_field_keys', sa.JSON(), nullable=False),
        sa.Column('expected_status_semantics', sa.JSON(), nullable=False),
        sa.Column('expected_comment_structure', sa.JSON(), nullable=False),
        sa.Column('expected_identity_assertions', sa.JSON(), nullable=False),
        sa.Column('expected_structural_fingerprint', sa.String(64), nullable=False),
        sa.Column('parser_version', sa.String(50), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='portal_read_contracts_pkey'),
    )
    op.create_table('portal_reconciliation_results',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('identity_type', sa.String(50), nullable=False),
        sa.Column('identity_key', sa.String(150), nullable=False),
        sa.Column('expected', sa.JSON(), nullable=False),
        sa.Column('observed', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='portal_reconciliation_results_pkey'),
    )
    op.create_table('portal_snapshots',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('snapshot_type', sa.String(40), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('capture_method', sa.String(40), nullable=False),
        sa.Column('field_state', sa.JSON(), nullable=False),
        sa.Column('grid_state', sa.JSON(), nullable=False),
        sa.Column('attachment_state', sa.JSON(), nullable=False),
        sa.Column('validation_state', sa.JSON(), nullable=False),
        sa.Column('precheck_state', sa.JSON(), nullable=False),
        sa.Column('snapshot_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='portal_snapshots_pkey'),
    )
    op.create_table('portal_structure_fingerprints',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('scope', sa.String(50), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=True),
        sa.Column('contract_version', sa.String(40), nullable=False),
        sa.Column('expected_hash', sa.String(64), nullable=False),
        sa.Column('observed_hash', sa.String(64), nullable=False),
        sa.Column('expected_structure', sa.JSON(), nullable=False),
        sa.Column('observed_structure', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='portal_structure_fingerprints_pkey'),
    )
    op.create_table('portal_validation_finding_rules',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('validation_code', sa.String(120), nullable=False),
        sa.Column('create_finding', sa.Boolean(), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('finding_code_id', sa.String(36), nullable=True),
        sa.Column('owner_role', sa.String(80), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='portal_validation_finding_rules_pkey'),
        sa.UniqueConstraint('validation_code', name='portal_validation_finding_rules_validation_code_key'),
    )
    op.create_table('precheck_clearance_evaluations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('precheck_run_id', sa.String(36), nullable=False),
        sa.Column('blocking_finding_count', sa.Integer(), nullable=False),
        sa.Column('unresolved_blocking_count', sa.Integer(), nullable=False),
        sa.Column('stale_input', sa.Boolean(), nullable=False),
        sa.Column('result', sa.String(60), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evaluation_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='precheck_clearance_evaluations_pkey'),
    )
    op.create_table('precheck_decisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('available', sa.Boolean(), nullable=False),
        sa.Column('trigger_method', sa.String(200), nullable=False),
        sa.Column('capture_method', sa.String(200), nullable=False),
        sa.Column('machine_readable', sa.Boolean(), nullable=False),
        sa.Column('required_before_final_review', sa.Boolean(), nullable=False),
        sa.Column('correction_loop_supported', sa.Boolean(), nullable=False),
        sa.Column('fallback', sa.Text(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='precheck_decisions_pkey'),
    )
    op.create_table('preparation_revisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=True),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('scenario_version', sa.String(40), nullable=False),
        sa.Column('field_authority_version', sa.String(40), nullable=False),
        sa.Column('requirement_config_version', sa.String(40), nullable=False),
        sa.Column('rendering_config_version', sa.String(40), nullable=False),
        sa.Column('package_id', sa.String(36), nullable=True),
        sa.Column('package_manifest_hash', sa.String(64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('configuration_bundle_id', sa.String(36), nullable=True),
        sa.Column('authority_case_id', sa.String(36), nullable=True),
        sa.Column('authority_revision_number', sa.Integer(), nullable=True),
        sa.Column('authority_policy_version_id', sa.String(36), nullable=True),
        sa.Column('authority_approved_design_baseline_id', sa.String(36), nullable=True),
        sa.Column('authority_state', sa.String(40), nullable=True),
        sa.Column('authority_snapshot_hash', sa.String(64), nullable=True),
        sa.Column('authority_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('case_party_snapshot_id', sa.String(36), nullable=True),
        sa.Column('authority_locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('authority_supersedes_revision_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='preparation_revisions_pkey'),
    )
    op.create_table('preparation_snapshots',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('verified_field_values', sa.JSON(), nullable=False),
        sa.Column('rendered_target_values', sa.JSON(), nullable=False),
        sa.Column('repeating_rows', sa.JSON(), nullable=False),
        sa.Column('attachment_manifest', sa.JSON(), nullable=False),
        sa.Column('dependency_state', sa.JSON(), nullable=False),
        sa.Column('human_gate_state', sa.JSON(), nullable=False),
        sa.Column('snapshot_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='preparation_snapshots_pkey'),
        sa.UniqueConstraint('preparation_revision_id', name='preparation_snapshots_preparation_revision_id_key'),
    )
    op.create_table('prior_finding_preventive_checks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('finding_code', sa.String(120), nullable=False),
        sa.Column('prior_finding_ids', sa.JSON(), nullable=False),
        sa.Column('current_affected_object', sa.String(200), nullable=True),
        sa.Column('relevance_result', sa.String(80), nullable=False),
        sa.Column('action', sa.String(80), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.Column('result_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='prior_finding_preventive_checks_pkey'),
    )
    op.create_table('production_mode_decisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('mode', sa.String(40), nullable=False),
        sa.Column('supported_operations', sa.JSON(), nullable=False),
        sa.Column('environment_assumptions', sa.JSON(), nullable=False),
        sa.Column('capability_policy', sa.JSON(), nullable=False),
        sa.Column('observed_quality_performance', sa.JSON(), nullable=False),
        sa.Column('defects', sa.JSON(), nullable=False),
        sa.Column('drift_behavior', sa.Text(), nullable=False),
        sa.Column('mfa_session_behavior', sa.Text(), nullable=False),
        sa.Column('recovery_takeover', sa.Text(), nullable=False),
        sa.Column('residual_risks', sa.JSON(), nullable=False),
        sa.Column('g10_dependencies', sa.JSON(), nullable=False),
        sa.Column('decision', sa.String(80), nullable=False),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint('id', name='production_mode_decisions_pkey'),
    )
    op.create_table('professional_credentials',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('credential_type', sa.String(100), nullable=False),
        sa.Column('holder', sa.String(200), nullable=False),
        sa.Column('registration_number', sa.String(120), nullable=False),
        sa.Column('authority', sa.String(200), nullable=False),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('evidence_document_version_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='professional_credentials_pkey'),
    )
    op.create_table('project_activations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('accepted_proposal_revision_id', sa.String(36), nullable=True),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('project_code', sa.String(80), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('original_start_date', sa.Date(), nullable=False),
        sa.Column('activated_by', sa.String(200), nullable=False),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('audit_metadata', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='project_activations_pkey'),
        sa.UniqueConstraint('project_code', name='project_activations_project_code_key'),
        sa.UniqueConstraint('contract_id', name='uq_project_activation_contract'),
        sa.UniqueConstraint('idempotency_key', name='uq_project_activation_idempotency'),
        sa.UniqueConstraint('project_id', name='uq_project_activation_project'),
    )
    op.create_table('project_administration_records',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('reference_number_id', sa.String(36), nullable=False),
        sa.Column('client_account_id', sa.String(36), nullable=False),
        sa.Column('payment_status', sa.String(50), nullable=False),
        sa.Column('payment_followup_state', sa.String(50), nullable=False),
        sa.Column('project_status', sa.String(50), nullable=False),
        sa.Column('engineer_contact_id', sa.String(36), nullable=True),
        sa.Column('engineer_email_projection', sa.String(200), nullable=True),
        sa.Column('synology_linkage_reference', sa.String(300), nullable=True),
        sa.Column('excel_linkage_reference', sa.String(300), nullable=True),
        sa.Column('last_governed_update_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='project_administration_records_pkey'),
        sa.UniqueConstraint('project_id', name='project_administration_records_project_id_key'),
    )
    op.create_table('project_archive_records',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('assessment_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('archived_by', sa.String(200), nullable=False),
        sa.Column('archived_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='project_archive_records_pkey'),
        sa.UniqueConstraint('project_id', name='uq_project_archive_project'),
    )
    op.create_table('project_artifact_records',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('opportunity_id', sa.String(36), nullable=True),
        sa.Column('contract_id', sa.String(36), nullable=True),
        sa.Column('artifact_type', sa.String(50), nullable=False),
        sa.Column('semantic_class', sa.String(50), nullable=False),
        sa.Column('source_filename', sa.String(300), nullable=False),
        sa.Column('stored_filename', sa.String(300), nullable=False),
        sa.Column('sor_path', sa.String(600), nullable=False),
        sa.Column('source_revision', sa.String(80), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('content_type', sa.String(120), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.String(200), nullable=False),
        sa.Column('folder_template_version', sa.String(60), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=True),
        sa.Column('evidence_artifact_id', sa.String(36), nullable=True),
        sa.Column('supersedes_record_id', sa.String(36), nullable=True),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.Column('verification_state', sa.String(40), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('audit_metadata', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='project_artifact_records_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_project_artifact_idempotency'),
    )
    op.create_table('project_closeout_assessments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('policy_version_id', sa.String(36), nullable=True),
        sa.Column('service_scope_state', sa.String(40), nullable=False),
        sa.Column('handover_state', sa.String(40), nullable=False),
        sa.Column('regulatory_state', sa.String(40), nullable=False),
        sa.Column('contract_admin_state', sa.String(40), nullable=False),
        sa.Column('financial_state', sa.String(40), nullable=False),
        sa.Column('archive_state', sa.String(50), nullable=False),
        sa.Column('axes_json', sa.JSON(), nullable=False),
        sa.Column('assessed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assessed_by', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='project_closeout_assessments_pkey'),
        sa.UniqueConstraint('project_id', name='uq_project_closeout_assessment_project'),
    )
    op.create_table('project_closeout_policy_versions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('policy_code', sa.String(100), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('required_axes_json', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='project_closeout_policy_versions_pkey'),
        sa.UniqueConstraint('policy_code', 'version', name='uq_project_closeout_policy_version'),
    )
    op.create_table('project_engineering_reviews',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('revision_id', sa.String(36), nullable=False),
        sa.Column('review_category_id', sa.String(36), nullable=True),
        sa.Column('review_number', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('started_by', sa.String(200), nullable=False),
        sa.Column('completed_by', sa.String(200), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='project_engineering_reviews_pkey'),
    )
    op.create_table('project_handovers',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('readiness_state', sa.String(50), nullable=False),
        sa.Column('rendered_artifact_id', sa.String(36), nullable=True),
        sa.Column('approval_id', sa.String(36), nullable=True),
        sa.Column('communication_draft_id', sa.String(36), nullable=True),
        sa.Column('readiness_checks', sa.JSON(), nullable=False),
        sa.Column('selected_deliverables', sa.JSON(), nullable=False),
        sa.Column('approval_state', sa.String(50), nullable=False),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('approved_role', sa.String(100), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('release_evidence', sa.JSON(), nullable=False),
        sa.Column('release_evidence_status', sa.String(60), nullable=False),
        sa.Column('stale_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='project_handovers_pkey'),
    )
    op.create_table('project_initiations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('initiation_type', sa.String(40), nullable=False),
        sa.Column('initiation_reference', sa.String(200), nullable=False),
        sa.Column('initiated_by', sa.String(200), nullable=False),
        sa.Column('initiated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='project_initiations_pkey'),
    )
    op.create_table('project_number_reservations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposed_number', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('reserved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_authority', sa.String(100), nullable=False),
        sa.Column('initiation_id', sa.String(36), nullable=True),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='project_number_reservations_pkey'),
        sa.UniqueConstraint('proposed_number', name='project_number_reservations_proposed_number_key'),
    )
    op.create_table('project_status_projections',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('reference_number', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('client', sa.String(250), nullable=False),
        sa.Column('payment', sa.String(100), nullable=False),
        sa.Column('status', sa.String(80), nullable=False),
        sa.Column('engineer_email', sa.String(200), nullable=True),
        sa.Column('workbook_reference', sa.String(200), nullable=False),
        sa.Column('human_owned_cells_protected', sa.Boolean(), nullable=False),
        sa.Column('projected_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='project_status_projections_pkey'),
        sa.UniqueConstraint('project_id', name='project_status_projections_project_id_key'),
    )
    op.create_table('projects',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_number', sa.String(50), nullable=False),
        sa.Column('project_name', sa.String(200), nullable=False),
        sa.Column('office_id', sa.String(36), nullable=False),
        sa.Column('workstream', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('municipality', sa.String(100), nullable=False),
        sa.Column('permit_type', sa.String(100), nullable=False),
        sa.Column('assigned_engineer', sa.String(200), nullable=True),
        sa.Column('project_code', sa.String(80), nullable=True),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('activated_by', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='projects_pkey'),
        sa.UniqueConstraint('project_number', name='projects_project_number_key'),
    )
    op.create_table('properties',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('pin', sa.String(100), nullable=False),
        sa.Column('plot_number', sa.String(100), nullable=False),
        sa.Column('zone', sa.String(100), nullable=True),
        sa.Column('municipality', sa.String(100), nullable=False),
        sa.Column('plan_reference', sa.String(100), nullable=True),
        sa.Column('land_area', sa.Float(), nullable=True),
        sa.Column('land_area_unit', sa.String(20), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('source_observation_id', sa.String(36), nullable=True),
        sa.Column('source_assertion_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='properties_pkey'),
    )
    op.create_table('property_ownerships',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('property_id', sa.String(36), nullable=False),
        sa.Column('party_id', sa.String(36), nullable=False),
        sa.Column('share_numerator', sa.Integer(), nullable=True),
        sa.Column('share_denominator', sa.Integer(), nullable=True),
        sa.Column('normalized_share', sa.Float(), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('source_assertion_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='property_ownerships_pkey'),
    )
    op.create_table('proposal_accepted_revisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('validation_snapshot', sa.JSON(), nullable=False),
        sa.Column('template_ref', sa.String(100), nullable=True),
        sa.Column('template_version_id', sa.String(36), nullable=True),
        sa.Column('template_version', sa.String(40), nullable=True),
        sa.Column('template_hash', sa.String(64), nullable=True),
        sa.Column('checklist_ref', sa.String(100), nullable=True),
        sa.Column('checklist_version_id', sa.String(36), nullable=True),
        sa.Column('checklist_version', sa.String(40), nullable=True),
        sa.Column('checklist_hash', sa.String(64), nullable=True),
        sa.Column('definition_refs', sa.JSON(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('accepted_by', sa.String(200), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('supersedes_revision_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='proposal_accepted_revisions_pkey'),
        sa.UniqueConstraint('proposal_id', 'revision_number', name='uq_proposal_accepted_revision'),
    )
    op.create_table('proposal_assumptions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('category', sa.String(80), nullable=False),
        sa.Column('statement', sa.Text(), nullable=False),
        sa.Column('materiality', sa.String(30), nullable=False),
        sa.Column('source_type', sa.String(40), nullable=False),
        sa.Column('source_reference', sa.String(300), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('acknowledged_by', sa.String(200), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_assumptions_pkey'),
    )
    op.create_table('proposal_client_responses',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('accepted_revision_id', sa.String(36), nullable=True),
        sa.Column('response_type', sa.String(50), nullable=False),
        sa.Column('evidence_reference', sa.String(600), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_client_responses_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_proposal_client_response_idempotency'),
    )
    op.create_table('proposal_commercial_outcomes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('accepted_revision_id', sa.String(36), nullable=True),
        sa.Column('outcome', sa.String(50), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('evidence_reference', sa.String(600), nullable=True),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_commercial_outcomes_pkey'),
        sa.UniqueConstraint('proposal_id', name='uq_proposal_commercial_outcome'),
    )
    op.create_table('proposal_conflicts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('field_code', sa.String(100), nullable=False),
        sa.Column('source_a', sa.String(300), nullable=False),
        sa.Column('value_a', sa.Text(), nullable=True),
        sa.Column('source_b', sa.String(300), nullable=False),
        sa.Column('value_b', sa.Text(), nullable=True),
        sa.Column('materiality', sa.String(30), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('resolver', sa.String(200), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_conflicts_pkey'),
    )
    op.create_table('proposal_contact_contexts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('party_id', sa.String(36), nullable=True),
        sa.Column('display_name', sa.String(240), nullable=True),
        sa.Column('email', sa.String(240), nullable=True),
        sa.Column('mobile', sa.String(80), nullable=True),
        sa.Column('purpose', sa.String(50), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_contact_contexts_pkey'),
        sa.UniqueConstraint('proposal_id', name='uq_proposal_contact_context_proposal'),
    )
    op.create_table('proposal_engineering_contributions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('discipline_code', sa.String(100), nullable=True),
        sa.Column('contribution_type', sa.String(60), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('technical_rule_set_version_id', sa.String(36), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('contributed_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_engineering_contributions_pkey'),
    )
    op.create_table('proposal_expected_input_previews',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('policy_version_ids', sa.JSON(), nullable=False),
        sa.Column('scope_intent_ids', sa.JSON(), nullable=False),
        sa.Column('result_items', sa.JSON(), nullable=False),
        sa.Column('evaluation_context', sa.JSON(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evaluated_by', sa.String(200), nullable=False),
        sa.Column('superseded', sa.Boolean(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_expected_input_previews_pkey'),
    )
    op.create_table('proposal_external_cost_assumptions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('external_body_id', sa.String(36), nullable=True),
        sa.Column('estimated_amount', sa.Float(), nullable=True),
        sa.Column('currency', sa.String(20), nullable=True),
        sa.Column('treatment', sa.String(40), nullable=False),
        sa.Column('source_reference', sa.String(300), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_external_cost_assumptions_pkey'),
    )
    op.create_table('proposal_intake_artifacts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('opportunity_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('opportunity_reference', sa.String(100), nullable=False),
        sa.Column('artifact_type', sa.String(80), nullable=False),
        sa.Column('semantic_class', sa.String(80), nullable=False),
        sa.Column('source_filename', sa.String(300), nullable=False),
        sa.Column('stored_filename', sa.String(300), nullable=False),
        sa.Column('sor_path', sa.String(600), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('content_type', sa.String(120), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('uploaded_by', sa.String(200), nullable=False),
        sa.Column('source_revision', sa.String(80), nullable=True),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.Column('verification_state', sa.String(40), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('evidence_artifact_id', sa.String(36), nullable=True),
        sa.Column('supersedes_artifact_id', sa.String(36), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_intake_artifacts_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_proposal_intake_idempotency'),
    )
    op.create_table('proposal_material_acknowledgments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('target_type', sa.String(40), nullable=False),
        sa.Column('target_id', sa.String(36), nullable=False),
        sa.Column('target_revision_hash', sa.String(64), nullable=False),
        sa.Column('acknowledged_by', sa.String(200), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_material_acknowledgments_pkey'),
        sa.UniqueConstraint('proposal_id', 'target_type', 'target_id', name='uq_proposal_material_ack_target'),
    )
    op.create_table('proposal_notes',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('note_type', sa.String(40), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('entered_by', sa.String(200), nullable=False),
        sa.Column('related_contact', sa.String(240), nullable=True),
        sa.Column('provenance', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_notes_pkey'),
    )
    op.create_table('proposal_output_artifacts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('revision_id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('artifact_type', sa.String(40), nullable=False),
        sa.Column('filename', sa.String(300), nullable=False),
        sa.Column('content_type', sa.String(120), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('storage_reference', sa.String(600), nullable=False),
        sa.Column('lineage', sa.JSON(), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('synthetic_only', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_output_artifacts_pkey'),
        sa.UniqueConstraint('revision_id', 'artifact_type', name='uq_proposal_output_type'),
    )
    op.create_table('proposal_owner_settings',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('setting_key', sa.String(120), nullable=False),
        sa.Column('value_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('updated_by', sa.String(200), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_owner_settings_pkey'),
        sa.UniqueConstraint('setting_key', name='uq_proposal_owner_setting_key'),
    )
    op.create_table('proposal_regulatory_scope_intents',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('proposal_scope_item_id', sa.String(36), nullable=True),
        sa.Column('external_body_id', sa.String(36), nullable=True),
        sa.Column('service_type_id', sa.String(36), nullable=True),
        sa.Column('service_type_version_id', sa.String(36), nullable=True),
        sa.Column('jurisdiction_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('source_type', sa.String(40), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('source_assertion_id', sa.String(36), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('human_confirmed_by', sa.String(200), nullable=True),
        sa.Column('human_confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_regulatory_scope_intents_pkey'),
    )
    op.create_table('proposal_revisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('base_accepted_revision_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('change_summary', sa.JSON(), nullable=False),
        sa.Column('snapshot', sa.JSON(), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='proposal_revisions_pkey'),
        sa.UniqueConstraint('proposal_id', 'revision_number', name='uq_proposal_revision_number'),
    )
    op.create_table('proposal_service_scope_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('service_offering_code', sa.String(100), nullable=True),
        sa.Column('scope_category_code', sa.String(100), nullable=True),
        sa.Column('discipline_code', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('included', sa.Boolean(), nullable=False),
        sa.Column('commercial_treatment', sa.String(40), nullable=False),
        sa.Column('regulatory_service_type_id', sa.String(36), nullable=True),
        sa.Column('external_body_id', sa.String(36), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_service_scope_items_pkey'),
    )
    op.create_table('proposal_site_contexts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('property_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('location_text', sa.String(300), nullable=True),
        sa.Column('plot_text', sa.String(160), nullable=True),
        sa.Column('area_value', sa.Float(), nullable=True),
        sa.Column('area_unit', sa.String(30), nullable=True),
        sa.Column('area_kind', sa.String(50), nullable=False),
        sa.Column('site_description', sa.Text(), nullable=True),
        sa.Column('site_photo_source_link_id', sa.String(36), nullable=True),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('resolution_note', sa.Text(), nullable=True),
        sa.Column('resolved_by', sa.String(200), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('historical_snapshot', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_site_contexts_pkey'),
        sa.UniqueConstraint('proposal_id', name='uq_proposal_site_context_proposal'),
    )
    op.create_table('proposal_source_evidence',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('source_type', sa.String(40), nullable=False),
        sa.Column('source_filename', sa.String(300), nullable=False),
        sa.Column('source_reference', sa.String(600), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('content_type', sa.String(120), nullable=False),
        sa.Column('source_revision', sa.String(80), nullable=True),
        sa.Column('provenance', sa.JSON(), nullable=False),
        sa.Column('conflict_key', sa.String(120), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('verification_state', sa.String(40), nullable=False),
        sa.Column('supersedes_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_source_evidence_pkey'),
        sa.UniqueConstraint('proposal_id', 'source_type', 'content_hash', name='uq_proposal_source_hash'),
    )
    op.create_table('proposal_source_links',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('source_evidence_id', sa.String(36), nullable=True),
        sa.Column('document_id', sa.String(36), nullable=True),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('source_role', sa.String(50), nullable=False),
        sa.Column('added_by', sa.String(200), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_source_links_pkey'),
        sa.UniqueConstraint('proposal_id', 'document_version_id', 'source_role', name='uq_proposal_source_link_version_role'),
    )
    op.create_table('proposal_stakeholder_intents',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('role_code', sa.String(60), nullable=False),
        sa.Column('party_id', sa.String(36), nullable=True),
        sa.Column('display_snapshot', sa.String(300), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('source_type', sa.String(40), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_stakeholder_intents_pkey'),
    )
    op.create_table('proposal_staleness_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('trigger_type', sa.String(80), nullable=False),
        sa.Column('trigger_reference', sa.String(300), nullable=True),
        sa.Column('reason_code', sa.String(100), nullable=False),
        sa.Column('impacted_sections', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('detected_by', sa.String(200), nullable=False),
        sa.Column('cleared_by', sa.String(200), nullable=True),
        sa.Column('cleared_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_staleness_events_pkey'),
    )
    op.create_table('proposal_unknowns',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('proposal_id', sa.String(36), nullable=False),
        sa.Column('category', sa.String(80), nullable=False),
        sa.Column('statement', sa.Text(), nullable=False),
        sa.Column('materiality', sa.String(30), nullable=False),
        sa.Column('source_type', sa.String(40), nullable=False),
        sa.Column('source_reference', sa.String(300), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('resolved_by', sa.String(200), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='proposal_unknowns_pkey'),
    )
    op.create_table('quotation_approvals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('quotation_revision_id', sa.String(36), nullable=False),
        sa.Column('approval_id', sa.String(36), nullable=False),
        sa.Column('approval_type', sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint('id', name='quotation_approvals_pkey'),
        sa.UniqueConstraint('approval_id', name='quotation_approvals_approval_id_key'),
    )
    op.create_table('quotation_field_observations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('quotation_revision_id', sa.String(36), nullable=False),
        sa.Column('field_code', sa.String(80), nullable=False),
        sa.Column('candidate_value', sa.Text(), nullable=True),
        sa.Column('verified_value', sa.Text(), nullable=True),
        sa.Column('proposed_offer_value', sa.Text(), nullable=True),
        sa.Column('approved_offer_value', sa.Text(), nullable=True),
        sa.Column('authority_mode', sa.String(50), nullable=False),
        sa.Column('state', sa.String(40), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('evidence_artifact_id', sa.String(36), nullable=True),
        sa.Column('material', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='quotation_field_observations_pkey'),
    )
    op.create_table('quotation_releases',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('quotation_revision_id', sa.String(36), nullable=False),
        sa.Column('rendered_artifact_id', sa.String(36), nullable=False),
        sa.Column('approval_id', sa.String(36), nullable=False),
        sa.Column('released_by', sa.String(200), nullable=False),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('release_channel_intent', sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint('id', name='quotation_releases_pkey'),
        sa.UniqueConstraint('quotation_revision_id', name='quotation_releases_quotation_revision_id_key'),
    )
    op.create_table('quotation_revisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('quotation_id', sa.String(36), nullable=False),
        sa.Column('revision_number', sa.Integer(), nullable=False),
        sa.Column('source_snapshot', sa.JSON(), nullable=False),
        sa.Column('template_version_id', sa.String(36), nullable=True),
        sa.Column('rendered_artifact_id', sa.String(36), nullable=True),
        sa.Column('render_input_hash', sa.String(64), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('semantic_hash', sa.String(64), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('supersedes_revision_id', sa.String(36), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='quotation_revisions_pkey'),
        sa.UniqueConstraint('quotation_id', 'revision_number', name='uq_quotation_revision_number'),
    )
    op.create_table('quotations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('opportunity_id', sa.String(36), nullable=False),
        sa.Column('quotation_reference', sa.String(100), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('current_revision_id', sa.String(36), nullable=True),
        sa.Column('client_account_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='quotations_pkey'),
        sa.UniqueConstraint('quotation_reference', name='quotations_quotation_reference_key'),
    )
    op.create_table('raid_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('type', sa.Enum('RISK', 'ASSUMPTION', 'ISSUE', 'DEPENDENCY', name='raidtype'), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('owner', sa.String(200), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('mitigation', sa.Text(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('phase0_close_impact', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='raid_items_pkey'),
    )
    op.create_table('readiness_result_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('evaluation_id', sa.String(36), nullable=False),
        sa.Column('requirement_code', sa.String(120), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('evidence_refs', sa.JSON(), nullable=False),
        sa.Column('related_entity_refs', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='readiness_result_items_pkey'),
    )
    op.create_table('real_document_test_gates',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('real_document_test_approved', sa.Boolean(), nullable=False),
        sa.Column('approved_test_location', sa.String(300), nullable=True),
        sa.Column('raw_access_roles', sa.JSON(), nullable=False),
        sa.Column('remote_raw_access_allowed', sa.Boolean(), nullable=False),
        sa.Column('external_ai_allowed', sa.Boolean(), nullable=False),
        sa.Column('approved_ai_provider', sa.String(100), nullable=True),
        sa.Column('approved_region', sa.String(100), nullable=True),
        sa.Column('retention_policy_reference', sa.String(300), nullable=True),
        sa.Column('approval_reference', sa.String(300), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='real_document_test_gates_pkey'),
    )
    op.create_table('receivable_follow_ups',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('invoice_id', sa.String(36), nullable=False),
        sa.Column('follow_up_date', sa.Date(), nullable=False),
        sa.Column('channel', sa.String(60), nullable=False),
        sa.Column('contact_party_id', sa.String(36), nullable=True),
        sa.Column('note', sa.Text(), nullable=False),
        sa.Column('outcome', sa.String(120), nullable=True),
        sa.Column('next_follow_up_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recorded_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='receivable_follow_ups_pkey'),
    )
    op.create_table('recovery_manifests',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('environment', sa.String(40), nullable=False),
        sa.Column('backup_set_id', sa.String(160), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('database_backup_ref', sa.String(300), nullable=False),
        sa.Column('evidence_store_backup_ref', sa.String(300), nullable=True),
        sa.Column('config_snapshot_ref', sa.String(300), nullable=False),
        sa.Column('schema_migration_head', sa.String(80), nullable=False),
        sa.Column('fixture_manifest_hash', sa.String(64), nullable=False),
        sa.Column('config_manifest_hash', sa.String(64), nullable=False),
        sa.Column('encryption_handling_status', sa.String(100), nullable=False),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint('id', name='recovery_manifests_pkey'),
    )
    op.create_table('reference_numbers',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('reference_value', sa.String(100), nullable=False),
        sa.Column('reference_type', sa.String(50), nullable=False),
        sa.Column('opportunity_id', sa.String(36), nullable=True),
        sa.Column('quotation_id', sa.String(36), nullable=True),
        sa.Column('contract_id', sa.String(36), nullable=True),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('permit_application_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('reserved_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='reference_numbers_pkey'),
        sa.UniqueConstraint('reference_value', name='reference_numbers_reference_value_key'),
    )
    op.create_table('regulation_applicabilities',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('regulation_version_id', sa.String(36), nullable=False),
        sa.Column('context_type', sa.String(80), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('discipline', sa.String(100), nullable=False),
        sa.Column('applicability_status', sa.String(60), nullable=False),
        sa.Column('approved_by_user_id', sa.String(36), nullable=True),
        sa.Column('approval_id', sa.String(36), nullable=True),
        sa.Column('effective_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('review_scope_id', sa.String(36), nullable=True),
        sa.Column('basis_evidence', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='regulation_applicabilities_pkey'),
    )
    op.create_table('regulation_sources',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('source_code', sa.String(100), nullable=False),
        sa.Column('title', sa.String(250), nullable=False),
        sa.Column('jurisdiction', sa.String(100), nullable=False),
        sa.Column('authority_name', sa.String(200), nullable=False),
        sa.Column('source_type', sa.String(50), nullable=False),
        sa.Column('publication_state', sa.String(60), nullable=False),
        sa.PrimaryKeyConstraint('id', name='regulation_sources_pkey'),
        sa.UniqueConstraint('source_code', name='regulation_sources_source_code_key'),
    )
    op.create_table('regulation_versions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('regulation_source_id', sa.String(36), nullable=False),
        sa.Column('edition', sa.String(100), nullable=False),
        sa.Column('version', sa.String(100), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('source_uri_or_reference', sa.String(300), nullable=True),
        sa.Column('content_status', sa.String(60), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=True),
        sa.PrimaryKeyConstraint('id', name='regulation_versions_pkey'),
    )
    op.create_table('regulatory_closeout_assessments',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('service_engagement_id', sa.String(36), nullable=True),
        sa.Column('state', sa.String(50), nullable=False),
        sa.Column('authority_case_ids_json', sa.JSON(), nullable=False),
        sa.Column('blocking_case_ids_json', sa.JSON(), nullable=False),
        sa.Column('assessment_json', sa.JSON(), nullable=False),
        sa.Column('assessed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('assessed_by', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='regulatory_closeout_assessments_pkey'),
    )
    op.create_table('regulatory_journeys',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('journey_code', sa.String(100), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('service_type_id', sa.String(36), nullable=False),
        sa.Column('jurisdiction_id', sa.String(36), nullable=False),
        sa.Column('external_body_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='regulatory_journeys_pkey'),
        sa.UniqueConstraint('journey_code', name='uq_regulatory_journey_code'),
    )
    op.create_table('regulatory_lifecycle_phases',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(60), nullable=False),
        sa.Column('name_en', sa.String(160), nullable=False),
        sa.Column('name_ar', sa.String(160), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='regulatory_lifecycle_phases_pkey'),
        sa.UniqueConstraint('code', name='uq_regulatory_phase_code'),
    )
    op.create_table('regulatory_relations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('source_type', sa.String(60), nullable=False),
        sa.Column('source_id', sa.String(36), nullable=False),
        sa.Column('relation_type', sa.String(60), nullable=False),
        sa.Column('target_type', sa.String(60), nullable=False),
        sa.Column('target_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='regulatory_relations_pkey'),
        sa.UniqueConstraint('source_type', 'source_id', 'relation_type', 'target_type', 'target_id', name='uq_regulatory_relation'),
    )
    op.create_table('rendered_artifacts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('template_version_id', sa.String(36), nullable=False),
        sa.Column('context_type', sa.String(80), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('artifact_type', sa.String(80), nullable=False),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('storage_reference', sa.String(300), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('render_input_hash', sa.String(64), nullable=True),
        sa.Column('source_revision_ids', sa.JSON(), nullable=False),
        sa.Column('rendered_values', sa.JSON(), nullable=False),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('synthetic_only', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='rendered_artifacts_pkey'),
    )
    op.create_table('rendered_forms',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('package_id', sa.String(36), nullable=True),
        sa.Column('template_version_id', sa.String(36), nullable=False),
        sa.Column('rendering_rule_versions', sa.JSON(), nullable=False),
        sa.Column('input_truth_hash', sa.String(64), nullable=False),
        sa.Column('output_file_hash', sa.String(64), nullable=False),
        sa.Column('rendered_values', sa.JSON(), nullable=False),
        sa.Column('review_state', sa.String(40), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('configuration_bundle_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='rendered_forms_pkey'),
    )
    op.create_table('representations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('principal_party_id', sa.String(36), nullable=False),
        sa.Column('representative_party_id', sa.String(36), nullable=False),
        sa.Column('authorization_type', sa.String(100), nullable=False),
        sa.Column('scope', sa.Text(), nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('evidence_document_version_id', sa.String(36), nullable=True),
        sa.Column('authorization_id', sa.String(36), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='representations_pkey'),
    )
    op.create_table('requirement_applicability_decisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('policy_item_id', sa.String(36), nullable=False),
        sa.Column('context_type', sa.String(50), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('value', sa.String(30), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('authority', sa.String(200), nullable=True),
        sa.Column('decided_by', sa.String(200), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='requirement_applicability_decisions_pkey'),
    )
    op.create_table('requirement_configs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('requirement_code', sa.String(100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('requirement_type', sa.Enum('DOCUMENT', 'FIELD', 'DEPENDENCY', 'ATTACHMENT', 'PORTAL_SECTION', 'HUMAN_DECISION', name='requirementtype'), nullable=False),
        sa.Column('applicability_expression_json', sa.JSON(), nullable=False),
        sa.Column('required_document_type', sa.String(100), nullable=True),
        sa.Column('required_dependency_type', sa.String(100), nullable=True),
        sa.Column('human_decision_required', sa.Boolean(), nullable=False),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('PROVISIONAL', 'CONFIRMED', 'NEEDS_DECISION', name='configstatus'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='requirement_configs_pkey'),
    )
    op.create_table('requirement_decisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('policy_item_id', sa.String(36), nullable=False),
        sa.Column('context_type', sa.String(50), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('decision_type', sa.String(30), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('authority', sa.String(200), nullable=True),
        sa.Column('policy_version_id', sa.String(36), nullable=False),
        sa.Column('decided_by', sa.String(200), nullable=False),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='requirement_decisions_pkey'),
    )
    op.create_table('requirement_definitions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(120), nullable=False),
        sa.Column('name_en', sa.String(240), nullable=False),
        sa.Column('name_ar', sa.String(240), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('kind', sa.String(50), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='requirement_definitions_pkey'),
        sa.UniqueConstraint('code', name='uq_requirement_definition_code'),
    )
    op.create_table('requirement_evaluations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('policy_version_id', sa.String(36), nullable=False),
        sa.Column('policy_item_id', sa.String(36), nullable=False),
        sa.Column('context_type', sa.String(50), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('applicability', sa.String(30), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_summary', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='requirement_evaluations_pkey'),
    )
    op.create_table('requirement_evidence_constraints',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('policy_item_id', sa.String(36), nullable=False),
        sa.Column('copy_type', sa.String(40), nullable=True),
        sa.Column('side_requirement', sa.String(30), nullable=True),
        sa.Column('min_count', sa.Integer(), nullable=True),
        sa.Column('allowed_formats', sa.JSON(), nullable=False),
        sa.Column('freshness_days', sa.Integer(), nullable=True),
        sa.Column('validity_days', sa.Integer(), nullable=True),
        sa.Column('signature_roles', sa.JSON(), nullable=False),
        sa.Column('stamp_roles', sa.JSON(), nullable=False),
        sa.Column('accreditation', sa.String(160), nullable=True),
        sa.Column('approval_authority', sa.String(160), nullable=True),
        sa.Column('extra_constraints', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='requirement_evidence_constraints_pkey'),
        sa.UniqueConstraint('policy_item_id', name='uq_requirement_evidence_constraint_item'),
    )
    op.create_table('requirement_evidence_evaluations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('requirement_evaluation_id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=True),
        sa.Column('evidence_ref', sa.String(240), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('details_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='requirement_evidence_evaluations_pkey'),
    )
    op.create_table('requirement_groups',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('policy_version_id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(100), nullable=False),
        sa.Column('group_type', sa.String(30), nullable=False),
        sa.Column('min_count', sa.Integer(), nullable=True),
        sa.Column('label', sa.String(240), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='requirement_groups_pkey'),
        sa.UniqueConstraint('policy_version_id', 'code', name='uq_requirement_group_code'),
    )
    op.create_table('requirement_instances',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('policy_version_id', sa.String(36), nullable=False),
        sa.Column('policy_item_id', sa.String(36), nullable=False),
        sa.Column('requirement_definition_id', sa.String(36), nullable=False),
        sa.Column('group_id', sa.String(36), nullable=True),
        sa.Column('lifecycle_phase_id', sa.String(36), nullable=True),
        sa.Column('purpose', sa.String(50), nullable=False),
        sa.Column('applicability', sa.String(30), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('dependency_state', sa.String(30), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('source_snapshot', sa.JSON(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evaluated_by', sa.String(200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='requirement_instances_pkey'),
        sa.UniqueConstraint('authority_case_id', 'policy_item_id', name='uq_requirement_instance_case_policy_item'),
    )
    op.create_table('requirement_matrix_coverage',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(120), nullable=False),
        sa.Column('scenario_version', sa.String(80), nullable=False),
        sa.Column('total_requirements', sa.Integer(), nullable=False),
        sa.Column('complete', sa.Integer(), nullable=False),
        sa.Column('incomplete', sa.Integer(), nullable=False),
        sa.Column('blocked_external', sa.Integer(), nullable=False),
        sa.Column('not_applicable', sa.Integer(), nullable=False),
        sa.Column('unknown', sa.Integer(), nullable=False),
        sa.Column('coverage_percent', sa.Integer(), nullable=False),
        sa.Column('missing_attributes', sa.JSON(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='requirement_matrix_coverage_pkey'),
    )
    op.create_table('requirement_policy_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('policy_version_id', sa.String(36), nullable=False),
        sa.Column('requirement_definition_id', sa.String(36), nullable=False),
        sa.Column('phase_id', sa.String(36), nullable=True),
        sa.Column('group_id', sa.String(36), nullable=True),
        sa.Column('applicability_expression', sa.JSON(), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('source_section_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='requirement_policy_items_pkey'),
    )
    op.create_table('requirement_policy_lineage',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('policy_version_id', sa.String(36), nullable=False),
        sa.Column('master_content_item_id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('source_section_id', sa.String(36), nullable=True),
        sa.Column('relation_type', sa.String(40), nullable=False),
        sa.Column('source_role', sa.String(40), nullable=False),
        sa.Column('governance_status', sa.String(30), nullable=False),
        sa.Column('governance_note', sa.Text(), nullable=True),
        sa.Column('confirmed_by', sa.String(200), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='requirement_policy_lineage_pkey'),
    )
    op.create_table('requirement_policy_versions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('service_type_id', sa.String(36), nullable=False),
        sa.Column('jurisdiction_id', sa.String(36), nullable=True),
        sa.Column('external_body_id', sa.String(36), nullable=True),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('purpose', sa.String(50), nullable=False),
        sa.Column('provenance_json', sa.JSON(), nullable=False),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('supersedes_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='requirement_policy_versions_pkey'),
    )
    op.create_table('restore_rehearsals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('recovery_manifest_id', sa.String(36), nullable=False),
        sa.Column('rehearsal_type', sa.String(60), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result', sa.String(40), nullable=False),
        sa.Column('checks', sa.JSON(), nullable=False),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.Column('not_formal_g10', sa.Boolean(), nullable=False),
        sa.Column('result_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='restore_rehearsals_pkey'),
    )
    op.create_table('resubmission_readiness_evaluations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('submission_cycle_id', sa.String(36), nullable=True),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('package_id', sa.String(36), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('overall_status', sa.String(60), nullable=False),
        sa.Column('blocking_finding_count', sa.Integer(), nullable=False),
        sa.Column('allowed_dispute_count', sa.Integer(), nullable=False),
        sa.Column('package_status', sa.String(50), nullable=True),
        sa.Column('precheck_status', sa.String(60), nullable=True),
        sa.Column('dependency_validity_status', sa.String(60), nullable=True),
        sa.Column('approval_status', sa.String(60), nullable=True),
        sa.Column('portal_reconciliation_status', sa.String(60), nullable=True),
        sa.Column('reasons', sa.JSON(), nullable=False),
        sa.Column('evaluation_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='resubmission_readiness_evaluations_pkey'),
    )
    op.create_table('rfqs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('opportunity_id', sa.String(36), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('sender_reference', sa.String(200), nullable=True),
        sa.Column('source_reference', sa.String(200), nullable=True),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='rfqs_pkey'),
    )
    op.create_table('role_readiness_matrix',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('role', sa.String(100), nullable=False),
        sa.Column('training_material_exists', sa.Boolean(), nullable=False),
        sa.Column('rehearsal_performed', sa.Boolean(), nullable=False),
        sa.Column('competency_evidence', sa.Text(), nullable=False),
        sa.Column('open_questions', sa.JSON(), nullable=False),
        sa.Column('client_approved', sa.Boolean(), nullable=False),
        sa.Column('g10_impact', sa.String(100), nullable=False),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint('id', name='role_readiness_matrix_pkey'),
    )
    op.create_table('role_training_checklists',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('role', sa.String(100), nullable=False),
        sa.Column('checklist_version', sa.String(40), nullable=False),
        sa.Column('boundaries', sa.JSON(), nullable=False),
        sa.Column('evidence_requirements', sa.JSON(), nullable=False),
        sa.Column('stop_conditions', sa.JSON(), nullable=False),
        sa.Column('escalation_route', sa.String(200), nullable=False),
        sa.Column('evidence_class', sa.String(80), nullable=False),
        sa.PrimaryKeyConstraint('id', name='role_training_checklists_pkey'),
    )
    op.create_table('rule_candidates',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('source_finding_id', sa.String(36), nullable=False),
        sa.Column('proposed_control_area', sa.String(120), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('status', sa.String(60), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='rule_candidates_pkey'),
    )
    op.create_table('scenario_configs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_code', sa.String(100), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('version', sa.String(30), nullable=False),
        sa.Column('office_workstream', sa.String(200), nullable=False),
        sa.Column('municipality', sa.String(100), nullable=False),
        sa.Column('permit_type', sa.String(100), nullable=False),
        sa.Column('application_transaction_type', sa.String(100), nullable=False),
        sa.Column('supported_owner_variants', sa.JSON(), nullable=False),
        sa.Column('supported_languages', sa.JSON(), nullable=False),
        sa.Column('supported_complexity_notes', sa.Text(), nullable=False),
        sa.Column('interaction_mode', sa.Enum('ASSISTED', 'API_CANDIDATE', 'BROWSER_CANDIDATE', 'MOCK', 'NOT_SUPPORTED', name='interactionmode'), nullable=False),
        sa.Column('status', sa.Enum('PROVISIONAL', 'CONFIRMED', 'NEEDS_DECISION', name='configstatus'), nullable=False),
        sa.PrimaryKeyConstraint('id', name='scenario_configs_pkey'),
        sa.UniqueConstraint('scenario_code', name='scenario_configs_scenario_code_key'),
    )
    op.create_table('scenario_variants',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('variant_code', sa.String(100), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('applicability', sa.JSON(), nullable=False),
        sa.Column('canonical_fixture_project_id', sa.String(36), nullable=True),
        sa.Column('included', sa.Boolean(), nullable=False),
        sa.Column('signed_scope_basis', sa.String(300), nullable=False),
        sa.Column('rule_set_version', sa.String(50), nullable=False),
        sa.Column('field_set_version', sa.String(50), nullable=False),
        sa.Column('rendering_set_version', sa.String(50), nullable=False),
        sa.Column('attachment_rule_set_version', sa.String(50), nullable=False),
        sa.Column('grid_rule_set_version', sa.String(50), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='scenario_variants_pkey'),
    )
    op.create_table('semantic_key_definitions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('semantic_key', sa.String(200), nullable=False),
        sa.Column('value_type', sa.String(40), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('consequential', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='semantic_key_definitions_pkey'),
        sa.UniqueConstraint('semantic_key', name='uq_semantic_key'),
    )
    op.create_table('semantic_value_assertions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('semantic_key_id', sa.String(36), nullable=False),
        sa.Column('context_type', sa.String(50), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('value_json', sa.JSON(), nullable=False),
        sa.Column('value_type', sa.String(40), nullable=False),
        sa.Column('source_type', sa.String(60), nullable=False),
        sa.Column('source_id', sa.String(36), nullable=False),
        sa.Column('source_version', sa.String(80), nullable=True),
        sa.Column('verification_status', sa.String(40), nullable=False),
        sa.Column('authority', sa.String(200), nullable=True),
        sa.Column('effective_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('asserted_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='semantic_value_assertions_pkey'),
    )
    op.create_table('service_engagements',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('proposal_scope_item_id', sa.String(36), nullable=True),
        sa.Column('service_ref', sa.String(120), nullable=False),
        sa.Column('service_offering_code', sa.String(100), nullable=False),
        sa.Column('scope_category_code', sa.String(100), nullable=True),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='service_engagements_pkey'),
        sa.UniqueConstraint('project_id', 'contract_id', 'service_ref', name='uq_service_engagement_ref'),
    )
    op.create_table('service_scope_closures',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('service_engagement_id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('contract_id', sa.String(36), nullable=False),
        sa.Column('contract_revision_id', sa.String(36), nullable=False),
        sa.Column('handover_package_revision_id', sa.String(36), nullable=False),
        sa.Column('handover_acceptance_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('closure_basis', sa.String(120), nullable=False),
        sa.Column('closed_by', sa.String(200), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='service_scope_closures_pkey'),
        sa.UniqueConstraint('service_engagement_id', name='uq_service_scope_closure_engagement'),
    )
    op.create_table('service_type_versions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('service_type_id', sa.String(36), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('provenance_json', sa.JSON(), nullable=False),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='service_type_versions_pkey'),
        sa.UniqueConstraint('service_type_id', 'version', name='uq_service_type_version'),
    )
    op.create_table('service_types',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(100), nullable=False),
        sa.Column('name_en', sa.String(240), nullable=False),
        sa.Column('name_ar', sa.String(240), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('current_version_id', sa.String(36), nullable=True),
        sa.Column('provenance_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='service_types_pkey'),
        sa.UniqueConstraint('code', name='uq_service_type_code'),
    )
    op.create_table('shadow_corrections',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=True),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('entity_type', sa.String(100), nullable=False),
        sa.Column('field_or_category', sa.String(160), nullable=False),
        sa.Column('proposed_value', sa.JSON(), nullable=False),
        sa.Column('approved_human_value', sa.JSON(), nullable=False),
        sa.Column('correction_type', sa.String(80), nullable=False),
        sa.Column('root_cause_category', sa.String(80), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_artifact_id', sa.String(300), nullable=True),
        sa.PrimaryKeyConstraint('id', name='shadow_corrections_pkey'),
    )
    op.create_table('shadow_defect_dispositions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('defect_id', sa.String(100), nullable=False),
        sa.Column('severity', sa.String(20), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('affected_requirement', sa.String(100), nullable=False),
        sa.Column('scenario_variant', sa.String(100), nullable=False),
        sa.Column('root_cause', sa.String(160), nullable=False),
        sa.Column('status', sa.String(50), nullable=False),
        sa.Column('owner', sa.String(200), nullable=False),
        sa.Column('fix', sa.Text(), nullable=False),
        sa.Column('test_reference', sa.String(300), nullable=False),
        sa.Column('acceptance_impact', sa.String(100), nullable=False),
        sa.Column('g10_impact', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id', name='shadow_defect_dispositions_pkey'),
    )
    op.create_table('signature_packets',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('form_instance_id', sa.String(36), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('signer_refs', sa.JSON(), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='signature_packets_pkey'),
    )
    op.create_table('signoff_c_proposals',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('stage2_baseline_id', sa.String(36), nullable=False),
        sa.Column('version', sa.String(30), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'READY_FOR_COMMERCIAL_REVIEW', 'ISSUED', 'SIGNED', 'DECLINED', name='signoffstatus'), nullable=False),
        sa.Column('scope_summary', sa.Text(), nullable=False),
        sa.Column('capability_depth_json', sa.JSON(), nullable=False),
        sa.Column('delivery_scenario', sa.String(100), nullable=False),
        sa.Column('schedule_json', sa.JSON(), nullable=False),
        sa.Column('fixed_price_qar', sa.Float(), nullable=True),
        sa.Column('payment_plan_json', sa.JSON(), nullable=False),
        sa.Column('holdback_percent', sa.Float(), nullable=False),
        sa.Column('client_staffing_json', sa.JSON(), nullable=False),
        sa.Column('technical_thresholds_json', sa.JSON(), nullable=False),
        sa.Column('remediation_commitment', sa.Text(), nullable=False),
        sa.Column('g10_conditions_json', sa.JSON(), nullable=False),
        sa.Column('hypercare_weeks', sa.Integer(), nullable=False),
        sa.Column('operational_observation_days', sa.Integer(), nullable=False),
        sa.Column('support_terms', sa.Text(), nullable=False),
        sa.Column('warranty_terms', sa.Text(), nullable=False),
        sa.Column('maintenance_terms', sa.Text(), nullable=False),
        sa.Column('ip_terms', sa.Text(), nullable=False),
        sa.Column('data_exit_terms', sa.Text(), nullable=False),
        sa.Column('exclusions_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='signoff_c_proposals_pkey'),
    )
    op.create_table('source_intake_batches',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('source_kind', sa.String(40), nullable=False),
        sa.Column('source_display_name', sa.String(300), nullable=False),
        sa.Column('source_archive_hash', sa.String(64), nullable=False),
        sa.Column('source_location_reference', sa.String(700), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('received_by', sa.String(200), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('item_count_discovered', sa.Integer(), nullable=False),
        sa.Column('empty_folder_count_observed', sa.Integer(), nullable=False),
        sa.Column('manifest_version', sa.String(40), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_summary', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='source_intake_batches_pkey'),
        sa.UniqueConstraint('source_archive_hash', 'source_location_reference', name='uq_source_intake_batch_source'),
    )
    op.create_table('source_intake_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('batch_id', sa.String(36), nullable=False),
        sa.Column('source_ordinal', sa.Integer(), nullable=False),
        sa.Column('original_relative_path', sa.String(700), nullable=False),
        sa.Column('original_filename', sa.String(300), nullable=True),
        sa.Column('normalized_safe_path', sa.String(700), nullable=False),
        sa.Column('size_bytes', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(64), nullable=True),
        sa.Column('media_type', sa.String(120), nullable=True),
        sa.Column('source_mtime', sa.String(80), nullable=True),
        sa.Column('source_locator', sa.String(900), nullable=True),
        sa.Column('disposition', sa.String(50), nullable=True),
        sa.Column('disposition_reason', sa.Text(), nullable=True),
        sa.Column('duplicate_group', sa.String(120), nullable=True),
        sa.Column('promotion_status', sa.String(40), nullable=False),
        sa.Column('target_master_content_id', sa.String(36), nullable=True),
        sa.Column('target_document_version_id', sa.String(36), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='source_intake_items_pkey'),
        sa.UniqueConstraint('batch_id', 'source_ordinal', 'original_relative_path', name='uq_source_intake_item_identity'),
    )
    op.create_table('spike_document_results',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('spike_run_id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('expected_class', sa.String(100), nullable=False),
        sa.Column('predicted_class', sa.String(100), nullable=False),
        sa.Column('result', sa.String(30), nullable=False),
        sa.Column('critical_fields_json', sa.JSON(), nullable=False),
        sa.Column('corrections', sa.Integer(), nullable=False),
        sa.Column('verification_time_seconds', sa.Float(), nullable=False),
        sa.Column('evidence_usability', sa.Enum('GOOD', 'USABLE', 'POOR', 'MISSING', name='evidenceusability'), nullable=False),
        sa.Column('failure_mode', sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint('id', name='spike_document_results_pkey'),
    )
    op.create_table('spike_field_results',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('spike_run_id', sa.String(36), nullable=False),
        sa.Column('field_code', sa.String(120), nullable=False),
        sa.Column('samples', sa.Integer(), nullable=False),
        sa.Column('correct_candidate', sa.Integer(), nullable=False),
        sa.Column('wrong_candidate', sa.Integer(), nullable=False),
        sa.Column('missing_candidate', sa.Integer(), nullable=False),
        sa.Column('keyed', sa.Integer(), nullable=False),
        sa.Column('corrected', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='spike_field_results_pkey'),
    )
    op.create_table('stage2_baselines',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('version', sa.String(30), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('status', sa.Enum('DRAFT', 'READY_FOR_REVIEW', 'APPROVED', 'APPROVED_WITH_CONDITIONS', 'REJECTED', name='stage2status'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('scenario_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('tier1_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('threshold_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('municipality_mode_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('data_delivery_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('security_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('pilot_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('acceptance_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('tier2_backlog_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('business_kpi_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('decision_log_snapshot_json', sa.JSON(), nullable=False),
        sa.Column('checksum', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='stage2_baselines_pkey'),
    )
    op.create_table('stage2_review_acknowledgements',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('baseline_id', sa.String(36), nullable=False),
        sa.Column('reviewer_role', sa.String(100), nullable=False),
        sa.Column('reviewer_name', sa.String(200), nullable=False),
        sa.Column('acknowledgement', sa.String(40), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='stage2_review_acknowledgements_pkey'),
    )
    op.create_table('stale_reasons',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('target_type', sa.String(100), nullable=False),
        sa.Column('target_id', sa.String(160), nullable=False),
        sa.Column('material_change_event_id', sa.String(36), nullable=False),
        sa.Column('reason_code', sa.String(100), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('cleared_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cleared_by', sa.String(200), nullable=True),
        sa.Column('replacement_target_id', sa.String(160), nullable=True),
        sa.PrimaryKeyConstraint('id', name='stale_reasons_pkey'),
    )
    op.create_table('storage_operations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('idempotency_key', sa.String(240), nullable=False),
        sa.Column('operation_type', sa.String(60), nullable=False),
        sa.Column('document_id', sa.String(36), nullable=True),
        sa.Column('document_version_id', sa.String(36), nullable=True),
        sa.Column('provider_id', sa.String(100), nullable=False),
        sa.Column('target_locator', sa.String(900), nullable=False),
        sa.Column('temporary_locator', sa.String(900), nullable=True),
        sa.Column('expected_sha256', sa.String(64), nullable=False),
        sa.Column('expected_size', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(50), nullable=False),
        sa.Column('attempt_count', sa.Integer(), nullable=False),
        sa.Column('lease_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error_class', sa.String(80), nullable=True),
        sa.Column('last_error_message', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='storage_operations_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_storage_operation_idempotency'),
    )
    op.create_table('storage_outbox_events',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('event_key', sa.String(240), nullable=False),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('aggregate_type', sa.String(100), nullable=False),
        sa.Column('aggregate_id', sa.String(36), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('available_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='storage_outbox_events_pkey'),
        sa.UniqueConstraint('event_key', name='uq_storage_outbox_event_key'),
    )
    op.create_table('submission_attempts',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('submission_package_id', sa.String(36), nullable=False),
        sa.Column('precheck_run_id', sa.String(36), nullable=False),
        sa.Column('channel_code', sa.String(60), nullable=False),
        sa.Column('attempt_number', sa.Integer(), nullable=False),
        sa.Column('idempotency_key', sa.String(200), nullable=False),
        sa.Column('state', sa.String(40), nullable=False),
        sa.Column('authorized_by', sa.String(200), nullable=False),
        sa.Column('authorized_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='submission_attempts_pkey'),
        sa.UniqueConstraint('idempotency_key', name='uq_submission_attempt_idempotency'),
    )
    op.create_table('submission_confirmations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('mode', sa.String(50), nullable=False),
        sa.Column('request_reference', sa.String(100), nullable=False),
        sa.Column('visible_status', sa.String(50), nullable=False),
        sa.Column('confirmation_timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence_reference', sa.String(300), nullable=True),
        sa.Column('second_verifier', sa.String(200), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('application_identity_json', sa.JSON(), nullable=True),
        sa.Column('confirmed_by', sa.String(200), nullable=True),
        sa.Column('status', sa.String(40), nullable=True),
        sa.PrimaryKeyConstraint('id', name='submission_confirmations_pkey'),
    )
    op.create_table('submission_cycles',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('cycle_number', sa.Integer(), nullable=False),
        sa.Column('external_reference', sa.String(160), nullable=True),
        sa.Column('source_reference', sa.String(300), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=True),
        sa.Column('submitted_snapshot_id', sa.String(36), nullable=True),
        sa.Column('submission_confirmation_id', sa.String(36), nullable=True),
        sa.Column('authority_repetition_number', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('returned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='submission_cycles_pkey'),
    )
    op.create_table('submission_handoffs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('package_id', sa.String(36), nullable=False),
        sa.Column('portal_snapshot_id', sa.String(36), nullable=True),
        sa.Column('handoff_status', sa.String(50), nullable=False),
        sa.Column('final_submitter_user_id', sa.String(36), nullable=False),
        sa.Column('prepared_by', sa.String(200), nullable=False),
        sa.Column('prepared_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('from_user_id', sa.String(36), nullable=True),
        sa.Column('from_role', sa.String(80), nullable=True),
        sa.Column('final_submitter_role', sa.String(80), nullable=True),
        sa.Column('handoff_state', sa.String(50), nullable=True),
        sa.Column('checklist_hash', sa.String(64), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=True),
        sa.Column('readiness_summary', sa.JSON(), nullable=False),
        sa.Column('unresolved_nonblocking_items', sa.JSON(), nullable=False),
        sa.Column('evidence_refs', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='submission_handoffs_pkey'),
    )
    op.create_table('submission_package_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('package_id', sa.String(36), nullable=False),
        sa.Column('item_type', sa.String(50), nullable=False),
        sa.Column('requirement_instance_id', sa.String(36), nullable=True),
        sa.Column('evidence_selection_id', sa.String(36), nullable=True),
        sa.Column('document_version_id', sa.String(36), nullable=True),
        sa.Column('form_instance_id', sa.String(36), nullable=True),
        sa.Column('baseline_id', sa.String(36), nullable=True),
        sa.Column('baseline_member_id', sa.String(36), nullable=True),
        sa.Column('as_built_baseline_id', sa.String(36), nullable=True),
        sa.Column('physical_evidence_item_id', sa.String(36), nullable=True),
        sa.Column('display_order', sa.Integer(), nullable=False),
        sa.Column('section', sa.String(120), nullable=True),
        sa.Column('submission_filename', sa.String(300), nullable=True),
        sa.Column('label', sa.String(300), nullable=True),
        sa.PrimaryKeyConstraint('id', name='submission_package_items_pkey'),
        sa.UniqueConstraint('package_id', 'display_order', name='uq_submission_package_item_order'),
    )
    op.create_table('submission_packages',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('state', sa.String(30), nullable=False),
        sa.Column('manifest_hash', sa.String(64), nullable=True),
        sa.Column('manifest_json', sa.JSON(), nullable=False),
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='submission_packages_pkey'),
        sa.UniqueConstraint('preparation_revision_id', name='uq_submission_package_preparation'),
    )
    op.create_table('submission_precheck_checks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('precheck_run_id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50), nullable=False),
        sa.Column('result', sa.String(30), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('source_type', sa.String(80), nullable=True),
        sa.Column('source_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='submission_precheck_checks_pkey'),
    )
    op.create_table('submission_precheck_runs',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('authority_case_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('submission_package_id', sa.String(36), nullable=False),
        sa.Column('policy_version_id', sa.String(36), nullable=True),
        sa.Column('package_hash', sa.String(64), nullable=False),
        sa.Column('result', sa.String(30), nullable=False),
        sa.Column('digital_readiness', sa.String(30), nullable=False),
        sa.Column('physical_readiness', sa.String(30), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evaluated_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='submission_precheck_runs_pkey'),
    )
    op.create_table('submitted_snapshots',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('application_id', sa.String(36), nullable=False),
        sa.Column('submission_cycle_id', sa.String(36), nullable=False),
        sa.Column('preparation_revision_id', sa.String(36), nullable=False),
        sa.Column('package_id', sa.String(36), nullable=False),
        sa.Column('package_manifest_hash', sa.String(64), nullable=False),
        sa.Column('portal_snapshot_id', sa.String(36), nullable=True),
        sa.Column('submitted_values', sa.JSON(), nullable=False),
        sa.Column('submitted_grids', sa.JSON(), nullable=False),
        sa.Column('submitted_attachments', sa.JSON(), nullable=False),
        sa.Column('authority_status', sa.String(50), nullable=False),
        sa.Column('submission_reference', sa.String(160), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('captured_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('capture_method', sa.String(60), nullable=False),
        sa.Column('snapshot_hash', sa.String(64), nullable=False),
        sa.PrimaryKeyConstraint('id', name='submitted_snapshots_pkey'),
    )
    op.create_table('support_cases',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('category', sa.String(100), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('application_id', sa.String(36), nullable=True),
        sa.Column('finding_id', sa.String(36), nullable=True),
        sa.Column('monitoring_run_id', sa.String(36), nullable=True),
        sa.Column('opened_by', sa.String(200), nullable=False),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('current_level', sa.String(20), nullable=False),
        sa.Column('assigned_to', sa.String(200), nullable=True),
        sa.Column('status', sa.String(40), nullable=False),
        sa.Column('external_dependency', sa.String(200), nullable=True),
        sa.Column('resolution_summary', sa.Text(), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.PrimaryKeyConstraint('id', name='support_cases_pkey'),
    )
    op.create_table('synology_project_bootstraps',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('root_path', sa.String(400), nullable=False),
        sa.Column('subfolders_json', sa.JSON(), nullable=False),
        sa.Column('template_applied', sa.Boolean(), nullable=False),
        sa.Column('template_manifest_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='synology_project_bootstraps_pkey'),
        sa.UniqueConstraint('project_id', name='synology_project_bootstraps_project_id_key'),
    )
    op.create_table('synthetic_fixture_sets',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('fixture_set_id', sa.String(120), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('semantic_version', sa.String(30), nullable=False),
        sa.Column('manifest_sha256', sa.String(64), nullable=False),
        sa.Column('source_manifest_path', sa.String(300), nullable=False),
        sa.Column('imported_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('synthetic_only', sa.Boolean(), nullable=False),
        sa.Column('golden_path_authority', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(100), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('manifest_json', sa.JSON(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='synthetic_fixture_sets_pkey'),
        sa.UniqueConstraint('fixture_set_id', name='synthetic_fixture_sets_fixture_set_id_key'),
    )
    op.create_table('system_blocks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('context_type', sa.String(80), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('control_code', sa.String(100), nullable=False),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('owner_role', sa.String(100), nullable=False),
        sa.Column('required_action', sa.Text(), nullable=False),
        sa.Column('resolution_condition', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id', name='system_blocks_pkey'),
    )
    op.create_table('target_rendering_coverages',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('variant_id', sa.String(36), nullable=False),
        sa.Column('target_type', sa.String(60), nullable=False),
        sa.Column('supported_fields', sa.JSON(), nullable=False),
        sa.Column('mapped_fields', sa.JSON(), nullable=False),
        sa.Column('missing_fields', sa.JSON(), nullable=False),
        sa.Column('blocked_external', sa.JSON(), nullable=False),
        sa.Column('not_applicable', sa.JSON(), nullable=False),
        sa.Column('coverage_percent', sa.Float(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='target_rendering_coverages_pkey'),
    )
    op.create_table('target_rendering_rules',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('field_definition_id', sa.String(36), nullable=False),
        sa.Column('target_system', sa.String(30), nullable=False),
        sa.Column('target_location', sa.String(200), nullable=False),
        sa.Column('format_rule', sa.String(200), nullable=True),
        sa.Column('language_rule', sa.String(100), nullable=True),
        sa.Column('unit_rule', sa.String(100), nullable=True),
        sa.Column('dropdown_code_map', sa.JSON(), nullable=False),
        sa.Column('null_behavior', sa.String(100), nullable=False),
        sa.Column('version', sa.String(30), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.PrimaryKeyConstraint('id', name='target_rendering_rules_pkey'),
        sa.UniqueConstraint('scenario_id', 'field_definition_id', 'target_system', 'version', name='uq_target_rendering_rule'),
    )
    op.create_table('technical_rule_evaluations',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('technical_rule_id', sa.String(36), nullable=False),
        sa.Column('context_type', sa.String(50), nullable=False),
        sa.Column('context_id', sa.String(36), nullable=False),
        sa.Column('result', sa.String(20), nullable=False),
        sa.Column('calculated_values', sa.JSON(), nullable=False),
        sa.Column('inputs_json', sa.JSON(), nullable=False),
        sa.Column('rule_version', sa.String(40), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='technical_rule_evaluations_pkey'),
    )
    op.create_table('technical_rule_lineage',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('technical_rule_id', sa.String(36), nullable=False),
        sa.Column('master_content_item_id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('source_section_id', sa.String(36), nullable=True),
        sa.Column('relation_type', sa.String(40), nullable=False),
        sa.Column('source_role', sa.String(40), nullable=False),
        sa.Column('governance_status', sa.String(30), nullable=False),
        sa.Column('governance_note', sa.Text(), nullable=True),
        sa.Column('confirmed_by', sa.String(200), nullable=True),
        sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='technical_rule_lineage_pkey'),
    )
    op.create_table('technical_rule_set_versions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(120), nullable=False),
        sa.Column('name', sa.String(240), nullable=False),
        sa.Column('discipline', sa.String(80), nullable=True),
        sa.Column('service_type_id', sa.String(36), nullable=True),
        sa.Column('jurisdiction_id', sa.String(36), nullable=True),
        sa.Column('external_body_id', sa.String(36), nullable=True),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('effective_from', sa.Date(), nullable=True),
        sa.Column('effective_to', sa.Date(), nullable=True),
        sa.Column('provenance_json', sa.JSON(), nullable=False),
        sa.Column('approved_by', sa.String(200), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('supersedes_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='technical_rule_set_versions_pkey'),
        sa.UniqueConstraint('code', 'version', name='uq_technical_rule_set_version'),
    )
    op.create_table('technical_rules',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('rule_set_version_id', sa.String(36), nullable=False),
        sa.Column('code', sa.String(120), nullable=False),
        sa.Column('name', sa.String(240), nullable=False),
        sa.Column('rule_type', sa.String(50), nullable=False),
        sa.Column('expression_json', sa.JSON(), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('order_index', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='technical_rules_pkey'),
        sa.UniqueConstraint('rule_set_version_id', 'code', name='uq_technical_rule_code'),
    )
    op.create_table('template_definitions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('template_code', sa.String(100), nullable=False),
        sa.Column('artifact_type', sa.String(80), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('language', sa.String(10), nullable=False),
        sa.Column('owner_role', sa.String(100), nullable=False),
        sa.Column('status', sa.String(60), nullable=False),
        sa.PrimaryKeyConstraint('id', name='template_definitions_pkey'),
        sa.UniqueConstraint('template_code', name='template_definitions_template_code_key'),
    )
    op.create_table('template_versions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('template_definition_id', sa.String(36), nullable=False),
        sa.Column('version', sa.String(40), nullable=False),
        sa.Column('status', sa.String(60), nullable=False),
        sa.Column('source_document_version_id', sa.String(36), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('supersedes_id', sa.String(36), nullable=True),
        sa.PrimaryKeyConstraint('id', name='template_versions_pkey'),
        sa.UniqueConstraint('template_definition_id', 'version', name='uq_template_version'),
    )
    op.create_table('tender_documents',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('opportunity_id', sa.String(36), nullable=False),
        sa.Column('document_version_id', sa.String(36), nullable=False),
        sa.Column('document_role', sa.String(80), nullable=False),
        sa.Column('status', sa.String(40), nullable=False),
        sa.PrimaryKeyConstraint('id', name='tender_documents_pkey'),
    )
    op.create_table('threshold_definitions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('metric_code', sa.String(100), nullable=False),
        sa.Column('metric_name', sa.String(200), nullable=False),
        sa.Column('category', sa.Enum('SAFETY', 'QUALITY', 'EFFICIENCY', 'OPERATIONS', 'ADOPTION', name='thresholdcategory'), nullable=False),
        sa.Column('observed_value', sa.Float(), nullable=True),
        sa.Column('sample_size', sa.Integer(), nullable=True),
        sa.Column('proposed_threshold', sa.Float(), nullable=True),
        sa.Column('comparison_operator', sa.String(10), nullable=False),
        sa.Column('severity', sa.String(30), nullable=False),
        sa.Column('acceptance_effect', sa.String(30), nullable=False),
        sa.Column('status', sa.Enum('MEASURED', 'PROPOSED', 'NEEDS_MORE_EVIDENCE', 'APPROVED_STAGE_2', 'NOT_APPLICABLE', name='thresholdstatus'), nullable=False),
        sa.Column('basis', sa.Text(), nullable=False),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('owner', sa.String(200), nullable=False),
        sa.PrimaryKeyConstraint('id', name='threshold_definitions_pkey'),
        sa.UniqueConstraint('metric_code', name='threshold_definitions_metric_code_key'),
    )
    op.create_table('tier1_decisions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('decision_code', sa.String(100), nullable=False),
        sa.Column('topic', sa.String(120), nullable=False),
        sa.Column('question', sa.Text(), nullable=False),
        sa.Column('options_json', sa.JSON(), nullable=False),
        sa.Column('recommendation', sa.Text(), nullable=False),
        sa.Column('owner', sa.String(200), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('status', sa.Enum('OPEN', 'ESCALATED', 'RESOLVED', 'RESOLVED_WITH_FALLBACK', 'BLOCKER', name='tier1decisionstatus'), nullable=False),
        sa.Column('evidence', sa.Text(), nullable=False),
        sa.Column('impact_if_unresolved', sa.Text(), nullable=False),
        sa.Column('resolution', sa.Text(), nullable=True),
        sa.Column('fallback', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='tier1_decisions_pkey'),
        sa.UniqueConstraint('decision_code', name='tier1_decisions_decision_code_key'),
    )
    op.create_table('tier2_backlog_items',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('category', sa.Enum('FIELD_MATRIX', 'REQUIREMENT_MATRIX', 'RENDERING', 'FINDING_TAXONOMY', 'EDGE_CASE', 'KPI', 'MUNICIPALITY_MAPPING', 'DOCUMENT', name='tier2category'), nullable=False),
        sa.Column('title', sa.String(240), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('owner', sa.String(200), nullable=False),
        sa.Column('priority', sa.String(30), nullable=False),
        sa.Column('due_build_week', sa.Integer(), nullable=False),
        sa.Column('blocking_week6', sa.Boolean(), nullable=False),
        sa.Column('status', sa.Enum('OPEN', 'IN_PROGRESS', 'DONE', 'DEFERRED', name='tier2status'), nullable=False),
        sa.Column('dependency', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=False),
        sa.Column('scenario_expansion_warning', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='tier2_backlog_items_pkey'),
    )
    op.create_table('users',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('entra_object_id', sa.String(36), nullable=True),
        sa.Column('email', sa.String(200), nullable=False),
        sa.Column('display_name', sa.String(200), nullable=False),
        sa.Column('role', sa.Enum('OWNER_SPONSOR', 'PROCESS_CHAMPION', 'REQUIREMENT_STEWARD', 'RESPONSIBLE_ENGINEER', 'PERMIT_PREPARER', 'FINAL_SUBMITTER', 'SYSTEM_ADMIN', name='role'), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('office_id', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='users_pkey'),
        sa.UniqueConstraint('email', name='users_email_key'),
    )
    op.create_table('variant_compatibility_results',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scenario_id', sa.String(36), nullable=False),
        sa.Column('base_variant', sa.String(100), nullable=False),
        sa.Column('second_variant', sa.String(100), nullable=False),
        sa.Column('domain_schema_change_required', sa.Boolean(), nullable=False),
        sa.Column('new_semantic_fields', sa.JSON(), nullable=False),
        sa.Column('new_rendering_rules', sa.JSON(), nullable=False),
        sa.Column('new_requirement_rules', sa.JSON(), nullable=False),
        sa.Column('new_attachment_rules', sa.JSON(), nullable=False),
        sa.Column('new_grid_rules', sa.JSON(), nullable=False),
        sa.Column('new_human_decisions', sa.JSON(), nullable=False),
        sa.Column('core_code_fork_required', sa.Boolean(), nullable=False),
        sa.Column('result', sa.String(40), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='variant_compatibility_results_pkey'),
    )
    op.create_table('verified_assertions',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=False),
        sa.Column('field_definition_id', sa.String(36), nullable=False),
        sa.Column('semantic_value_json', sa.JSON(), nullable=False),
        sa.Column('display_value', sa.Text(), nullable=False),
        sa.Column('status', sa.Enum('CURRENT', 'SUPERSEDED', 'STALE', 'REJECTED', name='assertionstatus'), nullable=False),
        sa.Column('source_observation_id', sa.String(36), nullable=True),
        sa.Column('verification_method', sa.Enum('SOURCE_CONFIRMED', 'CROSS_SOURCE_MATCH', 'HUMAN_VERIFIED', 'MANUAL_KEYED_VERIFIED', 'OTHER', name='verificationmethod'), nullable=False),
        sa.Column('verified_by', sa.String(36), nullable=False),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('authority_rule_id', sa.String(36), nullable=True),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('supersedes_assertion_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='verified_assertions_pkey'),
    )
    op.create_table('volume_baseline',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('values_json', sa.JSON(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name='volume_baseline_pkey'),
    )
    op.create_table('workflow_safety_holds',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('scope_type', sa.String(80), nullable=False),
        sa.Column('scope_id', sa.String(160), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('incident_id', sa.String(36), nullable=False),
        sa.Column('blocks_automated_writes', sa.Boolean(), nullable=False),
        sa.Column('blocks_final_review_readiness', sa.Boolean(), nullable=False),
        sa.Column('blocks_resubmission_readiness', sa.Boolean(), nullable=False),
        sa.Column('created_by', sa.String(200), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('released_by', sa.String(200), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('release_evidence', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id', name='workflow_safety_holds_pkey'),
    )
    op.create_table('workflow_tasks',
        sa.Column('id', sa.String(36), nullable=False),
        sa.Column('project_id', sa.String(36), nullable=True),
        sa.Column('application_id', sa.String(36), nullable=True),
        sa.Column('finding_id', sa.String(36), nullable=True),
        sa.Column('task_type', sa.String(100), nullable=False),
        sa.Column('title', sa.String(300), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('owner_user_id', sa.String(36), nullable=True),
        sa.Column('owner_role', sa.String(80), nullable=False),
        sa.Column('status', sa.String(30), nullable=False),
        sa.Column('priority', sa.String(30), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('escalation_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('correlation_id', sa.String(100), nullable=False),
        sa.Column('assistant_id', sa.String(80), nullable=True),
        sa.Column('task_family', sa.String(50), nullable=True),
        sa.Column('context_type', sa.String(80), nullable=True),
        sa.Column('context_id', sa.String(36), nullable=True),
        sa.Column('blocking', sa.Boolean(), nullable=False),
        sa.Column('next_action_code', sa.String(100), nullable=True),
        sa.Column('deep_link', sa.String(300), nullable=True),
        sa.Column('evidence_summary', sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint('id', name='workflow_tasks_pkey'),
    )

    # Foreign keys are added after all tables so cyclic dependencies remain intact.
    op.create_foreign_key('acceptance_corpus_definitions_scenario_id_fkey', 'acceptance_corpus_definitions', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('acceptance_metrics_rehearsal_run_id_fkey', 'acceptance_metrics', 'acceptance_rehearsal_runs', ['rehearsal_run_id'], ['id'])
    op.create_foreign_key('accounting_handoffs_assigned_user_id_fkey', 'accounting_handoffs', 'users', ['assigned_user_id'], ['id'])
    op.create_foreign_key('accounting_handoffs_invoice_id_fkey', 'accounting_handoffs', 'invoices', ['invoice_id'], ['id'])
    op.create_foreign_key('accounting_handoffs_workflow_task_id_fkey', 'accounting_handoffs', 'workflow_tasks', ['workflow_task_id'], ['id'])
    op.create_foreign_key('adjudication_cases_document_version_id_fkey', 'adjudication_cases', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('adjudication_cases_responsible_engineer_user_id_fkey', 'adjudication_cases', 'users', ['responsible_engineer_user_id'], ['id'])
    op.create_foreign_key('adjudication_cases_steward_user_id_fkey', 'adjudication_cases', 'users', ['steward_user_id'], ['id'])
    op.create_foreign_key('adjudication_histories_case_id_fkey', 'adjudication_histories', 'adjudication_cases', ['case_id'], ['id'])
    op.create_foreign_key('admin_document_comments_project_id_fkey', 'admin_document_comments', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('admin_document_comments_reviewed_artifact_id_fkey', 'admin_document_comments', 'rendered_artifacts', ['reviewed_artifact_id'], ['id'])
    op.create_foreign_key('admin_document_comments_source_document_version_id_fkey', 'admin_document_comments', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('applicable_rule_sets_configuration_bundle_id_fkey', 'applicable_rule_sets', 'configuration_bundles', ['configuration_bundle_id'], ['id'])
    op.create_foreign_key('applicable_rule_sets_project_id_fkey', 'applicable_rule_sets', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('approval_applicability_evaluations_approval_id_fkey', 'approval_applicability_evaluations', 'approvals', ['approval_id'], ['id'])
    op.create_foreign_key('approval_dependencies_evidence_document_id_fkey', 'approval_dependencies', 'documents', ['evidence_document_id'], ['id'])
    op.create_foreign_key('approval_dependencies_project_id_fkey', 'approval_dependencies', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('approved_design_baseline_members_baseline_id_fkey', 'approved_design_baseline_members', 'approved_design_baselines', ['baseline_id'], ['id'])
    op.create_foreign_key('approved_design_baseline_members_project_id_fkey', 'approved_design_baseline_members', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('approved_design_baseline_members_rendition_id_fkey', 'approved_design_baseline_members', 'engineering_renditions', ['rendition_id'], ['id'])
    op.create_foreign_key('approved_design_baseline_members_revision_id_fkey', 'approved_design_baseline_members', 'engineering_deliverable_revisions', ['revision_id'], ['id'])
    op.create_foreign_key('approved_design_baselines_project_id_fkey', 'approved_design_baselines', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('approved_design_baselines_supersedes_baseline_id_fkey', 'approved_design_baselines', 'approved_design_baselines', ['supersedes_baseline_id'], ['id'])
    op.create_foreign_key('as_built_baseline_members_baseline_id_fkey', 'as_built_baseline_members', 'as_built_baselines', ['baseline_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('as_built_baseline_members_building_snapshot_id_fkey', 'as_built_baseline_members', 'building_snapshots', ['building_snapshot_id'], ['id'])
    op.create_foreign_key('as_built_baseline_members_document_version_id_fkey', 'as_built_baseline_members', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('as_built_baseline_members_engineering_revision_id_fkey', 'as_built_baseline_members', 'engineering_deliverable_revisions', ['engineering_revision_id'], ['id'])
    op.create_foreign_key('as_built_baseline_members_project_id_fkey', 'as_built_baseline_members', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('as_built_baseline_members_rendition_id_fkey', 'as_built_baseline_members', 'engineering_renditions', ['rendition_id'], ['id'])
    op.create_foreign_key('as_built_baselines_authority_case_id_fkey', 'as_built_baselines', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('as_built_baselines_construction_execution_id_fkey', 'as_built_baselines', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('as_built_baselines_project_id_fkey', 'as_built_baselines', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('as_built_baselines_source_construction_design_snapshot_id_fkey', 'as_built_baselines', 'construction_design_snapshots', ['source_construction_design_snapshot_id'], ['id'])
    op.create_foreign_key('as_built_baselines_supersedes_baseline_id_fkey', 'as_built_baselines', 'as_built_baselines', ['supersedes_baseline_id'], ['id'])
    op.create_foreign_key('as_built_comparison_runs_baseline_id_fkey', 'as_built_comparison_runs', 'as_built_baselines', ['baseline_id'], ['id'])
    op.create_foreign_key('as_built_comparison_runs_construction_design_snapshot_id_fkey', 'as_built_comparison_runs', 'construction_design_snapshots', ['construction_design_snapshot_id'], ['id'])
    op.create_foreign_key('as_built_comparison_runs_project_id_fkey', 'as_built_comparison_runs', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('as_built_variances_building_asset_id_fkey', 'as_built_variances', 'building_assets', ['building_asset_id'], ['id'])
    op.create_foreign_key('as_built_variances_comparison_run_id_fkey', 'as_built_variances', 'as_built_comparison_runs', ['comparison_run_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('as_built_variances_design_change_request_id_fkey', 'as_built_variances', 'design_change_requests', ['design_change_request_id'], ['id'])
    op.create_foreign_key('as_built_variances_engineering_revision_id_fkey', 'as_built_variances', 'engineering_deliverable_revisions', ['engineering_revision_id'], ['id'])
    op.create_foreign_key('as_built_variances_project_id_fkey', 'as_built_variances', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('assistant_handoffs_opportunity_id_fkey', 'assistant_handoffs', 'opportunities', ['opportunity_id'], ['id'])
    op.create_foreign_key('assistant_handoffs_project_id_fkey', 'assistant_handoffs', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('assistant_handoffs_workflow_task_id_fkey', 'assistant_handoffs', 'workflow_tasks', ['workflow_task_id'], ['id'])
    op.create_foreign_key('attachment_association_intents_application_id_fkey', 'attachment_association_intents', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('attachment_association_intents_attachment_manifest_item_id_fkey', 'attachment_association_intents', 'attachment_manifest_items', ['attachment_manifest_item_id'], ['id'])
    op.create_foreign_key('attachment_association_intents_document_version_id_fkey', 'attachment_association_intents', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('attachment_association_intents_preparation_revision_id_fkey', 'attachment_association_intents', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('attachment_association_intents_replaces_association_id_fkey', 'attachment_association_intents', 'attachment_association_intents', ['replaces_association_id'], ['id'])
    op.create_foreign_key('attachment_category_configs_scenario_id_fkey', 'attachment_category_configs', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('attachment_category_rules_scenario_id_fkey', 'attachment_category_rules', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('attachment_manifest_items_attachment_manifest_id_fkey', 'attachment_manifest_items', 'attachment_manifests', ['attachment_manifest_id'], ['id'])
    op.create_foreign_key('attachment_manifest_items_document_id_fkey', 'attachment_manifest_items', 'documents', ['document_id'], ['id'])
    op.create_foreign_key('attachment_manifest_items_document_version_id_fkey', 'attachment_manifest_items', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('attachment_manifests_package_id_fkey', 'attachment_manifests', 'packages', ['package_id'], ['id'])
    op.create_foreign_key('attachment_persistence_evidence_application_id_fkey', 'attachment_persistence_evidence', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('attachment_persistence_evidence_document_version_id_fkey', 'attachment_persistence_evidence', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('attachment_persistence_evidence_preparation_revision_id_fkey', 'attachment_persistence_evidence', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('attachment_reconciliation_results_document_version_id_fkey', 'attachment_reconciliation_results', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('attachment_reconciliation_results_manifest_item_id_fkey', 'attachment_reconciliation_results', 'attachment_manifest_items', ['manifest_item_id'], ['id'])
    op.create_foreign_key('attachment_reconciliation_results_preparation_revision_id_fkey', 'attachment_reconciliation_results', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('attended_auth_sessions_application_id_fkey', 'attended_auth_sessions', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('attended_auth_sessions_completed_by_user_id_fkey', 'attended_auth_sessions', 'users', ['completed_by_user_id'], ['id'])
    op.create_foreign_key('attended_auth_sessions_user_id_fkey', 'attended_auth_sessions', 'users', ['user_id'], ['id'])
    op.create_foreign_key('attended_sessions_application_id_fkey', 'attended_sessions', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('attended_sessions_preparation_revision_id_fkey', 'attended_sessions', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('authority_approval_validities_approval_dependency_id_fkey', 'authority_approval_validities', 'approval_dependencies', ['approval_dependency_id'], ['id'])
    op.create_foreign_key('authority_approval_validities_evidence_document_version_id_fkey', 'authority_approval_validities', 'document_versions', ['evidence_document_version_id'], ['id'])
    op.create_foreign_key('authority_approved_design_sna_external_submission_snapshot_fkey', 'authority_approved_design_snapshots', 'external_submission_snapshots', ['external_submission_snapshot_id'], ['id'])
    op.create_foreign_key('authority_approved_design_snap_approved_design_baseline_id_fkey', 'authority_approved_design_snapshots', 'approved_design_baselines', ['approved_design_baseline_id'], ['id'])
    op.create_foreign_key('authority_approved_design_snapsh_construction_execution_id_fkey', 'authority_approved_design_snapshots', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('authority_approved_design_snapshot_preparation_revision_id_fkey', 'authority_approved_design_snapshots', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('authority_approved_design_snapshots_authority_case_id_fkey', 'authority_approved_design_snapshots', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('authority_approved_design_snapshots_authority_outcome_id_fkey', 'authority_approved_design_snapshots', 'authority_outcomes', ['authority_outcome_id'], ['id'])
    op.create_foreign_key('authority_approved_design_snapshots_project_id_fkey', 'authority_approved_design_snapshots', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('authority_approved_design_snapshots_submission_cycle_id_fkey', 'authority_approved_design_snapshots', 'authority_submission_cycles', ['submission_cycle_id'], ['id'])
    op.create_foreign_key('authority_approved_design_snapshots_submission_package_id_fkey', 'authority_approved_design_snapshots', 'submission_packages', ['submission_package_id'], ['id'])
    op.create_foreign_key('authority_case_create_requests_authority_case_id_fkey', 'authority_case_create_requests', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('authority_case_findings_affected_requirement_instance_id_fkey', 'authority_case_findings', 'requirement_instances', ['affected_requirement_instance_id'], ['id'])
    op.create_foreign_key('authority_case_findings_authority_case_id_fkey', 'authority_case_findings', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('authority_case_findings_source_document_version_id_fkey', 'authority_case_findings', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('authority_case_findings_submission_cycle_id_fkey', 'authority_case_findings', 'authority_submission_cycles', ['submission_cycle_id'], ['id'])
    op.create_foreign_key('authority_case_identifiers_authority_case_id_fkey', 'authority_case_identifiers', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('authority_case_outcomes_authority_case_id_fkey', 'authority_case_outcomes', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('authority_case_outcomes_source_document_version_id_fkey', 'authority_case_outcomes', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('authority_case_outcomes_submission_cycle_id_fkey', 'authority_case_outcomes', 'authority_submission_cycles', ['submission_cycle_id'], ['id'])
    op.create_foreign_key('authority_case_policy_bindings_authority_case_id_fkey', 'authority_case_policy_bindings', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('authority_case_policy_bindings_policy_version_id_fkey', 'authority_case_policy_bindings', 'requirement_policy_versions', ['policy_version_id'], ['id'])
    op.create_foreign_key('authority_case_subjects_authority_case_id_fkey', 'authority_case_subjects', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('authority_case_work_periods_authority_case_id_fkey', 'authority_case_work_periods', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('authority_case_work_periods_source_document_version_id_fkey', 'authority_case_work_periods', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('authority_cases_external_body_id_fkey', 'authority_cases', 'external_bodies', ['external_body_id'], ['id'])
    op.create_foreign_key('authority_cases_jurisdiction_id_fkey', 'authority_cases', 'jurisdictions', ['jurisdiction_id'], ['id'])
    op.create_foreign_key('authority_cases_regulatory_journey_id_fkey', 'authority_cases', 'regulatory_journeys', ['regulatory_journey_id'], ['id'])
    op.create_foreign_key('authority_cases_service_type_id_fkey', 'authority_cases', 'service_types', ['service_type_id'], ['id'])
    op.create_foreign_key('authority_comment_observations_application_id_fkey', 'authority_comment_observations', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('authority_comment_observations_monitoring_run_id_fkey', 'authority_comment_observations', 'monitoring_runs', ['monitoring_run_id'], ['id'])
    op.create_foreign_key('authority_comment_observations_submission_cycle_id_fkey', 'authority_comment_observations', 'submission_cycles', ['submission_cycle_id'], ['id'])
    op.create_foreign_key('authority_events_application_id_fkey', 'authority_events', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('authority_events_project_id_fkey', 'authority_events', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('authority_finding_responses_affected_baseline_id_fkey', 'authority_finding_responses', 'approved_design_baselines', ['affected_baseline_id'], ['id'])
    op.create_foreign_key('authority_finding_responses_affected_requirement_instance__fkey', 'authority_finding_responses', 'requirement_instances', ['affected_requirement_instance_id'], ['id'])
    op.create_foreign_key('authority_finding_responses_finding_id_fkey', 'authority_finding_responses', 'authority_case_findings', ['finding_id'], ['id'])
    op.create_foreign_key('authority_outcomes_authority_case_id_fkey', 'authority_outcomes', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('authority_outcomes_source_document_version_id_fkey', 'authority_outcomes', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('authority_precheck_items_precheck_run_id_fkey', 'authority_precheck_items', 'authority_precheck_runs', ['precheck_run_id'], ['id'])
    op.create_foreign_key('authority_precheck_runs_application_id_fkey', 'authority_precheck_runs', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('authority_precheck_runs_configuration_bundle_id_fkey', 'authority_precheck_runs', 'configuration_bundles', ['configuration_bundle_id'], ['id'])
    op.create_foreign_key('authority_precheck_runs_preparation_revision_id_fkey', 'authority_precheck_runs', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('authority_state_comparisons_monitoring_run_id_fkey', 'authority_state_comparisons', 'monitoring_runs', ['monitoring_run_id'], ['id'])
    op.create_foreign_key('authority_status_observations_application_id_fkey', 'authority_status_observations', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('authority_status_observations_monitoring_run_id_fkey', 'authority_status_observations', 'monitoring_runs', ['monitoring_run_id'], ['id'])
    op.create_foreign_key('authority_status_observations_submission_cycle_id_fkey', 'authority_status_observations', 'submission_cycles', ['submission_cycle_id'], ['id'])
    op.create_foreign_key('authority_submission_cycles_authority_case_id_fkey', 'authority_submission_cycles', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('authority_submission_cycles_external_submission_snapshot_i_fkey', 'authority_submission_cycles', 'external_submission_snapshots', ['external_submission_snapshot_id'], ['id'])
    op.create_foreign_key('authority_submission_cycles_preparation_revision_id_fkey', 'authority_submission_cycles', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('authority_submission_cycles_submission_package_id_fkey', 'authority_submission_cycles', 'submission_packages', ['submission_package_id'], ['id'])
    op.create_foreign_key('authorization_grants_authority_case_id_fkey', 'authorization_grants', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('authorization_grants_evidence_document_version_id_fkey', 'authorization_grants', 'document_versions', ['evidence_document_version_id'], ['id'])
    op.create_foreign_key('authorization_grants_grantee_party_id_fkey', 'authorization_grants', 'parties', ['grantee_party_id'], ['id'])
    op.create_foreign_key('authorization_grants_grantor_party_id_fkey', 'authorization_grants', 'parties', ['grantor_party_id'], ['id'])
    op.create_foreign_key('authorization_grants_project_id_fkey', 'authorization_grants', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('authorizations_evidence_document_version_id_fkey', 'authorizations', 'document_versions', ['evidence_document_version_id'], ['id'])
    op.create_foreign_key('authorizations_principal_party_id_fkey', 'authorizations', 'parties', ['principal_party_id'], ['id'])
    op.create_foreign_key('authorizations_representative_party_id_fkey', 'authorizations', 'parties', ['representative_party_id'], ['id'])
    op.create_foreign_key('automation_readiness_assessment_source_document_version_id_fkey', 'automation_readiness_assessments', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('automation_readiness_assessments_mapping_release_id_fkey', 'automation_readiness_assessments', 'form_mapping_releases', ['mapping_release_id'], ['id'])
    op.create_foreign_key('automation_readiness_assessments_master_content_item_id_fkey', 'automation_readiness_assessments', 'master_content_items', ['master_content_item_id'], ['id'])
    op.create_foreign_key('automation_readiness_assessments_profile_id_fkey', 'automation_readiness_assessments', 'form_automation_profiles', ['profile_id'], ['id'])
    op.create_foreign_key('billing_milestone_eligibilities_billing_milestone_id_fkey', 'billing_milestone_eligibilities', 'billing_milestones', ['billing_milestone_id'], ['id'])
    op.create_foreign_key('billing_milestones_billing_plan_revision_id_fkey', 'billing_milestones', 'billing_plan_revisions', ['billing_plan_revision_id'], ['id'])
    op.create_foreign_key('billing_milestones_source_contract_payment_term_id_fkey', 'billing_milestones', 'contract_payment_terms', ['source_contract_payment_term_id'], ['id'])
    op.create_foreign_key('billing_plan_revisions_billing_plan_id_fkey', 'billing_plan_revisions', 'billing_plans', ['billing_plan_id'], ['id'])
    op.create_foreign_key('billing_plan_revisions_client_account_id_fkey', 'billing_plan_revisions', 'client_accounts', ['client_account_id'], ['id'])
    op.create_foreign_key('billing_plan_revisions_contract_id_fkey', 'billing_plan_revisions', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('billing_plan_revisions_contract_revision_id_fkey', 'billing_plan_revisions', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('billing_plan_revisions_project_id_fkey', 'billing_plan_revisions', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('billing_plans_client_account_id_fkey', 'billing_plans', 'client_accounts', ['client_account_id'], ['id'])
    op.create_foreign_key('billing_plans_contract_id_fkey', 'billing_plans', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('billing_plans_contract_revision_id_fkey', 'billing_plans', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('billing_plans_project_id_fkey', 'billing_plans', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('building_assets_project_id_fkey', 'building_assets', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('building_assets_property_id_fkey', 'building_assets', 'properties', ['property_id'], ['id'])
    op.create_foreign_key('building_snapshots_building_asset_id_fkey', 'building_snapshots', 'building_assets', ['building_asset_id'], ['id'])
    op.create_foreign_key('building_snapshots_project_id_fkey', 'building_snapshots', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('building_snapshots_supersedes_id_fkey', 'building_snapshots', 'building_snapshots', ['supersedes_id'], ['id'])
    op.create_foreign_key('case_evidence_selections_approved_design_baseline_id_fkey', 'case_evidence_selections', 'approved_design_baselines', ['approved_design_baseline_id'], ['id'])
    op.create_foreign_key('case_evidence_selections_authority_case_id_fkey', 'case_evidence_selections', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('case_evidence_selections_document_version_id_fkey', 'case_evidence_selections', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('case_evidence_selections_form_instance_id_fkey', 'case_evidence_selections', 'form_instances', ['form_instance_id'], ['id'])
    op.create_foreign_key('case_evidence_selections_requirement_instance_id_fkey', 'case_evidence_selections', 'requirement_instances', ['requirement_instance_id'], ['id'])
    op.create_foreign_key('case_party_snapshots_authority_case_id_fkey', 'case_party_snapshots', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('case_party_snapshots_preparation_revision_id_fkey', 'case_party_snapshots', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('case_party_snapshots_project_id_fkey', 'case_party_snapshots', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('checklist_items_current_document_version_id_fkey', 'checklist_items', 'document_versions', ['current_document_version_id'], ['id'])
    op.create_foreign_key('client_accounts_canonical_party_id_fkey', 'client_accounts', 'parties', ['canonical_party_id'], ['id'])
    op.create_foreign_key('client_contacts_client_account_id_fkey', 'client_contacts', 'client_accounts', ['client_account_id'], ['id'])
    op.create_foreign_key('client_responses_evidence_artifact_id_fkey', 'client_responses', 'evidence_artifacts', ['evidence_artifact_id'], ['id'])
    op.create_foreign_key('client_responses_opportunity_id_fkey', 'client_responses', 'opportunities', ['opportunity_id'], ['id'])
    op.create_foreign_key('client_responses_quotation_revision_id_fkey', 'client_responses', 'quotation_revisions', ['quotation_revision_id'], ['id'])
    op.create_foreign_key('commercial_terms_evidence_artifact_id_fkey', 'commercial_terms', 'evidence_artifacts', ['evidence_artifact_id'], ['id'])
    op.create_foreign_key('commercial_terms_quotation_revision_id_fkey', 'commercial_terms', 'quotation_revisions', ['quotation_revision_id'], ['id'])
    op.create_foreign_key('commercial_terms_source_document_version_id_fkey', 'commercial_terms', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('communication_approvals_approval_id_fkey', 'communication_approvals', 'approvals', ['approval_id'], ['id'])
    op.create_foreign_key('communication_approvals_communication_draft_id_fkey', 'communication_approvals', 'communication_drafts', ['communication_draft_id'], ['id'])
    op.create_foreign_key('communication_deliveries_communication_draft_id_fkey', 'communication_deliveries', 'communication_drafts', ['communication_draft_id'], ['id'])
    op.create_foreign_key('communication_deliveries_evidence_artifact_id_fkey', 'communication_deliveries', 'evidence_artifacts', ['evidence_artifact_id'], ['id'])
    op.create_foreign_key('communication_drafts_recipient_contact_id_fkey', 'communication_drafts', 'client_contacts', ['recipient_contact_id'], ['id'])
    op.create_foreign_key('communication_drafts_template_version_id_fkey', 'communication_drafts', 'template_versions', ['template_version_id'], ['id'])
    op.create_foreign_key('completion_case_links_authority_case_id_fkey', 'completion_case_links', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('completion_case_links_construction_completion_context_id_fkey', 'completion_case_links', 'construction_completion_contexts', ['construction_completion_context_id'], ['id'])
    op.create_foreign_key('completion_case_links_construction_execution_id_fkey', 'completion_case_links', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('completion_case_links_project_id_fkey', 'completion_case_links', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('configuration_bundles_scenario_id_fkey', 'configuration_bundles', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('conflicts_field_definition_id_fkey', 'conflicts', 'field_definitions', ['field_definition_id'], ['id'])
    op.create_foreign_key('conflicts_project_id_fkey', 'conflicts', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_authority_notifi_evidence_document_version_id_fkey', 'construction_authority_notifications', 'document_versions', ['evidence_document_version_id'], ['id'])
    op.create_foreign_key('construction_authority_notificat_construction_execution_id_fkey', 'construction_authority_notifications', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('construction_authority_notification_obligation_instance_id_fkey', 'construction_authority_notifications', 'construction_obligation_instances', ['obligation_instance_id'], ['id'])
    op.create_foreign_key('construction_authority_notifications_authority_case_id_fkey', 'construction_authority_notifications', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('construction_authority_notifications_project_id_fkey', 'construction_authority_notifications', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_authority_notifications_work_control_event_id_fkey', 'construction_authority_notifications', 'construction_work_control_events', ['work_control_event_id'], ['id'])
    op.create_foreign_key('construction_completion_conte_authority_approved_design_sn_fkey', 'construction_completion_contexts', 'authority_approved_design_snapshots', ['authority_approved_design_snapshot_id'], ['id'])
    op.create_foreign_key('construction_completion_conte_construction_design_snapshot_fkey', 'construction_completion_contexts', 'construction_design_snapshots', ['construction_design_snapshot_id'], ['id'])
    op.create_foreign_key('construction_completion_contexts_construction_execution_id_fkey', 'construction_completion_contexts', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('construction_completion_contexts_project_id_fkey', 'construction_completion_contexts', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_correspondence_authority_case_id_fkey', 'construction_correspondence', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('construction_correspondence_construction_execution_id_fkey', 'construction_correspondence', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('construction_correspondence_document_version_id_fkey', 'construction_correspondence', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('construction_correspondence_project_id_fkey', 'construction_correspondence', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_correspondence_recipient_party_id_fkey', 'construction_correspondence', 'parties', ['recipient_party_id'], ['id'])
    op.create_foreign_key('construction_correspondence_sender_party_id_fkey', 'construction_correspondence', 'parties', ['sender_party_id'], ['id'])
    op.create_foreign_key('construction_design_snapshots_approved_design_baseline_id_fkey', 'construction_design_snapshots', 'approved_design_baselines', ['approved_design_baseline_id'], ['id'])
    op.create_foreign_key('construction_design_snapshots_authority_approved_design_sn_fkey', 'construction_design_snapshots', 'authority_approved_design_snapshots', ['authority_approved_design_snapshot_id'], ['id'])
    op.create_foreign_key('construction_design_snapshots_construction_execution_id_fkey', 'construction_design_snapshots', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('construction_design_snapshots_project_id_fkey', 'construction_design_snapshots', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_design_snapshots_supersedes_id_fkey', 'construction_design_snapshots', 'construction_design_snapshots', ['supersedes_id'], ['id'])
    op.create_foreign_key('construction_evidence_links_construction_execution_id_fkey', 'construction_evidence_links', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('construction_evidence_links_document_version_id_fkey', 'construction_evidence_links', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('construction_evidence_links_material_test_id_fkey', 'construction_evidence_links', 'engineering_material_tests', ['material_test_id'], ['id'])
    op.create_foreign_key('construction_evidence_links_physical_evidence_item_id_fkey', 'construction_evidence_links', 'physical_evidence_items', ['physical_evidence_item_id'], ['id'])
    op.create_foreign_key('construction_evidence_links_project_id_fkey', 'construction_evidence_links', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_executions_authority_case_id_fkey', 'construction_executions', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('construction_executions_contract_id_fkey', 'construction_executions', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('construction_executions_contract_revision_id_fkey', 'construction_executions', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('construction_executions_project_id_fkey', 'construction_executions', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_inspections_authority_case_id_fkey', 'construction_inspections', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('construction_inspections_construction_execution_id_fkey', 'construction_inspections', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('construction_inspections_inspector_party_id_fkey', 'construction_inspections', 'parties', ['inspector_party_id'], ['id'])
    op.create_foreign_key('construction_inspections_project_id_fkey', 'construction_inspections', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_issues_authority_case_finding_id_fkey', 'construction_issues', 'authority_case_findings', ['authority_case_finding_id'], ['id'])
    op.create_foreign_key('construction_issues_construction_execution_id_fkey', 'construction_issues', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('construction_issues_design_change_request_id_fkey', 'construction_issues', 'design_change_requests', ['design_change_request_id'], ['id'])
    op.create_foreign_key('construction_issues_project_id_fkey', 'construction_issues', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_issues_requirement_instance_id_fkey', 'construction_issues', 'requirement_instances', ['requirement_instance_id'], ['id'])
    op.create_foreign_key('construction_obligation_definit_source_document_version_id_fkey', 'construction_obligation_definitions', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('construction_obligation_definiti_requirement_definition_id_fkey', 'construction_obligation_definitions', 'requirement_definitions', ['requirement_definition_id'], ['id'])
    op.create_foreign_key('construction_obligation_definitions_authority_case_id_fkey', 'construction_obligation_definitions', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('construction_obligation_definitions_policy_version_id_fkey', 'construction_obligation_definitions', 'requirement_policy_versions', ['policy_version_id'], ['id'])
    op.create_foreign_key('construction_obligation_definitions_project_id_fkey', 'construction_obligation_definitions', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_obligation_instance_construction_execution_id_fkey', 'construction_obligation_instances', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('construction_obligation_instances_authority_case_id_fkey', 'construction_obligation_instances', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('construction_obligation_instances_definition_id_fkey', 'construction_obligation_instances', 'construction_obligation_definitions', ['definition_id'], ['id'])
    op.create_foreign_key('construction_obligation_instances_project_id_fkey', 'construction_obligation_instances', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_obligation_participant_obligation_instance_id_fkey', 'construction_obligation_participants', 'construction_obligation_instances', ['obligation_instance_id'], ['id'])
    op.create_foreign_key('construction_obligation_participants_party_id_fkey', 'construction_obligation_participants', 'parties', ['party_id'], ['id'])
    op.create_foreign_key('construction_obligation_participants_project_id_fkey', 'construction_obligation_participants', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_party_assignments_authority_case_id_fkey', 'construction_party_assignments', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('construction_party_assignments_construction_execution_id_fkey', 'construction_party_assignments', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('construction_party_assignments_party_id_fkey', 'construction_party_assignments', 'parties', ['party_id'], ['id'])
    op.create_foreign_key('construction_party_assignments_party_role_assignment_id_fkey', 'construction_party_assignments', 'party_role_assignments', ['party_role_assignment_id'], ['id'])
    op.create_foreign_key('construction_party_assignments_professional_credential_id_fkey', 'construction_party_assignments', 'professional_credentials', ['professional_credential_id'], ['id'])
    op.create_foreign_key('construction_party_assignments_project_id_fkey', 'construction_party_assignments', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_party_assignments_source_document_version_id_fkey', 'construction_party_assignments', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('construction_start_authorizat_authority_approved_design_sn_fkey', 'construction_start_authorizations', 'authority_approved_design_snapshots', ['authority_approved_design_snapshot_id'], ['id'])
    op.create_foreign_key('construction_start_authorizat_construction_design_snapshot_fkey', 'construction_start_authorizations', 'construction_design_snapshots', ['construction_design_snapshot_id'], ['id'])
    op.create_foreign_key('construction_start_authorization_construction_execution_id_fkey', 'construction_start_authorizations', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('construction_start_authorizations_contract_revision_id_fkey', 'construction_start_authorizations', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('construction_start_authorizations_project_activation_id_fkey', 'construction_start_authorizations', 'project_activations', ['project_activation_id'], ['id'])
    op.create_foreign_key('construction_start_authorizations_project_id_fkey', 'construction_start_authorizations', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_start_readiness_construction_execution_id_fkey', 'construction_start_readiness', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('construction_start_readiness_project_id_fkey', 'construction_start_readiness', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_work_control_eve_evidence_document_version_id_fkey', 'construction_work_control_events', 'document_versions', ['evidence_document_version_id'], ['id'])
    op.create_foreign_key('construction_work_control_events_construction_execution_id_fkey', 'construction_work_control_events', 'construction_executions', ['construction_execution_id'], ['id'])
    op.create_foreign_key('construction_work_control_events_project_id_fkey', 'construction_work_control_events', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('construction_work_control_events_start_authorization_id_fkey', 'construction_work_control_events', 'construction_start_authorizations', ['start_authorization_id'], ['id'])
    op.create_foreign_key('contact_points_authority_case_id_fkey', 'contact_points', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('contact_points_party_id_fkey', 'contact_points', 'parties', ['party_id'], ['id'])
    op.create_foreign_key('contact_points_project_id_fkey', 'contact_points', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('contact_points_source_document_version_id_fkey', 'contact_points', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('contract_admin_evidence_contract_id_fkey', 'contract_admin_evidence', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('contract_admin_evidence_contract_revision_id_fkey', 'contract_admin_evidence', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('contract_admin_evidence_document_version_id_fkey', 'contract_admin_evidence', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('contract_admin_inputs_contract_id_fkey', 'contract_admin_inputs', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('contract_administrative_closures_contract_id_fkey', 'contract_administrative_closures', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('contract_administrative_closures_contract_revision_id_fkey', 'contract_administrative_closures', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('contract_administrative_closures_project_id_fkey', 'contract_administrative_closures', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('contract_approvals_approval_id_fkey', 'contract_approvals', 'approvals', ['approval_id'], ['id'])
    op.create_foreign_key('contract_approvals_contract_revision_id_fkey', 'contract_approvals', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('contract_client_input_requireme_source_document_version_id_fkey', 'contract_client_input_requirements', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('contract_client_input_requirements_contract_id_fkey', 'contract_client_input_requirements', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('contract_client_input_requirements_contract_revision_id_fkey', 'contract_client_input_requirements', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('contract_deliverable_commitment_source_document_version_id_fkey', 'contract_deliverable_commitments', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('contract_deliverable_commitments_contract_id_fkey', 'contract_deliverable_commitments', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('contract_deliverable_commitments_contract_revision_id_fkey', 'contract_deliverable_commitments', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('contract_execution_evidence_contract_revision_id_fkey', 'contract_execution_evidence', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('contract_execution_evidence_evidence_artifact_id_fkey', 'contract_execution_evidence', 'evidence_artifacts', ['evidence_artifact_id'], ['id'])
    op.create_foreign_key('contract_milestones_contract_id_fkey', 'contract_milestones', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('contract_milestones_contract_revision_id_fkey', 'contract_milestones', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('contract_payment_terms_contract_id_fkey', 'contract_payment_terms', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('contract_payment_terms_contract_revision_id_fkey', 'contract_payment_terms', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('contract_payment_terms_source_document_version_id_fkey', 'contract_payment_terms', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('contract_revisions_accepted_proposal_revision_id_fkey', 'contract_revisions', 'proposal_accepted_revisions', ['accepted_proposal_revision_id'], ['id'])
    op.create_foreign_key('contract_revisions_contract_id_fkey', 'contract_revisions', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('contract_revisions_controlling_quotation_revision_id_fkey', 'contract_revisions', 'quotation_revisions', ['controlling_quotation_revision_id'], ['id'])
    op.create_foreign_key('contract_revisions_rendered_artifact_id_fkey', 'contract_revisions', 'rendered_artifacts', ['rendered_artifact_id'], ['id'])
    op.create_foreign_key('contract_revisions_template_version_id_fkey', 'contract_revisions', 'template_versions', ['template_version_id'], ['id'])
    op.create_foreign_key('contract_template_snapshots_contract_id_fkey', 'contract_template_snapshots', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('contract_template_snapshots_contract_revision_id_fkey', 'contract_template_snapshots', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('contract_template_snapshots_document_version_id_fkey', 'contract_template_snapshots', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('contract_template_snapshots_master_content_id_fkey', 'contract_template_snapshots', 'master_content_items', ['master_content_id'], ['id'])
    op.create_foreign_key('contracts_accepted_proposal_revision_id_fkey', 'contracts', 'proposal_accepted_revisions', ['accepted_proposal_revision_id'], ['id'])
    op.create_foreign_key('contracts_client_account_id_fkey', 'contracts', 'client_accounts', ['client_account_id'], ['id'])
    op.create_foreign_key('contracts_project_id_fkey', 'contracts', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('contracts_proposal_id_fkey', 'contracts', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('contracts_quotation_id_fkey', 'contracts', 'quotations', ['quotation_id'], ['id'])
    op.create_foreign_key('control_runs_control_definition_id_fkey', 'control_runs', 'control_definitions', ['control_definition_id'], ['id'])
    op.create_foreign_key('control_runs_package_id_fkey', 'control_runs', 'packages', ['package_id'], ['id'])
    op.create_foreign_key('control_runs_preparation_revision_id_fkey', 'control_runs', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('control_runs_project_id_fkey', 'control_runs', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('corpus_case_results_corpus_case_id_fkey', 'corpus_case_results', 'corpus_cases', ['corpus_case_id'], ['id'])
    op.create_foreign_key('corpus_case_results_corpus_run_id_fkey', 'corpus_case_results', 'corpus_runs', ['corpus_run_id'], ['id'])
    op.create_foreign_key('corpus_cases_corpus_run_id_fkey', 'corpus_cases', 'corpus_runs', ['corpus_run_id'], ['id'])
    op.create_foreign_key('corpus_cases_document_version_id_fkey', 'corpus_cases', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('definition_revisions_definition_id_fkey', 'definition_revisions', 'definition_entries', ['definition_id'], ['id'])
    op.create_foreign_key('design_change_requests_from_baseline_id_fkey', 'design_change_requests', 'approved_design_baselines', ['from_baseline_id'], ['id'])
    op.create_foreign_key('design_change_requests_next_baseline_id_fkey', 'design_change_requests', 'approved_design_baselines', ['next_baseline_id'], ['id'])
    op.create_foreign_key('design_change_requests_project_id_fkey', 'design_change_requests', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('document_classifications_document_version_id_fkey', 'document_classifications', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('document_requests_checklist_item_id_fkey', 'document_requests', 'checklist_items', ['checklist_item_id'], ['id'])
    op.create_foreign_key('document_requests_client_account_id_fkey', 'document_requests', 'client_accounts', ['client_account_id'], ['id'])
    op.create_foreign_key('document_requests_requested_from_contact_id_fkey', 'document_requests', 'client_contacts', ['requested_from_contact_id'], ['id'])
    op.create_foreign_key('document_validities_document_version_id_fkey', 'document_validities', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('document_versions_document_id_fkey', 'document_versions', 'documents', ['document_id'], ['id'])
    op.create_foreign_key('documents_project_id_fkey', 'documents', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('drawing_metadata_controls_field_definition_id_fkey', 'drawing_metadata_controls', 'field_definitions', ['field_definition_id'], ['id'])
    op.create_foreign_key('drawing_metadata_controls_scenario_id_fkey', 'drawing_metadata_controls', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('drawing_review_cycles_input_drawing_version_id_fkey', 'drawing_review_cycles', 'document_versions', ['input_drawing_version_id'], ['id'])
    op.create_foreign_key('drawing_review_cycles_output_drawing_version_id_fkey', 'drawing_review_cycles', 'document_versions', ['output_drawing_version_id'], ['id'])
    op.create_foreign_key('drawing_review_cycles_project_id_fkey', 'drawing_review_cycles', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('drawing_review_cycles_review_run_id_fkey', 'drawing_review_cycles', 'engineering_review_runs', ['review_run_id'], ['id'])
    op.create_foreign_key('engineering_ai_comment_artifac_drawing_document_version_id_fkey', 'engineering_ai_comment_artifacts', 'document_versions', ['drawing_document_version_id'], ['id'])
    op.create_foreign_key('engineering_ai_comment_artifacts_project_id_fkey', 'engineering_ai_comment_artifacts', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_ai_comment_artifacts_review_id_fkey', 'engineering_ai_comment_artifacts', 'project_engineering_reviews', ['review_id'], ['id'])
    op.create_foreign_key('engineering_ai_comment_artifacts_revision_id_fkey', 'engineering_ai_comment_artifacts', 'engineering_deliverable_revisions', ['revision_id'], ['id'])
    op.create_foreign_key('engineering_authority_finding_links_authority_finding_id_fkey', 'engineering_authority_finding_links', 'authority_case_findings', ['authority_finding_id'], ['id'])
    op.create_foreign_key('engineering_authority_finding_links_project_id_fkey', 'engineering_authority_finding_links', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_authority_finding_links_review_category_id_fkey', 'engineering_authority_finding_links', 'engineering_review_categories', ['review_category_id'], ['id'])
    op.create_foreign_key('engineering_authority_finding_links_review_id_fkey', 'engineering_authority_finding_links', 'project_engineering_reviews', ['review_id'], ['id'])
    op.create_foreign_key('engineering_authority_finding_links_revision_id_fkey', 'engineering_authority_finding_links', 'engineering_deliverable_revisions', ['revision_id'], ['id'])
    op.create_foreign_key('engineering_calculation_recor_technical_rule_set_version_i_fkey', 'engineering_calculation_records', 'technical_rule_set_versions', ['technical_rule_set_version_id'], ['id'])
    op.create_foreign_key('engineering_calculation_records_project_id_fkey', 'engineering_calculation_records', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_calculation_records_revision_id_fkey', 'engineering_calculation_records', 'engineering_deliverable_revisions', ['revision_id'], ['id'])
    op.create_foreign_key('engineering_category_assignments_project_id_fkey', 'engineering_category_assignments', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_category_assignments_review_category_id_fkey', 'engineering_category_assignments', 'engineering_review_categories', ['review_category_id'], ['id'])
    op.create_foreign_key('engineering_category_assignments_work_package_id_fkey', 'engineering_category_assignments', 'engineering_work_packages', ['work_package_id'], ['id'])
    op.create_foreign_key('engineering_comments_drawing_document_version_id_fkey', 'engineering_comments', 'document_versions', ['drawing_document_version_id'], ['id'])
    op.create_foreign_key('engineering_comments_engineering_review_run_id_fkey', 'engineering_comments', 'engineering_review_runs', ['engineering_review_run_id'], ['id'])
    op.create_foreign_key('engineering_comments_regulation_version_id_fkey', 'engineering_comments', 'regulation_versions', ['regulation_version_id'], ['id'])
    op.create_foreign_key('engineering_comments_supersedes_comment_id_fkey', 'engineering_comments', 'engineering_comments', ['supersedes_comment_id'], ['id'])
    op.create_foreign_key('engineering_deliverable_revisions_deliverable_id_fkey', 'engineering_deliverable_revisions', 'engineering_deliverables', ['deliverable_id'], ['id'])
    op.create_foreign_key('engineering_deliverable_revisions_project_id_fkey', 'engineering_deliverable_revisions', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_deliverable_revisions_supersedes_revision_id_fkey', 'engineering_deliverable_revisions', 'engineering_deliverable_revisions', ['supersedes_revision_id'], ['id'])
    op.create_foreign_key('engineering_deliverables_current_revision_id_fkey', 'engineering_deliverables', 'engineering_deliverable_revisions', ['current_revision_id'], ['id'])
    op.create_foreign_key('engineering_deliverables_project_id_fkey', 'engineering_deliverables', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_deliverables_work_package_id_fkey', 'engineering_deliverables', 'engineering_work_packages', ['work_package_id'], ['id'])
    op.create_foreign_key('engineering_internal_review_co_drawing_document_version_id_fkey', 'engineering_internal_review_comments', 'document_versions', ['drawing_document_version_id'], ['id'])
    op.create_foreign_key('engineering_internal_review_comments_project_id_fkey', 'engineering_internal_review_comments', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_internal_review_comments_review_id_fkey', 'engineering_internal_review_comments', 'project_engineering_reviews', ['review_id'], ['id'])
    op.create_foreign_key('engineering_internal_review_comments_revision_id_fkey', 'engineering_internal_review_comments', 'engineering_deliverable_revisions', ['revision_id'], ['id'])
    op.create_foreign_key('engineering_material_tests_certificate_document_version_id_fkey', 'engineering_material_tests', 'document_versions', ['certificate_document_version_id'], ['id'])
    op.create_foreign_key('engineering_material_tests_laboratory_party_id_fkey', 'engineering_material_tests', 'parties', ['laboratory_party_id'], ['id'])
    op.create_foreign_key('engineering_material_tests_project_id_fkey', 'engineering_material_tests', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_material_tests_revision_id_fkey', 'engineering_material_tests', 'engineering_deliverable_revisions', ['revision_id'], ['id'])
    op.create_foreign_key('engineering_professional_approv_professional_credential_id_fkey', 'engineering_professional_approvals', 'professional_credentials', ['professional_credential_id'], ['id'])
    op.create_foreign_key('engineering_professional_approvals_approver_party_id_fkey', 'engineering_professional_approvals', 'parties', ['approver_party_id'], ['id'])
    op.create_foreign_key('engineering_professional_approvals_project_id_fkey', 'engineering_professional_approvals', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_professional_approvals_revision_id_fkey', 'engineering_professional_approvals', 'engineering_deliverable_revisions', ['revision_id'], ['id'])
    op.create_foreign_key('engineering_project_members_project_id_fkey', 'engineering_project_members', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_renditions_document_version_id_fkey', 'engineering_renditions', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('engineering_renditions_project_id_fkey', 'engineering_renditions', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_renditions_revision_id_fkey', 'engineering_renditions', 'engineering_deliverable_revisions', ['revision_id'], ['id'])
    op.create_foreign_key('engineering_renditions_source_rendition_id_fkey', 'engineering_renditions', 'engineering_renditions', ['source_rendition_id'], ['id'])
    op.create_foreign_key('engineering_review_findings_project_id_fkey', 'engineering_review_findings', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_review_findings_review_id_fkey', 'engineering_review_findings', 'project_engineering_reviews', ['review_id'], ['id'])
    op.create_foreign_key('engineering_review_runs_drawing_document_version_id_fkey', 'engineering_review_runs', 'document_versions', ['drawing_document_version_id'], ['id'])
    op.create_foreign_key('engineering_review_runs_engineering_review_id_fkey', 'engineering_review_runs', 'engineering_reviews', ['engineering_review_id'], ['id'])
    op.create_foreign_key('engineering_review_runs_review_scope_id_fkey', 'engineering_review_runs', 'engineering_review_scopes', ['review_scope_id'], ['id'])
    op.create_foreign_key('engineering_review_scopes_engineering_review_id_fkey', 'engineering_review_scopes', 'engineering_reviews', ['engineering_review_id'], ['id'])
    op.create_foreign_key('engineering_review_scopes_project_id_fkey', 'engineering_review_scopes', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_reviews_authorized_engineer_user_id_fkey', 'engineering_reviews', 'users', ['authorized_engineer_user_id'], ['id'])
    op.create_foreign_key('engineering_reviews_current_drawing_version_id_fkey', 'engineering_reviews', 'document_versions', ['current_drawing_version_id'], ['id'])
    op.create_foreign_key('engineering_reviews_current_scope_id_fkey', 'engineering_reviews', 'engineering_review_scopes', ['current_scope_id'], ['id'])
    op.create_foreign_key('engineering_reviews_drawing_document_id_fkey', 'engineering_reviews', 'documents', ['drawing_document_id'], ['id'])
    op.create_foreign_key('engineering_reviews_project_id_fkey', 'engineering_reviews', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_technical_checks_project_id_fkey', 'engineering_technical_checks', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('engineering_technical_checks_revision_id_fkey', 'engineering_technical_checks', 'engineering_deliverable_revisions', ['revision_id'], ['id'])
    op.create_foreign_key('engineering_technical_checks_technical_rule_id_fkey', 'engineering_technical_checks', 'technical_rules', ['technical_rule_id'], ['id'])
    op.create_foreign_key('engineering_technical_checks_technical_rule_set_version_id_fkey', 'engineering_technical_checks', 'technical_rule_set_versions', ['technical_rule_set_version_id'], ['id'])
    op.create_foreign_key('engineering_work_packages_project_id_fkey', 'engineering_work_packages', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('excel_project_rows_project_id_fkey', 'excel_project_rows', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('excel_projection_rules_scenario_id_fkey', 'excel_projection_rules', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('excel_projections_configuration_bundle_id_fkey', 'excel_projections', 'configuration_bundles', ['configuration_bundle_id'], ['id'])
    op.create_foreign_key('excel_projections_project_id_fkey', 'excel_projections', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('excel_projections_source_verified_assertion_id_fkey', 'excel_projections', 'verified_assertions', ['source_verified_assertion_id'], ['id'])
    op.create_foreign_key('excel_projections_target_rendering_rule_id_fkey', 'excel_projections', 'target_rendering_rules', ['target_rendering_rule_id'], ['id'])
    op.create_foreign_key('external_bodies_jurisdiction_id_fkey', 'external_bodies', 'jurisdictions', ['jurisdiction_id'], ['id'])
    op.create_foreign_key('external_body_units_external_body_id_fkey', 'external_body_units', 'external_bodies', ['external_body_id'], ['id'])
    op.create_foreign_key('external_interaction_profiles_external_body_id_fkey', 'external_interaction_profiles', 'external_bodies', ['external_body_id'], ['id'])
    op.create_foreign_key('external_mutation_observations_application_id_fkey', 'external_mutation_observations', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('external_mutation_observations_monitoring_run_id_fkey', 'external_mutation_observations', 'monitoring_runs', ['monitoring_run_id'], ['id'])
    op.create_foreign_key('external_submission_snapshots_authority_case_id_fkey', 'external_submission_snapshots', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('external_submission_snapshots_evidence_document_version_id_fkey', 'external_submission_snapshots', 'document_versions', ['evidence_document_version_id'], ['id'])
    op.create_foreign_key('external_submission_snapshots_submission_attempt_id_fkey', 'external_submission_snapshots', 'submission_attempts', ['submission_attempt_id'], ['id'])
    op.create_foreign_key('external_system_links_project_id_fkey', 'external_system_links', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('field_authority_rules_field_definition_id_fkey', 'field_authority_rules', 'field_definitions', ['field_definition_id'], ['id'])
    op.create_foreign_key('field_authority_rules_scenario_id_fkey', 'field_authority_rules', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('field_observations_document_version_id_fkey', 'field_observations', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('field_observations_field_definition_id_fkey', 'field_observations', 'field_definitions', ['field_definition_id'], ['id'])
    op.create_foreign_key('field_observations_project_id_fkey', 'field_observations', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('finance_evidence_invoice_id_fkey', 'finance_evidence', 'invoices', ['invoice_id'], ['id'])
    op.create_foreign_key('financial_account_masters_legal_entity_party_id_fkey', 'financial_account_masters', 'parties', ['legal_entity_party_id'], ['id'])
    op.create_foreign_key('financial_account_versions_financial_account_master_id_fkey', 'financial_account_versions', 'financial_account_masters', ['financial_account_master_id'], ['id'])
    op.create_foreign_key('financial_settlement_contexts_contract_id_fkey', 'financial_settlement_contexts', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('financial_settlement_contexts_project_id_fkey', 'financial_settlement_contexts', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('financial_settlement_records_context_id_fkey', 'financial_settlement_records', 'financial_settlement_contexts', ['context_id'], ['id'])
    op.create_foreign_key('financial_settlement_records_contract_id_fkey', 'financial_settlement_records', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('financial_settlement_records_project_id_fkey', 'financial_settlement_records', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('finding_closure_evaluations_finding_id_fkey', 'finding_closure_evaluations', 'findings', ['finding_id'], ['id'])
    op.create_foreign_key('finding_closure_evaluations_resolution_id_fkey', 'finding_closure_evaluations', 'finding_resolutions', ['resolution_id'], ['id'])
    op.create_foreign_key('finding_disputes_finding_id_fkey', 'finding_disputes', 'findings', ['finding_id'], ['id'])
    op.create_foreign_key('finding_history_links_current_finding_id_fkey', 'finding_history_links', 'findings', ['current_finding_id'], ['id'])
    op.create_foreign_key('finding_history_links_preparation_revision_id_fkey', 'finding_history_links', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('finding_history_links_prior_finding_id_fkey', 'finding_history_links', 'findings', ['prior_finding_id'], ['id'])
    op.create_foreign_key('finding_history_links_submission_cycle_id_fkey', 'finding_history_links', 'submission_cycles', ['submission_cycle_id'], ['id'])
    op.create_foreign_key('finding_prevention_controls_finding_code_id_fkey', 'finding_prevention_controls', 'finding_codes', ['finding_code_id'], ['id'])
    op.create_foreign_key('finding_recurrence_analysis_items_run_id_fkey', 'finding_recurrence_analysis_items', 'finding_recurrence_analysis_runs', ['run_id'], ['id'])
    op.create_foreign_key('finding_recurrence_analysis_runs_scenario_id_fkey', 'finding_recurrence_analysis_runs', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('finding_reopen_events_finding_id_fkey', 'finding_reopen_events', 'findings', ['finding_id'], ['id'])
    op.create_foreign_key('finding_reopen_events_prior_resolution_id_fkey', 'finding_reopen_events', 'finding_resolutions', ['prior_resolution_id'], ['id'])
    op.create_foreign_key('finding_reopen_events_source_authority_event_id_fkey', 'finding_reopen_events', 'authority_events', ['source_authority_event_id'], ['id'])
    op.create_foreign_key('finding_resolution_evidence_finding_resolution_id_fkey', 'finding_resolution_evidence', 'finding_resolutions', ['finding_resolution_id'], ['id'])
    op.create_foreign_key('finding_resolutions_finding_id_fkey', 'finding_resolutions', 'findings', ['finding_id'], ['id'])
    op.create_foreign_key('finding_resolutions_prior_resolution_id_fkey', 'finding_resolutions', 'finding_resolutions', ['prior_resolution_id'], ['id'])
    op.create_foreign_key('finding_routing_rules_finding_code_id_fkey', 'finding_routing_rules', 'finding_codes', ['finding_code_id'], ['id'])
    op.create_foreign_key('finding_routing_rules_preferred_user_id_fkey', 'finding_routing_rules', 'users', ['preferred_user_id'], ['id'])
    op.create_foreign_key('findings_application_id_fkey', 'findings', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('findings_assignee_user_id_fkey', 'findings', 'users', ['assignee_user_id'], ['id'])
    op.create_foreign_key('findings_authority_event_id_fkey', 'findings', 'authority_events', ['authority_event_id'], ['id'])
    op.create_foreign_key('findings_authority_precheck_run_id_fkey', 'findings', 'authority_precheck_runs', ['authority_precheck_run_id'], ['id'])
    op.create_foreign_key('findings_contract_id_fkey', 'findings', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('findings_finding_code_id_fkey', 'findings', 'finding_codes', ['finding_code_id'], ['id'])
    op.create_foreign_key('findings_permit_id_fkey', 'findings', 'permit_applications', ['permit_id'], ['id'])
    op.create_foreign_key('findings_preparation_revision_id_fkey', 'findings', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('findings_project_id_fkey', 'findings', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('findings_proposal_id_fkey', 'findings', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('findings_submission_cycle_id_fkey', 'findings', 'submission_cycles', ['submission_cycle_id'], ['id'])
    op.create_foreign_key('form_automation_profiles_master_content_item_id_fkey', 'form_automation_profiles', 'master_content_items', ['master_content_item_id'], ['id'])
    op.create_foreign_key('form_automation_profiles_source_document_version_id_fkey', 'form_automation_profiles', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('form_instances_mapping_release_id_fkey', 'form_instances', 'form_mapping_releases', ['mapping_release_id'], ['id'])
    op.create_foreign_key('form_instances_master_content_item_id_fkey', 'form_instances', 'master_content_items', ['master_content_item_id'], ['id'])
    op.create_foreign_key('form_instances_profile_id_fkey', 'form_instances', 'form_automation_profiles', ['profile_id'], ['id'])
    op.create_foreign_key('form_instances_source_document_version_id_fkey', 'form_instances', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('form_mapping_release_qa_gates_mapping_release_id_fkey', 'form_mapping_release_qa_gates', 'form_mapping_releases', ['mapping_release_id'], ['id'])
    op.create_foreign_key('form_mapping_release_qa_gates_qa_run_id_fkey', 'form_mapping_release_qa_gates', 'form_qa_runs', ['qa_run_id'], ['id'])
    op.create_foreign_key('form_mapping_releases_master_content_item_id_fkey', 'form_mapping_releases', 'master_content_items', ['master_content_item_id'], ['id'])
    op.create_foreign_key('form_mapping_releases_profile_id_fkey', 'form_mapping_releases', 'form_automation_profiles', ['profile_id'], ['id'])
    op.create_foreign_key('form_mapping_releases_source_document_version_id_fkey', 'form_mapping_releases', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('form_mapping_rules_mapping_release_id_fkey', 'form_mapping_rules', 'form_mapping_releases', ['mapping_release_id'], ['id'])
    op.create_foreign_key('form_qa_runs_generated_artifact_id_fkey', 'form_qa_runs', 'generated_artifacts', ['generated_artifact_id'], ['id'])
    op.create_foreign_key('form_qa_runs_mapping_release_id_fkey', 'form_qa_runs', 'form_mapping_releases', ['mapping_release_id'], ['id'])
    op.create_foreign_key('form_signature_requirements_form_instance_id_fkey', 'form_signature_requirements', 'form_instances', ['form_instance_id'], ['id'])
    op.create_foreign_key('form_template_versions_template_id_fkey', 'form_template_versions', 'form_templates', ['template_id'], ['id'])
    op.create_foreign_key('form_validation_results_generated_artifact_id_fkey', 'form_validation_results', 'generated_artifacts', ['generated_artifact_id'], ['id'])
    op.create_foreign_key('generated_artifacts_form_instance_id_fkey', 'generated_artifacts', 'form_instances', ['form_instance_id'], ['id'])
    op.create_foreign_key('generated_artifacts_mapping_release_id_fkey', 'generated_artifacts', 'form_mapping_releases', ['mapping_release_id'], ['id'])
    op.create_foreign_key('generated_artifacts_profile_id_fkey', 'generated_artifacts', 'form_automation_profiles', ['profile_id'], ['id'])
    op.create_foreign_key('generated_artifacts_source_document_version_id_fkey', 'generated_artifacts', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('gold_document_labels_document_version_id_fkey', 'gold_document_labels', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('gold_field_labels_document_version_id_fkey', 'gold_field_labels', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('gold_field_labels_field_definition_id_fkey', 'gold_field_labels', 'field_definitions', ['field_definition_id'], ['id'])
    op.create_foreign_key('grid_field_diffs_row_result_id_fkey', 'grid_field_diffs', 'grid_row_reconciliation_results', ['row_result_id'], ['id'])
    op.create_foreign_key('grid_persistence_evidence_post_save_snapshot_id_fkey', 'grid_persistence_evidence', 'portal_snapshots', ['post_save_snapshot_id'], ['id'])
    op.create_foreign_key('grid_persistence_evidence_preparation_revision_id_fkey', 'grid_persistence_evidence', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('grid_persistence_evidence_reopened_snapshot_id_fkey', 'grid_persistence_evidence', 'portal_snapshots', ['reopened_snapshot_id'], ['id'])
    op.create_foreign_key('grid_reconciliation_runs_portal_snapshot_id_fkey', 'grid_reconciliation_runs', 'portal_snapshots', ['portal_snapshot_id'], ['id'])
    op.create_foreign_key('grid_reconciliation_runs_preparation_revision_id_fkey', 'grid_reconciliation_runs', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('grid_row_reconciliation_results_run_id_fkey', 'grid_row_reconciliation_results', 'grid_reconciliation_runs', ['run_id'], ['id'])
    op.create_foreign_key('handover_acceptances_accepted_by_party_id_fkey', 'handover_acceptances', 'parties', ['accepted_by_party_id'], ['id'])
    op.create_foreign_key('handover_acceptances_handover_package_revision_id_fkey', 'handover_acceptances', 'handover_package_revisions', ['handover_package_revision_id'], ['id'])
    op.create_foreign_key('handover_acceptances_signature_packet_id_fkey', 'handover_acceptances', 'signature_packets', ['signature_packet_id'], ['id'])
    op.create_foreign_key('handover_acceptances_signed_form_document_version_id_fkey', 'handover_acceptances', 'document_versions', ['signed_form_document_version_id'], ['id'])
    op.create_foreign_key('handover_distribution_require_handover_package_revision_id_fkey', 'handover_distribution_requirements', 'handover_package_revisions', ['handover_package_revision_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('handover_distribution_requirements_recipient_party_id_fkey', 'handover_distribution_requirements', 'parties', ['recipient_party_id'], ['id'])
    op.create_foreign_key('handover_distributions_distribution_requirement_id_fkey', 'handover_distributions', 'handover_distribution_requirements', ['distribution_requirement_id'], ['id'])
    op.create_foreign_key('handover_distributions_evidence_document_version_id_fkey', 'handover_distributions', 'document_versions', ['evidence_document_version_id'], ['id'])
    op.create_foreign_key('handover_distributions_handover_package_revision_id_fkey', 'handover_distributions', 'handover_package_revisions', ['handover_package_revision_id'], ['id'])
    op.create_foreign_key('handover_distributions_recipient_party_id_fkey', 'handover_distributions', 'parties', ['recipient_party_id'], ['id'])
    op.create_foreign_key('handover_package_items_as_built_baseline_id_fkey', 'handover_package_items', 'as_built_baselines', ['as_built_baseline_id'], ['id'])
    op.create_foreign_key('handover_package_items_authority_case_id_fkey', 'handover_package_items', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('handover_package_items_document_version_id_fkey', 'handover_package_items', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('handover_package_items_engineering_rendition_id_fkey', 'handover_package_items', 'engineering_renditions', ['engineering_rendition_id'], ['id'])
    op.create_foreign_key('handover_package_items_engineering_revision_id_fkey', 'handover_package_items', 'engineering_deliverable_revisions', ['engineering_revision_id'], ['id'])
    op.create_foreign_key('handover_package_items_form_instance_id_fkey', 'handover_package_items', 'form_instances', ['form_instance_id'], ['id'])
    op.create_foreign_key('handover_package_items_handover_package_revision_id_fkey', 'handover_package_items', 'handover_package_revisions', ['handover_package_revision_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('handover_package_items_rendered_artifact_id_fkey', 'handover_package_items', 'rendered_artifacts', ['rendered_artifact_id'], ['id'])
    op.create_foreign_key('handover_package_revisions_approved_design_baseline_id_fkey', 'handover_package_revisions', 'approved_design_baselines', ['approved_design_baseline_id'], ['id'])
    op.create_foreign_key('handover_package_revisions_as_built_baseline_id_fkey', 'handover_package_revisions', 'as_built_baselines', ['as_built_baseline_id'], ['id'])
    op.create_foreign_key('handover_package_revisions_authority_case_outcome_id_fkey', 'handover_package_revisions', 'authority_case_outcomes', ['authority_case_outcome_id'], ['id'])
    op.create_foreign_key('handover_package_revisions_contract_id_fkey', 'handover_package_revisions', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('handover_package_revisions_contract_revision_id_fkey', 'handover_package_revisions', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('handover_package_revisions_handover_package_id_fkey', 'handover_package_revisions', 'handover_packages', ['handover_package_id'], ['id'])
    op.create_foreign_key('handover_package_revisions_policy_version_id_fkey', 'handover_package_revisions', 'handover_policy_versions', ['policy_version_id'], ['id'])
    op.create_foreign_key('handover_package_revisions_project_id_fkey', 'handover_package_revisions', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('handover_package_revisions_service_engagement_id_fkey', 'handover_package_revisions', 'service_engagements', ['service_engagement_id'], ['id'])
    op.create_foreign_key('handover_packages_contract_id_fkey', 'handover_packages', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('handover_packages_project_id_fkey', 'handover_packages', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('handover_packages_service_engagement_id_fkey', 'handover_packages', 'service_engagements', ['service_engagement_id'], ['id'])
    op.create_foreign_key('handover_participants_handover_package_revision_id_fkey', 'handover_participants', 'handover_package_revisions', ['handover_package_revision_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('handover_participants_party_id_fkey', 'handover_participants', 'parties', ['party_id'], ['id'])
    op.create_foreign_key('handover_policy_versions_source_document_version_id_fkey', 'handover_policy_versions', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('handover_punch_items_handover_package_revision_id_fkey', 'handover_punch_items', 'handover_package_revisions', ['handover_package_revision_id'], ['id'])
    op.create_foreign_key('handover_punch_items_package_item_id_fkey', 'handover_punch_items', 'handover_package_items', ['package_item_id'], ['id'])
    op.create_foreign_key('handover_punch_items_resolution_evidence_document_version__fkey', 'handover_punch_items', 'document_versions', ['resolution_evidence_document_version_id'], ['id'])
    op.create_foreign_key('handover_readiness_handover_package_revision_id_fkey', 'handover_readiness', 'handover_package_revisions', ['handover_package_revision_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('handover_receipts_distribution_id_fkey', 'handover_receipts', 'handover_distributions', ['distribution_id'], ['id'])
    op.create_foreign_key('handover_receipts_evidence_document_version_id_fkey', 'handover_receipts', 'document_versions', ['evidence_document_version_id'], ['id'])
    op.create_foreign_key('handover_receipts_received_by_party_id_fkey', 'handover_receipts', 'parties', ['received_by_party_id'], ['id'])
    op.create_foreign_key('handover_release_authorizatio_handover_package_revision_id_fkey', 'handover_release_authorizations', 'handover_package_revisions', ['handover_package_revision_id'], ['id'])
    op.create_foreign_key('handover_release_authorizations_readiness_id_fkey', 'handover_release_authorizations', 'handover_readiness', ['readiness_id'], ['id'])
    op.create_foreign_key('human_monitoring_captures_application_id_fkey', 'human_monitoring_captures', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('human_monitoring_captures_submission_cycle_id_fkey', 'human_monitoring_captures', 'submission_cycles', ['submission_cycle_id'], ['id'])
    op.create_foreign_key('human_portal_verifications_application_id_fkey', 'human_portal_verifications', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('human_portal_verifications_preparation_revision_id_fkey', 'human_portal_verifications', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('human_takeover_events_application_id_fkey', 'human_takeover_events', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('incident_impact_assessments_incident_id_fkey', 'incident_impact_assessments', 'integrity_incidents', ['incident_id'], ['id'])
    op.create_foreign_key('integrity_incidents_application_id_fkey', 'integrity_incidents', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('integrity_incidents_project_id_fkey', 'integrity_incidents', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('invoice_accept_records_invoice_revision_id_fkey', 'invoice_accept_records', 'invoice_revisions', ['invoice_revision_id'], ['id'])
    op.create_foreign_key('invoice_acknowledgments_invoice_id_fkey', 'invoice_acknowledgments', 'invoices', ['invoice_id'], ['id'])
    op.create_foreign_key('invoice_acknowledgments_issued_revision_id_fkey', 'invoice_acknowledgments', 'invoice_revisions', ['issued_revision_id'], ['id'])
    op.create_foreign_key('invoice_acknowledgments_source_document_version_id_fkey', 'invoice_acknowledgments', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('invoice_approval_records_invoice_revision_id_fkey', 'invoice_approval_records', 'invoice_revisions', ['invoice_revision_id'], ['id'])
    op.create_foreign_key('invoice_approval_records_source_document_version_id_fkey', 'invoice_approval_records', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('invoice_approvals_approval_id_fkey', 'invoice_approvals', 'approvals', ['approval_id'], ['id'])
    op.create_foreign_key('invoice_approvals_invoice_revision_id_fkey', 'invoice_approvals', 'invoice_revisions', ['invoice_revision_id'], ['id'])
    op.create_foreign_key('invoice_delivery_events_evidence_document_version_id_fkey', 'invoice_delivery_events', 'document_versions', ['evidence_document_version_id'], ['id'])
    op.create_foreign_key('invoice_delivery_events_invoice_id_fkey', 'invoice_delivery_events', 'invoices', ['invoice_id'], ['id'])
    op.create_foreign_key('invoice_delivery_events_issue_event_id_fkey', 'invoice_delivery_events', 'invoice_issue_events', ['issue_event_id'], ['id'])
    op.create_foreign_key('invoice_delivery_events_issued_revision_id_fkey', 'invoice_delivery_events', 'invoice_revisions', ['issued_revision_id'], ['id'])
    op.create_foreign_key('invoice_issue_events_financial_account_version_id_fkey', 'invoice_issue_events', 'financial_account_versions', ['financial_account_version_id'], ['id'])
    op.create_foreign_key('invoice_issue_events_invoice_id_fkey', 'invoice_issue_events', 'invoices', ['invoice_id'], ['id'])
    op.create_foreign_key('invoice_issue_events_invoice_revision_id_fkey', 'invoice_issue_events', 'invoice_revisions', ['invoice_revision_id'], ['id'])
    op.create_foreign_key('invoice_issue_events_rendered_artifact_id_fkey', 'invoice_issue_events', 'rendered_artifacts', ['rendered_artifact_id'], ['id'])
    op.create_foreign_key('invoice_issue_events_template_version_id_fkey', 'invoice_issue_events', 'template_versions', ['template_version_id'], ['id'])
    op.create_foreign_key('invoice_line_items_billing_milestone_id_fkey', 'invoice_line_items', 'billing_milestones', ['billing_milestone_id'], ['id'])
    op.create_foreign_key('invoice_line_items_invoice_revision_id_fkey', 'invoice_line_items', 'invoice_revisions', ['invoice_revision_id'], ['id'])
    op.create_foreign_key('invoice_milestones_contract_milestone_id_fkey', 'invoice_milestones', 'contract_milestones', ['contract_milestone_id'], ['id'])
    op.create_foreign_key('invoice_milestones_invoice_id_fkey', 'invoice_milestones', 'invoices', ['invoice_id'], ['id'])
    op.create_foreign_key('invoice_payment_allocations_invoice_id_fkey', 'invoice_payment_allocations', 'invoices', ['invoice_id'], ['id'])
    op.create_foreign_key('invoice_payment_allocations_payment_receipt_id_fkey', 'invoice_payment_allocations', 'payment_receipts', ['payment_receipt_id'], ['id'])
    op.create_foreign_key('invoice_references_invoice_revision_id_fkey', 'invoice_references', 'invoice_revisions', ['invoice_revision_id'], ['id'])
    op.create_foreign_key('invoice_references_source_document_version_id_fkey', 'invoice_references', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('invoice_requirement_decisions_contract_id_fkey', 'invoice_requirement_decisions', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('invoice_requirement_decisions_contract_revision_id_fkey', 'invoice_requirement_decisions', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('invoice_requirement_decisions_milestone_id_fkey', 'invoice_requirement_decisions', 'contract_milestones', ['milestone_id'], ['id'])
    op.create_foreign_key('invoice_revisions_billing_plan_revision_id_fkey', 'invoice_revisions', 'billing_plan_revisions', ['billing_plan_revision_id'], ['id'])
    op.create_foreign_key('invoice_revisions_controlling_contract_revision_id_fkey', 'invoice_revisions', 'contract_revisions', ['controlling_contract_revision_id'], ['id'])
    op.create_foreign_key('invoice_revisions_controlling_milestone_id_fkey', 'invoice_revisions', 'contract_milestones', ['controlling_milestone_id'], ['id'])
    op.create_foreign_key('invoice_revisions_invoice_id_fkey', 'invoice_revisions', 'invoices', ['invoice_id'], ['id'])
    op.create_foreign_key('invoice_revisions_rendered_artifact_id_fkey', 'invoice_revisions', 'rendered_artifacts', ['rendered_artifact_id'], ['id'])
    op.create_foreign_key('invoice_revisions_template_version_id_fkey', 'invoice_revisions', 'template_versions', ['template_version_id'], ['id'])
    op.create_foreign_key('invoices_billing_plan_id_fkey', 'invoices', 'billing_plans', ['billing_plan_id'], ['id'])
    op.create_foreign_key('invoices_client_account_id_fkey', 'invoices', 'client_accounts', ['client_account_id'], ['id'])
    op.create_foreign_key('invoices_contract_id_fkey', 'invoices', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('invoices_project_id_fkey', 'invoices', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('invoices_requirement_decision_id_fkey', 'invoices', 'invoice_requirement_decisions', ['requirement_decision_id'], ['id'])
    op.create_foreign_key('jurisdictions_parent_id_fkey', 'jurisdictions', 'jurisdictions', ['parent_id'], ['id'])
    op.create_foreign_key('lineage_edges_project_id_fkey', 'lineage_edges', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('master_content_applicability_external_body_id_fkey', 'master_content_applicability', 'external_bodies', ['external_body_id'], ['id'])
    op.create_foreign_key('master_content_applicability_jurisdiction_id_fkey', 'master_content_applicability', 'jurisdictions', ['jurisdiction_id'], ['id'])
    op.create_foreign_key('master_content_applicability_lifecycle_phase_id_fkey', 'master_content_applicability', 'regulatory_lifecycle_phases', ['lifecycle_phase_id'], ['id'])
    op.create_foreign_key('master_content_applicability_master_content_item_id_fkey', 'master_content_applicability', 'master_content_items', ['master_content_item_id'], ['id'])
    op.create_foreign_key('master_content_applicability_service_type_id_fkey', 'master_content_applicability', 'service_types', ['service_type_id'], ['id'])
    op.create_foreign_key('master_content_applicability_source_document_version_id_fkey', 'master_content_applicability', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('master_content_applicability_supersedes_id_fkey', 'master_content_applicability', 'master_content_applicability', ['supersedes_id'], ['id'])
    op.create_foreign_key('master_content_change_events_definition_id_fkey', 'master_content_change_events', 'definition_entries', ['definition_id'], ['id'])
    op.create_foreign_key('master_content_change_events_master_content_id_fkey', 'master_content_change_events', 'master_content_items', ['master_content_id'], ['id'])
    op.create_foreign_key('master_content_dependencies_bound_document_version_id_fkey', 'master_content_dependencies', 'document_versions', ['bound_document_version_id'], ['id'])
    op.create_foreign_key('master_content_dependencies_expected_current_version_id_fkey', 'master_content_dependencies', 'document_versions', ['expected_current_version_id'], ['id'])
    op.create_foreign_key('master_content_dependencies_master_content_id_fkey', 'master_content_dependencies', 'master_content_items', ['master_content_id'], ['id'])
    op.create_foreign_key('master_content_dependencies_project_id_fkey', 'master_content_dependencies', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('master_content_event_deliveries_event_id_fkey', 'master_content_event_deliveries', 'master_content_change_events', ['event_id'], ['id'])
    op.create_foreign_key('master_content_governance_profiles_master_content_item_id_fkey', 'master_content_governance_profiles', 'master_content_items', ['master_content_item_id'], ['id'])
    op.create_foreign_key('master_content_idempotency_document_version_id_fkey', 'master_content_idempotency', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('master_content_idempotency_master_content_id_fkey', 'master_content_idempotency', 'master_content_items', ['master_content_id'], ['id'])
    op.create_foreign_key('master_content_items_category_id_fkey', 'master_content_items', 'content_categories', ['category_id'], ['id'])
    op.create_foreign_key('master_content_items_current_document_version_id_fkey', 'master_content_items', 'document_versions', ['current_document_version_id'], ['id'])
    op.create_foreign_key('master_content_items_document_id_fkey', 'master_content_items', 'documents', ['document_id'], ['id'])
    op.create_foreign_key('master_content_module_bindings_definition_id_fkey', 'master_content_module_bindings', 'definition_entries', ['definition_id'], ['id'])
    op.create_foreign_key('master_content_module_bindings_master_content_id_fkey', 'master_content_module_bindings', 'master_content_items', ['master_content_id'], ['id'])
    op.create_foreign_key('master_content_quality_flags_document_version_id_fkey', 'master_content_quality_flags', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('master_content_quality_flags_master_content_item_id_fkey', 'master_content_quality_flags', 'master_content_items', ['master_content_item_id'], ['id'])
    op.create_foreign_key('master_content_readiness_assessment_master_content_item_id_fkey', 'master_content_readiness_assessments', 'master_content_items', ['master_content_item_id'], ['id'])
    op.create_foreign_key('master_content_readiness_assessments_document_version_id_fkey', 'master_content_readiness_assessments', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('master_content_source_provenance_document_version_id_fkey', 'master_content_source_provenance', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('master_content_source_sections_document_version_id_fkey', 'master_content_source_sections', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('master_content_source_sections_master_content_item_id_fkey', 'master_content_source_sections', 'master_content_items', ['master_content_item_id'], ['id'])
    op.create_foreign_key('material_change_events_project_id_fkey', 'material_change_events', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('mfa_challenge_events_auth_session_id_fkey', 'mfa_challenge_events', 'attended_auth_sessions', ['auth_session_id'], ['id'])
    op.create_foreign_key('mfa_challenge_events_completed_by_user_id_fkey', 'mfa_challenge_events', 'users', ['completed_by_user_id'], ['id'])
    op.create_foreign_key('minimum_package_definitions_scenario_id_fkey', 'minimum_package_definitions', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('monitoring_checks_monitoring_run_id_fkey', 'monitoring_checks', 'monitoring_runs', ['monitoring_run_id'], ['id'])
    op.create_foreign_key('monitoring_execution_decisions_monitoring_policy_id_fkey', 'monitoring_execution_decisions', 'monitoring_policies', ['monitoring_policy_id'], ['id'])
    op.create_foreign_key('monitoring_execution_decisions_run_id_fkey', 'monitoring_execution_decisions', 'monitoring_runs', ['run_id'], ['id'])
    op.create_foreign_key('monitoring_policies_application_id_fkey', 'monitoring_policies', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('monitoring_policies_scenario_id_fkey', 'monitoring_policies', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('monitoring_runs_application_id_fkey', 'monitoring_runs', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('monitoring_runs_monitoring_policy_id_fkey', 'monitoring_runs', 'monitoring_policies', ['monitoring_policy_id'], ['id'])
    op.create_foreign_key('monitoring_runs_submission_cycle_id_fkey', 'monitoring_runs', 'submission_cycles', ['submission_cycle_id'], ['id'])
    op.create_foreign_key('monitoring_state_snapshots_application_id_fkey', 'monitoring_state_snapshots', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('monitoring_state_snapshots_monitoring_run_id_fkey', 'monitoring_state_snapshots', 'monitoring_runs', ['monitoring_run_id'], ['id'])
    op.create_foreign_key('municipality_configs_scenario_id_fkey', 'municipality_configs', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('municipality_drafts_application_id_fkey', 'municipality_drafts', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('municipality_preparation_exception_preparation_revision_id_fkey', 'municipality_preparation_exceptions', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('municipality_preparation_exceptions_application_id_fkey', 'municipality_preparation_exceptions', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('notification_delivery_attempts_notification_event_id_fkey', 'notification_delivery_attempts', 'notification_events', ['notification_event_id'], ['id'])
    op.create_foreign_key('notification_events_contract_id_fkey', 'notification_events', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('notification_events_finding_id_fkey', 'notification_events', 'findings', ['finding_id'], ['id'])
    op.create_foreign_key('notification_events_permit_id_fkey', 'notification_events', 'permit_applications', ['permit_id'], ['id'])
    op.create_foreign_key('notification_events_proposal_id_fkey', 'notification_events', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('notification_events_recipient_user_id_fkey', 'notification_events', 'users', ['recipient_user_id'], ['id'])
    op.create_foreign_key('notification_events_workflow_task_id_fkey', 'notification_events', 'workflow_tasks', ['workflow_task_id'], ['id'])
    op.create_foreign_key('notification_read_states_notification_event_id_fkey', 'notification_read_states', 'notification_events', ['notification_event_id'], ['id'])
    op.create_foreign_key('office_credentials_evidence_document_version_id_fkey', 'office_credentials', 'document_versions', ['evidence_document_version_id'], ['id'])
    op.create_foreign_key('office_credentials_office_id_fkey', 'office_credentials', 'consultancy_offices', ['office_id'], ['id'])
    op.create_foreign_key('operator_exercise_evidence_preparation_revision_id_fkey', 'operator_exercise_evidence', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('operator_task_timings_preparation_revision_id_fkey', 'operator_task_timings', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('opportunities_client_account_id_fkey', 'opportunities', 'client_accounts', ['client_account_id'], ['id'])
    op.create_foreign_key('opportunities_current_owner_user_id_fkey', 'opportunities', 'users', ['current_owner_user_id'], ['id'])
    op.create_foreign_key('opportunities_office_id_fkey', 'opportunities', 'consultancy_offices', ['office_id'], ['id'])
    op.create_foreign_key('opportunities_project_id_fkey', 'opportunities', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('owner_decision_history_decision_id_fkey', 'owner_decision_history', 'owner_decisions', ['decision_id'], ['id'])
    op.create_foreign_key('package_items_document_version_id_fkey', 'package_items', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('package_items_package_id_fkey', 'package_items', 'packages', ['package_id'], ['id'])
    op.create_foreign_key('package_readiness_evaluations_applicable_rule_set_id_fkey', 'package_readiness_evaluations', 'applicable_rule_sets', ['applicable_rule_set_id'], ['id'])
    op.create_foreign_key('package_readiness_evaluations_configuration_bundle_id_fkey', 'package_readiness_evaluations', 'configuration_bundles', ['configuration_bundle_id'], ['id'])
    op.create_foreign_key('package_readiness_evaluations_project_id_fkey', 'package_readiness_evaluations', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('packages_configuration_bundle_id_fkey', 'packages', 'configuration_bundles', ['configuration_bundle_id'], ['id'])
    op.create_foreign_key('packages_project_id_fkey', 'packages', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('parties_source_document_version_id_fkey', 'parties', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('party_role_assignments_authority_case_id_fkey', 'party_role_assignments', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('party_role_assignments_party_id_fkey', 'party_role_assignments', 'parties', ['party_id'], ['id'])
    op.create_foreign_key('party_role_assignments_project_id_fkey', 'party_role_assignments', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('party_role_assignments_source_document_version_id_fkey', 'party_role_assignments', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('payment_receipts_client_account_id_fkey', 'payment_receipts', 'client_accounts', ['client_account_id'], ['id'])
    op.create_foreign_key('payment_receipts_contract_id_fkey', 'payment_receipts', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('payment_receipts_evidence_document_version_id_fkey', 'payment_receipts', 'document_versions', ['evidence_document_version_id'], ['id'])
    op.create_foreign_key('payment_receipts_project_id_fkey', 'payment_receipts', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('permit_applications_controlling_contract_id_fkey', 'permit_applications', 'contracts', ['controlling_contract_id'], ['id'])
    op.create_foreign_key('permit_applications_project_id_fkey', 'permit_applications', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('physical_evidence_items_authority_case_id_fkey', 'physical_evidence_items', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('physical_evidence_items_requirement_instance_id_fkey', 'physical_evidence_items', 'requirement_instances', ['requirement_instance_id'], ['id'])
    op.create_foreign_key('pilot_cohorts_final_submitter_id_fkey', 'pilot_cohorts', 'users', ['final_submitter_id'], ['id'])
    op.create_foreign_key('pilot_cohorts_process_champion_id_fkey', 'pilot_cohorts', 'users', ['process_champion_id'], ['id'])
    op.create_foreign_key('pilot_cohorts_requirement_steward_id_fkey', 'pilot_cohorts', 'users', ['requirement_steward_id'], ['id'])
    op.create_foreign_key('pilot_cohorts_responsible_engineer_id_fkey', 'pilot_cohorts', 'users', ['responsible_engineer_id'], ['id'])
    op.create_foreign_key('pilot_cohorts_scenario_id_fkey', 'pilot_cohorts', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('pilot_cohorts_super_user_id_fkey', 'pilot_cohorts', 'users', ['super_user_id'], ['id'])
    op.create_foreign_key('pilot_workflow_approvals_rehearsal_run_id_fkey', 'pilot_workflow_approvals', 'acceptance_rehearsal_runs', ['rehearsal_run_id'], ['id'])
    op.create_foreign_key('pilot_workflow_approvals_user_id_fkey', 'pilot_workflow_approvals', 'users', ['user_id'], ['id'])
    op.create_foreign_key('portal_derived_field_reconciliatio_preparation_revision_id_fkey', 'portal_derived_field_reconciliations', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('portal_drift_events_monitoring_run_id_fkey', 'portal_drift_events', 'monitoring_runs', ['monitoring_run_id'], ['id'])
    op.create_foreign_key('portal_grid_row_intents_preparation_revision_id_fkey', 'portal_grid_row_intents', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('portal_grid_row_observations_portal_snapshot_id_fkey', 'portal_grid_row_observations', 'portal_snapshots', ['portal_snapshot_id'], ['id'])
    op.create_foreign_key('portal_intended_states_configuration_bundle_id_fkey', 'portal_intended_states', 'configuration_bundles', ['configuration_bundle_id'], ['id'])
    op.create_foreign_key('portal_intended_states_preparation_revision_id_fkey', 'portal_intended_states', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('portal_reconciliation_results_preparation_revision_id_fkey', 'portal_reconciliation_results', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('portal_snapshots_application_id_fkey', 'portal_snapshots', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('portal_snapshots_preparation_revision_id_fkey', 'portal_snapshots', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('portal_structure_fingerprints_preparation_revision_id_fkey', 'portal_structure_fingerprints', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('portal_structure_fingerprints_scenario_id_fkey', 'portal_structure_fingerprints', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('portal_validation_finding_rules_finding_code_id_fkey', 'portal_validation_finding_rules', 'finding_codes', ['finding_code_id'], ['id'])
    op.create_foreign_key('precheck_clearance_evaluations_precheck_run_id_fkey', 'precheck_clearance_evaluations', 'authority_precheck_runs', ['precheck_run_id'], ['id'])
    op.create_foreign_key('precheck_clearance_evaluations_preparation_revision_id_fkey', 'precheck_clearance_evaluations', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('preparation_revisions_application_id_fkey', 'preparation_revisions', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('preparation_revisions_authority_approved_design_baseline_i_fkey', 'preparation_revisions', 'approved_design_baselines', ['authority_approved_design_baseline_id'], ['id'])
    op.create_foreign_key('preparation_revisions_authority_case_id_fkey', 'preparation_revisions', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('preparation_revisions_authority_policy_version_id_fkey', 'preparation_revisions', 'requirement_policy_versions', ['authority_policy_version_id'], ['id'])
    op.create_foreign_key('preparation_revisions_case_party_snapshot_id_fkey', 'preparation_revisions', 'case_party_snapshots', ['case_party_snapshot_id'], ['id'])
    op.create_foreign_key('preparation_revisions_configuration_bundle_id_fkey', 'preparation_revisions', 'configuration_bundles', ['configuration_bundle_id'], ['id'])
    op.create_foreign_key('preparation_revisions_package_id_fkey', 'preparation_revisions', 'packages', ['package_id'], ['id'])
    op.create_foreign_key('preparation_revisions_project_id_fkey', 'preparation_revisions', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('preparation_snapshots_preparation_revision_id_fkey', 'preparation_snapshots', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('prior_finding_preventive_checks_application_id_fkey', 'prior_finding_preventive_checks', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('prior_finding_preventive_checks_preparation_revision_id_fkey', 'prior_finding_preventive_checks', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('prior_finding_preventive_checks_project_id_fkey', 'prior_finding_preventive_checks', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('professional_credentials_evidence_document_version_id_fkey', 'professional_credentials', 'document_versions', ['evidence_document_version_id'], ['id'])
    op.create_foreign_key('professional_credentials_project_id_fkey', 'professional_credentials', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('project_activations_accepted_proposal_revision_id_fkey', 'project_activations', 'proposal_accepted_revisions', ['accepted_proposal_revision_id'], ['id'])
    op.create_foreign_key('project_activations_contract_id_fkey', 'project_activations', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('project_activations_contract_revision_id_fkey', 'project_activations', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('project_activations_project_id_fkey', 'project_activations', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('project_administration_records_client_account_id_fkey', 'project_administration_records', 'client_accounts', ['client_account_id'], ['id'])
    op.create_foreign_key('project_administration_records_engineer_contact_id_fkey', 'project_administration_records', 'client_contacts', ['engineer_contact_id'], ['id'])
    op.create_foreign_key('project_administration_records_project_id_fkey', 'project_administration_records', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('project_administration_records_reference_number_id_fkey', 'project_administration_records', 'reference_numbers', ['reference_number_id'], ['id'])
    op.create_foreign_key('project_archive_records_assessment_id_fkey', 'project_archive_records', 'project_closeout_assessments', ['assessment_id'], ['id'])
    op.create_foreign_key('project_archive_records_project_id_fkey', 'project_archive_records', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('project_artifact_records_contract_id_fkey', 'project_artifact_records', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('project_artifact_records_document_version_id_fkey', 'project_artifact_records', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('project_artifact_records_evidence_artifact_id_fkey', 'project_artifact_records', 'evidence_artifacts', ['evidence_artifact_id'], ['id'])
    op.create_foreign_key('project_artifact_records_opportunity_id_fkey', 'project_artifact_records', 'opportunities', ['opportunity_id'], ['id'])
    op.create_foreign_key('project_artifact_records_project_id_fkey', 'project_artifact_records', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('project_closeout_assessments_policy_version_id_fkey', 'project_closeout_assessments', 'project_closeout_policy_versions', ['policy_version_id'], ['id'])
    op.create_foreign_key('project_closeout_assessments_project_id_fkey', 'project_closeout_assessments', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('project_engineering_reviews_project_id_fkey', 'project_engineering_reviews', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('project_engineering_reviews_review_category_id_fkey', 'project_engineering_reviews', 'engineering_review_categories', ['review_category_id'], ['id'])
    op.create_foreign_key('project_engineering_reviews_revision_id_fkey', 'project_engineering_reviews', 'engineering_deliverable_revisions', ['revision_id'], ['id'])
    op.create_foreign_key('project_handovers_approval_id_fkey', 'project_handovers', 'approvals', ['approval_id'], ['id'])
    op.create_foreign_key('project_handovers_communication_draft_id_fkey', 'project_handovers', 'communication_drafts', ['communication_draft_id'], ['id'])
    op.create_foreign_key('project_handovers_project_id_fkey', 'project_handovers', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('project_handovers_rendered_artifact_id_fkey', 'project_handovers', 'rendered_artifacts', ['rendered_artifact_id'], ['id'])
    op.create_foreign_key('project_initiations_project_id_fkey', 'project_initiations', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('project_number_reservations_initiation_id_fkey', 'project_number_reservations', 'project_initiations', ['initiation_id'], ['id'])
    op.create_foreign_key('project_number_reservations_project_id_fkey', 'project_number_reservations', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('project_status_projections_project_id_fkey', 'project_status_projections', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('projects_office_id_fkey', 'projects', 'consultancy_offices', ['office_id'], ['id'])
    op.create_foreign_key('properties_project_id_fkey', 'properties', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('properties_source_assertion_id_fkey', 'properties', 'verified_assertions', ['source_assertion_id'], ['id'])
    op.create_foreign_key('properties_source_document_version_id_fkey', 'properties', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('properties_source_observation_id_fkey', 'properties', 'field_observations', ['source_observation_id'], ['id'])
    op.create_foreign_key('property_ownerships_party_id_fkey', 'property_ownerships', 'parties', ['party_id'], ['id'])
    op.create_foreign_key('property_ownerships_property_id_fkey', 'property_ownerships', 'properties', ['property_id'], ['id'])
    op.create_foreign_key('property_ownerships_source_assertion_id_fkey', 'property_ownerships', 'verified_assertions', ['source_assertion_id'], ['id'])
    op.create_foreign_key('property_ownerships_source_document_version_id_fkey', 'property_ownerships', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('proposal_accepted_revisions_proposal_id_fkey', 'proposal_accepted_revisions', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_assumptions_proposal_id_fkey', 'proposal_assumptions', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_client_responses_proposal_id_fkey', 'proposal_client_responses', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_commercial_outcomes_proposal_id_fkey', 'proposal_commercial_outcomes', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_conflicts_proposal_id_fkey', 'proposal_conflicts', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_contact_contexts_party_id_fkey', 'proposal_contact_contexts', 'parties', ['party_id'], ['id'])
    op.create_foreign_key('proposal_contact_contexts_proposal_id_fkey', 'proposal_contact_contexts', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_contact_contexts_source_document_version_id_fkey', 'proposal_contact_contexts', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('proposal_engineering_contribu_technical_rule_set_version_i_fkey', 'proposal_engineering_contributions', 'technical_rule_set_versions', ['technical_rule_set_version_id'], ['id'])
    op.create_foreign_key('proposal_engineering_contributi_source_document_version_id_fkey', 'proposal_engineering_contributions', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('proposal_engineering_contributions_proposal_id_fkey', 'proposal_engineering_contributions', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_expected_input_previews_proposal_id_fkey', 'proposal_expected_input_previews', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_external_cost_assumptions_external_body_id_fkey', 'proposal_external_cost_assumptions', 'external_bodies', ['external_body_id'], ['id'])
    op.create_foreign_key('proposal_external_cost_assumptions_proposal_id_fkey', 'proposal_external_cost_assumptions', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_intake_artifacts_evidence_artifact_id_fkey', 'proposal_intake_artifacts', 'evidence_artifacts', ['evidence_artifact_id'], ['id'])
    op.create_foreign_key('proposal_intake_artifacts_opportunity_id_fkey', 'proposal_intake_artifacts', 'opportunities', ['opportunity_id'], ['id'])
    op.create_foreign_key('proposal_intake_artifacts_project_id_fkey', 'proposal_intake_artifacts', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('proposal_material_acknowledgments_proposal_id_fkey', 'proposal_material_acknowledgments', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_notes_proposal_id_fkey', 'proposal_notes', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_output_artifacts_proposal_id_fkey', 'proposal_output_artifacts', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_output_artifacts_revision_id_fkey', 'proposal_output_artifacts', 'proposal_accepted_revisions', ['revision_id'], ['id'])
    op.create_foreign_key('proposal_regulatory_scope_inten_source_document_version_id_fkey', 'proposal_regulatory_scope_intents', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('proposal_regulatory_scope_intents_external_body_id_fkey', 'proposal_regulatory_scope_intents', 'external_bodies', ['external_body_id'], ['id'])
    op.create_foreign_key('proposal_regulatory_scope_intents_jurisdiction_id_fkey', 'proposal_regulatory_scope_intents', 'jurisdictions', ['jurisdiction_id'], ['id'])
    op.create_foreign_key('proposal_regulatory_scope_intents_proposal_id_fkey', 'proposal_regulatory_scope_intents', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_regulatory_scope_intents_proposal_scope_item_id_fkey', 'proposal_regulatory_scope_intents', 'proposal_service_scope_items', ['proposal_scope_item_id'], ['id'])
    op.create_foreign_key('proposal_regulatory_scope_intents_service_type_id_fkey', 'proposal_regulatory_scope_intents', 'service_types', ['service_type_id'], ['id'])
    op.create_foreign_key('proposal_regulatory_scope_intents_service_type_version_id_fkey', 'proposal_regulatory_scope_intents', 'service_type_versions', ['service_type_version_id'], ['id'])
    op.create_foreign_key('proposal_regulatory_scope_intents_source_assertion_id_fkey', 'proposal_regulatory_scope_intents', 'verified_assertions', ['source_assertion_id'], ['id'])
    op.create_foreign_key('proposal_revisions_proposal_id_fkey', 'proposal_revisions', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_service_scope_items_external_body_id_fkey', 'proposal_service_scope_items', 'external_bodies', ['external_body_id'], ['id'])
    op.create_foreign_key('proposal_service_scope_items_proposal_id_fkey', 'proposal_service_scope_items', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_service_scope_items_regulatory_service_type_id_fkey', 'proposal_service_scope_items', 'service_types', ['regulatory_service_type_id'], ['id'])
    op.create_foreign_key('proposal_service_scope_items_source_document_version_id_fkey', 'proposal_service_scope_items', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('proposal_site_contexts_property_id_fkey', 'proposal_site_contexts', 'properties', ['property_id'], ['id'])
    op.create_foreign_key('proposal_site_contexts_proposal_id_fkey', 'proposal_site_contexts', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_site_contexts_source_document_version_id_fkey', 'proposal_site_contexts', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('proposal_source_evidence_proposal_id_fkey', 'proposal_source_evidence', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_source_links_document_id_fkey', 'proposal_source_links', 'documents', ['document_id'], ['id'])
    op.create_foreign_key('proposal_source_links_document_version_id_fkey', 'proposal_source_links', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('proposal_source_links_proposal_id_fkey', 'proposal_source_links', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_source_links_source_evidence_id_fkey', 'proposal_source_links', 'proposal_source_evidence', ['source_evidence_id'], ['id'])
    op.create_foreign_key('proposal_stakeholder_intents_party_id_fkey', 'proposal_stakeholder_intents', 'parties', ['party_id'], ['id'])
    op.create_foreign_key('proposal_stakeholder_intents_proposal_id_fkey', 'proposal_stakeholder_intents', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_stakeholder_intents_source_document_version_id_fkey', 'proposal_stakeholder_intents', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('proposal_staleness_events_proposal_id_fkey', 'proposal_staleness_events', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('proposal_unknowns_proposal_id_fkey', 'proposal_unknowns', 'opportunities', ['proposal_id'], ['id'])
    op.create_foreign_key('quotation_approvals_approval_id_fkey', 'quotation_approvals', 'approvals', ['approval_id'], ['id'])
    op.create_foreign_key('quotation_approvals_quotation_revision_id_fkey', 'quotation_approvals', 'quotation_revisions', ['quotation_revision_id'], ['id'])
    op.create_foreign_key('quotation_field_observations_evidence_artifact_id_fkey', 'quotation_field_observations', 'evidence_artifacts', ['evidence_artifact_id'], ['id'])
    op.create_foreign_key('quotation_field_observations_quotation_revision_id_fkey', 'quotation_field_observations', 'quotation_revisions', ['quotation_revision_id'], ['id'])
    op.create_foreign_key('quotation_field_observations_source_document_version_id_fkey', 'quotation_field_observations', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('quotation_releases_approval_id_fkey', 'quotation_releases', 'approvals', ['approval_id'], ['id'])
    op.create_foreign_key('quotation_releases_quotation_revision_id_fkey', 'quotation_releases', 'quotation_revisions', ['quotation_revision_id'], ['id'])
    op.create_foreign_key('quotation_releases_rendered_artifact_id_fkey', 'quotation_releases', 'rendered_artifacts', ['rendered_artifact_id'], ['id'])
    op.create_foreign_key('quotation_revisions_quotation_id_fkey', 'quotation_revisions', 'quotations', ['quotation_id'], ['id'])
    op.create_foreign_key('quotation_revisions_rendered_artifact_id_fkey', 'quotation_revisions', 'rendered_artifacts', ['rendered_artifact_id'], ['id'])
    op.create_foreign_key('quotation_revisions_template_version_id_fkey', 'quotation_revisions', 'template_versions', ['template_version_id'], ['id'])
    op.create_foreign_key('quotations_client_account_id_fkey', 'quotations', 'client_accounts', ['client_account_id'], ['id'])
    op.create_foreign_key('quotations_opportunity_id_fkey', 'quotations', 'opportunities', ['opportunity_id'], ['id'])
    op.create_foreign_key('readiness_result_items_evaluation_id_fkey', 'readiness_result_items', 'package_readiness_evaluations', ['evaluation_id'], ['id'])
    op.create_foreign_key('receivable_follow_ups_contact_party_id_fkey', 'receivable_follow_ups', 'parties', ['contact_party_id'], ['id'])
    op.create_foreign_key('receivable_follow_ups_invoice_id_fkey', 'receivable_follow_ups', 'invoices', ['invoice_id'], ['id'])
    op.create_foreign_key('reference_numbers_contract_id_fkey', 'reference_numbers', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('reference_numbers_opportunity_id_fkey', 'reference_numbers', 'opportunities', ['opportunity_id'], ['id'])
    op.create_foreign_key('reference_numbers_permit_application_id_fkey', 'reference_numbers', 'permit_applications', ['permit_application_id'], ['id'])
    op.create_foreign_key('reference_numbers_project_id_fkey', 'reference_numbers', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('reference_numbers_quotation_id_fkey', 'reference_numbers', 'quotations', ['quotation_id'], ['id'])
    op.create_foreign_key('regulation_applicabilities_approval_id_fkey', 'regulation_applicabilities', 'approvals', ['approval_id'], ['id'])
    op.create_foreign_key('regulation_applicabilities_approved_by_user_id_fkey', 'regulation_applicabilities', 'users', ['approved_by_user_id'], ['id'])
    op.create_foreign_key('regulation_applicabilities_regulation_version_id_fkey', 'regulation_applicabilities', 'regulation_versions', ['regulation_version_id'], ['id'])
    op.create_foreign_key('regulation_applicabilities_review_scope_id_fkey', 'regulation_applicabilities', 'engineering_review_scopes', ['review_scope_id'], ['id'])
    op.create_foreign_key('regulation_versions_regulation_source_id_fkey', 'regulation_versions', 'regulation_sources', ['regulation_source_id'], ['id'])
    op.create_foreign_key('regulatory_closeout_assessments_project_id_fkey', 'regulatory_closeout_assessments', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('regulatory_closeout_assessments_service_engagement_id_fkey', 'regulatory_closeout_assessments', 'service_engagements', ['service_engagement_id'], ['id'])
    op.create_foreign_key('regulatory_journeys_external_body_id_fkey', 'regulatory_journeys', 'external_bodies', ['external_body_id'], ['id'])
    op.create_foreign_key('regulatory_journeys_jurisdiction_id_fkey', 'regulatory_journeys', 'jurisdictions', ['jurisdiction_id'], ['id'])
    op.create_foreign_key('regulatory_journeys_project_id_fkey', 'regulatory_journeys', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('regulatory_journeys_service_type_id_fkey', 'regulatory_journeys', 'service_types', ['service_type_id'], ['id'])
    op.create_foreign_key('rendered_artifacts_template_version_id_fkey', 'rendered_artifacts', 'template_versions', ['template_version_id'], ['id'])
    op.create_foreign_key('rendered_forms_configuration_bundle_id_fkey', 'rendered_forms', 'configuration_bundles', ['configuration_bundle_id'], ['id'])
    op.create_foreign_key('rendered_forms_package_id_fkey', 'rendered_forms', 'packages', ['package_id'], ['id'])
    op.create_foreign_key('rendered_forms_project_id_fkey', 'rendered_forms', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('rendered_forms_template_version_id_fkey', 'rendered_forms', 'form_template_versions', ['template_version_id'], ['id'])
    op.create_foreign_key('representations_authorization_id_fkey', 'representations', 'authorizations', ['authorization_id'], ['id'])
    op.create_foreign_key('representations_evidence_document_version_id_fkey', 'representations', 'document_versions', ['evidence_document_version_id'], ['id'])
    op.create_foreign_key('representations_principal_party_id_fkey', 'representations', 'parties', ['principal_party_id'], ['id'])
    op.create_foreign_key('representations_representative_party_id_fkey', 'representations', 'parties', ['representative_party_id'], ['id'])
    op.create_foreign_key('requirement_applicability_decisions_policy_item_id_fkey', 'requirement_applicability_decisions', 'requirement_policy_items', ['policy_item_id'], ['id'])
    op.create_foreign_key('requirement_configs_scenario_id_fkey', 'requirement_configs', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('requirement_decisions_policy_item_id_fkey', 'requirement_decisions', 'requirement_policy_items', ['policy_item_id'], ['id'])
    op.create_foreign_key('requirement_decisions_policy_version_id_fkey', 'requirement_decisions', 'requirement_policy_versions', ['policy_version_id'], ['id'])
    op.create_foreign_key('requirement_evaluations_policy_item_id_fkey', 'requirement_evaluations', 'requirement_policy_items', ['policy_item_id'], ['id'])
    op.create_foreign_key('requirement_evaluations_policy_version_id_fkey', 'requirement_evaluations', 'requirement_policy_versions', ['policy_version_id'], ['id'])
    op.create_foreign_key('requirement_evidence_constraints_policy_item_id_fkey', 'requirement_evidence_constraints', 'requirement_policy_items', ['policy_item_id'], ['id'])
    op.create_foreign_key('requirement_evidence_evaluations_document_version_id_fkey', 'requirement_evidence_evaluations', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('requirement_evidence_evaluations_requirement_evaluation_id_fkey', 'requirement_evidence_evaluations', 'requirement_evaluations', ['requirement_evaluation_id'], ['id'])
    op.create_foreign_key('requirement_groups_policy_version_id_fkey', 'requirement_groups', 'requirement_policy_versions', ['policy_version_id'], ['id'])
    op.create_foreign_key('requirement_instances_authority_case_id_fkey', 'requirement_instances', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('requirement_instances_group_id_fkey', 'requirement_instances', 'requirement_groups', ['group_id'], ['id'])
    op.create_foreign_key('requirement_instances_lifecycle_phase_id_fkey', 'requirement_instances', 'regulatory_lifecycle_phases', ['lifecycle_phase_id'], ['id'])
    op.create_foreign_key('requirement_instances_policy_item_id_fkey', 'requirement_instances', 'requirement_policy_items', ['policy_item_id'], ['id'])
    op.create_foreign_key('requirement_instances_policy_version_id_fkey', 'requirement_instances', 'requirement_policy_versions', ['policy_version_id'], ['id'])
    op.create_foreign_key('requirement_instances_requirement_definition_id_fkey', 'requirement_instances', 'requirement_definitions', ['requirement_definition_id'], ['id'])
    op.create_foreign_key('requirement_policy_items_group_id_fkey', 'requirement_policy_items', 'requirement_groups', ['group_id'], ['id'])
    op.create_foreign_key('requirement_policy_items_phase_id_fkey', 'requirement_policy_items', 'regulatory_lifecycle_phases', ['phase_id'], ['id'])
    op.create_foreign_key('requirement_policy_items_policy_version_id_fkey', 'requirement_policy_items', 'requirement_policy_versions', ['policy_version_id'], ['id'])
    op.create_foreign_key('requirement_policy_items_requirement_definition_id_fkey', 'requirement_policy_items', 'requirement_definitions', ['requirement_definition_id'], ['id'])
    op.create_foreign_key('requirement_policy_items_source_section_id_fkey', 'requirement_policy_items', 'master_content_source_sections', ['source_section_id'], ['id'])
    op.create_foreign_key('requirement_policy_lineage_document_version_id_fkey', 'requirement_policy_lineage', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('requirement_policy_lineage_master_content_item_id_fkey', 'requirement_policy_lineage', 'master_content_items', ['master_content_item_id'], ['id'])
    op.create_foreign_key('requirement_policy_lineage_policy_version_id_fkey', 'requirement_policy_lineage', 'requirement_policy_versions', ['policy_version_id'], ['id'])
    op.create_foreign_key('requirement_policy_lineage_source_section_id_fkey', 'requirement_policy_lineage', 'master_content_source_sections', ['source_section_id'], ['id'])
    op.create_foreign_key('requirement_policy_versions_external_body_id_fkey', 'requirement_policy_versions', 'external_bodies', ['external_body_id'], ['id'])
    op.create_foreign_key('requirement_policy_versions_jurisdiction_id_fkey', 'requirement_policy_versions', 'jurisdictions', ['jurisdiction_id'], ['id'])
    op.create_foreign_key('requirement_policy_versions_service_type_id_fkey', 'requirement_policy_versions', 'service_types', ['service_type_id'], ['id'])
    op.create_foreign_key('requirement_policy_versions_supersedes_id_fkey', 'requirement_policy_versions', 'requirement_policy_versions', ['supersedes_id'], ['id'])
    op.create_foreign_key('restore_rehearsals_recovery_manifest_id_fkey', 'restore_rehearsals', 'recovery_manifests', ['recovery_manifest_id'], ['id'])
    op.create_foreign_key('resubmission_readiness_evaluations_application_id_fkey', 'resubmission_readiness_evaluations', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('resubmission_readiness_evaluations_package_id_fkey', 'resubmission_readiness_evaluations', 'packages', ['package_id'], ['id'])
    op.create_foreign_key('resubmission_readiness_evaluations_preparation_revision_id_fkey', 'resubmission_readiness_evaluations', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('resubmission_readiness_evaluations_submission_cycle_id_fkey', 'resubmission_readiness_evaluations', 'submission_cycles', ['submission_cycle_id'], ['id'])
    op.create_foreign_key('rfqs_opportunity_id_fkey', 'rfqs', 'opportunities', ['opportunity_id'], ['id'])
    op.create_foreign_key('rfqs_source_document_version_id_fkey', 'rfqs', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('rule_candidates_source_finding_id_fkey', 'rule_candidates', 'findings', ['source_finding_id'], ['id'])
    op.create_foreign_key('scenario_variants_canonical_fixture_project_id_fkey', 'scenario_variants', 'projects', ['canonical_fixture_project_id'], ['id'])
    op.create_foreign_key('scenario_variants_scenario_id_fkey', 'scenario_variants', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('semantic_value_assertions_semantic_key_id_fkey', 'semantic_value_assertions', 'semantic_key_definitions', ['semantic_key_id'], ['id'])
    op.create_foreign_key('service_engagements_contract_id_fkey', 'service_engagements', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('service_engagements_contract_revision_id_fkey', 'service_engagements', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('service_engagements_project_id_fkey', 'service_engagements', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('service_engagements_proposal_scope_item_id_fkey', 'service_engagements', 'proposal_service_scope_items', ['proposal_scope_item_id'], ['id'])
    op.create_foreign_key('service_scope_closures_contract_id_fkey', 'service_scope_closures', 'contracts', ['contract_id'], ['id'])
    op.create_foreign_key('service_scope_closures_contract_revision_id_fkey', 'service_scope_closures', 'contract_revisions', ['contract_revision_id'], ['id'])
    op.create_foreign_key('service_scope_closures_handover_acceptance_id_fkey', 'service_scope_closures', 'handover_acceptances', ['handover_acceptance_id'], ['id'])
    op.create_foreign_key('service_scope_closures_handover_package_revision_id_fkey', 'service_scope_closures', 'handover_package_revisions', ['handover_package_revision_id'], ['id'])
    op.create_foreign_key('service_scope_closures_project_id_fkey', 'service_scope_closures', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('service_scope_closures_service_engagement_id_fkey', 'service_scope_closures', 'service_engagements', ['service_engagement_id'], ['id'])
    op.create_foreign_key('service_type_versions_service_type_id_fkey', 'service_type_versions', 'service_types', ['service_type_id'], ['id'])
    op.create_foreign_key('shadow_corrections_application_id_fkey', 'shadow_corrections', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('shadow_corrections_preparation_revision_id_fkey', 'shadow_corrections', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('shadow_corrections_project_id_fkey', 'shadow_corrections', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('signature_packets_form_instance_id_fkey', 'signature_packets', 'form_instances', ['form_instance_id'], ['id'])
    op.create_foreign_key('signoff_c_proposals_stage2_baseline_id_fkey', 'signoff_c_proposals', 'stage2_baselines', ['stage2_baseline_id'], ['id'])
    op.create_foreign_key('source_intake_items_batch_id_fkey', 'source_intake_items', 'source_intake_batches', ['batch_id'], ['id'], ondelete='CASCADE')
    op.create_foreign_key('source_intake_items_target_document_version_id_fkey', 'source_intake_items', 'document_versions', ['target_document_version_id'], ['id'])
    op.create_foreign_key('source_intake_items_target_master_content_id_fkey', 'source_intake_items', 'master_content_items', ['target_master_content_id'], ['id'])
    op.create_foreign_key('spike_document_results_document_version_id_fkey', 'spike_document_results', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('spike_document_results_spike_run_id_fkey', 'spike_document_results', 'extraction_spike_runs', ['spike_run_id'], ['id'])
    op.create_foreign_key('spike_field_results_spike_run_id_fkey', 'spike_field_results', 'extraction_spike_runs', ['spike_run_id'], ['id'])
    op.create_foreign_key('stage2_baselines_scenario_id_fkey', 'stage2_baselines', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('stage2_review_acknowledgements_baseline_id_fkey', 'stage2_review_acknowledgements', 'stage2_baselines', ['baseline_id'], ['id'])
    op.create_foreign_key('stale_reasons_material_change_event_id_fkey', 'stale_reasons', 'material_change_events', ['material_change_event_id'], ['id'])
    op.create_foreign_key('stale_reasons_project_id_fkey', 'stale_reasons', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('storage_operations_document_id_fkey', 'storage_operations', 'documents', ['document_id'], ['id'])
    op.create_foreign_key('submission_attempts_authority_case_id_fkey', 'submission_attempts', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('submission_attempts_precheck_run_id_fkey', 'submission_attempts', 'submission_precheck_runs', ['precheck_run_id'], ['id'])
    op.create_foreign_key('submission_attempts_preparation_revision_id_fkey', 'submission_attempts', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('submission_attempts_submission_package_id_fkey', 'submission_attempts', 'submission_packages', ['submission_package_id'], ['id'])
    op.create_foreign_key('fk_submission_confirmation_preparation_revision', 'submission_confirmations', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('submission_confirmations_application_id_fkey', 'submission_confirmations', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('submission_confirmations_preparation_revision_id_fkey', 'submission_confirmations', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('submission_cycles_application_id_fkey', 'submission_cycles', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('submission_cycles_preparation_revision_id_fkey', 'submission_cycles', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('submission_handoffs_application_id_fkey', 'submission_handoffs', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('submission_handoffs_final_submitter_user_id_fkey', 'submission_handoffs', 'users', ['final_submitter_user_id'], ['id'])
    op.create_foreign_key('submission_handoffs_from_user_id_fkey', 'submission_handoffs', 'users', ['from_user_id'], ['id'])
    op.create_foreign_key('submission_handoffs_package_id_fkey', 'submission_handoffs', 'packages', ['package_id'], ['id'])
    op.create_foreign_key('submission_handoffs_portal_snapshot_id_fkey', 'submission_handoffs', 'portal_snapshots', ['portal_snapshot_id'], ['id'])
    op.create_foreign_key('submission_handoffs_preparation_revision_id_fkey', 'submission_handoffs', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('submission_package_items_as_built_baseline_id_fkey', 'submission_package_items', 'as_built_baselines', ['as_built_baseline_id'], ['id'])
    op.create_foreign_key('submission_package_items_baseline_id_fkey', 'submission_package_items', 'approved_design_baselines', ['baseline_id'], ['id'])
    op.create_foreign_key('submission_package_items_baseline_member_id_fkey', 'submission_package_items', 'approved_design_baseline_members', ['baseline_member_id'], ['id'])
    op.create_foreign_key('submission_package_items_document_version_id_fkey', 'submission_package_items', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('submission_package_items_evidence_selection_id_fkey', 'submission_package_items', 'case_evidence_selections', ['evidence_selection_id'], ['id'])
    op.create_foreign_key('submission_package_items_form_instance_id_fkey', 'submission_package_items', 'form_instances', ['form_instance_id'], ['id'])
    op.create_foreign_key('submission_package_items_package_id_fkey', 'submission_package_items', 'submission_packages', ['package_id'], ['id'])
    op.create_foreign_key('submission_package_items_physical_evidence_item_id_fkey', 'submission_package_items', 'physical_evidence_items', ['physical_evidence_item_id'], ['id'])
    op.create_foreign_key('submission_package_items_requirement_instance_id_fkey', 'submission_package_items', 'requirement_instances', ['requirement_instance_id'], ['id'])
    op.create_foreign_key('submission_packages_authority_case_id_fkey', 'submission_packages', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('submission_packages_preparation_revision_id_fkey', 'submission_packages', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('submission_precheck_checks_precheck_run_id_fkey', 'submission_precheck_checks', 'submission_precheck_runs', ['precheck_run_id'], ['id'])
    op.create_foreign_key('submission_precheck_runs_authority_case_id_fkey', 'submission_precheck_runs', 'authority_cases', ['authority_case_id'], ['id'])
    op.create_foreign_key('submission_precheck_runs_policy_version_id_fkey', 'submission_precheck_runs', 'requirement_policy_versions', ['policy_version_id'], ['id'])
    op.create_foreign_key('submission_precheck_runs_preparation_revision_id_fkey', 'submission_precheck_runs', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('submission_precheck_runs_submission_package_id_fkey', 'submission_precheck_runs', 'submission_packages', ['submission_package_id'], ['id'])
    op.create_foreign_key('submitted_snapshots_application_id_fkey', 'submitted_snapshots', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('submitted_snapshots_package_id_fkey', 'submitted_snapshots', 'packages', ['package_id'], ['id'])
    op.create_foreign_key('submitted_snapshots_portal_snapshot_id_fkey', 'submitted_snapshots', 'portal_snapshots', ['portal_snapshot_id'], ['id'])
    op.create_foreign_key('submitted_snapshots_preparation_revision_id_fkey', 'submitted_snapshots', 'preparation_revisions', ['preparation_revision_id'], ['id'])
    op.create_foreign_key('submitted_snapshots_submission_cycle_id_fkey', 'submitted_snapshots', 'submission_cycles', ['submission_cycle_id'], ['id'])
    op.create_foreign_key('support_cases_application_id_fkey', 'support_cases', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('support_cases_finding_id_fkey', 'support_cases', 'findings', ['finding_id'], ['id'])
    op.create_foreign_key('support_cases_monitoring_run_id_fkey', 'support_cases', 'monitoring_runs', ['monitoring_run_id'], ['id'])
    op.create_foreign_key('support_cases_project_id_fkey', 'support_cases', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('synology_project_bootstraps_project_id_fkey', 'synology_project_bootstraps', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('target_rendering_coverages_scenario_id_fkey', 'target_rendering_coverages', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('target_rendering_coverages_variant_id_fkey', 'target_rendering_coverages', 'scenario_variants', ['variant_id'], ['id'])
    op.create_foreign_key('target_rendering_rules_field_definition_id_fkey', 'target_rendering_rules', 'field_definitions', ['field_definition_id'], ['id'])
    op.create_foreign_key('target_rendering_rules_scenario_id_fkey', 'target_rendering_rules', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('technical_rule_evaluations_technical_rule_id_fkey', 'technical_rule_evaluations', 'technical_rules', ['technical_rule_id'], ['id'])
    op.create_foreign_key('technical_rule_lineage_document_version_id_fkey', 'technical_rule_lineage', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('technical_rule_lineage_master_content_item_id_fkey', 'technical_rule_lineage', 'master_content_items', ['master_content_item_id'], ['id'])
    op.create_foreign_key('technical_rule_lineage_source_section_id_fkey', 'technical_rule_lineage', 'master_content_source_sections', ['source_section_id'], ['id'])
    op.create_foreign_key('technical_rule_lineage_technical_rule_id_fkey', 'technical_rule_lineage', 'technical_rules', ['technical_rule_id'], ['id'])
    op.create_foreign_key('technical_rule_set_versions_external_body_id_fkey', 'technical_rule_set_versions', 'external_bodies', ['external_body_id'], ['id'])
    op.create_foreign_key('technical_rule_set_versions_jurisdiction_id_fkey', 'technical_rule_set_versions', 'jurisdictions', ['jurisdiction_id'], ['id'])
    op.create_foreign_key('technical_rule_set_versions_service_type_id_fkey', 'technical_rule_set_versions', 'service_types', ['service_type_id'], ['id'])
    op.create_foreign_key('technical_rule_set_versions_supersedes_id_fkey', 'technical_rule_set_versions', 'technical_rule_set_versions', ['supersedes_id'], ['id'])
    op.create_foreign_key('technical_rules_rule_set_version_id_fkey', 'technical_rules', 'technical_rule_set_versions', ['rule_set_version_id'], ['id'])
    op.create_foreign_key('template_versions_source_document_version_id_fkey', 'template_versions', 'document_versions', ['source_document_version_id'], ['id'])
    op.create_foreign_key('template_versions_template_definition_id_fkey', 'template_versions', 'template_definitions', ['template_definition_id'], ['id'])
    op.create_foreign_key('tender_documents_document_version_id_fkey', 'tender_documents', 'document_versions', ['document_version_id'], ['id'])
    op.create_foreign_key('tender_documents_opportunity_id_fkey', 'tender_documents', 'opportunities', ['opportunity_id'], ['id'])
    op.create_foreign_key('users_office_id_fkey', 'users', 'consultancy_offices', ['office_id'], ['id'])
    op.create_foreign_key('variant_compatibility_results_scenario_id_fkey', 'variant_compatibility_results', 'scenario_configs', ['scenario_id'], ['id'])
    op.create_foreign_key('verified_assertions_field_definition_id_fkey', 'verified_assertions', 'field_definitions', ['field_definition_id'], ['id'])
    op.create_foreign_key('verified_assertions_project_id_fkey', 'verified_assertions', 'projects', ['project_id'], ['id'])
    op.create_foreign_key('verified_assertions_source_observation_id_fkey', 'verified_assertions', 'field_observations', ['source_observation_id'], ['id'])
    op.create_foreign_key('workflow_safety_holds_incident_id_fkey', 'workflow_safety_holds', 'integrity_incidents', ['incident_id'], ['id'])
    op.create_foreign_key('workflow_tasks_application_id_fkey', 'workflow_tasks', 'permit_applications', ['application_id'], ['id'])
    op.create_foreign_key('workflow_tasks_finding_id_fkey', 'workflow_tasks', 'findings', ['finding_id'], ['id'])
    op.create_foreign_key('workflow_tasks_owner_user_id_fkey', 'workflow_tasks', 'users', ['owner_user_id'], ['id'])
    op.create_foreign_key('workflow_tasks_project_id_fkey', 'workflow_tasks', 'projects', ['project_id'], ['id'])

    op.create_index('ix_accounting_handoffs_invoice_id', 'accounting_handoffs', ['invoice_id'])
    op.create_index('ix_admin_document_comments_project_id', 'admin_document_comments', ['project_id'])
    op.create_index('ix_approved_design_baseline_member_baseline', 'approved_design_baseline_members', ['baseline_id'])
    op.create_index('ix_approved_design_baseline_project', 'approved_design_baselines', ['project_id', 'purpose', 'status'])
    op.create_index('ix_as_built_baseline_member_baseline', 'as_built_baseline_members', ['baseline_id'])
    op.create_index('ix_as_built_baseline_members_building_snapshot_id', 'as_built_baseline_members', ['building_snapshot_id'])
    op.create_index('ix_as_built_baseline_members_document_version_id', 'as_built_baseline_members', ['document_version_id'])
    op.create_index('ix_as_built_baseline_members_engineering_revision_id', 'as_built_baseline_members', ['engineering_revision_id'])
    op.create_index('ix_as_built_baseline_members_project_id', 'as_built_baseline_members', ['project_id'])
    op.create_index('ix_as_built_baseline_members_rendition_id', 'as_built_baseline_members', ['rendition_id'])
    op.create_index('ix_as_built_baseline_scope', 'as_built_baselines', ['project_id', 'construction_execution_id', 'status'])
    op.create_index('ix_as_built_baselines_authority_case_id', 'as_built_baselines', ['authority_case_id'])
    op.create_index('ix_as_built_baselines_construction_execution_id', 'as_built_baselines', ['construction_execution_id'])
    op.create_index('ix_as_built_baselines_project_id', 'as_built_baselines', ['project_id'])
    op.create_index('ix_as_built_baselines_source_construction_design_snapshot_id', 'as_built_baselines', ['source_construction_design_snapshot_id'])
    op.create_index('ix_as_built_baselines_supersedes_baseline_id', 'as_built_baselines', ['supersedes_baseline_id'])
    op.create_index('ix_as_built_comparison_project', 'as_built_comparison_runs', ['project_id', 'result'])
    op.create_index('ix_as_built_comparison_runs_baseline_id', 'as_built_comparison_runs', ['baseline_id'])
    op.create_index('ix_as_built_comparison_runs_construction_design_snapshot_id', 'as_built_comparison_runs', ['construction_design_snapshot_id'])
    op.create_index('ix_as_built_comparison_runs_project_id', 'as_built_comparison_runs', ['project_id'])
    op.create_index('ix_as_built_variance_project_status', 'as_built_variances', ['project_id', 'status'])
    op.create_index('ix_as_built_variances_building_asset_id', 'as_built_variances', ['building_asset_id'])
    op.create_index('ix_as_built_variances_comparison_run_id', 'as_built_variances', ['comparison_run_id'])
    op.create_index('ix_as_built_variances_design_change_request_id', 'as_built_variances', ['design_change_request_id'])
    op.create_index('ix_as_built_variances_engineering_revision_id', 'as_built_variances', ['engineering_revision_id'])
    op.create_index('ix_as_built_variances_project_id', 'as_built_variances', ['project_id'])
    op.create_index('ix_assistant_capability_definitions_assistant_id', 'assistant_capability_definitions', ['assistant_id'])
    op.create_index('ix_assistant_handoffs_context_id', 'assistant_handoffs', ['context_id'])
    op.create_index('ix_assistant_handoffs_opportunity_id', 'assistant_handoffs', ['opportunity_id'])
    op.create_index('ix_assistant_handoffs_project_id', 'assistant_handoffs', ['project_id'])
    op.create_index('ix_audit_events_correlation_id', 'audit_events', ['correlation_id'])
    op.create_index('ix_authority_approved_design_snapshots_approved_design__f6b5', 'authority_approved_design_snapshots', ['approved_design_baseline_id'])
    op.create_index('ix_authority_approved_design_snapshots_authority_case_id', 'authority_approved_design_snapshots', ['authority_case_id'])
    op.create_index('ix_authority_approved_design_snapshots_authority_outcome_id', 'authority_approved_design_snapshots', ['authority_outcome_id'])
    op.create_index('ix_authority_approved_design_snapshots_construction_exe_0f48', 'authority_approved_design_snapshots', ['construction_execution_id'])
    op.create_index('ix_authority_approved_design_snapshots_external_submiss_16f8', 'authority_approved_design_snapshots', ['external_submission_snapshot_id'])
    op.create_index('ix_authority_approved_design_snapshots_preparation_revision_id', 'authority_approved_design_snapshots', ['preparation_revision_id'])
    op.create_index('ix_authority_approved_design_snapshots_project_id', 'authority_approved_design_snapshots', ['project_id'])
    op.create_index('ix_authority_approved_design_snapshots_submission_cycle_id', 'authority_approved_design_snapshots', ['submission_cycle_id'])
    op.create_index('ix_authority_approved_design_snapshots_submission_package_id', 'authority_approved_design_snapshots', ['submission_package_id'])
    op.create_index('ix_authority_approved_snapshot_execution', 'authority_approved_design_snapshots', ['construction_execution_id', 'status'])
    op.create_index('ix_authority_case_finding_case_status', 'authority_case_findings', ['authority_case_id', 'status'])
    op.create_index('ix_authority_case_finding_cycle', 'authority_case_findings', ['submission_cycle_id'])
    op.create_index('ix_authority_case_findings_affected_requirement_instance_id', 'authority_case_findings', ['affected_requirement_instance_id'])
    op.create_index('ix_authority_case_findings_source_document_version_id', 'authority_case_findings', ['source_document_version_id'])
    op.create_index('ix_authority_case_findings_submission_cycle_id', 'authority_case_findings', ['submission_cycle_id'])
    op.create_index('ix_authority_case_identifier_value', 'authority_case_identifiers', ['value'])
    op.create_index('ix_authority_case_identifiers_authority_case_id', 'authority_case_identifiers', ['authority_case_id'])
    op.create_index('ix_authority_case_outcome_case', 'authority_case_outcomes', ['authority_case_id', 'outcome_type'])
    op.create_index('ix_authority_case_outcomes_source_document_version_id', 'authority_case_outcomes', ['source_document_version_id'])
    op.create_index('ix_authority_case_policy_binding_policy', 'authority_case_policy_bindings', ['policy_version_id'])
    op.create_index('ix_authority_case_subjects_authority_case_id', 'authority_case_subjects', ['authority_case_id'])
    op.create_index('ix_authority_case_subjects_subject_id', 'authority_case_subjects', ['subject_id'])
    op.create_index('ix_authority_case_work_period_case', 'authority_case_work_periods', ['authority_case_id'])
    op.create_index('ix_authority_case_work_periods_source_document_version_id', 'authority_case_work_periods', ['source_document_version_id'])
    op.create_index('ix_authority_case_context', 'authority_cases', ['external_body_id', 'service_type_id', 'jurisdiction_id'])
    op.create_index('ix_authority_case_journey', 'authority_cases', ['regulatory_journey_id'])
    op.create_index('ix_authority_cases_external_body_id', 'authority_cases', ['external_body_id'])
    op.create_index('ix_authority_cases_jurisdiction_id', 'authority_cases', ['jurisdiction_id'])
    op.create_index('ix_authority_cases_regulatory_journey_id', 'authority_cases', ['regulatory_journey_id'])
    op.create_index('ix_authority_cases_service_type_id', 'authority_cases', ['service_type_id'])
    op.create_index('ix_authority_cases_subject_id', 'authority_cases', ['subject_id'])
    op.create_index('ix_authority_finding_response_finding', 'authority_finding_responses', ['finding_id', 'status'])
    op.create_index('ix_authority_outcome_case', 'authority_outcomes', ['authority_case_id'])
    op.create_index('ix_authority_outcomes_source_document_version_id', 'authority_outcomes', ['source_document_version_id'])
    op.create_index('ix_authority_submission_cycle_case_status', 'authority_submission_cycles', ['authority_case_id', 'status'])
    op.create_index('ix_authorization_grant_case_status', 'authorization_grants', ['authority_case_id', 'status'])
    op.create_index('ix_authorization_grant_scope', 'authorization_grants', ['grantor_party_id', 'grantee_party_id', 'status'])
    op.create_index('ix_authorization_grants_authority_case_id', 'authorization_grants', ['authority_case_id'])
    op.create_index('ix_authorization_grants_evidence_document_version_id', 'authorization_grants', ['evidence_document_version_id'])
    op.create_index('ix_authorization_grants_grantee_party_id', 'authorization_grants', ['grantee_party_id'])
    op.create_index('ix_authorization_grants_grantor_party_id', 'authorization_grants', ['grantor_party_id'])
    op.create_index('ix_authorization_grants_project_id', 'authorization_grants', ['project_id'])
    op.create_index('ix_automation_readiness_assessments_mapping_release_id', 'automation_readiness_assessments', ['mapping_release_id'])
    op.create_index('ix_automation_readiness_assessments_master_content_item_id', 'automation_readiness_assessments', ['master_content_item_id'])
    op.create_index('ix_automation_readiness_assessments_profile_id', 'automation_readiness_assessments', ['profile_id'])
    op.create_index('ix_automation_readiness_assessments_source_document_version_id', 'automation_readiness_assessments', ['source_document_version_id'])
    op.create_index('ix_automation_readiness_assessments_state', 'automation_readiness_assessments', ['state'])
    op.create_index('ix_automation_readiness_profile', 'automation_readiness_assessments', ['profile_id', 'evaluated_at'])
    op.create_index('ix_billing_milestone_eligibilities_billing_milestone_id', 'billing_milestone_eligibilities', ['billing_milestone_id'])
    op.create_index('ix_billing_milestone_eligibility', 'billing_milestones', ['eligibility_state', 'status'])
    op.create_index('ix_billing_milestones_billing_plan_revision_id', 'billing_milestones', ['billing_plan_revision_id'])
    op.create_index('ix_billing_milestones_source_contract_payment_term_id', 'billing_milestones', ['source_contract_payment_term_id'])
    op.create_index('ix_billing_plan_revisions_billing_plan_id', 'billing_plan_revisions', ['billing_plan_id'])
    op.create_index('ix_billing_plan_revisions_client_account_id', 'billing_plan_revisions', ['client_account_id'])
    op.create_index('ix_billing_plan_revisions_contract_id', 'billing_plan_revisions', ['contract_id'])
    op.create_index('ix_billing_plan_revisions_contract_revision_id', 'billing_plan_revisions', ['contract_revision_id'])
    op.create_index('ix_billing_plan_revisions_project_id', 'billing_plan_revisions', ['project_id'])
    op.create_index('ix_billing_plan_revisions_status', 'billing_plan_revisions', ['status'])
    op.create_index('ix_billing_plans_client_account_id', 'billing_plans', ['client_account_id'])
    op.create_index('ix_billing_plans_contract_id', 'billing_plans', ['contract_id'])
    op.create_index('ix_billing_plans_contract_revision_id', 'billing_plans', ['contract_revision_id'])
    op.create_index('ix_billing_plans_current_revision_id', 'billing_plans', ['current_revision_id'])
    op.create_index('ix_billing_plans_project_id', 'billing_plans', ['project_id'])
    op.create_index('ix_billing_plans_status', 'billing_plans', ['status'])
    op.create_index('ix_building_asset_project_status', 'building_assets', ['project_id', 'status'])
    op.create_index('ix_building_assets_project_id', 'building_assets', ['project_id'])
    op.create_index('ix_building_assets_property_id', 'building_assets', ['property_id'])
    op.create_index('ix_building_snapshot_project_type', 'building_snapshots', ['project_id', 'snapshot_type', 'status'])
    op.create_index('ix_building_snapshots_building_asset_id', 'building_snapshots', ['building_asset_id'])
    op.create_index('ix_building_snapshots_project_id', 'building_snapshots', ['project_id'])
    op.create_index('ix_capability_invocation_records_assistant_id', 'capability_invocation_records', ['assistant_id'])
    op.create_index('ix_capability_invocation_records_capability_id', 'capability_invocation_records', ['capability_id'])
    op.create_index('ix_capability_invocation_records_context_id', 'capability_invocation_records', ['context_id'])
    op.create_index('ix_case_evidence_selection_case', 'case_evidence_selections', ['authority_case_id', 'document_version_id'])
    op.create_index('ix_case_evidence_selection_instance', 'case_evidence_selections', ['requirement_instance_id', 'status'])
    op.create_index('ix_case_evidence_selections_approved_design_baseline_id', 'case_evidence_selections', ['approved_design_baseline_id'])
    op.create_index('ix_case_evidence_selections_document_version_id', 'case_evidence_selections', ['document_version_id'])
    op.create_index('ix_case_evidence_selections_form_instance_id', 'case_evidence_selections', ['form_instance_id'])
    op.create_index('ix_case_party_snapshot_case', 'case_party_snapshots', ['authority_case_id', 'snapshot_number'])
    op.create_index('ix_case_party_snapshots_authority_case_id', 'case_party_snapshots', ['authority_case_id'])
    op.create_index('ix_case_party_snapshots_preparation_revision_id', 'case_party_snapshots', ['preparation_revision_id'])
    op.create_index('ix_case_party_snapshots_project_id', 'case_party_snapshots', ['project_id'])
    op.create_index('ix_checklist_items_context_id', 'checklist_items', ['context_id'])
    op.create_index('ix_client_accounts_canonical_party_id', 'client_accounts', ['canonical_party_id'])
    op.create_index('ix_client_contacts_client_account_id', 'client_contacts', ['client_account_id'])
    op.create_index('ix_client_responses_opportunity_id', 'client_responses', ['opportunity_id'])
    op.create_index('ix_client_responses_quotation_revision_id', 'client_responses', ['quotation_revision_id'])
    op.create_index('ix_commercial_terms_quotation_revision_id', 'commercial_terms', ['quotation_revision_id'])
    op.create_index('ix_communication_approvals_communication_draft_id', 'communication_approvals', ['communication_draft_id'])
    op.create_index('ix_communication_deliveries_communication_draft_id', 'communication_deliveries', ['communication_draft_id'])
    op.create_index('ix_communication_drafts_context_id', 'communication_drafts', ['context_id'])
    op.create_index('ix_completion_case_link_project', 'completion_case_links', ['project_id', 'status'])
    op.create_index('ix_completion_case_links_authority_case_id', 'completion_case_links', ['authority_case_id'])
    op.create_index('ix_completion_case_links_construction_completion_context_id', 'completion_case_links', ['construction_completion_context_id'])
    op.create_index('ix_completion_case_links_construction_execution_id', 'completion_case_links', ['construction_execution_id'])
    op.create_index('ix_completion_case_links_project_id', 'completion_case_links', ['project_id'])
    op.create_index('ix_completion_case_links_subject_id', 'completion_case_links', ['subject_id'])
    op.create_index('ix_construction_authority_notification_execution', 'construction_authority_notifications', ['construction_execution_id', 'status'])
    op.create_index('ix_construction_authority_notifications_authority_case_id', 'construction_authority_notifications', ['authority_case_id'])
    op.create_index('ix_construction_authority_notifications_construction_ex_91d8', 'construction_authority_notifications', ['construction_execution_id'])
    op.create_index('ix_construction_authority_notifications_evidence_docume_72b8', 'construction_authority_notifications', ['evidence_document_version_id'])
    op.create_index('ix_construction_authority_notifications_obligation_instance_id', 'construction_authority_notifications', ['obligation_instance_id'])
    op.create_index('ix_construction_authority_notifications_project_id', 'construction_authority_notifications', ['project_id'])
    op.create_index('ix_construction_authority_notifications_work_control_event_id', 'construction_authority_notifications', ['work_control_event_id'])
    op.create_index('ix_completion_context_project', 'construction_completion_contexts', ['project_id', 'status'])
    op.create_index('ix_construction_completion_contexts_authority_approved__fa83', 'construction_completion_contexts', ['authority_approved_design_snapshot_id'])
    op.create_index('ix_construction_completion_contexts_construction_design_31a6', 'construction_completion_contexts', ['construction_design_snapshot_id'])
    op.create_index('ix_construction_completion_contexts_construction_execution_id', 'construction_completion_contexts', ['construction_execution_id'])
    op.create_index('ix_construction_completion_contexts_project_id', 'construction_completion_contexts', ['project_id'])
    op.create_index('ix_construction_correspondence_authority_case_id', 'construction_correspondence', ['authority_case_id'])
    op.create_index('ix_construction_correspondence_construction_execution_id', 'construction_correspondence', ['construction_execution_id'])
    op.create_index('ix_construction_correspondence_document_version_id', 'construction_correspondence', ['document_version_id'])
    op.create_index('ix_construction_correspondence_execution', 'construction_correspondence', ['construction_execution_id', 'status', 'occurred_at'])
    op.create_index('ix_construction_correspondence_project_id', 'construction_correspondence', ['project_id'])
    op.create_index('ix_construction_design_snapshot_execution', 'construction_design_snapshots', ['construction_execution_id', 'status'])
    op.create_index('ix_construction_design_snapshots_construction_execution_id', 'construction_design_snapshots', ['construction_execution_id'])
    op.create_index('ix_construction_design_snapshots_project_id', 'construction_design_snapshots', ['project_id'])
    op.create_index('ix_construction_evidence_link_execution', 'construction_evidence_links', ['construction_execution_id', 'evidence_type'])
    op.create_index('ix_construction_evidence_links_construction_execution_id', 'construction_evidence_links', ['construction_execution_id'])
    op.create_index('ix_construction_evidence_links_document_version_id', 'construction_evidence_links', ['document_version_id'])
    op.create_index('ix_construction_evidence_links_material_test_id', 'construction_evidence_links', ['material_test_id'])
    op.create_index('ix_construction_evidence_links_physical_evidence_item_id', 'construction_evidence_links', ['physical_evidence_item_id'])
    op.create_index('ix_construction_evidence_links_project_id', 'construction_evidence_links', ['project_id'])
    op.create_index('ix_construction_execution_project_status', 'construction_executions', ['project_id', 'status', 'work_state'])
    op.create_index('ix_construction_executions_authority_case_id', 'construction_executions', ['authority_case_id'])
    op.create_index('ix_construction_executions_contract_id', 'construction_executions', ['contract_id'])
    op.create_index('ix_construction_executions_contract_revision_id', 'construction_executions', ['contract_revision_id'])
    op.create_index('ix_construction_executions_current_authority_snapshot_id', 'construction_executions', ['current_authority_snapshot_id'])
    op.create_index('ix_construction_executions_current_design_snapshot_id', 'construction_executions', ['current_design_snapshot_id'])
    op.create_index('ix_construction_executions_project_id', 'construction_executions', ['project_id'])
    op.create_index('ix_construction_inspection_execution', 'construction_inspections', ['construction_execution_id', 'inspection_kind', 'status'])
    op.create_index('ix_construction_inspections_authority_case_id', 'construction_inspections', ['authority_case_id'])
    op.create_index('ix_construction_inspections_construction_execution_id', 'construction_inspections', ['construction_execution_id'])
    op.create_index('ix_construction_inspections_idempotency_key', 'construction_inspections', ['idempotency_key'])
    op.create_index('ix_construction_inspections_inspector_party_id', 'construction_inspections', ['inspector_party_id'])
    op.create_index('ix_construction_inspections_project_id', 'construction_inspections', ['project_id'])
    op.create_index('ix_construction_issue_execution', 'construction_issues', ['construction_execution_id', 'status', 'severity'])
    op.create_index('ix_construction_issues_authority_case_finding_id', 'construction_issues', ['authority_case_finding_id'])
    op.create_index('ix_construction_issues_construction_execution_id', 'construction_issues', ['construction_execution_id'])
    op.create_index('ix_construction_issues_design_change_request_id', 'construction_issues', ['design_change_request_id'])
    op.create_index('ix_construction_issues_project_id', 'construction_issues', ['project_id'])
    op.create_index('ix_construction_issues_requirement_instance_id', 'construction_issues', ['requirement_instance_id'])
    op.create_index('ix_construction_obligation_definitions_authority_case_id', 'construction_obligation_definitions', ['authority_case_id'])
    op.create_index('ix_construction_obligation_definitions_policy_version_id', 'construction_obligation_definitions', ['policy_version_id'])
    op.create_index('ix_construction_obligation_definitions_project_id', 'construction_obligation_definitions', ['project_id'])
    op.create_index('ix_construction_obligation_definitions_requirement_defi_935b', 'construction_obligation_definitions', ['requirement_definition_id'])
    op.create_index('ix_construction_obligation_definitions_source_document__a0f6', 'construction_obligation_definitions', ['source_document_version_id'])
    op.create_index('ix_construction_obligation_instance_execution', 'construction_obligation_instances', ['construction_execution_id', 'status', 'due_at'])
    op.create_index('ix_construction_obligation_instances_authority_case_id', 'construction_obligation_instances', ['authority_case_id'])
    op.create_index('ix_construction_obligation_instances_construction_execution_id', 'construction_obligation_instances', ['construction_execution_id'])
    op.create_index('ix_construction_obligation_instances_due_at', 'construction_obligation_instances', ['due_at'])
    op.create_index('ix_construction_obligation_instances_project_id', 'construction_obligation_instances', ['project_id'])
    op.create_index('ix_construction_obligation_participants_obligation_instance_id', 'construction_obligation_participants', ['obligation_instance_id'])
    op.create_index('ix_construction_obligation_participants_party_id', 'construction_obligation_participants', ['party_id'])
    op.create_index('ix_construction_obligation_participants_project_id', 'construction_obligation_participants', ['project_id'])
    op.create_index('ix_construction_party_assignment_execution', 'construction_party_assignments', ['construction_execution_id', 'role_code', 'status'])
    op.create_index('ix_construction_party_assignments_authority_case_id', 'construction_party_assignments', ['authority_case_id'])
    op.create_index('ix_construction_party_assignments_construction_execution_id', 'construction_party_assignments', ['construction_execution_id'])
    op.create_index('ix_construction_party_assignments_party_id', 'construction_party_assignments', ['party_id'])
    op.create_index('ix_construction_party_assignments_party_role_assignment_id', 'construction_party_assignments', ['party_role_assignment_id'])
    op.create_index('ix_construction_party_assignments_professional_credential_id', 'construction_party_assignments', ['professional_credential_id'])
    op.create_index('ix_construction_party_assignments_project_id', 'construction_party_assignments', ['project_id'])
    op.create_index('ix_construction_party_assignments_source_document_version_id', 'construction_party_assignments', ['source_document_version_id'])
    op.create_index('ix_construction_start_authorization_execution', 'construction_start_authorizations', ['construction_execution_id', 'status'])
    op.create_index('ix_construction_start_authorizations_construction_execution_id', 'construction_start_authorizations', ['construction_execution_id'])
    op.create_index('ix_construction_start_authorizations_project_id', 'construction_start_authorizations', ['project_id'])
    op.create_index('ix_construction_start_readiness_construction_execution_id', 'construction_start_readiness', ['construction_execution_id'])
    op.create_index('ix_construction_start_readiness_execution', 'construction_start_readiness', ['construction_execution_id', 'evaluated_at'])
    op.create_index('ix_construction_start_readiness_project_id', 'construction_start_readiness', ['project_id'])
    op.create_index('ix_construction_work_control_event_execution', 'construction_work_control_events', ['construction_execution_id', 'event_at'])
    op.create_index('ix_construction_work_control_events_construction_execution_id', 'construction_work_control_events', ['construction_execution_id'])
    op.create_index('ix_construction_work_control_events_evidence_document_v_72df', 'construction_work_control_events', ['evidence_document_version_id'])
    op.create_index('ix_construction_work_control_events_project_id', 'construction_work_control_events', ['project_id'])
    op.create_index('ix_construction_work_control_events_start_authorization_id', 'construction_work_control_events', ['start_authorization_id'])
    op.create_index('ix_contact_point_case_purpose', 'contact_points', ['authority_case_id', 'purpose', 'status'])
    op.create_index('ix_contact_point_project_purpose', 'contact_points', ['project_id', 'purpose', 'status'])
    op.create_index('ix_contact_points_authority_case_id', 'contact_points', ['authority_case_id'])
    op.create_index('ix_contact_points_party_id', 'contact_points', ['party_id'])
    op.create_index('ix_contact_points_project_id', 'contact_points', ['project_id'])
    op.create_index('ix_contact_points_source_document_version_id', 'contact_points', ['source_document_version_id'])
    op.create_index('ix_contract_admin_evidence_contract_id', 'contract_admin_evidence', ['contract_id'])
    op.create_index('ix_contract_admin_evidence_contract_revision_id', 'contract_admin_evidence', ['contract_revision_id'])
    op.create_index('ix_contract_admin_evidence_document_version_id', 'contract_admin_evidence', ['document_version_id'])
    op.create_index('ix_contract_admin_inputs_contract_id', 'contract_admin_inputs', ['contract_id'])
    op.create_index('ix_contract_administrative_closures_contract_id', 'contract_administrative_closures', ['contract_id'])
    op.create_index('ix_contract_administrative_closures_project_id', 'contract_administrative_closures', ['project_id'])
    op.create_index('ix_contract_approvals_contract_revision_id', 'contract_approvals', ['contract_revision_id'])
    op.create_index('ix_contract_client_input_requirements_contract_id', 'contract_client_input_requirements', ['contract_id'])
    op.create_index('ix_contract_client_input_requirements_contract_revision_id', 'contract_client_input_requirements', ['contract_revision_id'])
    op.create_index('ix_contract_client_input_requirements_source_document_v_2916', 'contract_client_input_requirements', ['source_document_version_id'])
    op.create_index('ix_contract_deliverable_commitments_contract_id', 'contract_deliverable_commitments', ['contract_id'])
    op.create_index('ix_contract_deliverable_commitments_contract_revision_id', 'contract_deliverable_commitments', ['contract_revision_id'])
    op.create_index('ix_contract_deliverable_commitments_source_document_version_id', 'contract_deliverable_commitments', ['source_document_version_id'])
    op.create_index('ix_contract_deliverable_commitments_source_scope_item_id', 'contract_deliverable_commitments', ['source_scope_item_id'])
    op.create_index('ix_contract_execution_evidence_contract_revision_id', 'contract_execution_evidence', ['contract_revision_id'])
    op.create_index('ix_contract_milestones_contract_id', 'contract_milestones', ['contract_id'])
    op.create_index('ix_contract_milestones_contract_revision_id', 'contract_milestones', ['contract_revision_id'])
    op.create_index('ix_contract_payment_terms_contract_id', 'contract_payment_terms', ['contract_id'])
    op.create_index('ix_contract_payment_terms_contract_revision_id', 'contract_payment_terms', ['contract_revision_id'])
    op.create_index('ix_contract_payment_terms_source_document_version_id', 'contract_payment_terms', ['source_document_version_id'])
    op.create_index('ix_contract_revisions_accepted_proposal_revision_id', 'contract_revisions', ['accepted_proposal_revision_id'])
    op.create_index('ix_contract_revisions_agreement_type', 'contract_revisions', ['agreement_type'])
    op.create_index('ix_contract_revisions_contract_id', 'contract_revisions', ['contract_id'])
    op.create_index('ix_contract_revisions_controlling_quotation_revision_id', 'contract_revisions', ['controlling_quotation_revision_id'])
    op.create_index('ix_contract_template_snapshots_contract_id', 'contract_template_snapshots', ['contract_id'])
    op.create_index('ix_contract_template_snapshots_contract_revision_id', 'contract_template_snapshots', ['contract_revision_id'])
    op.create_index('ix_contracts_accepted_proposal_revision_id', 'contracts', ['accepted_proposal_revision_id'])
    op.create_index('ix_contracts_agreement_type', 'contracts', ['agreement_type'])
    op.create_index('ix_contracts_client_account_id', 'contracts', ['client_account_id'])
    op.create_index('ix_contracts_project_id', 'contracts', ['project_id'])
    op.create_index('ix_contracts_project_opportunity_ref', 'contracts', ['project_opportunity_ref'])
    op.create_index('ix_contracts_proposal_id', 'contracts', ['proposal_id'])
    op.create_index('ix_contracts_quotation_id', 'contracts', ['quotation_id'])
    op.create_index('ix_contracts_stage', 'contracts', ['stage'])
    op.create_index('ix_dashboard_input_items_context_key', 'dashboard_input_items', ['context_key'])
    op.create_index('ix_dashboard_input_items_input_key', 'dashboard_input_items', ['input_key'])
    op.create_index('ix_dashboard_input_items_status', 'dashboard_input_items', ['status'])
    op.create_index('ix_definition_entries_current_revision_id', 'definition_entries', ['current_revision_id'])
    op.create_index('ix_definition_entries_ref', 'definition_entries', ['ref'])
    op.create_index('ix_definition_entries_status', 'definition_entries', ['status'])
    op.create_index('ix_definition_entries_term', 'definition_entries', ['term'])
    op.create_index('ix_definition_revisions_definition_id', 'definition_revisions', ['definition_id'])
    op.create_index('ix_design_change_project_status', 'design_change_requests', ['project_id', 'status'])
    op.create_index('ix_document_requests_checklist_item_id', 'document_requests', ['checklist_item_id'])
    op.create_index('ix_document_requests_client_account_id', 'document_requests', ['client_account_id'])
    op.create_index('ix_document_versions_document_id', 'document_versions', ['document_id'])
    op.create_index('ix_document_versions_sha256', 'document_versions', ['sha256'])
    op.create_index('ix_documents_project_id', 'documents', ['project_id'])
    op.create_index('ix_drawing_review_cycles_project_id', 'drawing_review_cycles', ['project_id'])
    op.create_index('ix_engineering_ai_comment_artifact_review', 'engineering_ai_comment_artifacts', ['review_id', 'generated_at'])
    op.create_index('ix_engineering_ai_comment_artifacts_project_id', 'engineering_ai_comment_artifacts', ['project_id'])
    op.create_index('ix_engineering_ai_comment_artifacts_review_id', 'engineering_ai_comment_artifacts', ['review_id'])
    op.create_index('ix_engineering_authority_finding_links_authority_finding_id', 'engineering_authority_finding_links', ['authority_finding_id'])
    op.create_index('ix_engineering_authority_finding_links_project_id', 'engineering_authority_finding_links', ['project_id'])
    op.create_index('ix_engineering_authority_finding_links_review_category_id', 'engineering_authority_finding_links', ['review_category_id'])
    op.create_index('ix_engineering_authority_finding_links_review_id', 'engineering_authority_finding_links', ['review_id'])
    op.create_index('ix_engineering_authority_finding_links_revision_id', 'engineering_authority_finding_links', ['revision_id'])
    op.create_index('ix_engineering_authority_link_project', 'engineering_authority_finding_links', ['project_id', 'status'])
    op.create_index('ix_engineering_calculation_revision', 'engineering_calculation_records', ['revision_id'])
    op.create_index('ix_engineering_category_assignment_project_state', 'engineering_category_assignments', ['project_id', 'effective_state'])
    op.create_index('ix_engineering_category_assignments_project_id', 'engineering_category_assignments', ['project_id'])
    op.create_index('ix_engineering_category_assignments_review_category_id', 'engineering_category_assignments', ['review_category_id'])
    op.create_index('ix_engineering_category_assignments_work_package_id', 'engineering_category_assignments', ['work_package_id'])
    op.create_index('ix_engineering_comments_engineering_review_run_id', 'engineering_comments', ['engineering_review_run_id'])
    op.create_index('ix_engineering_comments_stable_comment_number', 'engineering_comments', ['stable_comment_number'])
    op.create_index('ix_engineering_revision_deliverable', 'engineering_deliverable_revisions', ['deliverable_id', 'sequence'])
    op.create_index('ix_engineering_revision_status', 'engineering_deliverable_revisions', ['status', 'approval_status'])
    op.create_index('ix_engineering_deliverable_discipline', 'engineering_deliverables', ['discipline'])
    op.create_index('ix_engineering_deliverable_project', 'engineering_deliverables', ['project_id', 'status'])
    op.create_index('ix_engineering_deliverables_current_revision_id', 'engineering_deliverables', ['current_revision_id'])
    op.create_index('ix_engineering_internal_review_comment_review', 'engineering_internal_review_comments', ['review_id', 'status'])
    op.create_index('ix_engineering_internal_review_comments_project_id', 'engineering_internal_review_comments', ['project_id'])
    op.create_index('ix_engineering_internal_review_comments_review_id', 'engineering_internal_review_comments', ['review_id'])
    op.create_index('ix_engineering_internal_review_comments_revision_id', 'engineering_internal_review_comments', ['revision_id'])
    op.create_index('ix_engineering_material_test_project', 'engineering_material_tests', ['project_id', 'status'])
    op.create_index('ix_engineering_approval_revision', 'engineering_professional_approvals', ['revision_id', 'status'])
    op.create_index('ix_engineering_professional_approvals_approver_party_id', 'engineering_professional_approvals', ['approver_party_id'])
    op.create_index('ix_engineering_professional_approvals_professional_cred_0990', 'engineering_professional_approvals', ['professional_credential_id'])
    op.create_index('ix_engineering_member_project', 'engineering_project_members', ['project_id', 'status'])
    op.create_index('ix_engineering_rendition_document', 'engineering_renditions', ['document_version_id'])
    op.create_index('ix_engineering_review_category_active_order', 'engineering_review_categories', ['active', 'sort_order'])
    op.create_index('ix_engineering_finding_review', 'engineering_review_findings', ['review_id', 'status', 'severity'])
    op.create_index('ix_engineering_review_runs_drawing_document_version_id', 'engineering_review_runs', ['drawing_document_version_id'])
    op.create_index('ix_engineering_review_runs_engineering_review_id', 'engineering_review_runs', ['engineering_review_id'])
    op.create_index('ix_engineering_review_runs_review_scope_id', 'engineering_review_runs', ['review_scope_id'])
    op.create_index('ix_engineering_review_scopes_engineering_review_id', 'engineering_review_scopes', ['engineering_review_id'])
    op.create_index('ix_engineering_review_scopes_project_id', 'engineering_review_scopes', ['project_id'])
    op.create_index('ix_engineering_reviews_project_id', 'engineering_reviews', ['project_id'])
    op.create_index('ix_engineering_technical_check_revision', 'engineering_technical_checks', ['revision_id', 'result'])
    op.create_index('ix_engineering_technical_check_rule_set', 'engineering_technical_checks', ['technical_rule_set_version_id'])
    op.create_index('ix_engineering_technical_checks_technical_rule_id', 'engineering_technical_checks', ['technical_rule_id'])
    op.create_index('ix_engineering_work_package_project', 'engineering_work_packages', ['project_id', 'status'])
    op.create_index('ix_expansion_fixture_resources_fixture_version', 'expansion_fixture_resources', ['fixture_version'])
    op.create_index('ix_external_bodies_jurisdiction_id', 'external_bodies', ['jurisdiction_id'])
    op.create_index('ix_external_body_jurisdiction', 'external_bodies', ['jurisdiction_id'])
    op.create_index('ix_external_body_status', 'external_bodies', ['status'])
    op.create_index('ix_external_body_units_external_body_id', 'external_body_units', ['external_body_id'])
    op.create_index('ix_external_interaction_profiles_external_body_id', 'external_interaction_profiles', ['external_body_id'])
    op.create_index('ix_external_snapshot_case', 'external_submission_snapshots', ['authority_case_id', 'external_status'])
    op.create_index('ix_external_submission_snapshots_evidence_document_version_id', 'external_submission_snapshots', ['evidence_document_version_id'])
    op.create_index('ix_field_observations_project_id', 'field_observations', ['project_id'])
    op.create_index('ix_finance_evidence_invoice_id', 'finance_evidence', ['invoice_id'])
    op.create_index('ix_financial_account_masters_legal_entity_party_id', 'financial_account_masters', ['legal_entity_party_id'])
    op.create_index('ix_financial_account_versions_currency', 'financial_account_versions', ['currency'])
    op.create_index('ix_financial_account_versions_financial_account_master_id', 'financial_account_versions', ['financial_account_master_id'])
    op.create_index('ix_financial_settlement_contexts_contract_id', 'financial_settlement_contexts', ['contract_id'])
    op.create_index('ix_financial_settlement_contexts_project_id', 'financial_settlement_contexts', ['project_id'])
    op.create_index('ix_financial_settlement_records_contract_id', 'financial_settlement_records', ['contract_id'])
    op.create_index('ix_financial_settlement_records_project_id', 'financial_settlement_records', ['project_id'])
    op.create_index('ix_findings_contract_id', 'findings', ['contract_id'])
    op.create_index('ix_findings_domain', 'findings', ['domain'])
    op.create_index('ix_findings_owner_persona', 'findings', ['owner_persona'])
    op.create_index('ix_findings_permit_id', 'findings', ['permit_id'])
    op.create_index('ix_findings_proposal_id', 'findings', ['proposal_id'])
    op.create_index('ix_form_automation_profile_source', 'form_automation_profiles', ['source_document_version_id'])
    op.create_index('ix_form_automation_profile_status', 'form_automation_profiles', ['automation_status'])
    op.create_index('ix_form_instance_context', 'form_instances', ['context_type', 'context_id'])
    op.create_index('ix_form_instance_source', 'form_instances', ['source_document_version_id'])
    op.create_index('ix_form_instance_status', 'form_instances', ['status'])
    op.create_index('ix_form_instances_mapping_release_id', 'form_instances', ['mapping_release_id'])
    op.create_index('ix_form_instances_master_content_item_id', 'form_instances', ['master_content_item_id'])
    op.create_index('ix_form_instances_profile_id', 'form_instances', ['profile_id'])
    op.create_index('ix_form_instances_source_document_version_id', 'form_instances', ['source_document_version_id'])
    op.create_index('ix_form_mapping_release_qa_gates_mapping_release_id', 'form_mapping_release_qa_gates', ['mapping_release_id'])
    op.create_index('ix_form_mapping_release_qa_gates_qa_run_id', 'form_mapping_release_qa_gates', ['qa_run_id'])
    op.create_index('ix_form_mapping_release_status', 'form_mapping_releases', ['status'])
    op.create_index('ix_form_mapping_releases_mapping_checksum', 'form_mapping_releases', ['mapping_checksum'])
    op.create_index('ix_form_mapping_releases_master_content_item_id', 'form_mapping_releases', ['master_content_item_id'])
    op.create_index('ix_form_mapping_releases_profile_id', 'form_mapping_releases', ['profile_id'])
    op.create_index('ix_form_mapping_releases_source_document_version_id', 'form_mapping_releases', ['source_document_version_id'])
    op.create_index('ix_form_mapping_rules_mapping_release_id', 'form_mapping_rules', ['mapping_release_id'])
    op.create_index('ix_form_qa_artifact', 'form_qa_runs', ['generated_artifact_id'])
    op.create_index('ix_form_qa_runs_mapping_release_id', 'form_qa_runs', ['mapping_release_id'])
    op.create_index('ix_form_signature_requirement_instance', 'form_signature_requirements', ['form_instance_id'])
    op.create_index('ix_form_validation_artifact', 'form_validation_results', ['generated_artifact_id'])
    op.create_index('ix_generated_artifact_hash', 'generated_artifacts', ['content_hash'])
    op.create_index('ix_generated_artifact_instance', 'generated_artifacts', ['form_instance_id'])
    op.create_index('ix_handover_acceptances_accepted_by_party_id', 'handover_acceptances', ['accepted_by_party_id'])
    op.create_index('ix_handover_acceptances_handover_package_revision_id', 'handover_acceptances', ['handover_package_revision_id'])
    op.create_index('ix_handover_acceptances_signature_packet_id', 'handover_acceptances', ['signature_packet_id'])
    op.create_index('ix_handover_acceptances_signed_form_document_version_id', 'handover_acceptances', ['signed_form_document_version_id'])
    op.create_index('ix_handover_distribution_requirement_revision', 'handover_distribution_requirements', ['handover_package_revision_id', 'status'])
    op.create_index('ix_handover_distribution_requirements_handover_package__88ea', 'handover_distribution_requirements', ['handover_package_revision_id'])
    op.create_index('ix_handover_distribution_requirements_recipient_party_id', 'handover_distribution_requirements', ['recipient_party_id'])
    op.create_index('ix_handover_distribution_revision_status', 'handover_distributions', ['handover_package_revision_id', 'status'])
    op.create_index('ix_handover_distributions_distribution_requirement_id', 'handover_distributions', ['distribution_requirement_id'])
    op.create_index('ix_handover_distributions_evidence_document_version_id', 'handover_distributions', ['evidence_document_version_id'])
    op.create_index('ix_handover_distributions_handover_package_revision_id', 'handover_distributions', ['handover_package_revision_id'])
    op.create_index('ix_handover_distributions_recipient_party_id', 'handover_distributions', ['recipient_party_id'])
    op.create_index('ix_handover_item_revision', 'handover_package_items', ['handover_package_revision_id', 'status'])
    op.create_index('ix_handover_package_items_as_built_baseline_id', 'handover_package_items', ['as_built_baseline_id'])
    op.create_index('ix_handover_package_items_authority_case_id', 'handover_package_items', ['authority_case_id'])
    op.create_index('ix_handover_package_items_document_version_id', 'handover_package_items', ['document_version_id'])
    op.create_index('ix_handover_package_items_engineering_rendition_id', 'handover_package_items', ['engineering_rendition_id'])
    op.create_index('ix_handover_package_items_engineering_revision_id', 'handover_package_items', ['engineering_revision_id'])
    op.create_index('ix_handover_package_items_form_instance_id', 'handover_package_items', ['form_instance_id'])
    op.create_index('ix_handover_package_items_handover_package_revision_id', 'handover_package_items', ['handover_package_revision_id'])
    op.create_index('ix_handover_package_items_rendered_artifact_id', 'handover_package_items', ['rendered_artifact_id'])
    op.create_index('ix_handover_package_revisions_approved_design_baseline_id', 'handover_package_revisions', ['approved_design_baseline_id'])
    op.create_index('ix_handover_package_revisions_as_built_baseline_id', 'handover_package_revisions', ['as_built_baseline_id'])
    op.create_index('ix_handover_package_revisions_authority_case_outcome_id', 'handover_package_revisions', ['authority_case_outcome_id'])
    op.create_index('ix_handover_package_revisions_contract_id', 'handover_package_revisions', ['contract_id'])
    op.create_index('ix_handover_package_revisions_contract_revision_id', 'handover_package_revisions', ['contract_revision_id'])
    op.create_index('ix_handover_package_revisions_handover_package_id', 'handover_package_revisions', ['handover_package_id'])
    op.create_index('ix_handover_package_revisions_policy_version_id', 'handover_package_revisions', ['policy_version_id'])
    op.create_index('ix_handover_package_revisions_project_id', 'handover_package_revisions', ['project_id'])
    op.create_index('ix_handover_package_revisions_service_engagement_id', 'handover_package_revisions', ['service_engagement_id'])
    op.create_index('ix_handover_revision_state', 'handover_package_revisions', ['handover_package_id', 'status'])
    op.create_index('ix_handover_package_project_status', 'handover_packages', ['project_id', 'status'])
    op.create_index('ix_handover_packages_contract_id', 'handover_packages', ['contract_id'])
    op.create_index('ix_handover_packages_current_revision_id', 'handover_packages', ['current_revision_id'])
    op.create_index('ix_handover_packages_project_id', 'handover_packages', ['project_id'])
    op.create_index('ix_handover_packages_service_engagement_id', 'handover_packages', ['service_engagement_id'])
    op.create_index('ix_handover_participants_handover_package_revision_id', 'handover_participants', ['handover_package_revision_id'])
    op.create_index('ix_handover_participants_party_id', 'handover_participants', ['party_id'])
    op.create_index('ix_handover_policy_versions_source_document_version_id', 'handover_policy_versions', ['source_document_version_id'])
    op.create_index('ix_handover_punch_items_handover_package_revision_id', 'handover_punch_items', ['handover_package_revision_id'])
    op.create_index('ix_handover_punch_items_package_item_id', 'handover_punch_items', ['package_item_id'])
    op.create_index('ix_handover_punch_items_resolution_evidence_document_version_id', 'handover_punch_items', ['resolution_evidence_document_version_id'])
    op.create_index('ix_handover_punch_revision_status', 'handover_punch_items', ['handover_package_revision_id', 'status', 'blocking'])
    op.create_index('ix_handover_readiness_handover_package_revision_id', 'handover_readiness', ['handover_package_revision_id'])
    op.create_index('ix_handover_receipts_distribution_id', 'handover_receipts', ['distribution_id'])
    op.create_index('ix_handover_receipts_evidence_document_version_id', 'handover_receipts', ['evidence_document_version_id'])
    op.create_index('ix_handover_receipts_received_by_party_id', 'handover_receipts', ['received_by_party_id'])
    op.create_index('ix_handover_release_authorizations_handover_package_revision_id', 'handover_release_authorizations', ['handover_package_revision_id'])
    op.create_index('ix_invoice_accept_records_invoice_revision_id', 'invoice_accept_records', ['invoice_revision_id'])
    op.create_index('ix_invoice_acknowledgments_invoice_id', 'invoice_acknowledgments', ['invoice_id'])
    op.create_index('ix_invoice_acknowledgments_issued_revision_id', 'invoice_acknowledgments', ['issued_revision_id'])
    op.create_index('ix_invoice_acknowledgments_source_document_version_id', 'invoice_acknowledgments', ['source_document_version_id'])
    op.create_index('ix_invoice_approval_records_invoice_revision_id', 'invoice_approval_records', ['invoice_revision_id'])
    op.create_index('ix_invoice_approval_records_source_document_version_id', 'invoice_approval_records', ['source_document_version_id'])
    op.create_index('ix_invoice_approvals_invoice_revision_id', 'invoice_approvals', ['invoice_revision_id'])
    op.create_index('ix_invoice_delivery_events_evidence_document_version_id', 'invoice_delivery_events', ['evidence_document_version_id'])
    op.create_index('ix_invoice_delivery_events_invoice_id', 'invoice_delivery_events', ['invoice_id'])
    op.create_index('ix_invoice_delivery_events_issue_event_id', 'invoice_delivery_events', ['issue_event_id'])
    op.create_index('ix_invoice_delivery_events_issued_revision_id', 'invoice_delivery_events', ['issued_revision_id'])
    op.create_index('ix_invoice_delivery_invoice_time', 'invoice_delivery_events', ['invoice_id', 'delivered_at'])
    op.create_index('ix_invoice_issue_events_invoice_id', 'invoice_issue_events', ['invoice_id'])
    op.create_index('ix_invoice_issue_events_invoice_revision_id', 'invoice_issue_events', ['invoice_revision_id'])
    op.create_index('ix_invoice_line_items_billing_milestone_id', 'invoice_line_items', ['billing_milestone_id'])
    op.create_index('ix_invoice_line_items_invoice_revision_id', 'invoice_line_items', ['invoice_revision_id'])
    op.create_index('ix_invoice_milestones_invoice_id', 'invoice_milestones', ['invoice_id'])
    op.create_index('ix_invoice_payment_allocations_invoice_id', 'invoice_payment_allocations', ['invoice_id'])
    op.create_index('ix_invoice_payment_allocations_payment_receipt_id', 'invoice_payment_allocations', ['payment_receipt_id'])
    op.create_index('ix_invoice_references_invoice_revision_id', 'invoice_references', ['invoice_revision_id'])
    op.create_index('ix_invoice_references_source_document_version_id', 'invoice_references', ['source_document_version_id'])
    op.create_index('ix_invoice_requirement_decisions_contract_id', 'invoice_requirement_decisions', ['contract_id'])
    op.create_index('ix_invoice_requirement_decisions_contract_revision_id', 'invoice_requirement_decisions', ['contract_revision_id'])
    op.create_index('ix_invoice_revisions_billing_plan_revision_id', 'invoice_revisions', ['billing_plan_revision_id'])
    op.create_index('ix_invoice_revisions_invoice_id', 'invoice_revisions', ['invoice_id'])
    op.create_index('ix_invoices_billing_plan_id', 'invoices', ['billing_plan_id'])
    op.create_index('ix_invoices_client_account_id', 'invoices', ['client_account_id'])
    op.create_index('ix_invoices_contract_id', 'invoices', ['contract_id'])
    op.create_index('ix_invoices_project_id', 'invoices', ['project_id'])
    op.create_index('ix_jurisdiction_parent', 'jurisdictions', ['parent_id'])
    op.create_index('ix_jurisdiction_status', 'jurisdictions', ['status'])
    op.create_index('ix_jurisdictions_parent_id', 'jurisdictions', ['parent_id'])
    op.create_index('ix_master_content_applicability_context', 'master_content_applicability', ['external_body_id', 'jurisdiction_id', 'service_type_id', 'lifecycle_phase_id'])
    op.create_index('ix_master_content_applicability_external_body_id', 'master_content_applicability', ['external_body_id'])
    op.create_index('ix_master_content_applicability_jurisdiction_id', 'master_content_applicability', ['jurisdiction_id'])
    op.create_index('ix_master_content_applicability_lifecycle_phase_id', 'master_content_applicability', ['lifecycle_phase_id'])
    op.create_index('ix_master_content_applicability_master_content_item_id', 'master_content_applicability', ['master_content_item_id'])
    op.create_index('ix_master_content_applicability_service_type_id', 'master_content_applicability', ['service_type_id'])
    op.create_index('ix_master_content_applicability_source_document_version_id', 'master_content_applicability', ['source_document_version_id'])
    op.create_index('ix_master_content_applicability_status', 'master_content_applicability', ['status'])
    op.create_index('ix_master_content_change_events_definition_id', 'master_content_change_events', ['definition_id'])
    op.create_index('ix_master_content_change_events_master_content_id', 'master_content_change_events', ['master_content_id'])
    op.create_index('ix_master_content_dependencies_downstream_id', 'master_content_dependencies', ['downstream_id'])
    op.create_index('ix_master_content_dependencies_master_content_id', 'master_content_dependencies', ['master_content_id'])
    op.create_index('ix_master_content_dependencies_project_id', 'master_content_dependencies', ['project_id'])
    op.create_index('ix_master_content_event_deliveries_event_id', 'master_content_event_deliveries', ['event_id'])
    op.create_index('ix_master_content_governance_profiles_artifact_kind', 'master_content_governance_profiles', ['artifact_kind'])
    op.create_index('ix_master_content_governance_profiles_content_ownership_class', 'master_content_governance_profiles', ['content_ownership_class'])
    op.create_index('ix_master_content_governance_profiles_currentness_status', 'master_content_governance_profiles', ['currentness_status'])
    op.create_index('ix_master_content_governance_profiles_master_content_item_id', 'master_content_governance_profiles', ['master_content_item_id'])
    op.create_index('ix_master_content_governance_profiles_official_form_no', 'master_content_governance_profiles', ['official_form_no'])
    op.create_index('ix_master_content_governance_profiles_restricted_refere_ac8e', 'master_content_governance_profiles', ['restricted_reference_sample'])
    op.create_index('ix_mcgov_artifact_kind', 'master_content_governance_profiles', ['artifact_kind'])
    op.create_index('ix_mcgov_currentness', 'master_content_governance_profiles', ['currentness_status'])
    op.create_index('ix_mcgov_official_form', 'master_content_governance_profiles', ['official_form_no'])
    op.create_index('ix_mcgov_ownership', 'master_content_governance_profiles', ['content_ownership_class'])
    op.create_index('ix_mcgov_restricted', 'master_content_governance_profiles', ['restricted_reference_sample'])
    op.create_index('ix_master_content_items_category_id', 'master_content_items', ['category_id'])
    op.create_index('ix_master_content_items_content_type', 'master_content_items', ['content_type'])
    op.create_index('ix_master_content_items_current_document_version_id', 'master_content_items', ['current_document_version_id'])
    op.create_index('ix_master_content_items_needs_review', 'master_content_items', ['needs_review'])
    op.create_index('ix_master_content_items_ref', 'master_content_items', ['ref'])
    op.create_index('ix_master_content_items_source_type_code', 'master_content_items', ['source_type_code'])
    op.create_index('ix_master_content_items_status', 'master_content_items', ['status'])
    op.create_index('ix_master_content_module_bindings_definition_id', 'master_content_module_bindings', ['definition_id'])
    op.create_index('ix_master_content_module_bindings_master_content_id', 'master_content_module_bindings', ['master_content_id'])
    op.create_index('ix_master_content_quality_flags_code', 'master_content_quality_flags', ['code'])
    op.create_index('ix_master_content_quality_flags_document_version_id', 'master_content_quality_flags', ['document_version_id'])
    op.create_index('ix_master_content_quality_flags_master_content_item_id', 'master_content_quality_flags', ['master_content_item_id'])
    op.create_index('ix_master_content_quality_flags_severity', 'master_content_quality_flags', ['severity'])
    op.create_index('ix_master_content_quality_flags_status', 'master_content_quality_flags', ['status'])
    op.create_index('ix_mcq_item', 'master_content_quality_flags', ['master_content_item_id'])
    op.create_index('ix_mcq_severity', 'master_content_quality_flags', ['severity'])
    op.create_index('ix_mcq_status', 'master_content_quality_flags', ['status'])
    op.create_index('ix_master_content_readiness_assessments_document_version_id', 'master_content_readiness_assessments', ['document_version_id'])
    op.create_index('ix_master_content_readiness_assessments_master_content_item_id', 'master_content_readiness_assessments', ['master_content_item_id'])
    op.create_index('ix_master_content_readiness_assessments_state', 'master_content_readiness_assessments', ['state'])
    op.create_index('ix_mcready_item', 'master_content_readiness_assessments', ['master_content_item_id'])
    op.create_index('ix_mcready_version', 'master_content_readiness_assessments', ['document_version_id'])
    op.create_index('ix_master_content_reference_sequences_content_type', 'master_content_reference_sequences', ['content_type'])
    op.create_index('ix_master_content_source_provenance_document_version_id', 'master_content_source_provenance', ['document_version_id'])
    op.create_index('ix_mcprov_version', 'master_content_source_provenance', ['document_version_id'])
    op.create_index('ix_master_content_source_sections_document_version_id', 'master_content_source_sections', ['document_version_id'])
    op.create_index('ix_master_content_source_sections_master_content_item_id', 'master_content_source_sections', ['master_content_item_id'])
    op.create_index('ix_master_content_source_sections_status', 'master_content_source_sections', ['status'])
    op.create_index('ix_mcsection_item', 'master_content_source_sections', ['master_content_item_id'])
    op.create_index('ix_mcsection_version', 'master_content_source_sections', ['document_version_id'])
    op.create_index('ix_notification_events_contract_id', 'notification_events', ['contract_id'])
    op.create_index('ix_notification_events_domain', 'notification_events', ['domain'])
    op.create_index('ix_notification_events_permit_id', 'notification_events', ['permit_id'])
    op.create_index('ix_notification_events_proposal_id', 'notification_events', ['proposal_id'])
    op.create_index('ix_notification_read_states_notification_event_id', 'notification_read_states', ['notification_event_id'])
    op.create_index('ix_notification_read_states_persona', 'notification_read_states', ['persona'])
    op.create_index('ix_notification_read_states_principal_key', 'notification_read_states', ['principal_key'])
    op.create_index('ix_opportunities_canonical_project_reference', 'opportunities', ['canonical_project_reference'])
    op.create_index('ix_opportunities_client_account_id', 'opportunities', ['client_account_id'])
    op.create_index('ix_opportunities_current_owner_user_id', 'opportunities', ['current_owner_user_id'])
    op.create_index('ix_opportunities_office_id', 'opportunities', ['office_id'])
    op.create_index('ix_opportunities_project_id', 'opportunities', ['project_id'])
    op.create_index('ix_opportunities_provisional_reference', 'opportunities', ['provisional_reference'])
    op.create_index('ix_opportunities_status', 'opportunities', ['status'])
    op.create_index('ix_owner_decision_aliases_canonical_key', 'owner_decision_aliases', ['canonical_key'])
    op.create_index('ix_owner_decision_history_decision_id', 'owner_decision_history', ['decision_id'])
    op.create_index('ix_owner_decision_history_decision_key', 'owner_decision_history', ['decision_key'])
    op.create_index('ix_owner_decisions_blocking_level', 'owner_decisions', ['blocking_level'])
    op.create_index('ix_owner_decisions_decision_key', 'owner_decisions', ['decision_key'])
    op.create_index('ix_owner_decisions_group_name', 'owner_decisions', ['group_name'])
    op.create_index('ix_owner_decisions_status', 'owner_decisions', ['status'])
    op.create_index('ix_owner_decisions_supersedes_decision_id', 'owner_decisions', ['supersedes_decision_id'])
    op.create_index('ix_party_role_assignment_case_status', 'party_role_assignments', ['authority_case_id', 'status'])
    op.create_index('ix_party_role_assignment_project_role', 'party_role_assignments', ['project_id', 'role_code', 'status'])
    op.create_index('ix_party_role_assignments_authority_case_id', 'party_role_assignments', ['authority_case_id'])
    op.create_index('ix_party_role_assignments_party_id', 'party_role_assignments', ['party_id'])
    op.create_index('ix_party_role_assignments_project_id', 'party_role_assignments', ['project_id'])
    op.create_index('ix_party_role_assignments_source_document_version_id', 'party_role_assignments', ['source_document_version_id'])
    op.create_index('ix_payment_receipt_scope', 'payment_receipts', ['contract_id', 'project_id', 'verification_status'])
    op.create_index('ix_payment_receipts_client_account_id', 'payment_receipts', ['client_account_id'])
    op.create_index('ix_payment_receipts_contract_id', 'payment_receipts', ['contract_id'])
    op.create_index('ix_payment_receipts_evidence_document_version_id', 'payment_receipts', ['evidence_document_version_id'])
    op.create_index('ix_payment_receipts_project_id', 'payment_receipts', ['project_id'])
    op.create_index('ix_payment_receipts_verification_status', 'payment_receipts', ['verification_status'])
    op.create_index('ix_permit_applications_controlling_contract_id', 'permit_applications', ['controlling_contract_id'])
    op.create_index('ix_permit_applications_workflow_stage', 'permit_applications', ['workflow_stage'])
    op.create_index('ix_physical_evidence_case_status', 'physical_evidence_items', ['authority_case_id', 'status'])
    op.create_index('ix_physical_evidence_items_requirement_instance_id', 'physical_evidence_items', ['requirement_instance_id'])
    op.create_index('ix_physical_evidence_requirement', 'physical_evidence_items', ['requirement_instance_id'])
    op.create_index('ix_preparation_revisions_authority_approved_design_baseline_id', 'preparation_revisions', ['authority_approved_design_baseline_id'])
    op.create_index('ix_preparation_revisions_authority_case_id', 'preparation_revisions', ['authority_case_id'])
    op.create_index('ix_preparation_revisions_authority_policy_version_id', 'preparation_revisions', ['authority_policy_version_id'])
    op.create_index('ix_preparation_revisions_authority_state', 'preparation_revisions', ['authority_state'])
    op.create_index('ix_preparation_revisions_case_party_snapshot_id', 'preparation_revisions', ['case_party_snapshot_id'])
    op.create_index('ix_project_activations_accepted_proposal_revision_id', 'project_activations', ['accepted_proposal_revision_id'])
    op.create_index('ix_project_activations_contract_id', 'project_activations', ['contract_id'])
    op.create_index('ix_project_activations_project_id', 'project_activations', ['project_id'])
    op.create_index('ix_project_archive_records_project_id', 'project_archive_records', ['project_id'])
    op.create_index('ix_project_artifact_records_content_hash', 'project_artifact_records', ['content_hash'])
    op.create_index('ix_project_artifact_records_contract_id', 'project_artifact_records', ['contract_id'])
    op.create_index('ix_project_artifact_records_document_version_id', 'project_artifact_records', ['document_version_id'])
    op.create_index('ix_project_artifact_records_evidence_artifact_id', 'project_artifact_records', ['evidence_artifact_id'])
    op.create_index('ix_project_artifact_records_opportunity_id', 'project_artifact_records', ['opportunity_id'])
    op.create_index('ix_project_artifact_records_project_id', 'project_artifact_records', ['project_id'])
    op.create_index('ix_project_closeout_assessments_policy_version_id', 'project_closeout_assessments', ['policy_version_id'])
    op.create_index('ix_project_closeout_assessments_project_id', 'project_closeout_assessments', ['project_id'])
    op.create_index('ix_project_engineering_review_revision', 'project_engineering_reviews', ['revision_id', 'status'])
    op.create_index('ix_project_engineering_reviews_review_category_id', 'project_engineering_reviews', ['review_category_id'])
    op.create_index('ix_project_handovers_project_id', 'project_handovers', ['project_id'])
    op.create_index('ix_projects_project_code', 'projects', ['project_code'], unique=True, mssql_where=sa.text('project_code IS NOT NULL'))
    op.create_index('ix_properties_project_id', 'properties', ['project_id'])
    op.create_index('ix_proposal_accepted_revisions_content_hash', 'proposal_accepted_revisions', ['content_hash'])
    op.create_index('ix_proposal_accepted_revisions_proposal_id', 'proposal_accepted_revisions', ['proposal_id'])
    op.create_index('ix_proposal_assumption_proposal_status', 'proposal_assumptions', ['proposal_id', 'status'])
    op.create_index('ix_proposal_assumptions_proposal_id', 'proposal_assumptions', ['proposal_id'])
    op.create_index('ix_proposal_client_responses_accepted_revision_id', 'proposal_client_responses', ['accepted_revision_id'])
    op.create_index('ix_proposal_client_responses_proposal_id', 'proposal_client_responses', ['proposal_id'])
    op.create_index('ix_proposal_commercial_outcomes_accepted_revision_id', 'proposal_commercial_outcomes', ['accepted_revision_id'])
    op.create_index('ix_proposal_commercial_outcomes_proposal_id', 'proposal_commercial_outcomes', ['proposal_id'])
    op.create_index('ix_proposal_conflict_proposal_status', 'proposal_conflicts', ['proposal_id', 'status'])
    op.create_index('ix_proposal_conflicts_proposal_id', 'proposal_conflicts', ['proposal_id'])
    op.create_index('ix_proposal_contact_contexts_party_id', 'proposal_contact_contexts', ['party_id'])
    op.create_index('ix_proposal_contact_contexts_proposal_id', 'proposal_contact_contexts', ['proposal_id'])
    op.create_index('ix_proposal_contact_contexts_source_document_version_id', 'proposal_contact_contexts', ['source_document_version_id'])
    op.create_index('ix_proposal_engineering_contribution_proposal', 'proposal_engineering_contributions', ['proposal_id'])
    op.create_index('ix_proposal_engineering_contributions_discipline_code', 'proposal_engineering_contributions', ['discipline_code'])
    op.create_index('ix_proposal_engineering_contributions_proposal_id', 'proposal_engineering_contributions', ['proposal_id'])
    op.create_index('ix_proposal_engineering_contributions_source_document_v_df3b', 'proposal_engineering_contributions', ['source_document_version_id'])
    op.create_index('ix_proposal_engineering_contributions_technical_rule_se_4120', 'proposal_engineering_contributions', ['technical_rule_set_version_id'])
    op.create_index('ix_proposal_expected_input_previews_content_hash', 'proposal_expected_input_previews', ['content_hash'])
    op.create_index('ix_proposal_expected_input_previews_proposal_id', 'proposal_expected_input_previews', ['proposal_id'])
    op.create_index('ix_proposal_expected_input_previews_status', 'proposal_expected_input_previews', ['status'])
    op.create_index('ix_proposal_expected_input_previews_superseded', 'proposal_expected_input_previews', ['superseded'])
    op.create_index('ix_proposal_expected_preview_proposal_created', 'proposal_expected_input_previews', ['proposal_id', 'created_at'])
    op.create_index('ix_proposal_external_cost_assumptions_external_body_id', 'proposal_external_cost_assumptions', ['external_body_id'])
    op.create_index('ix_proposal_external_cost_assumptions_proposal_id', 'proposal_external_cost_assumptions', ['proposal_id'])
    op.create_index('ix_proposal_external_cost_proposal', 'proposal_external_cost_assumptions', ['proposal_id'])
    op.create_index('ix_proposal_intake_artifacts_content_hash', 'proposal_intake_artifacts', ['content_hash'])
    op.create_index('ix_proposal_intake_artifacts_evidence_artifact_id', 'proposal_intake_artifacts', ['evidence_artifact_id'])
    op.create_index('ix_proposal_intake_artifacts_opportunity_id', 'proposal_intake_artifacts', ['opportunity_id'])
    op.create_index('ix_proposal_intake_artifacts_opportunity_reference', 'proposal_intake_artifacts', ['opportunity_reference'])
    op.create_index('ix_proposal_intake_artifacts_project_id', 'proposal_intake_artifacts', ['project_id'])
    op.create_index('ix_proposal_material_acknowledgments_proposal_id', 'proposal_material_acknowledgments', ['proposal_id'])
    op.create_index('ix_proposal_notes_proposal_created', 'proposal_notes', ['proposal_id', 'created_at'])
    op.create_index('ix_proposal_notes_proposal_id', 'proposal_notes', ['proposal_id'])
    op.create_index('ix_proposal_output_artifacts_content_hash', 'proposal_output_artifacts', ['content_hash'])
    op.create_index('ix_proposal_output_artifacts_proposal_id', 'proposal_output_artifacts', ['proposal_id'])
    op.create_index('ix_proposal_output_artifacts_revision_id', 'proposal_output_artifacts', ['revision_id'])
    op.create_index('ix_proposal_regulatory_scope_intents_external_body_id', 'proposal_regulatory_scope_intents', ['external_body_id'])
    op.create_index('ix_proposal_regulatory_scope_intents_jurisdiction_id', 'proposal_regulatory_scope_intents', ['jurisdiction_id'])
    op.create_index('ix_proposal_regulatory_scope_intents_proposal_id', 'proposal_regulatory_scope_intents', ['proposal_id'])
    op.create_index('ix_proposal_regulatory_scope_intents_proposal_scope_item_id', 'proposal_regulatory_scope_intents', ['proposal_scope_item_id'])
    op.create_index('ix_proposal_regulatory_scope_intents_service_type_id', 'proposal_regulatory_scope_intents', ['service_type_id'])
    op.create_index('ix_proposal_regulatory_scope_intents_service_type_version_id', 'proposal_regulatory_scope_intents', ['service_type_version_id'])
    op.create_index('ix_proposal_regulatory_scope_intents_source_assertion_id', 'proposal_regulatory_scope_intents', ['source_assertion_id'])
    op.create_index('ix_proposal_regulatory_scope_intents_source_document_version_id', 'proposal_regulatory_scope_intents', ['source_document_version_id'])
    op.create_index('ix_proposal_regulatory_scope_intents_status', 'proposal_regulatory_scope_intents', ['status'])
    op.create_index('ix_proposal_regulatory_scope_proposal_status', 'proposal_regulatory_scope_intents', ['proposal_id', 'status'])
    op.create_index('ix_proposal_revisions_base_accepted_revision_id', 'proposal_revisions', ['base_accepted_revision_id'])
    op.create_index('ix_proposal_revisions_content_hash', 'proposal_revisions', ['content_hash'])
    op.create_index('ix_proposal_revisions_proposal_id', 'proposal_revisions', ['proposal_id'])
    op.create_index('ix_proposal_service_scope_items_discipline_code', 'proposal_service_scope_items', ['discipline_code'])
    op.create_index('ix_proposal_service_scope_items_external_body_id', 'proposal_service_scope_items', ['external_body_id'])
    op.create_index('ix_proposal_service_scope_items_proposal_id', 'proposal_service_scope_items', ['proposal_id'])
    op.create_index('ix_proposal_service_scope_items_regulatory_service_type_id', 'proposal_service_scope_items', ['regulatory_service_type_id'])
    op.create_index('ix_proposal_service_scope_items_service_offering_code', 'proposal_service_scope_items', ['service_offering_code'])
    op.create_index('ix_proposal_service_scope_items_source_document_version_id', 'proposal_service_scope_items', ['source_document_version_id'])
    op.create_index('ix_proposal_service_scope_proposal_order', 'proposal_service_scope_items', ['proposal_id', 'sort_order'])
    op.create_index('ix_proposal_site_contexts_property_id', 'proposal_site_contexts', ['property_id'])
    op.create_index('ix_proposal_site_contexts_proposal_id', 'proposal_site_contexts', ['proposal_id'])
    op.create_index('ix_proposal_site_contexts_source_document_version_id', 'proposal_site_contexts', ['source_document_version_id'])
    op.create_index('ix_proposal_source_evidence_conflict_key', 'proposal_source_evidence', ['conflict_key'])
    op.create_index('ix_proposal_source_evidence_content_hash', 'proposal_source_evidence', ['content_hash'])
    op.create_index('ix_proposal_source_evidence_proposal_id', 'proposal_source_evidence', ['proposal_id'])
    op.create_index('ix_proposal_source_evidence_source_type', 'proposal_source_evidence', ['source_type'])
    op.create_index('ix_proposal_source_links_active', 'proposal_source_links', ['active'])
    op.create_index('ix_proposal_source_links_document_id', 'proposal_source_links', ['document_id'])
    op.create_index('ix_proposal_source_links_document_version_id', 'proposal_source_links', ['document_version_id'])
    op.create_index('ix_proposal_source_links_proposal_id', 'proposal_source_links', ['proposal_id'])
    op.create_index('ix_proposal_source_links_source_evidence_id', 'proposal_source_links', ['source_evidence_id'])
    op.create_index('ix_proposal_source_links_source_role', 'proposal_source_links', ['source_role'])
    op.create_index('ix_proposal_stakeholder_intents_party_id', 'proposal_stakeholder_intents', ['party_id'])
    op.create_index('ix_proposal_stakeholder_intents_proposal_id', 'proposal_stakeholder_intents', ['proposal_id'])
    op.create_index('ix_proposal_stakeholder_intents_role_code', 'proposal_stakeholder_intents', ['role_code'])
    op.create_index('ix_proposal_stakeholder_intents_source_document_version_id', 'proposal_stakeholder_intents', ['source_document_version_id'])
    op.create_index('ix_proposal_stakeholder_proposal_status', 'proposal_stakeholder_intents', ['proposal_id', 'status'])
    op.create_index('ix_proposal_staleness_events_proposal_id', 'proposal_staleness_events', ['proposal_id'])
    op.create_index('ix_proposal_staleness_proposal_status', 'proposal_staleness_events', ['proposal_id', 'status'])
    op.create_index('ix_proposal_unknown_proposal_status', 'proposal_unknowns', ['proposal_id', 'status'])
    op.create_index('ix_proposal_unknowns_proposal_id', 'proposal_unknowns', ['proposal_id'])
    op.create_index('ix_quotation_approvals_quotation_revision_id', 'quotation_approvals', ['quotation_revision_id'])
    op.create_index('ix_quotation_field_observations_quotation_revision_id', 'quotation_field_observations', ['quotation_revision_id'])
    op.create_index('ix_quotation_revisions_quotation_id', 'quotation_revisions', ['quotation_id'])
    op.create_index('ix_quotations_client_account_id', 'quotations', ['client_account_id'])
    op.create_index('ix_quotations_opportunity_id', 'quotations', ['opportunity_id'])
    op.create_index('ix_receivable_follow_ups_contact_party_id', 'receivable_follow_ups', ['contact_party_id'])
    op.create_index('ix_receivable_follow_ups_invoice_id', 'receivable_follow_ups', ['invoice_id'])
    op.create_index('ix_regulation_applicabilities_context_id', 'regulation_applicabilities', ['context_id'])
    op.create_index('ix_regulation_applicabilities_regulation_version_id', 'regulation_applicabilities', ['regulation_version_id'])
    op.create_index('ix_regulation_applicabilities_review_scope_id', 'regulation_applicabilities', ['review_scope_id'])
    op.create_index('ix_regulation_versions_regulation_source_id', 'regulation_versions', ['regulation_source_id'])
    op.create_index('ix_regulatory_closeout_assessments_project_id', 'regulatory_closeout_assessments', ['project_id'])
    op.create_index('ix_regulatory_closeout_assessments_service_engagement_id', 'regulatory_closeout_assessments', ['service_engagement_id'])
    op.create_index('ix_regulatory_journey_project', 'regulatory_journeys', ['project_id'])
    op.create_index('ix_regulatory_journey_status', 'regulatory_journeys', ['status'])
    op.create_index('ix_regulatory_journeys_external_body_id', 'regulatory_journeys', ['external_body_id'])
    op.create_index('ix_regulatory_journeys_jurisdiction_id', 'regulatory_journeys', ['jurisdiction_id'])
    op.create_index('ix_regulatory_journeys_project_id', 'regulatory_journeys', ['project_id'])
    op.create_index('ix_regulatory_journeys_service_type_id', 'regulatory_journeys', ['service_type_id'])
    op.create_index('ix_regulatory_phase_order', 'regulatory_lifecycle_phases', ['sort_order'])
    op.create_index('ix_regulatory_relation_source', 'regulatory_relations', ['source_type', 'source_id'])
    op.create_index('ix_regulatory_relation_target', 'regulatory_relations', ['target_type', 'target_id'])
    op.create_index('ix_rendered_artifacts_context_id', 'rendered_artifacts', ['context_id'])
    op.create_index('ix_rendered_artifacts_template_version_id', 'rendered_artifacts', ['template_version_id'])
    op.create_index('ix_requirement_applicability_context', 'requirement_applicability_decisions', ['context_type', 'context_id'])
    op.create_index('ix_requirement_applicability_decisions_policy_item_id', 'requirement_applicability_decisions', ['policy_item_id'])
    op.create_index('ix_requirement_decision_context', 'requirement_decisions', ['context_type', 'context_id'])
    op.create_index('ix_requirement_definition_status', 'requirement_definitions', ['status'])
    op.create_index('ix_requirement_evaluation_context', 'requirement_evaluations', ['context_type', 'context_id'])
    op.create_index('ix_requirement_evaluation_policy', 'requirement_evaluations', ['policy_version_id'])
    op.create_index('ix_requirement_evidence_constraints_policy_item_id', 'requirement_evidence_constraints', ['policy_item_id'])
    op.create_index('ix_requirement_evidence_evaluation_requirement', 'requirement_evidence_evaluations', ['requirement_evaluation_id'])
    op.create_index('ix_requirement_evidence_evaluations_document_version_id', 'requirement_evidence_evaluations', ['document_version_id'])
    op.create_index('ix_requirement_groups_policy_version_id', 'requirement_groups', ['policy_version_id'])
    op.create_index('ix_requirement_instance_case_status', 'requirement_instances', ['authority_case_id', 'status'])
    op.create_index('ix_requirement_instances_group_id', 'requirement_instances', ['group_id'])
    op.create_index('ix_requirement_instances_lifecycle_phase_id', 'requirement_instances', ['lifecycle_phase_id'])
    op.create_index('ix_requirement_policy_item_policy', 'requirement_policy_items', ['policy_version_id'])
    op.create_index('ix_requirement_policy_item_requirement', 'requirement_policy_items', ['requirement_definition_id'])
    op.create_index('ix_requirement_policy_items_group_id', 'requirement_policy_items', ['group_id'])
    op.create_index('ix_requirement_policy_items_phase_id', 'requirement_policy_items', ['phase_id'])
    op.create_index('ix_requirement_policy_items_source_section_id', 'requirement_policy_items', ['source_section_id'])
    op.create_index('ix_requirement_policy_lineage_document_version_id', 'requirement_policy_lineage', ['document_version_id'])
    op.create_index('ix_requirement_policy_lineage_governance_status', 'requirement_policy_lineage', ['governance_status'])
    op.create_index('ix_requirement_policy_lineage_master_content_item_id', 'requirement_policy_lineage', ['master_content_item_id'])
    op.create_index('ix_requirement_policy_lineage_policy_version_id', 'requirement_policy_lineage', ['policy_version_id'])
    op.create_index('ix_requirement_policy_lineage_source_section_id', 'requirement_policy_lineage', ['source_section_id'])
    op.create_index('ix_requirement_policy_context', 'requirement_policy_versions', ['service_type_id', 'jurisdiction_id', 'external_body_id'])
    op.create_index('ix_requirement_policy_effective', 'requirement_policy_versions', ['effective_from', 'effective_to'])
    op.create_index('ix_requirement_policy_status', 'requirement_policy_versions', ['status'])
    op.create_index('ix_rfqs_opportunity_id', 'rfqs', ['opportunity_id'])
    op.create_index('ix_rfqs_source_document_version_id', 'rfqs', ['source_document_version_id'])
    op.create_index('ix_semantic_key_status', 'semantic_key_definitions', ['status'])
    op.create_index('ix_semantic_assertion_context', 'semantic_value_assertions', ['context_type', 'context_id'])
    op.create_index('ix_semantic_assertion_key', 'semantic_value_assertions', ['semantic_key_id'])
    op.create_index('ix_service_engagement_project_status', 'service_engagements', ['project_id', 'status'])
    op.create_index('ix_service_engagements_contract_id', 'service_engagements', ['contract_id'])
    op.create_index('ix_service_engagements_contract_revision_id', 'service_engagements', ['contract_revision_id'])
    op.create_index('ix_service_engagements_project_id', 'service_engagements', ['project_id'])
    op.create_index('ix_service_engagements_proposal_scope_item_id', 'service_engagements', ['proposal_scope_item_id'])
    op.create_index('ix_service_scope_closures_contract_id', 'service_scope_closures', ['contract_id'])
    op.create_index('ix_service_scope_closures_contract_revision_id', 'service_scope_closures', ['contract_revision_id'])
    op.create_index('ix_service_scope_closures_project_id', 'service_scope_closures', ['project_id'])
    op.create_index('ix_service_scope_closures_service_engagement_id', 'service_scope_closures', ['service_engagement_id'])
    op.create_index('ix_service_type_version_effective', 'service_type_versions', ['service_type_id', 'effective_from', 'effective_to'])
    op.create_index('ix_service_type_versions_service_type_id', 'service_type_versions', ['service_type_id'])
    op.create_index('ix_service_type_status', 'service_types', ['status'])
    op.create_index('ix_service_types_current_version_id', 'service_types', ['current_version_id'])
    op.create_index('ix_signature_packet_instance', 'signature_packets', ['form_instance_id'])
    op.create_index('ix_source_intake_batches_source_archive_hash', 'source_intake_batches', ['source_archive_hash'])
    op.create_index('ix_source_intake_batches_status', 'source_intake_batches', ['status'])
    op.create_index('ix_source_intake_item_batch_disposition', 'source_intake_items', ['batch_id', 'disposition'])
    op.create_index('ix_source_intake_items_batch_id', 'source_intake_items', ['batch_id'])
    op.create_index('ix_source_intake_items_disposition', 'source_intake_items', ['disposition'])
    op.create_index('ix_source_intake_items_duplicate_group', 'source_intake_items', ['duplicate_group'])
    op.create_index('ix_source_intake_items_promotion_status', 'source_intake_items', ['promotion_status'])
    op.create_index('ix_source_intake_items_sha256', 'source_intake_items', ['sha256'])
    op.create_index('ix_source_intake_items_target_document_version_id', 'source_intake_items', ['target_document_version_id'])
    op.create_index('ix_source_intake_items_target_master_content_id', 'source_intake_items', ['target_master_content_id'])
    op.create_index('ix_storage_operation_document_version', 'storage_operations', ['document_version_id'])
    op.create_index('ix_storage_operation_state', 'storage_operations', ['state'])
    op.create_index('ix_storage_operations_document_id', 'storage_operations', ['document_id'])
    op.create_index('ix_storage_operations_document_version_id', 'storage_operations', ['document_version_id'])
    op.create_index('ix_storage_outbox_status', 'storage_outbox_events', ['status'])
    op.create_index('ix_submission_attempt_case_state', 'submission_attempts', ['authority_case_id', 'state'])
    op.create_index('ix_submission_package_item_package', 'submission_package_items', ['package_id'])
    op.create_index('ix_submission_package_items_as_built_baseline_id', 'submission_package_items', ['as_built_baseline_id'])
    op.create_index('ix_submission_package_items_baseline_id', 'submission_package_items', ['baseline_id'])
    op.create_index('ix_submission_package_items_baseline_member_id', 'submission_package_items', ['baseline_member_id'])
    op.create_index('ix_submission_package_items_document_version_id', 'submission_package_items', ['document_version_id'])
    op.create_index('ix_submission_package_items_evidence_selection_id', 'submission_package_items', ['evidence_selection_id'])
    op.create_index('ix_submission_package_items_form_instance_id', 'submission_package_items', ['form_instance_id'])
    op.create_index('ix_submission_package_items_physical_evidence_item_id', 'submission_package_items', ['physical_evidence_item_id'])
    op.create_index('ix_submission_package_items_requirement_instance_id', 'submission_package_items', ['requirement_instance_id'])
    op.create_index('ix_submission_package_case_state', 'submission_packages', ['authority_case_id', 'state'])
    op.create_index('ix_submission_precheck_check_run', 'submission_precheck_checks', ['precheck_run_id', 'blocking', 'result'])
    op.create_index('ix_submission_precheck_case_result', 'submission_precheck_runs', ['authority_case_id', 'result'])
    op.create_index('ix_submission_precheck_runs_policy_version_id', 'submission_precheck_runs', ['policy_version_id'])
    op.create_index('ix_system_blocks_context_id', 'system_blocks', ['context_id'])
    op.create_index('ix_technical_rule_evaluation_context', 'technical_rule_evaluations', ['context_type', 'context_id'])
    op.create_index('ix_technical_rule_lineage_document_version_id', 'technical_rule_lineage', ['document_version_id'])
    op.create_index('ix_technical_rule_lineage_governance_status', 'technical_rule_lineage', ['governance_status'])
    op.create_index('ix_technical_rule_lineage_master_content_item_id', 'technical_rule_lineage', ['master_content_item_id'])
    op.create_index('ix_technical_rule_lineage_source_section_id', 'technical_rule_lineage', ['source_section_id'])
    op.create_index('ix_technical_rule_lineage_technical_rule_id', 'technical_rule_lineage', ['technical_rule_id'])
    op.create_index('ix_technical_rule_set_context', 'technical_rule_set_versions', ['service_type_id', 'jurisdiction_id', 'external_body_id'])
    op.create_index('ix_technical_rule_set_effective', 'technical_rule_set_versions', ['effective_from', 'effective_to'])
    op.create_index('ix_technical_rule_set_status', 'technical_rule_set_versions', ['status'])
    op.create_index('ix_technical_rule_set_versions_external_body_id', 'technical_rule_set_versions', ['external_body_id'])
    op.create_index('ix_technical_rule_set_versions_jurisdiction_id', 'technical_rule_set_versions', ['jurisdiction_id'])
    op.create_index('ix_technical_rule_set_versions_service_type_id', 'technical_rule_set_versions', ['service_type_id'])
    op.create_index('ix_technical_rule_set', 'technical_rules', ['rule_set_version_id'])
    op.create_index('ix_technical_rule_status', 'technical_rules', ['status'])
    op.create_index('ix_template_versions_template_definition_id', 'template_versions', ['template_definition_id'])
    op.create_index('ix_tender_documents_document_version_id', 'tender_documents', ['document_version_id'])
    op.create_index('ix_tender_documents_opportunity_id', 'tender_documents', ['opportunity_id'])
    op.create_index('ix_users_entra_object_id', 'users', ['entra_object_id'], unique=True, mssql_where=sa.text('entra_object_id IS NOT NULL'))
    op.create_index('ix_verified_assertions_project_id', 'verified_assertions', ['project_id'])
    op.create_index('ix_workflow_tasks_assistant_id', 'workflow_tasks', ['assistant_id'])
    op.create_index('ix_workflow_tasks_context_id', 'workflow_tasks', ['context_id'])
    op.create_index('ix_workflow_tasks_task_family', 'workflow_tasks', ['task_family'])
    op.create_index('uq_as_built_baseline_member', 'as_built_baseline_members', ['baseline_id', 'engineering_revision_id', 'rendition_id', 'building_snapshot_id'], unique=True, mssql_where=sa.text('engineering_revision_id IS NOT NULL AND rendition_id IS NOT NULL AND building_snapshot_id IS NOT NULL'))
    op.create_index('uq_as_built_variance_field', 'as_built_variances', ['comparison_run_id', 'building_asset_id', 'field_key'], unique=True, mssql_where=sa.text('building_asset_id IS NOT NULL'))
    op.create_index('uq_case_party_snapshot_scope', 'case_party_snapshots', ['authority_case_id', 'preparation_revision_id', 'snapshot_number'], unique=True, mssql_where=sa.text('preparation_revision_id IS NOT NULL'))
    op.create_index('uq_construction_inspection_idempotency', 'construction_inspections', ['construction_execution_id', 'idempotency_key'], unique=True, mssql_where=sa.text('idempotency_key IS NOT NULL'))
    op.create_index('uq_engineering_category_assignment_scope', 'engineering_category_assignments', ['project_id', 'work_package_id', 'review_category_id'], unique=True, mssql_where=sa.text('work_package_id IS NOT NULL'))
    op.create_index('engineering_deliverable_revisions_idempotency_key_key', 'engineering_deliverable_revisions', ['idempotency_key'], unique=True, mssql_where=sa.text('idempotency_key IS NOT NULL'))
    op.create_index('engineering_work_packages_idempotency_key_key', 'engineering_work_packages', ['idempotency_key'], unique=True, mssql_where=sa.text('idempotency_key IS NOT NULL'))
    op.create_index('uq_master_content_applicability_version', 'master_content_applicability', ['master_content_item_id', 'source_document_version_id', 'external_body_id', 'jurisdiction_id', 'service_type_id', 'lifecycle_phase_id'], unique=True, mssql_where=sa.text('jurisdiction_id IS NOT NULL AND lifecycle_phase_id IS NOT NULL'))
    op.create_index('uq_definition_module_binding', 'master_content_module_bindings', ['definition_id', 'module', 'usage_type'], unique=True, mssql_where=sa.text('definition_id IS NOT NULL'))
    op.create_index('uq_master_content_module_binding', 'master_content_module_bindings', ['master_content_id', 'module', 'usage_type'], unique=True, mssql_where=sa.text('master_content_id IS NOT NULL'))
    op.create_index('uq_regulatory_closeout_scope', 'regulatory_closeout_assessments', ['project_id', 'service_engagement_id'], unique=True, mssql_where=sa.text('service_engagement_id IS NOT NULL'))
    op.create_index('uq_requirement_policy_item', 'requirement_policy_items', ['policy_version_id', 'requirement_definition_id', 'phase_id'], unique=True, mssql_where=sa.text('phase_id IS NOT NULL'))
    op.create_index('uq_requirement_policy_lineage', 'requirement_policy_lineage', ['policy_version_id', 'master_content_item_id', 'document_version_id', 'source_section_id'], unique=True, mssql_where=sa.text('source_section_id IS NOT NULL'))
    op.create_index('uq_requirement_policy_context_version', 'requirement_policy_versions', ['service_type_id', 'jurisdiction_id', 'external_body_id', 'version'], unique=True, mssql_where=sa.text('jurisdiction_id IS NOT NULL AND external_body_id IS NOT NULL'))
    op.create_index('uq_technical_rule_lineage', 'technical_rule_lineage', ['technical_rule_id', 'master_content_item_id', 'document_version_id', 'source_section_id'], unique=True, mssql_where=sa.text('source_section_id IS NOT NULL'))

    bind = op.get_bind()
    bind.execute(sa.text("INSERT INTO master_content_reference_sequences (active, content_type, created_at, current_value, id, padding, prefix, scope, updated_at) SELECT :value_0, :value_1, CURRENT_TIMESTAMP, :value_3, :value_4, :value_5, :value_6, :value_7, CURRENT_TIMESTAMP WHERE NOT EXISTS (SELECT 1 FROM master_content_reference_sequences WHERE content_type = :value_1 AND scope = :value_7)"),
        {'value_0': True, 'value_1': 'PROPOSAL_REFERENCE', 'value_3': 0, 'value_4': 'proposal-reference-sequence', 'value_5': 4, 'value_6': 'AMEC-SYN-PROP', 'value_7': 'GLOBAL'})
    # Control data source: accepted reference revision 0055; no business rows.

    op.create_table(
        "phase4_source_change_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("event_id", sa.String(160), nullable=False),
        sa.Column("scan_id_or_observation_group", sa.String(160), nullable=False),
        sa.Column("source_surface", sa.String(80), nullable=False),
        sa.Column("source_artifact_id_or_locator", sa.String(500), nullable=False),
        sa.Column("source_version_id", sa.String(160)),
        sa.Column("source_version_token", sa.String(160), nullable=False),
        sa.Column("source_collection_role_if_applicable", sa.String(120)),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("observed_size", sa.Integer),
        sa.Column("observed_mtime", sa.String(80)),
        sa.Column("previous_observation_id", sa.String(160)),
        sa.Column("origin", sa.String(40), nullable=False),
        sa.Column("correlation_id", sa.String(160), nullable=False),
        sa.Column("observed_at", sa.String(80), nullable=False),
        sa.Column("stability_state", sa.String(40), nullable=False),
        sa.Column("observation_count", sa.Integer, nullable=False),
        sa.Column("stability_window_seconds", sa.Integer, nullable=False),
        sa.Column("content_identity_proof", sa.JSON, nullable=False),
        sa.Column("immutable_payload_hash", sa.String(64), nullable=False),
        sa.Column("record_version", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("event_id", name="uq_phase4_source_event_id"),
    )
    op.create_table(
        "phase4_document_evidence_envelopes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("root_event_id", sa.String(36), nullable=False),
        sa.Column("source_artifact_id", sa.String(500), nullable=False),
        sa.Column("source_version_id", sa.String(160)),
        sa.Column("source_version_token", sa.String(160), nullable=False),
        sa.Column("source_surface", sa.String(80), nullable=False),
        sa.Column("evidence_envelope_sha256", sa.String(64), nullable=False),
        sa.Column("document_intelligence_runtime_version", sa.String(100), nullable=False),
        sa.Column("runtime_sha256", sa.String(64), nullable=False),
        sa.Column("capability_id", sa.String(160), nullable=False),
        sa.Column("handler_parser_identity", sa.String(200), nullable=False),
        sa.Column("metering_json", sa.JSON, nullable=False),
        sa.Column("warnings_json", sa.JSON, nullable=False),
        sa.Column("content_retention_class", sa.String(80), nullable=False),
        sa.Column("unsupported_capability_state", sa.String(120)),
        sa.Column("evidence_json", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("evidence_envelope_sha256", name="uq_phase4_evidence_envelope_sha"),
    )
    op.create_table(
        "phase4_classification_envelopes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("envelope_id", sa.String(160), nullable=False),
        sa.Column("root_event_id", sa.String(36), nullable=False),
        sa.Column("document_version_id", sa.String(36)),
        sa.Column("source_mode", sa.String(60), nullable=False),
        sa.Column("classifier_version", sa.String(100), nullable=False),
        sa.Column("rules_version", sa.String(100), nullable=False),
        sa.Column("taxonomy_revision", sa.String(100), nullable=False),
        sa.Column("module_truth_contract_sha", sa.String(64), nullable=False),
        sa.Column("corpus_app_contract_sha", sa.String(64), nullable=False),
        sa.Column("axes_json", sa.JSON, nullable=False),
        sa.Column("immutable_result_hash", sa.String(64), nullable=False),
        sa.Column("record_version", sa.Integer, nullable=False),
        sa.Column("status", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("envelope_id", name="uq_phase4_classification_envelope_id"),
    )
    op.create_table(
        "phase4_review_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("decision_id", sa.String(160), nullable=False),
        sa.Column("classification_envelope_id", sa.String(36), nullable=False),
        sa.Column("decision", sa.String(40), nullable=False),
        sa.Column("actor_id", sa.String(200), nullable=False),
        sa.Column("capability", sa.String(160), nullable=False),
        sa.Column("scope_type", sa.String(80), nullable=False),
        sa.Column("scope_id", sa.String(160), nullable=False),
        sa.Column("record_version", sa.Integer, nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("corrections_json", sa.JSON, nullable=False),
        sa.Column("immutable_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("decision_id", name="uq_phase4_review_decision_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_phase4_review_decision_idempotency"),
    )
    op.create_table(
        "phase4_classifier_correction_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source_version", sa.String(160), nullable=False),
        sa.Column("classification_envelope_id", sa.String(36), nullable=False),
        sa.Column("axis", sa.String(80), nullable=False),
        sa.Column("old_value_json", sa.JSON),
        sa.Column("new_value_json", sa.JSON),
        sa.Column("reason", sa.Text, nullable=False),
        sa.Column("reviewer", sa.String(200), nullable=False),
        sa.Column("evidence_ids_json", sa.JSON, nullable=False),
        sa.Column("classifier_version", sa.String(100), nullable=False),
        sa.Column("rules_version", sa.String(100), nullable=False),
        sa.Column("taxonomy_revision", sa.String(100), nullable=False),
        sa.Column("module_truth_contract_sha", sa.String(64), nullable=False),
        sa.Column("immutable_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "phase4_projection_plans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("verified_assertion_id", sa.String(36), nullable=False),
        sa.Column("target_domain", sa.String(80), nullable=False),
        sa.Column("target_entity_type", sa.String(100), nullable=False),
        sa.Column("target_entity_id", sa.String(160), nullable=False),
        sa.Column("precondition_version", sa.String(160), nullable=False),
        sa.Column("plan_json", sa.JSON, nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("result", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_phase4_projection_plan_idempotency"),
    )
    op.create_table(
        "phase4_projection_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("projection_id", sa.String(160), nullable=False),
        sa.Column("root_event_id", sa.String(36)),
        sa.Column("verified_assertion_id", sa.String(36), nullable=False),
        sa.Column("module_truth_contract_sha", sa.String(64), nullable=False),
        sa.Column("corpus_app_contract_sha", sa.String(64), nullable=False),
        sa.Column("target_domain", sa.String(80), nullable=False),
        sa.Column("target_entity_type", sa.String(100), nullable=False),
        sa.Column("target_entity_id", sa.String(160), nullable=False),
        sa.Column("operation", sa.String(80), nullable=False),
        sa.Column("precondition_version", sa.String(160), nullable=False),
        sa.Column("postcondition_version", sa.String(160), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("result", sa.String(40), nullable=False),
        sa.Column("created_ids_json", sa.JSON, nullable=False),
        sa.Column("updated_ids_json", sa.JSON, nullable=False),
        sa.Column("work_ids_json", sa.JSON, nullable=False),
        sa.Column("issue_ids_json", sa.JSON, nullable=False),
        sa.Column("notification_ids_json", sa.JSON, nullable=False),
        sa.Column("audit_ids_json", sa.JSON, nullable=False),
        sa.Column("failure_or_review_reason", sa.Text),
        sa.Column("correlation_id", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("projection_id", name="uq_phase4_projection_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_phase4_projection_idempotency"),
    )
    op.create_table(
        "phase4_verified_assertion_bridges",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("bridge_id", sa.String(160), nullable=False),
        sa.Column("classification_envelope_id", sa.String(36), nullable=False),
        sa.Column("review_decision_id", sa.String(36), nullable=False),
        sa.Column("verified_assertion_id", sa.String(36), nullable=False),
        sa.Column("strategy", sa.String(80), nullable=False),
        sa.Column("lineage_json", sa.JSON, nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("bridge_id", name="uq_phase4_bridge_id"),
        sa.UniqueConstraint("idempotency_key", name="uq_phase4_bridge_idempotency"),
    )

def downgrade() -> None:
    raise RuntimeError("Azure SQL canonical root downgrade is intentionally unsupported")
