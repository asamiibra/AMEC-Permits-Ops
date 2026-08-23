"""Canonical ProposalOps lineage and provisional intake SOR."""

import sqlalchemy as sa
from alembic import op

revision = "0022_proposalops_master_realignment"
down_revision = "0021_e7_unified_task_context"
branch_labels = None
depends_on = None


def _add(table: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    if column.name not in {item["name"] for item in inspector.get_columns(table)}:
        if op.get_bind().dialect.name == "sqlite":
            with op.batch_alter_table(table) as batch:
                batch.add_column(column)
        else:
            op.add_column(table, column)


def upgrade():
    # Alembic's default version column is often VARCHAR(32); this revision id
    # is longer.  Widen it before Alembic writes the new revision so existing
    # PostgreSQL deployments can migrate without manual SQL.
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("alembic_version") as batch:
            batch.alter_column("version_num", existing_type=sa.String(length=32), type_=sa.String(length=64), existing_nullable=False)
    else:
        op.alter_column("alembic_version", "version_num", existing_type=sa.String(length=32), type_=sa.String(length=64), existing_nullable=False)
    _add("opportunities", sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", name="fk_opportunities_project_id"), nullable=True))
    _add("opportunities", sa.Column("reference_state", sa.String(30), nullable=False, server_default="PROVISIONAL"))
    _add("opportunities", sa.Column("proposal_fields_json", sa.JSON(), nullable=False, server_default="{}"))
    _add("contracts", sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id", name="fk_contracts_project_id"), nullable=True))
    _add("contracts", sa.Column("end_date", sa.Date(), nullable=True))
    _add("permit_applications", sa.Column("controlling_contract_id", sa.String(36), sa.ForeignKey("contracts.id", name="fk_permit_applications_controlling_contract_id"), nullable=True))
    inspector = sa.inspect(op.get_bind())
    if "proposal_intake_artifacts" not in inspector.get_table_names():
        op.create_table(
            "proposal_intake_artifacts",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
            sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=True),
            sa.Column("opportunity_reference", sa.String(100), nullable=False),
            sa.Column("artifact_type", sa.String(80), nullable=False),
            sa.Column("semantic_class", sa.String(80), nullable=False),
            sa.Column("source_filename", sa.String(300), nullable=False),
            sa.Column("stored_filename", sa.String(300), nullable=False),
            sa.Column("sor_path", sa.String(600), nullable=False),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("content_type", sa.String(120), nullable=False),
            sa.Column("file_size", sa.Integer(), nullable=False),
            sa.Column("uploaded_by", sa.String(200), nullable=False),
            sa.Column("source_revision", sa.String(80), nullable=True),
            sa.Column("idempotency_key", sa.String(200), nullable=False),
            sa.Column("verification_state", sa.String(40), nullable=False, server_default="READ_BACK_VERIFIED"),
            sa.Column("status", sa.String(40), nullable=False, server_default="REGISTERED"),
            sa.Column("evidence_artifact_id", sa.String(36), sa.ForeignKey("evidence_artifacts.id"), nullable=True),
            sa.Column("supersedes_artifact_id", sa.String(36), nullable=True),
            sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
            sa.UniqueConstraint("idempotency_key", name="uq_proposal_intake_idempotency"),
        )


def downgrade():
    op.drop_table("proposal_intake_artifacts")
