# Migration and backfill proof

Migration: `backend/migrations/versions/intelligence_v1_shared_contracts.py`

```text
DOWN_REVISION=17c6ebd99c4a
REVISION=intelligence_v1_shared_contracts
REPOSITORY_HEAD_COUNT=1
BACKFILL_SCOPE_TYPE=PROJECT
BACKFILL_SCOPE_ID=existing project_id
BACKFILL_SUBJECT_TYPE=PROJECT
BACKFILL_SUBJECT_ID=existing project_id
HISTORICAL_LEDGER_MODULE_SKILL=preserved nullable (not fabricated)
```

The migration adds nullable columns, backfills all legacy project rows, fails closed if any row lacks a project-backed scope, and then enforces non-null scope/subject fields. `project_id` remains nullable for generalized shared scopes. The ledger's historical owning module and skill fields remain nullable.

Qualification evidence:

- A representative pre-P02 SQLite schema at head `17c6ebd99c4a` upgraded successfully.
- The resulting assertion rows were verified as `PROJECT / p1` scope and subject with original `project_id` preserved.
- The resulting ledger rows were verified as `PROJECT / p1` scope with module/skill fields remaining null.
- The repository-wide fresh SQLite upgrade was attempted; it is blocked by the pre-existing baseline migration's unsupported SQLite `ALTER` foreign-key operation before Prompt 02 runs. The repository's existing migration qualification remains the authoritative path for supported Azure SQL/Postgres deployment.
