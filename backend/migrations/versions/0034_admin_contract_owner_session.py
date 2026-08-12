"""Administration Contract owner session and explicit Project activation."""

import sqlalchemy as sa
from alembic import op


revision = "0034_admin_contract_owner_session"
down_revision = "0033_dashboard_owner_session_v3"
branch_labels = None
depends_on = None


def _add(table: str, column: sa.Column) -> None:
    bind = op.get_bind()
    if column.name not in {item["name"] for item in sa.inspect(bind).get_columns(table)}:
        op.add_column(table, column)


def upgrade() -> None:
    _add("projects", sa.Column("project_code", sa.String(80), nullable=True))
    _add("projects", sa.Column("start_date", sa.Date(), nullable=True))
    _add("projects", sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True))
    _add("projects", sa.Column("activated_by", sa.String(200), nullable=True))
    _add("contracts", sa.Column("contract_name", sa.String(250), nullable=True))
    _add("contracts", sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=True))
    _add("contracts", sa.Column("accepted_proposal_revision_id", sa.String(36), sa.ForeignKey("proposal_accepted_revisions.id"), nullable=True))
    _add("contracts", sa.Column("project_opportunity_ref", sa.String(120), nullable=True))
    _add("contracts", sa.Column("stage", sa.String(50), nullable=False, server_default="DRAFT"))
    _add("contracts", sa.Column("amount_value", sa.String(100), nullable=True))
    _add("contracts", sa.Column("currency", sa.String(20), nullable=True))
    _add("contracts", sa.Column("duration", sa.String(120), nullable=True))
    _add("contracts", sa.Column("expected_close_date", sa.Date(), nullable=True))
    _add("contracts", sa.Column("actual_close_date", sa.Date(), nullable=True))
    _add("contracts", sa.Column("close_date_meaning", sa.String(120), nullable=True))
    _add("contracts", sa.Column("authority_state", sa.String(50), nullable=False, server_default="NOT_REVIEWED"))
    _add("contracts", sa.Column("last_activity_at", sa.DateTime(timezone=True), nullable=True))
    _add("contracts", sa.Column("field_provenance", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    _add("contract_revisions", sa.Column("accepted_proposal_revision_id", sa.String(36), sa.ForeignKey("proposal_accepted_revisions.id"), nullable=True))
    _add("contract_revisions", sa.Column("source_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    _add("contract_revisions", sa.Column("contract_name", sa.String(250), nullable=True))
    _add("contract_revisions", sa.Column("stage", sa.String(50), nullable=False, server_default="DRAFT"))
    _add("contract_revisions", sa.Column("amount_value", sa.String(100), nullable=True))
    _add("contract_revisions", sa.Column("currency", sa.String(20), nullable=True))
    _add("contract_revisions", sa.Column("duration", sa.String(120), nullable=True))
    _add("contract_revisions", sa.Column("expected_close_date", sa.Date(), nullable=True))
    _add("contract_revisions", sa.Column("actual_close_date", sa.Date(), nullable=True))
    _add("contract_revisions", sa.Column("admin_input_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing = set(inspector.get_table_names())
    if "contract_reference_sequences" not in existing:
        op.create_table("contract_reference_sequences", sa.Column("id", sa.String(36), primary_key=True), sa.Column("sequence_key", sa.String(60), nullable=False, unique=True), sa.Column("next_number", sa.Integer(), nullable=False, server_default="1"))
    if "contract_template_snapshots" not in existing:
        op.create_table("contract_template_snapshots", sa.Column("id", sa.String(36), primary_key=True), sa.Column("contract_id", sa.String(36), sa.ForeignKey("contracts.id"), nullable=False), sa.Column("contract_revision_id", sa.String(36), sa.ForeignKey("contract_revisions.id"), nullable=False), sa.Column("master_content_id", sa.String(36), sa.ForeignKey("master_content_items.id"), nullable=False), sa.Column("master_content_ref", sa.String(100), nullable=False), sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False), sa.Column("version", sa.String(40), nullable=False), sa.Column("content_hash", sa.String(64), nullable=False), sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False), sa.Column("captured_by", sa.String(200), nullable=False))
    if "contract_admin_inputs" not in existing:
        op.create_table("contract_admin_inputs", sa.Column("id", sa.String(36), primary_key=True), sa.Column("contract_id", sa.String(36), sa.ForeignKey("contracts.id"), nullable=False), sa.Column("input_key", sa.String(120), nullable=False), sa.Column("value_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")), sa.Column("entered_by", sa.String(200), nullable=False), sa.Column("reason", sa.Text(), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("contract_id", "input_key", name="uq_contract_admin_input_key"))
    if "contract_admin_evidence" not in existing:
        op.create_table("contract_admin_evidence", sa.Column("id", sa.String(36), primary_key=True), sa.Column("contract_id", sa.String(36), sa.ForeignKey("contracts.id"), nullable=False), sa.Column("contract_revision_id", sa.String(36), sa.ForeignKey("contract_revisions.id"), nullable=True), sa.Column("evidence_type", sa.String(100), nullable=False), sa.Column("source_reference", sa.String(600), nullable=False), sa.Column("content_hash", sa.String(64)), sa.Column("status", sa.String(40), nullable=False, server_default="RECORDED"), sa.Column("recorded_by", sa.String(200), nullable=False), sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False), sa.Column("metadata_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    if "project_activations" not in existing:
        op.create_table("project_activations", sa.Column("id", sa.String(36), primary_key=True), sa.Column("contract_id", sa.String(36), sa.ForeignKey("contracts.id"), nullable=False), sa.Column("contract_revision_id", sa.String(36), sa.ForeignKey("contract_revisions.id"), nullable=False), sa.Column("accepted_proposal_revision_id", sa.String(36), sa.ForeignKey("proposal_accepted_revisions.id"), nullable=True), sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False), sa.Column("project_code", sa.String(80), nullable=False, unique=True), sa.Column("start_date", sa.Date(), nullable=False), sa.Column("original_start_date", sa.Date(), nullable=False), sa.Column("activated_by", sa.String(200), nullable=False), sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("idempotency_key", sa.String(200), nullable=False, unique=True), sa.Column("status", sa.String(40), nullable=False, server_default="ACTIVE"), sa.Column("audit_metadata", sa.JSON(), nullable=False, server_default=sa.text("'{}'")), sa.UniqueConstraint("contract_id", name="uq_project_activation_contract"), sa.UniqueConstraint("project_id", name="uq_project_activation_project"))
    for table, column in (("projects", "project_code"), ("contracts", "proposal_id"), ("contracts", "accepted_proposal_revision_id"), ("contracts", "stage"), ("contracts", "project_opportunity_ref"), ("contract_revisions", "accepted_proposal_revision_id"), ("contract_template_snapshots", "contract_id"), ("contract_admin_inputs", "contract_id"), ("contract_admin_evidence", "contract_id"), ("project_activations", "contract_id"), ("project_activations", "project_id")):
        index_name = f"ix_{table}_{column}"
        if index_name not in {item["name"] for item in sa.inspect(bind).get_indexes(table)}:
            op.create_index(index_name, table, [column])


def downgrade() -> None:
    # Additive migration; production downgrade is intentionally conservative.
    pass
