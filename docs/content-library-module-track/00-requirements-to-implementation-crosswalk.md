# Content Library requirements-to-implementation crosswalk

Run: `RUN_CONTENT_LIBRARY_REQUIREMENTS_TO_IMPLEMENTATION_GAP_CLOSURE`

Frozen module base:

- branch: `module/content-library`
- SHA: `96bb23378d3a78855a315ea751e2b3b66839cb02`
- tree: `34350399d5a113f4d2a21f728b1220f9c39c48f3`
- integration target: `next/module-integration` (read-only)

This is the required read-only audit result. The implementation status is
classified from executable code and the focused test suite before this file
was written. No application or database code was changed to produce the
audit.

## Classification key

- `PASS_IMPLEMENTED`: executable behavior and focused evidence agree.
- `PARTIAL`: a required behavior exists but has a material unclosed path.
- `GAP`: required behavior is missing or accepts an unsafe state.
- `EVIDENCE_GAP`: behavior may exist, but this run lacks complete proof; it is
  not authorization to redesign the product.
- `SUPERSEDED`: historical requirement or implementation is replaced by the
  current accepted architecture.
- `NOT_APPLICABLE`: the requirement is outside this module's governed scope.
- `BLOCKED`: verification requires prohibited external state or new authority.

## Crosswalk

| ID | Requirement | Source | Current implementation / evidence | Current status |
| --- | --- | --- | --- | --- |
| CL-001 | Content Library is one governed discovery/reuse projection containing Forms, Reports, Engineering Works, and Definitions; it is not an operational system of record. | Owner architecture invariant; original track §§6, 11 | `master_content_routers.py`, `master_content.py`, `Dashboard.tsx`, and `MasterContentForms.tsx` expose the four libraries and canonical read projection. | PASS_IMPLEMENTED |
| CL-002 | Checklist remains a reusable Form; operational project checklists remain downstream projections of canonical project requirement items. | Owner architecture invariant; original track §12 | Forms API/UI uses `content_type=FORM`; no separate Checklist master library was found. Project requirement/checklist paths remain outside Content Library. | PASS_IMPLEMENTED |
| CL-003 | Forms list/search/filter/open/create/metadata/version/history/current/download/category/reference/status/Used In are governed and persisted. | Original track §12 | Canonical forms API/UI and `test_dashboard_forms_governance_wave_a.py`, `test_owner_dashboard_master_content.py`, `test_dashboard_master_content_v2.py`. | PASS_IMPLEMENTED |
| CL-004 | Reports have the same controlled lifecycle and canonical storage/version behavior. | Original track §13 | Report create/version/history/download/governance paths are present; focused owner and convergence tests pass. Downstream report dependency uses `MasterContentDependency`. | PASS_IMPLEMENTED |
| CL-005 | Engineering Works preserve executable source-type and discipline taxonomies and resolve through canonical current versions. | Owner architecture invariant; original track §14 | `ENGINEERING_SOURCE_TYPES`, `ENGINEERING_DISCIPLINES`, canonical candidate resolver, proposal Engineering reference path, and focused consumer tests pass. | PASS_IMPLEMENTED |
| CL-006 | Definitions support unique term, canonical reference, revision concurrency, immutable history, persona visibility, audit, and consumer lookup. | Original track §15 | Most behavior exists and stale revision protection is tested. Revision rename can collide with another active term; lookup/revision/binding endpoints bypass the existing persona visibility predicate. | PARTIAL |
| CL-007 | Category create/update enforces allowed content types, active state, order, source kind, duplicate prevention, RBAC, and audit. | Original track §16 | Create validates content types and duplicates; update assigns `allowed_content_types` without validating the values. | GAP |
| CL-008 | Reference policy and allocation cover FORM, REPORT, ENGINEERING_WORK, and DEFINITION with collision safety, non-renumbering, and auditable policy changes. | Original track §17 | Sequence allocation and master-content collision protection exist; Definition refs have no application-level collision check, and explicit policy prefix whitespace is not rejected. | PARTIAL |
| CL-009 | Active Used In/module bindings must be content-type compatible and purpose-compatible; invalid bindings fail closed and inactive bindings cannot become authoritative. | Owner architecture invariant; original track §§18–20 | Generic module/usage allow-lists exist, but master and definition binding routes do not enforce `CONTENT_TYPE_MODULES` or `PURPOSE_CONTENT_TYPES`. A REPORT can be bound to `PROPOSAL_TEMPLATE` and the API accepts it. | GAP |
| CL-010 | Purpose resolver exposes only actual governed purposes, preserves canonical truth, and fails closed for invalid purpose/module combinations. | Original track §19 | Resolver uses canonical candidates and rejects unauthorized persona access, but binding validation is too permissive and invalid purpose/module input is not explicitly rejected. | PARTIAL |
| CL-011 | Consumer resolver and actual downstream paths use `DASHBOARD_MASTER_CONTENT`, exact current version, and deterministic ambiguity behavior. | Original track §20 | BD proposal and Engineering paths use canonical candidates; focused convergence/resolution tests pass. Consumer route has only BD/Admin mappings and relies on the permissive binding layer. | PARTIAL |
| CL-012 | Versioning preserves old bytes/metadata, current pointer, change reason, actor, timestamps, and audit. | Original track §21 | Controlled Document/DocumentVersion promotion and historical download tests pass for Forms, Reports, and Engineering Works. | PASS_IMPLEMENTED |
| CL-013 | Dependency registration pins the bound version; current-version change marks downstream stale; revalidation is explicit and auditable. | Original track §22 | Service propagation, lineage, and revalidation are implemented and tested. Mutation routes do not require a Content Library dependency capability. | GAP |
| CL-014 | Governance, provenance, quality, currentness, source sections, readiness, and restricted-sample controls persist and authorize correctly. | Owner architecture invariant; original track §§23–24 | Governance/provenance/quality/readiness routes and focused tests pass. Source sections pin item/version but accept malformed PAGE_RANGE values such as missing/negative/reversed page ranges. | PARTIAL |
| CL-015 | Retrieval applies status/currentness/module/purpose/quality/readiness constraints where applicable; ranking never creates authority. | Original track §25 | Canonical read and candidate resolver enforce current/reviewed/source/readiness conditions. `/eligible` applies lifecycle checks but not role, binding, purpose, or currentness scope. | PARTIAL |
| CL-016 | AI assistance cannot approve/sign/stamp/release/final-submit, fabricate provenance, or bypass RBAC; deferred AI is safe. | Owner architecture invariant; original track §26 | AI assist endpoint returns `AI_ASSIST_NOT_ENABLED`; UI controls are disabled/marked deferred. | PASS_IMPLEMENTED |
| CL-017 | Owner, Business Development, and Engineering persona visibility is enforced by server capability and applicable module scope; forbidden writes do not persist. | Owner architecture invariant; original track §27 | Canonical reads and write capability matrix are present; focused unauthorized-write tests pass. Definition secondary read endpoints and dependency mutations have visibility/capability gaps. | PARTIAL |
| CL-018 | Reusable master content cannot silently become project/client truth or vice versa; actual Technical Reports remain controlled project artifacts. | Owner architecture invariant; original track §28 | Content Library stores governed master records; project artifact and proposal/permit consumers maintain separate models/lineage. | PASS_IMPLEMENTED |
| CL-019 | Storage bytes, checksum, version pinning, missing-blob behavior, and audit are proven without production/real-data mutation. | Original track §§29–30; execution correction | Synthetic adapter and isolated SQLite tests prove upload/read/download/failure behavior. Production/preprod/Azure/DSM/real AMEC state was not touched. | PASS_IMPLEMENTED |
| CL-020 | Negative matrix covers unauthorized writes, invalid category/reference/binding/purpose, stale revisions, unsafe dependency, invalid source section, and protected AI behavior with persisted-state checks. | Original track §31 | Existing focused suite covers most lifecycle/authorization cases; the newly identified invalid binding, dependency authorization, definition secondary visibility, and locator cases lack complete proof. | PARTIAL |
| CL-021 | Historical Content Library branches are reconciled semantically and are not wholesale cherry-picked. | Execution correction; original track §§2, 9 | 18 `branch/content-library-*` refs were inventoried. Current baseline already contains the relevant canonical dashboard, retrieval, consumer, lineage, and UI behavior; governed prefill/Azure work is out of module scope. | PASS_IMPLEMENTED |

## Historical unique-change disposition

| Historical area | Disposition |
| --- | --- |
| Canonical dashboard/discovery, owner product, retrieval-quality, consumer-resolution/convergence, lineage, and purpose-UI changes | ALREADY_INTEGRATED_SEMANTICALLY |
| Governed prefill/draft-apply changes | SUPERSEDED (downstream operational authority/project-artifact scope, not Content Library implementation) |
| Azure/preprod integration and shared P0 repair changes | NOT_APPLICABLE / UNSAFE_TO_REINTRODUCE for this isolated module run |
| Commissioning-prep evidence | HISTORICAL_EXPERIMENT_ONLY / evidence retained, no wholesale replay |

## Authorized implementation set

Only `GAP` and `PARTIAL` rows with a concrete code/test closure are in scope:

1. validate category updates and reference policy input;
2. centralize and enforce content-type/module/purpose binding compatibility;
3. authorize dependency registration and revalidation through explicit Owner/System Admin capabilities;
4. apply definition visibility to secondary reads and lookup, and prevent term collisions on revision;
5. validate source-section locators;
6. make eligible retrieval use governed module/role/currentness constraints;
7. retain the verified Content Library UX surfaces; no frontend change is authorized because the suspected duplicate table/error markup is absent at the frozen tree.

No migration, production/preprod/Azure/Entra/DSM/real-data mutation, authority action, AI enablement, project artifact redesign, or integration-branch change is authorized by this crosswalk.
