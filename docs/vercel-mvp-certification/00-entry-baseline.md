# Entry baseline

- Branch: `branch/owner-form-simple-dashboard`.
- Pre-Vercel local closure SHA: `2e3cff6bb5781aaaa4b8751f6f41f0455b20c369`.
- Vercel compatibility work was based on the subsequent repository head and the final deployment was made from the exact frozen worktree SHA reported in the certification handoff.
- The only unrelated working-tree change preserved throughout is `mock-systems/excel/permit_tracker.xlsx`.
- Alembic head: `0058_source_intake_ledger`.
- Python pin: `backend/pyproject.toml` requires Python `>=3.12`; Vercel selected Python 3.12.
- Dependency sources: `backend/pyproject.toml`, `backend/requirements.txt`, and `backend/uv.lock`.
- Frontend: npm/Vite build from `frontend/package.json`.
- Entrypoint: `app.main:app` through `backend/pyproject.toml` and `backend/vercel.json`.
- Backend routing: FastAPI routers included from `backend/app/main.py`.

The baseline is a synthetic TEST MVP, not an Owner-document or production baseline.
