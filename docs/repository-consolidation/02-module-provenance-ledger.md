# Module Provenance Ledger

The current implementation is in the integrated tree at `cfc5374` and is reachable from the feature branch. The feature branch is a strict descendant of `origin/main`; therefore the 13 commits below are the only current work not yet in main. Current paths were located by repository history and current-tree inspection, not branch names.

| Module | Current code ownership | Migration / tests / evidence | Origin and reachability |
|---|---|---|---|
| Dashboard / Master Content | `frontend/src/Dashboard.tsx`, `MasterContentForms.tsx`, `dashboard.css`; `backend/app/api/master_content_routers.py`, `services/master_content.py`, `models/master_content_entities.py` | 0027–0031, 0036; Dashboard/master-content tests and `docs/dashboard-v2-promotion/` | main history through 227d91d/cc604f8; reachable from feature, not entry main |
| Dashboard Governance V2 | `backend/app/api/dashboard_v2_routers.py`, `services/dashboard_v2_governance.py`; shared frontend form governance | 0041; `test_dashboard_v2_waves_b_c.py` | main history through 9690e56; reachable from feature |
| BD / Proposal | `bd_proposal_routers.py`, `proposals_main_routers.py`, proposal services/components | 0042, 0054, 0055; BD tests | main history; hardened by cfc5374; reachable from feature |
| Administration / Contract | `contract_workspace_routers.py`, `contract_workspace.py`, admin contract models, `ProposalsContracts.tsx` | 0034, 0045; admin/contract tests | main history; reachable from feature |
| Permit / Regulatory | `permit_ux_routers.py`, `regulatory_context_routers.py`, regulatory services/models | 0037, 0047; permit/regulatory tests | main history; reachable from feature |
| Requirements / Technical Rules | shared-domain routers/services and `technical_rule_core` migration | 0038–0040; shared-domain and Dashboard governance tests | main history; reachable from feature |
| Engineering | project engineering and engineering review routers/models/components | 0043–0046; engineering tests | main history; reachable from feature |
| Billing / Invoicing / Receivables | `billing_invoice_routers.py`, `billing_entities.py`, `BillingInvoice.tsx` | 0048–0049; billing tests | main history; reachable from feature |
| Construction | `construction_routers.py`, construction models/components | 0050–0051; construction tests | main history; reachable from feature |
| Completion / Handover | completion and handover routers/models/components | 0052–0053; completion/handover tests | main history; reachable from feature |
| Party / Client / Property | canonical party/property/project models and Proposal/Contract consumers | earlier integrated history; proposal/contract tests | main history; reachable from feature |
| Verified Semantic Foundation | shared domain entities, definitions, rules, RBAC/audit seams | 0018, 0037–0041; shared-domain tests | main history; reachable from feature |
| Document / Storage | `backend/app/storage/{service,factory,archive,smb,outbox}.py`, document models | 0056; storage tests and `docs/storage-integration/` | 227d91d, a77b11c, 1728bfc; reachable from feature |
| SMB | `backend/app/storage/smb.py`, `dev/storage-lab/` | storage-integration evidence and SMB tests | a77b11c/1728bfc; reachable from feature |
| Source Intake | `source_intake_entities.py`, `source_intake.py`, archive service, intake router usage | 0058; source-intake tests and v1.4 evidence | 1728bfc; reachable from feature |
| FORME reconciliation | `backend/scripts/forme_acceptance_v1_4.py`, intake/storage seams | FORME acceptance artifacts | 2e3cff6, 3ad241a; reachable from feature |
| Reports | Dashboard Reports projection in `Dashboard.tsx`/`MasterContentForms.tsx`; canonical master-content APIs | Dashboard browser/regression evidence | main history; reachable from feature |
| Definitions | Dashboard definitions projection and canonical definition APIs/services | Dashboard and shared-domain tests | main history; reachable from feature |
| Vercel MVP runtime | `backend/vercel.json`, `frontend/vercel.json`, runtime/bootstrap scripts and deployment evidence | Vercel certification artifacts; 0058 head | bacb1f8–e3b488f; reachable from feature |
| Shared auth / RBAC / audit | `backend/app/auth`, `backend/app/audit`, role checks in routers/services | RBAC/audit tests and promotion evidence | integrated main history; reachable from feature |
| Database / migrations | `backend/migrations/versions/0001..0058` | one head `0058_source_intake_ledger` | 0056–0058 are feature-only; reachable from feature |

`MODULE_PROVENANCE_LEDGER_COMPLETE=1`; `MODULE_WITH_UNKNOWN_CURRENT_CODE_LOCATION_COUNT=0` for the requested module set. No `MasterContentItemV2`, `DocumentV2`, or `FormV2` data model was introduced.
