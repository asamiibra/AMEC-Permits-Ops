# Home data contract

| Home section | Existing source | Projection rule |
|---|---|---|
| Business Flow | Static route map | Seven links only; no mutation |
| Attention | `/api/work` plus persona-scoped `/api/issues` | Normalize, preserve kind, dedupe issues already represented by `issue_id`, retain source deep links |
| Finance | `/api/billing/summary`, `/api/billing/invoices` | Show canonical invoice/payment counts; do not invent currency totals |
| Content Library | Four `/api/master-content` content-type lists plus `/api/definitions` | Show canonical counts and `/dashboard` link; no content writes |
| Recent Business Activity | Role-scoped `/api/work.recent_changes` | Bounded existing event projection; no new activity store |

Home uses `Promise.allSettled` and truthful loading/unavailable states. All API calls carry the existing persona role header through the shared API client.
