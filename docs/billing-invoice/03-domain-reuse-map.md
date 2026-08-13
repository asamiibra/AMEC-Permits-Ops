# Domain reuse map

Existing canonical sources reused: `Contract`, exact `ContractRevision`, `ContractPaymentTerm`, `ContractDeliverableCommitment`, `ContractAdminEvidence`, `ClientAccount`, `ProjectActivation`, `DocumentVersion`, `Approval`, `AuditEvent`, `LineageEdge`, `RenderedArtifact`, `TemplateVersion`, `MasterContentItem`, and existing `Invoice`/`InvoiceRevision` tables. No Client, Contract, Project, PaymentTerm, or Permit-local duplicate truth is introduced. New tables are limited to operational Billing/Invoice/Financial Account/Payment/Receivable semantics absent from the repository.
