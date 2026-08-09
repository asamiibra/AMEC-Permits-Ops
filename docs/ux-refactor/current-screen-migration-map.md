# Current screen migration map

| Current screen | New location | Route / entry | Retain |
|---|---|---|---|
| Dashboard / Discovery | Administration → Governance & Discovery | `/admin/discovery` | Yes |
| Phase 0 | Administration → Governance & Discovery | `/admin/phase0` | Yes |
| Projects | Permits / permit workspace | `/permits` | Yes, contextualized |
| Documents | Project & Sources / Verify Data | `/permits/:projectId/sources` | Yes |
| Conflicts | Verify Data contextual review | `/permits/:projectId/verify` | Yes |
| Package readiness | Prepare Package | `/permits/:projectId/package` | Yes |
| Municipality preparation | Municipality Preparation | `/permits/:projectId/municipality` | Yes |
| Attachments & grids | Package / Municipality Preparation | Contextual links | Yes |
| Findings & work | Comments & Corrections + Issues | `/issues`, permit stage | Yes |
| Lineage & validity | History / Administration audit | `/permits/:projectId/history` | Yes |
| Spike, adjudication, analysis, corpus | Administration → Validation & Corpus | `/admin/...` | Yes |
| Thresholds, Tier 1/2, delivery, close | Administration → Governance / Acceptance | `/admin/...` | Yes |
| Week 10–14 diagnostics | Administration → Control diagnostics | `/admin/control-diagnostics` | Yes |

Orphaned screens: 0. Legacy in-app entries remain reachable through Administration; old business paths are represented by safe admin/contextual destinations.
