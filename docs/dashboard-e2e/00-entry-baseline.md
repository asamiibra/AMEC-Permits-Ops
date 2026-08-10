# Entry baseline

- Branch: `main`
- Commit before this closure: `22f45d02c28b1ad7fbd792996ce27b9b9e4bd976`
- Alembic before: `0030_dashboard_master_content_inputs`
- Deployed backend before repair: PostgreSQL durable, synthetic-only TEST SOR, real Synology not configured.
- Frontend: `https://amec-permits-ops.vercel.app`
- Backend: `https://amec-permits-ops-backend.vercel.app`
- Test SOR: `MockSynologyAdapter`; serverless synthetic bytes became durable in migration `0031`.
- Entry tree was clean before the closure changes.

Evidence: `artifacts/dashboard-e2e/entry-baseline.json`.

Result: `DASHBOARD_E2E_ENTRY_BASELINE_PASS`.
