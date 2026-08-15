# Migration Provenance

Alembic reports one head: `0058_source_intake_ledger`. The tail is `0054 -> 0055 -> 0056 -> 0057 -> 0058`, with 0055 introduced by the Proposal hardening commit, 0056/0057 by the Owner Forms/storage commit, and 0058 by the Source Intake reconciliation commit. No orphan revision or second head exists.

At the audit point the migration chain is fully reachable from the tested feature SHA, but not yet from `origin/main` because main is 13 commits behind. This is the explicit expected pre-integration state; after fast-forward, the final-main gate must be rerun and must report `MIGRATION_REACHABILITY_FROM_TARGET_MAIN_PASS=1`.
