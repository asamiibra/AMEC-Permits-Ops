"""Versioned Technical Rule Foundation."""

from alembic import op

from backend.app.models import Base


revision = "0039_technical_rule_core"
down_revision = "0038_requirement_engine_v2"
branch_labels = None
depends_on = None

TABLES = ["technical_rule_set_versions", "technical_rules", "technical_rule_lineage", "technical_rule_evaluations"]


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
