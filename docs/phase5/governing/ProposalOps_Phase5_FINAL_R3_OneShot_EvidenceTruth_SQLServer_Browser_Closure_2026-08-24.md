# ONE-SHOT CODEX OWNER AUTHORIZATION — PROPOSALOPS / AMEC PHASE 5 FINAL R3
## Evidence-truth repair + deterministic freeze proof + actual SHADOW replay + native SQL Server 2022 + real browser
**Date:** 2026-08-24 / 2026-08-25 UTC boundary

---

# 0. OWNER AUTHORIZATION / SUPERSESSION

The Owner explicitly authorizes one new bounded Phase5 repair/replacement
revision after the exhausted R2 attempt.

This R3 prompt supersedes the failed R2 execution state for **repair authority**
only. Preserve R2 as immutable historical provenance.

Do not rerun R2 unchanged.

R3 objective:

```text
repair all independently confirmed Phase5 evidence-integrity defects
+
repair all currently known deterministic validation-workflow blockers
+
preserve classifier/freeze business behavior
+
execute one complete fresh native SQL Server + real browser validation
+
STOP for independent Phase5 acceptance
```

This is not deployment authorization.

No Azure mutation.
No Entra mutation.
No Synology/SMB access.
No real AMEC data.
No continuous live shadow.
No writeback.
No Phase6.

---

# 1. GOVERNING SOURCE / STATE RULE

Use:

```text
latest explicit Owner/product decision
+ later executable repository/runtime evidence
+ later independent acceptance where required
= governing current state
```

Exact run/artifact evidence outranks prompt intent.

Do not collapse:

```text
IMPLEMENTED
VERIFIED_LOCAL
VERIFIED_SQLSERVER_COMPAT
VERIFIED_BROWSER
VERIFIED_AZURE_SQL
VERIFIED_DEPLOYED
INDEPENDENTLY_ACCEPTED
```

into one state.

---

# 2. EXACT PHASE4 ENTRY — MUST REMAIN IMMUTABLE

Require live:

```text
PHASE4_INDEPENDENT_ACCEPTANCE=PASS

PHASE4_ACCEPTED_SHA=
707003fc16767fb28b9c968fbcf168ab03ebadc1

PHASE4_ACCEPTED_TREE=
af473134f6a92b9dc9919eae71f1e02a3ed81e1e

PHASE4_ACCEPTANCE_VALIDATION_SHA=
d56817d27a9aaaf69aa08b5e314f78297ed45376

PHASE4_ACCEPTANCE_RUN_ID=
32778775085

PHASE4_ACCEPTANCE_ARTIFACT_SHA256=
877f1e39c4bb0e16187dcf4de76ba47cff7df3bdf7cb01a2ae6027da1df4f4a6
```

Preserve Phase4 accepted bytes.

No Phase4 reimplementation.

---

# 3. EXACT FAILED PHASE5 R2 STATE — REPROVE FIRST

Application:

```text
PHASE5_R2_APPLICATION_BRANCH=
phase5-classifier-shadow-validation-v1

PHASE5_R2_APPLICATION_SHA=
ca60459f2103cbf30e52e05c59b8af6d7714be12

PHASE5_R2_APPLICATION_PARENT=
707003fc16767fb28b9c968fbcf168ab03ebadc1

PHASE5_R2_APPLICATION_TREE=
fb6699657a562b079c11b96c03961c85931a0e66
```

Validation:

```text
PHASE5_R2_VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-v1

PHASE5_R2_VALIDATION_SHA=
3842fc0faf4c95bf933d0a56cd8773162e97f893

PHASE5_R2_VALIDATION_PARENT=
ca60459f2103cbf30e52e05c59b8af6d7714be12

PHASE5_R2_VALIDATION_TREE=
c45bcad7e229fa7902713a9fad31fa51aea62615

PHASE5_R2_WORKFLOW_PATH=
.github/workflows/phase5-classifier-shadow-validation-ci.yml

PHASE5_R2_WORKFLOW_BLOB_SHA1=
03dfbe144e9a0e61b7ddc648ebe9cc8cf711f560
```

Failed remote run:

```text
RUN_ID=32792676257
JOB_ID=97637300326
ARTIFACT_ID=9543681332

ARTIFACT_SHA256=
6406064757f308c25c983b895acb1993f6b8626013c1d579be2d4b39be62b6b3

FIRST_FAILED_GATE=
NATIVE_SQL_SERVER_2022_DEVELOPER_BOOTSTRAP

FIRST_FAILED_SUBGATE=
SQLSERVER_CONTAINER_IMAGE_MANIFEST

FAILED_IMAGE=
mcr.microsoft.com/mssql/server:2022-GA-ubuntu-20.04
```

Reprove the exact failed artifact / job before mutation.

Require:

```text
R2_RUN_RESULT=VALID_FAIL_CLOSED
R2_SQLSERVER_CONTAINER_EXIT_CODE=125
R2_DOWNSTREAM_RUNTIME_NOT_EXECUTED=true
R2_BROWSER_NOT_EXECUTED=true
R2_FINALIZER_NOT_EXECUTED=true
```

If materially different:

```text
RESULT=STOP_PHASE5_R3_DIAGNOSIS_CHANGED
```

STOP.

---

# 4. NEW R3 BRANCHES — LIVE ABSENCE GATE

Before mutation require both absent:

```text
phase5-classifier-shadow-validation-r3-v1
phase5-classifier-shadow-validation-ci-r3-v1
```

If either exists:

```text
RESULT=STOP_PHASE5_R3_BRANCH_COLLISION
```

STOP.

---

# 5. CURRENT OWNER DATABASE DECISION

Preserve current governing target:

```text
DATABASE_TARGET_DECISION=OWNER_CONFIRMED
DATABASE_ENGINE_TARGET=AZURE_SQL_SQL_SERVER_ENGINE

AZURE_SQL_SERVICE_VARIANT=AZURE_SQL_DATABASE
AZURE_SQL_DATABASE_SELECTED=true
AZURE_SQL_MANAGED_INSTANCE_SELECTED=false

AZURE_SQL_EXACT_SKU=OWNER_DECISION_PENDING
```

R3 uses local disposable Microsoft SQL Server 2022 for engine-compatibility
proof.

It does **not** establish actual Azure SQL service verification.

---

# 6. R3 IS NOT A CLASSIFIER REDESIGN

R2 classifier/freeze behavior is preserved.

R3 must not modify:

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
```

Require exact byte equality against `ca60459...` for those paths.

If classifier/rule/corpus/holdout behavior must change:

```text
RESULT=STOP_PHASE5_R3_CLASSIFIER_BEHAVIOR_SCOPE_EXPANSION_REQUIRED
```

STOP. Do not silently burn/rebuild holdout.

---

# 7. CREATE FRESH R3 APPLICATION BRANCH

Create:

```text
PHASE5_R3_APPLICATION_BRANCH=
phase5-classifier-shadow-validation-r3-v1

PHASE5_R3_APPLICATION_BASE=
ca60459f2103cbf30e52e05c59b8af6d7714be12
```

Directly from exact R2 application candidate.

No merge.
No rebase.
No amend.
No force push.

---

# 8. R3 APPLICATION MUTATION SURFACE

R3 may modify only this evidence/validation surface:

```text
scripts/phase5/common.py
scripts/phase5/registry.py
scripts/phase5/source_preflight.py
scripts/phase5/browser_evidence.py
scripts/phase5/sqlserver_targeted.py
scripts/phase5/shadow_replay.py
scripts/phase5/acceptance.py
scripts/phase5/evidence_validate.py
scripts/phase5/finalize.py
scripts/phase5/phase5_finalize.py
scripts/phase5/reproducibility.py
scripts/phase5/runtime_evidence.py

backend/tests/test_phase5_contracts.py
backend/tests/test_phase5_finalizer_negative.py
backend/tests/test_phase5_evidence_integrity.py
backend/tests/test_phase5_sqlserver_runtime.py

frontend/browser-real-stack/phase5-classifier-shadow.spec.ts
frontend/tests/phase5-review-evidence.test.tsx
```

New files from that exact list are permitted.

A path may remain unchanged if not needed.

No other application path is authorized.

If another path is truly required:

```text
RESULT=STOP_PHASE5_R3_APPLICATION_SCOPE_EXPANSION_REQUIRED
REQUIRED_PATH=<exact>
REASON=<exact>
```

STOP before commit.

---

# 9. R3 REPAIR LEDGER — ALL RUN-10 DEFECTS MUST CLOSE

Before app commit maintain an explicit machine-readable repair ledger with these
exact rows:

```text
C01_SOURCE_PREFLIGHT_HARDCODED_FIELDS
C02_FIXED_SHA_DESCENDANT_AUDIT_INCOMPLETE
C03_BROWSER_EVIDENCE_HARDCODED_PASS
C04_SQLSERVER_EVIDENCE_HARDCODED_PASS
C05_SHADOW_REPLAY_HARDCODED_PASS
C06_ACCEPTANCE_GENERATOR_HARDCODED_PASS
C07_ACCEPTANCE_EVIDENCE_SELF_REFERENTIAL
C08_EVIDENCE_VALIDATOR_SEMANTIC_GAP
C09_FINALIZER_DEFAULT_RUNTIME_PASS
C10_FINALIZER_CANDIDATE_SHA_NOT_EXACT
C11_FINALIZER_SUMMARY_HARDCODED_RUNTIME
C12_REPRODUCIBILITY_NOT_REGENERATED

W01_INVALID_SQLSERVER_IMAGE_TAG
W02_SQLSERVER_PASSWORD_NOT_EXPORTED
W03_IN_CONTAINER_SQLCMD_BOOTSTRAP
W04_PLAYWRIGHT_BROWSER_NOT_EXPLICITLY_INSTALLED
```

Before commit every row must be:

```text
CLOSED_WITH_EXECUTABLE_REGRESSION
```

or R3 must STOP.

Write local-only:

```text
artifacts/phase5-r3-repair-ledger.json
```

Do not commit generated ledger output.

---

# 10. CENTRAL EVIDENCE REGISTRY — ACTUAL PRODUCER CONTRACTS

Upgrade the existing central registry rather than creating ad hoc evidence
names in the workflow.

Every registered producer must define at minimum:

```text
producer_id
raw_log_name
meta_name
result_name
runtime_required
```

The registry remains the source of truth for accepted producer IDs.

Runtime-required producers must include at minimum:

```text
sqlserver-bootstrap
sqlserver-targeted
shadow-replay
browser-required-paths
browser-quality
backend-targeted
phase4-integration-regression
backend-full
frontend-targeted
frontend-full
frontend-build
authority-denial
observability
security-hygiene
```

Source/deterministic producers include at minimum:

```text
entry-identity
input-identity
source-preflight
freeze-reproducibility
classifier-calibration
classifier-validation
classifier-holdout
classifier-cross-context
classifier-path-counterfactual
acceptance
finalizer
```

No producer may report PASS solely because its source file exists.

---

# 11. C01/C02 — SOURCE PREFLIGHT MUST ACTUALLY EXECUTE ITS CLAIMS

Repair `source_preflight.py`.

No output field representing a check may be assigned zero/true unless computed
from inspected source/repository state.

At minimum mechanically inspect:

```text
imports/module paths
API registration
Phase4 service signatures
Pydantic constructors
SQLAlchemy constructor fields
SQLAlchemy mapped attributes
SQL Server-sensitive SQL
text() implicit binds

canonical Phase5 filenames
producer/consumer evidence names
input-identity references
freeze references
acceptance producer IDs
finalizer producer requirements

fixed-SHA repository references
fixed ancestor git-show/read patterns
current descendant path enumeration
descendant-only additive files
fixed path/count assumptions

Playwright config/spec paths
all ten required browser IDs
business API mock/intercept patterns
role/capability names

workflow-required script paths
```

## Fixed-SHA descendant audit

Do not special-case only `LEGACY_BOOLEAN_BASELINE_SHA`.

The audit must mechanically identify patterns equivalent to:

```text
enumerate/current HEAD paths
→ read same path from fixed ancestor SHA
```

and report any descendant-only ancestor read that would fail.

Require:

```text
PHASE5_SOURCE_PREFLIGHT_VERSION=3
PHASE5_SOURCE_PREFLIGHT_DEFINITE_BLOCKER_COUNT=0

PHASE5_INHERITED_FIXED_SHA_TEST_COUNT=<actual>
PHASE5_INHERITED_FIXED_SHA_DESCENDANT_BLOCKER_COUNT=0

PHASE5_INVALID_MODEL_CONSTRUCTOR_KWARG_COUNT=0
PHASE5_INVALID_MAPPED_ATTRIBUTE_COUNT=0
PHASE5_IMPLICIT_TEXT_BIND_COUNT=0

PHASE5_CANONICAL_FILENAME_REFERENCE_MISMATCH_COUNT=0
PHASE5_OUTPUT_CONTRACT_MISMATCH_COUNT=0
PHASE5_MISSING_RUNTIME_PATH_COUNT=0
PHASE5_ACCEPTANCE_UNKNOWN_EVIDENCE_ID_COUNT=0
PHASE5_FREEZE_REFERENCED_FILE_MISSING_COUNT=0
PHASE5_BROWSER_REQUIRED_PATH_SPEC_MISSING=0
PHASE5_WORKFLOW_EVIDENCE_NAME_MISMATCH_COUNT=0
```

Add negative unit fixtures proving the preflight detects:
- descendant-only fixed-ancestor read;
- unknown producer;
- missing canonical file;
- implicit textual bind;
- missing browser ID.

Hardcoded-zero implementation is forbidden.

---

# 12. C03 — BROWSER EVIDENCE MUST PARSE REAL PLAYWRIGHT OUTPUT

Repair `browser_evidence.py`.

Required CLI shape:

```bash
python scripts/phase5/browser_evidence.py \
  --playwright-json <actual-json-report> \
  --spec frontend/browser-real-stack/phase5-classifier-shadow.spec.ts \
  --output <browser-quality.result.json>
```

It must consume actual Playwright JSON.

It must locate the exact required IDs:

```text
P5-BROWSER-NEW
P5-BROWSER-AMBIGUOUS_REVIEW
P5-BROWSER-OUT_OF_SCOPE
P5-BROWSER-SECRET_EXCLUDE
P5-BROWSER-MODIFIED_KNOWN_SOURCE
P5-BROWSER-MOVE_RENAME_CANDIDATE
P5-BROWSER-MISSING_CANDIDATE
P5-BROWSER-CORRECTION
P5-BROWSER-PROTECTED_ACTION
P5-BROWSER-PERSONA_SCOPE
```

Derive, never hardcode:

```text
required_path_count
required_path_pass
required_path_fail
required_path_skip
```

Require exact remote success:

```text
PHASE5_BROWSER_REQUIRED_PATH_COUNT=10
PHASE5_BROWSER_REQUIRED_PATH_PASS=10
PHASE5_BROWSER_REQUIRED_PATH_FAIL=0
PHASE5_BROWSER_REQUIRED_PATH_SKIP=0
```

Also source-inspect the required spec and require:

```text
PHASE5_BROWSER_API_MOCK_COUNT_FOR_REQUIRED_PATHS=0
```

Do not treat route/request mocking of ProposalOps business API as proof.

## Browser quality evidence

The current UI already contains loading, error and empty states. Add executable
tests/evidence rather than booleans in Python source.

At minimum prove through browser and/or actual frontend test execution:

```text
LOADING_STATE_PROVEN=true
ERROR_STATE_PROVEN=true
EMPTY_STATE_PROVEN=true
KEYBOARD_ACTION_PATHS_PASS=true
BASIC_ACCESSIBILITY_PASS=true
DEEP_LINK_RESOLUTION_PASS=true
CORRELATION_ID_INSPECTABLE=true
ROOT_EVENT_INSPECTABLE=true
```

If extra Playwright quality tests are required, add them without renaming or
removing the ten required path IDs.

No quality PASS may be manufactured in `browser_evidence.py`.

---

# 13. C04 — SQL SERVER TARGETED PRODUCER MUST CONSUME ACTUAL SQL SERVER PROOF

Repair `sqlserver_targeted.py`.

It must not return SQL Server 16 / migration PASS / 16 gates PASS from constants.

R3 remote execution must first generate real SQL Server evidence.

Reuse the independently accepted Phase4 SQL Server seam and Phase5 targeted
tests rather than duplicating business logic.

At minimum actual runtime must prove:

```text
engine=mssql
SQLSERVER_MAJOR=16
ACTIVE_MIGRATION_HEAD=baseline_phase4_v36_azure_sql
```

The Phase5 required runtime gates remain:

```text
source_event_idempotency
replay_stable_across_time
evidence_intake_idempotency
classification_envelope_immutability
review_locking_concurrency
correction_append_only
reviewed_assertion_promotion
assertion_supersession
projection_idempotency
duplicate_side_effect_protection
rollback
freeze_metadata
hard_gate_short_circuit
out_of_scope_no_projection
secret_exclude_no_projection
protected_action_denial
```

Implement actual SQL Server-backed tests or map them to already-executed exact
Phase4 SQL Server gate evidence + Phase5-specific runtime tests.

Every gate must have a real evidence reference.

Required:

```text
PHASE5_SQLSERVER_TARGETED_GATE_COUNT=16
PHASE5_SQLSERVER_TARGETED_PASS=16
PHASE5_SQLSERVER_TARGETED_FAIL=0
PHASE5_SQLSERVER_TARGETED_SKIP=0
PHASE5_SQLSERVER_TARGETED_SOURCE_ONLY_PASS_COUNT=0
```

`sqlserver_targeted.py` must consume the produced SQL Server runtime/JUnit/gate
evidence and derive its result.

---

# 14. C05 — SHADOW REPLAY MUST EXECUTE REAL SYNTHETIC REPLAY

Repair `shadow_replay.py`.

When used for remote acceptance it must require the current SQL Server-backed
`DATABASE_URL`.

Execute a controlled synthetic replay through the actual Phase5 classifier and
accepted Phase4 persistence/review seams.

At minimum:
1. create a deterministic synthetic classification request;
2. execute it and persist source/evidence/classification envelope;
3. replay the same logical input;
4. prove stable logical event identity/result;
5. prove original ClassificationEnvelope remains immutable;
6. execute an explicit permitted correction/review case;
7. prove correction is append-only;
8. query state before/after;
9. prove no classifier-only VerifiedAssertion;
10. prove no classifier-only typed projection;
11. prove no protected action execution;
12. prove no Synology/writeback/external calls.

Derive:

```text
SHADOW_CLASSIFICATION_GENERATED=true
SHADOW_COMPARISON_RECORDED=true
SHADOW_CLASSIFICATION_ENVELOPE_IMMUTABLE=true
SHADOW_CORRECTION_APPEND_ONLY=true

CLASSIFIER_ONLY_VERIFIED_ASSERTION_PROMOTION_COUNT=0
CLASSIFIER_ONLY_TYPED_PROJECTION_COUNT=0
CLASSIFIER_PROTECTED_ACTION_EXECUTION_COUNT=0

REPLAY_EVENT_ID_STABLE_ACROSS_TIME=true
REPLAY_RESULT_HASH_STABLE_ACROSS_TIME=true
REPLAY_SIDE_EFFECT_DUPLICATE_COUNT=0

SYNOLOGY_WRITEBACK_COUNT=0
LLM_EXTERNAL_CALL_COUNT=0
REAL_CONTENT=false
```

Do not assign those values before querying/executing their proof.

Provide a `--output` result JSON.

---

# 15. C06/C07 — ACCEPTANCE MAY NOT MANUFACTURE 300 PASS CHECKS

Repair `acceptance.py`.

Preserve the >=300 unique primary requirements.

Do **not** set every primary result to PASS unconditionally.

Do **not** use `scripts/phase5/acceptance.py` itself as substantive evidence
for each requirement.

## Evidence mapping

Each requirement/category must map to one or more exact registered producer
IDs whose result/raw/meta evidence can prove it.

Examples:

```text
SQLSERVER
→ sqlserver-bootstrap + sqlserver-targeted

BROWSER_*
→ browser-required-paths + browser-quality

REGRESSION
→ backend-targeted + phase4-integration-regression + backend-full
  + frontend-targeted + frontend-full + frontend-build

BOUNDARY / authority
→ shadow-replay + authority-denial + security-hygiene

FREEZE
→ input-identity + freeze-reproducibility
  + classifier-validation + classifier-holdout
  + classifier-cross-context + classifier-path-counterfactual

REVIEW / PROMOTION / CORRECTION
→ shadow-replay + sqlserver-targeted + authority-denial
```

Use specific evidence mappings rather than round-robin producer IDs.

## Precommit dry-run mode

Support an explicit dry-run evidence set where runtime producers are:

```text
NOT_EXECUTED
```

In dry run:
- source/deterministic checks may be evaluated;
- runtime-required checks must **not** become PASS;
- overall dry-run state is not Phase5 PASS.

Require:

```text
PHASE5_ACCEPTANCE_REFERENCE_DRY_RUN=PASS
PHASE5_PRECOMMIT_RUNTIME_FALSE_ACCEPT_COUNT=0
```

## Remote mode

Only after actual runtime result files exist may acceptance produce:

```text
result=PASS
```

Require:

```text
PHASE5_ACCEPTANCE_CHECK_COUNT>=300
PHASE5_ACCEPTANCE_CHECK_PASS=PHASE5_ACCEPTANCE_CHECK_COUNT
PHASE5_ACCEPTANCE_CHECK_FAIL=0

PHASE5_ACCEPTANCE_CHECK_WITHOUT_REQUIREMENT_ID=0
PHASE5_ACCEPTANCE_DUPLICATE_CHECK_ID_COUNT=0
PHASE5_ACCEPTANCE_DUPLICATE_REQUIREMENT_PADDING_COUNT=0
PHASE5_ACCEPTANCE_DUPLICATE_ASSERTION_COUNT=0

PHASE5_ACCEPTANCE_UNKNOWN_EVIDENCE_ID_COUNT=0
PHASE5_ACCEPTANCE_UNRESOLVED_EVIDENCE_REFERENCE_COUNT=0

PHASE5_ACCEPTANCE_RUNTIME_REQUIRED_SOURCE_ONLY_PASS_COUNT=0
```

---

# 16. C08 — EVIDENCE VALIDATOR MUST DETECT FALSE ACCEPTS

Repair `evidence_validate.py`.

It must not trust `check["result"] == "PASS"` by itself.

For every PASS primary check:
1. resolve all `evidence_ids` through the central registry;
2. resolve the actual evidence files under the supplied evidence directory;
3. prove every required producer exists;
4. prove producer identity matches candidate/validation/run when runtime;
5. prove producer result is PASS;
6. prove runtime-required checks cite at least one runtime-required producer;
7. prove runtime producer was actually executed;
8. reject `NOT_EXECUTED`;
9. reject zero-byte/missing result evidence;
10. reject self-reference to acceptance.py as sole substantive proof.

Compute, do not assign:

```text
false_accept_count
runtime_required_source_only_pass_count
unknown_evidence_id_count
unresolved_evidence_reference_count
duplicate_assertion_count
```

Required remote:

```text
false_accept_count=0
runtime_required_source_only_pass_count=0
```

Add negative tests showing each becomes nonzero/fail when evidence is corrupted.

---

# 17. C09/C10 — FINALIZER MUST FAIL CLOSED AND BIND EXACT PHASE5 CANDIDATE

Repair `finalize.py` / `phase5_finalize.py`.

## No default runtime PASS

The acceptance finalizer must never infer SQL Server/browser/regression PASS
from `evidence_dir=None`.

For acceptance mode:

```text
evidence_dir missing => FAIL
required producer missing => FAIL
runtime result missing => FAIL
```

A helper used for non-acceptance artifact construction may exist only if it is
clearly named/non-acceptance and cannot output `COMPLETE_PASS`.

## Exact externally supplied candidate identity

Add CLI:

```bash
--expected-candidate-sha <40-hex Phase5 SHA>
```

Remote invocation must supply:

```bash
--expected-candidate-sha "$CANDIDATE_SHA"
```

The finalizer must require:

```text
runtime candidate_sha == expected_candidate_sha
```

exactly.

Do not accept arbitrary 40-hex SHA merely because it is well formed.

Do not use accepted Phase4 SHA as the Phase5 runtime candidate identity.

`LOCAL_PRECOMMIT` may be accepted only in an explicit local-test mode.

Add actual-finalizer tests for:
- exact matching remote-shaped 40-hex candidate => allowed when all other
  fixture evidence valid;
- different valid 40-hex candidate => rejected;
- blank expected candidate => rejected;
- malformed expected candidate => rejected;
- missing CLI expected candidate => rejected.

---

# 18. C11 — FINAL SUMMARY MUST BE DERIVED, NOT HARDCODED

Finalizer must parse actual evidence results and derive:

```text
browser_required_path_count
browser_required_path_pass
browser_required_path_fail

sqlserver_validation_result
sqlserver_major
migration_head

critical_false_promotions

shadow_state
promotion_requires_human_review
projection_requires_existing_verified_assertion

backend_regression
frontend_regression
frontend_build

new_source_reads
auto_promotion_enabled
llm_real_content_mode
llm_external_call_count
```

Do not emit:

```text
browser_required_path_pass=10
sqlserver_validation_result=PASS
critical_false_promotions=0
```

unless those exact values were read/validated from actual evidence.

`handoff_state=READY_FOR_INDEPENDENT_PHASE5_ACCEPTANCE` is permitted only after
all required evidence is complete and acceptance validator reports zero false
accepts.

---

# 19. C12 — REPRODUCIBILITY MUST REGENERATE

Repair `reproducibility.py`.

It must not hash the same already-written files twice.

Create two independent temporary regeneration roots from the same exact source
bytes and rerun deterministic Phase5 generators for the classifier/freeze
artifact families that are intended to be reproducible.

At minimum independently regenerate and compare:

```text
input identity
robustness corpus
calibration manifest
validation manifest
holdout/adversarial manifest
calibration results
validation results
holdout results
cross-context results
path-counterfactual results
```

Also recompute and verify every freeze-manifest referenced SHA which depends on
those deterministic files/classifier/rules.

Require:
- regeneration A == regeneration B;
- regeneration A == committed canonical bytes;
- every referenced SHA matches;
- no wall-clock/temporary path leaks;
- no recursive self-hash.

Output actual mismatch lists.

Require remote:

```text
REMOTE_CLASSIFIER_FREEZE_REPRODUCIBILITY=PASS
REMOTE_CLASSIFIER_RESULT_HASH_MISMATCH_COUNT=0
REMOTE_CANONICAL_ARTIFACT_MISSING_COUNT=0
REMOTE_FREEZE_REFERENCE_MISMATCH_COUNT=0
```

The classifier/rules/corpus committed bytes remain unchanged from R2.

---

# 20. FINALIZER NEGATIVE SUITE — EXPAND, DO NOT WEAKEN

Retain the existing actual-finalizer negative tests and add coverage for the
new evidence truth contract.

At minimum actual CLI finalizer must reject:

```text
missing evidence directory
missing required producer
failed producer
producer NOT_EXECUTED
producer candidate SHA mismatch
producer validation SHA mismatch
producer run ID mismatch
blank/noninteger exit code
zero-byte required raw log
failed acceptance
duplicate check ID
duplicate normalized assertion
missing requirement ID
runtime-required source-only PASS
false-accept evidence mapping
critical false promotion
new source reads > 0
auto promotion enabled
LLM real content enabled
browser evidence missing/fail/skip
SQL Server evidence missing/fail
freeze digest mismatch
unresolved evidence
secret hygiene failure
candidate SHA mismatch
malformed expected candidate SHA
```

Require:

```text
PHASE5_FINALIZER_NEGATIVE_FIXTURE_COUNT>=25
PHASE5_FINALIZER_NEGATIVE_FALSE_ACCEPT_COUNT=0
PHASE5_FINALIZER_NEGATIVE_TESTS_INVOKE_ACTUAL_FINALIZER=true
PHASE5_FINALIZER_HELPER_ONLY_NEGATIVE_TEST_COUNT=0
```

---

# 21. BROWSER SPEC QUALITY — ACTUAL TESTS, NOT PYTHON FLAGS

Preserve the ten required business path IDs.

Add actual checks, using the real frontend/backend where appropriate, for:
- initial loading state;
- empty state against fresh pre-Phase5 queue when deterministically available;
- error state via a test-only/non-business transport failure mechanism that
  does not mock a successful ProposalOps business response;
- keyboard-accessible review actions;
- basic accessible roles/names;
- deep-link route resolution;
- visible correlation ID;
- visible root event.

If a quality test uses network interception only to induce an error, it must
not fabricate a successful business response and must be excluded from the
required-path API mock count.

No application truth may be mocked.

---

# 22. PRESERVE ZERO-SCHEMA-DELTA

R3 must retain:

```text
PHASE5_MIGRATION_REQUIRED=false
DATABASE_SCHEMA_DELTA=0

ACTIVE_MIGRATION_HEAD=
baseline_phase4_v36_azure_sql
```

No model/migration changes.

---

# 23. LOCAL PRECOMMIT EVIDENCE CONTRACT

Before application commit create temporary precommit evidence.

Runtime producers must be explicitly:

```text
NOT_EXECUTED
```

Run:
- source preflight V3;
- deterministic regeneration;
- evidence-registry/reference dry run;
- acceptance dry run;
- finalizer positive local fixture;
- >=25 actual-finalizer negative fixtures.

Require:

```text
PHASE5_PRECOMMIT_RUNTIME_FALSE_ACCEPT_COUNT=0
PHASE5_ACCEPTANCE_REFERENCE_DRY_RUN=PASS
PHASE5_FINALIZER_NEGATIVE_FALSE_ACCEPT_COUNT=0
```

Delete temporary evidence before staging.

---

# 24. WHOLE-SURFACE R3 NO-LOOP AUDIT

Before the one application commit, perform a fresh independent source audit over
the entire Phase5 candidate surface and inherited consumers.

Re-adjudicate every Run-10 defect and workflow defect.

Require:

```text
C01_SOURCE_PREFLIGHT_HARDCODED_FIELDS=CLOSED
C02_FIXED_SHA_DESCENDANT_AUDIT_INCOMPLETE=CLOSED
C03_BROWSER_EVIDENCE_HARDCODED_PASS=CLOSED
C04_SQLSERVER_EVIDENCE_HARDCODED_PASS=CLOSED
C05_SHADOW_REPLAY_HARDCODED_PASS=CLOSED
C06_ACCEPTANCE_GENERATOR_HARDCODED_PASS=CLOSED
C07_ACCEPTANCE_EVIDENCE_SELF_REFERENTIAL=CLOSED
C08_EVIDENCE_VALIDATOR_SEMANTIC_GAP=CLOSED
C09_FINALIZER_DEFAULT_RUNTIME_PASS=CLOSED
C10_FINALIZER_CANDIDATE_SHA_NOT_EXACT=CLOSED
C11_FINALIZER_SUMMARY_HARDCODED_RUNTIME=CLOSED
C12_REPRODUCIBILITY_NOT_REGENERATED=CLOSED

W01_INVALID_SQLSERVER_IMAGE_TAG=CLOSED
W02_SQLSERVER_PASSWORD_NOT_EXPORTED=CLOSED
W03_IN_CONTAINER_SQLCMD_BOOTSTRAP=CLOSED
W04_PLAYWRIGHT_BROWSER_NOT_EXPLICITLY_INSTALLED=CLOSED

KNOWN_NEXT_DETERMINISTIC_BLOCKER_COUNT=0
```

The audit must inspect executable code, not merely search for these output
strings.

If a definite blocker remains inside the authorized surface, repair it before
the first application commit.

If it requires an unauthorized path:

```text
RESULT=STOP_PHASE5_R3_ADDITIONAL_SCOPE_REQUIRED
```

STOP before commit.

---

# 25. LOCAL APPLICATION VALIDATION

Run all impacted tests and full regressions.

At minimum:

```bash
pytest -q \
  backend/tests/test_phase5_contracts.py \
  backend/tests/test_phase5_finalizer_negative.py \
  backend/tests/test_phase5_evidence_integrity.py \
  backend/tests/test_phase5_sqlserver_runtime.py \
  backend/tests/test_phase5_classifier.py \
  backend/tests/test_phase5_portability.py

pytest -q backend/tests/test_phase4_corpus_app_integration.py

pytest -q

python -m compileall -q backend scripts

python scripts/phase5/source_preflight.py
python scripts/phase5/reproducibility.py

git diff --check
```

Frontend:

```bash
cd frontend
npm ci
npm test -- --run
npx tsc -b
npx vite build
npx playwright test \
  browser-real-stack/phase5-classifier-shadow.spec.ts \
  --config=playwright.real-stack.config.ts \
  --list
```

Require all failures zero.

Do not claim SQL Server/browser runtime proof from these local tests.

---

# 26. APPLICATION DIFF GATE

Before commit:

```text
PHASE5_R3_APPLICATION_PARENT=
ca60459f2103cbf30e52e05c59b8af6d7714be12
```

Changed paths must be a subset of Section 8 only.

Require classifier/freeze protected bytes unchanged from R2.

Require:

```text
PHASE5_R3_CLASSIFIER_BEHAVIOR_PATH_CHANGE_COUNT=0
PHASE5_R3_PHASE4_PATH_CHANGE_COUNT=0
PHASE5_R3_MIGRATION_MODEL_CHANGE_COUNT=0
PHASE5_R3_UNAUTHORIZED_PATH_COUNT=0
```

No generated `artifacts/**` files staged.

---

# 27. CREATE EXACTLY ONE R3 APPLICATION COMMIT

Create one commit on:

```text
phase5-classifier-shadow-validation-r3-v1
```

Parent exactly:

```text
ca60459f2103cbf30e52e05c59b8af6d7714be12
```

Recommended message:

```text
fix(phase5): bind acceptance to actual runtime evidence
```

Record:

```text
PHASE5_R3_CANDIDATE_SHA=<exact>
PHASE5_R3_CANDIDATE_TREE=<exact>
```

Push only this application branch.

After push:

```text
SECOND_APPLICATION_COMMIT_AUTHORIZED=false
```

---

# 28. CREATE FRESH VALIDATION BRANCH DIRECTLY FROM R3 CANDIDATE

Create:

```text
PHASE5_R3_VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-r3-v1
```

directly from exact:

```text
PHASE5_R3_CANDIDATE_SHA
```

Do not branch from `3842fc0...`.

Create exactly one workflow-only child commit.

---

# 29. WORKFLOW SOURCE AUTHORITY

Use the exact failed R2 workflow as structural source:

```text
SOURCE_VALIDATION_SHA=
3842fc0faf4c95bf933d0a56cd8773162e97f893

SOURCE_WORKFLOW_PATH=
.github/workflows/phase5-classifier-shadow-validation-ci.yml

SOURCE_WORKFLOW_BLOB_SHA1=
03dfbe144e9a0e61b7ddc648ebe9cc8cf711f560
```

Create fresh workflow path:

```text
.github/workflows/phase5-classifier-shadow-validation-ci-r3.yml
```

Preserve:
- exact candidate/parent/branch binding pattern;
- Ubuntu x64 proof;
- ODBC install approach that already passed;
- dependency installation;
- raw/meta evidence wrapper;
- always-on cleanup;
- credential-free artifact upload.

Apply all R3 repairs below.

---

# 30. WORKFLOW BINDING

Set exact:

```text
CANDIDATE_SHA=<PHASE5_R3_CANDIDATE_SHA>

CANDIDATE_BRANCH=
phase5-classifier-shadow-validation-r3-v1

VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-r3-v1
```

Require remote branch→candidate SHA and validation parent→candidate SHA.

Validation diff must equal exactly:

```text
.github/workflows/phase5-classifier-shadow-validation-ci-r3.yml
```

No other validation-child path.

---

# 31. SQL SERVER IMAGE — CURRENT SUPPORTED TAG + WITHIN-RUN DIGEST FREEZE

Use:

```text
SQLSERVER_IMAGE_TAG=
mcr.microsoft.com/mssql/server:2022-latest
```

Explicitly:

```bash
docker pull --platform linux/amd64 "$SQLSERVER_IMAGE_TAG"
```

Resolve the pulled repo digest:

```bash
SQLSERVER_IMAGE_REPODIGEST="$(
  docker image inspect "$SQLSERVER_IMAGE_TAG" \
    --format '{{index .RepoDigests 0}}'
)"
```

Require:

```text
mcr.microsoft.com/mssql/server@sha256:<64 hex>
```

Then run the SQL Server container using the exact resolved RepoDigest, not the
mutable tag.

Record both tag and RepoDigest in credential-free evidence.

Workflow source must contain zero active occurrences of:

```text
mcr.microsoft.com/mssql/server:2022-GA-ubuntu-20.04
```

---

# 32. SQL SERVER PASSWORD — MASK + EXPORT + FUTURE-STEP PERSISTENCE

Generate a strong random password.

Required order in same step:

```text
generate
→ mask
→ export SQLSERVER_PASSWORD
→ write SQLSERVER_PASSWORD to GITHUB_ENV
→ host pyodbc bootstrap
→ DATABASE_URL construction
```

Require:

```text
SQLSERVER_PASSWORD_EXPORT_COUNT=1
SQLSERVER_PASSWORD_GITHUB_ENV_WRITE_COUNT=1
SQLSERVER_PASSWORD_PLAINTEXT_EVIDENCE_MATCH_COUNT=0
```

---

# 33. SQL SERVER BOOTSTRAP — HOST PYODBC, NOT CONTAINER SQLCMD

Do not use container-internal `sqlcmd` for the bootstrap/readiness contract.

Use the already-installed host:

```text
ODBC Driver 18 for SQL Server
pyodbc
```

Run a bounded retry probe against master.

Require actual queries:

```text
SELECT 1
SELECT SERVERPROPERTY('ProductMajorVersion')
```

Require:

```text
SQLSERVER_MAJOR=16
```

With pyodbc `autocommit=True`, create:

```text
phase5db
```

if absent.

Then build:

```text
mssql+pyodbc://...
```

`DATABASE_URL` for `phase5db` and persist to `GITHUB_ENV`.

Require source preflight:

```text
IN_CONTAINER_SQLCMD_BOOTSTRAP_COUNT=0
HOST_PYODBC_SQLSERVER_BOOTSTRAP_COUNT=1
```

---

# 34. PLAYWRIGHT BROWSER INSTALL — EXPLICIT

After `npm ci` run:

```bash
cd frontend
npx playwright install --with-deps chromium
```

Capture raw/meta evidence.

Require:

```text
PLAYWRIGHT_CHROMIUM_INSTALL=PASS
```

Do not assume browser binaries from npm package installation.

---

# 35. R3 REMOTE EXECUTION ORDER

Use a single fresh run.

Required high-level order:

```text
1 candidate/workflow identity
2 Ubuntu x64 + Docker
3 Python/Node/dependencies/ODBC
4 explicit Playwright Chromium install
5 SQL Server image pull + digest freeze
6 SQL Server host-pyodbc readiness/version + fresh DB
7 Alembic migration + synthetic seed + head check
8 source preflight V3
9 deterministic corpus/evaluation/freeze regeneration proof
10 actual SQL Server targeted evidence
11 actual SHADOW replay evidence
12 targeted + Phase4 integration + full backend regression
13 start real SQL Server-backed API
14 start real frontend
15 ten required real browser paths + quality evidence
16 frontend targeted/full/build
17 authority / observability / security evidence
18 generate >=300 evidence-bound acceptance checks
19 semantic evidence validation
20 actual fail-closed finalizer with exact candidate SHA
21 evidence manifest
22 artifact upload
23 cleanup
24 independent artifact recheck/handoff
```

Do not run final acceptance before runtime evidence exists.

---

# 36. REMOTE FREEZE REPRODUCTION

Require fresh:

```text
REMOTE_PHASE5_INPUT_IDENTITY=PASS
REMOTE_CLASSIFIER_FREEZE_REPRODUCIBILITY=PASS
REMOTE_CLASSIFIER_RESULT_HASH_MISMATCH_COUNT=0
REMOTE_CANONICAL_ARTIFACT_MISSING_COUNT=0
REMOTE_FREEZE_REFERENCE_MISMATCH_COUNT=0
```

R3 must prove the preserved R2 classifier/freeze bytes are reproducible.

---

# 37. REMOTE SQL SERVER TARGETED PROOF

Use the fresh `phase5db`.

Require:

```text
SQLSERVER_MAJOR=16
MIGRATION_PASS=true
ACTIVE_MIGRATION_HEAD=baseline_phase4_v36_azure_sql

PHASE5_SQLSERVER_TARGETED_GATE_COUNT=16
PHASE5_SQLSERVER_TARGETED_PASS=16
PHASE5_SQLSERVER_TARGETED_FAIL=0
PHASE5_SQLSERVER_TARGETED_SKIP=0
```

No hardcoded producer PASS.

---

# 38. REMOTE SHADOW PROOF

Require evidence-derived:

```text
SHADOW_CLASSIFICATION_GENERATED=true
SHADOW_COMPARISON_RECORDED=true
SHADOW_CLASSIFICATION_ENVELOPE_IMMUTABLE=true
SHADOW_CORRECTION_APPEND_ONLY=true

CLASSIFIER_ONLY_VERIFIED_ASSERTION_PROMOTION_COUNT=0
CLASSIFIER_ONLY_TYPED_PROJECTION_COUNT=0
CLASSIFIER_PROTECTED_ACTION_EXECUTION_COUNT=0

REPLAY_EVENT_ID_STABLE_ACROSS_TIME=true
REPLAY_RESULT_HASH_STABLE_ACROSS_TIME=true
REPLAY_SIDE_EFFECT_DUPLICATE_COUNT=0

SYNOLOGY_WRITEBACK_COUNT=0
LLM_EXTERNAL_CALL_COUNT=0
REAL_CONTENT=false
```

---

# 39. REAL BROWSER — SAME SQL SERVER BACKEND

Topology must be:

```text
real ProposalOps frontend
→ local ProposalOps backend
→ fresh R3 SQL Server 2022 x64 database
```

No mocked ProposalOps business API for the required ten paths.

Require:

```text
PHASE5_BROWSER_REQUIRED_PATH_COUNT=10
PHASE5_BROWSER_REQUIRED_PATH_PASS=10
PHASE5_BROWSER_REQUIRED_PATH_FAIL=0
PHASE5_BROWSER_REQUIRED_PATH_SKIP=0

PHASE5_BROWSER_API_MOCK_COUNT_FOR_REQUIRED_PATHS=0
```

Browser evidence script must parse the actual Playwright JSON.

---

# 40. FULL REGRESSIONS

Same run require:

```text
PHASE5_TARGETED_BACKEND_FAIL=0
PHASE5_TARGETED_BACKEND_SKIP=0

PHASE4_INTEGRATION_REGRESSION_FAIL=0
BACKEND_FULL_FAIL=0

PHASE5_TARGETED_FRONTEND_FAIL=0
FRONTEND_FULL_FAIL=0
FRONTEND_BUILD=PASS

PHASE5_BROWSER_FAIL=0
```

---

# 41. AUTHORITY / OBSERVABILITY / SECURITY PRODUCERS

Do not create PASS values in runtime-gates.json merely because earlier steps did
not fail.

Each must have actual producer evidence.

## Authority

Prove at minimum:
- protected action denial;
- classifier-only promotion count zero;
- classifier-only projection count zero;
- client actor does not override server authority;
- human review remains required.

## Observability

Prove reconstructed chain includes:
- root event;
- source artifact/version;
- evidence envelope;
- classifier/rules/taxonomy;
- correlation ID;
- review/correction;
- result identity.

## Security/source hygiene

Prove:
- new source reads = 0;
- real data = false;
- external LLM calls = 0;
- secret pattern matches in evidence = 0;
- no Synology/SMB/Azure/Entra access.

Require actual result files from all three producers.

---

# 42. REMOTE ACCEPTANCE — AFTER RUNTIME

Run acceptance only after Sections 36–41 evidence exists.

Require:

```text
PHASE5_ACCEPTANCE_CHECK_COUNT>=300
PHASE5_ACCEPTANCE_CHECK_PASS=PHASE5_ACCEPTANCE_CHECK_COUNT
PHASE5_ACCEPTANCE_CHECK_FAIL=0

PHASE5_ACCEPTANCE_CHECK_WITHOUT_REQUIREMENT_ID=0
PHASE5_ACCEPTANCE_DUPLICATE_CHECK_ID_COUNT=0
PHASE5_ACCEPTANCE_DUPLICATE_REQUIREMENT_PADDING_COUNT=0
PHASE5_ACCEPTANCE_DUPLICATE_ASSERTION_COUNT=0

PHASE5_ACCEPTANCE_UNKNOWN_EVIDENCE_ID_COUNT=0
PHASE5_ACCEPTANCE_UNRESOLVED_EVIDENCE_REFERENCE_COUNT=0

PHASE5_ACCEPTANCE_RUNTIME_REQUIRED_SOURCE_ONLY_PASS_COUNT=0
PHASE5_ACCEPTANCE_FALSE_ACCEPT_COUNT=0

CRITICAL_FALSE_PROMOTIONS=0
```

---

# 43. ACTUAL FINALIZER — EXACT R3 CANDIDATE

Invoke:

```bash
python scripts/phase5/phase5_finalize.py \
  --evidence-dir "$EVIDENCE_DIR" \
  --acceptance-result "$EVIDENCE_DIR/acceptance-result.json" \
  --contracts-dir contracts/amec/phase5 \
  --expected-candidate-sha "$CANDIDATE_SHA" \
  --output "$EVIDENCE_DIR/phase5-final-summary.json"
```

Finalizer must derive rather than manufacture the summary.

Require:

```text
RUN_EVIDENCE_STATE=COMPLETE_PASS
```

Anything required missing/failing/NOT_EXECUTED:

```text
RUN_EVIDENCE_STATE=PARTIAL_FAILED
```

never PASS.

---

# 44. EVIDENCE INTEGRITY

Every mandatory producer must have:

```text
raw log or explicit success marker
meta JSON
result JSON
integer exit code
candidate SHA
validation SHA
run ID
```

Require:

```text
UNRESOLVED_EVIDENCE_REFERENCE_COUNT=0
BLANK_EXIT_CODE_COUNT=0
MISSING_EVIDENCE_FILE_COUNT=0
ZERO_BYTE_REQUIRED_RAW_LOG_COUNT=0

DUPLICATE_ACCEPTANCE_ID_COUNT=0
SELF_CERTIFYING_PASS_COUNT=0
SECRET_EVIDENCE_MATCH_COUNT=0

RUNTIME_REQUIRED_SOURCE_ONLY_PASS_COUNT=0
FALSE_ACCEPT_COUNT=0
```

---

# 45. WORKFLOW STATIC NO-LOOP PREFLIGHT BEFORE FIRST COMMIT

Before validation workflow commit inspect the actual YAML/shell.

Require:

```text
WORKFLOW_STALE_2022_GA_UBUNTU_20_04_COUNT=0

WORKFLOW_SQLSERVER_2022_LATEST_PULL_COUNT=1
WORKFLOW_SQLSERVER_RUN_BY_RESOLVED_DIGEST=true
WORKFLOW_SQLSERVER_PLATFORM_AMD64=true

WORKFLOW_SQLSERVER_PASSWORD_EXPORT_COUNT=1
WORKFLOW_SQLSERVER_PASSWORD_GITHUB_ENV_COUNT=1

WORKFLOW_IN_CONTAINER_SQLCMD_BOOTSTRAP_COUNT=0
WORKFLOW_HOST_PYODBC_BOOTSTRAP_COUNT=1

WORKFLOW_PLAYWRIGHT_CHROMIUM_INSTALL_COUNT=1

WORKFLOW_ACCEPTANCE_AFTER_BROWSER_SQLSERVER_REGRESSIONS=true
WORKFLOW_FINALIZER_EXPECTED_CANDIDATE_SHA_BINDING=true

WORKFLOW_PHASE5_SCRIPT_PATH_MISSING_COUNT=0
WORKFLOW_EVIDENCE_PRODUCER_UNKNOWN_COUNT=0
WORKFLOW_REQUIRED_EVIDENCE_NAME_MISMATCH_COUNT=0

WORKFLOW_DUPLICATE_MICROSOFT_APT_SOURCE_COUNT=0
WORKFLOW_LOCAL_MAC_DOCKER_REFERENCE_COUNT=0
```

Do not commit workflow until all are green.

---

# 46. CREATE EXACTLY ONE VALIDATION WORKFLOW COMMIT

On:

```text
phase5-classifier-shadow-validation-ci-r3-v1
```

commit only:

```text
.github/workflows/phase5-classifier-shadow-validation-ci-r3.yml
```

Parent must be exact R3 application SHA.

Recommended message:

```text
ci(phase5): validate evidence-bound shadow on SQL Server
```

Push only validation branch.

After push:

```text
SECOND_WORKFLOW_COMMIT_AUTHORIZED=false
```

---

# 47. FAILURE POLICY — NO R3 PATCH LOOP

If precommit cannot close all deterministic defects:

```text
RESULT=STOP_PHASE5_R3_PRECOMMIT_NO_GO
FIRST_FAILED_GATE=<exact>
```

STOP before app commit.

If remote run fails:

```text
RESULT=STOP_PHASE5_R3_REMOTE_VALIDATION_FAILED

FIRST_FAILED_GATE=<exact>
FIRST_FAILED_SUBGATE=<exact if known>
FAILURE_EVIDENCE=<exact sanitized>

PHASE5_R3_CANDIDATE_SHA=<exact>
PHASE5_R3_VALIDATION_SHA=<exact>

RUN_ID=<exact>
JOB_ID=<exact>
ARTIFACT_ID=<exact>
ARTIFACT_SHA256=<exact>

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

Do not create R3R1/R4 automatically.

---

# 48. INDEPENDENT ARTIFACT RECHECK AFTER REMOTE COMPLETE PASS

Only after the remote workflow itself passes:

1. download exact artifact;
2. hash artifact;
3. re-extract;
4. verify application/validation/run binding;
5. verify every registered producer raw/meta/result;
6. verify no missing/unmanifested/hash-mismatched evidence;
7. independently recalculate acceptance counts;
8. independently recalculate false-accept/runtime-source-only counts;
9. verify SQL Server image RepoDigest + major 16;
10. verify migration head;
11. verify 16 SQL Server targeted gates;
12. verify SHADOW replay state;
13. parse Playwright JSON independently for ten paths;
14. verify regressions/build;
15. verify finalizer result;
16. secret/raw-content scan;
17. verify no external access.

Create:

```text
ProposalOps_Phase5_R3_Independent_Review_Handoff_<candidate_short>_<timestamp>/
ProposalOps_Phase5_R3_Independent_Review_Handoff_<candidate_short>_<timestamp>.tar.gz
```

Manifest every file and re-extract archive.

Do not independently accept Phase5 inside Codex.

---

# 49. SAFETY BOUNDARY

Throughout:

```text
AZURE_ACCESSED=false
ENTRA_ACCESSED=false
SYNOLOGY_ACCESSED=false
SMB_ACCESSED=false
REAL_DATA_USED=false

NEW_SMB_CONNECTIONS=0
NEW_AMEC_SOURCE_READS=0
NEW_AMEC_SOURCE_BYTES=0

AUTO_PROMOTION_ENABLED=false
REAL_LIVE_SHADOW_ENABLED=false
LIVE_SYNOLOGY_MONITOR_ENABLED=false
SYNOLOGY_WRITEBACK_ENABLED=false

LLM_REAL_CONTENT_MODE=DISABLED
LLM_EXTERNAL_CALL_COUNT=0

MAIN_CHANGED=false
MAIN_PUSHED=false
TAG_CREATED=false
RELEASE_CREATED=false
DEPLOYMENT_STARTED=false

PHASE6_STARTED=false
```

---

# 50. TRUTHFUL SUCCESS CLASSIFICATION

A successful exact R3 run may establish for Phase5:

```text
PHASE5_CANDIDATE_COMPLETE=true
CLASSIFIER_V2_FROZEN=true
PRODUCTION_CLASSIFIER_CANDIDATE=true

VERIFIED_LOCAL=true
VERIFIED_SQLSERVER_COMPAT=true
VERIFIED_BROWSER=true

VERIFIED_AZURE_SQL=false
VERIFIED_DEPLOYED=false

AUTO_PROMOTION_ENABLED=false
REAL_LIVE_SHADOW_ENABLED=false
SYNOLOGY_WRITEBACK_ENABLED=false
LLM_REAL_CONTENT_MODE=DISABLED

PHASE5_CODEX_SELF_ACCEPTED=false
PHASE5_INDEPENDENT_ACCEPTANCE=PENDING
```

Do not claim Azure SQL verification from local SQL Server.

---

# 51. FINAL SUCCESS RETURN

Only if:
- application precommit all green;
- one R3 application commit;
- one workflow-only validation child;
- remote workflow complete PASS;
- independent artifact recheck complete PASS;
- evidence false-accept count zero;
- all Run-10 defects closed;

return:

```text
RESULT=PHASE5_R3_CANDIDATE_READY_FOR_INDEPENDENT_ACCEPTANCE

PHASE5_R3_APPLICATION_BRANCH=
phase5-classifier-shadow-validation-r3-v1

PHASE5_R3_CANDIDATE_SHA=<exact>
PHASE5_R3_CANDIDATE_PARENT=
ca60459f2103cbf30e52e05c59b8af6d7714be12
PHASE5_R3_CANDIDATE_TREE=<exact>

PHASE5_R3_VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-r3-v1

PHASE5_R3_VALIDATION_SHA=<exact>
PHASE5_R3_VALIDATION_PARENT=<PHASE5_R3_CANDIDATE_SHA>

RUN_ID=<exact>
JOB_ID=<exact>
ARTIFACT_ID=<exact>
ARTIFACT_SHA256=<exact>

SQLSERVER_IMAGE_TAG=
mcr.microsoft.com/mssql/server:2022-latest

SQLSERVER_IMAGE_REPODIGEST=<exact>

SQLSERVER_MAJOR=16
MIGRATION_PASS=true
ACTIVE_MIGRATION_HEAD=baseline_phase4_v36_azure_sql

PHASE5_SQLSERVER_TARGETED_GATE_COUNT=16
PHASE5_SQLSERVER_TARGETED_PASS=16
PHASE5_SQLSERVER_TARGETED_FAIL=0
PHASE5_SQLSERVER_TARGETED_SKIP=0

SHADOW_CLASSIFICATION_GENERATED=true
SHADOW_COMPARISON_RECORDED=true
SHADOW_CLASSIFICATION_ENVELOPE_IMMUTABLE=true
SHADOW_CORRECTION_APPEND_ONLY=true

CLASSIFIER_ONLY_VERIFIED_ASSERTION_PROMOTION_COUNT=0
CLASSIFIER_ONLY_TYPED_PROJECTION_COUNT=0
CLASSIFIER_PROTECTED_ACTION_EXECUTION_COUNT=0

REPLAY_EVENT_ID_STABLE_ACROSS_TIME=true
REPLAY_RESULT_HASH_STABLE_ACROSS_TIME=true
REPLAY_SIDE_EFFECT_DUPLICATE_COUNT=0

PHASE5_BROWSER_REQUIRED_PATH_COUNT=10
PHASE5_BROWSER_REQUIRED_PATH_PASS=10
PHASE5_BROWSER_REQUIRED_PATH_FAIL=0
PHASE5_BROWSER_REQUIRED_PATH_SKIP=0

PHASE5_TARGETED_BACKEND_FAIL=0
PHASE4_INTEGRATION_REGRESSION_FAIL=0
BACKEND_FULL_FAIL=0

PHASE5_TARGETED_FRONTEND_FAIL=0
FRONTEND_FULL_FAIL=0
FRONTEND_BUILD=PASS

REMOTE_CLASSIFIER_FREEZE_REPRODUCIBILITY=PASS
REMOTE_CLASSIFIER_RESULT_HASH_MISMATCH_COUNT=0
REMOTE_FREEZE_REFERENCE_MISMATCH_COUNT=0

PHASE5_ACCEPTANCE_CHECK_COUNT=<actual >=300>
PHASE5_ACCEPTANCE_CHECK_PASS=<same>
PHASE5_ACCEPTANCE_CHECK_FAIL=0

PHASE5_ACCEPTANCE_RUNTIME_REQUIRED_SOURCE_ONLY_PASS_COUNT=0
PHASE5_ACCEPTANCE_FALSE_ACCEPT_COUNT=0

RUN_EVIDENCE_STATE=COMPLETE_PASS

UNRESOLVED_EVIDENCE_REFERENCE_COUNT=0
BLANK_EXIT_CODE_COUNT=0
MISSING_EVIDENCE_FILE_COUNT=0
ZERO_BYTE_REQUIRED_RAW_LOG_COUNT=0
DUPLICATE_ACCEPTANCE_ID_COUNT=0
SELF_CERTIFYING_PASS_COUNT=0
SECRET_EVIDENCE_MATCH_COUNT=0

C01_SOURCE_PREFLIGHT_HARDCODED_FIELDS=CLOSED
C02_FIXED_SHA_DESCENDANT_AUDIT_INCOMPLETE=CLOSED
C03_BROWSER_EVIDENCE_HARDCODED_PASS=CLOSED
C04_SQLSERVER_EVIDENCE_HARDCODED_PASS=CLOSED
C05_SHADOW_REPLAY_HARDCODED_PASS=CLOSED
C06_ACCEPTANCE_GENERATOR_HARDCODED_PASS=CLOSED
C07_ACCEPTANCE_EVIDENCE_SELF_REFERENTIAL=CLOSED
C08_EVIDENCE_VALIDATOR_SEMANTIC_GAP=CLOSED
C09_FINALIZER_DEFAULT_RUNTIME_PASS=CLOSED
C10_FINALIZER_CANDIDATE_SHA_NOT_EXACT=CLOSED
C11_FINALIZER_SUMMARY_HARDCODED_RUNTIME=CLOSED
C12_REPRODUCIBILITY_NOT_REGENERATED=CLOSED

W01_INVALID_SQLSERVER_IMAGE_TAG=CLOSED
W02_SQLSERVER_PASSWORD_NOT_EXPORTED=CLOSED
W03_IN_CONTAINER_SQLCMD_BOOTSTRAP=CLOSED
W04_PLAYWRIGHT_BROWSER_NOT_EXPLICITLY_INSTALLED=CLOSED

PHASE5_HANDOFF_ARCHIVE=<exact>
PHASE5_HANDOFF_ARCHIVE_SHA256=<exact>
HANDOFF_REEXTRACTION_PASS=true

PHASE5_CANDIDATE_COMPLETE=true
CLASSIFIER_V2_FROZEN=true
PRODUCTION_CLASSIFIER_CANDIDATE=true

VERIFIED_LOCAL=true
VERIFIED_SQLSERVER_COMPAT=true
VERIFIED_BROWSER=true
VERIFIED_AZURE_SQL=false
VERIFIED_DEPLOYED=false

DATABASE_TARGET_DECISION=OWNER_CONFIRMED
DATABASE_ENGINE_TARGET=AZURE_SQL_SQL_SERVER_ENGINE
AZURE_SQL_SERVICE_VARIANT=AZURE_SQL_DATABASE
AZURE_SQL_EXACT_SKU=OWNER_DECISION_PENDING

AUTO_PROMOTION_ENABLED=false
REAL_LIVE_SHADOW_ENABLED=false
SYNOLOGY_WRITEBACK_ENABLED=false
LLM_REAL_CONTENT_MODE=DISABLED
LLM_EXTERNAL_CALL_COUNT=0

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

NEXT=INDEPENDENT_PHASE5_ACCEPTANCE_REVIEW
```

Then STOP.

No post-success implementation mutation is authorized.
