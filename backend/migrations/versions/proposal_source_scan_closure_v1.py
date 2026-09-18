"""Persist signed complete Synology source scans and directory entries."""

from alembic import op
import sqlalchemy as sa

revision = "proposal_source_scan_closure_v1"
down_revision = "proposal_billing_contract_convergence_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proposal_source_scans",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scan_id", sa.String(160), nullable=False),
        sa.Column("source_identity", sa.String(160), nullable=False),
        sa.Column("source_root", sa.String(700), nullable=False),
        sa.Column("source_project_identity", sa.String(200), nullable=False),
        sa.Column("project_number", sa.String(50), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("bridge_machine_identity", sa.String(200)),
        sa.Column("signed_manifest_hash", sa.String(64)),
        sa.Column("signature_b64", sa.Text()),
        sa.Column("directories_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_bytes_seen", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_successfully_captured", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_skipped_oversize", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("files_unsupported", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("projects_unmapped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("source_identity", "scan_id", name="uq_proposal_source_scan_identity"),
    )
    op.create_index("ix_proposal_source_scans_scan_id", "proposal_source_scans", ["scan_id"])
    op.create_index("ix_proposal_source_scans_source_identity", "proposal_source_scans", ["source_identity"])
    op.create_index("ix_proposal_source_scans_source_project_identity", "proposal_source_scans", ["source_project_identity"])
    op.create_index("ix_proposal_source_scans_project_number", "proposal_source_scans", ["project_number"])
    op.create_index("ix_proposal_source_scans_status", "proposal_source_scans", ["status"])
    op.create_index("ix_proposal_source_scans_signed_manifest_hash", "proposal_source_scans", ["signed_manifest_hash"])
    op.create_table(
        "proposal_source_scan_entries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("scan_id", sa.String(36), sa.ForeignKey("proposal_source_scans.id", ondelete="CASCADE"), nullable=False),
        sa.Column("relative_path", sa.String(700), nullable=False),
        sa.Column("entry_type", sa.String(20), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mtime_token", sa.String(160)),
        sa.Column("sha256", sa.String(64)),
        sa.Column("capture_status", sa.String(40), nullable=False, server_default="PENDING"),
        sa.Column("failure_reason", sa.Text()),
        sa.Column("source_version_token", sa.String(160)),
        sa.Column("metadata_json", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scan_id", "relative_path", name="uq_proposal_source_scan_entry_path"),
    )
    op.create_index("ix_proposal_source_scan_entries_scan_id", "proposal_source_scan_entries", ["scan_id"])
    op.create_index("ix_proposal_source_scan_entries_sha256", "proposal_source_scan_entries", ["sha256"])
    op.create_index("ix_proposal_source_scan_entries_capture_status", "proposal_source_scan_entries", ["capture_status"])


def downgrade() -> None:
    op.drop_table("proposal_source_scan_entries")
    op.drop_table("proposal_source_scans")
