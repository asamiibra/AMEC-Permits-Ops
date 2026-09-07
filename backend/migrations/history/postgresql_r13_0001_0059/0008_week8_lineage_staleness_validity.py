"""Week 8 relational lineage, material changes, validity, and shadow evidence."""

from alembic import op
from backend.app.models import Base

revision = "0008_week8_lineage"
down_revision = "0007_week7_findings"
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    bind = op.get_bind()
    for table in [
        "shadow_corrections", "corpus_case_results", "corpus_cases", "corpus_runs",
        "configuration_change_impact_policies", "authority_approval_validities",
        "document_validities", "stale_reasons", "material_change_events", "lineage_edges",
    ]:
        bind.exec_driver_sql(f"DROP TABLE IF EXISTS {table}")
