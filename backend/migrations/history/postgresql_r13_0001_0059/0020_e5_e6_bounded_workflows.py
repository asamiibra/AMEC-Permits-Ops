"""E5/E6 bounded engineering and commercial-closeout contracts."""

import sqlalchemy as sa
from alembic import op

revision = "0020_e5_e6_bounded_workflows"
down_revision = "0019_e3_e4_traceability"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    # A prior interrupted SQLite batch migration can leave its private temp
    # table behind. It contains no committed application rows and is safe to
    # remove before retrying this additive migration.
    for table in ("invoice_revisions", "project_handovers", "regulation_applicabilities", "engineering_reviews", "engineering_review_runs", "engineering_comments"):
        op.execute(sa.text(f"DROP TABLE IF EXISTS _alembic_tmp_{table}"))

    def add_missing(table, columns):
        existing = {item["name"] for item in inspector.get_columns(table)}
        missing = [column for column in columns if column.name not in existing]
        if missing:
            with op.batch_alter_table(table) as batch:
                for column in missing:
                    batch.add_column(column)

    add_missing("invoices", [
        sa.Column("requirement_decision_id", sa.String(36), nullable=True),
    ])
    add_missing("invoice_revisions", [
        sa.Column("template_version_id", sa.String(36), nullable=True),
        sa.Column("rendered_artifact_id", sa.String(36), nullable=True),
        sa.Column("render_input_hash", sa.String(64), nullable=True),
        sa.Column("content_hash", sa.String(64), nullable=True),
        sa.Column("source_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("stale_reason", sa.Text(), nullable=True),
    ])
    add_missing("accounting_handoffs", [
        sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    ])
    add_missing("project_handovers", [
        sa.Column("readiness_checks", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("selected_deliverables", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("approval_state", sa.String(50), nullable=False, server_default="HANDOVER_DRAFT_READY"),
        sa.Column("approved_by", sa.String(200), nullable=True),
        sa.Column("approved_role", sa.String(100), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("release_evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("release_evidence_status", sa.String(60), nullable=False, server_default="NOT_RECORDED"),
        sa.Column("stale_reason", sa.Text(), nullable=True),
    ])
    add_missing("regulation_applicabilities", [
        sa.Column("review_scope_id", sa.String(36), nullable=True),
        sa.Column("basis_evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    ])
    add_missing("engineering_reviews", [
        sa.Column("current_scope_id", sa.String(36), nullable=True),
        sa.Column("current_drawing_version_id", sa.String(36), nullable=True),
    ])
    add_missing("engineering_review_runs", [
        sa.Column("review_scope_id", sa.String(36), nullable=True),
        sa.Column("pinned_drawing_hash", sa.String(64), nullable=True),
        sa.Column("pinned_revision_label", sa.String(50), nullable=True),
        sa.Column("model_config_version", sa.String(80), nullable=True),
        sa.Column("prompt_bundle_version", sa.String(80), nullable=True),
        sa.Column("evidence_recipe", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    ])
    add_missing("engineering_comments", [
        sa.Column("stable_comment_number", sa.String(60), nullable=True),
        sa.Column("location_reference", sa.String(200), nullable=True),
        sa.Column("issue_text", sa.Text(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("regulation_version_id", sa.String(36), nullable=True),
        sa.Column("regulation_evidence_reference", sa.String(300), nullable=True),
        sa.Column("severity", sa.String(30), nullable=False, server_default="ADVISORY"),
        sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("uncertainty_state", sa.String(50), nullable=False, server_default="SUPPORTED_EVIDENCE"),
        sa.Column("engineer_notes", sa.Text(), nullable=True),
        sa.Column("closure_state", sa.String(50), nullable=False, server_default="OPEN"),
        sa.Column("required_action", sa.Text(), nullable=True),
        sa.Column("supersedes_comment_id", sa.String(36), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("correction_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("re_reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("evidence_snapshot", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
    ])
    add_missing("drawing_review_cycles", [
        sa.Column("material_change_reason", sa.Text(), nullable=True),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
    ])

    tables = set(inspector.get_table_names())
    if "invoice_requirement_decisions" not in tables:
        op.create_table(
            "invoice_requirement_decisions",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("contract_id", sa.String(36), sa.ForeignKey("contracts.id"), nullable=False),
            sa.Column("contract_revision_id", sa.String(36), sa.ForeignKey("contract_revisions.id"), nullable=False),
            sa.Column("milestone_id", sa.String(36), sa.ForeignKey("contract_milestones.id"), nullable=True),
            sa.Column("decision", sa.String(40), nullable=False),
            sa.Column("decision_source", sa.String(50), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("decided_by", sa.String(200), nullable=True),
            sa.Column("rule_id", sa.String(120), nullable=True),
            sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "finance_evidence" not in tables:
        op.create_table(
            "finance_evidence",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("invoice_id", sa.String(36), sa.ForeignKey("invoices.id"), nullable=False),
            sa.Column("evidence_type", sa.String(60), nullable=False),
            sa.Column("status", sa.String(60), nullable=False),
            sa.Column("source", sa.String(60), nullable=False),
            sa.Column("evidence_reference", sa.String(300), nullable=False),
            sa.Column("recorded_by", sa.String(200), nullable=False),
            sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "engineering_review_scopes" not in tables:
        op.create_table(
            "engineering_review_scopes",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("engineering_review_id", sa.String(36), sa.ForeignKey("engineering_reviews.id"), nullable=False),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=False),
            sa.Column("scope_code", sa.String(100), unique=True, nullable=False),
            sa.Column("discipline", sa.String(100), nullable=False),
            sa.Column("supported_drawing_types", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("selected_regulation_version_ids", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("applicability_basis", sa.Text(), nullable=False),
            sa.Column("review_objectives", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("excluded_topics", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("authorized_engineer_role", sa.String(100), nullable=False, server_default="AUTHORIZED_ENGINEER"),
            sa.Column("stage2_disposition", sa.String(40), nullable=False, server_default="UNDECIDED_STAGE2"),
            sa.Column("evidence_class", sa.String(100), nullable=False, server_default="SYNTHETIC_IMPLEMENTATION_EVIDENCE"),
            sa.Column("status", sa.String(50), nullable=False, server_default="CONFIGURED"),
            sa.Column("synthetic_only", sa.Boolean(), nullable=False, server_default=sa.text("TRUE")),
        )


def downgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    revision_tables = {"finance_evidence", "invoice_requirement_decisions", "engineering_review_scopes"}

    # These tables are created from the current model metadata by the
    # preceding expansion migration, so their parent tables can still carry
    # reverse foreign keys when this revision is downgraded.
    for table in ("invoices", "engineering_reviews", "engineering_review_runs", "regulation_applicabilities"):
        for foreign_key in inspector.get_foreign_keys(table):
            if foreign_key.get("referred_table") in revision_tables and foreign_key.get("name"):
                op.drop_constraint(foreign_key["name"], table, type_="foreignkey")

    for table in ("finance_evidence", "invoice_requirement_decisions", "engineering_review_scopes"):
        if table in inspector.get_table_names():
            op.drop_table(table)
