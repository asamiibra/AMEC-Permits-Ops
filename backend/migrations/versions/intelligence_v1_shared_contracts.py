"""ProposalOps Intelligence v1 shared contracts and persistence.

Revision ID: intelligence_v1_shared_contracts
Revises: 17c6ebd99c4a
"""

from alembic import op
import sqlalchemy as sa


revision = "intelligence_v1_shared_contracts"
down_revision = "17c6ebd99c4a"
branch_labels = None
depends_on = None


def _batch_nullable(table: str, column: str, existing_type: sa.types.TypeEngine, nullable: bool) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table, recreate="always") as batch:
            batch.alter_column(column, existing_type=existing_type, nullable=nullable)
    else:
        op.alter_column(table, column, existing_type=existing_type, nullable=nullable)


def _ensure_scope_backfill(table: str) -> None:
    bind = op.get_bind()
    bind.execute(sa.text(f"""
        UPDATE {table}
        SET scope_type = 'PROJECT',
            scope_id = project_id
        WHERE project_id IS NOT NULL
          AND (scope_type IS NULL OR scope_id IS NULL)
    """))
    remaining = bind.execute(sa.text(f"""
        SELECT COUNT(*) FROM {table}
        WHERE scope_type IS NULL OR scope_id IS NULL
    """)).scalar_one()
    if remaining:
        raise RuntimeError(f"{table} contains {remaining} rows without a project-backed scope")


def upgrade() -> None:
    # Existing verified assertions are generalized in place.  No values are
    # replaced: legacy project rows receive a PROJECT scope and subject.
    op.add_column("verified_assertions", sa.Column("scope_type", sa.String(length=50), nullable=True))
    op.add_column("verified_assertions", sa.Column("scope_id", sa.String(length=160), nullable=True))
    op.add_column("verified_assertions", sa.Column("subject_type", sa.String(length=50), nullable=True))
    op.add_column("verified_assertions", sa.Column("subject_id", sa.String(length=160), nullable=True))
    op.add_column("verified_assertions", sa.Column("verified_by_capability", sa.String(length=120), nullable=True))
    op.add_column("verified_assertions", sa.Column("verification_origin_module", sa.String(length=120), nullable=True))
    op.add_column("verified_assertions", sa.Column("review_decision_reference", sa.String(length=200), nullable=True))
    _ensure_scope_backfill("verified_assertions")
    bind = op.get_bind()
    bind.execute(sa.text("""
        UPDATE verified_assertions
        SET subject_type = 'PROJECT', subject_id = project_id
        WHERE subject_type IS NULL OR subject_id IS NULL
    """))
    _batch_nullable("verified_assertions", "project_id", sa.String(length=36), True)
    _batch_nullable("verified_assertions", "scope_type", sa.String(length=50), False)
    _batch_nullable("verified_assertions", "scope_id", sa.String(length=160), False)
    _batch_nullable("verified_assertions", "subject_type", sa.String(length=50), False)
    _batch_nullable("verified_assertions", "subject_id", sa.String(length=160), False)
    op.create_index("ix_verified_assertions_scope_type", "verified_assertions", ["scope_type"])
    op.create_index("ix_verified_assertions_scope_id", "verified_assertions", ["scope_id"])

    # Ledger scope is mandatory for all historical project rows.  Module and
    # skill identity stays nullable because it did not exist historically.
    op.add_column("ai_execution_ledger", sa.Column("scope_type", sa.String(length=50), nullable=True))
    op.add_column("ai_execution_ledger", sa.Column("scope_id", sa.String(length=160), nullable=True))
    op.add_column("ai_execution_ledger", sa.Column("owning_module", sa.String(length=120), nullable=True))
    op.add_column("ai_execution_ledger", sa.Column("skill_id", sa.String(length=160), nullable=True))
    op.add_column("ai_execution_ledger", sa.Column("skill_version", sa.String(length=80), nullable=True))
    op.add_column("ai_execution_ledger", sa.Column("skill_manifest_hash", sa.String(length=64), nullable=True))
    _ensure_scope_backfill("ai_execution_ledger")
    _batch_nullable("ai_execution_ledger", "project_id", sa.String(length=36), True)
    _batch_nullable("ai_execution_ledger", "scope_type", sa.String(length=50), False)
    _batch_nullable("ai_execution_ledger", "scope_id", sa.String(length=160), False)
    op.create_index("ix_ai_ledger_scope_type", "ai_execution_ledger", ["scope_type"])
    op.create_index("ix_ai_ledger_scope_id", "ai_execution_ledger", ["scope_id"])
    op.create_index("ix_ai_ledger_scope_started", "ai_execution_ledger", ["scope_type", "scope_id", "started_at"])

    op.create_table(
        "candidate_assertions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("scope_type", sa.String(length=50), nullable=False),
        sa.Column("scope_id", sa.String(length=160), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("target_module", sa.String(length=120), nullable=True),
        sa.Column("subject_type", sa.String(length=50), nullable=False),
        sa.Column("subject_id", sa.String(length=160), nullable=False),
        sa.Column("assertion_code", sa.String(length=160), nullable=False),
        sa.Column("field_definition_id", sa.String(length=36), nullable=True),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("display_value", sa.Text(), nullable=True),
        sa.Column("value_hash", sa.String(length=64), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("producer_kind", sa.String(length=80), nullable=False),
        sa.Column("producer_version", sa.String(length=80), nullable=False),
        sa.Column("producer_hash", sa.String(length=64), nullable=False),
        sa.Column("source_document_version_id", sa.String(length=36), nullable=True),
        sa.Column("source_observation_id", sa.String(length=36), nullable=True),
        sa.Column("evidence_envelope_id", sa.String(length=160), nullable=True),
        sa.Column("data_classification", sa.String(length=50), nullable=False),
        sa.Column("contains_sensitive_data", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("promoted_verified_assertion_id", sa.String(length=36), nullable=True),
        sa.Column("supersedes_candidate_assertion_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.ForeignKeyConstraint(["field_definition_id"], ["field_definitions.id"]),
        sa.ForeignKeyConstraint(["source_document_version_id"], ["document_versions.id"]),
        sa.ForeignKeyConstraint(["source_observation_id"], ["field_observations.id"]),
        sa.ForeignKeyConstraint(["promoted_verified_assertion_id"], ["verified_assertions.id"]),
        sa.ForeignKeyConstraint(["supersedes_candidate_assertion_id"], ["candidate_assertions.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_candidate_assertion_idempotency"),
    )
    op.create_index("ix_candidate_assertion_scope", "candidate_assertions", ["scope_type", "scope_id"])
    op.create_index("ix_candidate_assertion_status", "candidate_assertions", ["status"])
    op.create_index("ix_candidate_assertions_project_id", "candidate_assertions", ["project_id"])

    op.create_table(
        "context_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("owning_module", sa.String(length=120), nullable=False),
        sa.Column("scope_type", sa.String(length=50), nullable=False),
        sa.Column("scope_id", sa.String(length=160), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("actor_persona", sa.String(length=120), nullable=False),
        sa.Column("skill_id", sa.String(length=160), nullable=False),
        sa.Column("skill_version", sa.String(length=80), nullable=False),
        sa.Column("skill_manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("context_schema_version", sa.String(length=80), nullable=False),
        sa.Column("policy_version", sa.String(length=80), nullable=False),
        sa.Column("authorization_context_hash", sa.String(length=64), nullable=False),
        sa.Column("context_hash", sa.String(length=64), nullable=False),
        sa.Column("dependency_count", sa.Integer(), nullable=False),
        sa.Column("synthetic_only", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_context_snapshot_idempotency"),
    )
    op.create_index("ix_context_snapshot_scope", "context_snapshots", ["scope_type", "scope_id"])
    op.create_index("ix_context_snapshots_project_id", "context_snapshots", ["project_id"])

    op.create_table(
        "context_dependencies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("context_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("dependency_type", sa.String(length=80), nullable=False),
        sa.Column("dependency_id", sa.String(length=200), nullable=False),
        sa.Column("dependency_version_or_hash", sa.String(length=200), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("trust_state", sa.String(length=50), nullable=False),
        sa.Column("currentness_state_at_capture", sa.String(length=50), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["context_snapshot_id"], ["context_snapshots.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("context_snapshot_id", "dependency_type", "dependency_id", "dependency_version_or_hash", name="uq_context_dependency_identity"),
    )
    op.create_index("ix_context_dependencies_context_snapshot_id", "context_dependencies", ["context_snapshot_id"])
    op.create_index("ix_context_dependency_type_id", "context_dependencies", ["dependency_type", "dependency_id"])

    op.create_table(
        "ai_work_products",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("execution_ledger_id", sa.String(length=36), nullable=False),
        sa.Column("context_snapshot_id", sa.String(length=36), nullable=False),
        sa.Column("owning_module", sa.String(length=120), nullable=False),
        sa.Column("skill_id", sa.String(length=160), nullable=False),
        sa.Column("skill_version", sa.String(length=80), nullable=False),
        sa.Column("skill_manifest_hash", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.String(length=50), nullable=False),
        sa.Column("scope_id", sa.String(length=160), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=True),
        sa.Column("target_entity_type", sa.String(length=80), nullable=False),
        sa.Column("target_entity_id", sa.String(length=160), nullable=False),
        sa.Column("output_class", sa.String(length=30), nullable=False),
        sa.Column("structured_output_json", sa.JSON(), nullable=False),
        sa.Column("output_hash", sa.String(length=64), nullable=False),
        sa.Column("data_classification", sa.String(length=50), nullable=False),
        sa.Column("contains_sensitive_data", sa.Boolean(), nullable=False),
        sa.Column("state", sa.String(length=20), nullable=False),
        sa.Column("citation_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stale_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stale_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["execution_ledger_id"], ["ai_execution_ledger.id"]),
        sa.ForeignKeyConstraint(["context_snapshot_id"], ["context_snapshots.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_ai_work_product_idempotency"),
    )
    op.create_index("ix_ai_work_product_scope", "ai_work_products", ["scope_type", "scope_id"])
    op.create_index("ix_ai_work_product_state", "ai_work_products", ["state"])
    op.create_index("ix_ai_work_products_project_id", "ai_work_products", ["project_id"])

    op.create_table(
        "intelligence_citations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("work_product_id", sa.String(length=36), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("source_type", sa.String(length=80), nullable=False),
        sa.Column("source_id", sa.String(length=200), nullable=False),
        sa.Column("source_version_or_hash", sa.String(length=200), nullable=False),
        sa.Column("locator_json", sa.JSON(), nullable=False),
        sa.Column("citation_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["work_product_id"], ["ai_work_products.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("work_product_id", "ordinal", name="uq_intelligence_citation_ordinal"),
    )
    op.create_index("ix_intelligence_citations_work_product_id", "intelligence_citations", ["work_product_id"])
    op.create_index("ix_intelligence_citation_source", "intelligence_citations", ["source_type", "source_id"])


def downgrade() -> None:
    bind = op.get_bind()
    for table in ("verified_assertions", "ai_execution_ledger"):
        non_project = bind.execute(sa.text(f"SELECT COUNT(*) FROM {table} WHERE project_id IS NULL")).scalar_one()
        if non_project:
            raise RuntimeError(f"Cannot downgrade {table}: {non_project} generalized rows have no project identity")

    for index_name, table in (
        ("ix_intelligence_citation_source", "intelligence_citations"),
        ("ix_intelligence_citations_work_product_id", "intelligence_citations"),
    ):
        op.drop_index(index_name, table_name=table)
    op.drop_table("intelligence_citations")
    for index_name, table in (
        ("ix_ai_work_products_project_id", "ai_work_products"),
        ("ix_ai_work_product_state", "ai_work_products"),
        ("ix_ai_work_product_scope", "ai_work_products"),
    ):
        op.drop_index(index_name, table_name=table)
    op.drop_table("ai_work_products")
    for index_name, table in (
        ("ix_context_dependency_type_id", "context_dependencies"),
        ("ix_context_dependencies_context_snapshot_id", "context_dependencies"),
    ):
        op.drop_index(index_name, table_name=table)
    op.drop_table("context_dependencies")
    op.drop_index("ix_context_snapshots_project_id", table_name="context_snapshots")
    op.drop_index("ix_context_snapshot_scope", table_name="context_snapshots")
    op.drop_table("context_snapshots")
    for index_name, table in (
        ("ix_candidate_assertions_project_id", "candidate_assertions"),
        ("ix_candidate_assertion_status", "candidate_assertions"),
        ("ix_candidate_assertion_scope", "candidate_assertions"),
    ):
        op.drop_index(index_name, table_name=table)
    op.drop_table("candidate_assertions")

    op.drop_index("ix_ai_ledger_scope_started", table_name="ai_execution_ledger")
    op.drop_index("ix_ai_ledger_scope_id", table_name="ai_execution_ledger")
    op.drop_index("ix_ai_ledger_scope_type", table_name="ai_execution_ledger")
    _batch_nullable("ai_execution_ledger", "scope_id", sa.String(length=160), True)
    _batch_nullable("ai_execution_ledger", "scope_type", sa.String(length=50), True)
    _batch_nullable("ai_execution_ledger", "project_id", sa.String(length=36), False)
    with op.batch_alter_table("ai_execution_ledger") as batch:
        for column in ("skill_manifest_hash", "skill_version", "skill_id", "owning_module", "scope_id", "scope_type"):
            batch.drop_column(column)

    op.drop_index("ix_verified_assertions_scope_id", table_name="verified_assertions")
    op.drop_index("ix_verified_assertions_scope_type", table_name="verified_assertions")
    _batch_nullable("verified_assertions", "subject_id", sa.String(length=160), True)
    _batch_nullable("verified_assertions", "subject_type", sa.String(length=50), True)
    _batch_nullable("verified_assertions", "project_id", sa.String(length=36), False)
    with op.batch_alter_table("verified_assertions") as batch:
        for column in ("review_decision_reference", "verification_origin_module", "verified_by_capability", "subject_id", "subject_type", "scope_id", "scope_type"):
            batch.drop_column(column)
