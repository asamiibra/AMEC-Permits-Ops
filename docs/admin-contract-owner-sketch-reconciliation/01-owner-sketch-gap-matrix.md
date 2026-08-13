# Owner-sketch gap matrix

| Sketch concept | Current executable surface | Gap / safe reconciliation | Disposition |
|---|---|---|---|
| Contract list | `/admin/contract-setup`, `/api/admin/contracts` | Existing list is close but must keep default columns simple, hide internal IDs, and derive lanes from Contract state/readiness. | Implemented and verified |
| New / All / Need Action / Authority Review / Ready / Close | Admin filter buttons and configured stage list | Preserve Contract-specific operational filters; `Authority Review` remains Owner/Admin review, not Permit authority. | Reconciled with safe default |
| Contract Ref | `Contract.contract_reference` | Keep canonical reference; never Proposal Ref, Project Code, or DB ID. | Protected |
| Amount | `Contract.amount_value`, `currency`, revision snapshots | Preserve Proposal amount baseline and make Contract amount independently editable only through Contract revision. | Extend read model |
| Close Date | expected/actual/end date fields exist | Meaning is not proven as a single value; display a labeled safe state and preserve existing policy metadata. Do not use as a Billing trigger. | Owner decision pending safe default |
| Client Name / Company / Contact | `ClientAccount`, `ClientContact`, optional shared `Party` link | Build a composed read model; do not create ContractClientCopy or collapse organization/contact. | Implemented and verified |
| CR / ID / PIN | ClientAccount CR; Party and Property typed identifiers | Show only when subject type and provenance are proven; mask sensitive values by default. | Safe default |
| Client Document / LPO | `ContractAdminEvidence` string source reference | Add exact `DocumentVersion` and typed role seam; filename-only promotion is prohibited. | Implemented and verified |
| Project Description / Detailed Works | Proposal accepted snapshot and mutable Contract revision snapshot | Preserve Proposal origin and capture Contract-specific current scope without rewriting Proposal SOW. | Extend canonical revision snapshot |
| Documents Needed | Existing checklist/document-request concepts are not Contract-specific enough | Add Contract-scoped client-input commitment only if absent; keep distinct from regulatory `RequirementInstance`. | Implemented and verified |
| Deliverables | Existing `ContractMilestone` is billing-adjacent and not the right commercial commitment model | Add Contract-scoped commitment model; never merge with EngineeringDeliverable or create BillingMilestone. | Implemented and verified |
| Payment Condition | `ContractMilestone.payment_condition` exists but is not exact-revision Contract term truth | Add ContractRevision-scoped raw + human-verified structured terms. | Implemented and verified |
| Project Duration | `Contract.duration` text | Preserve as commercial/service duration and label its semantics separately from activation, Permit, and construction duration. | Implemented and verified |
| Valuation Amount | No proven canonical valuation model found | Add optional typed value/currency/basis with explicit unknown/non-authoritative state; no Billing use. | Owner decision pending safe default |
| Accept | Existing stage/approval/authority paths | Keep Proposal Accept, Contract authority, and Project Activation distinct. | Protected |
| Project Code / Start Date | canonical `Project` and `ProjectActivation` | Preserve explicit human activation and idempotency. | Protected |
| Billing Setup | no ContractBillingContext projection | Add read-only exact-revision DTO and readiness panel; no invoice/milestone creation. | Implemented and verified |
