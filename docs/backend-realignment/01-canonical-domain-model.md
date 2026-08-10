# Canonical domain model

ProposalOps presents `Opportunity` as the canonical Proposal and
`QuotationRevision` as the compatibility-backed ProposalRevision snapshot.
`Contract` → `ContractRevision` and the existing `PermitApplication` domain
remain authoritative. `Project` is the only canonical AMEC project identity.

Cardinality is Project 1→N Proposal, Proposal 1→0..N Contract and Contract
1→0..N PermitApplication. The database stores explicit `project_id` on
Opportunity and Contract and `controlling_contract_id` on PermitApplication.
No second permit entity or one-to-one constraint was introduced.
