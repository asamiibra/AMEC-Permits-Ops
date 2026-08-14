# Reproducibility

Authoritative command: `DATABASE_URL=postgresql+psycopg://<local-user>@localhost:5432/<fresh-db> PYTHONPATH=. pytest -q backend/tests`. Bridge-only command: the same environment with `backend/tests/test_handover_final_closure_bridge.py`. SQLite parity is run with `DATABASE_URL` unset. Frontend commands are `npm test -- --run` and `npm run build` from `frontend/`.

