# A1 pre-deployment hardening and release contract

This document is an executable-source contract. It authorizes no live Azure,
Entra, PostgreSQL, Synology, or real-data mutation.

`BACKEND_APP_SERVICE_HEALTH_CHECK=/health/ready`

`WORKER_SCHEDULE=LIVE_DEPLOYMENT_DECISION_PENDING`

`MIGRATION_ADMIN_SECRET_ISOLATION=LIVE_DEPLOYMENT_GATE`

`API_ACCEPTANCE_REQUIRES=DATABASE_MIGRATION_URL absent from runtime API environment`

## Execution identities

The worker is the only App Service WebJob. It is a triggered WebJob and
receives DATABASE_URL only.

Migration and database-role provisioning are isolated one-shot command
contracts:

    python -m backend.app.migrate
    python -m backend.app.provision_db_roles

They use DATABASE_MIGRATION_URL only, are not hosted under the backend
App Service WebJob identity, and do not produce a migration ZIP. The live
migration execution host and identity remain a later deployment gate.

## Release order

1. Accept the exact source SHA.
2. Run full tests and security scans.
3. Validate exact IaC and run what-if.
4. Obtain explicit Owner authorization for live mutation.
5. Register Entra applications and set `requestedAccessTokenVersion=2`.
6. Record exact HTTPS URLs and scopes.
7. Build frontend and backend once; test, scan, and generate SBOMs for those same images.
8. Push those immutable images to ACR and freeze their manifest digests.
9. Pass the Qatar PostgreSQL gate; create PostgreSQL 16 and establish a recovery point.
10. Migrate with the migration authority, provision the runtime role, and remove the migration credential from API runtime settings.
11. Bootstrap with the runtime role and provision only the protected synthetic Owner identity.
12. Deploy backend by immutable image identity, then the triggered worker WebJob, then frontend by immutable image identity. Migration/admin execution remains an isolated one-shot deployment contract and is not an App Service WebJob.
13. Run live Entra/token/browser E2E, readiness, telemetry/alerts, restart/persistence, PITR restore, and rollback drills.
14. Publish the final release manifest.

Azure App Service B1 has no deployment slots. Rollback is therefore a direct
immutable-image/configuration rollback; this contract makes no production
zero-downtime claim.
