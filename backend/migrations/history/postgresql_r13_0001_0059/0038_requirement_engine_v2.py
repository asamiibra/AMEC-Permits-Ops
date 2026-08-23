"""Versioned Requirement Engine v2 policy foundation."""

from alembic import op

from backend.app.models import Base


revision = "0038_requirement_engine_v2"
down_revision = "0037_regulatory_core"
branch_labels = None
depends_on = None

TABLES = [
    "requirement_definitions", "requirement_policy_versions", "requirement_groups", "requirement_policy_items",
    "requirement_evidence_constraints", "requirement_policy_lineage", "requirement_applicability_decisions",
    "requirement_evaluations", "requirement_evidence_evaluations", "requirement_decisions",
]


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
