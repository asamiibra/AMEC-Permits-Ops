# Rollback

Rollback target is the last known READY production deployment for each project, using the Vercel project deployment list/alias controls. Roll back frontend and backend together so the API route contract and frontend bundle remain aligned.

After rollback, verify `/health`, Alembic head, `database_dialect`, `sqlite_fallback_active`, storage mode, and the Dashboard/browser smoke path. Do not roll back environment policy independently: `APP_ENV`, `SYNTHETIC_ONLY`, `DATABASE_URL`, `STORAGE_PROVIDER`, and `RELEASE_SHA` must be reviewed with the selected deployment. A rollback does not verify real Synology, DSM, or AWS readiness.
