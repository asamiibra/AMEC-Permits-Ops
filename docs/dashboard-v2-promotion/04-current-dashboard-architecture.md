# Current Dashboard Architecture

```text
AMEC Work
  → /dashboard
  → DashboardPage
  → CanonicalFormsLibrary / MasterSection / DefinitionSection
  → /api/master-content and /api/definitions
  → MasterContentItem / Document / DocumentVersion
```

Advanced form governance remains a shared seam over the same IDs and versions:

```text
Current Dashboard Form detail
  → /api/dashboard-v2/forms/{id}
  → governance projection over canonical MasterContentItem + DocumentVersion
```

There is no `MasterContentItemV2`, `DocumentV2`, `FormV2`, or copied data universe.
