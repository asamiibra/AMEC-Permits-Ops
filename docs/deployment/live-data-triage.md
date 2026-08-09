# Live data triage

Verification date: 2026-08-09 UTC. Production aliases checked:

- Frontend: `https://amec-permits-ops.vercel.app`
- Backend: `https://amec-permits-ops-backend.vercel.app`

## Classification

The initial live behavior was **Branch B: schema exists but the core database was empty**.

- The direct backend health endpoint was reachable and the API returned JSON.
- Repeated direct probes of `/api/projects`, `/api/applications`, and `/api/dashboard` returned `200` with an empty project/application set and all-zero dashboard values. One early `/api/projects` probe returned a transient `500`; subsequent probes were stable and empty.
- `/api/office` returned `503` with `Seed office not found`, which was consistent with missing seed rows rather than missing route code.
- The frontend proxy returned the same empty JSON responses, so the frontend was not masking a populated backend.
- The repository migration metadata and model tables existed; this was not Branch A.

Branches C and D were not the final cause. After the safe bootstrap, health reported PostgreSQL, a valid connection, durable storage, and no SQLite fallback; the direct and proxy APIs returned the canonical four-project fixture.

## Remediation and evidence

The deployed build now runs `backend/scripts/vercel_data_bootstrap.py`. It refuses to reset a non-empty database, permits only the known synthetic browse-audit residue, verifies the current canonical manifest, ensures the migration head, and seeds only when the canonical fixture row is absent. It never prints `DATABASE_URL` or any credential.

The successful bootstrap log for deployment `dpl_vG889VrShs6Mqf2LXyvP3KgFPkUS` cloned commit `54ea216` and reported:

```text
Context impl PostgresqlImpl.
Running stamp_revision  -> 0021_e7_unified_task_context
synthetic_bootstrap=seeded fixture=PermitOps_Synthetic_MVP_Dataset_v1 migration=stamp_head_existing_current_schema projects=4 applications=4
```

The `stamp_head_existing_current_schema` action was deliberate: the existing tables matched the current SQLAlchemy metadata, there were no Alembic version rows, and the only pre-seed data was synthetic `DEV_USER` / `ROLE_FILTER_APPLIED` audit residue. No core data was deleted or regenerated locally.

## Final live state

`/health` reports `database_dialect=postgresql`, `database_durable=true`, `sqlite_fallback_active=false`, `database_connection_valid=true`, and Alembic version `0021_e7_unified_task_context`. `/api/projects` and `/api/applications` each return four canonical rows. The frontend proxy is JSON-equivalent to the direct backend on the verified routes.

All data is synthetic and scoped to the AMEC/QEC-DOHA demonstration office. No real permits, personal data, or production authority records were used.
