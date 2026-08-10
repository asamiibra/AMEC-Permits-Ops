# G11 — Browser regression scope

The repository contains 15 historical browser spec files under `frontend/browser-e2e`, covering shell, branding, About/Operating Guide, canonical permit controls, pre-client controls, expansion, readiness, workflow, and the new ProposalOps suites. No failing historical spec was deleted.

Classification:

- `STILL_VALID`: human-only boundary, language isolation, readiness drawer, accessibility-oriented shell behavior, and existing downstream workflow assertions that remain compatible with the current owner model.
- `UPDATED_FOR_REBRAND`: About/branding assertions and `proposalops-rebrand.spec.ts`; these assert ProposalOps/AMEC, AMEC Work, Proposals & Contracts, Owner, Business Development, and Engineering.
- `UPDATED_FOR_NEW_OWNER_MODEL`: `proposals-main.spec.ts` and the new detail-route scenario; these cover orange human source actions, blue derived KPIs, Proposal Preparation, Contract detail, and direct deep links.
- `OBSOLETE_BY_OWNER_DIRECTION`: assertions that require the retired PermitOps collection label, Permit Preparer persona, or four-assistant lens as a normal client-facing navigation model. Their underlying downstream Permit safety behavior is retained and covered by the current Permit workspace tests.

Run evidence from the local full suite: 118 tests discovered, 99 passed, 19 failed. The failures are recorded rather than suppressed; most are stale label/owner-model assertions, with legacy timing failures in the same superseded navigation paths. The focused current suite passed 7/7 locally and 7/7 against the deployed frontend/proxy stack.

The 19 historical failures were replaced with equivalent current-owner assertions and the repaired target set passes 28/28. Final evidence is recorded in `artifacts/master-realignment/full-browser-regression-final.json` and `docs/master-realignment/20-browser-regression-final.md`. The broader current browser suite still contains non-target assertion drift and one open Proposals & Contracts payload-robustness failure; those are listed separately rather than hidden or weakened.
