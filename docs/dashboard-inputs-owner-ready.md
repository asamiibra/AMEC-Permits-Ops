# Dashboard Master Content Inputs & Go-Live

The Dashboard now uses a persistent, Dashboard-specific readiness context for Forms, Reports, Engineering Works, and Definitions. The shared `/admin/go-live-readiness` route and its legacy control-room context remain available for other modules.

The checklist is stored in `dashboard_input_items`, keyed by the 13 stable `DASHBOARD_*` identifiers. Current content counts, category taxonomy, reference proposals, and Synology health are projected from existing master-content and Administration integration sources. Owner/System Admin changes create `AuditEvent` records; Business Development and Engineering are read-only. Real Synology confirmation is rejected until the production health check succeeds.

Local and production evidence is in `artifacts/dashboard-inputs-owner-ready/`.
