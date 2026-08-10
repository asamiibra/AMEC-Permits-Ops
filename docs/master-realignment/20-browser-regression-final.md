# G11 — Final browser regression evidence

The 19 failures recorded in `artifacts/master-realignment/full-browser-regression.json` were repaired as assertion drift. The focused historical set now passes 28/28, including the canonical bootstrap/safety scenario and the E7/E8 work-surface scenarios.

The changes are limited to `frontend/browser-e2e/canonical-controls.spec.ts` and `frontend/browser-e2e/e7-e8-expanded.spec.ts`. They replace retired PermitOps/Permit labels, the Permit Preparer/four-assistant owner model, legacy assistant summary labels, and removed navigation expectations with the current AMEC Work, Owner/Business Development/Engineering, and Proposals & Contracts behavior. No feature code was changed and no safety assertion was removed.

The current 110-test browser suite was also exercised against a persistent local Vite server. It aggregated 82 passing and 28 remaining failures. Of those remaining failures, 27 are non-target historical assertion contracts in expansion, language, persona, pre-client, pre-G10, readiness, and workflow specs; one is a server-lifecycle failure during the legacy pre-client reload path. They are not counted as product behavior changes in this realignment.

## Remaining genuine product failure

The Proposals & Contracts register throws `TypeError: Cannot read properties of undefined (reading 'OPEN_PROPOSALS')` when `/api/proposals-main` returns an incomplete payload. This is observed at `frontend/src/ProposalsContracts.tsx:466` and remains open because the requested scope is limited to obsolete browser expectations.

Final machine-readable evidence: `artifacts/master-realignment/full-browser-regression-final.json`.
