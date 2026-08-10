# Browser Golden Paths

The active real-stack Playwright suite passed 19 tests locally and 19 tests against `https://amec-permits-ops.vercel.app`. It used real Vite, real FastAPI, real PostgreSQL-backed deployment data, and no API interception.

The new Owner path covers Dashboard loading, Form create/modify/history, Engineering Works create/modify, explicit Engineering dependency registration, material change propagation, Issues, AMEC Work, Notifications, Definitions lookup, and dependency revalidation. Existing Owner, Business Development, Engineering, Administration, mobile, accessibility, and controlled-error coverage also passed.

Evidence: `artifacts/owner-dashboard-sor/browser-result.json` and the Playwright JSON output under `artifacts/pre-client-final-closure/real-stack-playwright.json`.
