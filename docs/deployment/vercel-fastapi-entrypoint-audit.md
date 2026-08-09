# Vercel FastAPI entrypoint audit

The backend deployment root is `backend/`. The application exports a FastAPI instance named `app` from `backend/app/main.py`, so the explicit Vercel entrypoint is `app.main:app` when Vercel runs from that root.

The authoritative backend dependency file is `backend/requirements.txt`. There was no backend-specific `vercel.json`, no backend static rewrite, and no frontend fallback rewrite that could serve the API. The branded Vercel 404 was therefore treated as an ambiguous/missing backend entrypoint configuration issue; this audit does not claim a live Vercel deployment was independently changed or verified.

The deployment configuration is explicit in `backend/pyproject.toml`:

```toml
[tool.vercel]
entrypoint = "app.main:app"
```

Because the live project was still returning Vercel's `404: NOT_FOUND` after the
explicit configuration was pushed, `backend/index.py` also re-exports the same
verified object as Vercel's standard root `index.py` FastAPI detection path. It
contains no second application instance and no route logic.

The backend exposes both `/` and `/health`. Runtime configuration remains environment-driven through the existing settings (`DATABASE_URL`, `APP_ENV`, and `SYNTHETIC_ONLY`). No secret or credential is stored in the repository. No migration or seed operation was added to an import or request path; the existing application lifespan only initializes the configured database schema.

Local verification uses `backend/scripts/vercel_backend_smoke.py`, which imports `app.main:app`, checks the OpenAPI document, and exercises `/`, `/health`, `/docs`, and `/openapi.json` without starting lifespan or mutating the repository databases.
