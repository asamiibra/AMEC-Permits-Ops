# Deployment baseline readback

Read-only discovery found no accepted immutable Azure-preprod runtime handoff
that exposes an application SHA, frontend SHA, backend SHA, Azure revision, or
accepted deployment branch. The separate Azure lane currently exposes:

- SQL/token closure branch: `azure-preprod-sql-mi-token-closure-v1` at
  `02b797d323acafb754f579331d2d1dc022b647b2`;
- preview compatibility branch: `azure-preprod-preview-auth-cors-compat-v1` at
  `b6328317abc57d2b06b249e68dd9ad41d63ad6c1`.

Neither branch is adopted as a deployment target by naming convention.

The publicly reachable Vercel TEST health response was read only. It reported
PostgreSQL, synthetic-only mode, no SQLite fallback, and migration head
`0058_source_intake_ledger`. `/health/live` and `/health/ready` returned 404;
therefore this response is useful runtime evidence but not Azure-preprod
commissioning evidence. Frontend `/release.json` was not exposed.

Result: `CURRENT_DEPLOYMENT_BASELINE=DEPLOYMENT_BASELINE_PENDING_EXTERNAL_WORKSTREAM`.
The future `INTEGRATION_TARGET_SHA` remains unresolved until the separate lane
produces an accepted immutable deployment handoff.
