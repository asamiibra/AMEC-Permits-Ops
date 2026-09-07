"""Week 4–5 package foundation and assisted municipality workflow."""

from alembic import op
from backend.app.models import Base

revision = "0005_week45"
down_revision = "0004_recording_reconciliation_foundation"
branch_labels = None
depends_on = None


def upgrade():
    # The Week 4–5 seam is additive and is intentionally created from the
    # same SQLAlchemy metadata used by the application.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    bind = op.get_bind()
    for table in [
        "operator_exercise_evidence", "municipality_preparation_exceptions", "submission_handoffs",
        "attended_sessions", "authority_precheck_items", "authority_precheck_runs",
        "human_portal_verifications", "portal_reconciliation_results", "portal_snapshots",
        "portal_intended_states", "portal_grid_row_intents", "preparation_snapshots",
        "preparation_revisions", "approvals", "excel_projections", "rendered_forms",
        "form_template_versions", "form_templates", "attachment_manifests", "package_items",
        "packages", "readiness_result_items", "package_readiness_evaluations",
        "minimum_package_definitions", "office_credentials", "professional_credentials",
        "applicable_rule_sets",
    ]:
        bind.exec_driver_sql(f"DROP TABLE IF EXISTS {table}")
