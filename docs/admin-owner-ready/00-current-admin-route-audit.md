# Current Administration route audit

Audit basis: `frontend/src/App.tsx` legacy route inventory, `frontend/src/WorkflowFirst.tsx`, and the owner Administration projection introduced for this realignment.

| Existing item | Existing route | Owner disposition | Destination / reason |
|---|---|---|---|
| Expansion foundation | `/admin/expansion-foundation` | INTERNAL_IMPLEMENTATION | Rehomed from owner navigation |
| Legacy control room | `/admin/dashboard` | OBSOLETE | No longer a normal Administration peer |
| Project register | `/admin/projects` | OWNER_READ_ONLY | Project & Folder Setup / operational work |
| Documents / source evidence | `/admin/documents` | OWNER_READ_ONLY | Project evidence and workflow context |
| Conflicts | `/admin/conflicts` | OWNER_READ_ONLY | Operational Issues / permit context |
| Configuration | `/admin/config` | INTERNAL_IMPLEMENTATION | Decomposed into owner projections |
| Package readiness | `/admin/package` | MOVE_TO_GO_LIVE | Inputs & Go-Live / permit workspace |
| Municipality preparation | `/admin/municipality` | MOVE_TO_GO_LIVE | Permit workflow workspace |
| Findings & work | `/admin/findings` | OWNER_READ_ONLY | Issues and permit workflow |
| Lineage & validity | `/admin/lineage` | MOVE_TO_AUDIT | Audit History / technical detail |
| Attachments & grids | `/admin/attachments-grids` | ADVANCED_DIAGNOSTIC | Advanced Diagnostics |
| Test extraction | `/admin/spike` | INTERNAL_TESTING | Hidden from owner runtime navigation |
| Expected results | `/admin/adjudication` | INTERNAL_TESTING | Hidden from owner runtime navigation |
| Test analysis | `/admin/analysis` | INTERNAL_TESTING | Hidden from owner runtime navigation |
| Test targets | `/admin/thresholds` | INTERNAL_TESTING | Hidden from owner runtime navigation |
| Test documents | `/admin/corpus` | INTERNAL_TESTING | Hidden from owner runtime navigation |
| Tier 1 decisions | `/admin/tier1` | INTERNAL_IMPLEMENTATION | Hidden from owner runtime navigation |
| Tier 2 backlog | `/admin/tier2` | INTERNAL_IMPLEMENTATION | Hidden from owner runtime navigation |
| Delivery / data | `/admin/delivery` | MOVE_TO_INTEGRATION_HEALTH | Business-readable health projection |
| Go-live setup decision | `/admin/close` | MOVE_TO_GO_LIVE | Inputs & Go-Live |
| Setup baseline | `/admin/baseline` | OWNER_READ_ONLY | Configuration evidence, not a top-level peer |
| Commercial draft | `/admin/signoff` | INTERNAL_IMPLEMENTATION | Templates and governed Proposal/Contract flow |
| Submission confirmation | `/admin/confirmation` | MOVE_TO_GO_LIVE | Human submission boundary |
| Project setup | `/admin/discovery` | OWNER_RUNTIME_ADMIN | Replaced by `/admin/project-folder-setup` |
| Business case | `/admin/business` | INTERNAL_IMPLEMENTATION | Hidden from owner runtime navigation |
| Business baseline | `/admin/business-baseline` | INTERNAL_IMPLEMENTATION | Hidden from owner runtime navigation |
| Privacy & data | `/admin/privacy` | OWNER_READ_ONLY | Data, Security & Retention |
| Volume baseline | `/admin/volume` | INTERNAL_IMPLEMENTATION | Hidden from owner runtime navigation |
| Ministry inquiry | `/admin/inquiries` | MOVE_TO_GO_LIVE | Inputs and external coordination |
| RAID log | `/admin/raid` | INTERNAL_IMPLEMENTATION | Hidden from owner runtime navigation |
| Control diagnostics | `/admin/control-diagnostics` | ADVANCED_DIAGNOSTIC | Advanced Diagnostics; direct route remains controlled |

The old routes remain only as compatibility/deep-link surfaces where the application still needs them. They are not presented as peers in the owner Administration index. The owner index contains exactly the 11 primary business categories plus Advanced Diagnostics, with Inputs & Go-Live kept separate.
