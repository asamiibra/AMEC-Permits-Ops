# Regression

Protected seams: prior Stage 1 source intake and handoff, Dashboard Template / Checklist / Definitions / Engineering Works resolution, shared WorkflowTask handoff, AcceptedProposalRevision lineage, Contract handoff, separate AuthorityCase boundary, and existing source/history behavior.

Verified results:

- SQLite backend: 195 passed, 8 skipped, 2 warnings.
- Fresh PostgreSQL backend: 203 passed, 2 warnings; database `bd_owner_fidelity_pg_20260815` was dropped after the run.
- Frontend: 13 test files, 34 tests passed.
- Production frontend build: passed; only the existing large-chunk advisory was emitted.
- Browser journey: passed on the local seeded stack, including lanes/search, four source families, BD → Engineering → BD, technical-only Engineering edit, Breakdown, AMEC Input, human Accept, pinned Proposal/Checklist downloads, refresh, and Ready / Close row.
- RBAC: Engineering Accept remains denied by the existing capability boundary; technical preparation editing is server-enforced and was exercised in the browser journey.

The exact commands, evidence routes, and machine-readable counters are in `12-final-result.md` and `artifacts/bd-proposal-owner-sketch-fidelity/final-result.json`.
