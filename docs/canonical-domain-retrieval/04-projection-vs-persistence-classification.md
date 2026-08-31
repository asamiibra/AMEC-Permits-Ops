# Phase 2 — Projection versus persistence classification

| Field/representation | Classification | Evidence |
|---|---|---|
| `MasterContentItem.status` | `CANONICAL_PERSISTED_TRUTH` | Stored on master item and changed by canonical commands |
| Owner status / Needs Review label | `DERIVED_PROJECTION` | `item_projection()` derives it from status and review overlay |
| Current version display | `DERIVED_PROJECTION` over `CANONICAL_RELATIONSHIP` | Derived from `current_document_version_id` and linked `DocumentVersion` |
| Used In / module bindings | `CANONICAL_RELATIONSHIP` | `MasterContentModuleBinding` and service synchronization |
| Review note | `CANONICAL_PERSISTED_TRUTH` | Stored on the master item; displayed by multiple surfaces |
| Governance/readiness badges | `DERIVED_PROJECTION` | `governance_projection()` and `evaluate_readiness()` |
| Source provenance/currentness | `CANONICAL_PERSISTED_TRUTH` plus derived readiness | Governance tables linked to exact version |
| Audit events | `AUDIT/TELEMETRY` | `AuditEvent` and material-change events |
| Dashboard V2 applicability/automation | `DERIVED_PROJECTION` / configuration | References canonical master/version IDs; does not copy master bytes |
| Frontend layout/cards | `UI_ONLY` | React components in `Dashboard.tsx` and `AdministrationOwner.tsx` |

`DUPLICATE_CANONICAL_MASTER_TRUTH_COUNT=0`

`DASHBOARD_PROJECTION_NOT_SECOND_TRUTH_PASS=1`
