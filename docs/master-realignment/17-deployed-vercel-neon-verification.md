# G11 — Deployed Vercel / Neon verification

Verification date: 2026-08-09.

Frontend: `https://amec-permits-ops.vercel.app`, production deployment `dpl_D3uiiBqE3fG2gMa8hKz5Y8MvGQjV`, READY. Backend: `https://amec-permits-ops-backend.vercel.app`, production deployment `dpl_4D6gDnf2W9mwWvei7HK37oQebpA8`, READY. Public runtime probes do not expose a Git SHA; the deployment IDs are recorded instead and no secret environment values were retrieved.

Backend `/`, `/health`, `/docs`, and `/openapi.json` returned the expected JSON/Swagger responses. Material direct API routes and frontend proxy routes returned 200 JSON. The health payload reports `database_dialect=postgresql`, `database_durable=true`, `sqlite_fallback_active=false`, a valid connection, and Alembic `0022_proposalops_master_realignment`.

The four canonical projects and four applications are present. The idempotent bootstrap repaired the known synthetic ProposalOps fixture binding so `SYN-OPP-0001` is canonical to `GHCE-2026-0142`, its Contract is linked to that Project, and the Permit controls the Contract. The deployed fixture still has no captured early-stage source artifacts, so it is not yet the completed deployed G11 source-to-promotion fixture.

Result: deployed infrastructure, migration, API, proxy, and fixture-link gates pass. The overall deployed G11 gate remains open until the deployed source-intake/promotion and complete Owner/BD/Engineering paths are run against real Neon-backed records.
