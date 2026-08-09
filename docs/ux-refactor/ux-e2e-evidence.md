# UX E2E evidence

Existing browser regression coverage remains green: 14 tests covering canonical fixture visibility, control safety, RTL/LTR identifiers, monitoring, drift fallback, attended handoff, recurrence, and acceptance boundaries.

The operator shell is covered by `frontend/tests/workflow-first.test.tsx` for returned-state and authority-review projections. `frontend/browser-e2e/workflow-first.spec.ts` exercises a seeded returned permit from My Work through all eight permit steps and asserts route, current stage, next action/blocker context, human-submit boundary, and Administration role visibility.
