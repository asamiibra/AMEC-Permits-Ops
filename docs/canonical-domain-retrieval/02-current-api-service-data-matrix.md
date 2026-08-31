# Phase 2 — Current API/service/data matrix

| Capability | Current API surface | Current service | Persistence truth | Result |
|---|---|---|---|---|
| Master list/detail | `/api/master-content` | `item_projection`, `eligible_master_content` | `MasterContentItem`, linked `Document`/`DocumentVersion`, governance tables | Canonical |
| Master create/version/archive | `/api/master-content` commands | `create_master_content`, `create_master_content_version`, `archive_master_content` | Same canonical records and material-change/audit events | Single owner |
| Master bindings | `/api/master-content/{id}/module-bindings` | Binding helpers in `master_content.py` | `MasterContentModuleBinding` | Relationship, no copy |
| Definitions | `/api/definitions` and related master-content routes | Definition commands/projections | `DefinitionEntry`, `DefinitionRevision` | Separate semantic authority |
| Dashboard V2 applicability/automation | `/api/dashboard-v2/...` | `dashboard_v2_routers.py` plus shared services | Configuration and lineage tables reference master/version IDs | Projection/configuration, not duplicate Form truth |
| Administration Forms | `/admin` → `/api/master-content?content_type=FORM` | Same master-content projection | Same `MasterContentItem` IDs and versions | Converged |
| Source intake | service-only synthetic path | `SourceIntakeService` | Intake ledger; approved master promotion calls canonical create command | Controlled boundary |
| Evidence | Week-2 document routes/services | `register_version`, `classify_version`, `extract_version`, `verify_observation` | Document/version/observation/assertion tables | Canonical evidence lineage |

`/api/dashboard-v2/forms/{item_id}/...` exists for automation configuration
around a master item; it does not replace the `/api/master-content` Form
identity API.
