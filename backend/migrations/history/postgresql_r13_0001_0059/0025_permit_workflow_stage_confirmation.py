"""Persist downstream permit workflow stage and Stage 1 evidence."""

import sqlalchemy as sa
from alembic import op


revision = "0025_permit_workflow_stage_confirmation"
down_revision = "0024_persona_issues_notifications"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns("permit_applications")}
    additions = [
        ("workflow_stage", sa.Column("workflow_stage", sa.String(60), nullable=True)),
        ("project_sources_confirmed_at", sa.Column("project_sources_confirmed_at", sa.DateTime(timezone=True), nullable=True)),
        ("project_sources_confirmed_by", sa.Column("project_sources_confirmed_by", sa.String(120), nullable=True)),
    ]
    for name, column in additions:
        if name not in columns:
            op.add_column("permit_applications", column)


def downgrade():
    inspector = sa.inspect(op.get_bind())
    columns = {item["name"] for item in inspector.get_columns("permit_applications")}
    for name in ("project_sources_confirmed_by", "project_sources_confirmed_at", "workflow_stage"):
        if name in columns:
            op.drop_column("permit_applications", name)
