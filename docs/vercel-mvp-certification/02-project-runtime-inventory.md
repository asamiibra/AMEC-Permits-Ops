# Project and runtime inventory

Frontend project: `amec-permits-ops`, root `frontend`, Node 24.x, build `npm run build`, output `dist`, production alias `https://amec-permits-ops.vercel.app`.

Backend project: `amec-permits-ops-backend`, root `backend`, Node 24.x project setting, FastAPI framework configuration from `backend/vercel.json`, production alias `https://amec-permits-ops-backend.vercel.app`.

Backend production environment is `APP_ENV=TEST`, `SYNTHETIC_ONLY=true`, PostgreSQL-backed, with explicit `STORAGE_PROVIDER=mock`. No real Synology credentials or real Owner documents are present.

The CLI/project inspection did not expose the team billing plan or a separate Fluid Compute switch; those are recorded as not independently asserted.
