# Current page audit

The Proposals & Contracts page remains the owner-facing register. ProposalOps, AMEC Work, Proposals & Contracts, Issues, Notifications, Operating Guide, Owner, Business Development, and Engineering remain visible product areas; Permit remains downstream.

The register is backend-backed by `/api/proposals-main`. Proposal rows use `/proposals/{id}` and contract rows use `/contracts/{id}`. No row action is derived from an artifact label.

Local evidence: `backend/tests/test_proposals_main.py`; `artifacts/proposals-contracts-final/data-reconciliation.json`.
