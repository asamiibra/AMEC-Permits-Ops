# E0/E1 entry baseline

## Repository state

No Git metadata is present under the workspace or its immediate parent, so Git commit/status state is unavailable. The repository uses FastAPI/SQLAlchemy, Alembic, SQLite test fallback, native PostgreSQL target validation, and React/TypeScript/Vite.

## Runtime and migration baseline

- Repository migration head before E1: `0015_week14_acceptance`.
- Configured local `permitops.db` migration before E1: `0006_confirmation_binding`.
- PostgreSQL: 16.14, available and accepting connections.
- Accepted PostgreSQL pre-G10 evidence: `permitops_pre_g10`, migration `0015_week14_acceptance`.
- E1 migration: `0016_stage1_v2_6_expansion_foundation`.

## Fixture and governance baseline

- Permit fixture: `PermitOps_Synthetic_MVP_Dataset_v1`, v1.1.1.
- Permit manifest hash: `b3a5fbee1a968e3740801b0b696b31a39a3a907437f2377fcdfdfad3bb3546cb`.
- Original A12 registry: 20 rows.
- Active display label: `AMEC Engineering`.
- Stable historical IDs: `GHCE-*` retained as synthetic fixture lineage and compatibility IDs.

## Existing reusable controls

The repository already contains Project, Document, DocumentVersion, FieldObservation, VerifiedAssertion, FieldAuthorityRule, TargetRenderingRule, ApprovalDependency, DocumentValidity, Approval, WorkflowTask, NotificationEvent, AuditEvent, LineageEdge, MaterialChangeEvent, Finding, FindingResolution, Package, PreparationRevision, AuthorityPrecheckRun, and PortalSnapshot. `EvidenceArtifact` was not present as a concrete model, so E1 adds it once as a shared evidence pointer rather than creating domain-specific evidence tables.

## Existing regression commands

`make test`, `make migrate`, `make seed`, `make canonical-fixture-check`, `make golden-path-v1`, `make golden-path-v2`, `make acceptance-rehearsal`, `make pre-g10-reconcile`, `make registry-safety`, `cd frontend && npm test -- --run`, `cd frontend && npm run build`, and `cd frontend && npm run browser-e2e`.

## Conflicts and blockers

The only baseline conflict is the stale local SQLite migration version versus the repository migration head; it is an environment-state discrepancy and does not justify rewriting migration history. No signed Stage 2 approval, production authorization, or external-system access is present.
