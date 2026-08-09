# Vercel FastAPI deployment fix

## Required Vercel project settings

- Root Directory: `backend`
- Framework preset: FastAPI, pinned in `backend/vercel.json`
- Build/install source: `pyproject.toml` runtime dependencies derived from the tested `requirements.txt`; `requirements.txt` remains the complete local/test manifest
- Entrypoint: resolved explicitly as `app.main:app` from `backend/pyproject.toml`; no wrapper or static Python entrypoint is retained
- Environment variables: provide the deployment-specific `DATABASE_URL`, `APP_ENV`, and `SYNTHETIC_ONLY`; do not commit their values

## Expected URLs

- `https://<deployment-domain>/`
- `https://<deployment-domain>/health`
- `https://<deployment-domain>/docs`
- `https://<deployment-domain>/openapi.json`

After Vercel redeploys the pushed commit, manually verify those URLs and confirm that the response is the PermitOps API rather than a Vercel branded 404. A frontend SPA rewrite must not be added to the backend project.

## Local evidence

Run from `backend/` with a temporary SQLite URL:

```bash
DATABASE_URL="sqlite:////tmp/permitops-vercel-smoke.db" APP_ENV=TEST SYNTHETIC_ONLY=true PYTHONPATH=. python scripts/vercel_backend_smoke.py
```

The smoke check is intentionally read-only with respect to the tracked synthetic databases. The repository's `.db` files remain required fixtures and are not ignored, replaced, or regenerated.
