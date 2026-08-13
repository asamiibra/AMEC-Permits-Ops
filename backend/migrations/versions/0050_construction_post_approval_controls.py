"""Add construction and post-approval execution controls."""

from alembic import op

from backend.app.models import Base


revision = "0050_construction_post_approval_controls"
down_revision = "0049_billing_v2_communication_due_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    tables = (
        "construction_executions",
        "authority_approved_design_snapshots",
        "construction_design_snapshots",
        "construction_start_readiness",
        "construction_start_authorizations",
        "construction_party_assignments",
        "construction_obligation_definitions",
        "construction_obligation_instances",
        "construction_obligation_participants",
        "construction_work_control_events",
        "construction_authority_notifications",
        "construction_correspondence",
        "construction_inspections",
        "construction_issues",
        "construction_evidence_links",
    )
    for table in tables:
        Base.metadata.tables[table].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    # Construction evidence is an audit boundary. Preserve it during ordinary
    # downgrades; operators must explicitly archive the domain if ever needed.
    pass
