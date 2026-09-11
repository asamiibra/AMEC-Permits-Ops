# Unresolved Control Ledger

This ledger reproduces every prior `FAIL` or `BLOCKED` entry from the existing
`docs/module-assurance/contract-mobilization/13-cm01-cm30-ledger.md`. No control
was removed or redefined.

| CONTROL_ID | CONTROL_REQUIREMENT | PREVIOUS_RESULT | WHY_NOT_PASS | CODE_PATHS | TEST_PATHS | EVIDENCE_NEEDED | MODULE_LOCAL_OR_RELEASE_STAGE | IMPLEMENTATION_ACTION | CLASSIFICATION |
|---|---|---|---|---|---|---|---|---|---|
| CM09 | Executed Contract evidence/forms/signature policy is retained and distinct from Contract acceptance. | BLOCKED | Executed evidence/forms/signature policy was documented but not fully exercised. | `backend/app/api/contract_workspace_routers.py`; `backend/app/models/admin_contract_entities.py`; `backend/app/services/contract_workspace.py` | Existing Contract acceptance/evidence tests; new executed-evidence lifecycle tests | Exact Contract ID, exact ContractRevision, versioned executed evidence, human actor/time, audit lineage, and independent persistence reopen | MODULE_IMPLEMENTATION_GAP + MODULE_TEST_GAP | Add a fail-closed executed-evidence predicate/proof path without synthesizing a signature or conflating acceptance with execution. | MODULE_IMPLEMENTATION_GAP |
| CM10 | Executed Contract/form evidence delivery and retained evidence are independently verified. | BLOCKED | End-to-end executed-copy delivery/read-back was not exercised in the prior run. | `backend/app/api/contract_workspace_routers.py`; document storage/version models | New API/storage read-back tests | Response plus independent DB/document-version reopen and exact hash/reference verification | MODULE_TEST_GAP; hosted delivery remains release-stage | Exercise the existing versioned synthetic document path and expose exact evidence references in the Contract projection. | MODULE_TEST_GAP |
| CM15 | ServiceEngagement is created only under the exact accepted/current Contract revision and valid Contract/Project boundary. | BLOCKED | Existing endpoint checked parent existence but did not fully gate Contract acceptance/current revision or relationship. | `backend/app/api/handover_closeout_routers.py`; `backend/app/services/contract_workspace.py`; `backend/app/models/handover_closeout_entities.py` | `backend/tests/test_handover_admin_closeout.py`; `backend/tests/test_handover_final_closure_bridge.py`; new CM15 negative/positive tests | Denied API transition, zero forbidden row mutation, exact accepted revision, active Project Activation, relationship, audit result, replay behavior | MODULE_IMPLEMENTATION_GAP + MODULE_TEST_GAP | Enforce exact accepted current revision, activation, Contract/Project relationship, and fail-closed idempotency/replay behavior at the API boundary. | MODULE_IMPLEMENTATION_GAP |
| CM16 | Operations handoff/control surface consumes canonical Contract, Project, mobilization, schedule, risk, blockers, and next-action truth. | FAIL | Dedicated Contract/Mobilization Operations handoff and reconciled control surface were not implemented. | `backend/app/services/contract_workspace.py`; `backend/app/api/contract_workspace_routers.py`; canonical `WorkflowTask`, `Finding`, `NotificationEvent`, `ProjectActivation`, `ServiceEngagement` | Existing operations helper tests; new CM16 projection/RBAC/stale-state tests | Deterministic read model from canonical rows, no UI-authoritative writes, stale/closed/blocked and RBAC evidence | MODULE_IMPLEMENTATION_GAP + MODULE_TEST_GAP | Add a read-only Operations projection over canonical Contract/Project/Mobilization records and surface it in the Owner Contract workspace. | MODULE_IMPLEMENTATION_GAP |
| CM28 | Contract/Mobilization UI behavior is buildable and exercised in the supported local browser path. | BLOCKED | UI source was repaired, but dependencies were absent; frontend build/browser proof did not run. | `frontend/package.json`; `frontend/src/AdministrationOwner.tsx`; `frontend/playwright.config.ts` | Frontend unit/browser suites; new local module browser evidence | Lockfile-driven install, typecheck, frontend tests/build, isolated synthetic browser flow and persistence reconciliation | LOCAL_TOOLING_GAP + MODULE_BROWSER_PROOF_GAP; hosted proof is release-stage | Install the committed npm dependency contract in the isolated clone, run exact scripts, and add/run the bounded local browser proof. | LOCAL_TOOLING_GAP / MODULE_BROWSER_PROOF_GAP |
| CM30 | Complete existing CM matrix is re-scored, with module-local proof separated from hosted release acceptance. | BLOCKED | Full matrix and production/preprod/real external acceptance were not executed. | Existing CM assurance package; new gap-closure evidence | Full applicable backend/frontend/browser/regression suite | Exact CM01–CM30 re-score and explicit hosted deferral | RELEASE_ENVIRONMENT_ACCEPTANCE + MODULE_TEST_GAP | Re-score the unchanged controls with prior evidence where valid; report local module PASS separately from governed release-train acceptance. | RELEASE_ENVIRONMENT_ACCEPTANCE |

## Classification rule

The classifications used are exactly the mandate vocabulary:

```text
MODULE_IMPLEMENTATION_GAP
MODULE_TEST_GAP
LOCAL_TOOLING_GAP
MODULE_BROWSER_PROOF_GAP
RELEASE_ENVIRONMENT_ACCEPTANCE
EXTERNAL_DEPENDENCY_ACCEPTANCE
UNKNOWN
```

Missing `node_modules` is classified as `LOCAL_TOOLING_GAP`. Hosted
preprod/production acceptance is classified as
`RELEASE_ENVIRONMENT_ACCEPTANCE` and is not manufactured by this branch.
