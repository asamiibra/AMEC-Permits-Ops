# Regression evidence

- `pytest -q backend/tests/test_project_engineering_approved_baseline.py`: 1 passed.
- `pytest -q backend/tests/test_engineering_drawing_review_reconciliation.py`: 1 passed.
- `pytest -q backend/tests`: 159 passed, 1 skipped, 2 warnings.
- Fresh SQLite Alembic upgrade: head `0046_engineering_drawing_review_reconciliation` reached successfully.
- `npm run build`: passed; Vite emitted only the existing chunk-size warning.
