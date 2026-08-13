# Migration and backfill

SQLite and PostgreSQL both passed upgrade-to-head, downgrade-to-0040, and upgrade-to-head round trips. PostgreSQL finished at `0041_dashboard_v2_waves_b_c (head)`. The new tables are additive and source-version constrained; no unsafe inferred activation or fabricated historical backfill is performed.

Evidence: `artifacts/dashboard-v2-waves-b-c/03-migration-summary.json`.
