# CM rescore — isolated module scope

The historical audit report remains unchanged on the parent assurance tip. This child records the gap-closure rescore without deleting or rewriting any prior FAIL/BLOCKED item.

| Control | Result | Basis |
|---|---|---|
| CM01–CM08 | PASS reused | Existing assurance results were not invalidated by this scoped change. |
| CM09 | PASS | Executed Contract evidence is a dedicated, persisted, exact-revision action; generic document upload cannot claim it. |
| CM10 | PASS | Evidence metadata, actor/time/hash/reference, audit event, independent DB read-back, and idempotency are tested. |
| CM11–CM14 | PASS reused | Existing assurance results were not invalidated. |
| CM15 | PASS | Exact Contract/Project/current-revision/accepted-revision/Project-Activation gate plus denial and duplicate tests. |
| CM16 | PASS | Read-only canonical Operations projection and browser rendering are implemented and tested. |
| CM17–CM27 | PASS reused | Existing assurance results were not invalidated. |
| CM28 | BLOCKED | Frontend dependencies, typecheck, Vitest baseline, and focused browser proof completed, but the required post-change Vite production build is blocked by the isolated clone's local tracked-static-file/filesystem failure. |
| CM29 | PASS reused | Existing assurance result was not invalidated. |
| CM30 | PASS — module-local | Matrix and isolated evidence are complete for module scope. Hosted release acceptance remains future evidence. |

## Classifications

- `MODULE_IMPLEMENTATION_GAP`: CM15 gate, CM16 projection, executed-evidence action/UI.
- `MODULE_TEST_GAP`: negative gate, evidence persistence/idempotency, and projection coverage added.
- `LOCAL_TOOLING_GAP`: post-change Vite static-public-file copy and wider pytest process stalled in this local filesystem; no release environment was used.
- `MODULE_BROWSER_PROOF_GAP`: closed by the focused synthetic Playwright test.
- `RELEASE_ENVIRONMENT_ACCEPTANCE`: not executed; requires a governed release train.
- `EXTERNAL_DEPENDENCY_ACCEPTANCE`: not executed; no external system was in scope.
- `UNKNOWN`: none remaining for the module-local controls above.

## Scope result

`MODULE_CODE_AND_ISOLATED_ACCEPTANCE` is incomplete only at CM28 because of the local tooling/build blocker. `FUTURE_RELEASE_HOSTED_ACCEPTANCE` remains separate and deferred.
