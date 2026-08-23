"""Week 11 read-only monitoring and portal drift guardrails."""

from alembic import op
import sqlalchemy as sa
from backend.app.models import Base

revision = "0012_week11_monitoring"
down_revision = "0011_week10_closure_resubmission"
branch_labels = None
depends_on = None


def upgrade():
    # The repository uses metadata-backed migrations for its modular monolith;
    # this also keeps SQLite and PostgreSQL clean-target creation identical.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    bind = op.get_bind()
    for table in [
        "operator_task_timings", "notification_delivery_attempts",
        "external_mutation_observations", "human_monitoring_captures",
        "authority_state_comparisons", "authority_comment_observations",
        "authority_status_observations", "monitoring_state_snapshots", "portal_contract_validation_runs",
        "portal_drift_events", "portal_read_contracts", "monitoring_checks",
        "monitoring_execution_decisions", "monitoring_runs", "monitoring_policies",
    ]:
        if table in sa.inspect(bind).get_table_names():
            op.drop_table(table)
