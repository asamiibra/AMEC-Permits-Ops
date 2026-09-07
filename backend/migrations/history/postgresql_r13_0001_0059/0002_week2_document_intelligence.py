"""Week 2 document intelligence and controlled configuration schema."""
revision = "0002_week2_document_intelligence"
down_revision = "0001_week1_skeleton"
branch_labels = None
depends_on = None

from backend.app.models import Base

def upgrade():
    from alembic import op
    Base.metadata.create_all(bind=op.get_bind())

def downgrade():
    # Week 2 tables are intentionally left intact in this lightweight local migration.
    pass
