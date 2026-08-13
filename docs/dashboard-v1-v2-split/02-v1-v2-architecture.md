# V1 / V2 Architecture

The split is a presentation and route split over one canonical master-content foundation.

```text
MasterContentItem / Document / DocumentVersion / bindings / audit / security
                 │
                 ├── /dashboard       → stable legacy V1 presentation
                 └── /dashboard-v2    → Wave A governance presentation
```

V1 and V2 both use `/api/master-content` and the same canonical IDs, version lineage, purpose bindings, and security policy. V2 opts into governance filtering and renders Wave A profile, provenance, currentness, sensitivity, restricted-reference, quality, source-section, readiness, and Inputs & Go-Live context. V1 omits those controls and sections.

No `MasterContentItemV1`, `MasterContentItemV2`, Dashboard-version column, duplicate CRUD service, copy migration, or second readiness/currentness truth was added. Migration `0036_dashboard_forms_governance_wave_a` is preserved.

V1 is the stable/legacy surface. V2 is the active evolution surface and the future destination for Wave B/C once the shared domain foundations exist. No Wave B/C tables, controls, or fake automation readiness were implemented here.
