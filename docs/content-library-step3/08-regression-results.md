# Regression results

## Observed acceptance results

- Focused Step 3 consumer suite: `4 passed, 1 warning`.
- Full backend suite: `240 passed, 15 skipped, 2 warnings`.
- Cross-domain order probes in both forward and reverse file order: `37 passed, 1 skipped` each.
- Frontend Vitest: `39 passed` across 14 files.
- Frontend production build: passed (`92 modules`); existing Vite chunk-size advisory remains.
- Python compile check: passed.
- Alembic head: `0058_source_intake_ledger`; no migration created.
- `git diff --check`: passed.
- Changed-path audit: only Step 3 backend code, tests, and evidence are present; no mock/real-data artifacts are changed.
- `npm ci` reported existing dependency advisories: 1 high and 1 critical; no audit fix was run.
