# Regression

Local repair worktree results:

- Backend PostgreSQL-equivalent test suite: `229 passed, 14 skipped, 2 warnings`.
- FORME parity/idempotency/resolver test: `1 passed`.
- Frontend tests: `39 passed` across `15` files.
- Frontend production build: PASS; only the existing large-chunk advisory remains.

The repair is bootstrap/data-layer scoped. Dashboard V2 presentation,
proposal/checklist/contract resolver behavior, canonical DocumentVersion
history, and storage/source-intake code were not rolled back or duplicated.
