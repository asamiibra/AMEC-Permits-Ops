# Content Library Step 2 — Current Path and Ownership Matrix

The matrix records the pre-change consumer paths inspected for this closure.
`CANONICAL_SHARED` means the path reads the shared canonical read contract;
`CANONICAL_PROJECTION` means it renders a projection over the canonical item,
document, or definition revision; `LEGACY_COMPATIBILITY` means the route is
retained for compatibility but is not an independent content store.

| Surface/path | Consumer | Owner | Classification at entry | Step 2 target |
|---|---|---|---|---|
| `/dashboard` | Owner Dashboard master content and search | `frontend/src/Dashboard.tsx` | CANONICAL_PROJECTION | Governed discovery is read-only and cites canonical results |
| `/dashboard-v2` | Dashboard Forms catalog/detail | `dashboard_v2_routers.py`, `MasterContentForms.tsx` | DUPLICATE_IMPLEMENTATION | Canonical shared read contract |
| Admin Forms / `/api/master-content` | Owner/admin library | `master_content_routers.py` | CANONICAL_PROJECTION | Single shared read owner |
| Forms | Form consumers | MasterContentItem → Document → DocumentVersion | CANONICAL_SHARED | Preserve identity, current version, history |
| Reports | Report consumers | MasterContentItem → Document → DocumentVersion | CANONICAL_SHARED | Same canonical item/version model |
| Engineering Works | Engineering consumers | MasterContentItem → Document → DocumentVersion | CANONICAL_SHARED | Same canonical item/version model |
| Definitions | Definition consumers | DefinitionEntry → DefinitionRevision | CANONICAL_SHARED | Keep separate canonical definition lineage |
| Search/filter | Dashboard and Forms library | canonical read service + governed retrieval | DUPLICATE_IMPLEMENTATION | Compose filters at one read owner |
| Inputs & Go-Live | Owner configuration launcher | `ProductionReadiness.tsx` / dashboard inputs APIs | CANONICAL_PROJECTION | No duplicate library mutation path |
| Detail/history/open/download | Dashboard and Forms library | master-content routes and storage service | CANONICAL_PROJECTION | Same item and immutable version history |
| Source Intake | promotion/read model | `source_intake.py` | CANONICAL_PROJECTION | Promoted source visible as master; transactional source is not |
| Proposal/Contract consumers | resolver services | `proposal_reference.py`, `contract_workspace.py` | CANONICAL_SHARED | Continue canonical resolver path |
| Unrelated permit/project workspaces | transactional records | domain-specific routers/services | LEGACY_COMPATIBILITY | Out of scope; no reclassification or redesign |

No entry in the inspected matrix was classified as a second authorized master
content persistence model. Unknown/dead paths are not promoted by this step;
they remain compatibility or out-of-scope paths until separately governed.
