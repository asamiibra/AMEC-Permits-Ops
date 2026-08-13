# Full Regression

- SQLite backend: `151 passed, 1 skipped`.
- PostgreSQL backend: `152 passed`.
- Frontend: `32 passed` across 12 test files.
- Production build: `tsc -b && vite build` passed.
- Real-stack browser: `4 passed` — shared foundation smoke plus the three existing Dashboard V1/V2 split checks.
- Migration: fresh upgrade, downgrade to `0036`, and re-upgrade to `0040` passed on SQLite and fresh upgrade reached `0040` on PostgreSQL.
