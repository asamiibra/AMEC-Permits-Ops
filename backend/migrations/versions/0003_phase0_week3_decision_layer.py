"""Phase 0 Week 3 decision layer.

Revision ID: 0003_phase0_week3_decision_layer
Revises: 0002_week2_document_intelligence
"""
from alembic import op
import sqlalchemy as sa
from backend.app.models.base import Base

revision = "0003_phase0_week3_decision_layer"
down_revision = "0002_week2_document_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("raid_items")}
    if "phase0_close_impact" not in existing:
        op.add_column("raid_items", sa.Column("phase0_close_impact", sa.String(length=30), nullable=False, server_default="NONE"))
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    bind = op.get_bind()
    # Week 3 owns these decision/evidence tables. Shared Week 1/2 tables are
    # intentionally preserved (including raid_items after its column is removed).
    for table in [
        "signoff_c_proposals", "stage2_review_acknowledgements", "stage2_baselines",
        "phase0_decisions", "pilot_cohorts", "precheck_decisions", "municipality_operation_decisions",
        "delivery_scenarios", "business_kpi_targets", "business_baselines", "tier2_backlog_items",
        "tier1_decisions", "acceptance_corpus_definitions", "threshold_definitions",
        "adjudication_histories", "adjudication_cases", "phase_baselines",
    ]:
        if table in sa.inspect(bind).get_table_names():
            op.drop_table(table)
    if "phase0_close_impact" in {column["name"] for column in sa.inspect(bind).get_columns("raid_items")}:
        op.drop_column("raid_items", "phase0_close_impact")
