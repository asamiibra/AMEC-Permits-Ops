"""Proposal Intelligence v1 module-owned review binding."""

from alembic import op
import sqlalchemy as sa


revision = "p08_proposal_intelligence"
down_revision = "p07_intelligence_foundation_closure"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proposal_intelligence_review_bindings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workflow_task_id", sa.String(length=36), nullable=False),
        sa.Column("proposal_id", sa.String(length=36), nullable=False),
        sa.Column("review_subject_type", sa.String(length=80), nullable=False),
        sa.Column("review_subject_id", sa.String(length=160), nullable=False),
        sa.Column("candidate_assertion_id", sa.String(length=36), nullable=True),
        sa.Column("work_product_id", sa.String(length=36), nullable=True),
        sa.Column("context_snapshot_id", sa.String(length=36), nullable=True),
        sa.Column("dependency_type", sa.String(length=80), nullable=False),
        sa.Column("dependency_id", sa.String(length=200), nullable=False),
        sa.Column("dependency_version_or_hash", sa.String(length=200), nullable=False),
        sa.Column("required_persona", sa.String(length=80), nullable=False),
        sa.Column("required_capability", sa.String(length=160), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("precondition_version", sa.String(length=200), nullable=False),
        sa.Column("actionable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("stale_reason", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workflow_task_id"], ["workflow_tasks.id"]),
        sa.ForeignKeyConstraint(["proposal_id"], ["opportunities.id"]),
        sa.ForeignKeyConstraint(["candidate_assertion_id"], ["candidate_assertions.id"]),
        sa.ForeignKeyConstraint(["work_product_id"], ["ai_work_products.id"]),
        sa.ForeignKeyConstraint(["context_snapshot_id"], ["context_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_task_id", name="uq_proposal_intelligence_review_task"),
        sa.UniqueConstraint("idempotency_key", name="uq_proposal_intelligence_review_idempotency"),
    )
    op.create_index("ix_proposal_intelligence_review_bindings_workflow_task_id", "proposal_intelligence_review_bindings", ["workflow_task_id"])
    op.create_index("ix_proposal_intelligence_review_bindings_proposal_id", "proposal_intelligence_review_bindings", ["proposal_id"])
    op.create_index("ix_proposal_intelligence_review_proposal", "proposal_intelligence_review_bindings", ["proposal_id", "actionable"])
    op.create_index("ix_proposal_intelligence_review_bindings_candidate_assertion_id", "proposal_intelligence_review_bindings", ["candidate_assertion_id"])
    op.create_index("ix_proposal_intelligence_review_bindings_work_product_id", "proposal_intelligence_review_bindings", ["work_product_id"])
    op.create_index("ix_proposal_intelligence_review_bindings_context_snapshot_id", "proposal_intelligence_review_bindings", ["context_snapshot_id"])


def downgrade() -> None:
    op.drop_index("ix_proposal_intelligence_review_bindings_context_snapshot_id", table_name="proposal_intelligence_review_bindings")
    op.drop_index("ix_proposal_intelligence_review_bindings_work_product_id", table_name="proposal_intelligence_review_bindings")
    op.drop_index("ix_proposal_intelligence_review_bindings_candidate_assertion_id", table_name="proposal_intelligence_review_bindings")
    op.drop_index("ix_proposal_intelligence_review_proposal", table_name="proposal_intelligence_review_bindings")
    op.drop_index("ix_proposal_intelligence_review_bindings_proposal_id", table_name="proposal_intelligence_review_bindings")
    op.drop_index("ix_proposal_intelligence_review_bindings_workflow_task_id", table_name="proposal_intelligence_review_bindings")
    op.drop_table("proposal_intelligence_review_bindings")
