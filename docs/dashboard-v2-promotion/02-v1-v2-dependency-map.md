# V1/V2 Dependency Map

The old split was a presentation split over shared canonical data, not two data stores.

| Surface | Before | After | Classification |
|---|---|---|---|
| `/dashboard` | simplified `DashboardPage` | current governance-capable `DashboardPage` | REPOINT_TO_V2 |
| `/dashboard-v2` | current governance page | compatibility redirect to `/dashboard` | TEMP_COMPATIBILITY |
| `CanonicalFormsLibrary` | simplified or governance mode | one canonical library with Owner status plus governance controls | SHARED_KEEP |
| `DashboardInputsPage` | two URL projections | one `/dashboard/inputs-go-live` projection | REPOINT_TO_V2 |
| `/api/master-content` | canonical list/write/history/download | unchanged canonical contract | SHARED_KEEP |
| `/api/dashboard-v2/*` | governance facade | retained as shared governance seam, no Owner product route | SHARED_KEEP |
| `MasterContentItem`, `Document`, `DocumentVersion` | shared | unchanged | SHARED_KEEP |

`UNCLASSIFIED_V1_RUNTIME_DEPENDENCY_COUNT=0` after the cleanup search recorded in `cleanup-results.json`.
