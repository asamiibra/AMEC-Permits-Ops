# Content Library Step 2 — Verification Plan

Focused backend tests prove canonical/v2 parity across composed filters,
`CURRENT`/`NEEDS_REVIEW`/`INACTIVE` discovery, detail identity, and historical
version replay. Frontend tests prove that the Forms library builds requests
against `/api/master-content` and does not branch to `/api/dashboard-v2/forms`
or `/api/dashboard-v2/catalogs` for normal discovery reads.

The closure also runs the existing backend suite, frontend suite, frontend
build, `git diff --check`, and Alembic head/current inspection. Test data is
synthetic and isolated by the repository test fixtures. No deployment or
runtime database mutation is part of this work.
