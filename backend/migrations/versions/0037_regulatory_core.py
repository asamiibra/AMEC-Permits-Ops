"""Canonical Regulatory Core shared domain."""

from alembic import op

from backend.app.models import Base


revision = "0037_regulatory_core"
down_revision = "0036_dashboard_forms_governance_wave_a"
branch_labels = None
depends_on = None

TABLES = [
    "jurisdictions", "external_bodies", "external_body_units", "service_types", "service_type_versions",
    "regulatory_lifecycle_phases", "regulatory_journeys", "authority_cases", "authority_case_identifiers",
    "authority_case_work_periods", "external_interaction_profiles", "authority_outcomes", "regulatory_relations",
]


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        Base.metadata.tables[name].create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        Base.metadata.tables[name].drop(bind=bind, checkfirst=True)
