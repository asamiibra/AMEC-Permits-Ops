# Domain inventory

- Canonical external finding: `AuthorityCaseFinding`; there is no `AuthorityFinding` table/model.
- Finding links: Preparation/Submission and Permit UX read the canonical finding; Engineering uses `EngineeringAuthorityFindingLink.authority_finding_id`.
- Contract authority: `Contract` plus exact finalized `ContractRevision`; `agreement_type` is typed and persisted on both revisions.
- Billing identity: `BillingPlan`/`BillingPlanRevision` pins Contract, ContractRevision, client, currency, and nullable Project plus `contract_project_context_snapshot`.
- Invoice identity: `Invoice`/`InvoiceRevision` pins the plan revision, exact contract revision, project context, due-date rule, and issue artifact.
- Communication: `InvoiceIssueEvent`, `InvoiceDeliveryEvent`, `InvoiceAcknowledgment`, and `InvoiceApprovalRecord` are separate records.
- Receivable: payment evidence and allocation remain separate from issue, delivery, approval, and financial settlement.
- ExternalAgreement: no repository entity exists; non-AMEC typed contract values are rejected by the billing guard.
