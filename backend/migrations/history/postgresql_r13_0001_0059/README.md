# PostgreSQL R13 0001–0059 historical migration archive

This directory preserves the exact 59 Alembic revisions that were executed
against the R13 PostgreSQL reference databases before the rebaseline.

- `HISTORICAL_PROVENANCE_ONLY`
- `NOT_AN_ACTIVE_ALEMBIC_VERSION_LOCATION`
- `DO_NOT_EXECUTE_AGAINST_FUTURE_APPLICATION_MODELS`
- `REFERENCE_EXECUTION_REQUIRES_EXACT_R13_WORKTREE`

The active Alembic version directory contains only
`baseline_r13_0059.py`. The archived revisions are retained for byte-level
provenance and are intentionally not discovered by Alembic.
