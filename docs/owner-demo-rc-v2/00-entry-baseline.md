# ProposalOps — Owner Demo RC v2 Entry Baseline

Date: 2026-08-09. Repository: `main`, HEAD `3495937b898444ba78f275cbdbb562ff8e23e36e`. The working tree contains pre-existing user changes; this audit preserves them.

The protected local baseline is the AMEC Work homepage, role-scoped work projection, Administration owner surface, Proposal/Contract lineage, Issues/Notifications, and permit Stage 1 command. Local verification uses disposable PostgreSQL database `permitops_owner_demo_rc_v2`, migration head `0025_permit_workflow_stage_confirmation`, and the seeded synthetic fixture.

Entry evidence: PostgreSQL migration and seed completed; backend `99 passed`; frontend Vitest `24 passed`; Vite build passed; selected real-stack browser suite `15 passed`; targeted cross-project negative suite `3 passed`. The final deployment closure subsequently aligned the public frontend/backend to this RC, verified Neon PostgreSQL at migration head `0025`, and passed the Owner, BD, and Engineering deployed golden paths. Final status is ready; see `RC_LOCK.md` for the immutable closure record.
