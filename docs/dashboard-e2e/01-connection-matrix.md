# Connection matrix

The matrix is based on current routes, services, bindings, and tests. A row marked `NO_CURRENT_CONSUMER_SEAM_VERIFIED` is an explicit absence of a dedicated downstream UI, backed by the canonical eligibility/binding/dependency seam; it is not a fabricated module pass.

| Source | Used In | Target | Current seam / evidence | Status |
|---|---|---|---|---|
| FORM | MY_WORK | AMEC Work | Binding and dependency policy; no form-specific task is created by ordinary upload. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| FORM | BD | Business Development | Canonical `/api/master-content/eligible` and module filtering; no dedicated BD form picker exists. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| FORM | ADMIN | Administration | Same canonical library; browser parity and historical downloads pass. | CONNECTED_AND_E2E_VERIFIED |
| FORM | PERMIT | Permit | Canonical eligibility/binding seam; no dedicated Permit form picker exists. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| FORM | PROPOSAL | Proposal | Binding/eligibility seam; no current Proposal master-form consumer route. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| FORM | CONTRACT | Contract | Binding/eligibility seam; no current Contract master-form consumer route. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| REPORT | REPORTS | Reports | `REPORTS` binding, query filter, and dependency/revalidation service. | CONNECTED_AND_E2E_VERIFIED |
| REPORT | ENGINEERING | Engineering | Binding/eligibility seam; no dedicated Engineering report picker. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| REPORT | PERMIT | Permit | Binding/eligibility seam; no dedicated Permit report picker. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| ENGINEERING_WORK | ENGINEERING | Engineering | Dashboard lifecycle, version history, current eligibility, propagation, and revalidation. | CONNECTED_AND_E2E_VERIFIED |
| ENGINEERING_WORK | PERMIT | Permit | Binding/eligibility and lineage seam; no dedicated Permit master-reference UI. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| ENGINEERING_WORK | ISSUES | Issues | Material revision creates one Finding/Issue projection. | CONNECTED_AND_E2E_VERIFIED |
| ENGINEERING_WORK | MY_WORK | AMEC Work | Material revision creates one WorkflowTask in `/api/work`. | CONNECTED_AND_E2E_VERIFIED |
| ENGINEERING_WORK | NOTIFICATIONS | Notifications | Material revision creates role-scoped NotificationEvent. | CONNECTED_AND_E2E_VERIFIED |
| ENGINEERING_WORK | REPORTS | Reports | Binding/lineage seam; no dedicated generated-report UI. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| ENGINEERING_WORK | AI/retrieval | AI seam | `/api/master-content/eligible?use=ENGINEERING_AI` returns current verified content; AI assist remains disabled. | CONNECTED_AND_E2E_VERIFIED |
| DEFINITION | BD | Business Development | Current `/api/definitions/lookup/{term}` and Used In metadata; no dedicated BD lookup UI. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| DEFINITION | ADMIN | Administration | Dashboard structured definition library and revision history. | CONNECTED_AND_E2E_VERIFIED |
| DEFINITION | ENGINEERING | Engineering | Current lookup seam; no dedicated Engineering definition picker. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| DEFINITION | PERMIT | Permit | Current lookup seam; no dedicated Permit definition picker. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| DEFINITION | REPORTS | Reports | Current lookup seam; no dedicated Reports definition picker. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| DEFINITION | PROPOSAL | Proposal | Current lookup seam; no dedicated Proposal definition picker. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| DEFINITION | CONTRACT | Contract | Current lookup seam; no dedicated Contract definition picker. | NO_CURRENT_CONSUMER_SEAM_VERIFIED |
| DEFINITION | AI/context | AI seam | Lookup is current/revision-aware; autonomous AI output is disabled. | CONNECTED_AND_E2E_VERIFIED |

No row is `UNKNOWN`, `ASSUMED`, `PARTIAL`, `UNTESTED`, or `BROKEN`.

Evidence: `artifacts/dashboard-e2e/connection-matrix.json`.
