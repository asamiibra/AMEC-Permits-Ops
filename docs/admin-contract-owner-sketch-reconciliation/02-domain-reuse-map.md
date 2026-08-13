# Domain reuse map

| Owner concept | Canonical model / field | Reuse or extension | New storage? |
|---|---|---|---|
| Contract identity | `Contract.id`, `contract_reference`, `contract_name`, lifecycle fields | Reuse; list projects a safe display projection. | No |
| Proposal origin | `Opportunity`, `ProposalAcceptedRevision`, `QuotationRevision` | Pin exact accepted revision and preserve proposal amount/scope baseline. | No |
| Client company | `ClientAccount`, optional `canonical_party_id` | Reuse; no mutable Contract copy. | No |
| Contact | `ClientContact`, shared Party/ContactPoint seam if available | Reuse and compose; subject-correct identifiers only. | No duplicate |
| Contract revision | `ContractRevision` | Extend snapshot/child references; finalized revisions remain immutable. | Existing table + child tables |
| Template | `ContractTemplateSnapshot`, `MasterContentItem`, `DocumentVersion` | Reuse exact snapshot/version. | No duplicate |
| Client Document / LPO | `DocumentVersion` + Contract evidence role | Extend existing evidence with exact version FK and role. | Existing table extension |
| Amount / currency | `Contract` + `ContractRevision` | Reuse typed-safe string money representation until a wider money migration is approved; validate input and preserve currency. | No duplicate |
| Payment Condition | ContractRevision snapshot + `ContractPaymentTerm` | Raw text always preserved; structured terms human-verified. | New canonical child |
| Duration | `Contract.duration` / revision snapshot | Reuse with explicit semantic label/source. | No duplicate |
| Valuation | No proven canonical source | Optional typed ContractRevision value with unknown/non-authoritative basis. | New field only if approved |
| Detailed Works | ContractRevision snapshot | Contracted scope remains distinct from Proposal SOW and Engineering outputs. | No duplicate source model |
| Documents Needed | `ContractClientInputRequirement` | Contractual client input only; not `RequirementInstance`. | New canonical child |
| Deliverables | `ContractDeliverableCommitment` | Commercial commitments only; not `EngineeringDeliverable` or `ContractMilestone`. | New canonical child |
| Authority | `ContractApproval`, shared `Approval`, execution evidence | Reuse explicit human authority path; do not make stage label legal execution by itself. | No duplicate authority |
| Project activation | `ProjectActivation`, `Project` | Reuse exact idempotent activation and lineage. | No duplicate project |
| Billing context | read-only projection from exact ContractRevision | Contract-owned output for next workstream; no Billing runtime writes. | DTO/read model only |
| Invoice template / financial account | existing master/content or finance audit surfaces | Audit availability only. | Deferred |
