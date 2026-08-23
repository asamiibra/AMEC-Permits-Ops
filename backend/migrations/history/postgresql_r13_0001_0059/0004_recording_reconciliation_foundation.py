"""Recording-derived reconciliation foundation.

Revision ID: 0004_recording_reconciliation_foundation
Revises: 0003_phase0_week3_decision_layer
"""

from alembic import op
import sqlalchemy as sa
from backend.app.models import Base

revision = "0004_recording_reconciliation_foundation"
down_revision = "0003_phase0_week3_decision_layer"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    Base.metadata.create_all(bind=bind)
    # Alembic creates version_num as VARCHAR(32), but this revision's
    # descriptive identifier is longer. PostgreSQL enforces the length;
    # SQLite does not. Widen it before Alembic records this revision.
    if bind.dialect.name == "postgresql":
        op.alter_column(
            "alembic_version",
            "version_num",
            existing_type=sa.String(length=32),
            type_=sa.String(length=128),
            existing_nullable=False,
        )


def downgrade():
    bind = op.get_bind()
    # Drop child edges owned by tables removed at this historical boundary.
    # Explicit cleanup preserves dependency ownership and avoids CASCADE.
    for table_name, constraint_name in (
        ("representations", "representations_authorization_id_fkey"),
        ("excel_projections", "excel_projections_target_rendering_rule_id_fkey"),
    ):
        bind.exec_driver_sql(
            f"ALTER TABLE IF EXISTS {table_name} "
            f"DROP CONSTRAINT IF EXISTS {constraint_name}"
        )
    for table in [
        "target_rendering_rules", "representations", "authorizations", "property_ownerships", "parties", "properties",
        "excel_projection_rules", "excel_project_rows", "synology_project_bootstraps", "project_number_reservations",
        "project_initiations", "synthetic_fixture_sets",
    ]:
        bind.exec_driver_sql(f"DROP TABLE IF EXISTS {table}")
    # Keep the widened PostgreSQL version column. Alembic updates the version
    # row after this downgrade function returns, so narrowing here would try
    # to fit the still-current long revision identifier into VARCHAR(32).
