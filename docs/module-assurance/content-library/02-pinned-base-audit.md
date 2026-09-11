# Pinned-base Content Library audit

Audit target:

```text
MODULE_RUN_BASE_SHA=96bb23378d3a78855a315ea751e2b3b66839cb02
MODULE_RUN_BASE_TREE=34350399d5a113f4d2a21f728b1220f9c39c48f3
ACTIVE_DEVELOPMENT_BRANCH=module/content-library-gap-closure-v1
INTEGRATION_TARGET=next/module-integration (read-only)
```

The branch was created directly from the exact pinned SHA after a read-only check that the requested branch name was absent locally and remotely. The dirty user checkout was not used. The remote release was inspected without mutation: `e6d214ee3af7ff4559d1d5234afaf59763f42924` (tree `ef63c78696aac2224a2b71200b87d33c10e07fba`) is a descendant of the pinned base and changes only bridge-intake/runtime files and its transport test. It does not touch Content Library files or Content Library dependencies. Therefore, at the initial audit timestamp, `REMOTE_RELEASE_ADVANCED=true`, `REMOTE_DELTA_CONTENT_LIBRARY_TOUCH=false`, `REMOTE_DELTA_CONTENT_LIBRARY_DEPENDENCY_TOUCH=false`, `REMOTE_DELTA_CONFLICT_RISK=LOW`, and `CONTENT_LIBRARY_BASE_SYNC_REQUIRED_AT_INITIAL_AUDIT=true`. The later closure revalidated and merged this same release tip; current `BEHIND_BY=0` and `CONTENT_LIBRARY_BASE_SYNC_REQUIRED=false` are recorded in the final acceptance documents.

## Current implementation map

The pinned base contains the governed Content Library projection in `backend/app/models/master_content_entities.py`, `backend/app/services/master_content.py`, `backend/app/api/master_content_routers.py`, `backend/app/services/forms_governance.py`, `backend/app/services/governed_retrieval.py`, and `backend/app/services/governed_prefill.py`. Persistence is shared through `Document`/`DocumentVersion`, master-content entities, source/provenance entities, dependency/change-event entities, and the existing Alembic graph. The frontend projection is in `frontend/src/Dashboard.tsx`, `frontend/src/MasterContentForms.tsx`, `frontend/src/masterContentUi.tsx`, and `frontend/src/contentLibraryApi.ts`.

The operational boundaries are present in the pinned base: project requirements and evidence use their owning records; Source18 owns official authority controls; `DocumentVersion` carries content lineage; Technical Reports and Engineering approval use project/engineering records; finance and correspondence use their own workspaces. No new parallel system is authorized.

## Architecture-invariant audit

| Failure mode | Pinned-base result | Evidence / disposition |
|---|---|---|
| duplicate MasterContent/content read engines | PASS | one `master_content` service plus governed retrieval seam |
| duplicate template engines | PASS | reusable definitions remain `MasterContentItem`/`DocumentVersion` |
| parallel Checklist library | PASS | checklist ownership remains Project Requirement Items |
| parallel Form version authority | PASS | official currentness remains Source18/DocumentVersion-owned |
| Content Library as Project evidence or requirement truth | PASS | owning-domain routes/models remain separate |
| arbitrary `master_content_id` bypass | PARTIAL | binding and consumer validation gaps are recorded as AT-063/AT-065 |
| AI-specific direct read bypass | PASS | AI route uses governed library boundary and protected-action denial |
| stale Form used for live governed use | PASS | current/reviewed version gates are present; live authority is Source18-owned |
| official Form collapsed with AMEC template | PARTIAL | typed seam exists; official projection ownership decision remains AT-080 |
| `AUTHORITY_ONLY` editable/prefillable | PASS | authority controls and adversarial prefill tests are present |
| BLANK treated as NOT_APPLICABLE | PASS | explicit state distinction is covered by governance tests |
| generic verified flag accepted as evidence-grade | PASS | VerifiedAssertion/evidence path is separate |
| Form template collapsed with operational packet | PASS | AuthorityCase/SubmissionPackage remain owning-domain records |
| submitted revision overwritten | PASS | immutable version/package path remains separate |
| Report template collapsed with Technical Report | PASS | project/engineering artifact path remains separate |
| Engineering Work treated as professional approval | PASS | approval/baseline routes remain Engineering-owned |
| MasterContent versioning competes with DocumentVersion | PASS | master items point to shared DocumentVersion lineage |
| contracts/invoices/payments become Content Library truth | PASS | finance/contract routes remain separate |
| checklist UI manually copied instead of projected | PASS | project checklist consumer seam remains canonical |

## Gap classification before implementation

The complete atomic ledger is `01-atomic-owner-requirements-audit.tsv` (81 atomic Owner obligations). At audit start it contains 46 PASS, 8 PARTIAL, 14 MISSING, 4 BLOCKED, and 9 NOT_APPLICABLE rows. The six product gaps below are the only application-code gaps identified from the pinned-base comparison with the validated direct-child implementation candidate `da0ace1f26b33ff021a8ba54d46b7bf094a9932d`:

| GAP_ID | REQ_ID | CLASS | SEVERITY | Pinned-base finding | Minimal closure |
|---|---|---|---|---|---|
| CLG-001 | AT-061 | CL_API_GAP | P1 | category allowed types were not validated against the four-library taxonomy | enforce allowed types and deduplicate |
| CLG-002 | AT-062 | CL_API_GAP | P1 | reference-policy prefix accepted unsafe values | enforce bounded reference-prefix grammar |
| CLG-003 | AT-063 | CL_API_GAP | P0 | bindings did not enforce content-type/module/purpose compatibility | validate every binding and reject duplicates |
| CLG-004 | AT-064 | CL_RESOLVER_GAP | P0 | resolver accepted values outside governed purpose vocabulary | fail closed on unknown module/purpose |
| CLG-005 | AT-067 | CL_RBAC_GAP | P0 | dependency write and revalidation routes lacked capability gates | require dedicated dependency capabilities |
| CLG-006 | AT-069 | CL_API_GAP | P1 | PAGE_RANGE source locators allowed incomplete/reversed ranges | require positive complete non-reversed bounds |

The evidence-only missing rows are not product redesign authority. They are run artifacts to be completed after implementation. The blocked rows remain blocked where the Owner source set does not provide a decision on official authority projection or live external evidence; they must not be silently promoted to PASS.

## Historical reconciliation

Historical `branch/content-library-*` work was inspected as evidence only. The prior Step-5 convergence result is `HISTORICALLY_RECORDED_COMPLETE`; no historical branch was wholesale merged. The six closure gaps map exactly to the validated direct-child candidate above, which is semantically compatible with the pinned architecture and is eligible for a narrow cherry-pick after this audit record.
