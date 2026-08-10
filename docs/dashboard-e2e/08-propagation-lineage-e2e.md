# Propagation and lineage

The material Engineering Work trace is recorded in `artifacts/dashboard-e2e/engineering-propagation-trace.json`. It was produced from a real deployed API run and then archived. One causal v2 event links the source item, old/new versions, dependency, lineage edges, Finding, WorkflowTask, and NotificationEvent. The dependency is `NEEDS_REVALIDATION`, while historical v1 remains pinned.

Results: `MASTER_CONTENT_REVALIDATION_PASS`, `MASTER_CONTENT_LINEAGE_READY`, `HISTORICAL_ENGINEERING_LINEAGE_REWRITE_ZERO`, `DASHBOARD_MATERIAL_CHANGE_TRACE_E2E_PASS`.
