# Contract Lifecycle

## ROUTE / PERSONAS

`/contracts/:contractId`; Owner, Business Development, Engineering.

## DESIGN CONTRACT

Proposal → Contract → Contract → Permit. Contract detail shows canonical identity, related Proposal, status, and the downstream handoff.

## DESIGN PASS / FUNCTION PASS

PASS on current direct route coverage and raw-leak detection. Historical exact-copy assertions are not used as product proof.

## DATA / ROLE / INTEGRATION

Contract identity is sourced from `/api/proposals-main/contracts/:id`; related Proposal and Permit references are preserved.

## ERROR / LOADING / EMPTY / MOBILE / ACCESSIBILITY

Direct-load and failure-state evidence are recorded in the universal harness; no local console errors or overflow were observed.

## CROSS-PAGE / DEFECTS / EVIDENCE

Evidence: `screenshots/S02D-*`, route inventory, field authority map, and cross-page consistency registry.
