# Main Candidate Regression

Executed against candidate `4aedcc6c79973055aea14bb717c12a6dcb347953`:

- PostgreSQL backend: `236 passed, 6 skipped, 2 warnings`.
- Frontend unit tests: `39 passed` across `15` files.
- Frontend production build: PASS; only the existing large-chunk advisory remains.
- Focused browser acceptance: `27 passed, 0 failed`, one worker, PostgreSQL-backed local stack.
- Storage/source-intake subset: `7 passed, 6 skipped, 1 warning`; skipped tests are external SMB-provider cases, not local synthetic-storage failures.
- Fresh PostgreSQL migration: PASS through `0058_source_intake_ledger`.
- Upgrade migration from `0055_bd_proposal_final_hardening` to head: PASS.

`MAIN_CANDIDATE_POSTGRESQL_PASS=1`, `MAIN_CANDIDATE_FRONTEND_PASS=1`, `MAIN_CANDIDATE_BUILD_PASS=1`, `MAIN_CANDIDATE_BROWSER_PASS=1`, and `MAIN_CANDIDATE_STORAGE_SOURCE_INTAKE_PASS=1`.
