"""Persist synthetic TEST master-content bytes across serverless invocations."""

import sqlalchemy as sa
from alembic import op


revision = "0031_durable_synthetic_master_content_bytes"
down_revision = "0030_dashboard_master_content_inputs"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("document_versions")}
    if "synthetic_content" not in columns:
        op.add_column("document_versions", sa.Column("synthetic_content", sa.LargeBinary(), nullable=True))


def downgrade():
    op.drop_column("document_versions", "synthetic_content")
