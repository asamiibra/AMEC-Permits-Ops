# Dashboard V1 / V2 Split — Entry Baseline

Entry was verified before the split implementation on `main`.

| Check | Verified value |
|---|---|
| Starting HEAD | `f694a145dc927426d022e50f7e86348fa9ef879d` |
| `origin/main` | `f694a145dc927426d022e50f7e86348fa9ef879d` |
| Working tree | Clean at entry |
| Alembic head | `0036_dashboard_forms_governance_wave_a` |
| Pre-Wave-A behavioral reference | `0ccb61a2b7ac483a17590c27eca594b16b505bb7` |
| Branch | `main` |

The reference commit was inspected in the disposable worktree `/tmp/proposalops-wave-a-v1-reference`; it was not deployed or merged.

## Surface inventory

- Existing Dashboard route: `/dashboard`, rendered by `frontend/src/Dashboard.tsx`.
- Existing Inputs route: `/dashboard/inputs-go-live`, rendered by `frontend/src/DashboardInputs.tsx`.
- Home: `/work`, rendered by `frontend/src/AMECWork.tsx` through `MyWorkPage`.
- Canonical forms library: `frontend/src/MasterContentForms.tsx`.
- Canonical APIs: `/api/master-content`, `/api/master-content/categories`, `/api/definitions`, and `/api/dashboard-inputs`.
- Wave A governance API: the shared `/api/master-content/*/governance`, `/currentness`, `/quality-flags`, `/source-sections`, `/readiness/evaluate`, resolver, and download routes in `backend/app/api/master_content_routers.py`.
- Wave A models: `backend/app/models/forms_governance_entities.py`, attached to canonical master-content records.
- RBAC: shared `current_user_role`/Owner-role checks; existing Wave A governance writes are Owner-only.
- Audit/material propagation: existing shared master-content services and event paths; no version-specific audit model was added.
- Downstream resolvers: `BD/PROPOSAL_TEMPLATE`, `BD/PROPOSAL_CHECKLIST`, and `ADMIN/CONTRACT_TEMPLATE` through the existing master-content resolver service.

The entry tree contained no V1/V2 split files, no V2 route, and no Dashboard-local copies of canonical master-content models.
