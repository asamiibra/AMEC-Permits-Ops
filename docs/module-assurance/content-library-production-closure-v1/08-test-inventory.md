# Test inventory

The closure run uses synthetic TEST configuration only (`APP_ENV=TEST`, `SYNTHETIC_ONLY=true`, `REAL_DATA_ALLOWED=false`). At final candidate head `c07285bfb7466ba1fbbf92d5adcd6a6db0cf2b6b` (`TREE=9cf53dce56f97faf17ec4fe1d66b6eb7b687858c`), the focused Content Library/Source18/Dashboard/IaC reconciliation passed `77 tests, 2 skipped, 1 warning`. A bounded complete backend run reached `597 passed, 13 skipped` before manual interruption at an unrelated long-running test; it is not reported as a full-suite pass.

The exact-head PR checks passed for `backend-regression`, `frontend-regression`, `migration-head`, `policy-and-security`, and both `samba-contract` jobs. The backend Vercel preview failed independently and remains a production-shaped runtime gate, not an implementation failure.
