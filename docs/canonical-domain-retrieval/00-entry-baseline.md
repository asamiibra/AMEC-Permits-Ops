# Phase 0 — Actual repository baseline

Captured before architecture changes in the isolated implementation worktree.

| Field | Observed |
|---|---|
| Repository | `asamiibra/AMEC-Permits-Ops` |
| Starting branch | `azure-p0-v25-preauthorization-repair-v1` |
| Starting SHA | `0dd403fbf3f3100f283cd1ee1274465ded81998c` |
| Starting tree | `a250658597d47354b196698cfcc905c672e9c21b` |
| Remote parity | `origin/azure-p0-v25-preauthorization-repair-v1`, `0 0` ahead/behind |
| Starting worktree | Dirty only in the original checkout: Excel fixture plus untracked UI evidence/scripts; implementation worktree clean |
| Alembic head | `0058_source_intake_ledger` |
| Migration action | None in this phase or implementation |

## Route-to-canonical-truth evidence

| Frontend route/surface | Component/API client | HTTP route/router | Service/query | Canonical entity |
|---|---|---|---|---|
| `/dashboard` | `frontend/src/Dashboard.tsx` → `api('/api/master-content…')` | `/api/master-content` in `master_content_routers.py` | `item_projection()` and `eligible_master_content()` in `services/master_content.py`; SQL over `MasterContentItem`, `DocumentVersion`, bindings, governance | `MasterContentItem → Document → DocumentVersion` |
| `/dashboard-v2` | `App.tsx` maps this compatibility path to `CurrentDashboard` | Same `/api/master-content` route; dashboard-v2 API is used only for applicability/automation configuration | `dashboard_v2_routers.py` delegates master display to `item_projection()` | Same master identity and version history |
| `/admin` / `/admin/forms` | `AdministrationOwner.tsx` maps Forms to `/api/master-content?content_type=FORM` | Same `/api/master-content` route | Same `item_projection()` and canonical command service | Same `MasterContentItem → Document → DocumentVersion` |
| `/admin/contracts` | `AdministrationOwner.tsx` → `/api/admin/contracts…` | `contract_workspace_routers.py` | `contract_workspace.py` projections and document-version references | `Contract`, `ContractRevision`, linked `DocumentVersion` |
| Documents/source evidence | Legacy `DocumentsPage` and backend week-2 routes | `/api/documents…` in `week2_routers.py` | `register_version()`, `classify_version()`, `extract_version()`, `verify_observation()` | `Document`, immutable `DocumentVersion`, `DocumentClassification`, `FieldObservation`, `VerifiedAssertion` |
| Source intake | Synthetic/test service path | No public browser mutation route found | `SourceIntakeService.ingest_zip()` → `apply_manifest()` → `promote_batch()` | `SourceIntakeBatch/Item`, then canonical `MasterContentItem` only for approved master dispositions |
| Definitions | Dashboard Definitions surface | `/api/definitions…` in `master_content_routers.py` | `definition_projection()` and definition revision commands | `DefinitionEntry → DefinitionRevision` |
| AI/context predecessor | Existing assistant context packets | `/api/assistant-context-packets/{task_id}` | `recovery_routers.py` packet assembly | Task/business context; not a retrieval source of truth |

## Existing canonical model facts

- `MasterContentItem.document_id` is unique and points to `Document`.
- `MasterContentItem.current_document_version_id` and `Document.current_version_id` identify the current version; the implementation treats the linked records as one logical identity, not two stores.
- `DocumentVersion` rows are additive and old rows are marked `SUPERSEDED`; binaries are not overwritten.
- `DefinitionEntry` retains separate `DefinitionRevision` authority.
- Evidence is already represented by `DocumentClassification`, `FieldObservation`, `VerifiedAssertion`, and lineage/evidence models.
- No existing search, vector, or external retrieval service was found. Existing lookups are SQL projections and relationship queries.
