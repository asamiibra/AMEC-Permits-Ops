# Administration Forms connection

Administration now exposes `Forms` inside the existing `Proposals & Contracts` group at `/admin/forms`. It is a second business access and management surface over the existing canonical `MasterContentItem(content_type=FORM)` records.

The Administration and Dashboard surfaces both use `frontend/src/MasterContentForms.tsx`, query `GET /api/master-content?content_type=FORM`, and issue the existing create, version, history, and download commands. `X-Source-Surface` is audit context only; it does not create separate business state.

No AdminForm table, AdminFormVersion table, copy folder, sync job, Admin-only version pointer, or migration was added. Owner writes reuse `MASTER_FORM_WRITE`; Business Development and Engineering remain unable to retain Administration access or write Forms through direct API calls.

The focused backend parity test proves shared ref/category/description/status/current-version/history/download behavior, v1 supersession, Administration audit context, RBAC denial, and zero spurious Issue/Work/Notification records for an ordinary Form upload. The local active real-stack suite passed 21/21, including the new Administration Forms workflow.

The deployed aliases are live and the Owner-only production check passes. Production historical download is not claimed for the synthetic Vercel `/tmp` SOR: PostgreSQL metadata survives across serverless invocations, while that explicitly ephemeral test file store does not. This is an environment limitation, not a new Forms datastore or a real Synology verification result.

Evidence:

- `artifacts/owner-dashboard-sor/admin-forms-result.json`
- `artifacts/owner-dashboard-sor/admin-forms-browser-result.json`
- `artifacts/owner-dashboard-sor/admin-forms-duplication-result.json`
- `artifacts/owner-dashboard-sor/admin-forms-matrix-result.json`
