# G0 — Current-state audit

Baseline: 2026-08-09, local synthetic stack.

The repository already contained a partial ProposalOps rebrand and a Proposals & Contracts API/page. The reconciliation governance endpoint reproduced healthy at `200`; the historical `/api/reconciliation/governance` 500 is not active in this runtime. The material gaps were project-required intake, no provisional SOR record, no explicit Contract/Permit columns, no source-driven New Proposal UX, no separate Contract register, and a global Permit-to-Proposal text rewrite.

Evidence: `backend/tests/test_proposals_main.py`, `frontend/browser-e2e/proposals-main.spec.ts`, `frontend/browser-e2e/proposalops-rebrand.spec.ts`, `artifacts/master-realignment/current-screen-route-inventory.json`.

G0 result: PASS for the audited local implementation. Deployment verification remains a G11 item.
