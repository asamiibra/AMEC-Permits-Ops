# Neon/deployment verification

Deployment acceptance must record the actual Alembic head rather than assume
0022. The new local head is `0023_backend_realign_reference_metadata`.
Production verification must show PostgreSQL dialect, valid Neon connection,
fallback disabled, synthetic-only fixture, direct API/detail/KPI responses and
matching frontend proxy responses without emitting secrets.
