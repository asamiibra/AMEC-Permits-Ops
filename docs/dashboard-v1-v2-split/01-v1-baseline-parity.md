# Dashboard V1 — Baseline Parity

The pre-Wave-A commit `0ccb61a2b7ac483a17590c27eca594b16b505bb7` was inspected in an isolated reference worktree. The current V1 surface restores the baseline presentation while retaining shared security and persistence.

| Parity dimension | Result |
|---|---|
| Route/bookmark | `/dashboard` remains the legacy route; no redirect to V2 |
| Page identity | Heading remains `Dashboard` |
| Libraries | Forms, Reports, Engineering Works, Definitions; no fifth library |
| Primary filters | Search, Category, Status, Used In; no Wave A advanced filter disclosure |
| Forms table | Baseline-style S/N, Version, Reference, Form, Category, Description, Action columns |
| Forms details | Baseline category/version/status/used-in/description/purpose/download presentation; no governance sections |
| Actions | Existing New, Edit, History, and shared versioning actions remain available under existing role rules |
| Inputs | `/dashboard/inputs-go-live` requests the legacy payload (`include_governance` omitted) |
| Reports/Engineering/Definitions | Existing components and routes remain unchanged |

The V1 serializer boundary is presentation-level in this change: it calls the existing canonical APIs without governance filter parameters and suppresses governance-only list/detail sections. Backend access control, restricted-source checks, immutable version history, and shared resolver behavior remain authoritative.

Intentional non-baseline additions are confined to the home Dashboard V2 destination and the separate `/dashboard-v2` route.
