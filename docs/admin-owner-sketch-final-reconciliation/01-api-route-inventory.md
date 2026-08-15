# API and route inventory

The canonical Contract router is `backend/app/api/contract_workspace_routers.py` under `/api/admin/contracts`; it provides list, exact detail, revision PATCH, stage, authority, readiness, history, evidence, commercial terms, client inputs, billing context, and explicit project activation. The compatibility creation route `/api/admin/contracts/from-proposal/{proposal_id}` delegates to the same command/service.

The canonical Billing router is `backend/app/api/billing_invoice_routers.py` under `/api/billing`; it provides BillingPlan/BillingMilestone setup, `/invoices` list/detail, InvoiceRevision, references, approvals, human accept, issue, delivery, acknowledgment, receivable, follow-up, payment evidence, verification, allocation, and exact artifact download. The list accepts `lane` and server-side `q` search and returns lane counts from the same accessible result set.

Dashboard master content is served under `/api/master-content`, with resolver and version endpoints. Admin configuration remains under `/api/admin/*`. Proposal/Contract cross-module routes remain in `/api/bd/proposals`, `/api/proposals-main`, and `/contracts/{id}` compatibility UI. The UI Administration aliases `/admin/contracts` and `/admin/invoices` reuse these canonical services/components; they do not create duplicate records.
