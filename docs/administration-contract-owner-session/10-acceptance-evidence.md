# Administration + Contract Owner Session — Acceptance Evidence

## Build

The Owner API and Administration UI provide the Contract list, exact accepted Proposal handoff, manual-new policy, Contract reference/stage/amount/close-date fields, workbench, origin panel, canonical Dashboard Contract Template snapshot, admin inputs, readiness, evidence, append-only history, My Work/Issues/Notifications projections, explicit Project Activation, separate Project Code, Start Date, Contract→Project lineage, and read-only Engineering/Permit context.

## Verification

Focused and full regression evidence:

- `backend/tests/test_admin_contract_owner_session.py`: 2 passed
- `backend/tests/test_proposals_main.py`, `backend/tests/test_proposals_contracts_owner_model.py`, and BD/dashboard input regression: passed
- Full backend suite: `142 passed, 1 skipped`
- PostgreSQL disposable database: Alembic `0034_admin_contract_owner_session` upgraded successfully; focused Contract suite passed
- Frontend `npm --prefix frontend run build`: passed
- Deployed backend: `https://amec-permits-ops-backend.vercel.app`
- Deployed frontend: `https://amec-permits-ops.vercel.app`
- Browser smoke: Owner Administration Contract list, Contract workbench, and 22-item Contract Inputs & Go-Live surface rendered successfully.

The focused tests prove exact accepted-revision pinning, template snapshot identity/version/hash, immutable Proposal origin after later Proposal edits, Owner-only Contract authority and Project Activation, Project Code uniqueness boundary, activation idempotency, separate Project/Opportunity Reference and Project Code, and a 22-item Contract Inputs & Go-Live registry.
