"""Dashboard Forms Governance Wave A companion records and deterministic backfill."""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone
from uuid import uuid4

revision = "0036_dashboard_forms_governance_wave_a"
down_revision = "0035_owner_decision_closure"
branch_labels = None
depends_on = None


def _id():
    return str(uuid4())


def upgrade() -> None:
    bind = op.get_bind()
    existing = set(sa.inspect(bind).get_table_names())
    # Databases created by the older bootstrap path can retain Alembic's
    # original VARCHAR(32) version column. This revision is longer, so widen
    # the version ledger before Alembic records the new head. The operation
    # is additive and preserves the existing revision value/history.
    if "alembic_version" in existing:
        version_column = next((column for column in sa.inspect(bind).get_columns("alembic_version") if column["name"] == "version_num"), None)
        if version_column and getattr(version_column["type"], "length", None) and version_column["type"].length < 64:
            if bind.dialect.name == "sqlite":
                with op.batch_alter_table("alembic_version") as batch:
                    batch.alter_column("version_num", existing_type=sa.String(length=version_column["type"].length), type_=sa.String(length=64), existing_nullable=False)
            else:
                op.alter_column("alembic_version", "version_num", existing_type=sa.String(length=version_column["type"].length), type_=sa.String(length=64), existing_nullable=False)
    if "master_content_governance_profiles" not in existing:
        op.create_table(
            "master_content_governance_profiles",
            sa.Column("id", sa.String(36), primary_key=True),
            sa.Column("master_content_item_id", sa.String(36), sa.ForeignKey("master_content_items.id"), nullable=False),
            sa.Column("content_ownership_class", sa.String(40), nullable=False, server_default="NEEDS_REVIEW"),
            sa.Column("artifact_kind", sa.String(60), nullable=False, server_default="UNKNOWN"),
            sa.Column("publisher_name", sa.String(240)), sa.Column("publisher_unit", sa.String(240)), sa.Column("jurisdiction_text", sa.String(240)),
            sa.Column("official_form_no", sa.String(120)), sa.Column("official_issue_no", sa.String(80)), sa.Column("official_issue_date", sa.Date()),
            sa.Column("language_profile", sa.String(30), nullable=False, server_default="OTHER"),
            sa.Column("sensitivity_class", sa.String(40), nullable=False, server_default="NONE"),
            sa.Column("contains_pii", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("contains_signature", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("contains_stamp", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("contains_financial_data", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("contains_project_specific_data", sa.Boolean(), nullable=False, server_default=sa.false()), sa.Column("restricted_reference_sample", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("currentness_status", sa.String(40), nullable=False, server_default="UNVERIFIED"), sa.Column("currentness_verified_by", sa.String(200)),
            sa.Column("currentness_verified_at", sa.DateTime(timezone=True)), sa.Column("currentness_verification_note", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("master_content_item_id", name="uq_master_content_governance_item"),
        )
    if "master_content_source_provenance" not in existing:
        op.create_table("master_content_source_provenance", sa.Column("id", sa.String(36), primary_key=True), sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False), sa.Column("obtained_from", sa.String(240), nullable=False), sa.Column("obtained_by", sa.String(200), nullable=False), sa.Column("obtained_at", sa.DateTime(timezone=True), nullable=False), sa.Column("source_reference", sa.String(500)), sa.Column("ingest_batch", sa.String(160)), sa.Column("provenance_note", sa.Text()), sa.Column("evidence_reference", sa.String(500)))
    if "master_content_quality_flags" not in existing:
        op.create_table("master_content_quality_flags", sa.Column("id", sa.String(36), primary_key=True), sa.Column("master_content_item_id", sa.String(36), sa.ForeignKey("master_content_items.id"), nullable=False), sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id")), sa.Column("code", sa.String(80), nullable=False), sa.Column("severity", sa.String(20), nullable=False, server_default="WARNING"), sa.Column("status", sa.String(30), nullable=False, server_default="OPEN"), sa.Column("description", sa.Text(), nullable=False), sa.Column("evidence_note", sa.Text()), sa.Column("recommended_next_action", sa.Text()), sa.Column("raised_by", sa.String(200), nullable=False), sa.Column("raised_at", sa.DateTime(timezone=True), nullable=False), sa.Column("resolved_by", sa.String(200)), sa.Column("resolved_at", sa.DateTime(timezone=True)), sa.Column("resolution", sa.Text()))
    if "master_content_source_sections" not in existing:
        op.create_table("master_content_source_sections", sa.Column("id", sa.String(36), primary_key=True), sa.Column("master_content_item_id", sa.String(36), sa.ForeignKey("master_content_items.id"), nullable=False), sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False), sa.Column("section_key", sa.String(120), nullable=False), sa.Column("label", sa.String(240), nullable=False), sa.Column("locator_type", sa.String(40), nullable=False, server_default="PAGE_RANGE"), sa.Column("page_start", sa.Integer()), sa.Column("page_end", sa.Integer()), sa.Column("locator_payload", sa.JSON(), nullable=False, server_default=sa.text("'{}'")), sa.Column("description", sa.Text()), sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"), sa.Column("created_by", sa.String(200), nullable=False), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False))
    if "master_content_readiness_assessments" not in existing:
        op.create_table("master_content_readiness_assessments", sa.Column("id", sa.String(36), primary_key=True), sa.Column("master_content_item_id", sa.String(36), sa.ForeignKey("master_content_items.id"), nullable=False), sa.Column("document_version_id", sa.String(36), sa.ForeignKey("document_versions.id"), nullable=False), sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False), sa.Column("evaluator_version", sa.String(30), nullable=False, server_default="WAVE_A_1"), sa.Column("state", sa.String(30), nullable=False), sa.Column("blocking_reasons", sa.JSON(), nullable=False, server_default=sa.text("'[]'")), sa.Column("warnings", sa.JSON(), nullable=False, server_default=sa.text("'[]'")), sa.Column("dimensions", sa.JSON(), nullable=False, server_default=sa.text("'{}'")), sa.Column("evidence", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))
    inspector = sa.inspect(bind)
    indexes = {index["name"] for table in ("master_content_governance_profiles", "master_content_source_provenance", "master_content_quality_flags", "master_content_source_sections", "master_content_readiness_assessments") for index in inspector.get_indexes(table)}
    for name, table, column in (
        ("ix_mcgov_ownership", "master_content_governance_profiles", "content_ownership_class"), ("ix_mcgov_artifact_kind", "master_content_governance_profiles", "artifact_kind"), ("ix_mcgov_currentness", "master_content_governance_profiles", "currentness_status"), ("ix_mcgov_restricted", "master_content_governance_profiles", "restricted_reference_sample"), ("ix_mcgov_official_form", "master_content_governance_profiles", "official_form_no"),
        ("ix_mcprov_version", "master_content_source_provenance", "document_version_id"), ("ix_mcq_item", "master_content_quality_flags", "master_content_item_id"), ("ix_mcq_status", "master_content_quality_flags", "status"), ("ix_mcq_severity", "master_content_quality_flags", "severity"), ("ix_mcsection_item", "master_content_source_sections", "master_content_item_id"), ("ix_mcsection_version", "master_content_source_sections", "document_version_id"), ("ix_mcready_item", "master_content_readiness_assessments", "master_content_item_id"), ("ix_mcready_version", "master_content_readiness_assessments", "document_version_id"),
    ):
        if name not in indexes:
            op.create_index(name, table, [column])

    now = datetime.now(timezone.utc)
    rows = bind.execute(sa.text("SELECT id, created_by FROM master_content_items")).mappings().all()
    for row in rows:
        already = bind.execute(sa.text("SELECT 1 FROM master_content_governance_profiles WHERE master_content_item_id=:id"), {"id": row["id"]}).first()
        if already:
            continue
        # Only the existing canonical purpose bindings prove AMEC ownership;
        # every other record remains visibly ambiguous for Owner review.
        proven = bind.execute(sa.text("SELECT 1 FROM master_content_module_bindings WHERE master_content_id=:id AND active=true AND usage_type IN ('PROPOSAL_TEMPLATE','PROPOSAL_CHECKLIST','CONTRACT_TEMPLATE')"), {"id": row["id"]}).first()
        ownership = "AMEC_OWNED" if proven or str(row["created_by"] or "") == "owner-demo-seed" else "NEEDS_REVIEW"
        bind.execute(sa.text("INSERT INTO master_content_governance_profiles (id, master_content_item_id, content_ownership_class, artifact_kind, language_profile, sensitivity_class, contains_pii, contains_signature, contains_stamp, contains_financial_data, contains_project_specific_data, restricted_reference_sample, currentness_status, created_at, updated_at) VALUES (:id,:item,:ownership,'UNKNOWN','OTHER','NONE',false,false,false,false,false,false,'UNVERIFIED',:now,:now)"), {"id": _id(), "item": row["id"], "ownership": ownership, "now": now})


def downgrade() -> None:
    for table in ("master_content_readiness_assessments", "master_content_source_sections", "master_content_quality_flags", "master_content_source_provenance", "master_content_governance_profiles"):
        op.drop_table(table)
