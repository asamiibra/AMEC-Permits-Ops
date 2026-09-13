# Full regression

Executed in this P05 epoch:

- Backend: `952 passed, 33 skipped, 4 warnings` (`pytest -q backend/tests`, 509.09s).
- Clean frontend validation: build passed; `21` test files and `114` tests passed.
- Alembic: one head, `intelligence_v1_shared_contracts`.
- Relevant public response surface: no P05 frontend response contract changed; clean P04 frontend checkout was used to avoid the unrelated dirty UX edits.
