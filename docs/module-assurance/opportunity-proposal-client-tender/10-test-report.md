# Test report

Passing validation:

- Full backend regression after the one-time main merge: `887 passed, 33 skipped, 0 failed`.
- Focused Proposal commercial-control suite: `4 passed`, including deterministic concurrent replay coverage.
- Frontend production build: PASS.
- Frontend Vitest: `21 files, 114 tests passed`.
- Python compileall for backend application and migrations: PASS.
- `git diff --check`: PASS.
- SQL Server clean migration and persistence proof: PASS.
- Native SQL Server runtime gate: `16 passed, 0 skipped, 0 failed`.
