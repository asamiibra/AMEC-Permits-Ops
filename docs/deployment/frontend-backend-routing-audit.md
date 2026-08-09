# Frontend → FastAPI Vercel routing audit

Date: 2026-08-08

## Scope

- Frontend: `https://amec-permits-ops.vercel.app`
- Backend: `https://amec-permits-ops-backend.vercel.app`
- Frontend root: `frontend/`
- Branch audited: `main`

## Findings before the fix

The frontend API utility in `frontend/src/api.ts` constructed requests as `${VITE_API_URL || ""}${path}`. The application passes relative paths, including `/api/projects`, `/api/applications`, `/api/reconciliation/governance`, and the other `/api/...` paths in `frontend/src`. `Week45.tsx` also calls `/mock-authority/applications/{id}/draft`. No absolute backend URL was hard-coded in frontend source or deployment configuration, and no active `amec-permits-ops-r985.vercel.app` reference was found.

`frontend/vite.config.ts` has local development proxies for `/api`, `/health`, and `/mock-authority` to `127.0.0.1:8000`. Those proxies are development-only and do not configure the deployed Vercel project. There was no `frontend/vercel.json` before this fix.

Before the fix, the deployed frontend returned `404 text/plain; charset=utf-8` with `The page could not be found` for `/api/dashboard` and `/mock-authority/applications`. It also returned the same Vercel 404 for direct navigation to `/issues`, `/notifications`, and `/about`. Because the deployed frontend had no explicit backend rewrites or SPA fallback, material backend and client-side routes were handled by Vercel's default routing. The API utility then blindly called `response.json()` on the text error, producing the misleading `Unexpected token` message.

## Route inventory

The complete material route-family inventory is recorded in `artifacts/deployment/frontend-api-route-inventory.json`. The source audit found two backend families:

1. `/api/*` — the primary FastAPI namespace, used extensively throughout `frontend/src`.
2. `/mock-authority/*` — the synthetic authority namespace, used by `frontend/src/Week45.tsx`.

The frontend-only routes include `/`, `/issues`, `/notifications`, and `/about`. No other backend route family is called by the frontend source.

## Required routing contract

The `/api` prefix is part of the backend route and must be preserved. The synthetic authority namespace is separate and must also be preserved. Both rules must precede the SPA fallback. The resulting rules are in `frontend/vercel.json` and are documented in `frontend-backend-routing-fix.md`.

## Verification boundary

Direct backend probes reached FastAPI for `/`, `/health`, `/openapi.json`, and `/mock-authority/applications`. `/api/dashboard` reached FastAPI but returned a JSON `500`, which is a downstream database/environment condition, not a Vercel routing failure. No database, schema, seed, or backend business logic was changed for this routing fix.
