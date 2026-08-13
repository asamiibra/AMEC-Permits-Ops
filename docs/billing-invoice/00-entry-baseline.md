# Billing / Invoice — Entry Baseline

Run date: 2026-08-13. Branch `main`; starting HEAD and `origin/main` were `24e4e9d759eb681ad597c251303346e77cfeb7d8`; entry tree was clean. Alembic head is `0047_prebilling_regulatory_context`; the local SQLite database is stale at `0021_e7_unified_task_context` and is not deployment proof.

The certified pre-billing baseline is present at the starting SHA, including `PRE_BILLING_CROSS_WORKSTREAM_BASELINE_CODE_FROZEN` and `BILLING_INVOICE_CONTRACT_DEPENDENCIES_READY`. Existing repository finance code is a partial E5/E6 synthetic seam: `Invoice`, `InvoiceRevision`, `InvoiceMilestone`, `InvoiceApproval`, `FinanceEvidence`, and `AccountingHandoff` exist, but there are no canonical BillingPlan, BillingPlanRevision, BillingMilestone, line-item calculation, versioned financial-account, payment-allocation, or receivable-follow-up foundations. This implementation extends the existing Invoice/InvoiceRevision tables and adds only missing canonical finance companions.

No overlapping uncommitted Contract, Project, Billing, Invoice, Financial Account, template, artifact, Payment, or migration changes were present. The source `INV-Form.docx` was not found in the checkout or attachment directory; it is therefore treated as absent external sample evidence, never as a template or financial-data source.
