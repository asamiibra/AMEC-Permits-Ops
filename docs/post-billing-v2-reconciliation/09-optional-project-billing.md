# Optional Project billing

`BillingPlan.project_id`, `BillingPlanRevision.project_id`, `Invoice.project_id`, and the ContractBillingContext project are nullable where policy permits. Billing identity is Contract + exact finalized ContractRevision + Client + Currency, with optional Project. `BILLING_PROJECT_REQUIREMENT_POLICY` defaults conservatively to `REQUIRED` and supports `PRE_ACTIVATION_ALLOWED` through the runtime decision seam. `BILLING_PREACTIVATION_ISSUE_POLICY` defaults to `PROJECT_REQUIRED`; setup permission does not imply issue permission.

No fake Project is created by Billing. The invoice UI uses `Project Code` only when a canonical activated Project row supplies it.
