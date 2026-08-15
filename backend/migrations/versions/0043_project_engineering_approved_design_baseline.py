"""Project Engineering and immutable approved design baseline companions."""

from alembic import op
import sqlalchemy as sa

from backend.app.models import Base


revision = "0043_project_engineering_approved_design_baseline"
down_revision = "0042_bd_proposal_forms_driven_v2"
branch_labels = None
depends_on = None


TABLES = (
    "engineering_project_members",
    "engineering_work_packages",
    "engineering_deliverables",
    "engineering_deliverable_revisions",
    "engineering_renditions",
    "project_engineering_reviews",
    "engineering_review_findings",
    "engineering_professional_approvals",
    "engineering_technical_checks",
    "engineering_calculation_records",
    "engineering_material_tests",
    "approved_design_baselines",
    "approved_design_baseline_members",
    "design_change_requests",
)


def upgrade() -> None:
    # Deliverables and revisions reference each other. Creating each table
    # independently makes PostgreSQL reject an upgrade from the deployed
    # 0042 schema because the referenced table does not exist yet. Let
    # SQLAlchemy sort the table set and emit cyclic foreign keys afterward.
    bind = op.get_bind()
    Base.metadata.create_all(
        bind=bind,
        tables=[Base.metadata.tables[name] for name in TABLES],
        checkfirst=True,
    )


def downgrade() -> None:
    # Drop in reverse dependency order; no existing canonical data is touched.
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=op.get_bind(), checkfirst=True)
