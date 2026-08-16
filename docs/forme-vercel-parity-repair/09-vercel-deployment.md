# Vercel deployment

At repair entry, both production projects were READY at main SHA
`ba5089e40a9259dcc4a4d92cddf34bf5ccde0b29`. The backend health endpoint
reported PostgreSQL, Alembic `0058_source_intake_ledger`, durable synthetic
DB-backed storage, and `RELEASE_SHA=202728cb176d9ef561391531729b3d580a7837f0`.

Repair SHA: `4976034e91a10d8ef2950a6a1f56799905bea96e`.

The frontend deployment for the repair SHA reached `READY` and its production
alias was updated. The backend GitHub deployments for the same SHA reached
`ERROR`, and an explicit backend-root production deployment reached
`BLOCKED` (`dpl_GejGzr3kKJw5rNeHgJGXpv7T4gjQ`). Vercel reported empty build
output/config for those backend attempts, so there is no ready backend runtime
on the repair SHA to query.

`RELEASE_SHA` was configured on the backend production project to the exact
repair SHA, but the blocked deployment did not produce a runtime that could
load it. Therefore exact frontend/backend deployed SHA parity, deployed API
data proof, and browser parity remain blocked by the external Vercel backend
deployment state. No remote database seed was run while that gate was closed.
