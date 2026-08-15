# Vercel Network Trace

Production backend probe before frontend deployment:

- Frontend: `https://amec-permits-ops.vercel.app`
- Backend: `https://amec-permits-ops-backend.vercel.app`
- Backend health: PostgreSQL, migration `0058_source_intake_ledger`, release SHA `e3b488f122ea82b15e7572e8be375e165c3207c7`.
- Frontend browser trace before deployment: failed the new redirect/current-surface assertions, proving the deployed frontend was stale.

The post-deployment trace is written to `artifacts/dashboard-v2-promotion/vercel-network-trace.json` only after the promoted frontend is actually deployed and probed.
