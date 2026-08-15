# Final Main Regression

The pre-main feature regression evidence is already present under `docs/dashboard-v2-promotion/` and reports PostgreSQL 236 passed / 6 skipped, frontend 37 passed, build passed, focused promotion 39 passed, and production browser 6 passed. These results are not treated as final-main results until the fast-forwarded main SHA is tested again in a clean worktree.

On integrated SHA `07ea0478dd71f37c84995936c057acadf3e939a0`: backend 228 passed / 14 skipped / 2 warnings; frontend 37 passed; frontend build passed with the existing large-chunk warning; fresh SQLite zero-to-head migration passed and reported the single `0058_source_intake_ledger` head. The final evidence commit itself is documentation-only and is followed by one final rerun before the main push gate.
