# Neon migration and seed report

Verification date: 2026-08-09 UTC.

## Runtime proof

The deployed backend health contract now exposes safe connection metadata. Live values were:

| Check | Result |
|---|---|
| `database_configured` | `true` |
| `database_dialect` | `postgresql` |
| `database_durable` | `true` |
| `sqlite_fallback_active` | `false` |
| `database_connection_valid` | `true` |
| Alembic version | `0021_e7_unified_task_context` |
| Environment | `TEST`, with `synthetic_only=true` |

Vercel production environment configuration contains `DATABASE_URL`, `APP_ENV`, and `SYNTHETIC_ONLY`. Sensitive values were not retrieved, printed, or committed. The deployed runtime rejects a SQLite URL when running on Vercel in a deployed TEST/PROD environment.

## Migration

Repository Alembic head: `0021_e7_unified_task_context`.

Before seeding, the database had no Alembic version rows but already had the current model tables from the prior safe schema initialization. The bootstrap verified that every current model table existed, then ran `alembic stamp head` rather than applying an unnecessary destructive or historical migration chain. The live build log recorded `stamp_head_existing_current_schema`, and the post-seed health check reports the repository head.

This is a schema-state stamp, not a claim that historical migrations were replayed against a blank database. It is safe for this baseline because the database was empty of core application data, the current tables matched `Base.metadata`, and the only existing rows were known synthetic role-filter audit events.

## Canonical fixture

- Fixture set: `PermitOps_Synthetic_MVP_Dataset_v1`
- Version: `1.1.1`
- Manifest hash: `b3a5fbee1a968e3740801b0b696b31a39a3a907437f2377fcdfdfad3bb3546cb`
- Office: `QEC-DOHA` / `AMEC Engineering`
- Projects: 4
- Applications: 4
- Canonical project numbers: `GHCE-2026-0142`, `GHCE-2026-0187`, `GHCE-2026-0210`, `GHCE-2026-0244`
- Canonical application numbers: `GHCE-APP-0142`, `GHCE-APP-0187`, `GHCE-APP-0210`, `GHCE-APP-0244`

The live application status distribution is DRAFT 1, RETURNED 1, UNDER_REVIEW 1, and APPROVED 1. The fixture truth is retained: findings, workflow tasks, and notifications are currently zero; dashboard readiness counts remain populated from the canonical seed.

## Safety and idempotency

The bootstrap refuses to reset any non-empty database except the explicitly allow-listed synthetic browse-audit residue. Once the canonical fixture row exists, it verifies the manifest and core counts and performs no seed reset. It runs as a Vercel build command, not on each serverless cold start. The first seeded deployment was `dpl_vG889VrShs6Mqf2LXyvP3KgFPkUS` from commit `54ea216`; a subsequent deployment is used as the no-op idempotency probe for the final verification.

Two build failures were resolved with the smallest scoped changes: the Vercel Python builder required `reportlab` in `backend/pyproject.toml` (`71a51ec`), and the bootstrap was narrowed to allow only the known synthetic audit residue (`54ea216`). No feature behavior was redesigned.
