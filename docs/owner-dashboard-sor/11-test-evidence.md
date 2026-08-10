# Test evidence

Entry baseline: `artifacts/owner-dashboard-sor/entry-baseline.json`.

Focused Administration Forms/API suites: 11 passed. Full backend suite: 125 passed, 2 warnings locally and against clean PostgreSQL. Frontend Vitest: 11 files / 29 tests passed. Frontend production build: PASS. Active real-stack Playwright: 21 passed locally. The deployed aliases are live; the Owner-only Administration Forms check passed, while historical download against the explicitly ephemeral Vercel `/tmp` SOR is recorded as an environment limitation. Clean PostgreSQL Alembic migration reached `0028_master_content_propagation`. The SOR evidence class is synthetic filesystem/ephemeral TEST adapter, not production Synology.
