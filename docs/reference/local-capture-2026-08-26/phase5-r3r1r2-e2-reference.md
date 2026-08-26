# CRITICAL R3R1R2-E2 SUPERSESSION — LOCAL PRECOMMIT VS REMOTE NATIVE RUNTIME
## ProposalOps / AMEC Phase5 R3R1R2 — exact environment-boundary correction
**Date:** 2026-08-25

This document is the complete R3R1R2 authorization with one narrowly
superseding environment-boundary correction.

```text
R3R1R2_PARENT_PROMPT_SHA256=c71df8ecd7633b883d445befd3353ad54b4a73fc664692ea1571166c900ca258

LATEST_LOCAL_STOP=
STOP_PHASE5_R3R1R2_APPLICATION_PRECOMMIT_FAILED

LATEST_LOCAL_FIRST_FAILED_GATE=
pytest -q backend/tests/test_phase5_sqlserver_runtime.py

LATEST_LOCAL_STOP_CLASS=
VALID_FAIL_CLOSED_AUTHORIZATION_ENVIRONMENT_BOUNDARY

APPLICATION_DEFECT_PROVEN=false
NATIVE_SQLSERVER_RUNTIME_UNAVAILABLE_LOCALLY=true

APPLICATION_COMMIT_CREATED=false
APPLICATION_BRANCH_PUSHED=false
VALIDATION_COMMIT_CREATED=false
R3R1R2_TARGET_BRANCHES_CREATED=false
```

The native Phase5 SQL Server test module is deliberately fail-closed unless
`DATABASE_URL` is `mssql+pyodbc://...`. Therefore executing it on the current
Mac/default SQLite environment cannot be used as an application precommit
result.

The authoritative native runtime is the fresh GitHub-hosted Ubuntu 22.04
x86-64 SQL Server 2022 workflow. The exact R3R1R1 workflow already executed the
16 native SQL Server tests and the real SQL Server-backed browser stack before
the later evidence/finalizer failure.

## E2 precedence

Where the complete R3R1R2 authorization below conflicts with this E2
correction, **E2 wins only for local/precommit runtime location and commands**.

E2 supersedes:
1. local execution of `backend/tests/test_phase5_sqlserver_runtime.py` when no
   independently available native MSSQL endpoint exists;
2. local wildcard commands that transitively execute that module;
3. local full-backend commands that fail to exclude that module;
4. treating unavailable local Docker/native SQL Server as an application
   failure;
5. requiring real-browser acceptance before the application commit.

E2 does **not** supersede:
- exact source/entry identities;
- governing source bytes/hashes;
- R3R1R2 application mutation allowlist;
- frozen classifier/corpus/schema boundaries;
- producer-result contracts;
- 17-field finalizer source contract;
- exact 300-row evidence mapping;
- semantic mutation/false-accept gates;
- source preflight V6;
- 12-stage DAG;
- final-summary v1 truth;
- sanitizer/final-byte reconciliation;
- one-application-commit / one-workflow-commit discipline;
- fresh remote native SQL Server execution;
- fresh real browser execution;
- 280/290/300 evidence counts;
- safety boundaries;
- independent-acceptance separation.

## E2 exact live entry state — reprove before mutation

Require remote:

```text
PHASE5_R3R1R1_APPLICATION_BRANCH=
phase5-classifier-shadow-validation-r3r1r1-v1

PHASE5_R3R1R1_APPLICATION_SHA=
8cae536262756b15e26f08cc5eeed7641c0402bc

PHASE5_R3R1R1_APPLICATION_PARENT=
19a938761d9465d7fd2e0f61656f3d4838153d74

PHASE5_R3R1R1_APPLICATION_TREE=
50fe8025318b12ef6aeaf0f18f3d995856d51d93

PHASE5_R3R1R1_VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-r3r1r1-v1

PHASE5_R3R1R1_VALIDATION_SHA=
1c0cd794589118d097765c84666100f72551643b

PHASE5_R3R1R1_VALIDATION_PARENT=
8cae536262756b15e26f08cc5eeed7641c0402bc

PHASE5_R3R1R2_APPLICATION_BRANCH=
phase5-classifier-shadow-validation-r3r1r2-v1

PHASE5_R3R1R2_APPLICATION_BRANCH_STATE=ABSENT

PHASE5_R3R1R2_VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-r3r1r2-v1

PHASE5_R3R1R2_VALIDATION_BRANCH_STATE=ABSENT
```

If any entry identity differs, STOP before mutation.

## E2 local runtime classification

If a usable native `mssql+pyodbc` endpoint is not already independently
available on the current host, record:

```text
LOCAL_NATIVE_SQLSERVER_RUNTIME=
ENVIRONMENT_BLOCKED_LOCAL_ONLY

LOCAL_NATIVE_SQLSERVER_RUNTIME_REQUIRED_FOR_APP_COMMIT=false
LOCAL_NATIVE_SQLSERVER_RUNTIME_ACCEPTANCE_CREDIT=0

LOCAL_REAL_BROWSER_RUNTIME_REQUIRED_FOR_APP_COMMIT=false
LOCAL_BROWSER_RUNTIME_ACCEPTANCE_CREDIT=0
```

This is neither application PASS nor application FAIL.

Do not:
- start/restart/reinstall/troubleshoot Docker Desktop;
- emulate SQL Server on ARM;
- run native SQL Server tests against SQLite and interpret them as product
  failures;
- fabricate SQL Server/browser evidence.

## E2 exact local precommit matrix

This block replaces Section 29 below wherever the old Section 29 conflicts.

### Native SQL Server module — collection and contract only

Run:

```bash
pytest --collect-only -q backend/tests/test_phase5_sqlserver_runtime.py
```

Require:

```text
PHASE5_SQLSERVER_RUNTIME_TEST_COLLECTED=16
PHASE5_SQLSERVER_RUNTIME_TEST_COLLECTION_FAIL=0

PHASE5_SQLSERVER_RUNTIME_REQUIRES_MSSQL_PYODBC=true
PHASE5_SQLSERVER_RUNTIME_SKIP_XFAIL_ADDITION_COUNT=0

LOCAL_NATIVE_SQLSERVER_RUNTIME_ACCEPTANCE_CREDIT=0
```

Do not execute those 16 tests locally unless a real native MSSQL endpoint
already exists independently. Even then, local execution is optional diagnostic
evidence and is not the authoritative acceptance lane.

### Deterministic/backend local tests

Run:

```bash
pytest -q \
  backend/tests/test_phase5_contracts.py \
  backend/tests/test_phase5_evidence_integrity.py \
  backend/tests/test_phase5_finalizer_negative.py \
  backend/tests/test_phase5_classifier.py \
  backend/tests/test_phase5_portability.py \
  backend/tests/test_phase4_corpus_app_integration.py

pytest -q --ignore=backend/tests/test_phase5_sqlserver_runtime.py
```

Require zero actual failures and zero unexpected collection errors.

Do **not** run locally:

```text
pytest -q backend/tests/test_phase5*.py
pytest -q backend/tests
```

because both include the separately remote-required native SQL Server module.

### Deterministic/source tooling

Run:

```bash
python -m compileall -q backend scripts

python scripts/phase5/source_preflight.py \
  --output artifacts/phase5-r3r1r2-source-preflight.json \
  --planned-workflow <planned-R3R1R2-workflow-path>

python scripts/phase5/reproducibility.py

python scripts/phase5/corpus_coverage.py \
  --corpus contracts/amec/phase5/AMEC_CLASSIFIER_ROBUSTNESS_CORPUS_V2.json

git diff --check
```

Require the governing R3R1R2 source/evidence checks to pass, including source
preflight V6, producer contracts, 300 exact specs, 17 summary fields,
false-accept checks, DAG checks, and governing-source hashes.

### Frontend local precommit

Use the exact tracked candidate frontend tree.

If an isolated worktree is missing tracked frontend files, restore **only**
missing tracked bytes from the exact candidate index. Do not stage them and do
not count them as application mutations.

Run:

```bash
cd frontend
npm ci
npm test -- --run
npx tsc -b
npx vite build
```

Require zero test/build failures.

Do not require a real-browser acceptance result locally. Real browser proof is
remote-only.

## E2 no-loop source-preflight boundary

Before the application commit require the planned workflow audit to prove:

```text
LOCAL_PRECOMMIT_NATIVE_SQLSERVER_EXECUTION_REQUIRED=false
LOCAL_FULL_BACKEND_EXCLUDES_NATIVE_SQLSERVER_MODULE=true

REMOTE_WORKFLOW_NATIVE_SQLSERVER_EXECUTION_REQUIRED=true
REMOTE_WORKFLOW_NATIVE_SQLSERVER_TEST_COMMAND_PRESENT=true
REMOTE_WORKFLOW_NATIVE_SQLSERVER_TEST_COUNT=16

REMOTE_WORKFLOW_FULL_BACKEND_EXCLUDES_RUNTIME_MODULE=true

REMOTE_WORKFLOW_REAL_BROWSER_REQUIRED=true
REMOTE_WORKFLOW_REAL_BROWSER_USES_SQLSERVER_BACKED_API=true

LOCAL_RUNTIME_EVIDENCE_PROMOTED_TO_REMOTE_ACCEPTANCE_COUNT=0
```

A failure of any of these is an application-precommit STOP.

## E2 application commit authorization

If and only if:
- exact entry identity PASS;
- governing source bytes/hashes PASS;
- all R3R1R2 repair ledger rows close;
- local deterministic/source/backend/frontend matrix PASS;
- native SQL Server module collects exactly 16;
- source preflight V6 / no-loop audit PASS;
- local native-runtime acceptance credit remains zero;
- application diff remains entirely inside the existing R3R1R2 allowlist;

then local native SQL Server unavailability is **not** a blocker to creating the
single R3R1R2 application commit already authorized below.

## E2 remote native runtime remains mandatory

The fresh R3R1R2 validation workflow must execute on GitHub-hosted Ubuntu 22.04
x86-64 and must provision SQL Server 2022 Developer plus ODBC Driver 18.

It must execute exactly:

```bash
python -m pytest -q backend/tests/test_phase5_sqlserver_runtime.py
```

with:

```text
DATABASE_URL=mssql+pyodbc://...
```

and require:

```text
PHASE5_SQLSERVER_TARGETED_GATE_COUNT=16
PHASE5_SQLSERVER_TARGETED_PASS=16
PHASE5_SQLSERVER_TARGETED_FAIL=0
PHASE5_SQLSERVER_TARGETED_SKIP=0

SQLSERVER_MAJOR=16
ACTIVE_MIGRATION_HEAD=baseline_phase4_v36_azure_sql
```

The full backend remote producer must separately execute with the native module
excluded:

```bash
pytest -q --ignore=backend/tests/test_phase5_sqlserver_runtime.py
```

The same remote run must execute the actual SQL Server-backed shadow replay,
real SQL Server-backed API/frontend, Playwright Chromium, all 10 required
browser paths, frontend regressions/build, and the complete 12-stage evidence
DAG.

No PASS from R3R1R1 is inherited. R3R1R2 must earn fresh runtime/browser
evidence on its own exact candidate/validation/run identity.

---

# COMPLETE R3R1R2 AUTHORIZATION FOLLOWS
# E2 ABOVE GOVERNS ONLY THE EXPLICIT LOCAL/PRECOMMIT CONFLICTS

# ONE-SHOT CODEX OWNER AUTHORIZATION — PROPOSALOPS / AMEC PHASE5 FINAL R3R1R2
## Producer-contract closure + exact 300-row evidence truth + finalizer/schema truth + sanitizer final-byte proof + full native SQL Server/browser rerun
**Date:** 2026-08-25

---

# 0. OWNER AUTHORIZATION / OBJECTIVE

The Owner authorizes exactly one bounded Phase5 descendant repair after the
exact R3R1R1 remote run reached the post-producer acceptance DAG and stopped at
`FINALIZER_PRODUCE`.

R3R1R2 must close **all known currently deterministic blockers before another
remote run**, specifically:

```text
A. shadow-replay.new_source_reads producer/finalizer mismatch
B. missing producer-result-contract enforcement
C. heuristic/category-level 300-row semantic evidence fallback
D. canonical final-summary v1 vs emitted version mismatch
E. sanitizer post-manifest independent reconciliation weakness
F. local tests that handcraft producer fields not emitted by the real producer
```

Then execute one complete fresh native SQL Server 2022 + real browser Phase5
validation and STOP for independent Phase5 acceptance.

This is not deployment authorization.
This is not Phase6 authorization.
This is not real-data authorization.

No Azure mutation.
No Entra mutation.
No Synology/SMB access.
No real AMEC data.
No continuous live shadow.
No writeback.
No auto-promotion.

---

# 1. GOVERNING SOURCE / STATE RULE

Use:

```text
latest explicit Owner/product decision
+ later executable repository/runtime evidence
+ later independent acceptance where required
= governing current state
```

Exact run/source evidence outranks prompt self-report.

Keep separate:

```text
IMPLEMENTED
VERIFIED_LOCAL
VERIFIED_SQLSERVER_COMPAT
VERIFIED_BROWSER
VERIFIED_AZURE_SQL
VERIFIED_DEPLOYED
INDEPENDENTLY_ACCEPTED
```

Codex does not independently accept Phase5.

---

# 2. EXACT ACCEPTED PHASE4 ENTRY — IMMUTABLE

Reprove exact accepted entry:

```text
PHASE4_INDEPENDENT_ACCEPTANCE=PASS

PHASE4_ACCEPTED_SHA=
707003fc16767fb28b9c968fbcf168ab03ebadc1

PHASE4_ACCEPTED_PARENT=
fb1d504ae058c09a9fdd84a5afd68bcb3916e35c

PHASE4_ACCEPTED_TREE=
af473134f6a92b9dc9919eae71f1e02a3ed81e1e

PHASE4_ACCEPTANCE_VALIDATION_SHA=
d56817d27a9aaaf69aa08b5e314f78297ed45376

PHASE4_ACCEPTANCE_RUN_ID=
32778775085

PHASE4_ACCEPTANCE_ARTIFACT_SHA256=
877f1e39c4bb0e16187dcf4de76ba47cff7df3bdf7cb01a2ae6027da1df4f4a6
```

Do not modify Phase4.

---

# 3. EXACT CURRENT R3R1R1 APPLICATION — REPROVE LIVE

Require:

```text
PHASE5_R3R1R1_APPLICATION_BRANCH=
phase5-classifier-shadow-validation-r3r1r1-v1

PHASE5_R3R1R1_APPLICATION_SHA=
8cae536262756b15e26f08cc5eeed7641c0402bc

PHASE5_R3R1R1_APPLICATION_PARENT=
19a938761d9465d7fd2e0f61656f3d4838153d74

PHASE5_R3R1R1_APPLICATION_TREE=
50fe8025318b12ef6aeaf0f18f3d995856d51d93
```

Use direct remote authority. Do not amend or move the branch.

---

# 4. EXACT CURRENT R3R1R1 VALIDATION / WORKFLOW / RUN

Require:

```text
PHASE5_R3R1R1_VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-r3r1r1-v1

PHASE5_R3R1R1_VALIDATION_SHA=
1c0cd794589118d097765c84666100f72551643b

PHASE5_R3R1R1_VALIDATION_PARENT=
8cae536262756b15e26f08cc5eeed7641c0402bc

PHASE5_R3R1R1_VALIDATION_TREE=
dd00eed0a7230df2b906b0cd1f65e35befb75a22

PHASE5_R3R1R1_WORKFLOW_PATH=
.github/workflows/phase5-classifier-shadow-validation-ci-r3r1r1.yml

PHASE5_R3R1R1_WORKFLOW_BLOB_SHA1=
2c5bda0cb501b1d1afe7ea27b9386670041e9fc1

RUN_ID=32873374492
JOB_ID=97885456568
```

No successful sanitized artifact was uploaded because execution stopped before
sanitization/upload.

---

# 5. REPROVE EXACT R3R1R1 FAILURE BEFORE MUTATION

From live GitHub logs require:

```text
R3R1R1_RUNTIME_RESULT=VALID_FAIL_CLOSED

FIRST_FAILED_STAGE=FINALIZER_PRODUCE

FIRST_FAILED_ERROR=
shadow-replay.result.json missing required new_source_reads field
```

Require these stages/gates completed before failure:

```text
CANDIDATE_BINDING=PASS
NATIVE_X64_DOCKER=PASS
DEPENDENCY_INSTALL=PASS
PLAYWRIGHT_INSTALL=PASS

SQLSERVER_BOOTSTRAP=PASS
MIGRATION_HEAD=PASS

GOVERNING_SOURCE_BYTES=PASS
SOURCE_PREFLIGHT=PASS

CLASSIFIER_CALIBRATION=PASS
CLASSIFIER_VALIDATION=PASS
CLASSIFIER_HOLDOUT=PASS
CLASSIFIER_CROSS_CONTEXT=PASS
CLASSIFIER_PATH_COUNTERFACTUAL=PASS
FREEZE_REPRODUCIBILITY=PASS

PHASE5_SQLSERVER_TARGETED=PASS
SHADOW_REPLAY=PASS

BACKEND_TARGETED=PASS
PHASE4_INTEGRATION_REGRESSION=PASS
BACKEND_FULL=PASS

AUTHORITY_DENIAL=PASS
OBSERVABILITY=PASS
SECURITY_HYGIENE=PASS

REAL_SQLSERVER_API_FRONTEND=PASS
REAL_BROWSER_REQUIRED_PATHS=PASS
BROWSER_QUALITY=PASS
FRONTEND_TARGETED=PASS
FRONTEND_FULL=PASS
FRONTEND_BUILD=PASS

PRE_FINALIZER_ACCEPTANCE_COUNT=280
PRE_FINALIZER_ACCEPTANCE_PASS=280
PRE_FINALIZER_VALIDATION=PASS
```

Require downstream not executed:

```text
DRAFT_FINAL_NOT_EXECUTED=true
ACCEPTANCE_INTEGRITY_NOT_EXECUTED=true
FINAL_ACCEPTANCE_NOT_EXECUTED=true
FINAL_VALIDATION_NOT_EXECUTED=true
HANDOFF_SEAL_NOT_EXECUTED=true
SANITIZER_NOT_EXECUTED=true
UPLOAD_NOT_EXECUTED=true
```

If materially different:

```text
RESULT=STOP_PHASE5_R3R1R2_DIAGNOSIS_CHANGED
```

STOP.

---

# 6. REPROVE THE EXACT SOURCE MISMATCH

At exact `8cae536...` require:

```text
CURRENT_FINALIZER_REQUIRES_NEW_SOURCE_READS=true
CURRENT_SHADOW_PRODUCER_EMITS_NEW_SOURCE_READS=false
CURRENT_TEST_FIXTURE_MASKS_MISSING_SHADOW_FIELD=true
```

Prove `finalize.py` maps:

```text
new_source_reads
→ producer shadow-replay
→ json_path new_source_reads
→ integer
```

Prove the real `shadow_replay.py` result does not emit it.

Prove current finalizer tests manually inject `new_source_reads=0` and use a
non-governing test shadow state instead of the real producer shape.

If materially different:

```text
RESULT=STOP_PHASE5_R3R1R2_SOURCE_DIAGNOSIS_CHANGED
```

STOP.

---

# 7. FRESH BRANCH COLLISION GATE

Require remotely absent:

```text
phase5-classifier-shadow-validation-r3r1r2-v1
phase5-classifier-shadow-validation-ci-r3r1r2-v1
```

If either exists:

```text
RESULT=STOP_PHASE5_R3R1R2_BRANCH_COLLISION
```

STOP.

---

# 8. CREATE FRESH R3R1R2 APPLICATION BRANCH

Create:

```text
PHASE5_R3R1R2_APPLICATION_BRANCH=
phase5-classifier-shadow-validation-r3r1r2-v1

PHASE5_R3R1R2_APPLICATION_BASE=
8cae536262756b15e26f08cc5eeed7641c0402bc
```

Direct child only.

No merge.
No rebase.
No amend.
No force push.

---

# 9. CLASSIFIER / FROZEN BUSINESS BEHAVIOR — HARD FREEZE

This is evidence/governance closure, **not classifier redesign**.

Do not modify:

```text
backend/app/services/classifier_v2.py
backend/app/schemas/classifier_v2.py
backend/app/api/phase5.py

contracts/amec/phase5/AMEC_CLASSIFIER_V2_RULES_v1.json
contracts/amec/phase5/AMEC_CLASSIFIER_ROBUSTNESS_CORPUS_V2.json
contracts/amec/phase5/AMEC_CLASSIFIER_CALIBRATION_DEVELOPMENT_MANIFEST_v1.json
contracts/amec/phase5/AMEC_CLASSIFIER_VALIDATION_MANIFEST_v1.json
contracts/amec/phase5/AMEC_CLASSIFIER_HOLDOUT_ADVERSARIAL_MANIFEST_v1.json

contracts/amec/phase5/AMEC_CLASSIFIER_V2_CALIBRATION_RESULTS_v1.json
contracts/amec/phase5/AMEC_CLASSIFIER_V2_VALIDATION_RESULTS_v1.json
contracts/amec/phase5/AMEC_CLASSIFIER_V2_HOLDOUT_RESULTS_v1.json
contracts/amec/phase5/AMEC_CLASSIFIER_V2_CROSS_CONTEXT_RESULTS_v1.json
contracts/amec/phase5/AMEC_CLASSIFIER_V2_PATH_COUNTERFACTUAL_RESULTS_v1.json

contracts/amec/phase5/AMEC_CLASSIFIER_V2_FREEZE_MANIFEST_v1.json
contracts/amec/phase5/AMEC_PHASE5_SHADOW_CONTRACT_v1.json
contracts/amec/phase5/AMEC_PHASE5_INPUT_IDENTITY_MANIFEST_v1.json

contracts/amec/phase5/AMEC_PHASE5_FINAL_SUMMARY_v1.schema.json
```

Do not burn/rebuild holdout.
Do not change governing final-summary schema.

---

# 10. EXACT APPLICATION MUTATION ALLOWLIST

Only these paths may change:

```text
scripts/phase5/registry.py
scripts/phase5/shadow_replay.py
scripts/phase5/acceptance.py
scripts/phase5/evidence_validate.py
scripts/phase5/finalize.py
scripts/phase5/source_preflight.py
scripts/phase5/sanitize_evidence.py

backend/tests/test_phase5_contracts.py
backend/tests/test_phase5_evidence_integrity.py
backend/tests/test_phase5_finalizer_negative.py
```

A listed path may remain unchanged.

If another path is genuinely required:

```text
RESULT=STOP_PHASE5_R3R1R2_APPLICATION_SCOPE_EXPANSION_REQUIRED
REQUIRED_PATH=<exact>
REASON=<exact>
```

STOP before commit.

---

# 11. PRODUCER RESULT CONTRACT REGISTRY — HARD BOUNDARY

In `scripts/phase5/registry.py` define one normative machine-readable registry:

```text
PRODUCER_RESULT_CONTRACTS
```

for every producer in `EVIDENCE_PRODUCERS`.

Each producer contract must define:
- required JSON paths;
- exact required type per path;
- optional const/set/range/count semantics where governing;
- whether path is summary-consumed;
- whether producer is runtime-required.

No wildcard for summary-consumed fields.
No default insertion.
No assumption that top-level `result=PASS` proves consumed fields exist.

Implement a shared helper equivalent to:

```text
validate_producer_payload_contract(producer_id, payload)
```

It must:
- resolve nested JSON paths;
- enforce declared type;
- enforce configured constants/ranges/counts;
- fail closed on missing field/type mismatch;
- never mutate payload or manufacture defaults.

Require:

```text
PRODUCER_RESULT_CONTRACT_COUNT=len(EVIDENCE_PRODUCERS)
MISSING_PRODUCER_RESULT_CONTRACT_COUNT=0
UNKNOWN_PRODUCER_RESULT_CONTRACT_COUNT=0

SUMMARY_CONSUMED_PATH_COUNT=17
SUMMARY_CONSUMED_PATH_UNDECLARED_COUNT=0

ASSERTION_CONSUMED_PATH_UNDECLARED_COUNT=0
PRODUCER_RESULT_CONTRACT_TYPE_GAP_COUNT=0
```

`source_preflight.py`, `evidence_validate.py`, acceptance semantic proof
evaluation, and finalizer derivation must consume this same registry.

---

# 12. FIX REAL SHADOW-REPLAY BOUNDARY EVIDENCE

Modify evidence generation only; do not change classifier behavior.

## 12.1 One real result builder

In `scripts/phase5/shadow_replay.py` factor the real payload generation into a
pure/testable helper equivalent to:

```text
_build_shadow_result(...)
```

The actual CLI/runtime path must use it.

Tests must use this helper or a producer-contract fixture generated from the
same registry, not handcrafted extra keys.

## 12.2 Derive source-read truth from persisted evidence envelopes

From the unique evidence-envelope IDs returned by the actual replay calls,
load exact persisted:

```text
Phase4DocumentEvidenceEnvelope
```

rows.

Inspect:

```text
source_surface
content_retention_class
metering_json.bytes_read
metering_json.external_calls
```

Derive:

```text
new_source_bytes =
sum(int(bytes_read or 0))

new_source_reads =
count(unique replay evidence envelope where int(bytes_read or 0) > 0)

llm_external_call_count =
sum(int(external_calls or 0))

real_content =
any(
    source_surface != "CONTROLLED_SYNTHETIC_FIXTURE"
    OR content_retention_class != "METADATA_ONLY"
    OR int(bytes_read or 0) > 0
)
```

Do not hardcode those four outputs independently of persisted evidence.

For this synthetic-only authorized run, PASS requires:

```text
shadow_state=REVIEW_COMPARE_ONLY

new_source_reads=0
new_source_bytes=0
llm_external_call_count=0
real_content=false

classifier_only_verified_assertion_count=0
classifier_only_projection_count=0
synology_writeback_count=0
external_protected_action_count=0

replay_stable=true
replay_same_envelope=true
replay_side_effect_duplicate_count=0
```

Emit every fact in `shadow-replay.result.json`.

Require:

```text
SHADOW_NEW_SOURCE_READS_DERIVED=true
SHADOW_NEW_SOURCE_BYTES_DERIVED=true
SHADOW_LLM_EXTERNAL_CALLS_DERIVED=true
SHADOW_REAL_CONTENT_DERIVED=true
```

---

# 13. REMOVE TEST FIXTURE SHAPE DRIFT

In `backend/tests/test_phase5_finalizer_negative.py`:

- remove manual injection used only to satisfy finalizer;
- do not use `SHADOW_ONLY`;
- use governing/current `REVIEW_COMPARE_ONLY`;
- create shadow evidence using the real shadow result builder or
  contract-driven fixture generator.

Require:

```text
FINALIZER_TEST_SHADOW_STATE=REVIEW_COMPARE_ONLY
FINALIZER_TEST_HANDCRAFTED_NEW_SOURCE_READS_INJECTION=false
REAL_SHADOW_RESULT_BUILDER_TESTED=true
```

Add negative test:
- remove `new_source_reads` from a real-contract-valid shadow payload;
- `finalizer produce` must fail with the missing field.

---

# 14. 17-FIELD FINALIZER SOURCE CONTRACT AUDIT

Preserve exactly 17 governing summary fields.

Before app commit, for all 17 prove:

```text
mapped producer exists
producer result contract exists
mapped JSON path declared by producer contract
producer path declared type matches finalizer expected type
transform input count/type valid
```

Require:

```text
FINALIZER_REQUIRED_DERIVED_SUMMARY_FIELD_COUNT=17
FINALIZER_SUMMARY_SOURCE_MAP_COUNT=17
FINALIZER_SUMMARY_SOURCE_MAP_MISSING_COUNT=0
FINALIZER_SUMMARY_LITERAL_FALLBACK_COUNT=0

FINALIZER_SUMMARY_SOURCE_CONTRACT_AUDIT_COUNT=17
FINALIZER_SUMMARY_SOURCE_CONTRACT_AUDIT_PASS=17
FINALIZER_SUMMARY_SOURCE_UNPROVABLE_PATH_COUNT=0
FINALIZER_SUMMARY_SOURCE_TYPE_MISMATCH_COUNT=0
```

Retain a 17-case derivation mutation matrix:
- valid producer evidence;
- derive summary;
- mutate/remove exact source fact;
- summary must change or finalizer fail closed.

Require:

```text
FINALIZER_SUMMARY_DERIVATION_MUTATION_CASE_COUNT=17
FINALIZER_SUMMARY_DERIVATION_MUTATION_PASS=17
FINALIZER_SUMMARY_DERIVATION_FALSE_ACCEPT_COUNT=0
```

---

# 15. C06 — EXACT 300-ROW ASSERTION EVIDENCE SPEC

Remove semantic proof selection based on broad category/keywords.

Create one normative exact map:

```text
ASSERTION_EVIDENCE_SPEC
```

keyed by every exact `(category, assertion)` pair from
`acceptance.REQUIREMENT_GROUPS`.

Exactly 300 rows.

Require:

```text
ASSERTION_EVIDENCE_SPEC_COUNT=300
ASSERTION_EVIDENCE_SPEC_MISSING_COUNT=0
ASSERTION_EVIDENCE_SPEC_UNKNOWN_COUNT=0
ASSERTION_EVIDENCE_SPEC_DUPLICATE_KEY_COUNT=0

ASSERTION_EVIDENCE_SPEC_DEFAULT_FALLBACK_COUNT=0
ASSERTION_EVIDENCE_SPEC_KEYWORD_HEURISTIC_COUNT=0
ASSERTION_EVIDENCE_SPEC_EMPTY_PROOF_COUNT=0
```

Each exact assertion must identify concrete proof specs:

```text
producer_id
json_path OR explicit file/source fact
operator
expected value/source
expected type
runtime_required
```

Closed operator registry only; no arbitrary `eval`.

Allowed equivalents include:

```text
eq
zero
nonzero
true
false
exists
count_eq
set_eq
contains
all_pass
sha256_eq
identity_eq
file_exists_nonempty
no_local_path
no_secret_pattern
```

Every referenced JSON path must be declared in that producer's result contract.

Forbidden:
- `expected = observed`;
- wildcard/default assertion policy;
- "producer result PASS proves every assertion";
- substantive negative assertion represented only by top-level producer PASS.

---

# 16. EXPLICIT BOUNDARY FACTS — NO GENERIC PASS

At minimum exact BOUNDARY assertions must be bound as follows.

For `new source reads are zero`:

```text
producer=shadow-replay
json_path=new_source_reads
operator=zero
type=integer
```

For `new source bytes are zero`:

```text
producer=shadow-replay
json_path=new_source_bytes
operator=zero
type=integer
```

For LLM/real-content boundaries:

```text
shadow-replay.real_content=false
shadow-replay.llm_external_call_count=0
```

For writeback/protected action boundaries:

```text
shadow-replay.synology_writeback_count=0
shadow-replay.external_protected_action_count=0
```

Use actual authority/security/source-preflight facts for other exact boundary
assertions.

Require:

```text
BOUNDARY_ASSERTION_COUNT=10
BOUNDARY_GENERIC_RESULT_ONLY_PROOF_COUNT=0
```

---

# 17. EXPLICIT SQLSERVER / BROWSER / REGRESSION EVIDENCE

SQLSERVER assertions must bind to actual:
- SQL Server major;
- migration head;
- native gate count/pass/fail;
- specific target/runtime facts.

No `expected=observed`.

Browser assertions must bind to parsed Playwright/browser result:
- exact required path IDs;
- pass/fail/skip;
- browser-quality facts;
- no business API mock where required.

Regression assertions must cite actual:
- backend targeted/full;
- Phase4 integration regression;
- frontend targeted/full/build;
- SQL Server targeted.

Require:

```text
SQLSERVER_GENERIC_RESULT_ONLY_PROOF_COUNT=0
BROWSER_GENERIC_RESULT_ONLY_PROOF_COUNT=0
REGRESSION_GENERIC_RESULT_ONLY_PROOF_COUNT=0
```

---

# 18. ACCEPTANCE ENGINE — PASS ONLY FROM EXACT PROOFS

`acceptance.py` must:
1. use exact `ASSERTION_EVIDENCE_SPEC`;
2. resolve every required producer;
3. validate producer contract;
4. evaluate all exact proof specs;
5. emit `semantic_proofs`;
6. set row PASS only if every proof PASS.

No unconditional row PASS.
No category-level shortcut.

Require:

```text
ACCEPTANCE_PASS_WITH_FAILED_SEMANTIC_PROOF_COUNT=0
ACCEPTANCE_PASS_WITH_MISSING_PRODUCER_COUNT=0
ACCEPTANCE_PASS_WITH_CONTRACT_INVALID_PRODUCER_COUNT=0
```

---

# 19. EVIDENCE VALIDATOR — INDEPENDENT RECOMPUTATION

`evidence_validate.py` must **not trust** acceptance row:
- result;
- semantic proofs;
- expected values;
- producer state.

Independently:
1. load exact assertion spec;
2. reopen producer raw/meta/result evidence;
3. triple-bind candidate/validation/run;
4. require integer exit code 0;
5. validate result contract;
6. independently recompute each proof;
7. compare proof signature to acceptance row;
8. fail any mismatch.

Stages remain:

```text
PRE_FINALIZER
DRAFT_FINAL
FINAL
```

Require:

```text
ASSERTION_SEMANTIC_RECOMPUTE_COUNT=<stage exact count>
ASSERTION_SEMANTIC_RECOMPUTE_FAIL_COUNT=0
ASSERTION_SEMANTIC_PROOF_MISMATCH_COUNT=0

PRODUCER_RESULT_CONTRACT_FAILURE_COUNT=0
TAUTOLOGICAL_EXPECTED_OBSERVED_COUNT=0
```

FINAL additionally requires actual:
- finalizer PASS;
- acceptance-integrity PASS.

---

# 20. ALL-300 ASSERTION-SPECIFIC NEGATIVE MUTATION MATRIX

Before app commit exercise all exact 300 assertions.

For each:
1. build contract-valid producer evidence satisfying its exact spec;
2. verify assertion PASS;
3. mutate/remove at least one **specific fact referenced by that assertion's
   own proof**;
4. independently recompute;
5. require assertion FAIL.

It is invalid to use only:
- top-level `result`;
- exit code;
- candidate SHA;
as the mutation for all rows.

Require:

```text
ASSERTION_SEMANTIC_MUTATION_CASE_COUNT=300
ASSERTION_SEMANTIC_MUTATION_PASS=300
ASSERTION_SEMANTIC_MUTATION_FALSE_ACCEPT_COUNT=0

ASSERTION_MUTATION_ONLY_TOP_LEVEL_RESULT_COUNT=0
ASSERTION_MUTATION_TAUTOLOGY_COUNT=0
```

Write local-only:

```text
artifacts/phase5-r3r1r2-300-assertion-mutation.json
```

Do not commit it.

---

# 21. SOURCE PREFLIGHT V6 — MODEL REAL CONTRACTS

Upgrade:

```text
PHASE5_SOURCE_PREFLIGHT_VERSION=6
```

It must execute, not merely string-match:

```text
governing source hashes
current lineage
producer registry completeness
producer result-contract completeness
17-field finalizer producer/path/type contract
300 exact assertion-spec completeness
all assertion JSON paths declared in producer contracts
300 assertion-specific mutation sensitivity
12-stage DAG and cycle detection
planned workflow ordering/CLI/result names
canonical final-summary v1 contract compatibility
sanitizer post-manifest independent verifier presence
```

Require:

```text
CATEGORY_COUNT=30
REQUIREMENT_ASSERTION_COUNT=300

ASSERTION_EVIDENCE_SPEC_COUNT=300
ASSERTION_EVIDENCE_SPEC_MISSING_COUNT=0
ASSERTION_EVIDENCE_SPEC_DEFAULT_FALLBACK_COUNT=0
ASSERTION_EVIDENCE_SPEC_KEYWORD_HEURISTIC_COUNT=0

ASSERTION_SEMANTIC_MUTATION_FALSE_ACCEPT_COUNT=0

FINALIZER_SUMMARY_SOURCE_MAP_COUNT=17
FINALIZER_SUMMARY_SOURCE_UNPROVABLE_PATH_COUNT=0
FINALIZER_SUMMARY_SOURCE_TYPE_MISMATCH_COUNT=0

PRODUCER_RESULT_CONTRACT_MISSING_COUNT=0
ASSERTION_CONSUMED_PATH_UNDECLARED_COUNT=0

PIPELINE_STAGE_COUNT=12
PIPELINE_CYCLE_COUNT=0
PLANNED_WORKFLOW_CYCLE_COUNT=0

FINAL_SUMMARY_SCHEMA_CONFORMANCE_STATIC=PASS
SANITIZER_POST_MANIFEST_INDEPENDENT_RECONCILIATION_PRESENT=true

DEFINITE_BLOCKER_COUNT=0
```

Hardcoded-zero implementation is forbidden.

---

# 22. CANONICAL FINAL SUMMARY v1 — CLOSE VERSION MISMATCH NOW

Do not modify:

```text
contracts/amec/phase5/AMEC_PHASE5_FINAL_SUMMARY_v1.schema.json
```

Final emitted:

```text
phase5-final-summary.json
```

must use:

```text
version=1
```

Canonical required semantics include:

```text
result=PASS
shadow_state=REVIEW_COMPARE_ONLY
handoff_state=READY_FOR_INDEPENDENT_PHASE5_ACCEPTANCE
acceptance_check_count>=300
```

Before seal PASS:
- load canonical schema file;
- enforce every required field;
- enforce const values;
- enforce acceptance minimum;
- enforce final-summary version 1;
- independently require all 17 evidence-derived governing fields equal finalizer
  derivations.

Do not add a new dependency merely for schema validation; use standard library
for this exact schema subset unless an existing installed validator is already
available.

Require:

```text
FINAL_SUMMARY_SCHEMA_FILE_UNCHANGED=true
FINAL_SUMMARY_PAYLOAD_VERSION=1
FINAL_SUMMARY_SCHEMA_CONFORMANCE=PASS
FINAL_SUMMARY_17_FIELD_DERIVATION_MATCH=PASS
```

Negative tests:
- version 4;
- wrong shadow state;
- missing required field;
- wrong handoff state;
- acceptance count < 300.

---

# 23. PRESERVE EXACT ACYCLIC 12-STAGE DAG

Stages:

```text
BASE_EVIDENCE
PRE_FINALIZER_ACCEPTANCE
PRE_FINALIZER_VALIDATION
FINALIZER_PRODUCE
DRAFT_FINAL_ACCEPTANCE
DRAFT_FINAL_VALIDATION
ACCEPTANCE_INTEGRITY
FINAL_ACCEPTANCE
FINAL_VALIDATION
HANDOFF_SEAL
SANITIZER
UPLOAD
```

Require:

```text
PIPELINE_STAGE_COUNT=12
PIPELINE_CYCLE_COUNT=0
```

Never:
- preseed finalizer;
- preseed acceptance-integrity;
- run FINAL before acceptance-integrity;
- seal before FINAL validator;
- sanitize before seal;
- upload working evidence.

---

# 24. FINALIZER PRODUCE — FAIL CLOSED, NOT ACCEPTANCE-READY

`produce` requires:
- PRE_FINALIZER 280/280;
- PRE_FINALIZER evidence validator PASS;
- exact triple identity;
- required pre-finalizer producers PASS;
- producer contracts valid;
- all 17 summary derivations available.

Require before produce:

```text
PRESEEDED_FINALIZER_FILE_COUNT=0
```

Require after produce:

```text
FINALIZER_DERIVED_SUMMARY_FIELD_COUNT=17
FINALIZER_SUMMARY_LITERAL_FALLBACK_COUNT=0

FINALIZER_STAGE_HANDOFF_STATE=
FINALIZER_COMPLETE_PENDING_FULL_ACCEPTANCE
```

Produce must not claim independent-acceptance readiness.

---

# 25. DRAFT / INTEGRITY / FINAL ACCEPTANCE

After actual finalizer:

```text
DRAFT_FINAL acceptance = 290/290
DRAFT_FINAL validator = PASS
acceptance-integrity = PASS

FINAL acceptance = 300/300
FINAL validator = PASS
```

Require:

```text
DRAFT_FINAL_PRIMARY_CHECK_COUNT=290
DRAFT_FINAL_PRIMARY_CHECK_PASS=290

ACCEPTANCE_INTEGRITY_PRODUCER_RESULT=PASS

FINAL_PRIMARY_CHECK_COUNT=300
FINAL_PRIMARY_CHECK_PASS=300
FINAL_PRIMARY_CHECK_FAIL=0
FINAL_PRIMARY_CHECK_NOT_EXECUTED=0

FINAL_FALSE_ACCEPT_COUNT=0
FINAL_IDENTITY_MISMATCH_COUNT=0
FINAL_NOT_EXECUTED_COUNT=0
FINAL_MISSING_REQUIRED_PRODUCER_COUNT=0
FINAL_UNKNOWN_EVIDENCE_ID_COUNT=0
FINAL_UNRESOLVED_EVIDENCE_REFERENCE_COUNT=0
FINAL_ASSERTION_SEMANTIC_RECOMPUTE_FAIL_COUNT=0
FINAL_PRODUCER_RESULT_CONTRACT_FAILURE_COUNT=0
```

---

# 26. HANDOFF SEAL — ONLY ACCEPTANCE-READY DECLARATION

Seal only after FINAL 300/300 and FINAL validator PASS.

Require:
- finalizer PASS;
- acceptance-integrity PASS;
- runtime-freeze manifest;
- exact candidate/validation/run;
- zero false-accept/evidence/identity errors;
- all 17 summary fields;
- canonical final-summary v1 conformance.

Only seal may emit:

```text
handoff_state=READY_FOR_INDEPENDENT_PHASE5_ACCEPTANCE
```

Require:

```text
HANDOFF_SEAL_RESULT=PASS
FINAL_SUMMARY_SCHEMA_CONFORMANCE=PASS
```

---

# 27. SANITIZER V2 — INDEPENDENT POST-MANIFEST FINAL-BYTE PROOF

Preserve sanitized-only upload.

Required sequence:

```text
copy/sanitize
→ parse JSON/XML
→ generate rows from final sanitized bytes
→ write sanitized-manifest.json
→ reopen sanitized-manifest.json
→ independently rescan final directory excluding manifest
→ compare actual path set vs manifest
→ recompute each byte_count and sha256
→ reparse JSON/XML
→ rescan local absolute paths
→ rescan obvious secret patterns
→ verify four governing source files byte-for-byte
→ final PASS/FAIL
```

Require:

```text
SANITIZED_MANIFEST_SELF_EXCLUDED=true
SANITIZED_MANIFEST_SELF_RECURSION=false

SANITIZED_UNMANIFESTED_FILE_COUNT=0
SANITIZED_MISSING_MANIFEST_FILE_COUNT=0
SANITIZED_ARTIFACT_MANIFEST_HASH_MISMATCH_COUNT=0
SANITIZED_BYTE_COUNT_MISMATCH_COUNT=0

SANITIZED_JSON_PARSE_FAIL_COUNT=0
SANITIZED_XML_PARSE_FAIL_COUNT=0
SANITIZED_INVALID_FILE_COUNT=0

SANITIZED_LOCAL_ABSOLUTE_PATH_MATCH_COUNT=0
SANITIZED_OBVIOUS_SECRET_PATTERN_MATCH_COUNT=0
SANITIZED_GOVERNING_SOURCE_HASH_MISMATCH_COUNT=0

SANITIZED_POST_MANIFEST_RESCAN_COUNT=
SANITIZED_MANIFESTED_FILE_COUNT

SANITIZED_POST_MANIFEST_RECONCILIATION=PASS
```

Negative cases at minimum:
1. modify sanitized file after manifest;
2. add unmanifested file;
3. delete manifested file;
4. corrupt JSON;
5. inject `/home/runner/...`;
6. inject obvious secret assignment.

Require:

```text
SANITIZER_NEGATIVE_CASE_COUNT>=6
SANITIZER_NEGATIVE_FALSE_ACCEPT_COUNT=0
```

---

# 28. PRECOMMIT FULL LOCAL REAL-PRODUCER DAG

Before app commit execute the real code path using synthetic-only evidence:
- actual producer contracts;
- actual shadow result builder;
- actual acceptance;
- actual evidence validator;
- actual finalizer produce/seal;
- actual sanitizer.

Do not manually inject fields that are absent from real producer contracts.

Execute:

```text
PRE_FINALIZER 280
→ validate
→ finalizer produce
→ DRAFT_FINAL 290
→ validate
→ acceptance-integrity
→ FINAL 300
→ validate
→ handoff seal
→ sanitizer
```

Require:

```text
LOCAL_DAG_PRE_FINALIZER=280/280
LOCAL_DAG_DRAFT_FINAL=290/290
LOCAL_DAG_FINAL=300/300

LOCAL_DAG_FINALIZER=PASS
LOCAL_DAG_ACCEPTANCE_INTEGRITY=PASS
LOCAL_DAG_FINAL_VALIDATION=PASS
LOCAL_DAG_HANDOFF_SEAL=PASS
LOCAL_DAG_SANITIZER=PASS

LOCAL_DAG_REAL_SHADOW_RESULT_BUILDER_USED=true
LOCAL_DAG_HANDCRAFTED_SHADOW_FIELD_INJECTION_COUNT=0
```

---

# 29. APPLICATION PRECOMMIT TEST MATRIX — E2 ENVIRONMENT BOUNDARY

The current host has no independently available native SQL Server runtime.
Native SQL Server and real-browser acceptance are therefore remote-authoritative
and are not application-precommit requirements.

First require collection/contract integrity only:

```bash
pytest --collect-only -q backend/tests/test_phase5_sqlserver_runtime.py
```

Require exactly:

```text
PHASE5_SQLSERVER_RUNTIME_TEST_COLLECTED=16
PHASE5_SQLSERVER_RUNTIME_TEST_COLLECTION_FAIL=0
PHASE5_SQLSERVER_RUNTIME_REQUIRES_MSSQL_PYODBC=true
LOCAL_NATIVE_SQLSERVER_RUNTIME_REQUIRED_FOR_APP_COMMIT=false
LOCAL_NATIVE_SQLSERVER_RUNTIME_ACCEPTANCE_CREDIT=0
```

Run local deterministic/backend validation:

```bash
pytest -q \
  backend/tests/test_phase5_contracts.py \
  backend/tests/test_phase5_evidence_integrity.py \
  backend/tests/test_phase5_finalizer_negative.py \
  backend/tests/test_phase5_classifier.py \
  backend/tests/test_phase5_portability.py \
  backend/tests/test_phase4_corpus_app_integration.py

pytest -q --ignore=backend/tests/test_phase5_sqlserver_runtime.py

python -m compileall -q backend scripts

python scripts/phase5/source_preflight.py \
  --output artifacts/phase5-r3r1r2-source-preflight.json \
  --planned-workflow <planned-R3R1R2-workflow-path>

python scripts/phase5/reproducibility.py

python scripts/phase5/corpus_coverage.py \
  --corpus contracts/amec/phase5/AMEC_CLASSIFIER_ROBUSTNESS_CORPUS_V2.json

git diff --check
```

Do not execute locally:

```text
pytest -q backend/tests/test_phase5*.py
pytest -q backend/tests
```

because those commands transitively include the native SQL Server module.

Frontend local precommit:

```bash
cd frontend
npm ci
npm test -- --run
npx tsc -b
npx vite build
```

If the isolated worktree lacks tracked frontend files, restore only the missing
tracked bytes from the exact candidate index; do not stage those restorations.

Require zero actual deterministic/backend/frontend failures.

A missing local native MSSQL endpoint is:

```text
LOCAL_NATIVE_SQLSERVER_RUNTIME=ENVIRONMENT_BLOCKED_LOCAL_ONLY
```

and is not an application failure.

No local SQL Server/browser result earns Phase5 runtime acceptance credit.

---

# 30. NO-LOOP PRECOMMIT GATE — MUST PASS BEFORE COMMIT

Write local-only:

```text
artifacts/phase5-r3r1r2-no-loop-preflight.json
```

Require exact:

```text
SOURCE_PREFLIGHT_VERSION=6
DEFINITE_BLOCKER_COUNT=0

PRODUCER_RESULT_CONTRACT_MISSING_COUNT=0
SUMMARY_CONSUMED_PATH_UNDECLARED_COUNT=0
ASSERTION_CONSUMED_PATH_UNDECLARED_COUNT=0

ASSERTION_EVIDENCE_SPEC_COUNT=300
ASSERTION_EVIDENCE_SPEC_DEFAULT_FALLBACK_COUNT=0
ASSERTION_EVIDENCE_SPEC_KEYWORD_HEURISTIC_COUNT=0

ASSERTION_SEMANTIC_MUTATION_CASE_COUNT=300
ASSERTION_SEMANTIC_MUTATION_FALSE_ACCEPT_COUNT=0

FINALIZER_SUMMARY_SOURCE_CONTRACT_AUDIT_COUNT=17
FINALIZER_SUMMARY_SOURCE_UNPROVABLE_PATH_COUNT=0
FINALIZER_SUMMARY_DERIVATION_FALSE_ACCEPT_COUNT=0

PIPELINE_STAGE_COUNT=12
PIPELINE_CYCLE_COUNT=0
PLANNED_WORKFLOW_CYCLE_COUNT=0

FINAL_SUMMARY_SCHEMA_CONFORMANCE_STATIC=PASS

SANITIZER_POST_MANIFEST_INDEPENDENT_RECONCILIATION_PRESENT=true
SANITIZER_NEGATIVE_FALSE_ACCEPT_COUNT=0

EVERY_WORKFLOW_CLI_ARGUMENT_VALID=true
EVERY_WORKFLOW_RESULT_NAME_RESOLVABLE=true
ONLY_SANITIZED_EVIDENCE_UPLOADED=true

LOCAL_PRECOMMIT_NATIVE_SQLSERVER_EXECUTION_REQUIRED=false
LOCAL_FULL_BACKEND_EXCLUDES_NATIVE_SQLSERVER_MODULE=true

REMOTE_WORKFLOW_NATIVE_SQLSERVER_EXECUTION_REQUIRED=true
REMOTE_WORKFLOW_NATIVE_SQLSERVER_TEST_COMMAND_PRESENT=true
REMOTE_WORKFLOW_NATIVE_SQLSERVER_TEST_COUNT=16
REMOTE_WORKFLOW_FULL_BACKEND_EXCLUDES_RUNTIME_MODULE=true
REMOTE_WORKFLOW_REAL_BROWSER_REQUIRED=true
REMOTE_WORKFLOW_REAL_BROWSER_USES_SQLSERVER_BACKED_API=true

LOCAL_RUNTIME_EVIDENCE_PROMOTED_TO_REMOTE_ACCEPTANCE_COUNT=0
```

If any fail:

```text
RESULT=STOP_PHASE5_R3R1R2_APPLICATION_PRECOMMIT_FAILED
FIRST_FAILED_GATE=<exact>
FAILURE_EVIDENCE=<exact>
```

STOP before commit.

---

# 31. APPLICATION DIFF BOUNDARY

Require all changed paths belong to Section 10.

Require all classifier/frozen/schema paths in Section 9 byte-identical to
`8cae536...`.

Require:

```text
GOVERNING_SOURCE_MUTATION_COUNT=0
CLASSIFIER_BEHAVIOR_MUTATION_COUNT=0
FROZEN_CORPUS_RESULT_MUTATION_COUNT=0
FINAL_SUMMARY_SCHEMA_FILE_MUTATION_COUNT=0
```

No generated `artifacts/` output may be staged.

`git diff --check` must PASS.

---

# 32. CREATE EXACTLY ONE APPLICATION COMMIT

Branch:

```text
phase5-classifier-shadow-validation-r3r1r2-v1
```

Exact parent:

```text
8cae536262756b15e26f08cc5eeed7641c0402bc
```

Recommended commit message:

```text
fix(phase5): close producer contracts and final evidence truth
```

Record:

```text
PHASE5_R3R1R2_APPLICATION_SHA=<exact>
PHASE5_R3R1R2_APPLICATION_TREE=<exact>
```

Push only fresh app branch.

No main.
No tag.
No release.

---

# 33. CREATE FRESH VALIDATION BRANCH DIRECTLY FROM FINAL APP SHA

Create:

```text
PHASE5_R3R1R2_VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-r3r1r2-v1
```

directly from final application SHA.

Create exactly one workflow-only child commit.

Do not branch from old validation SHA.

---

# 34. VALIDATION WORKFLOW SOURCE AUTHORITY

Use exact working R3R1R1 workflow bytes:

```text
SOURCE_VALIDATION_SHA=
1c0cd794589118d097765c84666100f72551643b

SOURCE_WORKFLOW_PATH=
.github/workflows/phase5-classifier-shadow-validation-ci-r3r1r1.yml

SOURCE_WORKFLOW_BLOB_SHA1=
2c5bda0cb501b1d1afe7ea27b9386670041e9fc1
```

Create:

```text
.github/workflows/phase5-classifier-shadow-validation-ci-r3r1r2.yml
```

Preserve working SQL Server/browser/runtime logic.

Validation workflow changes are mechanical:
- display name;
- trigger branch;
- candidate SHA/parent;
- candidate branch;
- validation branch;
- self-check path;
- evidence temp name;
- planned-workflow path;
- branch-specific artifact/handoff name.

Do not redesign the working runtime harness.

---

# 35. EXACT WORKFLOW SHA / BRANCH BINDING

Set:

```text
CANDIDATE_SHA=<PHASE5_R3R1R2_APPLICATION_SHA>

CANDIDATE_PARENT_SHA=
8cae536262756b15e26f08cc5eeed7641c0402bc

CANDIDATE_BRANCH=
phase5-classifier-shadow-validation-r3r1r2-v1

VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-r3r1r2-v1
```

Require runtime:

```bash
test "$(git rev-parse "refs/remotes/origin/$CANDIDATE_BRANCH")" = "$CANDIDATE_SHA"
test "$(git rev-parse HEAD^1)" = "$CANDIDATE_SHA"
test "$(git rev-parse HEAD^1^1)" = "$CANDIDATE_PARENT_SHA"
```

Require validation commit changes exactly one workflow file.

---

# 36. FULL NATIVE SQL SERVER + REAL BROWSER RERUN — FROM BEGINNING

Rerun fresh:
- Ubuntu 22.04 x86-64;
- Docker;
- Python 3.12;
- Node;
- ODBC Driver 18;
- Playwright Chromium;
- SQL Server 2022 Developer;
- fresh database;
- Alembic exact head;
- native Phase5 SQL Server 16 gates;
- actual SQL Server-backed shadow replay;
- backend targeted/full;
- Phase4 integration regression;
- authority/observability/security;
- real API/frontend;
- required browser paths;
- browser quality;
- frontend targeted/full/build.

No inherited R3R1R1 PASS.

The fresh remote workflow must execute:

```bash
python -m pytest -q backend/tests/test_phase5_sqlserver_runtime.py
```

against an actual:

```text
DATABASE_URL=mssql+pyodbc://...
```

and the remote full-backend producer must separately execute:

```bash
pytest -q --ignore=backend/tests/test_phase5_sqlserver_runtime.py
```

Require:

```text
PHASE5_SQLSERVER_TARGETED_GATE_COUNT=16
PHASE5_SQLSERVER_TARGETED_PASS=16
PHASE5_SQLSERVER_TARGETED_FAIL=0
PHASE5_SQLSERVER_TARGETED_SKIP=0

REMOTE_WORKFLOW_REAL_BROWSER_REQUIRED=true
REMOTE_WORKFLOW_REAL_BROWSER_USES_SQLSERVER_BACKED_API=true
```

No Mac Docker.
No Azure SQL service.
No real data.

---

# 37. REMOTE BASE PRODUCER SUCCESS

Require:

```text
SQLSERVER_MAJOR=16
MIGRATION_HEAD=baseline_phase4_v36_azure_sql

PHASE5_SQLSERVER_TARGETED_PASS=16
PHASE5_SQLSERVER_TARGETED_FAIL=0

SHADOW_STATE=REVIEW_COMPARE_ONLY
NEW_SOURCE_READS=0
NEW_SOURCE_BYTES=0
LLM_EXTERNAL_CALL_COUNT=0
REAL_CONTENT=false

CRITICAL_FALSE_PROMOTIONS=0

PHASE5_BROWSER_REQUIRED_PATH_COUNT=10
PHASE5_BROWSER_REQUIRED_PATH_PASS=10
PHASE5_BROWSER_REQUIRED_PATH_FAIL=0
PHASE5_BROWSER_REQUIRED_PATH_SKIP=0

BACKEND_REGRESSION=PASS
FRONTEND_REGRESSION=PASS
FRONTEND_BUILD=PASS
```

---

# 38. REMOTE SOURCE-CONTRACT SUCCESS

Require:

```text
SOURCE_PREFLIGHT_VERSION=6
DEFINITE_BLOCKER_COUNT=0

PRODUCER_RESULT_CONTRACT_MISSING_COUNT=0

FINALIZER_SUMMARY_SOURCE_MAP_COUNT=17
FINALIZER_SUMMARY_SOURCE_UNPROVABLE_PATH_COUNT=0
FINALIZER_SUMMARY_SOURCE_TYPE_MISMATCH_COUNT=0

ASSERTION_EVIDENCE_SPEC_COUNT=300
ASSERTION_EVIDENCE_SPEC_MISSING_COUNT=0
ASSERTION_EVIDENCE_SPEC_DEFAULT_FALLBACK_COUNT=0
ASSERTION_EVIDENCE_SPEC_KEYWORD_HEURISTIC_COUNT=0

ASSERTION_CONSUMED_PATH_UNDECLARED_COUNT=0

ASSERTION_SEMANTIC_MUTATION_CASE_COUNT=300
ASSERTION_SEMANTIC_MUTATION_FALSE_ACCEPT_COUNT=0

PIPELINE_STAGE_COUNT=12
PIPELINE_CYCLE_COUNT=0
PLANNED_WORKFLOW_CYCLE_COUNT=0

FINAL_SUMMARY_SCHEMA_CONFORMANCE_STATIC=PASS
SANITIZER_POST_MANIFEST_INDEPENDENT_RECONCILIATION_PRESENT=true
```

---

# 39. REMOTE 12-STAGE DAG — ALL FRESH

Require exact ordering/state:

```text
BASE_EVIDENCE=PASS

PRE_FINALIZER_ACCEPTANCE=280/280
PRE_FINALIZER_VALIDATION=PASS

FINALIZER_PRODUCE=PASS

DRAFT_FINAL_ACCEPTANCE=290/290
DRAFT_FINAL_VALIDATION=PASS

ACCEPTANCE_INTEGRITY=PASS

FINAL_ACCEPTANCE=300/300
FINAL_VALIDATION=PASS

HANDOFF_SEAL=PASS

SANITIZER=PASS

UPLOAD=PASS
```

No skipped stage.

---

# 40. REMOTE FINALIZER SUCCESS

Require:

```text
FINALIZER_REQUIRED_DERIVED_SUMMARY_FIELD_COUNT=17
FINALIZER_DERIVED_SUMMARY_FIELD_COUNT=17
FINALIZER_SUMMARY_SOURCE_MAP_MISSING_COUNT=0
FINALIZER_SUMMARY_LITERAL_FALLBACK_COUNT=0

FINALIZER_META_CANDIDATE_BINDING=true
FINALIZER_META_VALIDATION_BINDING=true
FINALIZER_META_RUN_BINDING=true

FINALIZER_STAGE_HANDOFF_STATE=
FINALIZER_COMPLETE_PENDING_FULL_ACCEPTANCE

SHADOW_REPLAY_NEW_SOURCE_READS_FIELD_PRESENT=true
FINALIZER_NEW_SOURCE_READS_DERIVATION=PASS
```

---

# 41. REMOTE 300-ROW EVIDENCE TRUTH

Require:

```text
FINAL_PRIMARY_CHECK_COUNT=300
FINAL_PRIMARY_CHECK_PASS=300
FINAL_PRIMARY_CHECK_FAIL=0
FINAL_PRIMARY_CHECK_NOT_EXECUTED=0

ASSERTION_SEMANTIC_RECOMPUTE_COUNT=300
ASSERTION_SEMANTIC_RECOMPUTE_FAIL_COUNT=0
ASSERTION_SEMANTIC_PROOF_MISMATCH_COUNT=0

PRODUCER_RESULT_CONTRACT_FAILURE_COUNT=0

PASS_ROW_GENERIC_CATEGORY_ONLY_PROOF_COUNT=0
PASS_ROW_TAUTOLOGICAL_EXPECTED_OBSERVED_COUNT=0

BOUNDARY_GENERIC_RESULT_ONLY_PROOF_COUNT=0
SQLSERVER_GENERIC_RESULT_ONLY_PROOF_COUNT=0
BROWSER_GENERIC_RESULT_ONLY_PROOF_COUNT=0
REGRESSION_GENERIC_RESULT_ONLY_PROOF_COUNT=0

FINAL_FALSE_ACCEPT_COUNT=0
```

---

# 42. REMOTE FINAL SUMMARY / HANDOFF CONTRACT TRUTH

Generated:

```text
phase5-final-summary.json
```

must satisfy:

```text
version=1
result=PASS
acceptance_check_count=300
failed_acceptance_check_count=0

shadow_state=REVIEW_COMPARE_ONLY
new_source_reads=0
llm_external_call_count=0
llm_real_content_mode=DISABLED

handoff_state=READY_FOR_INDEPENDENT_PHASE5_ACCEPTANCE

RUN_EVIDENCE_STATE=COMPLETE_PASS

FINAL_SUMMARY_SCHEMA_CONFORMANCE=PASS
FINAL_SUMMARY_17_FIELD_DERIVATION_MATCH=PASS
```

---

# 43. REMOTE SANITIZER / UPLOAD SUCCESS

Require:

```text
SANITIZED_JSON_PARSE_FAIL_COUNT=0
SANITIZED_XML_PARSE_FAIL_COUNT=0
SANITIZED_INVALID_FILE_COUNT=0

SANITIZED_UNMANIFESTED_FILE_COUNT=0
SANITIZED_MISSING_MANIFEST_FILE_COUNT=0
SANITIZED_ARTIFACT_MANIFEST_HASH_MISMATCH_COUNT=0
SANITIZED_BYTE_COUNT_MISMATCH_COUNT=0

SANITIZED_LOCAL_ABSOLUTE_PATH_MATCH_COUNT=0
SANITIZED_OBVIOUS_SECRET_PATTERN_MATCH_COUNT=0
SANITIZED_GOVERNING_SOURCE_HASH_MISMATCH_COUNT=0

SANITIZED_POST_MANIFEST_RECONCILIATION=PASS
```

Upload sanitized evidence only.

Never upload working evidence.

---

# 44. FAILURE POLICY — NO AUTOMATIC R3R1R3

If application precommit fails:

```text
RESULT=STOP_PHASE5_R3R1R2_APPLICATION_PRECOMMIT_FAILED
FIRST_FAILED_GATE=<exact>
FAILURE_EVIDENCE=<exact sanitized>
```

STOP.

If remote fails:

```text
RESULT=STOP_PHASE5_R3R1R2_REMOTE_VALIDATION_FAILED

FIRST_FAILED_STAGE=<exact>
FIRST_FAILED_GATE=<exact if applicable>
FAILURE_EVIDENCE=<exact sanitized>

PHASE5_R3R1R2_APPLICATION_SHA=<exact>
PHASE5_R3R1R2_VALIDATION_SHA=<exact>

RUN_ID=<exact>
JOB_ID=<exact>
ARTIFACT_ID=<exact or NOT_UPLOADED>
ARTIFACT_SHA256=<exact or NOT_AVAILABLE>

SECOND_APPLICATION_COMMIT_CREATED=false
SECOND_WORKFLOW_COMMIT_CREATED=false

MAIN_CHANGED=false
AZURE_ACCESSED=false
ENTRA_ACCESSED=false
SYNOLOGY_ACCESSED=false
SMB_ACCESSED=false
REAL_DATA_USED=false

NEXT=STOP
```

Do not automatically create R3R1R3.
Do not make a second repair in this authorization.
Do not weaken failed evidence specs or producer contracts.

---

# 45. SAFETY / AUTHORITY

Throughout:

```text
AZURE_ACCESSED=false
AZURE_RESOURCE_CREATED=false
AZURE_RESOURCE_UPDATED=false
AZURE_RESOURCE_DELETED=false

ENTRA_ACCESSED=false

SYNOLOGY_ACCESSED=false
SMB_ACCESSED=false

REAL_DATA_USED=false
NEW_AMEC_SOURCE_READS=0
NEW_AMEC_SOURCE_BYTES=0

AUTO_PROMOTION_ENABLED=false
REAL_LIVE_SHADOW_ENABLED=false
SYNOLOGY_WRITEBACK_ENABLED=false

MAIN_CHANGED=false
MAIN_PUSHED=false
TAG_CREATED=false
RELEASE_CREATED=false
DEPLOYMENT_STARTED=false

PHASE6_STARTED=false
```

---

# 46. TRUTHFUL VERIFIED STATE

A complete fresh R3R1R2 run may establish:

```text
VERIFIED_LOCAL=true
VERIFIED_SQLSERVER_COMPAT=true
VERIFIED_BROWSER=true
```

It must preserve:

```text
VERIFIED_AZURE_SQL=false
VERIFIED_DEPLOYED=false
```

Do not claim Azure SQL-service verification from SQL Server container proof.

Do not self-accept Phase5.

---

# 47. SUCCESS ARTIFACT / HANDOFF VERIFICATION

After successful sanitized upload:

1. download exact artifact;
2. hash ZIP/archive;
3. re-extract;
4. verify application/validation/run triple identity;
5. independently reopen/recompute sanitized manifest;
6. independently validate canonical final-summary v1 contract;
7. independently recompute all 17 summary fields from producer evidence;
8. independently recompute all 300 assertion proofs if feasible; minimum is
   deterministic full validator replay over all 300;
9. verify 280/290/300 stage counts;
10. verify finalizer → acceptance-integrity → FINAL → seal ordering;
11. verify no local paths/secrets;
12. verify governing files;
13. verify only sanitized evidence was uploaded.

Create fresh independent-review handoff.

Do not declare independent acceptance.

---

# 48. FINAL SUCCESS RETURN

Only if the entire remote run, sanitizer, upload, and downloaded handoff
verification pass:

```text
RESULT=PHASE5_FINAL_R3R1R2_CANDIDATE_READY_FOR_INDEPENDENT_ACCEPTANCE

PHASE5_R3R1R2_APPLICATION_BRANCH=
phase5-classifier-shadow-validation-r3r1r2-v1

PHASE5_R3R1R2_APPLICATION_SHA=<exact>
PHASE5_R3R1R2_APPLICATION_PARENT=
8cae536262756b15e26f08cc5eeed7641c0402bc
PHASE5_R3R1R2_APPLICATION_TREE=<exact>

PHASE5_R3R1R2_VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-r3r1r2-v1

PHASE5_R3R1R2_VALIDATION_SHA=<exact>
PHASE5_R3R1R2_VALIDATION_PARENT=
<PHASE5_R3R1R2_APPLICATION_SHA>

REMOTE_RUN_ID=<exact>
REMOTE_JOB_ID=<exact>
REMOTE_ARTIFACT_ID=<exact>
REMOTE_ARTIFACT_SHA256=<exact>

R3R1R1_FINALIZER_NEW_SOURCE_READS_DEFECT_CLOSED=true
PRODUCER_RESULT_CONTRACT_CLOSURE=PASS

ASSERTION_EVIDENCE_SPEC_COUNT=300
ASSERTION_SEMANTIC_MUTATION_CASE_COUNT=300
ASSERTION_SEMANTIC_MUTATION_FALSE_ACCEPT_COUNT=0

FINALIZER_SUMMARY_SOURCE_MAP_COUNT=17
FINALIZER_SUMMARY_SOURCE_UNPROVABLE_PATH_COUNT=0
FINALIZER_SUMMARY_DERIVATION_FALSE_ACCEPT_COUNT=0

FINAL_SUMMARY_PAYLOAD_VERSION=1
FINAL_SUMMARY_SCHEMA_CONFORMANCE=PASS

SANITIZED_POST_MANIFEST_RECONCILIATION=PASS

SQLSERVER_MAJOR=16
MIGRATION_HEAD=baseline_phase4_v36_azure_sql

PHASE5_SQLSERVER_TARGETED_PASS=16
PHASE5_SQLSERVER_TARGETED_FAIL=0

PHASE5_BROWSER_REQUIRED_PATH_PASS=10
PHASE5_BROWSER_REQUIRED_PATH_FAIL=0

CRITICAL_FALSE_PROMOTIONS=0

PRE_FINALIZER_PRIMARY_CHECK_PASS=280
DRAFT_FINAL_PRIMARY_CHECK_PASS=290
FINAL_PRIMARY_CHECK_PASS=300

FINAL_ASSERTION_SEMANTIC_RECOMPUTE_FAIL_COUNT=0
FINAL_FALSE_ACCEPT_COUNT=0

RUN_EVIDENCE_STATE=COMPLETE_PASS

VERIFIED_LOCAL=true
VERIFIED_SQLSERVER_COMPAT=true
VERIFIED_BROWSER=true

VERIFIED_AZURE_SQL=false
VERIFIED_DEPLOYED=false

AUTO_PROMOTION_ENABLED=false
REAL_LIVE_SHADOW_ENABLED=false
SYNOLOGY_WRITEBACK_ENABLED=false

MAIN_CHANGED=false
MAIN_PUSHED=false

AZURE_ACCESSED=false
ENTRA_ACCESSED=false
SYNOLOGY_ACCESSED=false
SMB_ACCESSED=false
REAL_DATA_USED=false

PHASE5_CODEX_SELF_ACCEPTED=false
PHASE5_INDEPENDENT_ACCEPTANCE=PENDING
PHASE6_STARTED=false

NEXT=INDEPENDENT_PHASE5_R3R1R2_ACCEPTANCE_REVIEW
```

Then STOP.

No further implementation mutation is authorized after a successful R3R1R2
return.
