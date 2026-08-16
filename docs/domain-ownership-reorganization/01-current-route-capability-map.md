# Current route and capability map

| Capability | Current route | Current page/component | Canonical entity/service | Current UI owner | Target UI owner | Roles observed | Migration action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Contract register | `/admin/contracts`; `/proposals-contracts?view=contracts` | `OperationalContracts`; `ProposalsContractsPage` | `Contract`, `ContractRevision`, contract workspace read model | Admin plus commercial register | Contract & Mobilization | Owner, BD; backend remains authoritative | Use the existing Admin register/workbench components from the Contract & Mobilization route; keep old Admin URL as alias |
| Contract create | `/admin/contracts` | `OperationalContracts` | `create_contract_from_proposal` | Admin presentation | Contract & Mobilization | Existing Owner-controlled action | Preserve accepted Proposal selector and POST API; move only the button surface |
| Contract revision/commercial terms | `/admin/contracts/:id` | `ContractWorkbench` / `CommercialSection` | `ContractRevision`, payment terms | Admin presentation | Contract & Mobilization | Existing mutation guards | Reuse workbench in canonical business route |
| Client inputs/deliverables | `/admin/contracts/:id` | `CommitmentSection`, evidence sections | Contract client-input and deliverable services | Admin presentation | Contract & Mobilization | Existing guards | Reuse same components and endpoints |
| Project Activation | `/admin/contracts/:id#activation` | `ProjectActivationPanel` | `ProjectActivation`, Project | Admin presentation | Contract & Mobilization | Existing Owner guard and acceptance prerequisite | Reuse panel in business workspace; Admin alias redirects |
| Service Scope context | Contract workspace / downstream work | Existing project/service context links | `ServiceEngagement` and project context | Mixed | Contract & Mobilization | Existing role isolation | Add ownership wording/link only where existing canonical context supports it; no new model |
| Billing and invoices | `/billing`; legacy `/admin/invoices` | `BillingInvoicePage` | BillingPlan, BillingMilestone, Invoice, Receivable, payment services | Finance plus Admin alias | Finance | Existing finance API guards | `/billing` is canonical; legacy Admin URL redirects |
| Inputs & Go-Live | `/admin/go-live-readiness`, legacy contract input link | `ReadinessOverviewPage`, `ContractInputs` | Dashboard/readiness inputs | Admin | Admin | Existing Admin access | Route old contract-input alias to Admin readiness |
| Users & Access | `/admin/people-access` | `People` | Admin read model/RBAC | Admin | Admin | Owner/System Admin | Keep |
| Notification rules/defaults | `/admin/notifications` | `Notifications` | Admin configuration | Admin | Admin | Owner/System Admin | Keep; inbox remains `/notifications` |
| Integrations | `/admin/integration-health`, `/admin/data-connections` | `IntegrationHealth`, `Connections` | Admin connection/readiness | Admin | Admin | Owner/System Admin | Keep |
| Storage/connectivity | `/admin/data-connections` | `Connections` | Admin connection/readiness | Admin | Admin | Owner/System Admin | Keep |
| Audit/system activity | `/admin/audit`, `/admin/advanced-diagnostics` | `Audit`, `Advanced` | System audit/diagnostics | Admin | Admin | Owner/System Admin | Keep; business history remains in owning workspace |

The legacy API prefix `/api/admin/contracts` is retained because it is the existing canonical contract workspace API name and is covered by backend tests. It is not exposed as an Admin business page after this change.
