# Frontend → FastAPI Vercel routing fix

Date: 2026-08-08

## Final Vercel configuration

`frontend/vercel.json` now applies these rewrites in order:

1. `/api/:path*` → `https://amec-permits-ops-backend.vercel.app/api/:path*`
2. `/mock-authority/:path*` → `https://amec-permits-ops-backend.vercel.app/mock-authority/:path*`
3. `/(.*)` → `/index.html`

The first two rules preserve their original path prefixes. The SPA catch-all is last so it cannot intercept backend requests.

## API client hardening

The existing relative-path client remains in place. An optional `VITE_API_URL` is trimmed only for trailing slashes; with the production default unset, requests remain same-origin paths such as `/api/dashboard`. The client now checks status and content type before parsing, so a Vercel text response reports its status, endpoint, and safe content type instead of an `Unexpected token` JSON parse error.

## Verification results

The pre-fix production probes demonstrated the failure: `/api/dashboard`, `/mock-authority/applications`, `/issues`, `/notifications`, and `/about` returned Vercel `404 text/plain; charset=utf-8`. The direct backend probes and post-deployment proxy/SPA results are recorded in `artifacts/deployment/frontend-backend-proxy-result.json`.

The local configuration validation confirms valid JSON and the required rule order. Frontend unit tests cover successful JSON, JSON FastAPI errors, and non-JSON Vercel responses. The production build and routing smoke tests are part of the release verification.

## Database boundary

This change does not initialize or seed the database. A JSON `500` from the backend `/api/dashboard` route is evidence that the request reached FastAPI; it remains a downstream Neon/database setup matter and is not masked by the proxy.
