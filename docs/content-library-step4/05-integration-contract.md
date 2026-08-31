# Future integration and commissioning contract

The later execution must create a new integration branch from the accepted
Azure deployment baseline:

```text
INTEGRATION_TARGET_SHA=<accepted immutable Azure-preprod source SHA>
CONTENT_LIBRARY_SOURCE_SHA=46934d09c7df8c5a5b40e604ee9537e303273df1
CONTENT_LIBRARY_DELTA_BASE=0dd403fbf3f3100f283cd1ee1274465ded81998c
```

Required resulting behavior:

- Azure Entra/managed-identity SQL behavior and accepted migration head remain
  intact;
- `synthetic_only=true`, no real AMEC data, and no real Synology;
- `/health/live`, `/health/ready`, DB, storage, and release provenance are
  directly verified;
- one canonical Master Content discovery service and one governed cross-domain
  retrieval contract remain separate;
- Forms, Reports, Engineering Works, Definitions, current/history, exact
  citations, access isolation, ambiguity/conflict state, and current consumers
  remain green;
- no retrieval persistence, external vector/search service, or protected AI
  action authority is introduced.

Execution order: verify target identity → apply semantic delta by matrix → run
pre-integration regression → run migration/readiness checks → run deployed
synthetic commissioning matrix → capture release/source/migration evidence.

Rollback boundary: before any external deployment, discard the new integration
candidate; after an authorized deployment, use the accepted prior Azure
release/digest and preserve the deployment ledger. This Step 4 performs none of
those mutations.
