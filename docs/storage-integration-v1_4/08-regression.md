# regression

- Focused archive/intake tests: 9 passed.
- Local backend suite: 228 passed, 14 skipped, 2 warnings.
- PostgreSQL Docker backend suite: 236 passed, 6 skipped, 2 warnings.
- Frontend: 38 tests passed.
- Frontend production build: passed; Vite emitted only the existing chunk-size advisory.
- Live Samba storage contract: 12 passed.
- Alembic clean SQLite zero-to-head: passed at `0058_source_intake_ledger`.
- `git diff --check`: passed.

No browser acceptance run was required for this hidden source-intake path. Crash/process termination and multi-process intake concurrency harnesses were not run in this local pass and are intentionally not certified.
