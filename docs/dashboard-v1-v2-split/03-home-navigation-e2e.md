# Home and Navigation E2E

Real-stack Playwright coverage is in `frontend/browser-real-stack/dashboard-v1-v2-split.spec.ts`.

Verified against a fresh local PostgreSQL database migrated through `0036_dashboard_forms_governance_wave_a`, the real FastAPI backend, and the Vite proxy:

- `/work` shows the existing Dashboard destination and the Owner-only Dashboard V2 destination.
- Dashboard opens `/dashboard` with the `Dashboard` heading.
- Dashboard V2 opens `/dashboard-v2` with the `Dashboard V2` heading.
- V2 `Inputs & Go-Live` opens `/dashboard-v2/inputs-go-live`.
- Direct non-owner navigation to `/dashboard-v2` is replaced with `/dashboard` and the V2 home card is hidden.
- The focused browser suite passed all 3 tests; the test includes direct-route refresh coverage through fresh `page.goto` calls.
