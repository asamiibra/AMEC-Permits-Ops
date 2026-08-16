# Environment-variable audit

Names only were inspected; no values are recorded.

Frontend Production contains PostgreSQL integration variables managed by Vercel, including `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `DATABASE_POSTGRES_URL`, `DATABASE_POSTGRES_URL_NON_POOLING`, `DATABASE_PGHOST`, `DATABASE_PGHOST_UNPOOLED`, `DATABASE_PGDATABASE`, `DATABASE_PGUSER`, `DATABASE_PGPASSWORD`, `DATABASE_POSTGRES_USER`, `DATABASE_POSTGRES_PASSWORD`, and provider/project identifiers. These are not used as frontend secrets in the browser bundle.

Backend contains `DATABASE_URL` (Production), `APP_ENV` (Production and Preview), `SYNTHETIC_ONLY` (Production and Preview), `STORAGE_PROVIDER` (Production), and `RELEASE_SHA` (Production). Deployed health confirms `APP_ENV=TEST`, `SYNTHETIC_ONLY=true`, PostgreSQL, and durable database connectivity. The runtime is synthetic; real Owner Synology is not configured.

Status: required database and synthetic-mode variables present for the deployed backend; public frontend API routing is supplied by `frontend/vercel.json` rewrites; no secret value is exposed in this evidence.
