"""Typed Proposal Intake notes for Stage 1 reconciliation."""

from alembic import op
import sqlalchemy as sa

revision = "0054_bd_proposal_stage1_reconciliation"
down_revision = "0053_handover_admin_closeout"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS proposal_notes (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            proposal_id VARCHAR(36) NOT NULL REFERENCES opportunities(id),
            note_type VARCHAR(40) NOT NULL DEFAULT 'INTERNAL_INTAKE',
            content TEXT NOT NULL,
            entered_by VARCHAR(200) NOT NULL,
            related_contact VARCHAR(240),
            provenance JSON NOT NULL DEFAULT '{}',
            status VARCHAR(40) NOT NULL DEFAULT 'UNVERIFIED_CONTEXT',
            created_at TIMESTAMP WITH TIME ZONE NOT NULL,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL
        )
    """))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_proposal_notes_proposal_id ON proposal_notes (proposal_id)"))
    op.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_proposal_notes_proposal_created ON proposal_notes (proposal_id, created_at)"))


def downgrade() -> None:
    op.execute(sa.text("DROP TABLE IF EXISTS proposal_notes"))
