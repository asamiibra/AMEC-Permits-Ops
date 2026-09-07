"""Form Automation Runtime shared contracts and lineage."""

from alembic import op

from backend.app.models import Base


revision = "0040_form_automation_runtime"
down_revision = "0039_technical_rule_core"
branch_labels = None
depends_on = None

TABLES = [
    "form_automation_profiles", "semantic_key_definitions", "semantic_value_assertions", "form_mapping_releases",
    "form_mapping_rules", "form_instances", "generated_artifacts", "form_validation_results", "form_qa_runs",
    "form_signature_requirements", "signature_packets",
]


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
