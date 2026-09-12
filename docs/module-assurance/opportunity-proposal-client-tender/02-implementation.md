# Implementation and repairs

Implemented on the canonical branch:

- Human technical assessment, scope confirmation, service eligibility, commercial release, distribution, client acceptance verification, LPO reconciliation, and Proposal→Contract handoff eligibility persistence.
- Durable accepted-revision pinning and R2 draft revision re-approval; duplicate unchanged Accept remains rejected while an explicit draft revision is accepted.
- SQL Server-safe filtered Proposal creation idempotency (`idempotency_key IS NOT NULL`).
- Fail-closed stale revision, missing evidence, wrong order, LPO mismatch, unauthorized capability, and contract/project boundary checks.
- UI controls for assessment, scope, eligibility, release, distribution, response evidence, acceptance verification, LPO reconciliation, revision creation/re-approval, and handoff eligibility.
- Projection includes the current draft revision and control evidence without changing Proposal source lineage.

The changes are implemented in the existing backend/API and frontend workspaces; no competing domain aggregate was created.
