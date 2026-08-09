# Weeks 1–3 Reconciliation Prechange Baseline

> **DEMONSTRATION BASELINE — SYNTHETIC DATA — NOT CLIENT APPROVED**

Captured before the recording-derived reconciliation changes.

- Backend: `make migrate && make seed && make test && make spike` — 27 passed, one Python deprecation warning.
- Frontend: Vitest — 1 passed; TypeScript/Vite production build passed.
- Integration/smoke: existing Week 1–3 TestClient/API smoke paths passed; synthetic threshold approval returned 403, approved Stage 2 baseline re-approval returned 409, and sanitized export returned 200.
- Migrations: Alembic revisions 0001, 0002, and 0003 applied to the local SQLite DEV database.
- Current database: `sqlite:///./permitops.db`; Docker/PostgreSQL server availability had not been established.
- Existing fixture sources: `backend/app/seed/cli.py`, `synthetic-data/documents/week2`, `mock-systems/synology`, `mock-systems/excel/permit_tracker.xlsx`, and inline Week 1–3 test fixtures.
- Known partial items: workbook was read-only and recognized only `GENERAL FOLLOW UP`, `DESIGN`, and `SUPERVISION`; no canonical fixture manifest; no project-initiation/bootstrap domain; no relational multi-owner/property/representation model; no TargetRenderingRule.
- Known failures/gaps: recording-derived workbook spelling and ownership contract were incomplete; unresolved synthetic conflicts remained in the seeded corpus; PostgreSQL runtime had not been exercised.

This document is the evidence boundary for the follow-up. No broad Week 4 package, form, browser automation, or production integration work is included.
