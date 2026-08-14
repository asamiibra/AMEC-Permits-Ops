# Construction Post-Approval Closure — Entry Baseline

Captured before closure changes at `2026-08-13T23:31:40Z`.

- Branch: `main`
- HEAD: `19597f9390391310308ed4833232b8452c55f13e`
- `origin/main`: `19597f9390391310308ed4833232b8452c55f13e`
- Dirty tree: 32 tracked modifications, 1 tracked deletion, 107 untracked paths.
- `git diff --check`: passed at entry.
- Alembic current from the default local configuration: `0021_e7_unified_task_context`; Alembic head: `0050_construction_post_approval_controls`.
- Test database: SQLite by default; PostgreSQL selected by an explicit `DATABASE_URL`.
- Frontend commands: `npm test`, `npm run build`, `npm run browser-real-stack`.
- Browser config: `frontend/playwright.real-stack.config.ts`.

The prior Construction result and the post-Billing result were read from the repository before repair. The complete machine snapshot is in `00-entry-baseline.json`; exact per-path metadata is in `01-dirty-tree-inventory.json` and classifications are in `02-fixture-change-classification.json`.
