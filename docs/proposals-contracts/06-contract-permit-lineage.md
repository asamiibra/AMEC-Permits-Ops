# Contract → Permit lineage

Contract→Permit validates Contract, related Proposal, Project, Project Reference, and PermitApplication identity. `PermitApplication.controlling_contract_id` is the direct controlling relationship and `ReferenceNumber.permit_application_id` preserves the shared lifecycle root. Existing Permit Workspace routes and stage safety controls are reused. A cross-project contract or PermitApplication is rejected with a typed 409.
