"""Persist Proposal commercial release, distribution, acceptance and handoff controls."""

from alembic import op
import sqlalchemy as sa


revision = "opportunity_commercial_controls_v1"
down_revision = "source18_committee_implementation_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "proposal_technical_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("site_context_id", sa.String(36), sa.ForeignKey("proposal_site_contexts.id")),
        sa.Column("assessment_type", sa.String(60), nullable=False, server_default="SITE_TECHNICAL"),
        sa.Column("status", sa.String(30), nullable=False, server_default="INCOMPLETE"),
        sa.Column("findings", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("assumptions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("evidence_document_version_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("source_lineage", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("assessment_hash", sa.String(64), nullable=False),
        sa.Column("assessed_by", sa.String(200), nullable=False),
        sa.Column("assessed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("supersedes_id", sa.String(36), sa.ForeignKey("proposal_technical_assessments.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_proposal_technical_assessments_proposal_id", "proposal_technical_assessments", ["proposal_id"])
    op.create_index("ix_proposal_technical_assessment_proposal_status", "proposal_technical_assessments", ["proposal_id", "status"])
    op.create_table(
        "proposal_scope_confirmations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("scope_revision_hash", sa.String(64), nullable=False),
        sa.Column("scope_statement", sa.Text(), nullable=False),
        sa.Column("service_offering_codes", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("technical_assessment_ids", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("source_lineage", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("confirmed_by", sa.String(200), nullable=False),
        sa.Column("confirming_capability", sa.String(100), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("audit_correlation_id", sa.String(200), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="CURRENT"),
        sa.Column("supersedes_id", sa.String(36), sa.ForeignKey("proposal_scope_confirmations.id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_proposal_scope_confirmations_proposal_id", "proposal_scope_confirmations", ["proposal_id"])
    op.create_index("ix_proposal_scope_confirmation_proposal_status", "proposal_scope_confirmations", ["proposal_id", "status"])
    op.create_table(
        "proposal_service_eligibility",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("service_offering_code", sa.String(100), nullable=False),
        sa.Column("result", sa.String(60), nullable=False),
        sa.Column("professional_party_id", sa.String(36), sa.ForeignKey("parties.id")),
        sa.Column("capability_reference", sa.String(300)),
        sa.Column("policy_reference", sa.String(300)),
        sa.Column("evidence_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id")),
        sa.Column("decision_note", sa.Text()),
        sa.Column("decided_by", sa.String(200), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="CURRENT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("proposal_id", "service_offering_code", name="uq_proposal_service_eligibility_offering"),
    )
    op.create_index("ix_proposal_service_eligibility_proposal_id", "proposal_service_eligibility", ["proposal_id"])
    op.create_table(
        "proposal_commercial_releases",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("accepted_revision_id", sa.String(36), sa.ForeignKey("proposal_accepted_revisions.id"), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("scope_confirmation_id", sa.String(36), sa.ForeignKey("proposal_scope_confirmations.id"), nullable=False),
        sa.Column("eligibility_snapshot", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(30), nullable=False, server_default="AUTHORIZED"),
        sa.Column("authorized_by", sa.String(200), nullable=False),
        sa.Column("authorizing_capability", sa.String(100), nullable=False),
        sa.Column("authorized_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("audit_correlation_id", sa.String(200), nullable=False),
        sa.UniqueConstraint("accepted_revision_id", name="uq_proposal_commercial_release_revision"),
        sa.UniqueConstraint("idempotency_key", name="uq_proposal_commercial_releases_idempotency_key"),
    )
    op.create_table(
        "proposal_distribution_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("accepted_revision_id", sa.String(36), sa.ForeignKey("proposal_accepted_revisions.id"), nullable=False),
        sa.Column("commercial_release_id", sa.String(36), sa.ForeignKey("proposal_commercial_releases.id"), nullable=False),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("recipient_party_id", sa.String(36), sa.ForeignKey("parties.id")),
        sa.Column("recipient_contact_reference", sa.String(300)),
        sa.Column("evidence_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id")),
        sa.Column("evidence_reference", sa.String(600), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("sent_by", sa.String(200), nullable=False),
        sa.Column("audit_correlation_id", sa.String(200), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.UniqueConstraint("idempotency_key", name="uq_proposal_distribution_idempotency"),
    )
    op.create_table(
        "proposal_acceptance_verifications",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("accepted_revision_id", sa.String(36), sa.ForeignKey("proposal_accepted_revisions.id"), nullable=False),
        sa.Column("client_response_id", sa.String(36), sa.ForeignKey("proposal_client_responses.id"), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="VERIFIED"),
        sa.Column("evidence_reference", sa.String(600), nullable=False),
        sa.Column("evidence_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id")),
        sa.Column("verified_by", sa.String(200), nullable=False),
        sa.Column("verification_note", sa.Text()),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("audit_correlation_id", sa.String(200), nullable=False),
        sa.UniqueConstraint("client_response_id", name="uq_proposal_acceptance_verification_response"),
    )
    op.create_table(
        "proposal_lpo_reconciliations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("accepted_revision_id", sa.String(36), sa.ForeignKey("proposal_accepted_revisions.id"), nullable=False),
        sa.Column("client_document_version_id", sa.String(36), sa.ForeignKey("document_versions.id")),
        sa.Column("client_artifact_reference", sa.String(600)),
        sa.Column("applies", sa.Boolean(), nullable=False),
        sa.Column("fields_compared", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("variances", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("result", sa.String(40), nullable=False),
        sa.Column("adjudication_note", sa.Text()),
        sa.Column("adjudicated_by", sa.String(200)),
        sa.Column("adjudicated_at", sa.DateTime(timezone=True)),
        sa.Column("compared_by", sa.String(200), nullable=False),
        sa.Column("compared_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("audit_correlation_id", sa.String(200), nullable=False),
        sa.UniqueConstraint("proposal_id", "accepted_revision_id", name="uq_proposal_lpo_reconciliation_revision"),
        sa.UniqueConstraint("idempotency_key", name="uq_proposal_lpo_reconciliations_idempotency_key"),
    )
    op.create_table(
        "proposal_contract_handoffs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("opportunities.id"), nullable=False),
        sa.Column("accepted_revision_id", sa.String(36), sa.ForeignKey("proposal_accepted_revisions.id"), nullable=False),
        sa.Column("acceptance_verification_id", sa.String(36), sa.ForeignKey("proposal_acceptance_verifications.id"), nullable=False),
        sa.Column("reconciliation_id", sa.String(36), sa.ForeignKey("proposal_lpo_reconciliations.id")),
        sa.Column("status", sa.String(40), nullable=False, server_default="ELIGIBLE"),
        sa.Column("handoff_payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("handed_off_by", sa.String(200), nullable=False),
        sa.Column("handed_off_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("idempotency_key", sa.String(200), nullable=False),
        sa.Column("audit_correlation_id", sa.String(200), nullable=False),
        sa.UniqueConstraint("proposal_id", "accepted_revision_id", name="uq_proposal_contract_handoff_revision"),
        sa.UniqueConstraint("idempotency_key", name="uq_proposal_contract_handoffs_idempotency_key"),
    )


def downgrade() -> None:
    for table in (
        "proposal_contract_handoffs",
        "proposal_lpo_reconciliations",
        "proposal_acceptance_verifications",
        "proposal_distribution_events",
        "proposal_commercial_releases",
        "proposal_service_eligibility",
        "proposal_scope_confirmations",
    ):
        op.drop_table(table)
