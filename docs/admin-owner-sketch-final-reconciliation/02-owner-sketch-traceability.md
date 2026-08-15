# Owner sketch traceability

| Sketch element | Current implementation | Authority/result |
|---|---|---|
| Administration | `/admin` operational landing | Adapted; Contracts/Invoices primary |
| Contract / New | `/admin/contracts`, accepted-Proposal selector | Exact; backend Contract create command |
| Contract lanes | Contract list `filter` predicate | Exact label, derived backend filter |
| Contract columns/Open | Contract list projection → `/admin/contracts/{id}` | Exact; Open is navigation only |
| Project Code / Start Date | Contract workspace activation panel | Adapted; explicit human activation |
| Invoice / New or Prepare | `/admin/invoices` reuses BillingInvoice | Adapted; milestone-driven preparation |
| Invoice lanes | `/api/billing/invoices` stage projection | Exact label, derived backend result |
| Invoice columns/Open | Billing list projection → canonical Invoice detail | Exact; Open is navigation only |
| Automatic | Billing policy may prepare a draft | Adapted; Accept/Issue/Delivery/Payment remain human/evidence controlled |
| Handover & Closeout | `/handover` existing downstream area | Protected |
| Setup & Controls | `/admin/setup-controls` and existing `/admin/*` pages | Protected/rehomed |
