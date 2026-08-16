# API and PostgreSQL smoke

Representative deployed read-only API checks cover Work, Issues, Proposals & Contracts, Engineering, Permits, Construction, Completion, Handover, Billing, and Master Content. `/health` must report `database_dialect=postgresql`, `database_durable=true`, `sqlite_fallback_active=false`, `database_connection_valid=true`, and a present Alembic state. No credentials or connection strings are recorded.
