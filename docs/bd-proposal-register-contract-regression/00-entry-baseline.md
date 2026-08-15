# Entry baseline

- Date: 2026-08-15
- Repository: `main`
- Entry commit: `f956f5316515e2cd5a4fd2514604e2a78d9ad954`
- Alembic head: `0055_bd_proposal_final_hardening`
- Environment: synthetic/test data only; PostgreSQL-backed real stack
- Active route: `http://127.0.0.1:5179/opportunities`

The isolated real stack reproduced the Owner-facing failure deterministically: the Proposal Register rendered `Failed to fetch`, all four lane badges as `—`, and no rows. A direct backend `GET /api/bd/proposals?q=&lane=ALL` returned HTTP 200 with `count=2`, valid `items`, and valid `lane_counts`; this established that the first failing browser request was the preflight, not an empty business result.

Captured failing preflight correlation ID: `7ebd460d-9248-48f4-81de-35a4cc594a89`.
