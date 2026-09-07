"""BD Proposal Forms-v2 final hardening companions."""

from alembic import op
import sqlalchemy as sa

from backend.app.models import Base


revision = "0055_bd_proposal_final_hardening"
down_revision = "0054_bd_proposal_stage1_reconciliation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    op.execute(sa.text("""
        INSERT INTO master_content_reference_sequences
            (id, content_type, prefix, padding, scope, active, current_value, created_at, updated_at)
        SELECT 'proposal-reference-sequence', 'PROPOSAL_REFERENCE', 'AMEC-SYN-PROP', 4, 'GLOBAL', TRUE, 0, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
        WHERE NOT EXISTS (
            SELECT 1 FROM master_content_reference_sequences
            WHERE content_type = 'PROPOSAL_REFERENCE' AND scope = 'GLOBAL'
        )
    """))
    for name in (
        "proposal_unknowns",
        "proposal_conflicts",
        "proposal_material_acknowledgments",
        "proposal_staleness_events",
        "proposal_revisions",
        "proposal_client_responses",
        "proposal_commercial_outcomes",
    ):
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for name in (
        "proposal_commercial_outcomes",
        "proposal_client_responses",
        "proposal_revisions",
        "proposal_staleness_events",
        "proposal_material_acknowledgments",
        "proposal_conflicts",
        "proposal_unknowns",
    ):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
