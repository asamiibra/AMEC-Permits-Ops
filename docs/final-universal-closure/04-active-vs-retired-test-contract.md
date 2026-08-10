# Active versus retired test contract

## Current active release suites

- Backend: `pytest -q backend/tests` — 119 passed.
- Frontend unit: `npm test -- --run` — 29 passed.
- Frontend typecheck/build: `npx tsc --noEmit && npm run build` — pass.
- Current mocked browser: 69 passed.
- Current real-stack: 18 passed.
- UI conformance: 312 route/persona/viewport results, ready.

## Retired historical tests

The ignored expansion-e3-e4, expansion-e5-e6, pre-client-shell, pre-g10-control-paths, workflow-first, accessibility, issue-detail-final, new-proposal-final, owner-rehearsal, proposals-contracts-final, stage1-confirm-project-sources, and visual-qa contracts are preserved as historical evidence and are not mixed into the active release result. The issue deep-link and persona issue/notification suites are current active contracts.
