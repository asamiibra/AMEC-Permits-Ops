# Contract & Mobilization move

The existing `OperationalContracts` register and `ContractWorkbench` are now rendered by `ContractMobilizationPage` at `/contract-mobilization`. This reuses the canonical `/api/admin/contracts` read and mutation APIs; the API name is retained for compatibility and does not represent the user-facing owner.

The business workspace includes the existing operational register, Contract revisions, Proposal origin, client evidence and inputs, commercial terms, payment terms, deliverables, readiness/acceptance, Project Activation, history, and related Finance context. No decorative subpages or duplicate Contract entity were added.

The controlled create action remains available only through the existing accepted-Proposal selector. Contract existence still does not activate a Project. The workbench still uses the existing append-only audit and backend capability checks.

`Contract & Mobilization` is the primary Stage 2 navigation entry. The older `/proposals-contracts` Proposal/Contract register remains reachable as a preserved direct route for Proposal lineage and existing links.
