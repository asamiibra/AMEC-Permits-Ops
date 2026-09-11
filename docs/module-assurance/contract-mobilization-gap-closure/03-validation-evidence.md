# Validation evidence

All evidence in this file is synthetic and isolated to the gap-closure clone. No pre-production, production, Entra, Synology, DNS, release-artifact, or real AMEC source was used.

## Frontend

- `npm ci`: PASS; committed `frontend/package-lock.json` is the exact lockfile and the install produced no lockfile change.
- Typecheck: PASS (`npx tsc -b --pretty false`) after the Contract workspace changes.
- Vitest baseline: PASS, 21 files / 113 tests.
- Browser E2E: PASS, 1 focused synthetic test; it renders executed-evidence lineage and the canonical Operations projection.
- Production build: initial baseline PASS. A post-change rerun was blocked at Vite's copy of the tracked `frontend/public/brand/amec-logo-master.png` by the local checkout/filesystem stall; this is recorded as a local tooling gap and not represented as hosted acceptance.

## Backend

- Focused Contract/Mobilization and handover suite: **3 passed, 7 skipped, 1 warning**.
- The new test verifies exact evidence/revision persistence, idempotent evidence recording, no pre-activation ServiceEngagement mutation, activation gating, role denial, duplicate ServiceEngagement idempotency, canonical Operations projection, and audit persistence.
- Wider `PYTHONPATH=. pytest -q backend/tests` was started but stopped after an unrelated local test-process/filesystem stall; no failure result was produced by that interrupted run.

## Boundaries

Module-local code and isolated synthetic acceptance are distinct from future governed release-hosted acceptance. The latter remains deferred.
