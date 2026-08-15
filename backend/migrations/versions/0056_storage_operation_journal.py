"""Add durable storage journal and publication outbox."""

from alembic import op

from backend.app.models import StorageOperation, StorageOutboxEvent

revision = "0056_storage_operation_journal"
down_revision = "0055_bd_proposal_final_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    StorageOperation.__table__.create(bind=bind, checkfirst=True)
    StorageOutboxEvent.__table__.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    StorageOutboxEvent.__table__.drop(bind=bind, checkfirst=True)
    StorageOperation.__table__.drop(bind=bind, checkfirst=True)

