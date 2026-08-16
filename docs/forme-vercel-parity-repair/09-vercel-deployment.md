# Vercel deployment

At repair entry, both current production projects were READY at main SHA
`ba5089e40a9259dcc4a4d92cddf34bf5ccde0b29`. The backend health endpoint
reported PostgreSQL, Alembic `0058_source_intake_ledger`, durable synthetic
DB-backed storage, and `RELEASE_SHA=202728cb176d9ef561391531729b3d580a7837f0`.

The repair SHA has not yet been deployed in this evidence file. Frontend and
backend exact-repair SHA parity, backend RELEASE_SHA update, and deployed data
proof remain post-commit gates.
