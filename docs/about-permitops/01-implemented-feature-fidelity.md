# Implemented-feature fidelity contract

The About page is data-driven from `frontend/src/AboutPermitOps.tsx`. The following status enum is used:

- `IMPLEMENTED`: current runtime and tests support the business capability in the current environment.
- `IMPLEMENTED_PROTOTYPE`: current synthetic runtime works, but production authorization or external integration is not approved.
- `FOUNDATION_ONLY`: shared model/service/evidence exists without a complete business workflow.
- `PLANNED_PENDING_SCOPE`: requirement or design is not complete or not selected for scope.
- `EXCLUDED`: explicitly unavailable in the current environment.
- `NOT_APPLICABLE`: irrelevant to the current scenario.

## Fidelity register

Each feature rendered in the catalog carries `id`, English and Arabic copy, `status`, `evidence`, and optional `route`. The evidence strings point to the following executable or inspectable proof classes:

| Feature families | Runtime/UI evidence | Test/evidence class | User-facing status |
|---|---|---|---|
| Project onboarding, Synology/source links, document registry/versioning, ownership | Project register, `ExternalSystemLink`, document APIs, ownership/form APIs | canonical fixture, Week 2 tests | Implemented in prototype |
| Classification, extraction, keyed fallback, conflicts, verification, lineage | Week 2 document console/API, `FieldObservation`, `VerifiedAssertion`, conflict routes | Golden Path v1, Week 2/8 tests | Implemented in prototype |
| Requirements, validity, drawing controls, readiness, human gates | Week 4–5 pages/APIs, configuration and readiness services | Week 4–5, Week 10, acceptance rehearsal | Implemented in prototype |
| Forms, Excel projection, manifest, attachments, grids | Week 4–5/9 pages and APIs, mock Excel adapter | Week 9 and supported coverage | Implemented in prototype |
| Municipality preparation, reconciliation, read-back, takeover | Week 4–5 page, snapshot/reconciliation contracts, attended metadata | Week 9–12 evidence | Implemented in prototype |
| Precheck, findings, ownership, closure, human handoff | Week 7/10 pages and APIs, `Finding`, `WorkflowTask`, `NotificationEvent`, `SubmissionHandoff` | Golden Path v2, Week 7/10 tests | Implemented in prototype |
| Monitoring, My Work, history, lineage, staleness | Week 11–14 APIs, `MyWorkPage`, `LineageValidityPage`, audit projections | workflow-first, Week 8/11–14 tests | Implemented / implemented in prototype |
| RBAC, attended MFA boundary, fail-closed/synthetic separation | App role selector, role contracts, safe boundary banner, safety counters | role readiness and production evidence | Implemented in prototype |
| Four assistants | `UnifiedMyWorkPanel`, shared task context, expansion unified runtime | E7/E8 acceptance | Implemented in prototype, bounded |
| RFQ/quotation/contract/finance/handover | Expansion entities and foundation/runtime only | E1 expansion evidence | Foundation only |
| Live authority write, machine final submit, payment/signing/certification | No supported production route by contract | README safety boundary, zero-tolerance counters | Excluded / unavailable here |

The exact feature count is calculated in code from the status enum; it is intentionally not a hard-coded claim.

