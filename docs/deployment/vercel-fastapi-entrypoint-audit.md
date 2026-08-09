# Vercel FastAPI entrypoint audit

The backend deployment root is `backend/`. The application exports a FastAPI instance named `app` from `backend/app/main.py`, so the explicit Vercel entrypoint is `app.main:app` when Vercel runs from that root.

The complete tested backend dependency file is `backend/requirements.txt`. The
Vercel build also requires a valid PEP 621 `[project]` table, so
`backend/pyproject.toml` now declares the runtime subset derived from that
tested manifest; test-only packages remain in `requirements.txt`. There was no
backend static rewrite and no frontend fallback rewrite that could serve the
API. The original branded Vercel 404 was caused by skipped framework detection.

The deployment configuration is explicit in `backend/vercel.json` and
`backend/pyproject.toml`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "fastapi"
}
```

```toml
[tool.vercel]
entrypoint = "app.main:app"
```

An attempted root `backend/index.py` compatibility wrapper was removed after
`vercel dev` proved that Vercel served it as a downloadable static Python file
instead of executing the FastAPI application. The deployment therefore uses
the real `app.main:app` object directly. A local `vercel build` before the
framework pin reported `framework: null`, skipped detection, and selected only
`@vercel/static`; the explicit framework pin addresses that confirmed failure.

The backend exposes both `/` and `/health`. Runtime configuration remains environment-driven through the existing settings (`DATABASE_URL`, `APP_ENV`, and `SYNTHETIC_ONLY`). No secret or credential is stored in the repository. No migration or seed operation was added to an import or request path; the existing application lifespan only initializes the configured database schema.

Local verification uses `backend/scripts/vercel_backend_smoke.py`, which imports `app.main:app`, checks the OpenAPI document, and exercises `/`, `/health`, `/docs`, and `/openapi.json` without starting lifespan or mutating the repository databases.
