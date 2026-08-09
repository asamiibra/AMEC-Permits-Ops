"""Week 7 finding, task, SLA, authority-event, and notification core."""

from alembic import op
from backend.app.models import Base

revision = "0007_week7_findings"
down_revision = "0006_confirmation_binding"
branch_labels = None
depends_on = None


def upgrade():
    # Additive metadata migration keeps SQLite and PostgreSQL definitions in
    # lockstep while allowing the modular monolith to retain its single model
    # registry.
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    bind = op.get_bind()
    suffix = " CASCADE" if bind.dialect.name == "postgresql" else ""
    for table in [
        "portal_validation_finding_rules", "notification_events", "finding_routing_rules",
        "workflow_tasks", "findings", "authority_events", "submission_cycles",
        "finding_sla_policies", "finding_codes",
    ]:
        bind.exec_driver_sql(f"DROP TABLE IF EXISTS {table}{suffix}")
