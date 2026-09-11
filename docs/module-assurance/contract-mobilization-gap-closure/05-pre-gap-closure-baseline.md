# Pre-gap-closure baseline repair status

## Chronology

1. `module/contract-mobilization` remains the sealed historical first audit at `32b527e5d39b692d806d38014e26271715efe44f`; its FAIL/BLOCKED evidence is unchanged.
2. `module/contract-mobilization-gap-closure` is the bounded CM15/CM16 repair branch based on that exact audit tip.
3. This run revalidated the bounded repair and investigated local reproducibility before the deeper Owner program.
4. The newer `CM-G01..CM-G17` Owner / Execution-Contract program remains pending and is not implemented here.

## Hygiene

- The shared checkout was on an unrelated branch and was not mutated.
- The isolated branch's `.git/index.lock` was inspected; stale locks were removed only after no active task-owned Git process remained. It is not tracked as source.
- The isolated clone contains truncated promisor packfiles. Source files and the final commit tree remain available, but ordinary Git status/log/tree traversal is not a reliable verification mechanism in that clone.
- No release, pre-production, production, Entra, DSM, DNS, or real AMEC data access/mutation occurred.

## Current revalidation

```text
FRONTEND_BUILD=BLOCKED
WIDER_REGRESSION=BLOCKED
CM15=PASS
CM16=PASS
EXECUTED_EVIDENCE=PASS
INDEPENDENT_PERSISTENCE=PASS
BROWSER_E2E=PASS
LOCAL_BRANCH_REPRODUCIBLE=false
EXTERNAL_ENVIRONMENT_ACCEPTANCE=DEFERRED_TO_GOVERNED_RELEASE_TRAIN
NEW_OWNER_GAP_PROGRAM_PENDING=true
```

## Bounded blockers

### Frontend production build

Command: `npm run build` (`tsc -b && vite build`). A bounded rerun timed out after 20 seconds before completion. The earlier Vite trace stalled while reading/copying the tracked `frontend/public/brand/amec-logo-master.png`; subsequent typecheck/build startup also encountered the isolated clone's truncated Git/promisor-pack and local filesystem I/O stall. No source/configuration change was made to hide the problem. Classification: `LOCAL_MACHINE_ONLY_DEFECT`, with `SOURCE_BUILD_DEFECT=false` currently unproven until a clean worktree reproduces the build.

### Wider regression

Command: `PYTHONPATH=. pytest -q backend/tests`. The run progressed through passing tests, then a task-owned leftover `test_billing_invoice_full.py` process remained active for over a minute; the broader invocation was stopped after the local process/filesystem stall. No test was skipped, xfailed, or marked PASS because of the interruption. Classification: `LOCAL_ENVIRONMENT_DEFECT` pending a clean process invocation.

## Baseline gate

This branch is **not** declared a clean pre-deep-gap-closure baseline. The required next action is to run the frontend and backend checks from a genuinely clean, healthy isolated clone/worktree, then update this document with exact versions, counts, duration, and final result. The deeper CM-G01..CM-G17 implementation must not begin from this blocked baseline.
