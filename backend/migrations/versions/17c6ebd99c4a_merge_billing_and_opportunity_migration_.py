"""merge billing and opportunity migration heads

Revision ID: 17c6ebd99c4a
Revises: billing_module_closure_v8, opportunity_proposal_idempotency_v1
Create Date: 2026-09-12 23:26:15.831827

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "17c6ebd99c4a"
down_revision = ('billing_module_closure_v8', 'opportunity_proposal_idempotency_v1')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
