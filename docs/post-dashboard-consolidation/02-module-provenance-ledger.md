# Module Provenance Ledger

Current module code is path-owned in the integrated tree; branch names are not module ownership. All requested current modules are reachable from the common branch base and their current integration branches. Canonical storage and data models are shared rather than duplicated.

| Module | Current implementation locations | Migration / tests / evidence |
|---|---|---|
| Dashboard / Master Content / Governance | `frontend/src/Dashboard.tsx`, `MasterContentForms.tsx`; `backend/app/api/master_content_routers.py`, `dashboard_v2_routers.py`, master-content and governance services/models | 0027–0041, 0057; Dashboard and governance suites; `docs/dashboard-v2-final-closure/` |
| BD / Proposal | `backend/app/api/bd_proposal_routers.py`, proposal services; `frontend/src/BDProposalOwnerSession.tsx`, `ProposalsContracts.tsx` | 0042, 0054, 0055; BD/proposal suites |
| Administration / Contract | contract workspace routers/services/models; `frontend/src/AdministrationOwner.tsx`, `ProposalsContracts.tsx` | 0034, 0045; Admin/Contract suites |
| Permit / Regulatory | permit and regulatory routers/services/models/components | 0037, 0047; Permit/regulatory suites |
| Requirements / Technical Rules | shared-domain routers/services and technical-rule models | 0038–0040; shared-domain suites |
| Engineering | project engineering/review routers, models, `frontend/src/ProjectEngineering.tsx` and engineering surfaces | 0043–0046; engineering suites |
| Billing | billing/invoice routers/models and `BillingInvoice.tsx` | 0048–0049; billing suites |
| Construction | construction routers/models/components | 0050–0051; construction suites |
| Completion / Handover | completion/handover routers/models/components | 0052–0053; completion/handover suites |
| Party / Client / Property | canonical party/property/project models and proposal/contract consumers | integrated history; cross-module suites |
| Semantic foundation | shared-domain entities, definitions, rules, RBAC/audit seams | 0018, 0037–0041; shared-domain tests |
| Document / Storage | `backend/app/storage/`, Document/DocumentVersion models and archive services | 0056; storage tests |
| SMB | `backend/app/storage/smb.py`, `dev/storage-lab/` | SMB/storage integration evidence |
| Source Intake | source intake entities/service/router and archive linkage | 0058; Source Intake suites |
| FORME | `backend/scripts/forme_acceptance_v1_4.py` and intake/storage seams | FORME reconciliation tests/evidence; no real Owner import |
| Reports / Definitions | Dashboard projections and canonical APIs/services | Dashboard and shared-domain suites |
| Vercel | `backend/vercel.json`, `frontend/vercel.json`, runtime/bootstrap scripts | deployment and health evidence |
| Shared platform | frontend app shell, auth, RBAC, audit, migrations | full backend/frontend/cross-module regression |

`MasterContentItem`, `Document`, and `DocumentVersion` remain the canonical records. No V2 duplicate data model, migration, import, or deletion is part of this consolidation.

`MODULE_PROVENANCE_LEDGER_COMPLETE=1` and `MODULE_WITH_UNKNOWN_CURRENT_CODE_LOCATION_COUNT=0`.
