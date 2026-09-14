"""ProposalOps Intelligence v1 P07 foundation control-plane closure.

Revision ID: p07_intelligence_foundation_closure
Revises: intelligence_v1_shared_contracts
"""

from alembic import op
import sqlalchemy as sa


revision = "p07_intelligence_foundation_closure"
down_revision = "intelligence_v1_shared_contracts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("candidate_assertions", sa.Column("candidate_family_key", sa.String(length=300), nullable=True))
    op.create_index("ix_candidate_assertion_candidate_family_key", "candidate_assertions", ["candidate_family_key"])
    op.create_index(
        "uq_candidate_assertion_current_family",
        "candidate_assertions",
        ["candidate_family_key"],
        unique=True,
        mssql_where=sa.text("candidate_family_key IS NOT NULL AND status = 'CURRENT'"),
        sqlite_where=sa.text("status = 'CURRENT'"),
        postgresql_where=sa.text("status = 'CURRENT'"),
    )
    op.add_column("ai_execution_ledger", sa.Column("reservation_owner_token", sa.String(length=64), nullable=True))
    op.add_column("ai_execution_ledger", sa.Column("reservation_generation", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("ai_execution_ledger", sa.Column("reserved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_execution_ledger", sa.Column("reservation_lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("ai_execution_ledger", sa.Column("reservation_reclaimed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_ai_execution_ledger_reservation_owner_token", "ai_execution_ledger", ["reservation_owner_token"])
    op.create_index("ix_ai_execution_ledger_reserved_at", "ai_execution_ledger", ["reserved_at"])
    op.create_index("ix_ai_execution_ledger_reservation_lease_expires_at", "ai_execution_ledger", ["reservation_lease_expires_at"])

    op.add_column("ai_work_products", sa.Column("lineage_hash", sa.String(length=64), nullable=True))
    op.add_column("ai_work_products", sa.Column("invalidation_count", sa.Integer(), nullable=False, server_default="0"))
    op.create_index("ix_ai_work_products_lineage_hash", "ai_work_products", ["lineage_hash"])
    op.add_column("context_snapshots", sa.Column("policy_id", sa.String(length=160), nullable=True))
    op.add_column("context_snapshots", sa.Column("policy_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_context_snapshots_policy_id", "context_snapshots", ["policy_id"])

    op.create_table(
        "ai_work_product_dependencies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("work_product_id", sa.String(length=36), nullable=False),
        sa.Column("dependency_type", sa.String(length=80), nullable=False),
        sa.Column("dependency_id", sa.String(length=200), nullable=False),
        sa.Column("dependency_version_or_hash", sa.String(length=200), nullable=False),
        sa.Column("dependency_metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["work_product_id"], ["ai_work_products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_product_id", "dependency_type", "dependency_id", "dependency_version_or_hash", name="uq_ai_work_product_dependency_identity"),
    )
    op.create_index("ix_ai_work_product_dependencies_work_product_id", "ai_work_product_dependencies", ["work_product_id"])
    op.create_index("ix_ai_work_product_dependency_lookup", "ai_work_product_dependencies", ["dependency_type", "dependency_id"])

    op.create_table(
        "intelligence_invalidations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("work_product_id", sa.String(length=36), nullable=False),
        sa.Column("prior_state", sa.String(length=20), nullable=False),
        sa.Column("resulting_state", sa.String(length=20), nullable=False),
        sa.Column("dependency_type", sa.String(length=80), nullable=False),
        sa.Column("dependency_id", sa.String(length=200), nullable=False),
        sa.Column("prior_dependency_version_or_hash", sa.String(length=200), nullable=True),
        sa.Column("superseding_dependency_version_or_hash", sa.String(length=200), nullable=True),
        sa.Column("source_event_id", sa.String(length=200), nullable=False),
        sa.Column("reason_code", sa.String(length=120), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(["work_product_id"], ["ai_work_products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_product_id", "source_event_id", name="uq_intelligence_invalidation_event"),
    )
    op.create_index("ix_intelligence_invalidations_work_product_id", "intelligence_invalidations", ["work_product_id"])
    op.create_index("ix_intelligence_invalidation_dependency", "intelligence_invalidations", ["dependency_type", "dependency_id"])

    op.create_table(
        "intelligence_policies",
        sa.Column("id", sa.String(length=160), nullable=False),
        sa.Column("policy_code", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("declared_scope", sa.String(length=120), nullable=False),
        sa.Column("policy_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_code", "version", name="uq_intelligence_policy_identity"),
    )
    op.create_index("ix_intelligence_policies_policy_code", "intelligence_policies", ["policy_code"])

    op.create_table(
        "intelligence_eval_packs",
        sa.Column("id", sa.String(length=160), nullable=False),
        sa.Column("eval_pack_id", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("owning_module", sa.String(length=120), nullable=False),
        sa.Column("critical_case_policy", sa.String(length=120), nullable=False),
        sa.Column("acceptance_threshold_policy", sa.String(length=200), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("eval_pack_id", "version", name="uq_intelligence_eval_pack_identity"),
    )
    op.create_index("ix_intelligence_eval_packs_eval_pack_id", "intelligence_eval_packs", ["eval_pack_id"])

    op.create_table(
        "intelligence_review_decisions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("owning_module", sa.String(length=120), nullable=False),
        sa.Column("review_subject_type", sa.String(length=80), nullable=False),
        sa.Column("review_subject_id", sa.String(length=160), nullable=False),
        sa.Column("candidate_assertion_id", sa.String(length=36), nullable=True),
        sa.Column("work_product_id", sa.String(length=36), nullable=True),
        sa.Column("source_currentness_identity", sa.JSON(), nullable=False),
        sa.Column("context_snapshot_id", sa.String(length=36), nullable=True),
        sa.Column("reviewer_user_id", sa.String(length=36), nullable=False),
        sa.Column("reviewer_persona", sa.String(length=120), nullable=False),
        sa.Column("authorizing_capability", sa.String(length=160), nullable=False),
        sa.Column("decision", sa.String(length=30), nullable=False),
        sa.Column("correction_payload", sa.JSON(), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("precondition_version", sa.String(length=200), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("decision_hash", sa.String(length=64), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["candidate_assertion_id"], ["candidate_assertions.id"]),
        sa.ForeignKeyConstraint(["work_product_id"], ["ai_work_products.id"]),
        sa.ForeignKeyConstraint(["context_snapshot_id"], ["context_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_intelligence_review_decision_idempotency"),
    )

    op.create_table(
        "intelligence_tool_definitions",
        sa.Column("id", sa.String(length=160), nullable=False),
        sa.Column("tool_id", sa.String(length=120), nullable=False),
        sa.Column("version", sa.String(length=80), nullable=False),
        sa.Column("immutable_hash", sa.String(length=64), nullable=False),
        sa.Column("input_schema_json", sa.JSON(), nullable=False),
        sa.Column("output_schema_json", sa.JSON(), nullable=False),
        sa.Column("allowed_modules", sa.JSON(), nullable=False),
        sa.Column("allowed_skills", sa.JSON(), nullable=False),
        sa.Column("required_capability", sa.String(length=160), nullable=True),
        sa.Column("data_classification_ceiling", sa.String(length=50), nullable=False),
        sa.Column("timeout_ms", sa.Integer(), nullable=False),
        sa.Column("budget_units", sa.Integer(), nullable=False),
        sa.Column("read_only", sa.Boolean(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tool_id", "version", name="uq_intelligence_tool_identity"),
    )
    op.create_index("ix_intelligence_tool_definitions_tool_id", "intelligence_tool_definitions", ["tool_id"])

    op.create_table(
        "intelligence_tool_invocations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("tool_id", sa.String(length=120), nullable=False),
        sa.Column("tool_version", sa.String(length=80), nullable=False),
        sa.Column("tool_hash", sa.String(length=64), nullable=False),
        sa.Column("owning_module", sa.String(length=120), nullable=False),
        sa.Column("skill_id", sa.String(length=160), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=False),
        sa.Column("context_snapshot_id", sa.String(length=36), nullable=True),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=40), nullable=False),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("output_hash", sa.String(length=64), nullable=True),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["context_snapshot_id"], ["context_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_intelligence_tool_invocation_idempotency"),
    )
    op.create_index("ix_intelligence_tool_invocations_idempotency_key", "intelligence_tool_invocations", ["idempotency_key"])


def downgrade() -> None:
    op.drop_index("uq_candidate_assertion_current_family", table_name="candidate_assertions")
    op.drop_index("ix_candidate_assertion_candidate_family_key", table_name="candidate_assertions")
    op.drop_column("candidate_assertions", "candidate_family_key")
    op.drop_index("ix_context_snapshots_policy_id", table_name="context_snapshots")
    op.drop_column("context_snapshots", "policy_hash")
    op.drop_column("context_snapshots", "policy_id")
    for table in ("intelligence_tool_invocations", "intelligence_tool_definitions", "intelligence_review_decisions", "intelligence_eval_packs", "intelligence_policies", "intelligence_invalidations", "ai_work_product_dependencies"):
        op.drop_table(table)
    op.drop_index("ix_ai_work_products_lineage_hash", table_name="ai_work_products")
    op.drop_column("ai_work_products", "invalidation_count")
    op.drop_column("ai_work_products", "lineage_hash")
    for index_name in ("ix_ai_execution_ledger_reservation_lease_expires_at", "ix_ai_execution_ledger_reserved_at", "ix_ai_execution_ledger_reservation_owner_token"):
        op.drop_index(index_name, table_name="ai_execution_ledger")
    for column in ("reservation_reclaimed_at", "reservation_lease_expires_at", "reserved_at", "reservation_generation", "reservation_owner_token"):
        op.drop_column("ai_execution_ledger", column)
