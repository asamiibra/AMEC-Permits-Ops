# Vercel Project State

Read from the authenticated Vercel dashboard without changing settings.

| Field | Observed value |
|---|---|
| Team | `Ahmed Sami's projects` |
| Plan | `Hobby` |
| Project | `amec-permits-ops` |
| Project ID | `prj_VFnILYm6UhREXZMV0h3ltXVz2nC4` |
| Git repository | `asamiibra/AMEC-Permits-Ops` |
| Production Branch | `main` |
| Project Root Directory | `frontend` |
| Framework preset | `Other` |
| Frontend build | repository `frontend/package.json` `npm run build` |
| Frontend config | `frontend/vercel.json` |
| Production domain | `https://amec-permits-ops.vercel.app` |
| Backend project | `amec-permits-ops-backend` |
| Backend project ID | `prj_qZ3NPWcODQDA8ukyhdC3NprMcIKi` |
| Backend alias | `https://amec-permits-ops-backend.vercel.app` |
| Backend config | `backend/vercel.json`, FastAPI, `python3 scripts/vercel_data_bootstrap.py` |

Current Production points to READY deployment `DfTQUvNBRV8u27CbpTP33tyjj6FB`, source branch `main`, source SHA `e02e033c4e7f5138cca99e5d8bb9f1651f22de5c`. The latest historical Production attempt shown in the dashboard is blocked because its commit author email is the invalid `.local` address. No settings were changed during this recovery.

The current release branch is `branch/owner-form-simple-dashboard`, which is not the configured Production Branch. A direct Production promotion would therefore require an approved CLI/source path or a normal merge/promotion policy; neither is used while the quota guard is blocked.

Backend Production currently points to READY deployment `DzTxceqwQekJUzFxQPbwnCc8J2im`, source branch `main`, source SHA `2ab7532d338edac05c8d5579ccb6700998f516af`. Its Production variable names include `DATABASE_URL`, `APP_ENV`, `SYNTHETIC_ONLY`, `STORAGE_PROVIDER`, and `RELEASE_SHA`; all values remain secret and were not read.
