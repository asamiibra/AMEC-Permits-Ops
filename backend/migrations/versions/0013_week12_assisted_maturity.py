"""Week 12 in-scope variant, attended authentication, and handoff maturity."""

from alembic import op
import sqlalchemy as sa
from backend.app.models import Base

revision = "0013_week12_assisted_maturity"
down_revision = "0012_week11_monitoring"
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
    _add_columns(bind, "submission_handoffs", [
        ("from_user_id", sa.Column("from_user_id", sa.String(36), nullable=True)),
        ("from_role", sa.Column("from_role", sa.String(80), nullable=True)),
        ("final_submitter_role", sa.Column("final_submitter_role", sa.String(80), nullable=True)),
        ("handoff_state", sa.Column("handoff_state", sa.String(50), nullable=True)),
        ("checklist_hash", sa.Column("checklist_hash", sa.String(64), nullable=True)),
        ("accepted_at", sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True)),
        ("cancelled_at", sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True)),
        ("correlation_id", sa.Column("correlation_id", sa.String(100), nullable=True)),
    ])


def downgrade():
    bind = op.get_bind()
    for table in ["human_takeover_events", "mfa_challenge_events", "attended_auth_sessions", "target_rendering_coverages", "variant_compatibility_results", "scenario_variants"]:
        if table in sa.inspect(bind).get_table_names():
            op.drop_table(table)
    existing = {column["name"] for column in sa.inspect(bind).get_columns("submission_handoffs")}
    for name in ["from_user_id", "from_role", "final_submitter_role", "handoff_state", "checklist_hash", "accepted_at", "cancelled_at", "correlation_id"]:
        if name in existing:
            op.drop_column("submission_handoffs", name)
