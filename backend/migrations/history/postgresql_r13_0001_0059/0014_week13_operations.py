"""Week 13 recurrence, support, incident, and recovery records."""

from alembic import op
from backend.app.models import Base

revision = "0014_week13_operations"
down_revision = "0013_week12_assisted_maturity"
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    bind = op.get_bind()
    for table in [
        "role_training_checklists", "kill_switch_readiness", "restore_rehearsals", "recovery_manifests",
        "incident_impact_assessments", "workflow_safety_holds", "integrity_incidents", "support_cases",
        "finding_prevention_controls", "prior_finding_preventive_checks", "finding_recurrence_analysis_items",
        "finding_recurrence_analysis_runs",
    ]:
        op.drop_table(table)
