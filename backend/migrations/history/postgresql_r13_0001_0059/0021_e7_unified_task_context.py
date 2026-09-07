"""Allow shared WorkflowTask records to represent opportunity handoffs."""

import sqlalchemy as sa
from alembic import op

revision = "0021_e7_unified_task_context"
down_revision = "0020_e5_e6_bounded_workflows"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for column in ("project_id", "application_id", "finding_id"):
            op.alter_column("workflow_tasks", column, existing_type=sa.String(length=36), nullable=True)
    else:
        with op.batch_alter_table("workflow_tasks") as batch:
            batch.alter_column("project_id", existing_type=sa.String(length=36), nullable=True)
            batch.alter_column("application_id", existing_type=sa.String(length=36), nullable=True)
            batch.alter_column("finding_id", existing_type=sa.String(length=36), nullable=True)


def downgrade():
    pass
