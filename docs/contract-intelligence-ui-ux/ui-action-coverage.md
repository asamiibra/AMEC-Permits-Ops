# Contract UI action / API coverage

This ledger covers consequential controls present in the canonical Contract and owning Handover surfaces. Every listed mutation has a real endpoint, capability check, canonical persistence, user feedback, and an applicable test seam. The authoritative 309-row Owner corpus is not present in this checkout; this ledger is not a substitute for that corpus.

| UI control | Component | Capability | Endpoint / verb | Canonical service | Persistence proof | Negative test | Browser proof |
|---|---|---|---|---|---|---|---|
| Edit Contract / save revision | ContractRevisionEditor | CONTRACT_EDIT | `/api/admin/contracts/{id}` PATCH | ContractRevision | reload + revision history | finalized revision / missing reason | existing Contract owner suite |
| Store PO, LPO, or Client Document | ContractSourceIntake | CONTRACT_EDIT | `/api/admin/contracts/{id}/documents/upload` POST | DocumentVersion + ContractAdminEvidence | exact SHA/version readback | invalid role / empty bytes | multipart source test |
| Add structured payment term | CommitmentPanel | CONTRACT_EDIT | `/api/admin/contracts/{id}/commercial-terms` POST | ContractPaymentTerm | current revision readback | finalized revision / invalid source | Contract owner suite |
| Add client input | CommitmentPanel | CONTRACT_EDIT | `/api/admin/contracts/{id}/client-inputs` POST | ContractClientInputRequirement | current revision readback | duplicate sequence / invalid source | Contract owner suite |
| Add deliverable | CommitmentPanel | CONTRACT_EDIT | `/api/admin/contracts/{id}/deliverables` POST | ContractDeliverableCommitment | current revision readback | duplicate sequence / invalid source | Contract owner suite |
| Request extension | ContractExtensionPanel | CONTRACT_EDIT | `/api/admin/contracts/{id}/extension-requests` POST | ContractAdminEvidence | append-only history readback | missing reason / unauthorized role | extension authority browser test |
| Approve, return, or reject extension | ContractExtensionDecisionPanel | CONTRACT_REVIEW_AUTHORITY | `/api/admin/contracts/{id}/extension-decisions` POST | ContractAdminEvidence | reload + original date unchanged | unauthorized role / invalid decision | extension authority browser test |
| Record checker review | Review | CONTRACT_CHECKER | `/api/admin/contracts/{id}/checker` POST | ContractRevision | maker/checker readback | maker equals checker | existing Contract owner suite |
| Approve or return Contract review | Review | CONTRACT_REVIEW_AUTHORITY | `/api/admin/contracts/{id}/authority` POST | ContractRevision | status readback | unauthorized / invalid transition | existing Contract owner suite |
| Accept Contract | Review | CONTRACT_ACCEPT_AUTHORITY | `/api/admin/contracts/{id}/accept` POST | ContractAcceptance | idempotent readback | authority missing | existing Contract owner suite |
| Record executed evidence | ContractExecutionHandoff | CONTRACT_EXECUTION | `/api/admin/contracts/{id}/executed-evidence` POST | ContractAdminEvidence | exact revision/document readback | acceptance/source mismatch | existing Contract owner suite |
| Distribute client copy | ContractExecutionHandoff | CONTRACT_HANDOFF | `/api/admin/contracts/{id}/client-copy-distribution` POST | ContractAdminEvidence | handoff readback | executed evidence missing | existing Contract owner suite |
| Handoff to Operations | ContractExecutionHandoff | CONTRACT_HANDOFF | `/api/admin/contracts/{id}/operations-handoff` POST | ContractAdminEvidence | handoff readback | client distribution missing | existing Contract owner suite |
| Activate Project | Mobilization | PROJECT_ACTIVATE | `/api/admin/contracts/{id}/activate-project` POST | ProjectActivation + Project | project/activation readback | acceptance/readiness missing | existing Contract owner suite |
| Create ServiceEngagement | ServiceScopeSetup | SERVICE_SCOPE_CREATE | `/api/handover/service-engagements` POST | Handover ServiceEngagement | returned owning-domain row | stale revision / inactive project / cross-project | owning Handover suite |
| Open Finance owning workflow | Operations | none (navigation) | `/billing` navigation | Billing | no Contract mutation | read-only boundary | Contract owner suite |

AI/intelligence controls are catalogue/read-only surfaces. No enabled Contract control grants canonical-write or protected-action authority.
