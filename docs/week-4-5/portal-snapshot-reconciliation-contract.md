# Portal Snapshot and Reconciliation Contract

`PortalSnapshot` captures simulator state as `PREPARATION_START`, `POST_SAVE`, `REOPENED`, `VALIDATION`, `PRECHECK`, or `HANDOFF`. `PortalReconciliationResult` returns `MATCH` or explicit `MISMATCH` by field/grid/attachment; critical mismatch prevents `VERIFIED_DRAFT` and creates a visible exception.
