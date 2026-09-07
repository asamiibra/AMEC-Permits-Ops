"""Week 10 finding closure, precheck correction, submission-cycle, and resubmission controls."""

from alembic import op
import sqlalchemy as sa
from backend.app.models import Base

revision = "0011_week10_closure_resubmission"
down_revision = "0010_week1_8_integrity_reconciliation"
branch_labels = None
depends_on = None


def _add_columns(bind, table_name, columns):
    existing = {column["name"] for column in sa.inspect(bind).get_columns(table_name)}
    for name, column in columns:
        if name not in existing:
            op.add_column(table_name, column)


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    _add_columns(bind, "finding_codes", [
        ("finding_class", sa.Column("finding_class", sa.String(60), nullable=False, server_default="DATA_INTEGRITY")),
        ("typical_root_cause_category", sa.Column("typical_root_cause_category", sa.String(100), nullable=False, server_default="UNKNOWN_REVIEW_REQUIRED")),
        ("closure_verifier_role", sa.Column("closure_verifier_role", sa.String(100), nullable=False, server_default="REQUIREMENT_STEWARD")),
        ("allowed_dispositions", sa.Column("allowed_dispositions", sa.JSON(), nullable=False, server_default="[]")),
        ("resubmission_gate_effect", sa.Column("resubmission_gate_effect", sa.String(60), nullable=False, server_default="STILL_BLOCKS")),
        ("precheck_gate_effect", sa.Column("precheck_gate_effect", sa.String(60), nullable=False, server_default="BLOCKS_PRECHECK")),
        ("recurrence_key_strategy", sa.Column("recurrence_key_strategy", sa.String(100), nullable=False, server_default="CODE_OBJECT")),
    ])
    _add_columns(bind, "submission_cycles", [
        ("preparation_revision_id", sa.Column("preparation_revision_id", sa.String(36), nullable=True)),
        ("source_reference", sa.Column("source_reference", sa.String(300), nullable=True)),
        ("submitted_snapshot_id", sa.Column("submitted_snapshot_id", sa.String(36), nullable=True)),
        ("submission_confirmation_id", sa.Column("submission_confirmation_id", sa.String(36), nullable=True)),
        ("authority_repetition_number", sa.Column("authority_repetition_number", sa.Integer(), nullable=True)),
        ("started_at", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True)),
        ("submitted_at", sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True)),
        ("returned_at", sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True)),
        ("approved_at", sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True)),
        ("closed_at", sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True)),
    ])
    _add_columns(bind, "authority_precheck_runs", [
        ("clearance_result", sa.Column("clearance_result", sa.String(60), nullable=True)),
        ("invalidated_at", sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True)),
        ("invalidated_reason", sa.Column("invalidated_reason", sa.Text(), nullable=True)),
    ])


def downgrade():
    bind = op.get_bind()
    for table in [
        "field_matrix_coverage", "requirement_matrix_coverage", "rule_candidates", "control_runs",
        "control_definitions", "resubmission_readiness_evaluations", "approval_applicability_evaluations",
        "submitted_snapshots", "precheck_clearance_evaluations", "finding_history_links",
        "finding_reopen_events", "finding_disputes", "finding_closure_evaluations",
        "finding_resolution_evidence", "finding_resolutions",
    ]:
        if table in sa.inspect(bind).get_table_names():
            op.drop_table(table)
    for table, columns in {
        "finding_codes": ["finding_class", "typical_root_cause_category", "closure_verifier_role", "allowed_dispositions", "resubmission_gate_effect", "precheck_gate_effect", "recurrence_key_strategy"],
        "submission_cycles": ["preparation_revision_id", "source_reference", "submitted_snapshot_id", "submission_confirmation_id", "authority_repetition_number", "started_at", "submitted_at", "returned_at", "approved_at", "closed_at"],
        "authority_precheck_runs": ["clearance_result", "invalidated_at", "invalidated_reason"],
    }.items():
        existing = {column["name"] for column in sa.inspect(bind).get_columns(table)}
        for column in columns:
            if column in existing:
                op.drop_column(table, column)
