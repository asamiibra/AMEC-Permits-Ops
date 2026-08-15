# PostgreSQL

Production health reported `database_dialect=postgresql`, `database_durable=true`, `database_connection_valid=true`, and `sqlite_fallback_active=false`. Vercel environment inventory identifies the connected PostgreSQL integration as Neon; secret values were not emitted.

Alembic health reported `0058_source_intake_ledger`. The exact server version, physical region, and TLS session flag were not exposed by the deployed health contract or masked Vercel environment listing, so they are not overclaimed here. PostgreSQL durability and migration state are certified; provider-region/TLS metadata remains an observability limitation.
