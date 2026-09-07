"""AI-D2 operational execution ledger.

Revision ID: ai_d2_execution_ledger_v1
Revises: step5_content_azure_sql_v2
"""

from alembic import op
import sqlalchemy as sa


revision = "ai_d2_execution_ledger_v1"
down_revision = "step5_content_azure_sql_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ai_execution_ledger",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=200), nullable=False),
        sa.Column("correlation_id", sa.String(length=100), nullable=False),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("auth_mode", sa.String(length=30), nullable=False),
        sa.Column("purpose", sa.String(length=100), nullable=False),
        sa.Column("execution_mode", sa.String(length=30), nullable=False),
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("target_entity_type", sa.String(length=50), nullable=False),
        sa.Column("target_entity_id", sa.String(length=100), nullable=False),
        sa.Column("architecture_version", sa.String(length=80), nullable=False),
        sa.Column("policy_version", sa.String(length=80), nullable=False),
        sa.Column("context_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=80), nullable=False),
        sa.Column("provider_region", sa.String(length=40), nullable=False),
        sa.Column("deployment_name", sa.String(length=120), nullable=False),
        sa.Column("model_name", sa.String(length=80), nullable=False),
        sa.Column("model_version", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("input_token_upper_bound", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("input_rate_usd_per_1m", sa.Numeric(18, 8), nullable=False),
        sa.Column("output_rate_usd_per_1m", sa.Numeric(18, 8), nullable=False),
        sa.Column("pricing_source_reference", sa.String(length=500), nullable=False),
        sa.Column("reserved_cost_usd", sa.Numeric(18, 8), nullable=False),
        sa.Column("estimated_cost_usd", sa.Numeric(18, 8), nullable=True),
        sa.Column("citation_count", sa.Integer(), nullable=False),
        sa.Column("provider_response_id", sa.String(length=200), nullable=True),
        sa.Column("output_fingerprint", sa.String(length=64), nullable=True),
        sa.Column("error_code", sa.String(length=120), nullable=True),
        sa.Column("synthetic_only", sa.Boolean(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_ai_execution_ledger_idempotency"),
    )
    op.create_index("ix_ai_ledger_actor_started", "ai_execution_ledger", ["actor_user_id", "started_at"])
    op.create_index("ix_ai_ledger_project_started", "ai_execution_ledger", ["project_id", "started_at"])
    op.create_index("ix_ai_ledger_status_started", "ai_execution_ledger", ["status", "started_at"])
    op.create_index("ix_ai_ledger_started", "ai_execution_ledger", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_ai_ledger_started", table_name="ai_execution_ledger")
    op.drop_index("ix_ai_ledger_status_started", table_name="ai_execution_ledger")
    op.drop_index("ix_ai_ledger_project_started", table_name="ai_execution_ledger")
    op.drop_index("ix_ai_ledger_actor_started", table_name="ai_execution_ledger")
    op.drop_table("ai_execution_ledger")
