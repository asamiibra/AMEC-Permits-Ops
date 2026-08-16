# Vercel project inventory

| Project | Root | Framework/build | Production alias |
|---|---|---|---|
| `amec-permits-ops` | `frontend` | Other; `npm run build`; output `dist`; Node 24.x | `https://amec-permits-ops.vercel.app` |
| `amec-permits-ops-backend` | `backend` | FastAPI; `python3 scripts/vercel_data_bootstrap.py`; Python 3.12 runtime; Node 24.x project setting | `https://amec-permits-ops-backend.vercel.app` |

Team/account: `Ahmed Sami's projects` (`ahmed-samis-projects-c4276939`). Project IDs: frontend `prj_VFnILYm6UhREXZMV0h3ltXVz2nC4`; backend `prj_qZ3NPWcODQDA8ukyhdC3NprMcIKi`.

The production alias is Git-integrated to `main`, but the established supported release path for this branch is authenticated Vercel CLI source deployment. The release ledger records the exact source SHA supplied to that deployment and any deployment metadata returned by Vercel.
