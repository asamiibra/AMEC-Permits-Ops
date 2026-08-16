# API and PostgreSQL smoke

The existing backend production alias was observed separately: `/health` returned PostgreSQL, durable database, valid connection, and present Alembic state. Representative read-only API probes remain current-backend evidence only, not post-deploy evidence for `e5b916d`. No credentials or connection strings are recorded.
