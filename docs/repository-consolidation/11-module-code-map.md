# Module Code Map

| Domain | Backend | Frontend | Tests / migration seam |
|---|---|---|---|
| Dashboard / Master Content | `backend/app/api/master_content_routers.py`, `backend/app/services/master_content.py`, `backend/app/models/master_content_entities.py` | `frontend/src/Dashboard.tsx`, `MasterContentForms.tsx`, `DashboardInputs.tsx` | `test_dashboard_*`, 0027–0041, 0057 |
| Proposal / Contract | `backend/app/api/bd_proposal_routers.py`, `proposals_main_routers.py`, `contract_workspace_routers.py` | `BDProposalOwnerSession.tsx`, `ProposalsContracts.tsx` | `test_bd_*`, `test_admin_contract_*`, 0042/0054/0055 |
| Permit / Engineering | permit/regulatory/project-engineering routers and services | `PermitAuthorityUX.tsx`, `ProjectEngineering.tsx`, `Engineering*` | permit/engineering tests, 0037–0047 |
| Billing / Construction / Completion | billing, construction, completion, handover routers/models | corresponding domain components | domain tests, 0048–0053 |
| Storage / SMB / Source Intake | `backend/app/storage/`, `source_intake.py`, intake entities | consumed through canonical APIs | storage/intake tests, 0056–0058 |
| Shared platform | auth, RBAC, audit, shared-domain routers/services | app shell and navigation in `frontend/src/App.tsx` | full backend/frontend suites |

Dependencies flow through canonical Master Content and Document records; Dashboard and Administration are projections, not duplicate sources of truth.
