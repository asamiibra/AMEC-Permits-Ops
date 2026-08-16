# Route compatibility

| Legacy route | Result | Canonical destination |
| --- | --- | --- |
| `/admin/contracts` | Redirect/alias | `/contract-mobilization?view=contracts` |
| `/admin/contracts/:id` | Redirect/alias, ID preserved | `/contract-mobilization/contracts/:id` |
| `/admin/project-activation` | Redirect/alias | `/contract-mobilization?view=activation` |
| `/admin/project-activation/:id` | Redirect/alias, ID preserved | `/contract-mobilization/contracts/:id#activation` |
| `/admin/invoices` | Redirect/alias | `/billing` |
| `/admin/invoices/:id` | Redirect/alias, ID preserved | `/billing/invoices/:id` |
| `/admin/contracts/inputs/go-live` | Compatibility route | `/admin/go-live-readiness` |

Query strings and hashes are preserved where they carry record context. The existing `/api/admin/contracts/*` and `/api/billing/*` API routes are unchanged. No redirect loop is introduced.

OLD_ADMIN_CONTRACT_ROUTE_COMPATIBILITY_PASS=1
OLD_ADMIN_INVOICE_ROUTE_COMPATIBILITY_PASS=1
OLD_ADMIN_PROJECT_ACTIVATION_ROUTE_COMPATIBILITY_PASS=1
DEEP_LINK_COMPATIBILITY_PASS=1
