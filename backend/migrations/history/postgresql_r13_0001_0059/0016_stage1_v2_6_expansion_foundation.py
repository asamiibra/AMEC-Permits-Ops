"""Stage 1 v2.6 E1 shared AMEC domain and synthetic fixture foundation."""

import sqlalchemy as sa
from alembic import op
from backend.app.models import Base

revision = "0016_stage1_v2_6_expansion_foundation"
down_revision = "0015_week14_acceptance"
branch_labels = None
depends_on = None


def upgrade():
    Base.metadata.create_all(bind=op.get_bind())


def downgrade():
    bind = op.get_bind()
    tables = [
        "expansion_fixture_resources", "assistant_capability_definitions", "project_handovers", "accounting_handoffs",
        "invoice_approvals", "invoice_milestones", "invoice_revisions", "invoices",
        "communication_deliveries", "communication_approvals", "communication_drafts",
        "drawing_review_cycles", "engineering_comments", "engineering_review_runs", "engineering_reviews", "regulation_applicabilities", "regulation_versions", "regulation_sources",
        "project_administration_records", "reference_numbers",
        "contract_approvals", "contract_milestones", "contract_revisions", "contracts",
        "quotation_approvals", "commercial_terms", "quotation_revisions", "quotations",
        "document_requests", "checklist_items",
        "tender_documents", "rfqs", "opportunities", "client_contacts", "client_accounts",
        "rendered_artifacts", "template_versions", "template_definitions", "evidence_artifacts",
    ]
    if bind.dialect.name == "postgresql":
        for table in tables:
            op.execute(sa.text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
    else:
        for table in tables:
            op.drop_table(table)
