# Regression evidence

- Focused backend hardening test: passed.
- Existing Forms-v2/Owner-session focused tests: `7 passed`.
- Full SQLite/root backend: `196 passed, 8 skipped`.
- Full PostgreSQL 16 backend after empty-schema migration: `204 passed`.
- Frontend Vitest: `35 passed`.
- Frontend production build: passed.
- Target-runtime Playwright browser acceptance: `3 passed` against PostgreSQL 16; final migration head asserted.
- Cross-module Dashboard numbering regression fixed by excluding Proposal-specific sequence from the four-library Dashboard preview.
