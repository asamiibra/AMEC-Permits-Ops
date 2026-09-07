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
    # Retained tables survive a downgrade. Reconcile only this migration's
    # owned FKs when they are absent on a later re-upgrade.
    if bind.dialect.name == "postgresql":
        for table_name, constraint_name, columns, referred_table in (
            ("engineering_internal_review_comments", "engineering_internal_review_comments_review_id_fkey", ["review_id"], "project_engineering_reviews"),
            ("engineering_internal_review_comments", "engineering_internal_review_comments_revision_id_fkey", ["revision_id"], "engineering_deliverable_revisions"),
            ("engineering_ai_comment_artifacts", "engineering_ai_comment_artifacts_review_id_fkey", ["review_id"], "project_engineering_reviews"),
            ("engineering_ai_comment_artifacts", "engineering_ai_comment_artifacts_revision_id_fkey", ["revision_id"], "engineering_deliverable_revisions"),
            ("engineering_category_assignments", "engineering_category_assignments_review_category_id_fkey", ["review_category_id"], "engineering_review_categories"),
            ("engineering_category_assignments", "engineering_category_assignments_work_package_id_fkey", ["work_package_id"], "engineering_work_packages"),
            ("engineering_authority_finding_links", "engineering_authority_finding_links_review_id_fkey", ["review_id"], "project_engineering_reviews"),
            ("engineering_authority_finding_links", "engineering_authority_finding_links_review_category_id_fkey", ["review_category_id"], "engineering_review_categories"),
            ("engineering_authority_finding_links", "engineering_authority_finding_links_revision_id_fkey", ["revision_id"], "engineering_deliverable_revisions"),
            ("engineering_authority_finding_links", "engineering_authority_finding_links_authority_finding_id_fkey", ["authority_finding_id"], "authority_case_findings"),
        ):
            exists = bind.execute(sa.text(
                "SELECT 1 FROM pg_constraint WHERE conname = :constraint_name"
            ), {"constraint_name": constraint_name}).scalar()
            if not exists:
                op.create_foreign_key(
                    constraint_name, table_name, referred_table, columns, ["id"]
                )


def downgrade() -> None:
    # The tables are retained as an additive audit boundary, but their FKs into
    # earlier-owned tables must be removed before those tables are downgraded.
    for table_name, constraint_name in (
        ("engineering_internal_review_comments", "engineering_internal_review_comments_review_id_fkey"),
        ("engineering_internal_review_comments", "engineering_internal_review_comments_revision_id_fkey"),
        ("engineering_ai_comment_artifacts", "engineering_ai_comment_artifacts_review_id_fkey"),
        ("engineering_ai_comment_artifacts", "engineering_ai_comment_artifacts_revision_id_fkey"),
        ("engineering_category_assignments", "engineering_category_assignments_review_category_id_fkey"),
        ("engineering_category_assignments", "engineering_category_assignments_work_package_id_fkey"),
        ("engineering_authority_finding_links", "engineering_authority_finding_links_review_id_fkey"),
        ("engineering_authority_finding_links", "engineering_authority_finding_links_review_category_id_fkey"),
        ("engineering_authority_finding_links", "engineering_authority_finding_links_revision_id_fkey"),
        ("engineering_authority_finding_links", "engineering_authority_finding_links_authority_finding_id_fkey"),
    ):
        op.execute(sa.text(
            f"ALTER TABLE {table_name} DROP CONSTRAINT IF EXISTS {constraint_name}"
        ))
