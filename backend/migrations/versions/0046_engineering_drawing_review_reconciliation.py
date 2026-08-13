"""Engineering Drawing Review categories, assignments, and future comment seam."""

import sqlalchemy as sa
from alembic import op

from backend.app.models import Base


revision = "0046_engineering_drawing_review_reconciliation"
down_revision = "0045_admin_contract_owner_sketch_reconciliation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for name in (
        "engineering_review_categories",
        "engineering_category_assignments",
        "engineering_internal_review_comments",
        "engineering_ai_comment_artifacts",
        "engineering_authority_finding_links",
    ):
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)
    if "review_category_id" not in {item["name"] for item in sa.inspect(bind).get_columns("project_engineering_reviews")}: 
        column = sa.Column("review_category_id", sa.String(36), sa.ForeignKey("engineering_review_categories.id"), nullable=True)
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("project_engineering_reviews", recreate="always") as batch:
                batch.add_column(column)
        else:
            op.add_column("project_engineering_reviews", column)
    op.create_index("ix_project_engineering_reviews_review_category_id", "project_engineering_reviews", ["review_category_id"], if_not_exists=True)
    op.create_index("uq_engineering_deliverable_revision_sequence", "engineering_deliverable_revisions", ["deliverable_id", "sequence"], unique=True, if_not_exists=True)


def downgrade() -> None:
    # Additive Engineering review evidence is retained during downgrade.
    pass
