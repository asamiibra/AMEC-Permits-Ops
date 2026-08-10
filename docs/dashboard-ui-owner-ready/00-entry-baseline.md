# Dashboard v2 Owner UI closure — entry baseline

- Branch: `main`
- Commit before this closure: `b8c827282d22ca26507b34899ebe8f4f37aac007`
- Alembic head before/after: `0029_dashboard_master_content_v2`
- Backend baseline: `130 passed, 1 skipped, 2 warnings`
- Frontend baseline: `29 passed`; production build passed
- Real-stack browser baseline: `21 passed`

The deployed inspection reproduced the defects in the request: confirmed browser/deployment probe rows were visible, curated category/Used In values were missing, controls exposed raw verbs/enums, and the editor/history surface was oversized and difficult to use. The deployed PostgreSQL database was reachable, but the real Synology adapter was not configured.

Evidence is recorded in `artifacts/dashboard-ui-owner-ready/entry-baseline.json` and `defect-matrix.json`.
