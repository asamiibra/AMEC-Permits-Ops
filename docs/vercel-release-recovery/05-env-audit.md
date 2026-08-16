# Vercel Environment Audit

Names and scopes only were inspected. Values and secrets are not recorded.

## Frontend project

The dashboard shows Neon-managed PostgreSQL variable names in Production, including `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `DATABASE_POSTGRES_URL`, `DATABASE_POSTGRES_URL_NON_POOLING`, `DATABASE_PGHOST`, `DATABASE_PGHOST_UNPOOLED`, `DATABASE_PGDATABASE`, `DATABASE_PGUSER`, `DATABASE_PGPASSWORD`, `DATABASE_POSTGRES_USER`, `DATABASE_POSTGRES_PASSWORD`, and provider/project identifiers.

Frontend API routing is bounded in `frontend/vercel.json` to `https://amec-permits-ops-backend.vercel.app/api/:path*`; no frontend secret is required for this rewrite.

## Backend project

The separate `amec-permits-ops-backend` project was inspected. Production contains `DATABASE_URL`, `APP_ENV`, `SYNTHETIC_ONLY`, `STORAGE_PROVIDER`, and `RELEASE_SHA`. `APP_ENV` and `SYNTHETIC_ONLY` are present in Production and Preview; the other listed variables are present in Production. Values remain secret and were not read.

Current classification for this recovery:

| Category | Status | Evidence |
|---|---|---|
| PostgreSQL connection | PRESENT | `DATABASE_URL` in backend Production and Neon-managed frontend names |
| API routing/base | PRESENT | `frontend/vercel.json` rewrite |
| Synthetic environment mode | PRESENT | `APP_ENV`, `SYNTHETIC_ONLY` in backend Production and Preview |
| Authentication/session | UNKNOWN | no required project variable identified in frontend project |
| CORS/origins | UNKNOWN | code defaults/settings; no backend project scope read |
| Document-storage mode/provider | PRESENT | `STORAGE_PROVIDER` in backend Production; value not read |
| Cron/job auth | NOT APPLICABLE | no cron configured in local project config or dashboard evidence |

Because quota is blocked, no environment-variable mutation is performed.
