# Capability Gap Map

No Owner-required capability was lost in promotion.

| Capability | Current Dashboard proof |
|---|---|
| Forms list/search/filter/Open/Modify/History | `CanonicalFormsLibrary` and `admin-forms-real-stack.spec.ts` |
| New Form / New Version / download | canonical Master Content routes and PostgreSQL suite |
| Used In / Current / Needs Review / Inactive / review note | `item_projection`, current Forms table, owner-status tests |
| Reports | `MasterSection type=REPORT` |
| Engineering Works | `MasterSection type=ENGINEERING_WORK` |
| Definitions / revision history | `DefinitionSection` and canonical definitions routes |
| Inputs & Go-Live | single `/dashboard/inputs-go-live` route, governance payload enabled |
| Wave A/B/C governance | advanced filters and detail drawer; shared `/api/dashboard-v2` facade |

`OWNER_REQUIRED_V1_CAPABILITY_LOST_COUNT=0`.
