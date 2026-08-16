# Target domain ownership map

| Capability | Old UI owner | New UI owner | Canonical entity/service | Deep link | RBAC preserved |
| --- | --- | --- | --- | --- | --- |
| Contract register | Admin | Contract & Mobilization | Contract / ContractRevision | `/contract-mobilization?view=contracts` | Yes |
| Contract create | Admin | Contract & Mobilization | `create_contract_from_proposal` | `/contract-mobilization?view=contracts` | Yes; accepted Proposal prerequisite remains |
| Contract revision | Admin | Contract & Mobilization | ContractRevision | `/contract-mobilization/contracts/:id` | Yes |
| Commercial terms | Admin | Contract & Mobilization | ContractRevision / ContractPaymentTerm | `/contract-mobilization/contracts/:id#commercial` | Yes |
| Payment terms | Admin | Contract & Mobilization | ContractPaymentTerm | `/contract-mobilization/contracts/:id#payment-terms` | Yes |
| Project Activation | Admin | Contract & Mobilization | ProjectActivation / Project | `/contract-mobilization/contracts/:id#activation` | Yes; explicit acceptance and mutation guard remain |
| Service Scope setup | Mixed downstream context | Contract & Mobilization | ServiceEngagement | Contract context / future service-scope context | Yes |
| Billing Plan | Admin-adjacent billing context | Finance | BillingPlan / BillingPlanRevision | `/billing` | Yes |
| Billing Milestone | Admin-adjacent billing context | Finance | BillingMilestone | `/billing` | Yes |
| Invoice | Admin alias plus Finance | Finance | Invoice / InvoiceRevision | `/billing/invoices/:id` | Yes |
| Receivable | Admin invoice preview plus Finance | Finance | Receivable | `/billing/invoices/:id` | Yes |
| Payment Evidence | Finance APIs | Finance | Payment | `/billing` and canonical API context | Yes |
| Payment Verification | Finance APIs | Finance | Payment verification evidence | `/billing` and canonical API context | Yes |
| Allocation | Finance APIs | Finance | Payment allocation | `/billing` and canonical API context | Yes |
| Financial Settlement | Handover/Finance context | Finance | Financial settlement records | `/billing` / Handover context | Yes |
| Users & Access | Admin | Admin | Admin configuration/RBAC read model | `/admin/people-access` | Yes |
| Notification Rules | Admin | Admin | Admin notification configuration | `/admin/notifications` | Yes |
| Integrations | Admin | Admin | Integration/connectivity read model | `/admin/integration-health` | Yes |
| Storage / Connectivity | Admin | Admin | Connection and storage readiness | `/admin/data-connections` | Yes |
| Inputs & Go-Live | Admin and Contract setup link | Admin | Readiness/input read model | `/admin/go-live-readiness` | Yes |

Admin remains allowed to configure Contract or Invoice numbering/policy. It does not render Contract or Invoice records.
