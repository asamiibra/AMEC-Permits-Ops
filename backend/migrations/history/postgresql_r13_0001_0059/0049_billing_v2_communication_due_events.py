"""Separate invoice delivery/acknowledgment and event-based due dates."""

import sqlalchemy as sa
from alembic import op

revision = "0049_billing_v2_communication_due_events"
down_revision = "0048_billing_invoice_full"
branch_labels = None
depends_on = None

def _add_columns(table: str, columns: list[sa.Column]) -> None:
    bind = op.get_bind()
    existing = {item["name"] for item in sa.inspect(bind).get_columns(table)}
    missing = [column for column in columns if column.name not in existing]
    if not missing:
        return
    if bind.dialect.name == "sqlite":
        with op.batch_alter_table(table, recreate="always") as batch:
            for column in missing:
                batch.add_column(column)
    else:
        for column in missing:
            op.add_column(table, column)

def upgrade() -> None:
    # Frozen 0049-era table DDL; current ORM metadata is intentionally not used.

    op.execute(sa.text('CREATE TABLE IF NOT EXISTS invoice_delivery_events (\n\tid VARCHAR(36) NOT NULL, \n\tinvoice_id VARCHAR(36) NOT NULL, \n\tissued_revision_id VARCHAR(36) NOT NULL, \n\tissue_event_id VARCHAR(36) NOT NULL, \n\tchannel VARCHAR(40) NOT NULL, \n\trecipient_snapshot JSON NOT NULL, \n\tdelivered_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tdelivery_reference VARCHAR(200), \n\tevidence_document_version_id VARCHAR(36), \n\trecorded_by VARCHAR(200) NOT NULL, \n\trecorded_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\tnotes TEXT, \n\tidempotency_key VARCHAR(200) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_invoice_delivery_idempotency UNIQUE (idempotency_key), \n\tFOREIGN KEY(invoice_id) REFERENCES invoices (id), \n\tFOREIGN KEY(issued_revision_id) REFERENCES invoice_revisions (id), \n\tFOREIGN KEY(issue_event_id) REFERENCES invoice_issue_events (id), \n\tFOREIGN KEY(evidence_document_version_id) REFERENCES document_versions (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_delivery_events_issued_revision_id ON invoice_delivery_events (issued_revision_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_delivery_invoice_time ON invoice_delivery_events (invoice_id, delivered_at)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_delivery_events_invoice_id ON invoice_delivery_events (invoice_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_delivery_events_issue_event_id ON invoice_delivery_events (issue_event_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_delivery_events_evidence_document_version_id ON invoice_delivery_events (evidence_document_version_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS invoice_acknowledgments (\n\tid VARCHAR(36) NOT NULL, \n\tinvoice_id VARCHAR(36) NOT NULL, \n\tissued_revision_id VARCHAR(36) NOT NULL, \n\tacknowledgment_reference VARCHAR(200), \n\tacknowledged_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tsource_document_version_id VARCHAR(36), \n\trecorded_by VARCHAR(200) NOT NULL, \n\trecorded_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\tnotes TEXT, \n\tidempotency_key VARCHAR(200) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_invoice_acknowledgment_idempotency UNIQUE (idempotency_key), \n\tFOREIGN KEY(invoice_id) REFERENCES invoices (id), \n\tFOREIGN KEY(issued_revision_id) REFERENCES invoice_revisions (id), \n\tFOREIGN KEY(source_document_version_id) REFERENCES document_versions (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_acknowledgments_source_document_version_id ON invoice_acknowledgments (source_document_version_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_acknowledgments_issued_revision_id ON invoice_acknowledgments (issued_revision_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_acknowledgments_invoice_id ON invoice_acknowledgments (invoice_id)'))
    _add_columns("invoice_revisions", [
        sa.Column("due_date_offset_days", sa.Integer(), nullable=True),
        sa.Column("due_date_fixed_date", sa.Date(), nullable=True),
        sa.Column("due_date_status", sa.String(40), nullable=False, server_default="NOT_CONFIGURED"),
        sa.Column("due_date_source_event_type", sa.String(80), nullable=True),
        sa.Column("due_date_source_event_id", sa.String(36), nullable=True),
        sa.Column("due_date_derived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contract_project_context_snapshot", sa.JSON(), nullable=False, server_default="{}"),
    ])
    _add_columns("billing_plan_revisions", [
        sa.Column("contract_project_context_snapshot", sa.JSON(), nullable=False, server_default="{}"),
    ])
    _add_columns("contracts", [
        sa.Column("agreement_type", sa.String(80), nullable=False, server_default="AMEC_PROFESSIONAL_SERVICES"),
    ])
    _add_columns("contract_revisions", [
        sa.Column("agreement_type", sa.String(80), nullable=False, server_default="AMEC_PROFESSIONAL_SERVICES"),
    ])

def downgrade() -> None:
    # Communication and due-date evidence is additive and must not be destructively removed.
    pass
