# API client reconciliation

The active Dashboard uses the shared api client with canonical calls:

- /api/master-content
- /api/definitions
- /api/master-content/categories
- /api/dashboard-v2/catalogs
- /api/dashboard-v2/forms
- canonical governance actions/readiness endpoints

There is no active V1-only Dashboard client, no duplicate Dashboard business implementation, and no UI-version business branch. The dashboard-v2 API namespace remains an internal compatibility/governance facade over canonical records; it is not a second business data model.
