# Vercel deployment entry baseline

- Branch: `branch/ui-productionization`.
- Entry HEAD: `4467c5532fc8aa19d48181e1debe1c109b643311`.
- `origin/branch/ui-productionization` matched entry HEAD.
- The worktree contained the approved Home implementation changes plus generated browser-artifact churn. Generated artifacts are preserved separately; only approved source, tests, Home evidence, and deployment evidence belong in the release commit.
- Frontend production build had passed before this deployment run; the final release gate is rerun against the immutable commit.
- Frontend project configuration: `frontend/vercel.json`; backend project configuration: `backend/vercel.json`.
- Current production aliases at entry: `https://amec-permits-ops.vercel.app` and `https://amec-permits-ops-backend.vercel.app`.
- Entry frontend production deployment was READY but predated this Home revision. Entry backend production `/health` was READY, PostgreSQL-backed, and synthetic-only.

The primary workbook hash remained `3eb887e87bf0d5695a570e8aa1e6c917d646176c77e1b978d6387681d58f1be0`.
