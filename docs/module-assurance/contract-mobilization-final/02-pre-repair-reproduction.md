# Pre-repair reproduction

At the baseline head:

- `backend/app/services/backend_realignment.py` and Contract routers used `CONTRACT_AUTHORITY_ACTION` for review, checker, acceptance, execution evidence, and handoff.
- `commercial_reconciliation()` initialized an order as `NOT_ASSERTED` and allowed overall `PASS`.
- `POST /api/admin/contracts/{contract_id}/stage` accepted `stage=CLOSED` and directly wrote Contract stage/status.
- `_document_version_or_404()` checked only UUID existence for payment terms, deliverables, client inputs, evidence, and executed evidence.
- The cold exact-head review also found the mounted legacy recovery API could approve a `ContractRevision` and record execution evidence using a separate model path; this was closed with an explicit `410 CANONICAL_CONTRACT_WORKSPACE_REQUIRED` response.

The targeted tests added in `backend/tests/test_admin_contract_owner_session.py` reproduce the corrected negative outcomes and prove the repaired behavior. Existing positive Contract, gap-closure, Handover, Billing, contact, and readiness tests remain the regression basis.
