# Data & Connections

The owner projection exposes four business connections: Synology / document SOR, Excel project register, Tender / email source, and Municipality / Portal. Each card shows purpose, mode, status, affected workflow, and a persisted last-test timestamp when one exists.

`POST /api/admin/connections/test` runs the adapter health check, records the result timestamp in the bounded `ADMIN_CONNECTION_HEALTH:AMEC` configuration artifact, and writes `ADMIN_CONNECTION_TESTED` to audit history. Secrets are server-side and are never included in the projection.

Synthetic, Test Mode, and Simulator labels are intentional. They prevent a local fixture from being represented as an AMEC production connection.
