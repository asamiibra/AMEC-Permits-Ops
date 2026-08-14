# SQLite and generated DB hygiene

SQLite full suite: 175 passed, 1 skipped, 2 warnings in 19.26 seconds. The skip is the existing PostgreSQL row-lock-only proof; its equivalent PostgreSQL test passed. The harness now uses an absolute PID-scoped temp path. Only pre-existing deliberately tracked synthetic/dev DB fixtures remain in the repository.
