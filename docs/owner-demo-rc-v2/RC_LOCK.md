# ProposalOps Owner Demo RC v2 — RC Lock

Status: `PROPOSALOPS_OWNER_DEMO_RELEASE_CANDIDATE_READY`

Locked at: `2026-08-09T15:04:23-05:00`

## Exact deployed state

- Local RC commit: `3495937b898444ba78f275cbdbb562ff8e23e36e` (HEAD).
- Deployment source note: the deployed RC includes the verified working-tree overlay for the named migration, bootstrap reconciliation, and frontend route/source-label fixes; those changes are not represented by the HEAD commit because the worktree contains unrelated user changes and was not committed.
- Frontend: `dpl_ES4KvUzAsWcDGEtcDqf7SQJPsYLq`, alias `https://amec-permits-ops.vercel.app`.
- Backend: `dpl_AhTpoekhRAcrZiret6xnQKNv6jbF`, alias `https://amec-permits-ops-backend.vercel.app`.
- Database: durable Neon PostgreSQL; public health confirms configured connection, PostgreSQL dialect, and no SQLite fallback.
- Alembic head: `0025_permit_workflow_stage_confirmation`.
- Fixture: `PermitOps_Synthetic_MVP_Dataset_v1@1.1.1`.
- Fixture manifest hash: `b3a5fbee1a968e3740801b0b696b31a39a3a907437f2377fcdfdfad3bb3546cb`.

## Verification lock

- Backend SQLite: `99 passed, 2 warnings`.
- Backend PostgreSQL: `99 passed, 2 warnings`.
- Frontend Vitest: `24 passed`.
- Vite production build: pass; one non-blocking chunk-size warning.
- Current-scope real-stack browser suite: `15/15 passed`; final Proposal Preparation route check: `2/2 passed`.
- Production API routes `/api/work`, `/api/issues`, `/api/notifications`, proposal, contract, project, findings, applications, permits, and admin summary: HTTP 200 JSON.
- Canonical lineage: `SYN-CLIENT-001 → SYN-OPP-0001 → SYN-CTR-0001 → GHCE-2026-0142 → GHCE-APP-0142`.
- Owner deployed golden path: pass, including persisted Stage 1 confirmation and Stage 2 `VERIFY_DATA` state.
- BD deployed golden path: pass, including scoped work and Contract Form access.
- Engineering deployed golden path: pass, including scoped work and Engineering-owned Proposal Preparation.
- Material 500s: `0`.
- Raw API errors: `0` on fresh final smoke.
- Fake empty states: `0`.
- Cross-project violations: `0`.
- Secret exposure: `0`.

Feature work is frozen at this lock.
