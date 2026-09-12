# Browser E2E

The repository’s real-stack Playwright surfaces are `frontend/browser-real-stack/contract-page-owner-sketch-delta.spec.ts`, `admin-owner-ready.spec.ts`, `contract-center-final-owner-hardening.spec.ts`, `administration-final-audit.spec.ts`, and the accessibility/visual suites. The final candidate must run these against the real test backend and persistence lane; mocked-only browser checks are not acceptance.

Local in-app browser smoke evidence was captured against the isolated Vite/API stack at `http://127.0.0.1:5177/contract-mobilization` with a seeded synthetic SQLite backend. The Contract Center loaded, opened the canonical Contract detail route, rendered the ordered section navigation, showed the legacy-safe blocked state, showed `Executed Contract Evidence` locked before acceptance, showed Operations and Related Finance read models, and reported zero browser console errors. The URL and page title were read back from the browser session.

The full Postgres real-stack suite was not claimed from this local SQLite seed because the golden `SYN-CTR-0007` fixture is intentionally created only by the repository's Postgres seed path. It remains a required governed PR check; no mocked-only browser result is promoted as production evidence.

Required checks include loading, empty/error/retry feedback, keyboard/focus/responsive behavior, Contract review/checker/acceptance, evidence and handoff ordering, readiness, contacts, billing, schedule, Handover, and blocked close actions.
