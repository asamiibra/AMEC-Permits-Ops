# Real-stack browser E2E

Status: `IMPLEMENTED_AND_VERIFIED`

Command:

```text
VITE_API_URL=http://127.0.0.1:8000 npm run browser-real-stack -- --workers=1 --grep "BD Proposal Forms-Driven v2|Dashboard V2|home exposes|captures sanitized visual evidence"
```

Environment: real Vite frontend, real Uvicorn backend, PostgreSQL database `bd_v2_full_pg_20260813_c`, Alembic `0042_bd_proposal_forms_driven_v2`, synthetic-only data, real API/RBAC headers, CORS origins configured for local browser testing.

Result: `5 passed` — BD Proposal workspace, Dashboard V1/V2 seam, non-owner redirect, sanitized split screenshots, and Dashboard V2 governance detail. Evidence: `artifacts/bd-proposal-forms-driven-v2/proposal-workspace.png` and the existing sanitized Dashboard V1/V2 artifacts.

The first local attempt without `FRONTEND_ORIGINS` was blocked by expected CORS configuration; the rerun with the documented local origins passed. No real PII or real government form data was used.
