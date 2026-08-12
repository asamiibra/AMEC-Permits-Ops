"""Canonical Owner decisions, aliases, history, and runtime state."""

import sqlalchemy as sa
from alembic import op


revision = "0035_owner_decision_closure"
down_revision = "0034_admin_contract_owner_session"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    if "owner_decisions" not in existing:
        op.create_table(
        "owner_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("decision_key", sa.String(120), nullable=False),
        sa.Column("group_name", sa.String(80), nullable=False),
        sa.Column("title", sa.String(240), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("why", sa.Text(), nullable=False),
        sa.Column("decision_type", sa.String(60), nullable=False),
        sa.Column("blocking_level", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("proposed_default_json", sa.JSON()),
        sa.Column("effective_value_json", sa.JSON()),
        sa.Column("options_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("affected_modules_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("owner_notes", sa.Text()),
        sa.Column("confirmed_by", sa.String(200)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("effective_from", sa.DateTime(timezone=True)),
        sa.Column("supersedes_decision_id", sa.String(36)),
        sa.Column("system_fact_source", sa.String(300)),
        sa.Column("current_system_state_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("runtime_value_json", sa.JSON()),
        sa.Column("apply_state", sa.String(40), nullable=False, server_default="NOT_APPLIED"),
        sa.Column("runtime_checked_at", sa.DateTime(timezone=True)),
        sa.Column("legacy_keys_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("decision_key", name="uq_owner_decision_key"),
        )
    if "owner_decision_history" not in existing:
        op.create_table(
        "owner_decision_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("decision_id", sa.String(36), sa.ForeignKey("owner_decisions.id"), nullable=False),
        sa.Column("decision_key", sa.String(120), nullable=False),
        sa.Column("event_type", sa.String(60), nullable=False),
        sa.Column("before_json", sa.JSON()),
        sa.Column("after_json", sa.JSON()),
        sa.Column("actor_id", sa.String(200)),
        sa.Column("actor_role", sa.String(80)),
        sa.Column("note", sa.Text()),
        sa.Column("correlation_id", sa.String(100), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "owner_decision_aliases" not in existing:
        op.create_table(
        "owner_decision_aliases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("legacy_key", sa.String(160), nullable=False),
        sa.Column("canonical_key", sa.String(120), nullable=False),
        sa.Column("source_module", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("migrated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("legacy_key", name="uq_owner_decision_legacy_key"),
        )
    for table, name, columns in (
        ("owner_decisions", "ix_owner_decisions_decision_key", ["decision_key"]),
        ("owner_decisions", "ix_owner_decisions_group_name", ["group_name"]),
        ("owner_decisions", "ix_owner_decisions_blocking_level", ["blocking_level"]),
        ("owner_decisions", "ix_owner_decisions_status", ["status"]),
        ("owner_decision_history", "ix_owner_decision_history_decision_id", ["decision_id"]),
        ("owner_decision_history", "ix_owner_decision_history_decision_key", ["decision_key"]),
        ("owner_decision_aliases", "ix_owner_decision_aliases_canonical_key", ["canonical_key"]),
    ):
        if name not in {index["name"] for index in sa.inspect(bind).get_indexes(table)}:
            op.create_index(name, table, columns)


def downgrade() -> None:
    op.drop_table("owner_decision_aliases")
    op.drop_table("owner_decision_history")
    op.drop_table("owner_decisions")
