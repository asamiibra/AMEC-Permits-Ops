# Deployed Stack Verification

Final production verification on 2026-08-09 passed against the exact aliases `https://amec-permits-ops.vercel.app` and `https://amec-permits-ops-backend.vercel.app`.

The backend health endpoint returns 200 with durable Neon PostgreSQL, no SQLite fallback, and Alembic `0025_permit_workflow_stage_confirmation`. `/api/work`, `/api/issues?persona=OWNER`, `/api/notifications?persona=OWNER`, proposal/contract/project/permit lineage routes, and `/api/admin/summary` all return 200 JSON. The final frontend deployment is `dpl_ES4KvUzAsWcDGEtcDqf7SQJPsYLq`; the final backend deployment is `dpl_AhTpoekhRAcrZiret6xnQKNv6jbF`.

Fresh browser verification found no raw errors, material 500s, fake empty states, cross-project violations, or secret exposure.
