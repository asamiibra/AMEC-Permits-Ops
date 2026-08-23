"""Week 1 canonical schema."""
revision = "0001_week1_skeleton"
down_revision = None
branch_labels = None
depends_on = None

from backend.app.models import Base

def upgrade():
    from alembic import op
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)

def downgrade():
    from alembic import op
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
