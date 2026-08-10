# Current homepage audit

## Finding

Before this change, `/work` rendered `MyWorkPage` and `UnifiedMyWorkPanel`. The page queried findings, tasks, notifications, and permit-oriented derived summaries independently. It exposed `Resume permit work`, duplicate KPI rows, permit-only sections, and raw communication state.

## Disposition

| Surface | Disposition | Reason |
| --- | --- | --- |
| `MyWorkPage` homepage rendering | Replaced by work projection | `/work` now renders `AMECWorkPage`. |
| `UnifiedMyWorkPanel` | Replaced by work projection | Its queue is no longer mounted from the homepage. |
| `/api/findings`, `/api/tasks`, `/api/notifications` homepage fan-out | Replaced by `/api/work` | Domain primitives are projected once server-side. |
| Permit workspace and downstream permit stages | Still valid downstream | Permit remains a lifecycle domain and exact-stage destination. |
| Lower permit summary, blocked-permits, authority-change, delivery-failure panels | Obsolete on homepage | Issues and Notifications own those boundaries. |
| `/api/reconciliation/governance` homepage call | Removed | Governance is not needed to render AMEC Work. |

The legacy source functions remain only where downstream screens still use the surrounding workflow module; the homepage path does not mount them.
