# Billing-readiness domain map

## Contract-owned inputs

- Exact finalized/accepted `ContractRevision`.
- Canonical Client and canonical Project relationship.
- Contract amount and currency, distinct from Proposal amount, valuation, Invoice amount, and paid amount.
- Raw Payment Condition plus optional human-verified `ContractPaymentTerm` rows.
- Contract duration with explicit commercial/service semantics.
- Optional valuation amount/currency/basis marked unknown or non-authoritative until Owner meaning is proven.
- Contracted detailed works, `ContractDeliverableCommitment`, and `ContractClientInputRequirement` rows where explicitly captured.
- Exact `DocumentVersion` evidence for LPO, client legal document, and executed/signed Contract where available.
- Contract authority state and ProjectActivation relationship.

## Read-only downstream seam

`ContractBillingContext` is a DTO assembled from an exact requested ContractRevision. It returns the Contract ref, exact revision id, canonical client/project, amount/currency, raw and structured payment terms, duration, valuation state, scope, deliverables, client inputs, LPO/execution evidence references, authority/activation state, and a safe readiness summary.

Readiness may return `READY_FOR_BILLING_SETUP`, `NEEDS_PAYMENT_TERM_REVIEW`, `NEEDS_PROJECT_ACTIVATION`, `NEEDS_CONTRACT_AUTHORITY`, or `NOT_READY`. It never creates BillingMilestone, Invoice, InvoiceRevision, Payment, or Settlement rows.

## Audit-only dependencies

Invoice template availability and financial account master availability are reported as audit metadata only. Bank data is never seeded or copied from invoice examples. Billing remains the next workstream.

## Hard boundaries

- Contract Accept does not create an Invoice.
- Project Activation does not create an Invoice.
- Permit approval does not create an Invoice.
- LPO receipt, Permit approval, and Engineering deliverable acceptance are future trigger data only; no executable cross-module triggers are wired here.
