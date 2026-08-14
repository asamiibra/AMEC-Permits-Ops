"""Billing plans, milestones, invoices, accounts, payments, and receivables."""

import sqlalchemy as sa
from alembic import op

revision = "0048_billing_invoice_full"
down_revision = "0047_prebilling_regulatory_context"
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
    # Frozen 0048-era table DDL; current ORM metadata is intentionally not used.

    op.execute(sa.text('CREATE TABLE IF NOT EXISTS billing_plans (\n\tid VARCHAR(36) NOT NULL, \n\tcontract_id VARCHAR(36) NOT NULL, \n\tcontract_revision_id VARCHAR(36) NOT NULL, \n\tproject_id VARCHAR(36), \n\tclient_account_id VARCHAR(36) NOT NULL, \n\tcurrency VARCHAR(20) NOT NULL, \n\tautomation_mode VARCHAR(40) NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\tcurrent_revision_id VARCHAR(36), \n\tcreated_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tactivated_by VARCHAR(200), \n\tactivated_at TIMESTAMP WITH TIME ZONE, \n\tsuperseded_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_billing_plan_contract_revision UNIQUE (contract_id, contract_revision_id), \n\tFOREIGN KEY(contract_id) REFERENCES contracts (id), \n\tFOREIGN KEY(contract_revision_id) REFERENCES contract_revisions (id), \n\tFOREIGN KEY(project_id) REFERENCES projects (id), \n\tFOREIGN KEY(client_account_id) REFERENCES client_accounts (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_plans_contract_id ON billing_plans (contract_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_plans_status ON billing_plans (status)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_plans_project_id ON billing_plans (project_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_plans_client_account_id ON billing_plans (client_account_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_plans_contract_revision_id ON billing_plans (contract_revision_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_plans_current_revision_id ON billing_plans (current_revision_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS billing_plan_revisions (\n\tid VARCHAR(36) NOT NULL, \n\tbilling_plan_id VARCHAR(36) NOT NULL, \n\trevision_number INTEGER NOT NULL, \n\tcontract_id VARCHAR(36) NOT NULL, \n\tcontract_revision_id VARCHAR(36) NOT NULL, \n\tproject_id VARCHAR(36), \n\tclient_account_id VARCHAR(36) NOT NULL, \n\tcontract_amount NUMERIC(18, 2), \n\tcurrency VARCHAR(20) NOT NULL, \n\tvaluation_amount NUMERIC(18, 2), \n\tvaluation_currency VARCHAR(20), \n\tvaluation_status VARCHAR(50) NOT NULL, \n\tcontract_project_context_snapshot JSON NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\tsupersedes_revision_id VARCHAR(36), \n\tsource_snapshot JSON NOT NULL, \n\tcreated_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tapproved_by VARCHAR(200), \n\tapproved_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_billing_plan_revision_number UNIQUE (billing_plan_id, revision_number), \n\tFOREIGN KEY(billing_plan_id) REFERENCES billing_plans (id), \n\tFOREIGN KEY(contract_id) REFERENCES contracts (id), \n\tFOREIGN KEY(contract_revision_id) REFERENCES contract_revisions (id), \n\tFOREIGN KEY(project_id) REFERENCES projects (id), \n\tFOREIGN KEY(client_account_id) REFERENCES client_accounts (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_plan_revisions_billing_plan_id ON billing_plan_revisions (billing_plan_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_plan_revisions_client_account_id ON billing_plan_revisions (client_account_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_plan_revisions_status ON billing_plan_revisions (status)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_plan_revisions_contract_revision_id ON billing_plan_revisions (contract_revision_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_plan_revisions_project_id ON billing_plan_revisions (project_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_plan_revisions_contract_id ON billing_plan_revisions (contract_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS billing_milestones (\n\tid VARCHAR(36) NOT NULL, \n\tbilling_plan_revision_id VARCHAR(36) NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tname VARCHAR(200) NOT NULL, \n\tdescription TEXT, \n\tsource_contract_payment_term_id VARCHAR(36), \n\tbasis_type VARCHAR(50) NOT NULL, \n\tbasis_amount NUMERIC(18, 2), \n\tpercentage NUMERIC(12, 6), \n\tcalculated_amount NUMERIC(18, 2), \n\tcurrency VARCHAR(20) NOT NULL, \n\ttrigger_type VARCHAR(80) NOT NULL, \n\ttrigger_description TEXT, \n\tdue_days INTEGER, \n\teligibility_state VARCHAR(40) NOT NULL, \n\tinvoiced_amount NUMERIC(18, 2) NOT NULL, \n\tremaining_invoiceable_amount NUMERIC(18, 2), \n\tstatus VARCHAR(40) NOT NULL, \n\tsource_snapshot JSON NOT NULL, \n\tcreated_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_billing_milestone_sequence UNIQUE (billing_plan_revision_id, sequence), \n\tFOREIGN KEY(billing_plan_revision_id) REFERENCES billing_plan_revisions (id), \n\tFOREIGN KEY(source_contract_payment_term_id) REFERENCES contract_payment_terms (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_milestones_source_contract_payment_term_id ON billing_milestones (source_contract_payment_term_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_milestone_eligibility ON billing_milestones (eligibility_state, status)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_milestones_billing_plan_revision_id ON billing_milestones (billing_plan_revision_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS billing_milestone_eligibilities (\n\tid VARCHAR(36) NOT NULL, \n\tbilling_milestone_id VARCHAR(36) NOT NULL, \n\tstate VARCHAR(40) NOT NULL, \n\tevaluated_by VARCHAR(200) NOT NULL, \n\tevaluated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\treason TEXT NOT NULL, \n\ttrigger_evidence JSON NOT NULL, \n\tpolicy_version VARCHAR(80) NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(billing_milestone_id) REFERENCES billing_milestones (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_billing_milestone_eligibilities_billing_milestone_id ON billing_milestone_eligibilities (billing_milestone_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS invoice_line_items (\n\tid VARCHAR(36) NOT NULL, \n\tinvoice_revision_id VARCHAR(36) NOT NULL, \n\tsequence INTEGER NOT NULL, \n\tline_role VARCHAR(30) NOT NULL, \n\titem_code VARCHAR(100), \n\tdescription TEXT NOT NULL, \n\tquantity NUMERIC(18, 6), \n\tunit VARCHAR(40), \n\tunit_price NUMERIC(18, 6), \n\tcurrency VARCHAR(20) NOT NULL, \n\tcalculated_line_amount NUMERIC(18, 2) NOT NULL, \n\tbilling_milestone_id VARCHAR(36), \n\taffects_payable_total BOOLEAN NOT NULL, \n\tsource_reference VARCHAR(300), \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_invoice_line_sequence UNIQUE (invoice_revision_id, sequence), \n\tFOREIGN KEY(invoice_revision_id) REFERENCES invoice_revisions (id), \n\tFOREIGN KEY(billing_milestone_id) REFERENCES billing_milestones (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_line_items_billing_milestone_id ON invoice_line_items (billing_milestone_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_line_items_invoice_revision_id ON invoice_line_items (invoice_revision_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS invoice_references (\n\tid VARCHAR(36) NOT NULL, \n\tinvoice_revision_id VARCHAR(36) NOT NULL, \n\treference_type VARCHAR(80) NOT NULL, \n\tvalue VARCHAR(300) NOT NULL, \n\tissuer_or_source VARCHAR(200), \n\tissued_at TIMESTAMP WITH TIME ZONE, \n\tsource_document_version_id VARCHAR(36), \n\tstatus VARCHAR(40) NOT NULL, \n\tverified_by VARCHAR(200), \n\tverified_at TIMESTAMP WITH TIME ZONE, \n\tnotes TEXT, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(invoice_revision_id) REFERENCES invoice_revisions (id), \n\tFOREIGN KEY(source_document_version_id) REFERENCES document_versions (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_references_source_document_version_id ON invoice_references (source_document_version_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_references_invoice_revision_id ON invoice_references (invoice_revision_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS invoice_approval_records (\n\tid VARCHAR(36) NOT NULL, \n\tinvoice_revision_id VARCHAR(36) NOT NULL, \n\tapproval_type VARCHAR(80) NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\tapproval_reference VARCHAR(200), \n\tapproving_party_or_body VARCHAR(200), \n\tdecision_date DATE, \n\tsource_document_version_id VARCHAR(36), \n\tnotes TEXT, \n\tverified_by VARCHAR(200), \n\tverified_at TIMESTAMP WITH TIME ZONE, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(invoice_revision_id) REFERENCES invoice_revisions (id), \n\tFOREIGN KEY(source_document_version_id) REFERENCES document_versions (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_approval_records_source_document_version_id ON invoice_approval_records (source_document_version_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_approval_records_invoice_revision_id ON invoice_approval_records (invoice_revision_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS invoice_accept_records (\n\tid VARCHAR(36) NOT NULL, \n\tinvoice_revision_id VARCHAR(36) NOT NULL, \n\taccepted_by VARCHAR(200) NOT NULL, \n\taccepted_role VARCHAR(80) NOT NULL, \n\taccepted_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tidempotency_key VARCHAR(200) NOT NULL, \n\tprecheck_snapshot JSON NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_invoice_accept_revision UNIQUE (invoice_revision_id), \n\tCONSTRAINT uq_invoice_accept_idempotency UNIQUE (idempotency_key), \n\tFOREIGN KEY(invoice_revision_id) REFERENCES invoice_revisions (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_accept_records_invoice_revision_id ON invoice_accept_records (invoice_revision_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS invoice_issue_events (\n\tid VARCHAR(36) NOT NULL, \n\tinvoice_id VARCHAR(36) NOT NULL, \n\tinvoice_revision_id VARCHAR(36) NOT NULL, \n\tofficial_invoice_ref VARCHAR(100) NOT NULL, \n\tinvoice_date DATE NOT NULL, \n\tissued_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tissued_by VARCHAR(200) NOT NULL, \n\tidempotency_key VARCHAR(200) NOT NULL, \n\ttemplate_version_id VARCHAR(36) NOT NULL, \n\tfinancial_account_version_id VARCHAR(36) NOT NULL, \n\trendered_artifact_id VARCHAR(36) NOT NULL, \n\tsource_snapshot JSON NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_invoice_issue_invoice UNIQUE (invoice_id), \n\tCONSTRAINT uq_invoice_issue_idempotency UNIQUE (idempotency_key), \n\tCONSTRAINT uq_invoice_issue_reference UNIQUE (official_invoice_ref), \n\tFOREIGN KEY(invoice_id) REFERENCES invoices (id), \n\tFOREIGN KEY(invoice_revision_id) REFERENCES invoice_revisions (id), \n\tFOREIGN KEY(template_version_id) REFERENCES template_versions (id), \n\tFOREIGN KEY(financial_account_version_id) REFERENCES financial_account_versions (id), \n\tFOREIGN KEY(rendered_artifact_id) REFERENCES rendered_artifacts (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_issue_events_invoice_revision_id ON invoice_issue_events (invoice_revision_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_issue_events_invoice_id ON invoice_issue_events (invoice_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS invoice_numbering_policies (\n\tid VARCHAR(36) NOT NULL, \n\tpolicy_key VARCHAR(80) NOT NULL, \n\tprefix VARCHAR(60) NOT NULL, \n\tpadding INTEGER NOT NULL, \n\tnext_number INTEGER NOT NULL, \n\tversion VARCHAR(40) NOT NULL, \n\tstatus VARCHAR(40) NOT NULL, \n\tno_reuse BOOLEAN NOT NULL, \n\tupdated_by VARCHAR(200), \n\tupdated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tUNIQUE (policy_key)\n)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS financial_account_masters (\n\tid VARCHAR(36) NOT NULL, \n\tlegal_entity_party_id VARCHAR(36), \n\tlegal_entity_ref VARCHAR(160) NOT NULL, \n\taccount_name VARCHAR(200) NOT NULL, \n\tstatus VARCHAR(30) NOT NULL, \n\tcreated_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(legal_entity_party_id) REFERENCES parties (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_financial_account_masters_legal_entity_party_id ON financial_account_masters (legal_entity_party_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS financial_account_versions (\n\tid VARCHAR(36) NOT NULL, \n\tfinancial_account_master_id VARCHAR(36) NOT NULL, \n\tversion_number INTEGER NOT NULL, \n\tbank_name VARCHAR(160) NOT NULL, \n\taccount_name VARCHAR(200) NOT NULL, \n\taccount_reference VARCHAR(200) NOT NULL, \n\tcurrency VARCHAR(20) NOT NULL, \n\teffective_from DATE NOT NULL, \n\teffective_to DATE, \n\tstatus VARCHAR(30) NOT NULL, \n\tpayment_instruction_metadata JSON NOT NULL, \n\tcreated_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tapproved_by VARCHAR(200), \n\tapproved_at TIMESTAMP WITH TIME ZONE, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_financial_account_version UNIQUE (financial_account_master_id, version_number), \n\tFOREIGN KEY(financial_account_master_id) REFERENCES financial_account_masters (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_financial_account_versions_currency ON financial_account_versions (currency)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_financial_account_versions_financial_account_master_id ON financial_account_versions (financial_account_master_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS payment_receipts (\n\tid VARCHAR(36) NOT NULL, \n\tclient_account_id VARCHAR(36) NOT NULL, \n\tcontract_id VARCHAR(36) NOT NULL, \n\tproject_id VARCHAR(36), \n\treceived_date DATE NOT NULL, \n\tamount NUMERIC(18, 2) NOT NULL, \n\tcurrency VARCHAR(20) NOT NULL, \n\treference VARCHAR(200) NOT NULL, \n\tpayment_method VARCHAR(80), \n\tevidence_document_version_id VARCHAR(36), \n\tverification_status VARCHAR(40) NOT NULL, \n\trecorded_by VARCHAR(200) NOT NULL, \n\trecorded_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tverified_by VARCHAR(200), \n\tverified_at TIMESTAMP WITH TIME ZONE, \n\tnotes TEXT, \n\tidempotency_key VARCHAR(200) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_payment_receipt_idempotency UNIQUE (idempotency_key), \n\tFOREIGN KEY(client_account_id) REFERENCES client_accounts (id), \n\tFOREIGN KEY(contract_id) REFERENCES contracts (id), \n\tFOREIGN KEY(project_id) REFERENCES projects (id), \n\tFOREIGN KEY(evidence_document_version_id) REFERENCES document_versions (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_payment_receipt_scope ON payment_receipts (contract_id, project_id, verification_status)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_payment_receipts_client_account_id ON payment_receipts (client_account_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_payment_receipts_evidence_document_version_id ON payment_receipts (evidence_document_version_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_payment_receipts_verification_status ON payment_receipts (verification_status)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_payment_receipts_contract_id ON payment_receipts (contract_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_payment_receipts_project_id ON payment_receipts (project_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS invoice_payment_allocations (\n\tid VARCHAR(36) NOT NULL, \n\tpayment_receipt_id VARCHAR(36) NOT NULL, \n\tinvoice_id VARCHAR(36) NOT NULL, \n\tallocated_amount NUMERIC(18, 2) NOT NULL, \n\tcurrency VARCHAR(20) NOT NULL, \n\tallocated_by VARCHAR(200) NOT NULL, \n\tallocated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tstatus VARCHAR(30) NOT NULL, \n\tidempotency_key VARCHAR(200) NOT NULL, \n\tPRIMARY KEY (id), \n\tCONSTRAINT uq_invoice_payment_allocation_idempotency UNIQUE (idempotency_key), \n\tFOREIGN KEY(payment_receipt_id) REFERENCES payment_receipts (id), \n\tFOREIGN KEY(invoice_id) REFERENCES invoices (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_payment_allocations_invoice_id ON invoice_payment_allocations (invoice_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_invoice_payment_allocations_payment_receipt_id ON invoice_payment_allocations (payment_receipt_id)'))
    op.execute(sa.text('CREATE TABLE IF NOT EXISTS receivable_follow_ups (\n\tid VARCHAR(36) NOT NULL, \n\tinvoice_id VARCHAR(36) NOT NULL, \n\tfollow_up_date DATE NOT NULL, \n\tchannel VARCHAR(60) NOT NULL, \n\tcontact_party_id VARCHAR(36), \n\tnote TEXT NOT NULL, \n\toutcome VARCHAR(120), \n\tnext_follow_up_at TIMESTAMP WITH TIME ZONE, \n\trecorded_by VARCHAR(200) NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tPRIMARY KEY (id), \n\tFOREIGN KEY(invoice_id) REFERENCES invoices (id), \n\tFOREIGN KEY(contact_party_id) REFERENCES parties (id)\n)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_receivable_follow_ups_contact_party_id ON receivable_follow_ups (contact_party_id)'))
    op.execute(sa.text('CREATE INDEX IF NOT EXISTS ix_receivable_follow_ups_invoice_id ON receivable_follow_ups (invoice_id)'))
    _add_columns("invoices", [
        sa.Column("project_id", sa.String(36), sa.ForeignKey("projects.id"), nullable=True),
        sa.Column("client_account_id", sa.String(36), sa.ForeignKey("client_accounts.id"), nullable=True),
        sa.Column("billing_plan_id", sa.String(36), sa.ForeignKey("billing_plans.id"), nullable=True),
        sa.Column("invoice_ref_status", sa.String(40), nullable=False, server_default="NOT_ALLOCATED"),
    ])
    _add_columns("invoice_revisions", [
        sa.Column("billing_plan_revision_id", sa.String(36), sa.ForeignKey("billing_plan_revisions.id"), nullable=True),
        sa.Column("invoice_date", sa.Date(), nullable=True),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("due_date_basis", sa.String(100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("currency", sa.String(20), nullable=True),
        sa.Column("gross_charge_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("adjustment_total", sa.Numeric(18, 2), nullable=True, server_default="0"),
        sa.Column("payable_total", sa.Numeric(18, 2), nullable=True),
        sa.Column("amount_in_words", sa.Text(), nullable=True),
        sa.Column("accepted_by", sa.String(200), nullable=True),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
    ])

def downgrade() -> None:
    # Additive finance history is retained; no issued or payment records are destructively removed.
    pass
