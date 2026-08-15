# Final Main Regression

The pre-main feature regression evidence is already present under `docs/dashboard-v2-promotion/` and reports PostgreSQL 236 passed / 6 skipped, frontend 37 passed, build passed, focused promotion 39 passed, and production browser 6 passed. These results are not treated as final-main results until the fast-forwarded main SHA is tested again in a clean worktree.

On the final tested main code SHA `2878c5d566a6157bbf6f38969088b28395bbdf58`: backend 228 passed / 14 skipped / 2 warnings; frontend 37 passed; frontend build passed with the existing large-chunk warning; fresh SQLite zero-to-head migration passed and reported the single `0058_source_intake_ledger` head. Final-main browser smoke was not run because Vercel exact-main deployment was blocked; the earlier 6-pass browser result is not reused as final-main proof. Therefore `FINAL_MAIN_FULL_REGRESSION_PASS=0` pending deployed browser validation.
