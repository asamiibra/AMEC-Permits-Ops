# Administration / Contract Owner-Sketch Reconciliation — Entry Baseline

Date: 2026-08-13

## Repository

- Branch: `main`
- Starting SHA: `3f8bf7ebab0ebaff3d7fb4a74cd68fb00982dc3d`
- `origin/main`: `3f8bf7ebab0ebaff3d7fb4a74cd68fb00982dc3d`
- Working tree: clean
- Alembic repository head: `0044_preparation_submission_loop`
- Local developer database observed by Alembic: `0021_e7_unified_task_context`; fresh migration verification remains required.

## Protected entry evidence

- Permit: `PERMIT_AUTHORITY_CASE_UX_CODE_FROZEN`; deployment provenance blocked externally; tested implementation is present at the starting SHA.
- Preparation/Submission: `PREPARATION_SUBMISSION_LOOP_CODE_FROZEN`; deployment provenance blocked externally.
- Engineering: `ENGINEERING_APPROVED_DESIGN_BASELINE_CODE_FROZEN`; `PREPARATION_SUBMISSION_ENGINEERING_DEPENDENCIES_READY`; deployment provenance blocked externally.
- BD / Proposal Forms-Driven v2: `BD_PROPOSAL_FORMS_DRIVEN_V2_CODE_FROZEN`; deployment provenance blocked externally.
- Downstream seam disposition: local code-frozen dependencies are sufficient to reconcile Administration / Contract; no Permit repair is in scope.

## Existing Contract architecture

- Models: `Contract`, `ContractRevision`, `Quotation`, `QuotationRevision`, `ProposalAcceptedRevision`, `ContractMilestone`, `ContractApproval`, `ContractExecutionEvidence`, `ContractAdminInput`, `ContractAdminEvidence`, `ContractTemplateSnapshot`, and `ProjectActivation`.
- API: `/api/admin/contracts` is the Owner Administration surface; Proposal handoff and canonical aliases remain in `proposals_main_routers.py`; legacy recovery contract routes remain protected and are not replaced.
- UI: `/admin/contract-setup` lists Contracts and `/admin/contracts/{id}` renders the existing Contract workbench. `/proposals-contracts?view=contracts` remains the commercial register.
- Authority: current Admin stage commands are human capability-gated and emit audit events; the deeper ContractRevision approval/execution-evidence routes remain canonical for explicit authority evidence.
- Template/evidence: `ContractTemplateSnapshot` pins Dashboard master content and exact `DocumentVersion`; `ContractAdminEvidence` currently has a string source reference and needs an exact DocumentVersion seam for LPO/client evidence.
- Activation: `ProjectActivation` is separate and idempotent; it writes unique Project Code and Start Date onto canonical `Project`, with ContractRevision/ProposalAcceptedRevision lineage.
- Client: commercial `ClientAccount` / `ClientContact` exist and may link to shared `Party`; shared `Party` has typed subject fields but no separate PartyIdentifier/ContactPoint tables.
- Billing audit: Invoice, InvoiceRevision, InvoiceMilestone, InvoiceRequirementDecision, AccountingHandoff, and FinanceEvidence already exist in the repository. They are preserved and not expanded or exposed as a new Invoice UI here. No canonical ContractPaymentTerm, ContractDeliverableCommitment, ContractClientInputRequirement, or ContractBillingContext read model was found.

## Baseline stability

The final verification will run the full backend suite, frontend tests/build, migration round-trip, and real-stack browser checks covering Dashboard V1/V2, BD, Administration/Contract, activation, Engineering, Preparation/Submission, Permit UX, Regulatory, Requirement, Form Automation, and DocumentVersion.

## Closure posture

This reconciliation will preserve the existing lifecycle and add only proven Owner-facing projections and the minimum Contract-scoped billing-readiness seam. It will not implement Invoice, BillingMilestone, payment, settlement, construction, or handover.
