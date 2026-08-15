# Vercel Network Trace

Production backend and frontend trace after the final deployment:

- Frontend: `https://amec-permits-ops.vercel.app`
- Backend: `https://amec-permits-ops-backend.vercel.app`
- Backend health: HTTP 200, PostgreSQL, durable database, migration `0058_source_intake_ledger`, release SHA `cfc5374b6183aba5c6522963789652ecc022763a`, build `dpl_He86XRGUjR7F1MFFpNNHYhN9LQGX`.
- Production API probes returned HTTP 200 for health, canonical Master Content Forms, governance catalogs/forms, Definitions, Inputs, AMEC Work, Projects, and Applications.
- Production browser acceptance passed all 6 promotion tests after deployment. The pre-deployment stale-frontend failures remain recorded as historical evidence.

The full structured trace is in `artifacts/dashboard-v2-promotion/vercel-network-trace.json`.
