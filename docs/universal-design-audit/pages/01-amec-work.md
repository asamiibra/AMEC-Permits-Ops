# AMEC Work

## ROUTE / PERSONAS

`/work`; Owner, Business Development, Engineering.

## DESIGN CONTRACT

AMEC Work is the shared prioritized worklist. It uses current business domains, current stage, owner team, blockers, and next action.

## DESIGN PASS / FUNCTION PASS

PASS locally. All three personas render the current shell and role-scoped work. No raw actor, enum, UUID, JSON, or forbidden-term hit was recorded.

## DATA / ROLE / INTEGRATION

Data comes from `/api/work`, projects, applications, issues, and notifications. Persona filters are scoped; Owner administration is not granted to the other personas.

## ERROR / LOADING / EMPTY / MOBILE / ACCESSIBILITY

Failure injection and mobile overflow checks pass in the universal harness. Broader legacy accessibility assertions expecting a removed global Arabic switch are stale.

## CROSS-PAGE / DEFECTS / EVIDENCE

Links to Proposals & Contracts, Issues, Notifications, and downstream Permit work remain current. Evidence: `artifacts/universal-design-audit/automated-harness-result.json`, `role-matrix-result.json`, and `screenshots/S01-*`.
