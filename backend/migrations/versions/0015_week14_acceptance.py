"""Week 14 acceptance rehearsal and G10 evidence records."""

from alembic import op
from backend.app.models import Base

revision = "0015_week14_acceptance"
down_revision = "0014_week13_operations"
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    bind = op.get_bind()
    for table in [
        "production_mode_decisions", "g10_evidence_items", "role_readiness_matrix", "pilot_workflow_approvals",
        "shadow_defect_dispositions", "acceptance_metrics", "acceptance_rehearsal_runs",
    ]:
        op.drop_table(table)
