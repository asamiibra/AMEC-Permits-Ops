# Cleanup and repository hygiene

The 20 repo-local generated SQLite databases were moved to recoverable quarantine at `/tmp/final-platform-closure-db-quarantine.dxsZBo` for the required zero-in-repository hygiene state. The temporary final audit PostgreSQL database is scheduled to be dropped. The generated Excel fixture is scheduled to be restored. No production data is deleted by this cleanup.
