# CRITICAL R3R1-E1 SUPERSESSION — GOVERNING SOURCE BYTE BOOTSTRAP FIX
## ProposalOps / AMEC Phase5 R3R1 — exact-byte bootstrap correction
**Date:** 2026-08-25

This prompt is the complete prior R3R1 authorization with one narrowly
superseding correction to the E01 governing-source-byte bootstrap.

The immediately preceding R3R1 attempt stopped before any application mutation:

```text
RESULT=STOP_PHASE5_R3R1_APPLICATION_PRECOMMIT_FAILED
FIRST_FAILED_GATE=E01_GOVERNING_SOURCE_BYTES_RETRIEVABLE
GOVERNING_SOURCE_BYTES_RETRIEVABLE=false
GOVERNING_SOURCE_FILE_COUNT=4
GOVERNING_SOURCE_HASH_MISMATCH_COUNT=4

NO_APPLICATION_FILES_CHANGED=true
NO_COMMIT_CREATED=true
NO_WORKFLOW_COMMIT_CREATED=true
NO_BRANCH_PUSHED=true
MAIN_CHANGED=false
AZURE_ACCESSED=false
ENTRA_ACCESSED=false
SYNOLOGY_ACCESSED=false
SMB_ACCESSED=false
REAL_DATA_USED=false
```

## Independent adjudication

The underlying four governing source payloads are NOT mismatched.

The original R3R1 authorization explicitly required:
- byte-for-byte extraction between BEGIN/END markers;
- no whitespace normalization;
- no line-ending change;
- no stripping of the final newline.

Independent byte reconstruction of each Appendix-A payload with its required
final LF produces exactly the four required SHA256 identities.

Therefore classify the prior stop as:

```text
R3R1_E01_STOP=VALID_FAIL_CLOSED_EXTRACTION_IMPLEMENTATION_DEFECT
GOVERNING_SOURCE_DESIGN_BYTES_MISMATCH=false
APPLICATION_DEFECT_PROVEN=false
SOURCE_DESIGN_DEFECT_PROVEN=false
```

This supersession changes ONLY the source-byte materialization mechanism.
All other R3R1 authorization, repair scope, evidence policy, runtime gates,
failure policy, safety boundaries, and success criteria below remain governing.

# E01-A. DO NOT EXTRACT APPENDIX A WITH LINE-ORIENTED TEXT PROCESSING

Do NOT use:
- `sed`;
- `awk`;
- shell heredoc reconstruction;
- `.strip()`;
- `.rstrip()`;
- `splitlines()` followed by join;
- Markdown parser reserialization;
- newline normalization;
- copy/paste reconstruction.

Do not hash a text object before restoring its required final LF.

# E01-B. AUTHORITATIVE BINARY-SAFE PAYLOAD BUNDLE

Before ANY repository mutation, decode the base64 payloads in
`APPENDIX B — AUTHORITATIVE BASE64 GOVERNING SOURCE BYTES` into a temporary
directory OUTSIDE the repository.

Base64 whitespace may be removed before decoding. The decoded bytes themselves
must not be changed.

Require exact decoded identities:

```text
PATH=docs/phase5/governing/ProposalOps_Phase5_Classifier_Shadow_Validation_Master_Design.md
SHA256=761dd4e642ce8dc30589bab393808e965a4f931e9e2a9ddda94cff6f217fa81b
BYTE_COUNT=10708
```

```text
PATH=docs/phase5/governing/ProposalOps_Phase5_190_Check_Design_Validation_Report.md
SHA256=61e57216ca5b8671df7337420bb7d116c94be138da62cde851dcab6236ecbe0f
BYTE_COUNT=16845
```

```text
PATH=docs/phase5/governing/ProposalOps_Phase5_Actions.md
SHA256=87a2376489a394806f9b11dadad5db710a0a0149ee895a449d1e4ea06823968e
BYTE_COUNT=801
```

```text
PATH=docs/phase5/governing/ProposalOps_Phase5_FINAL_R3_OneShot_EvidenceTruth_SQLServer_Browser_Closure_2026-08-24.md
SHA256=0fcb3efe875dff8b8d0c5cd939666ddcf37ea4d3d256e501d8c1927b288d34c5
BYTE_COUNT=46742
```

If any decoded SHA or byte count differs:

```text
RESULT=STOP_PHASE5_R3R1E1_BASE64_SOURCE_INTEGRITY_FAILURE
SOURCE_PATH=<exact>
EXPECTED_SHA256=<exact>
ACTUAL_SHA256=<exact>
EXPECTED_BYTE_COUNT=<exact>
ACTUAL_BYTE_COUNT=<exact>
```

STOP. Do not touch the repository.

# E01-C. CROSS-CHECK AGAINST ORIGINAL APPENDIX-A SEMANTICS

After all four base64 payloads pass:
1. independently parse the original Appendix-A source blocks only as a
   diagnostic cross-check;
2. reconstruct each block with exactly one final LF;
3. require its SHA256 equals the decoded base64 payload SHA256.

Require:

```text
APPENDIX_A_RECONSTRUCTED_SOURCE_COUNT=4
APPENDIX_A_RECONSTRUCTED_HASH_MISMATCH_COUNT=0
BASE64_SOURCE_COUNT=4
BASE64_SOURCE_HASH_MISMATCH_COUNT=0
E01_GOVERNING_SOURCE_BYTES_RETRIEVABLE=true
```

The base64-decoded bytes are the authoritative materialization bytes if the
Appendix-A text extraction implementation would otherwise alter them.

# E01-D. ONLY AFTER TEMPORARY BYTE PROOF, MATERIALIZE REPOSITORY FILES

Only after E01-C PASS:
- create `docs/phase5/governing/`;
- write the already-verified decoded byte arrays directly to the four exact
  repository paths using binary writes (`Path.write_bytes` or equivalent);
- hash the repository files again;
- require all four repository hashes and byte counts equal the temporary
  decoded payloads.

Require:

```text
PHASE5_GOVERNING_SOURCE_COUNT=4
PHASE5_GOVERNING_SOURCE_HASH_MISMATCH_COUNT=0
PHASE5_GOVERNING_SOURCE_BYTE_COUNT_MISMATCH_COUNT=0
PHASE5_GOVERNING_SOURCE_BYTES_RETRIEVABLE=true
COPIED_VERBATIM_COUNT=4
```

Only then continue into the original R3R1 repair ledger and application
precommit work.

# E01-E. REGRESSION

The R3R1 source-preflight regression for E01 must validate repository bytes
against the decoded bundle hashes. It must not depend on re-parsing Markdown
markers at runtime.

The committed repository does NOT contain the base64 bundle itself unless the
original R3R1 application allowlist already authorizes such a path. Do not
expand application scope merely to store this bootstrap bundle.

---

# COMPLETE ORIGINAL R3R1 AUTHORIZATION — ALL NON-E01 TERMS REMAIN IN FORCE

# ONE-SHOT CODEX OWNER AUTHORIZATION — PROPOSALOPS / AMEC PHASE5 FINAL R3R1
## Independent-NO_GO closure: evidence mapping + validator truth + finalizer identity + transparent corpus coverage + sanitized immutable handoff
**Date:** 2026-08-24 / 2026-08-25 UTC boundary

---

# 0. OWNER AUTHORIZATION / SUPERSESSION

The Owner explicitly authorizes exactly one bounded Phase5 descendant repair
after the R3 implementation/runtime completed successfully but independent
acceptance returned NO_GO.

This prompt supersedes the old R3 **repair authorization** only.

Preserve all R2/R3 commits, runs, artifacts, failures, and successful runtime
evidence as immutable historical provenance.

Do not rerun the old R3 prompt unchanged.

Do not rerun the old R3 independent-acceptance prompt unchanged after this
repair because its exact lineage is hard-bound to the two-application-commit
R3 state. A successful R3R1 requires a newly rebound independent review.

This is not Azure deployment authorization.
This is not Phase6 authorization.
This is not real-data authorization.

---

# 1. GOVERNING SOURCE / STATE RULE

Use:

```text
latest explicit Owner/product decision
+ later executable repository/runtime evidence
+ later independent acceptance where required
= governing current state
```

Keep distinct:

```text
IMPLEMENTED
VERIFIED_LOCAL
VERIFIED_SQLSERVER_COMPAT
VERIFIED_BROWSER
VERIFIED_AZURE_SQL
VERIFIED_DEPLOYED
INDEPENDENTLY_ACCEPTED
```

Exact executable run/artifact evidence outranks self-report.

Independent acceptance NO_GO outranks a successful self-validation workflow for
the acceptance state without erasing the successful runtime provenance.

---

# 2. EXACT ACCEPTED PHASE4 ENTRY — IMMUTABLE

Reprove live before mutation:

```text
PHASE4_INDEPENDENT_ACCEPTANCE=PASS

PHASE4_ACCEPTED_BRANCH=
phase4-v36r1-final-closure-r3r5r3-v1

PHASE4_ACCEPTED_SHA=
707003fc16767fb28b9c968fbcf168ab03ebadc1

PHASE4_ACCEPTED_PARENT=
fb1d504ae058c09a9fdd84a5afd68bcb3916e35c

PHASE4_ACCEPTED_TREE=
af473134f6a92b9dc9919eae71f1e02a3ed81e1e

PHASE4_ACCEPTANCE_VALIDATION_BRANCH=
phase4-v36r1-final-validation-r3r5r3-e2-v1

PHASE4_ACCEPTANCE_VALIDATION_SHA=
d56817d27a9aaaf69aa08b5e314f78297ed45376

PHASE4_ACCEPTANCE_RUN_ID=32778775085

PHASE4_ACCEPTANCE_ARTIFACT_SHA256=
877f1e39c4bb0e16187dcf4de76ba47cff7df3bdf7cb01a2ae6027da1df4f4a6

PHASE3C_ACCEPTED_SHA=
44968e3d43571ceb1df8493da683ff9e51a146d9

AMEC_MODULE_TRUTH_CONTRACT_SHA256=
d18ebed191b8f2633d5984ff57ab25803fe19beeb9c73999946abffddb974f2c

AMEC_CORPUS_APP_INTEGRATION_CONTRACT_SHA256=
387a741b2531afb54398fadbe8aac0d73e2a1ba9aab619e48d5dd5b5d7289908

ACTIVE_ALEMBIC_HEAD=
baseline_phase4_v36_azure_sql
```

No Phase4 reimplementation.

---

# 3. CURRENT DATABASE / SERVICE DECISION — DO NOT REOPEN

Preserve:

```text
DATABASE_TARGET_DECISION=OWNER_CONFIRMED
DATABASE_ENGINE_TARGET=AZURE_SQL_SQL_SERVER_ENGINE

AZURE_SQL_SERVICE_VARIANT=AZURE_SQL_DATABASE
AZURE_SQL_DATABASE_SELECTED=true
AZURE_SQL_MANAGED_INSTANCE_SELECTED=false
AZURE_SQL_EXACT_SKU=OWNER_DECISION_PENDING

PHASE5_ENGINE_VALIDATION_TARGET=MICROSOFT_SQL_SERVER_2022_X64

VERIFIED_AZURE_SQL=false
VERIFIED_DEPLOYED=false
```

Older exact governing design/action files copied later in this prompt contain
historical PostgreSQL wording. Preserve their bytes exactly for provenance.
Those historical field values do not supersede the later Owner SQL Server /
Azure SQL Database decision above.

---

# 4. EXACT R3 IMPLEMENTATION / VALIDATION / RUN — REPROVE LIVE

Application:

```text
PHASE5_R3_APPLICATION_BRANCH=
phase5-classifier-shadow-validation-r3-v1

PHASE5_R3_APPLICATION_SHA=
46c91cb74f8e686d99a82809ccc73553c7c781d1

PHASE5_R3_APPLICATION_PARENT=
ca60459f2103cbf30e52e05c59b8af6d7714be12

PHASE5_R3_APPLICATION_TREE=
0aacf61b86c3dbfbbe877c001a67b2f94eba8ef1
```

Validation:

```text
PHASE5_R3_VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-r3-v1

PHASE5_R3_VALIDATION_SHA=
a5e6b9425ead924e35bb55cafc065251de0cb021

PHASE5_R3_VALIDATION_PARENT=
46c91cb74f8e686d99a82809ccc73553c7c781d1

PHASE5_R3_VALIDATION_TREE=
02f75d956ebbd93b046ee7771c17a68688645191

PHASE5_R3_VALIDATION_WORKFLOW=
.github/workflows/phase5-classifier-shadow-validation-ci-r3.yml
```

Authoritative successful runtime:

```text
RUN_ID=32805203565
JOB_ID=97673870740
ARTIFACT_ID=9548038478

ARTIFACT_SHA256=
13e956cc29c1b3d66664152f0782df06f7c1f969ca5b3c28f0d6e3a3ebce675f

R3_WORKFLOW_CONCLUSION=success
```

Require exact app→validation diff:

```text
VALIDATION_CHANGED_PATH_COUNT=1
VALIDATION_CHANGED_PATH=
.github/workflows/phase5-classifier-shadow-validation-ci-r3.yml
```

---

# 5. EXACT INDEPENDENT R3 NO_GO — GOVERNING REPAIR INPUT

Record:

```text
RESULT=PHASE5_R3_INDEPENDENT_ACCEPTANCE_NO_GO
PHASE5_INDEPENDENT_ACCEPTANCE=FAIL
PHASE5_ACCEPTED_SHA=NOT_SET

HARD_FAIL_COUNT=5
FIRST_HARD_FAIL_CONTROL_ID=C06

C06_ACCEPTANCE_EVIDENCE_MAPPING_HARD_FAIL=true
C08_EVIDENCE_VALIDATOR_SEMANTIC_HARD_FAIL=true
FINALIZER_META_BINDING_HARD_FAIL=true

INDEPENDENT_RUBRIC_CONTROL_COUNT=350
INDEPENDENT_MACHINE_CHECK_COUNT=632
INDEPENDENT_MACHINE_CHECK_FAIL_COUNT=5

INDEPENDENT_EVIDENCE_GAP_COUNT=1
```

The exact five hard failures are repair authority:

```text
C06
Acceptance evidence mappings materially insufficient.
At least 150 PASS rows lack required producer coverage.

C08
evidence_validate.py accepts wrong candidate SHA, validation SHA, run ID,
and source-only runtime evidence; metric semantics are wrong.

C19C
finalizer.meta.json omits validation_sha and run_id.

C07
robustness corpus lacks transparent M1-M7 / FINANCE / MASTER_CONTENT / REPORTS
coverage accounting and exact FORM / REPORT / ENGINEERING_WORK / DEFINITION
Master Content type accounting.

C20
13 uploaded artifact members contain local absolute /home/runner/... paths.
```

Evidence gap:

```text
Exact governing Phase5 design/actions/R3 prompt source bytes were unavailable to
the independent reviewer for SHA256 recomputation.
```

R3R1 must close all five hard failures plus this evidence gap before remote
execution.

---

# 6. DO NOT MISCLASSIFY THE R3 RUN

Preserve successful R3 runtime provenance:

```text
CRITICAL_FALSE_PROMOTIONS=0

PHASE5_SQLSERVER_TARGETED_PASS=16
PHASE5_SQLSERVER_TARGETED_FAIL=0

PHASE5_BROWSER_REQUIRED_PATH_PASS=10
PHASE5_BROWSER_REQUIRED_PATH_FAIL=0

PHASE5_ACCEPTANCE_CHECK_COUNT=300
PHASE5_ACCEPTANCE_CHECK_FAIL=0
```

But preserve:

```text
PHASE5_R3_INDEPENDENT_ACCEPTANCE=FAIL
PHASE5_ACCEPTED_SHA=NOT_SET
```

Do not call R3 accepted.

---

# 7. NEW R3R1 BRANCHES — ABSENCE GATE

Before mutation require both absent remotely:

```text
phase5-classifier-shadow-validation-r3r1-v1
phase5-classifier-shadow-validation-ci-r3r1-v1
```

If either exists:

```text
RESULT=STOP_PHASE5_R3R1_BRANCH_ALREADY_EXISTS
```

STOP.

---

# 8. CREATE R3R1 APPLICATION BRANCH

Create directly from exact:

```text
PHASE5_R3R1_APPLICATION_BRANCH=
phase5-classifier-shadow-validation-r3r1-v1

PHASE5_R3R1_APPLICATION_BASE=
46c91cb74f8e686d99a82809ccc73553c7c781d1
```

No merge.
No rebase.
No amend.
No force push.

R3 remains immutable.

After successful R3R1 commit, lineage will be:

```text
accepted Phase4 707003...
→ R2 ca60459...
→ R3 46c91cb...
→ R3R1 <new candidate>
```

Therefore:

```text
PHASE5_APPLICATION_COMMITS_ABOVE_ACCEPTED_PHASE4=3
```

The old R3 independent-review assumption of 2 application commits is
SUPERSEDED for a successful R3R1 descendant.

---

# 9. APPLICATION MUTATION ALLOWLIST — EXACT

Only these paths may change or be created:

```text
scripts/phase5/registry.py
scripts/phase5/acceptance.py
scripts/phase5/evidence_validate.py
scripts/phase5/finalize.py
scripts/phase5/phase5_finalize.py
scripts/phase5/build_corpus.py
scripts/phase5/corpus_coverage.py
scripts/phase5/source_preflight.py
scripts/phase5/sanitize_evidence.py
scripts/phase5/browser_evidence.py

backend/tests/test_phase5_contracts.py
backend/tests/test_phase5_evidence_integrity.py
backend/tests/test_phase5_finalizer_negative.py

contracts/amec/phase5/AMEC_CLASSIFIER_ROBUSTNESS_CORPUS_V2.json
contracts/amec/phase5/AMEC_CLASSIFIER_V2_FREEZE_MANIFEST_v1.json

docs/phase5/governing/ProposalOps_Phase5_Classifier_Shadow_Validation_Master_Design.md
docs/phase5/governing/ProposalOps_Phase5_190_Check_Design_Validation_Report.md
docs/phase5/governing/ProposalOps_Phase5_Actions.md
docs/phase5/governing/ProposalOps_Phase5_FINAL_R3_OneShot_EvidenceTruth_SQLServer_Browser_Closure_2026-08-24.md
docs/phase5/governing/manifest.json
```

A listed path may remain unchanged if not needed.

No other application path is authorized.

Explicitly frozen:

```text
backend/app/services/classifier_v2.py

backend/app/models/**
backend/migrations/**
backend/app/db.py

backend/app/services/phase4.py
backend/app/schemas/phase4.py
backend/app/api/phase4.py

contracts/amec/phase3c/**
contracts/amec/phase4/**

backend/requirements*.txt
backend/requirements-runtime.lock
backend/pyproject.toml

frontend/**
```

No classifier behavior change is authorized by the known five hard failures.

If another application path is genuinely required:

```text
RESULT=STOP_PHASE5_R3R1_APPLICATION_SCOPE_EXPANSION_REQUIRED
REQUIRED_PATH=<exact>
REASON=<exact>
```

STOP before commit.

---

# 10. R3R1 REPAIR LEDGER — SIX ROWS, ALL EXECUTABLE

Before commit create a local-only repair ledger:

```text
artifacts/phase5-r3r1-repair-ledger.json
```

Rows exactly:

```text
C06_ACCEPTANCE_EVIDENCE_MAPPING
C08_EVIDENCE_VALIDATOR_SEMANTICS
C19C_FINALIZER_META_TRIPLE_BINDING
C07_CORPUS_COVERAGE_ACCOUNTING
C20_SANITIZED_ARTIFACT_PATHS
E01_GOVERNING_SOURCE_BYTES_RETRIEVABLE
```

Each must be:

```text
CLOSED_WITH_EXECUTABLE_REGRESSION
```

before commit.

Do not stage the local repair ledger.

---

# 11. CENTRAL CATEGORY EVIDENCE POLICY — SINGLE SOURCE OF TRUTH

Move/define the acceptance evidence policy in:

```text
scripts/phase5/registry.py
```

Acceptance and evidence validation must consume the same policy object.

Do not keep independent divergent category mappings.

At minimum each category policy has:

```text
category
required_producer_ids
runtime_required
```

Every producer ID must exist in the central producer registry.

## 11.1 Exact hard mappings required by the R3 authorization / C06 review

Require these mappings as complete required subsets:

```text
SQLSERVER
→ sqlserver-bootstrap
→ sqlserver-targeted

BROWSER_NEW
BROWSER_AMBIGUOUS
BROWSER_OUT_OF_SCOPE
BROWSER_SECRET
BROWSER_MODIFIED
BROWSER_MOVE_RENAME
BROWSER_MISSING
BROWSER_CORRECTION
BROWSER_PROTECTED
→ browser-required-paths
→ browser-quality

REGRESSION
→ backend-targeted
→ phase4-integration-regression
→ backend-full
→ frontend-targeted
→ frontend-full
→ frontend-build

BOUNDARY
→ shadow-replay
→ authority-denial
→ security-hygiene

FREEZE
→ input-identity
→ freeze-reproducibility
→ classifier-validation
→ classifier-holdout
→ classifier-cross-context
→ classifier-path-counterfactual

REVIEW
PROMOTION
CORRECTION
→ shadow-replay
→ sqlserver-targeted
→ authority-denial
```

Do not omit any producer above.

## 11.2 Audit all 30 categories, not only the known failures

For every one of the 30 acceptance categories, mechanically answer:

```text
DO_THE_REQUIRED_PRODUCERS_SUBSTANTIVELY_PROVE_THIS_CATEGORY'S_ASSERTIONS?
```

No round-robin producer assignment.

No acceptance.py self-reference as evidence.

A category may require additional producers beyond Section 11.1 when its
assertions need them.

Require:

```text
PHASE5_CATEGORY_POLICY_COUNT=30
PHASE5_CATEGORY_POLICY_UNKNOWN_PRODUCER_COUNT=0
PHASE5_CATEGORY_POLICY_EMPTY_REQUIRED_PRODUCER_COUNT=0

PHASE5_C06_REQUIRED_MAPPING_MISSING_COUNT=0
```

Add unit tests that compare the critical mappings above exactly.

---

# 12. ACCEPTANCE ENGINE — STABLE EVIDENCE IDS, NO LOCAL PATHS

Repair:

```text
scripts/phase5/acceptance.py
```

Preserve exactly 300 unique primary requirements unless a source audit proves a
different governing count; do not add padding.

Each primary check must contain:
- unique check ID;
- requirement ID;
- category;
- assertion;
- method;
- evidence IDs;
- result.

Evidence IDs must be stable registry identifiers, not local filesystem paths.

Use stable shape equivalent to:

```text
evidence://<producer-id>/result
```

or producer IDs resolved through the registry.

Never write:

```text
/home/runner/...
$RUNNER_TEMP absolute value
$GITHUB_WORKSPACE absolute value
local Path(...).as_posix() absolute path
```

into acceptance result evidence references.

Every PASS row must cite **all required producers** from the central category
policy.

Acceptance returns PASS only if:
- all required producers exist;
- all required producer states are PASS;
- runtime-required categories have actual runtime producer evidence;
- no required producer is NOT_EXECUTED;
- no unknown/unresolved evidence ID exists.

Require remote:

```text
PHASE5_ACCEPTANCE_CHECK_COUNT=300
PHASE5_ACCEPTANCE_CHECK_PASS=300
PHASE5_ACCEPTANCE_CHECK_FAIL=0

PHASE5_ACCEPTANCE_CHECK_WITHOUT_REQUIREMENT_ID=0
PHASE5_ACCEPTANCE_DUPLICATE_CHECK_ID_COUNT=0
PHASE5_ACCEPTANCE_DUPLICATE_REQUIREMENT_PADDING_COUNT=0
PHASE5_ACCEPTANCE_DUPLICATE_ASSERTION_COUNT=0

PHASE5_ACCEPTANCE_UNKNOWN_EVIDENCE_ID_COUNT=0
PHASE5_ACCEPTANCE_UNRESOLVED_EVIDENCE_REFERENCE_COUNT=0

PHASE5_C06_PASS_ROW_MISSING_REQUIRED_PRODUCER_COUNT=0
```

---

# 13. C08 — STRICT EVIDENCE VALIDATOR

Repair:

```text
scripts/phase5/evidence_validate.py
```

## 13.1 CLI identities are mandatory

CLI must require:

```text
--expected-candidate-sha
--expected-validation-sha
--expected-run-id
```

No default.
No environment-only implicit fallback for remote acceptance.

## 13.2 Validate every PASS check

For every PASS primary check:

1. resolve its category through the central category policy;
2. resolve every evidence ID through the central producer registry;
3. prove all required producer IDs for that category are cited;
4. prove required raw/meta/result files exist and are non-zero;
5. parse metadata;
6. for every runtime producer require exact:
   - `candidate_sha == expected candidate`;
   - `validation_sha == expected validation`;
   - `str(run_id) == str(expected run)`;
   - integer `exit_code == 0`;
7. require producer result `PASS`;
8. reject `NOT_EXECUTED`;
9. reject self-reference to acceptance/finalizer as sole substantive proof;
10. require at least one runtime-required producer for every runtime-required
    category;
11. reject unknown or unresolved evidence IDs.

## 13.3 Correct metric semantics

Compute:

```text
runtime_required_source_only_pass_count
```

as:

```text
count(
  PASS acceptance checks
  where category_policy.runtime_required == true
  and cited evidence contains ZERO runtime_required producers
)
```

Do not count passing runtime PRODUCERS.

Remote success requires:

```text
runtime_required_source_only_pass_count=0
```

Also compute:

```text
false_accept_count
unknown_evidence_id_count
unresolved_evidence_reference_count
identity_mismatch_count
not_executed_reference_count
self_reference_only_count
missing_required_producer_count
```

All must equal zero.

## 13.4 Mandatory negative matrix

Actual validator CLI/function must reject disposable fixtures for:

```text
wrong candidate SHA
wrong validation SHA
wrong run ID
runtime-required check backed only by deterministic/source evidence
missing required category producer
NOT_EXECUTED producer
missing producer file
zero-byte producer file
unknown evidence ID
unresolved evidence URI
self-referential evidence only
failed producer
noninteger/blank exit code
```

Require:

```text
PHASE5_EVIDENCE_VALIDATOR_NEGATIVE_CASE_COUNT>=13
PHASE5_EVIDENCE_VALIDATOR_FALSE_ACCEPT_COUNT=0
```

---

# 14. C19C — FINALIZER MUST NOT REQUIRE OR PRESEED ITSELF

Repair:

```text
scripts/phase5/finalize.py
scripts/phase5/phase5_finalize.py
```

## 14.1 Remove circular finalizer dependency

When validating prerequisite producers, `finalizer` is not an input producer to
itself.

Do not require `finalizer.raw/meta/result` to exist before the finalizer runs.

The validation workflow must not pre-seed a finalizer PASS.

Require source audit:

```text
FINALIZER_SELF_PREREQUISITE_COUNT=0
WORKFLOW_PRESEEDED_FINALIZER_PASS_COUNT=0
```

## 14.2 Triple identity binding

Finalizer CLI must require:

```text
--expected-candidate-sha
--expected-validation-sha
--expected-run-id
```

Finalizer validates all runtime producer metadata against all three exact
identities.

It also validates the evidence-validator result is bound to the same three.

Only after all prerequisite checks pass may finalizer write:

```text
finalizer.raw.log
finalizer.meta.json
finalizer.result.json
phase5-final-summary.json
```

`finalizer.meta.json` must contain exact:

```text
producer_id=finalizer
candidate_sha=<exact candidate>
validation_sha=<exact validation>
run_id=<exact run>
exit_code=0
```

The finalizer result and final summary must also include the exact three
identities.

## 14.3 Negative tests

Actual finalizer must reject at minimum:
- missing candidate identity;
- missing validation identity;
- missing run identity;
- wrong candidate identity;
- wrong validation identity;
- wrong run identity;
- failed evidence validator;
- source-only runtime false accept;
- missing required producer;
- failed producer;
- NOT_EXECUTED producer.

Preserve/expand the existing finalizer negative suite.

Require:

```text
PHASE5_FINALIZER_META_CANDIDATE_BINDING=true
PHASE5_FINALIZER_META_VALIDATION_BINDING=true
PHASE5_FINALIZER_META_RUN_BINDING=true
PHASE5_FINALIZER_NEGATIVE_FALSE_ACCEPT_COUNT=0
```

---

# 15. C07 — TRANSPARENT ROBUSTNESS COVERAGE, DO NOT FABRICATE

Repair deterministic corpus generation:

```text
scripts/phase5/build_corpus.py
scripts/phase5/corpus_coverage.py
contracts/amec/phase5/AMEC_CLASSIFIER_ROBUSTNESS_CORPUS_V2.json
```

Do not change the 12 existing case IDs.
Do not change split membership.
Do not change classifier/rules bytes.

Add deterministic coverage accounting for exact truth domains:

```text
M1
M2
M3
M4
M5
M6
M7
FINANCE
MASTER_CONTENT
REPORTS
```

and exact Master Content types:

```text
FORM
REPORT
ENGINEERING_WORK
DEFINITION
```

Each entry must include at minimum:

```text
coverage_state = ADEQUATE | THIN | MISSING
evidence_case_ids = []
reason
safe_disposition
```

Coverage must be derived only from explicit corpus metadata.

Do not infer a Master Content type from generic `MASTER_CONTENT`.

Do not infer REPORTS truth-domain coverage from Master Content `REPORT`.

Do not invent quotas.

Based on current explicit corpus metadata, the deterministic derivation should
truthfully produce unless the current exact source proves otherwise:

```text
FINANCE=THIN
MASTER_CONTENT=THIN

M1=MISSING
M2=MISSING
M3=MISSING
M4=MISSING
M5=MISSING
M6=MISSING
M7=MISSING
REPORTS=MISSING

FORM=MISSING
REPORT=MISSING
ENGINEERING_WORK=MISSING
DEFINITION=MISSING
```

If exact candidate metadata has changed before execution, derive rather than
hard-code, but never silently promote MISSING/THIN to ADEQUATE.

For THIN/MISSING:

```text
safe_disposition=REVIEW_OR_ABSTAIN
```

No automatic authoritative promotion may depend on missing coverage.

Require:

```text
PHASE5_TRUTH_DOMAIN_COVERAGE_ACCOUNTED_COUNT=10
PHASE5_MASTER_CONTENT_TYPE_COVERAGE_ACCOUNTED_COUNT=4
PHASE5_COVERAGE_UNKNOWN_STATE_COUNT=0
PHASE5_COVERAGE_UNACCOUNTED_DOMAIN_COUNT=0
PHASE5_COVERAGE_UNACCOUNTED_MASTER_CONTENT_TYPE_COUNT=0
PHASE5_FABRICATED_ADEQUATE_COUNT=0
```

`corpus_coverage.py` must validate the committed corpus and emit a deterministic
result JSON.

Register `corpus-coverage` as a deterministic producer and execute it remotely.

Preserve:

```text
CRITICAL_FALSE_PROMOTIONS=0
```

THIN/MISSING is not itself a classifier failure.

---

# 16. CORPUS/FREEZE NON-REGRESSION

Because the canonical corpus JSON gains coverage metadata, its SHA changes.

Preserve the actual case/split behavior.

Before commit compare R3 → R3R1 and require:

```text
CORPUS_CASE_ID_SET_UNCHANGED=true
CORPUS_CASE_SEMANTIC_FIELDS_UNCHANGED=true

CALIBRATION_CASE_IDS_UNCHANGED=true
VALIDATION_CASE_IDS_UNCHANGED=true
HOLDOUT_CASE_IDS_UNCHANGED=true
ADVERSARIAL_CASE_IDS_UNCHANGED=true

CLASSIFIER_SOURCE_SHA_UNCHANGED=true
RULES_SHA_UNCHANGED=true
CLASSIFIER_VERSION_UNCHANGED=true
RULES_VERSION_UNCHANGED=true
TAXONOMY_REVISION_UNCHANGED=true
```

Regenerate/update the committed freeze manifest only as required to bind the
new corpus SHA.

Do not manufacture changed classifier evaluation results if case semantics are
unchanged.

Require freeze consistency after regeneration.

---

# 17. C20 — SANITIZED ARTIFACT PIPELINE

Create:

```text
scripts/phase5/sanitize_evidence.py
```

## 17.1 Working evidence vs upload evidence

Use:

```text
WORKING_EVIDENCE_DIR=$RUNNER_TEMP/...
SANITIZED_EVIDENCE_DIR=$RUNNER_TEMP/...-sanitized
```

All runtime validation, acceptance, evidence validation, and finalizer operate
on `WORKING_EVIDENCE_DIR`.

After finalizer, build a separate sanitized immutable copy.

Upload only `SANITIZED_EVIDENCE_DIR`.

Never upload the working evidence directory.

## 17.2 Sanitization

For text/JSON/XML/log artifacts, sanitize local filesystem paths.

At minimum detect/replace:
- exact `$GITHUB_WORKSPACE`;
- exact `$RUNNER_TEMP`;
- `/home/runner/...`;
- `/tmp/...`;
- `/private/tmp/...`;
- `/Users/...`;
- Windows `C:\Users\...` / runner work equivalents.

Use stable non-absolute tokens, e.g.:

```text
<REPO_ROOT>
<RUNNER_TEMP>
```

Do not alter:
- SHA values;
- run IDs;
- candidate/validation identities;
- URLs;
- evidence producer IDs;
- business assertions/results.

For JSON/XML after sanitization, reparse to prove validity.

Create:

```text
artifact-sanitization.result.json
artifact-manifest.sha256
```

The sanitizer must copy the four committed governing source files into:

```text
SANITIZED_EVIDENCE_DIR/governing/
```

and include their exact hashes in the artifact manifest.

## 17.3 Hard path scan

After sanitization recursively scan every uploaded regular file.

Require:

```text
LOCAL_ABSOLUTE_PATH_MATCH_COUNT=0
HOME_RUNNER_PATH_MATCH_COUNT=0
RUNNER_TEMP_PATH_MATCH_COUNT=0
GITHUB_WORKSPACE_PATH_MATCH_COUNT=0

SANITIZED_JSON_PARSE_FAIL_COUNT=0
SANITIZED_XML_PARSE_FAIL_COUNT=0

SANITIZED_ARTIFACT_MANIFEST_HASH_MISMATCH_COUNT=0
```

## 17.4 Regression fixture

Create synthetic text/JSON/XML/log fixtures containing local absolute Linux,
macOS, and Windows paths.

Require sanitizer removes all local absolute paths while preserving semantic
identity fields.

---

# 18. STRUCTURED RESULT FILES SHOULD NOT CREATE ABSOLUTE PATHS

Repair where needed:

```text
scripts/phase5/acceptance.py
scripts/phase5/browser_evidence.py
```

Structured result JSON should reference:
- producer IDs;
- stable evidence URIs;
- artifact-relative names.

Do not write local absolute report/result paths into structured acceptance or
browser result JSON.

This reduces sanitizer burden; the final sanitizer remains mandatory because
third-party raw logs/Playwright/JUnit can still contain runner paths.

---

# 19. GOVERNING SOURCE BYTES — COMMIT EXACT APPENDICES

Create directory:

```text
docs/phase5/governing/
```

The four exact source files are appended verbatim to this authorization.

Extract them byte-for-byte between their BEGIN/END markers.

Do not normalize whitespace.
Do not change line endings.
Do not add headers.
Do not strip the final newline.

Required hashes:

```text
ProposalOps_Phase5_Classifier_Shadow_Validation_Master_Design.md
SHA256=
761dd4e642ce8dc30589bab393808e965a4f931e9e2a9ddda94cff6f217fa81b

ProposalOps_Phase5_190_Check_Design_Validation_Report.md
SHA256=
61e57216ca5b8671df7337420bb7d116c94be138da62cde851dcab6236ecbe0f

ProposalOps_Phase5_Actions.md
SHA256=
87a2376489a394806f9b11dadad5db710a0a0149ee895a449d1e4ea06823968e

ProposalOps_Phase5_FINAL_R3_OneShot_EvidenceTruth_SQLServer_Browser_Closure_2026-08-24.md
SHA256=
0fcb3efe875dff8b8d0c5cd939666ddcf37ea4d3d256e501d8c1927b288d34c5
```

Create deterministic:

```text
docs/phase5/governing/manifest.json
```

with:
- relative path;
- SHA256;
- byte count;
- source role;
- `copied_verbatim=true`.

Roles:

```text
MASTER_DESIGN
DESIGN_VALIDATION
ACTIONS
R3_EXECUTION_AUTHORIZATION
```

Also record:

```text
CURRENT_ENGINE_OVERLAY=
AZURE_SQL_SQL_SERVER_ENGINE

CURRENT_SERVICE_VARIANT_OVERLAY=
AZURE_SQL_DATABASE

HISTORICAL_ENGINE_WORDING_MAY_BE_SUPERSEDED=true
```

Require:

```text
PHASE5_GOVERNING_SOURCE_COUNT=4
PHASE5_GOVERNING_SOURCE_HASH_MISMATCH_COUNT=0
PHASE5_GOVERNING_SOURCE_BYTES_RETRIEVABLE=true
```

The source preflight must verify these hashes.

---

# 20. SOURCE PREFLIGHT V4 — MUST CATCH ALL FIVE HARD FAILURES BEFORE COMMIT

Upgrade:

```text
scripts/phase5/source_preflight.py
```

to:

```text
PHASE5_SOURCE_PREFLIGHT_VERSION=4
```

Preserve all V3 checks.

Add hard checks for:

## C06
- exact critical category producer mappings;
- all 30 categories resolve to known producers;
- runtime-required policies have runtime producers.

## C08
- validator requires candidate/validation/run identities;
- validator compares all three for runtime producers;
- validator computes per-check source-only runtime metric;
- negative fixture matrix passes.

## C19C
- finalizer has no self prerequisite;
- workflow plan contains no preseeded finalizer PASS;
- finalizer requires/writes candidate+validation+run.

## C07
- exact 10 truth-domain coverage entries;
- exact 4 Master Content type entries;
- valid states only;
- no fabricated ADEQUATE;
- safe disposition for THIN/MISSING.

## C20
- sanitizer exists;
- sanitizer regression passes;
- upload plan points only to sanitized evidence directory.

## Governing-source evidence gap
- all four exact committed source hashes match.

Require:

```text
PHASE5_SOURCE_PREFLIGHT_DEFINITE_BLOCKER_COUNT=0

C06_PREFLIGHT_PASS=true
C08_PREFLIGHT_PASS=true
C19C_PREFLIGHT_PASS=true
C07_PREFLIGHT_PASS=true
C20_PREFLIGHT_PASS=true
GOVERNING_SOURCE_PREFLIGHT_PASS=true
```

Do not hard-code these booleans. Derive from inspected executable source/tests.

Write local-only:

```text
artifacts/phase5-r3r1-source-preflight-v4.json
```

Do not stage generated preflight output.

---

# 21. PRECOMMIT FALSE-ACCEPT MATRIX — THE MOST IMPORTANT ANTI-LOOP GATE

Before the application commit, build temporary producer evidence.

Mark runtime producers:

```text
NOT_EXECUTED
```

Then prove:

```text
RUNTIME_REQUIRED_ACCEPTANCE_PASS_COUNT=0
PHASE5_PRECOMMIT_RUNTIME_FALSE_ACCEPT_COUNT=0
```

Next construct a complete **synthetic test evidence** set with fake-but-consistent
test identities solely for unit contract testing and prove:
- all 300 mappings resolve;
- all critical categories contain required producer sets;
- validator passes only when identities match;
- every corruption case fails.

This synthetic contract fixture is not runtime acceptance evidence and must not
be committed/uploaded as Phase5 runtime proof.

Require:

```text
PHASE5_ACCEPTANCE_REFERENCE_DRY_RUN=PASS
PHASE5_C06_300_ROW_MAPPING_DRY_RUN=PASS

PHASE5_EVIDENCE_VALIDATOR_NEGATIVE_FALSE_ACCEPT_COUNT=0
PHASE5_FINALIZER_NEGATIVE_FALSE_ACCEPT_COUNT=0
PHASE5_SANITIZER_NEGATIVE_FALSE_ACCEPT_COUNT=0
```

---

# 22. LOCAL PRECOMMIT MATRIX

Run at minimum:

```bash
pytest -q backend/tests/test_phase5_contracts.py
pytest -q backend/tests/test_phase5_evidence_integrity.py
pytest -q backend/tests/test_phase5_finalizer_negative.py

pytest -q backend/tests/test_phase5_sqlserver_runtime.py
pytest -q backend/tests/test_phase5_classifier.py
pytest -q backend/tests/test_phase5_integration.py
pytest -q backend/tests/test_phase5_shadow_runtime.py
pytest -q backend/tests/test_phase4_corpus_app_integration.py

pytest -q

python -m compileall -q backend scripts

python scripts/phase5/source_preflight.py
python scripts/phase5/reproducibility.py
python scripts/phase5/corpus_coverage.py \
  --corpus contracts/amec/phase5/AMEC_CLASSIFIER_ROBUSTNESS_CORPUS_V2.json

git diff --check
```

Frontend source/build preflight:

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

Require all actual failures zero.

No local test may be promoted to fresh remote SQL Server/browser proof.

---

# 23. WHOLE-SURFACE NO-LOOP AUDIT BEFORE APPLICATION COMMIT

Independently inspect all Phase5 producer/consumer surfaces, not just edited
lines.

At minimum audit:

```text
scripts/phase5/*.py
backend/tests/test_phase5*.py
contracts/amec/phase5/*
frontend/browser-real-stack/phase5-classifier-shadow.spec.ts

planned R3R1 workflow
```

Mechanically verify:
- every producer ID consumed is registered;
- every acceptance category policy resolves;
- every finalizer prerequisite can exist before finalizer;
- no circular producer dependency;
- every workflow CLI argument matches executable parser;
- every workflow required result name matches registry;
- all runtime producer meta is created with candidate/validation/run;
- no successful finalizer can overwrite complete identity with incomplete meta;
- sanitizer runs after finalizer and before upload;
- only sanitized evidence is uploaded;
- corpus coverage is transparent;
- governing source hashes are present;
- no classifier behavior path changed;
- no Phase4 path changed;
- no migration/model/dependency change.

Require:

```text
PHASE5_R3R1_WHOLE_SURFACE_DEFINITE_BLOCKER_COUNT=0
```

If a new definite blocker requires a non-allowlisted path:

```text
RESULT=STOP_PHASE5_R3R1_ADDITIONAL_DEFINITE_BLOCKER_FOUND
BLOCKER=<exact>
REQUIRED_PATH=<exact>
```

STOP before commit.

Do not silently broaden scope.

---

# 24. APPLICATION DIFF GATE

Before commit require:

```text
PHASE5_R3R1_APPLICATION_PARENT=
46c91cb74f8e686d99a82809ccc73553c7c781d1

PHASE5_R3R1_CLASSIFIER_BEHAVIOR_PATH_CHANGE_COUNT=0
PHASE5_R3R1_PHASE4_PATH_CHANGE_COUNT=0
PHASE5_R3R1_MIGRATION_MODEL_CHANGE_COUNT=0
PHASE5_R3R1_DEPENDENCY_CHANGE_COUNT=0
PHASE5_R3R1_FRONTEND_CHANGE_COUNT=0
PHASE5_R3R1_UNAUTHORIZED_PATH_COUNT=0
```

No generated `artifacts/**` staged.

---

# 25. CREATE EXACTLY ONE R3R1 APPLICATION COMMIT

Create one commit on:

```text
phase5-classifier-shadow-validation-r3r1-v1
```

Parent exactly:

```text
46c91cb74f8e686d99a82809ccc73553c7c781d1
```

Recommended message:

```text
fix(phase5): close independent evidence acceptance gaps
```

Record:

```text
PHASE5_R3R1_CANDIDATE_SHA=<exact>
PHASE5_R3R1_CANDIDATE_TREE=<exact>
PHASE5_R3R1_CHANGED_PATH_COUNT=<exact>
PHASE5_R3R1_CHANGED_PATHS=<exact>
```

Push only application branch.

After push:

```text
SECOND_APPLICATION_COMMIT_AUTHORIZED=false
```

---

# 26. CREATE FRESH R3R1 VALIDATION BRANCH

Create directly from exact R3R1 candidate:

```text
PHASE5_R3R1_VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-r3r1-v1
```

Create exactly one workflow-only child commit.

Workflow path:

```text
.github/workflows/phase5-classifier-shadow-validation-ci-r3r1.yml
```

Do not branch from `a5e6b942...`.

---

# 27. WORKFLOW SOURCE AUTHORITY

Use exact successful R3 workflow as structural/runtime source:

```text
SOURCE_VALIDATION_SHA=
a5e6b9425ead924e35bb55cafc065251de0cb021

SOURCE_WORKFLOW_PATH=
.github/workflows/phase5-classifier-shadow-validation-ci-r3.yml
```

Preserve:
- candidate/branch parent binding;
- Ubuntu 22.04 x86-64;
- Docker;
- Python 3.12;
- ODBC Driver 18;
- Node/npm;
- Playwright Chromium installation;
- SQL Server 2022 Developer;
- fresh databases;
- migration;
- seed;
- source/deterministic producers;
- native SQL Server targeted producer;
- real browser producer;
- regressions;
- authority/observability/security;
- cleanup.

Do not redesign working runtime harness unrelated to the five hard failures.

---

# 28. R3R1 WORKFLOW BINDING

Set:

```text
CANDIDATE_SHA=<PHASE5_R3R1_CANDIDATE_SHA>

CANDIDATE_PARENT_SHA=
46c91cb74f8e686d99a82809ccc73553c7c781d1

CANDIDATE_BRANCH=
phase5-classifier-shadow-validation-r3r1-v1

VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-r3r1-v1
```

Require:

```bash
test "$(git rev-parse "refs/remotes/origin/$CANDIDATE_BRANCH")" = "$CANDIDATE_SHA"
test "$(git rev-parse HEAD^1)" = "$CANDIDATE_SHA"
```

Validation commit diff must be exactly:

```text
.github/workflows/phase5-classifier-shadow-validation-ci-r3r1.yml
```

---

# 29. ADD CORPUS COVERAGE PRODUCER

During deterministic source producers run:

```text
producer_id=corpus-coverage
```

Execute committed `corpus_coverage.py`.

Require result:

```text
result=PASS
truth_domain_coverage_accounted=10
master_content_type_coverage_accounted=4
fabricated_adequate_count=0
```

Its raw/meta/result evidence must be registered.

---

# 30. REMOTE RUNTIME — FULL FRESH REEXECUTION

Do not inherit R3 runtime PASS.

Use fresh SQL Server databases.

Run:
- classifier source/freeze producers;
- native SQL Server 2022 targeted validation;
- actual SHADOW replay;
- authority/observability/security;
- backend/frontend regressions;
- real browser against same SQL Server-backed backend.

Require fresh:

```text
CRITICAL_FALSE_PROMOTIONS=0

PHASE5_SQLSERVER_TARGETED_GATE_COUNT=16
PHASE5_SQLSERVER_TARGETED_PASS=16
PHASE5_SQLSERVER_TARGETED_FAIL=0
PHASE5_SQLSERVER_TARGETED_SKIP=0

PHASE5_BROWSER_REQUIRED_PATH_COUNT=10
PHASE5_BROWSER_REQUIRED_PATH_PASS=10
PHASE5_BROWSER_REQUIRED_PATH_FAIL=0
PHASE5_BROWSER_REQUIRED_PATH_SKIP=0

PHASE5_BROWSER_API_MOCK_COUNT_FOR_REQUIRED_PATHS=0

PHASE5_TARGETED_BACKEND_FAIL=0
PHASE4_INTEGRATION_REGRESSION_FAIL=0
BACKEND_FULL_FAIL=0

PHASE5_TARGETED_FRONTEND_FAIL=0
FRONTEND_FULL_FAIL=0
FRONTEND_BUILD=PASS
PHASE5_BROWSER_FAIL=0
```

---

# 31. REMOTE ACCEPTANCE — C06 MUST BE PROVEN FROM THE 300 ROWS

Only after all runtime producer evidence exists run:

```text
scripts/phase5/acceptance.py
```

Then independently inside the workflow cross-check the acceptance result before
evidence validation.

For every PASS row verify:
- category policy exists;
- all required producer IDs are cited;
- no unknown evidence ID;
- every runtime-required category cites runtime evidence.

Require:

```text
PHASE5_ACCEPTANCE_CHECK_COUNT=300
PHASE5_ACCEPTANCE_CHECK_PASS=300
PHASE5_ACCEPTANCE_CHECK_FAIL=0

PHASE5_C06_PASS_ROW_MISSING_REQUIRED_PRODUCER_COUNT=0
PHASE5_ACCEPTANCE_RUNTIME_REQUIRED_SOURCE_ONLY_PASS_COUNT=0
```

If any one of the 300 rows lacks required producer coverage, STOP.

---

# 32. REMOTE EVIDENCE VALIDATOR — EXACT TRIPLE IDENTITY

Invoke equivalent:

```bash
python scripts/phase5/evidence_validate.py \
  --evidence-dir "$EVIDENCE_DIR" \
  --acceptance-result "$EVIDENCE_DIR/acceptance-result.json" \
  --expected-candidate-sha "$CANDIDATE_SHA" \
  --expected-validation-sha "$VALIDATION_SHA" \
  --expected-run-id "$GITHUB_RUN_ID" \
  --output "$EVIDENCE_DIR/evidence-validation.result.json"
```

Require:

```text
result=PASS

candidate_sha=<exact candidate>
validation_sha=<exact validation>
run_id=<exact run>

false_accept_count=0
runtime_required_source_only_pass_count=0
unknown_evidence_id_count=0
unresolved_evidence_reference_count=0
identity_mismatch_count=0
not_executed_reference_count=0
self_reference_only_count=0
missing_required_producer_count=0
```

---

# 33. REMOTE FINALIZER — NO PRESEED

Delete the R3 workflow's finalizer pre-seed workaround.

Do not create:

```text
finalizer.raw.log
finalizer.meta.json
finalizer.result.json
```

before invoking the actual finalizer.

Invoke equivalent:

```bash
python scripts/phase5/phase5_finalize.py \
  --evidence-dir "$EVIDENCE_DIR" \
  --acceptance-result "$EVIDENCE_DIR/acceptance-result.json" \
  --validation-result "$EVIDENCE_DIR/evidence-validation.result.json" \
  --contracts-dir contracts/amec/phase5 \
  --expected-candidate-sha "$CANDIDATE_SHA" \
  --expected-validation-sha "$VALIDATION_SHA" \
  --expected-run-id "$GITHUB_RUN_ID" \
  --output "$EVIDENCE_DIR/phase5-final-summary.json"
```

After actual finalizer returns 0 require:

```text
finalizer.meta.json:
candidate_sha=<exact>
validation_sha=<exact>
run_id=<exact>
exit_code=0
```

Require final summary:

```text
RUN_EVIDENCE_STATE=COMPLETE_PASS
```

Anything missing/failing/NOT_EXECUTED = fail closed.

---

# 34. SANITIZE ONLY AFTER SUCCESSFUL FINALIZATION

After actual finalizer:

```bash
python scripts/phase5/sanitize_evidence.py \
  --source "$EVIDENCE_DIR" \
  --dest "$SANITIZED_EVIDENCE_DIR" \
  --governing-source-dir docs/phase5/governing \
  --expected-candidate-sha "$CANDIDATE_SHA" \
  --expected-validation-sha "$VALIDATION_SHA" \
  --expected-run-id "$GITHUB_RUN_ID" \
  --require-complete
```

Then require:

```text
LOCAL_ABSOLUTE_PATH_MATCH_COUNT=0
HOME_RUNNER_PATH_MATCH_COUNT=0
RUNNER_TEMP_PATH_MATCH_COUNT=0
GITHUB_WORKSPACE_PATH_MATCH_COUNT=0

SANITIZED_ARTIFACT_MANIFEST_HASH_MISMATCH_COUNT=0
SANITIZED_GOVERNING_SOURCE_HASH_MISMATCH_COUNT=0
```

Re-run a read-only evidence consistency verification against the sanitized copy
where practical.

Do not alter runtime truth while sanitizing.

---

# 35. FAILURE ARTIFACT SANITIZATION

If any remote step fails before complete finalization, still build a sanitized
partial diagnostic artifact in an `if: always()` step.

The sanitizer must support explicit partial diagnostic mode:

```text
--allow-partial
```

Partial mode:
- sanitizes available evidence;
- never changes failure to PASS;
- records `RUN_EVIDENCE_STATE=PARTIAL_FAILED`;
- uploads sanitized diagnostics only.

Never upload an unsanitized working directory even on failure.

---

# 36. UPLOAD ONLY SANITIZED EVIDENCE

`actions/upload-artifact` path must be exactly the sanitized evidence directory.

Require:

```text
WORKING_EVIDENCE_UPLOAD_COUNT=0
SANITIZED_EVIDENCE_UPLOAD_COUNT=1
```

Artifact name should identify R3R1 + run ID.

Retention may remain bounded.

---

# 37. WORKFLOW PRECOMMIT AUDIT

Before workflow commit mechanically prove:

```text
VALIDATION_PARENT_SHA=
PHASE5_R3R1_CANDIDATE_SHA

VALIDATION_CHANGED_PATH_COUNT=1
VALIDATION_CHANGED_PATH=
.github/workflows/phase5-classifier-shadow-validation-ci-r3r1.yml

CANDIDATE_REMOTE_BRANCH_SHA_BINDING_PRESENT=true
CANDIDATE_PARENT_SHA_BINDING_PRESENT=true

EVIDENCE_VALIDATOR_EXPECTED_CANDIDATE_ARG_PRESENT=true
EVIDENCE_VALIDATOR_EXPECTED_VALIDATION_ARG_PRESENT=true
EVIDENCE_VALIDATOR_EXPECTED_RUN_ARG_PRESENT=true

FINALIZER_EXPECTED_CANDIDATE_ARG_PRESENT=true
FINALIZER_EXPECTED_VALIDATION_ARG_PRESENT=true
FINALIZER_EXPECTED_RUN_ARG_PRESENT=true

WORKFLOW_PRESEEDED_FINALIZER_PASS_COUNT=0

CORPUS_COVERAGE_PRODUCER_PRESENT=true

SANITIZER_ALWAYS_STEP_PRESENT=true
WORKING_EVIDENCE_UPLOAD_COUNT=0
SANITIZED_EVIDENCE_UPLOAD_COUNT=1

WORKFLOW_OUTPUT_CONTRACT_MISMATCH_COUNT=0
WORKFLOW_REQUIRED_EVIDENCE_NAME_MISMATCH_COUNT=0
```

Also syntax-check YAML and shell fragments.

---

# 38. CREATE EXACTLY ONE WORKFLOW-ONLY CHILD COMMIT

On:

```text
phase5-classifier-shadow-validation-ci-r3r1-v1
```

create exactly one commit.

Parent:

```text
PHASE5_R3R1_CANDIDATE_SHA
```

Only changed path:

```text
.github/workflows/phase5-classifier-shadow-validation-ci-r3r1.yml
```

Recommended message:

```text
ci(phase5): validate independently acceptable R3R1 evidence
```

Push only validation branch.

No main.
No tag.
No release.

---

# 39. RUN THE EXACT R3R1 WORKFLOW ONCE

Wait for exact:

```text
head_branch=
phase5-classifier-shadow-validation-ci-r3r1-v1

head_sha=
PHASE5_R3R1_VALIDATION_SHA
```

Run full workflow from the beginning.

No inherited PASS.

No auto-repair after a failure.

---

# 40. SUCCESS ARTIFACT INDEPENDENT-REVIEW READINESS CHECK

After a successful workflow, download the exact uploaded artifact outside the
repository.

Hash/re-extract it.

Before returning success, verify from the downloaded sanitized artifact:

```text
ZIP_DUPLICATE_MEMBER_COUNT=0
ZIP_UNSAFE_PATH_COUNT=0
ZIP_SYMLINK_COUNT=0
ZERO_BYTE_REQUIRED_MEMBER_COUNT=0

LOCAL_ABSOLUTE_PATH_MATCH_COUNT=0
MANIFEST_HASH_MISMATCH_COUNT=0

GOVERNING_SOURCE_FILE_COUNT=4
GOVERNING_SOURCE_HASH_MISMATCH_COUNT=0

FINALIZER_META_CANDIDATE_MATCH=true
FINALIZER_META_VALIDATION_MATCH=true
FINALIZER_META_RUN_MATCH=true

EVIDENCE_VALIDATOR_CANDIDATE_MATCH=true
EVIDENCE_VALIDATOR_VALIDATION_MATCH=true
EVIDENCE_VALIDATOR_RUN_MATCH=true

PHASE5_C06_PASS_ROW_MISSING_REQUIRED_PRODUCER_COUNT=0
runtime_required_source_only_pass_count=0

PHASE5_TRUTH_DOMAIN_COVERAGE_ACCOUNTED_COUNT=10
PHASE5_MASTER_CONTENT_TYPE_COVERAGE_ACCOUNTED_COUNT=4
```

This is still Codex self-check, not independent acceptance.

---

# 41. SAFETY / AUTHORITY BOUNDARY

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
LLM_REAL_CONTENT_MODE=DISABLED

MAIN_CHANGED=false
MAIN_PUSHED=false
TAG_CREATED=false
RELEASE_CREATED=false
DEPLOYMENT_STARTED=false

PHASE6_STARTED=false
```

Final government/consequential human authority remains unchanged.

---

# 42. FAILURE POLICY — NO AUTOMATIC R3R2

If application precommit fails:

```text
RESULT=STOP_PHASE5_R3R1_APPLICATION_PRECOMMIT_FAILED
FIRST_FAILED_GATE=<exact>
FAILURE_EVIDENCE=<sanitized exact>
```

STOP.

If remote run fails:

```text
RESULT=STOP_PHASE5_R3R1_REMOTE_VALIDATION_FAILED

FIRST_FAILED_GATE=<exact>
FIRST_FAILED_SUBGATE=<exact if known>
FAILURE_EVIDENCE=<sanitized exact>

PHASE5_R3R1_CANDIDATE_SHA=<exact>
PHASE5_R3R1_VALIDATION_SHA=<exact>

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

Do not create R3R2 automatically.
Do not weaken the failed gate.
Do not make a second app/workflow commit under this authorization.

---

# 43. TRUTHFUL SUCCESS STATE

A complete successful R3R1 runtime may establish:

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
```

But it does not self-accept Phase5.

Require:

```text
PHASE5_CODEX_SELF_ACCEPTED=false
PHASE5_INDEPENDENT_ACCEPTANCE=PENDING
PHASE5_ACCEPTED_SHA=NOT_SET
```

---

# 44. FINAL SUCCESS RETURN

Only if every R3R1 precommit/runtime/evidence/sanitized-artifact check passes:

```text
RESULT=PHASE5_FINAL_R3R1_CANDIDATE_READY_FOR_REBOUND_INDEPENDENT_ACCEPTANCE

PHASE5_R3R1_BRANCH=
phase5-classifier-shadow-validation-r3r1-v1

PHASE5_R3R1_CANDIDATE_SHA=<exact>
PHASE5_R3R1_CANDIDATE_PARENT=
46c91cb74f8e686d99a82809ccc73553c7c781d1
PHASE5_R3R1_CANDIDATE_TREE=<exact>

PHASE5_APPLICATION_COMMITS_ABOVE_ACCEPTED_PHASE4=3

PHASE5_R3R1_VALIDATION_BRANCH=
phase5-classifier-shadow-validation-ci-r3r1-v1

PHASE5_R3R1_VALIDATION_SHA=<exact>
PHASE5_R3R1_VALIDATION_PARENT=
<PHASE5_R3R1_CANDIDATE_SHA>
PHASE5_R3R1_VALIDATION_TREE=<exact>

REMOTE_RUN_ID=<exact>
REMOTE_JOB_ID=<exact>
REMOTE_ARTIFACT_ID=<exact>
REMOTE_ARTIFACT_SHA256=<exact>

C06_ACCEPTANCE_EVIDENCE_MAPPING_HARD_FAIL=false
C08_EVIDENCE_VALIDATOR_SEMANTIC_HARD_FAIL=false
FINALIZER_META_BINDING_HARD_FAIL=false
C07_CORPUS_COVERAGE_HARD_FAIL=false
C20_LOCAL_ABSOLUTE_PATH_HARD_FAIL=false
GOVERNING_SOURCE_EVIDENCE_GAP=false

PHASE5_C06_PASS_ROW_MISSING_REQUIRED_PRODUCER_COUNT=0

false_accept_count=0
runtime_required_source_only_pass_count=0
identity_mismatch_count=0

FINALIZER_META_CANDIDATE_BINDING=true
FINALIZER_META_VALIDATION_BINDING=true
FINALIZER_META_RUN_BINDING=true

PHASE5_TRUTH_DOMAIN_COVERAGE_ACCOUNTED_COUNT=10
PHASE5_MASTER_CONTENT_TYPE_COVERAGE_ACCOUNTED_COUNT=4
PHASE5_FABRICATED_ADEQUATE_COUNT=0

LOCAL_ABSOLUTE_PATH_MATCH_COUNT=0
SANITIZED_ARTIFACT_MANIFEST_HASH_MISMATCH_COUNT=0

GOVERNING_SOURCE_FILE_COUNT=4
GOVERNING_SOURCE_HASH_MISMATCH_COUNT=0

CRITICAL_FALSE_PROMOTIONS=0

PHASE5_SQLSERVER_TARGETED_PASS=16
PHASE5_SQLSERVER_TARGETED_FAIL=0
PHASE5_SQLSERVER_TARGETED_SKIP=0

PHASE5_BROWSER_REQUIRED_PATH_PASS=10
PHASE5_BROWSER_REQUIRED_PATH_FAIL=0
PHASE5_BROWSER_REQUIRED_PATH_SKIP=0

PHASE5_ACCEPTANCE_CHECK_COUNT=300
PHASE5_ACCEPTANCE_CHECK_PASS=300
PHASE5_ACCEPTANCE_CHECK_FAIL=0

RUN_EVIDENCE_STATE=COMPLETE_PASS

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

AZURE_ACCESSED=false
ENTRA_ACCESSED=false
SYNOLOGY_ACCESSED=false
SMB_ACCESSED=false
REAL_DATA_USED=false

MAIN_CHANGED=false
MAIN_PUSHED=false

PHASE5_CODEX_SELF_ACCEPTED=false
PHASE5_INDEPENDENT_ACCEPTANCE=PENDING
PHASE5_ACCEPTED_SHA=NOT_SET

NEXT=REBIND_AND_RUN_PHASE5_R3R1_INDEPENDENT_ACCEPTANCE_REVIEW
```

Then STOP.

Do not start deployment readiness.
Do not start Azure commissioning.
Do not start Phase6.

---

# APPENDIX A — EXACT GOVERNING SOURCE BYTES

The bytes between each BEGIN/END marker are the exact source file contents.
Write only the enclosed bytes to the stated repository path.

The marker lines themselves are NOT part of the target file.

<<<BEGIN_EXACT_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_Classifier_Shadow_Validation_Master_Design.md::SHA256=761dd4e642ce8dc30589bab393808e965a4f931e9e2a9ddda94cff6f217fa81b>>>
# ProposalOps / AMEC — Phase 5 Classifier v2 Freeze + Shadow/Review + LOCAL/POSTGRESQL/BROWSER Validation
## Locked master execution design

## Phase identity
Phase 5 closes the missing classifier step before shadowing. It includes: content-assisted Classifier v2 calibration from verified evidence; robustness/regression; classifier freeze; integration with accepted Phase4; SHADOW replay/review; `VERIFIED_LOCAL`; `VERIFIED_POSTGRESQL`; `VERIFIED_BROWSER`.

It does not include production auto-promotion, real continuous Synology monitoring unless separately authorized, Synology writeback, Azure deployed certification, or cloud LLM processing of real AMEC content without authority.

## Hard entry gate
Require `PHASE4_INDEPENDENT_ACCEPTANCE=PASS`, exact `PHASE4_ACCEPTED_SHA`, exact Phase4 integration/freeze SHAs, Phase3C independent acceptance, exact Module Truth SHA, Stage1R-A complete and Stage1R-B not required. Otherwise `RESULT=PHASE5_NOT_AUTHORIZED_PHASE4_ACCEPTANCE_MISSING`, STOP.

Create `phase5-classifier-shadow-validation-v1` zero-delta from exact Phase4 accepted SHA.

## Robustness corpus
Create/freeze `AMEC_CLASSIFIER_ROBUSTNESS_CORPUS_V2`. Allowed: existing sanitized/golden fixtures; dangerous negatives; VERIFIED Stage1R evidence; sanitized derivatives; synthetic counterfactual/adversarial variants; reviewed correction events only for future versions. Never use unverified classifier output as ground truth. Raw AMEC content stays outside Git.

Track source family, format, business scope, source role, instantiation, module, family, Master Content candidacy, revision/currentness, project/entity link, duplicate/version, sensitivity, noise, path reliability. Cover M1-M7, FINANCE, MASTER_CONTENT FORM/REPORT/ENGINEERING_WORK/DEFINITION, REPORTS. Mark ADEQUATE/THIN/MISSING; do not invent quotas.

## Leakage-safe splits
Freeze CALIBRATION_DEVELOPMENT, VALIDATION, HOLDOUT_ADVERSARIAL. Group by source artifact/version, duplicates, template family, project/entity where feasible. Holdout remains untouched during development. Freeze manifest SHAs.

## Hybrid classifier
`DocumentEvidenceEnvelope → L0 prior-state/source mode → L1 hard gates → L2 typed rules/resolvers → L3 optional learned lane → L4 bounded LLM resolver → L5 cross-axis consistency → material review → ClassificationEnvelope proposal`.

LLM/model are not authority. Human review is not failure.

L0 distinguishes EXISTING_KNOWN_SOURCE, NEW_UNKNOWN_SOURCE, MODIFIED_KNOWN_SOURCE, MOVE_RENAME_CANDIDATE. Reuse frozen axes for known sources; reevaluate affected axes for modified sources; move/rename reuse only after identity proof.

L1 hard gates include object kind/noise, business scope, known identity, business/project identifiers, template IDs, duplicate graph, sensitivity. Scope values: CORE_IN_SCOPE, ADJACENT_RECOGNIZED, OUT_OF_SCOPE, AMBIGUOUS_REVIEW. OUT_OF_SCOPE means no deeper classifier, no LLM, no projection. SECRET_EXCLUDE means no LLM/index/preview/training/projection.

L2 decisions record rule_id, rule_version, axis, evidence_ids and cannot overwrite higher-authority evidence.

## Optional learned lane
Only if verified labels are sufficient. Compare rules-only vs rules+learned on untouched validation/holdout. Promote only with measurable benefit and no increase in critical false promotions. Otherwise `LEARNED_CLASSIFIER_MODE=NOT_PROMOTED_DATA_INSUFFICIENT`.

## LLM seam
Default `LLM_REAL_CONTENT_MODE=DISABLED`. Validate with synthetic/sanitized fixtures. LLM cannot override OUT_OF_SCOPE, declare canonical source, authorize Finance/professional approval, choose current version from prose, or execute protected actions.

## Confusable regressions
Mandatory: technical artifact vs business doc; blank vs false positive; directory vs file; backup vs active source; personal IBAN/payroll vs AMEC Finance; executed guarantee vs blank template; professional registration vs project permit; employee vs project handover; Shop Drawing vs Submittal; drawing vs authority submission; material technical data vs submittal; blank vs executed form; report template vs output; historical vs current; duplicate vs revision; path/filename hints vs stronger evidence; unresolved external provenance vs canonical AMEC authority. Contradiction→NEEDS_REVIEW.

## Acceptance philosophy and freeze
Optimize for `CRITICAL_FALSE_PROMOTIONS=0`, evidence-backed routing, useful coverage, safe abstention, bounded review, repeatability, cross-format/context robustness, low I/O, reproducibility. Require zero critical false promotions on golden, validation, untouched holdout/adversarial.

Freeze taxonomy revision, classifier version, rules version, ClassifierEnvelope schema SHA, calibration/validation/holdout manifests, golden/cross-format/cross-context/adversarial result SHAs, optional learned/LLM identities, LLM real-content mode, Document Intelligence Runtime/DocumentEvidenceEnvelope identity, Module Truth SHA, Phase4 Integration Contract SHA.

## SHADOW integration
Integrate frozen classifier with accepted Phase4:
`Source event/App Upload/replay → stability/version → Source Intake → DocumentEvidenceEnvelope → frozen Classifier v2 → ClassificationEnvelope → review comparison`.

SHADOW means classification generated and comparison recorded, but NO classifier-only VerifiedAssertion promotion, NO classifier-only typed projection, NO Synology writeback. VerifiedAssertion/projection may be exercised only through explicit review/test actions.

Review triggers: contradictions, AMBIGUOUS_REVIEW, low-confidence material module/family, project-link ambiguity, Master Content ambiguity, canonical conflict, external conflict, provenance dependency, unsupported parser. Optional unknown axis alone need not force review.

Every correction is immutable ClassifierCorrectionEvent. It cannot mutate this frozen version; changes belong to a future version.

## Shadow data sources / authority
Offline/replay shadow may use verified Stage1R evidence, golden/validation/holdout fixtures, and synthetic app uploads with no new NAS reads.

Real continuous shadow is separately authorized. Default:
- `REAL_LIVE_SHADOW_ENABLED=false`
- `NEW_SMB_CONNECTIONS=0`
- `NEW_AMEC_SOURCE_READS=0`
- no NAS secret
- no watcher

A future `AMEC_LIVE_SHADOW_ACTIVATION_MANIFEST_v1` is a separate gate.

## Verification states
Prove separately: `VERIFIED_LOCAL`, `VERIFIED_POSTGRESQL`, `VERIFIED_BROWSER`. Never infer `VERIFIED_DEPLOYED`.

### LOCAL
Full backend; full frontend; production build; golden/validation/holdout; cross-format/context; path counterfactual; unknown-family abstention; unsupported-capability review; Phase4 integration targeted suite.

### POSTGRESQL
Fresh disposable supported-major PostgreSQL; full migration chain; source-event idempotency; intake race/locks; immutable ClassificationEnvelope; review concurrency; append-only correction; VerifiedAssertion supersession; projection idempotency; side-effect de-duplication; rollback-on-failure; checkpoint/resume where applicable. SQLite cannot substitute.

### BROWSER
Use existing Playwright real-stack harness: real frontend→local backend→disposable PostgreSQL. Required paths:
1. NEW synthetic/app-upload→intake→classification→review→accept/correct→VerifiedAssertion→projection→audit/work.
2. AMBIGUOUS→reason visible→no auto-promotion.
3. OUT_OF_SCOPE→no deeper classifier/projection.
4. SECRET_EXCLUDE→no preview/model content.
5. modified known source→new version/affected-axis review.
6. move/rename→no duplicate logical record.
7. missing source→Issue/Notification/history retained.
8. correction→original envelope unchanged and correction event visible.
9. protected consequential action→server denial.
10. personas Owner/Business Development/Engineering see appropriate review/work.

Browser quality: no console errors/uncaught network failures in golden paths; loading/error/empty states; keyboard-accessible actions; basic axe pass; deep links resolve; root/correlation inspectable.

## Observability and drift
Each chain reconstructs root event, source/version/token, runtime/parser, classifier/rules/taxonomy/ModuleTruth/Phase4 identities, rule/evidence IDs, classification, review, optional reviewed projection, latency/bytes, LLM usage/cost, errors/retries. No secrets.

Track unknown/review/correction rates, module/business-scope/family/project/MasterContent corrections, unseen terms/families. Drift creates review/version-candidate work; never mutates frozen classifier.

## Production boundary after Phase5
Even after pass:
- `AUTO_PROMOTION_ENABLED=false`
- `REAL_LIVE_SHADOW_ENABLED=false` unless separately authorized
- `SYNOLOGY_WRITEBACK_ENABLED=false`
- `VERIFIED_DEPLOYED=false`

Allowed claim after actual pass: `PRODUCTION_CLASSIFIER_CANDIDATE=true` and `PRODUCTION_APP_CLASSIFICATION_READY_LOCAL_POSTGRESQL_BROWSER=true`, not deployed readiness.

## Artifacts and acceptance
Create Phase5 classifier freeze/runtime/input manifests plus coverage, regression, shadow, local, PostgreSQL, browser, and acceptance reports.

Codex must run at least 180 actual acceptance checks with per-check ID/category/assertion/method/evidence/result covering entry/ancestry, corpus provenance, no raw data, leakage, module coverage, negatives, source-mode/hard gates/rules, optional learned lane, LLM disabled-real-content, cross-axis invariants, critical false promotions, freeze identities, shadow boundaries, review/corrections, Phase4 integration, LOCAL/POSTGRESQL/BROWSER, persona/RBAC/protected actions, observability/drift, no NAS/SMB, no deployed claim, deterministic freeze.

Terminal if actually green:
- `PHASE5_CANDIDATE_COMPLETE=true`
- `CLASSIFIER_V2_FROZEN=true`
- `PRODUCTION_CLASSIFIER_CANDIDATE=true`
- `VERIFIED_LOCAL=true`
- `VERIFIED_POSTGRESQL=true`
- `VERIFIED_BROWSER=true`
- `VERIFIED_DEPLOYED=false`
- `AUTO_PROMOTION_ENABLED=false`
- `REAL_LIVE_SHADOW_ENABLED=false`
- `SYNOLOGY_WRITEBACK_ENABLED=false`
- `PHASE5_CODEX_SELF_ACCEPTED=false`
- `PHASE5_INDEPENDENT_ACCEPTANCE=PENDING`
- `NEXT=INDEPENDENT_PHASE5_REVIEW`

If any state fails, report it false and STOP; never weaken gates.


## Validation clarification — exact entry/domain/operational invariants
Required exact input identity fields:
- `PHASE4_INTEGRATION_CONTRACT_SHA256=<exact>`
- `AMEC_MODULE_TRUTH_CONTRACT_SHA256=<exact>`

Required domain coverage is explicit:
`M1`, `M2`, `M3`, `M4`, `M5`, `M6`, `M7`, `FINANCE`, `MASTER_CONTENT`, `REPORTS`.

Operational boundary:
- `SECRET_REQUIRED=false`
- classification, event intake, review decisions, VerifiedAssertion promotion, and projection retries must be idempotent where the operation contract requires retry safety.
<<<END_EXACT_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_Classifier_Shadow_Validation_Master_Design.md>>>

<<<BEGIN_EXACT_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_190_Check_Design_Validation_Report.md::SHA256=61e57216ca5b8671df7337420bb7d116c94be138da62cde851dcab6236ecbe0f>>>
# ProposalOps Phase5 190 Check Design Validation

```text
RESULT=PASS
CHECKS_TOTAL=190
CHECKS_PASS=190
CHECKS_FAIL=0
VALIDATED_DESIGN_SHA256=761dd4e642ce8dc30589bab393808e965a4f931e9e2a9ddda94cff6f217fa81b
```

> Pre-execution design validation only. This does not claim implementation or runtime verification. The final report reflects the surgically corrected design bytes after the first validation exposed missing explicit invariants.

| # | Category | Result | Assertion | Evidence |
|---:|---|:---:|---|---|
| 1 | entry | **PASS** | Requires Phase4 independent acceptance | `PHASE4_INDEPENDENT_ACCEPTANCE=PASS` |
| 2 | entry | **PASS** | Requires Phase4 exact SHA | `PHASE4_ACCEPTED_SHA` |
| 3 | entry | **PASS** | Requires Phase4 contract | `PHASE4_INTEGRATION_CONTRACT_SHA256` |
| 4 | entry | **PASS** | Requires Module Truth | `AMEC_MODULE_TRUTH_CONTRACT_SHA256` |
| 5 | corpus | **PASS** | Robustness corpus | `AMEC_CLASSIFIER_ROBUSTNESS_CORPUS_V2` |
| 6 | corpus | **PASS** | Calibration split | `CALIBRATION_DEVELOPMENT` |
| 7 | corpus | **PASS** | Validation split | `VALIDATION` |
| 8 | corpus | **PASS** | Holdout split | `HOLDOUT_ADVERSARIAL` |
| 9 | coverage | **PASS** | M1 | `M1` |
| 10 | coverage | **PASS** | M2 | `M2` |
| 11 | coverage | **PASS** | M3 | `M3` |
| 12 | coverage | **PASS** | M4 | `M4` |
| 13 | coverage | **PASS** | M5 | `M5` |
| 14 | coverage | **PASS** | M6 | `M6` |
| 15 | coverage | **PASS** | M7 | `M7` |
| 16 | coverage | **PASS** | Finance | `FINANCE` |
| 17 | coverage | **PASS** | MasterContent | `MASTER_CONTENT` |
| 18 | coverage | **PASS** | Reports | `REPORTS` |
| 19 | coverage | **PASS** | ADEQUATE | `ADEQUATE` |
| 20 | coverage | **PASS** | THIN | `THIN` |
| 21 | coverage | **PASS** | MISSING | `MISSING` |
| 22 | classifier | **PASS** | L0 | `L0 prior-state/source mode` |
| 23 | classifier | **PASS** | L1 | `L1 hard gates` |
| 24 | classifier | **PASS** | L2 | `L2 typed rules/resolvers` |
| 25 | classifier | **PASS** | L3 | `L3 optional learned lane` |
| 26 | classifier | **PASS** | L4 | `L4 bounded LLM resolver` |
| 27 | classifier | **PASS** | L5 | `L5 cross-axis consistency` |
| 28 | source-mode | **PASS** | Existing known | `EXISTING_KNOWN_SOURCE` |
| 29 | source-mode | **PASS** | New unknown | `NEW_UNKNOWN_SOURCE` |
| 30 | source-mode | **PASS** | Modified known | `MODIFIED_KNOWN_SOURCE` |
| 31 | source-mode | **PASS** | Move rename | `MOVE_RENAME_CANDIDATE` |
| 32 | scope | **PASS** | Core | `CORE_IN_SCOPE` |
| 33 | scope | **PASS** | Adjacent | `ADJACENT_RECOGNIZED` |
| 34 | scope | **PASS** | Out | `OUT_OF_SCOPE` |
| 35 | scope | **PASS** | Ambiguous | `AMBIGUOUS_REVIEW` |
| 36 | security | **PASS** | Secret exclude | `SECRET_EXCLUDE` |
| 37 | security | **PASS** | Real content LLM disabled | `LLM_REAL_CONTENT_MODE=DISABLED` |
| 38 | quality | **PASS** | Critical false promotions zero | `CRITICAL_FALSE_PROMOTIONS=0` |
| 39 | quality | **PASS** | Safe abstention | `safe abstention` |
| 40 | quality | **PASS** | Cross-format | `cross-format` |
| 41 | quality | **PASS** | Cross-context | `cross-context` |
| 42 | negative | **PASS** | Personal finance confusion | `personal IBAN/payroll vs AMEC Finance` |
| 43 | negative | **PASS** | Guarantee confusion | `executed guarantee vs blank template` |
| 44 | negative | **PASS** | Permit registration confusion | `professional registration vs project permit` |
| 45 | negative | **PASS** | Handover confusion | `employee vs project handover` |
| 46 | negative | **PASS** | Shop drawing confusion | `Shop Drawing vs Submittal` |
| 47 | negative | **PASS** | Material confusion | `material technical data vs submittal` |
| 48 | negative | **PASS** | Blank/executed form | `blank vs executed form` |
| 49 | negative | **PASS** | Report template/output | `report template vs output` |
| 50 | negative | **PASS** | Duplicate/revision | `duplicate vs revision` |
| 51 | freeze | **PASS** | Taxonomy revision | `taxonomy revision` |
| 52 | freeze | **PASS** | Classifier version | `classifier version` |
| 53 | freeze | **PASS** | Rules version | `rules version` |
| 54 | freeze | **PASS** | Schema SHA | `ClassifierEnvelope schema SHA` |
| 55 | freeze | **PASS** | Golden result | `golden` |
| 56 | shadow | **PASS** | Shadow integration | `SHADOW` |
| 57 | shadow | **PASS** | No classifier-only assertion | `NO classifier-only VerifiedAssertion promotion` |
| 58 | shadow | **PASS** | No writeback | `NO Synology writeback` |
| 59 | review | **PASS** | Review contradiction | `contradictions` |
| 60 | review | **PASS** | Correction immutable | `ClassifierCorrectionEvent` |
| 61 | authority | **PASS** | Real live shadow false | `REAL_LIVE_SHADOW_ENABLED=false` |
| 62 | verification | **PASS** | Local separate | `VERIFIED_LOCAL` |
| 63 | verification | **PASS** | Postgres separate | `VERIFIED_POSTGRESQL` |
| 64 | verification | **PASS** | Browser separate | `VERIFIED_BROWSER` |
| 65 | verification | **PASS** | Deployed false | `VERIFIED_DEPLOYED=false` |
| 66 | postgres | **PASS** | Event idempotency | `source-event idempotency` |
| 67 | postgres | **PASS** | Row locks | `locks` |
| 68 | postgres | **PASS** | Envelope immutability | `immutable ClassificationEnvelope` |
| 69 | postgres | **PASS** | Review concurrency | `review concurrency` |
| 70 | postgres | **PASS** | Correction append-only | `append-only correction` |
| 71 | postgres | **PASS** | Assertion supersession | `VerifiedAssertion supersession` |
| 72 | postgres | **PASS** | Projection idempotency | `projection idempotency` |
| 73 | browser | **PASS** | New path | `NEW synthetic/app-upload` |
| 74 | browser | **PASS** | Ambiguous path | `AMBIGUOUS` |
| 75 | browser | **PASS** | Out-of-scope path | `OUT_OF_SCOPE` |
| 76 | browser | **PASS** | Secret path | `SECRET_EXCLUDE` |
| 77 | browser | **PASS** | Modified path | `modified known source` |
| 78 | browser | **PASS** | Move path | `move/rename` |
| 79 | browser | **PASS** | Missing path | `missing source` |
| 80 | browser | **PASS** | Correction path | `original envelope unchanged` |
| 81 | browser | **PASS** | Protected action path | `protected consequential action` |
| 82 | browser | **PASS** | Persona path | `Owner/Business Development/Engineering` |
| 83 | browser-quality | **PASS** | Console errors | `no console errors` |
| 84 | browser-quality | **PASS** | Keyboard accessibility | `keyboard-accessible` |
| 85 | browser-quality | **PASS** | Axe | `axe` |
| 86 | observability | **PASS** | Root event | `root event` |
| 87 | observability | **PASS** | Classifier identity | `classifier/rules/taxonomy` |
| 88 | observability | **PASS** | Evidence IDs | `rule/evidence IDs` |
| 89 | drift | **PASS** | Unknown rate | `unknown` |
| 90 | drift | **PASS** | Correction rate | `correction` |
| 91 | boundary | **PASS** | No SMB | `NEW_SMB_CONNECTIONS=0` |
| 92 | boundary | **PASS** | No reads | `NEW_AMEC_SOURCE_READS=0` |
| 93 | boundary | **PASS** | No auto promotion | `AUTO_PROMOTION_ENABLED=false` |
| 94 | boundary | **PASS** | No writeback | `SYNOLOGY_WRITEBACK_ENABLED=false` |
| 95 | claim | **PASS** | Classifier candidate | `PRODUCTION_CLASSIFIER_CANDIDATE=true` |
| 96 | claim | **PASS** | Local/PG/browser readiness | `PRODUCTION_APP_CLASSIFICATION_READY_LOCAL_POSTGRESQL_BROWSER=true` |
| 97 | terminal | **PASS** | Candidate complete | `PHASE5_CANDIDATE_COMPLETE=true` |
| 98 | terminal | **PASS** | Frozen true | `CLASSIFIER_V2_FROZEN=true` |
| 99 | terminal | **PASS** | No self accept | `PHASE5_CODEX_SELF_ACCEPTED=false` |
| 100 | terminal | **PASS** | Independent pending | `PHASE5_INDEPENDENT_ACCEPTANCE=PENDING` |
| 101 | authority | **PASS** | Classifier output remains proposal — consistency lens 1 | `ClassificationEnvelope` |
| 102 | authority | **PASS** | Verified truth boundary explicit — consistency lens 1 | `VerifiedAssertion` |
| 103 | authority | **PASS** | Projection boundary explicit — consistency lens 1 | `typed projection` |
| 104 | authority | **PASS** | No auto-promotion — consistency lens 1 | `AUTO_PROMOTION_ENABLED=false` |
| 105 | authority | **PASS** | Deployed state kept separate — consistency lens 1 | `VERIFIED_DEPLOYED=false` |
| 106 | source | **PASS** | No new SMB path — consistency lens 1 | `NEW_SMB_CONNECTIONS=0` |
| 107 | source | **PASS** | No new AMEC source reads — consistency lens 1 | `NEW_AMEC_SOURCE_READS=0` |
| 108 | source | **PASS** | No secret required — consistency lens 1 | `SECRET_REQUIRED=false` |
| 109 | security | **PASS** | Secret exclusion exists — consistency lens 1 | `SECRET_EXCLUDE` |
| 110 | governance | **PASS** | Independent review required — consistency lens 1 | `INDEPENDENT_ACCEPTANCE=PENDING` |
| 111 | quality | **PASS** | Idempotency required — consistency lens 1 | `idempotent` |
| 112 | quality | **PASS** | Auditability required — consistency lens 1 | `audit` |
| 113 | quality | **PASS** | Protected actions preserved — consistency lens 1 | `protected` |
| 114 | testing | **PASS** | PostgreSQL proof present — consistency lens 1 | `PostgreSQL` |
| 115 | testing | **PASS** | Frontend/browser boundary present — consistency lens 1 | `frontend` |
| 116 | authority | **PASS** | Classifier output remains proposal — consistency lens 2 | `ClassificationEnvelope` |
| 117 | authority | **PASS** | Verified truth boundary explicit — consistency lens 2 | `VerifiedAssertion` |
| 118 | authority | **PASS** | Projection boundary explicit — consistency lens 2 | `typed projection` |
| 119 | authority | **PASS** | No auto-promotion — consistency lens 2 | `AUTO_PROMOTION_ENABLED=false` |
| 120 | authority | **PASS** | Deployed state kept separate — consistency lens 2 | `VERIFIED_DEPLOYED=false` |
| 121 | source | **PASS** | No new SMB path — consistency lens 2 | `NEW_SMB_CONNECTIONS=0` |
| 122 | source | **PASS** | No new AMEC source reads — consistency lens 2 | `NEW_AMEC_SOURCE_READS=0` |
| 123 | source | **PASS** | No secret required — consistency lens 2 | `SECRET_REQUIRED=false` |
| 124 | security | **PASS** | Secret exclusion exists — consistency lens 2 | `SECRET_EXCLUDE` |
| 125 | governance | **PASS** | Independent review required — consistency lens 2 | `INDEPENDENT_ACCEPTANCE=PENDING` |
| 126 | quality | **PASS** | Idempotency required — consistency lens 2 | `idempotent` |
| 127 | quality | **PASS** | Auditability required — consistency lens 2 | `audit` |
| 128 | quality | **PASS** | Protected actions preserved — consistency lens 2 | `protected` |
| 129 | testing | **PASS** | PostgreSQL proof present — consistency lens 2 | `PostgreSQL` |
| 130 | testing | **PASS** | Frontend/browser boundary present — consistency lens 2 | `frontend` |
| 131 | authority | **PASS** | Classifier output remains proposal — consistency lens 3 | `ClassificationEnvelope` |
| 132 | authority | **PASS** | Verified truth boundary explicit — consistency lens 3 | `VerifiedAssertion` |
| 133 | authority | **PASS** | Projection boundary explicit — consistency lens 3 | `typed projection` |
| 134 | authority | **PASS** | No auto-promotion — consistency lens 3 | `AUTO_PROMOTION_ENABLED=false` |
| 135 | authority | **PASS** | Deployed state kept separate — consistency lens 3 | `VERIFIED_DEPLOYED=false` |
| 136 | source | **PASS** | No new SMB path — consistency lens 3 | `NEW_SMB_CONNECTIONS=0` |
| 137 | source | **PASS** | No new AMEC source reads — consistency lens 3 | `NEW_AMEC_SOURCE_READS=0` |
| 138 | source | **PASS** | No secret required — consistency lens 3 | `SECRET_REQUIRED=false` |
| 139 | security | **PASS** | Secret exclusion exists — consistency lens 3 | `SECRET_EXCLUDE` |
| 140 | governance | **PASS** | Independent review required — consistency lens 3 | `INDEPENDENT_ACCEPTANCE=PENDING` |
| 141 | quality | **PASS** | Idempotency required — consistency lens 3 | `idempotent` |
| 142 | quality | **PASS** | Auditability required — consistency lens 3 | `audit` |
| 143 | quality | **PASS** | Protected actions preserved — consistency lens 3 | `protected` |
| 144 | testing | **PASS** | PostgreSQL proof present — consistency lens 3 | `PostgreSQL` |
| 145 | testing | **PASS** | Frontend/browser boundary present — consistency lens 3 | `frontend` |
| 146 | authority | **PASS** | Classifier output remains proposal — consistency lens 4 | `ClassificationEnvelope` |
| 147 | authority | **PASS** | Verified truth boundary explicit — consistency lens 4 | `VerifiedAssertion` |
| 148 | authority | **PASS** | Projection boundary explicit — consistency lens 4 | `typed projection` |
| 149 | authority | **PASS** | No auto-promotion — consistency lens 4 | `AUTO_PROMOTION_ENABLED=false` |
| 150 | authority | **PASS** | Deployed state kept separate — consistency lens 4 | `VERIFIED_DEPLOYED=false` |
| 151 | source | **PASS** | No new SMB path — consistency lens 4 | `NEW_SMB_CONNECTIONS=0` |
| 152 | source | **PASS** | No new AMEC source reads — consistency lens 4 | `NEW_AMEC_SOURCE_READS=0` |
| 153 | source | **PASS** | No secret required — consistency lens 4 | `SECRET_REQUIRED=false` |
| 154 | security | **PASS** | Secret exclusion exists — consistency lens 4 | `SECRET_EXCLUDE` |
| 155 | governance | **PASS** | Independent review required — consistency lens 4 | `INDEPENDENT_ACCEPTANCE=PENDING` |
| 156 | quality | **PASS** | Idempotency required — consistency lens 4 | `idempotent` |
| 157 | quality | **PASS** | Auditability required — consistency lens 4 | `audit` |
| 158 | quality | **PASS** | Protected actions preserved — consistency lens 4 | `protected` |
| 159 | testing | **PASS** | PostgreSQL proof present — consistency lens 4 | `PostgreSQL` |
| 160 | testing | **PASS** | Frontend/browser boundary present — consistency lens 4 | `frontend` |
| 161 | authority | **PASS** | Classifier output remains proposal — consistency lens 5 | `ClassificationEnvelope` |
| 162 | authority | **PASS** | Verified truth boundary explicit — consistency lens 5 | `VerifiedAssertion` |
| 163 | authority | **PASS** | Projection boundary explicit — consistency lens 5 | `typed projection` |
| 164 | authority | **PASS** | No auto-promotion — consistency lens 5 | `AUTO_PROMOTION_ENABLED=false` |
| 165 | authority | **PASS** | Deployed state kept separate — consistency lens 5 | `VERIFIED_DEPLOYED=false` |
| 166 | source | **PASS** | No new SMB path — consistency lens 5 | `NEW_SMB_CONNECTIONS=0` |
| 167 | source | **PASS** | No new AMEC source reads — consistency lens 5 | `NEW_AMEC_SOURCE_READS=0` |
| 168 | source | **PASS** | No secret required — consistency lens 5 | `SECRET_REQUIRED=false` |
| 169 | security | **PASS** | Secret exclusion exists — consistency lens 5 | `SECRET_EXCLUDE` |
| 170 | governance | **PASS** | Independent review required — consistency lens 5 | `INDEPENDENT_ACCEPTANCE=PENDING` |
| 171 | quality | **PASS** | Idempotency required — consistency lens 5 | `idempotent` |
| 172 | quality | **PASS** | Auditability required — consistency lens 5 | `audit` |
| 173 | quality | **PASS** | Protected actions preserved — consistency lens 5 | `protected` |
| 174 | testing | **PASS** | PostgreSQL proof present — consistency lens 5 | `PostgreSQL` |
| 175 | testing | **PASS** | Frontend/browser boundary present — consistency lens 5 | `frontend` |
| 176 | authority | **PASS** | Classifier output remains proposal — consistency lens 6 | `ClassificationEnvelope` |
| 177 | authority | **PASS** | Verified truth boundary explicit — consistency lens 6 | `VerifiedAssertion` |
| 178 | authority | **PASS** | Projection boundary explicit — consistency lens 6 | `typed projection` |
| 179 | authority | **PASS** | No auto-promotion — consistency lens 6 | `AUTO_PROMOTION_ENABLED=false` |
| 180 | authority | **PASS** | Deployed state kept separate — consistency lens 6 | `VERIFIED_DEPLOYED=false` |
| 181 | source | **PASS** | No new SMB path — consistency lens 6 | `NEW_SMB_CONNECTIONS=0` |
| 182 | source | **PASS** | No new AMEC source reads — consistency lens 6 | `NEW_AMEC_SOURCE_READS=0` |
| 183 | source | **PASS** | No secret required — consistency lens 6 | `SECRET_REQUIRED=false` |
| 184 | security | **PASS** | Secret exclusion exists — consistency lens 6 | `SECRET_EXCLUDE` |
| 185 | governance | **PASS** | Independent review required — consistency lens 6 | `INDEPENDENT_ACCEPTANCE=PENDING` |
| 186 | quality | **PASS** | Idempotency required — consistency lens 6 | `idempotent` |
| 187 | quality | **PASS** | Auditability required — consistency lens 6 | `audit` |
| 188 | quality | **PASS** | Protected actions preserved — consistency lens 6 | `protected` |
| 189 | testing | **PASS** | PostgreSQL proof present — consistency lens 6 | `PostgreSQL` |
| 190 | testing | **PASS** | Frontend/browser boundary present — consistency lens 6 | `frontend` |
<<<END_EXACT_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_190_Check_Design_Validation_Report.md>>>

<<<BEGIN_EXACT_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_Actions.md::SHA256=87a2376489a394806f9b11dadad5db710a0a0149ee895a449d1e4ea06823968e>>>
# Phase 5 Actions

Default DSM/human actions: none.

`DSM_ACTIONS_REQUIRED=0`, `NAS_TASK_SCHEDULER_RUNS=0`, `SMB_CONNECTIONS=0`, `NEW_AMEC_SOURCE_READS=0`, `SECRET_REQUIRED=false`.

Do not recreate the NAS secret and do not run a Synology watcher. Phase5 uses repository fixtures, sanitized Stage1R-derived fixtures, restricted accepted evidence where policy permits, synthetic app uploads, local backend/frontend, Playwright, and disposable PostgreSQL.

Disposable PostgreSQL proves PostgreSQL behavior only; it is not Azure PostgreSQL proof. Browser uses frontend→local backend→disposable PostgreSQL; it is not Vercel/Azure deployed proof.

Real continuous Synology shadow is not part of Phase5 by default. It needs a separately independently accepted `AMEC_LIVE_SHADOW_ACTIVATION_MANIFEST_v1`.
<<<END_EXACT_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_Actions.md>>>

<<<BEGIN_EXACT_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_FINAL_R3_OneShot_EvidenceTruth_SQLServer_Browser_Closure_2026-08-24.md::SHA256=0fcb3efe875dff8b8d0c5cd939666ddcf37ea4d3d256e501d8c1927b288d34c5>>>
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
<<<END_EXACT_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_FINAL_R3_OneShot_EvidenceTruth_SQLServer_Browser_Closure_2026-08-24.md>>>


---
# APPENDIX B — AUTHORITATIVE BASE64 GOVERNING SOURCE BYTES

<<<BEGIN_BASE64_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_Classifier_Shadow_Validation_Master_Design.md::SHA256=761dd4e642ce8dc30589bab393808e965a4f931e9e2a9ddda94cff6f217fa81b::BYTE_COUNT=10708>>>
IyBQcm9wb3NhbE9wcyAvIEFNRUMg4oCUIFBoYXNlIDUgQ2xhc3NpZmllciB2MiBGcmVlemUgKyBTaGFkb3cvUmV2aWV3ICsgTE9DQUwvUE9TVEdSRVNRTC9C
Uk9XU0VSIFZhbGlkYXRpb24KIyMgTG9ja2VkIG1hc3RlciBleGVjdXRpb24gZGVzaWduCgojIyBQaGFzZSBpZGVudGl0eQpQaGFzZSA1IGNsb3NlcyB0aGUg
bWlzc2luZyBjbGFzc2lmaWVyIHN0ZXAgYmVmb3JlIHNoYWRvd2luZy4gSXQgaW5jbHVkZXM6IGNvbnRlbnQtYXNzaXN0ZWQgQ2xhc3NpZmllciB2MiBjYWxp
YnJhdGlvbiBmcm9tIHZlcmlmaWVkIGV2aWRlbmNlOyByb2J1c3RuZXNzL3JlZ3Jlc3Npb247IGNsYXNzaWZpZXIgZnJlZXplOyBpbnRlZ3JhdGlvbiB3aXRo
IGFjY2VwdGVkIFBoYXNlNDsgU0hBRE9XIHJlcGxheS9yZXZpZXc7IGBWRVJJRklFRF9MT0NBTGA7IGBWRVJJRklFRF9QT1NUR1JFU1FMYDsgYFZFUklGSUVE
X0JST1dTRVJgLgoKSXQgZG9lcyBub3QgaW5jbHVkZSBwcm9kdWN0aW9uIGF1dG8tcHJvbW90aW9uLCByZWFsIGNvbnRpbnVvdXMgU3lub2xvZ3kgbW9uaXRv
cmluZyB1bmxlc3Mgc2VwYXJhdGVseSBhdXRob3JpemVkLCBTeW5vbG9neSB3cml0ZWJhY2ssIEF6dXJlIGRlcGxveWVkIGNlcnRpZmljYXRpb24sIG9yIGNs
b3VkIExMTSBwcm9jZXNzaW5nIG9mIHJlYWwgQU1FQyBjb250ZW50IHdpdGhvdXQgYXV0aG9yaXR5LgoKIyMgSGFyZCBlbnRyeSBnYXRlClJlcXVpcmUgYFBI
QVNFNF9JTkRFUEVOREVOVF9BQ0NFUFRBTkNFPVBBU1NgLCBleGFjdCBgUEhBU0U0X0FDQ0VQVEVEX1NIQWAsIGV4YWN0IFBoYXNlNCBpbnRlZ3JhdGlvbi9m
cmVlemUgU0hBcywgUGhhc2UzQyBpbmRlcGVuZGVudCBhY2NlcHRhbmNlLCBleGFjdCBNb2R1bGUgVHJ1dGggU0hBLCBTdGFnZTFSLUEgY29tcGxldGUgYW5k
IFN0YWdlMVItQiBub3QgcmVxdWlyZWQuIE90aGVyd2lzZSBgUkVTVUxUPVBIQVNFNV9OT1RfQVVUSE9SSVpFRF9QSEFTRTRfQUNDRVBUQU5DRV9NSVNTSU5H
YCwgU1RPUC4KCkNyZWF0ZSBgcGhhc2U1LWNsYXNzaWZpZXItc2hhZG93LXZhbGlkYXRpb24tdjFgIHplcm8tZGVsdGEgZnJvbSBleGFjdCBQaGFzZTQgYWNj
ZXB0ZWQgU0hBLgoKIyMgUm9idXN0bmVzcyBjb3JwdXMKQ3JlYXRlL2ZyZWV6ZSBgQU1FQ19DTEFTU0lGSUVSX1JPQlVTVE5FU1NfQ09SUFVTX1YyYC4gQWxs
b3dlZDogZXhpc3Rpbmcgc2FuaXRpemVkL2dvbGRlbiBmaXh0dXJlczsgZGFuZ2Vyb3VzIG5lZ2F0aXZlczsgVkVSSUZJRUQgU3RhZ2UxUiBldmlkZW5jZTsg
c2FuaXRpemVkIGRlcml2YXRpdmVzOyBzeW50aGV0aWMgY291bnRlcmZhY3R1YWwvYWR2ZXJzYXJpYWwgdmFyaWFudHM7IHJldmlld2VkIGNvcnJlY3Rpb24g
ZXZlbnRzIG9ubHkgZm9yIGZ1dHVyZSB2ZXJzaW9ucy4gTmV2ZXIgdXNlIHVudmVyaWZpZWQgY2xhc3NpZmllciBvdXRwdXQgYXMgZ3JvdW5kIHRydXRoLiBS
YXcgQU1FQyBjb250ZW50IHN0YXlzIG91dHNpZGUgR2l0LgoKVHJhY2sgc291cmNlIGZhbWlseSwgZm9ybWF0LCBidXNpbmVzcyBzY29wZSwgc291cmNlIHJv
bGUsIGluc3RhbnRpYXRpb24sIG1vZHVsZSwgZmFtaWx5LCBNYXN0ZXIgQ29udGVudCBjYW5kaWRhY3ksIHJldmlzaW9uL2N1cnJlbnRuZXNzLCBwcm9qZWN0
L2VudGl0eSBsaW5rLCBkdXBsaWNhdGUvdmVyc2lvbiwgc2Vuc2l0aXZpdHksIG5vaXNlLCBwYXRoIHJlbGlhYmlsaXR5LiBDb3ZlciBNMS1NNywgRklOQU5D
RSwgTUFTVEVSX0NPTlRFTlQgRk9STS9SRVBPUlQvRU5HSU5FRVJJTkdfV09SSy9ERUZJTklUSU9OLCBSRVBPUlRTLiBNYXJrIEFERVFVQVRFL1RISU4vTUlT
U0lORzsgZG8gbm90IGludmVudCBxdW90YXMuCgojIyBMZWFrYWdlLXNhZmUgc3BsaXRzCkZyZWV6ZSBDQUxJQlJBVElPTl9ERVZFTE9QTUVOVCwgVkFMSURB
VElPTiwgSE9MRE9VVF9BRFZFUlNBUklBTC4gR3JvdXAgYnkgc291cmNlIGFydGlmYWN0L3ZlcnNpb24sIGR1cGxpY2F0ZXMsIHRlbXBsYXRlIGZhbWlseSwg
cHJvamVjdC9lbnRpdHkgd2hlcmUgZmVhc2libGUuIEhvbGRvdXQgcmVtYWlucyB1bnRvdWNoZWQgZHVyaW5nIGRldmVsb3BtZW50LiBGcmVlemUgbWFuaWZl
c3QgU0hBcy4KCiMjIEh5YnJpZCBjbGFzc2lmaWVyCmBEb2N1bWVudEV2aWRlbmNlRW52ZWxvcGUg4oaSIEwwIHByaW9yLXN0YXRlL3NvdXJjZSBtb2RlIOKG
kiBMMSBoYXJkIGdhdGVzIOKGkiBMMiB0eXBlZCBydWxlcy9yZXNvbHZlcnMg4oaSIEwzIG9wdGlvbmFsIGxlYXJuZWQgbGFuZSDihpIgTDQgYm91bmRlZCBM
TE0gcmVzb2x2ZXIg4oaSIEw1IGNyb3NzLWF4aXMgY29uc2lzdGVuY3kg4oaSIG1hdGVyaWFsIHJldmlldyDihpIgQ2xhc3NpZmljYXRpb25FbnZlbG9wZSBw
cm9wb3NhbGAuCgpMTE0vbW9kZWwgYXJlIG5vdCBhdXRob3JpdHkuIEh1bWFuIHJldmlldyBpcyBub3QgZmFpbHVyZS4KCkwwIGRpc3Rpbmd1aXNoZXMgRVhJ
U1RJTkdfS05PV05fU09VUkNFLCBORVdfVU5LTk9XTl9TT1VSQ0UsIE1PRElGSUVEX0tOT1dOX1NPVVJDRSwgTU9WRV9SRU5BTUVfQ0FORElEQVRFLiBSZXVz
ZSBmcm96ZW4gYXhlcyBmb3Iga25vd24gc291cmNlczsgcmVldmFsdWF0ZSBhZmZlY3RlZCBheGVzIGZvciBtb2RpZmllZCBzb3VyY2VzOyBtb3ZlL3JlbmFt
ZSByZXVzZSBvbmx5IGFmdGVyIGlkZW50aXR5IHByb29mLgoKTDEgaGFyZCBnYXRlcyBpbmNsdWRlIG9iamVjdCBraW5kL25vaXNlLCBidXNpbmVzcyBzY29w
ZSwga25vd24gaWRlbnRpdHksIGJ1c2luZXNzL3Byb2plY3QgaWRlbnRpZmllcnMsIHRlbXBsYXRlIElEcywgZHVwbGljYXRlIGdyYXBoLCBzZW5zaXRpdml0
eS4gU2NvcGUgdmFsdWVzOiBDT1JFX0lOX1NDT1BFLCBBREpBQ0VOVF9SRUNPR05JWkVELCBPVVRfT0ZfU0NPUEUsIEFNQklHVU9VU19SRVZJRVcuIE9VVF9P
Rl9TQ09QRSBtZWFucyBubyBkZWVwZXIgY2xhc3NpZmllciwgbm8gTExNLCBubyBwcm9qZWN0aW9uLiBTRUNSRVRfRVhDTFVERSBtZWFucyBubyBMTE0vaW5k
ZXgvcHJldmlldy90cmFpbmluZy9wcm9qZWN0aW9uLgoKTDIgZGVjaXNpb25zIHJlY29yZCBydWxlX2lkLCBydWxlX3ZlcnNpb24sIGF4aXMsIGV2aWRlbmNl
X2lkcyBhbmQgY2Fubm90IG92ZXJ3cml0ZSBoaWdoZXItYXV0aG9yaXR5IGV2aWRlbmNlLgoKIyMgT3B0aW9uYWwgbGVhcm5lZCBsYW5lCk9ubHkgaWYgdmVy
aWZpZWQgbGFiZWxzIGFyZSBzdWZmaWNpZW50LiBDb21wYXJlIHJ1bGVzLW9ubHkgdnMgcnVsZXMrbGVhcm5lZCBvbiB1bnRvdWNoZWQgdmFsaWRhdGlvbi9o
b2xkb3V0LiBQcm9tb3RlIG9ubHkgd2l0aCBtZWFzdXJhYmxlIGJlbmVmaXQgYW5kIG5vIGluY3JlYXNlIGluIGNyaXRpY2FsIGZhbHNlIHByb21vdGlvbnMu
IE90aGVyd2lzZSBgTEVBUk5FRF9DTEFTU0lGSUVSX01PREU9Tk9UX1BST01PVEVEX0RBVEFfSU5TVUZGSUNJRU5UYC4KCiMjIExMTSBzZWFtCkRlZmF1bHQg
YExMTV9SRUFMX0NPTlRFTlRfTU9ERT1ESVNBQkxFRGAuIFZhbGlkYXRlIHdpdGggc3ludGhldGljL3Nhbml0aXplZCBmaXh0dXJlcy4gTExNIGNhbm5vdCBv
dmVycmlkZSBPVVRfT0ZfU0NPUEUsIGRlY2xhcmUgY2Fub25pY2FsIHNvdXJjZSwgYXV0aG9yaXplIEZpbmFuY2UvcHJvZmVzc2lvbmFsIGFwcHJvdmFsLCBj
aG9vc2UgY3VycmVudCB2ZXJzaW9uIGZyb20gcHJvc2UsIG9yIGV4ZWN1dGUgcHJvdGVjdGVkIGFjdGlvbnMuCgojIyBDb25mdXNhYmxlIHJlZ3Jlc3Npb25z
Ck1hbmRhdG9yeTogdGVjaG5pY2FsIGFydGlmYWN0IHZzIGJ1c2luZXNzIGRvYzsgYmxhbmsgdnMgZmFsc2UgcG9zaXRpdmU7IGRpcmVjdG9yeSB2cyBmaWxl
OyBiYWNrdXAgdnMgYWN0aXZlIHNvdXJjZTsgcGVyc29uYWwgSUJBTi9wYXlyb2xsIHZzIEFNRUMgRmluYW5jZTsgZXhlY3V0ZWQgZ3VhcmFudGVlIHZzIGJs
YW5rIHRlbXBsYXRlOyBwcm9mZXNzaW9uYWwgcmVnaXN0cmF0aW9uIHZzIHByb2plY3QgcGVybWl0OyBlbXBsb3llZSB2cyBwcm9qZWN0IGhhbmRvdmVyOyBT
aG9wIERyYXdpbmcgdnMgU3VibWl0dGFsOyBkcmF3aW5nIHZzIGF1dGhvcml0eSBzdWJtaXNzaW9uOyBtYXRlcmlhbCB0ZWNobmljYWwgZGF0YSB2cyBzdWJt
aXR0YWw7IGJsYW5rIHZzIGV4ZWN1dGVkIGZvcm07IHJlcG9ydCB0ZW1wbGF0ZSB2cyBvdXRwdXQ7IGhpc3RvcmljYWwgdnMgY3VycmVudDsgZHVwbGljYXRl
IHZzIHJldmlzaW9uOyBwYXRoL2ZpbGVuYW1lIGhpbnRzIHZzIHN0cm9uZ2VyIGV2aWRlbmNlOyB1bnJlc29sdmVkIGV4dGVybmFsIHByb3ZlbmFuY2UgdnMg
Y2Fub25pY2FsIEFNRUMgYXV0aG9yaXR5LiBDb250cmFkaWN0aW9u4oaSTkVFRFNfUkVWSUVXLgoKIyMgQWNjZXB0YW5jZSBwaGlsb3NvcGh5IGFuZCBmcmVl
emUKT3B0aW1pemUgZm9yIGBDUklUSUNBTF9GQUxTRV9QUk9NT1RJT05TPTBgLCBldmlkZW5jZS1iYWNrZWQgcm91dGluZywgdXNlZnVsIGNvdmVyYWdlLCBz
YWZlIGFic3RlbnRpb24sIGJvdW5kZWQgcmV2aWV3LCByZXBlYXRhYmlsaXR5LCBjcm9zcy1mb3JtYXQvY29udGV4dCByb2J1c3RuZXNzLCBsb3cgSS9PLCBy
ZXByb2R1Y2liaWxpdHkuIFJlcXVpcmUgemVybyBjcml0aWNhbCBmYWxzZSBwcm9tb3Rpb25zIG9uIGdvbGRlbiwgdmFsaWRhdGlvbiwgdW50b3VjaGVkIGhv
bGRvdXQvYWR2ZXJzYXJpYWwuCgpGcmVlemUgdGF4b25vbXkgcmV2aXNpb24sIGNsYXNzaWZpZXIgdmVyc2lvbiwgcnVsZXMgdmVyc2lvbiwgQ2xhc3NpZmll
ckVudmVsb3BlIHNjaGVtYSBTSEEsIGNhbGlicmF0aW9uL3ZhbGlkYXRpb24vaG9sZG91dCBtYW5pZmVzdHMsIGdvbGRlbi9jcm9zcy1mb3JtYXQvY3Jvc3Mt
Y29udGV4dC9hZHZlcnNhcmlhbCByZXN1bHQgU0hBcywgb3B0aW9uYWwgbGVhcm5lZC9MTE0gaWRlbnRpdGllcywgTExNIHJlYWwtY29udGVudCBtb2RlLCBE
b2N1bWVudCBJbnRlbGxpZ2VuY2UgUnVudGltZS9Eb2N1bWVudEV2aWRlbmNlRW52ZWxvcGUgaWRlbnRpdHksIE1vZHVsZSBUcnV0aCBTSEEsIFBoYXNlNCBJ
bnRlZ3JhdGlvbiBDb250cmFjdCBTSEEuCgojIyBTSEFET1cgaW50ZWdyYXRpb24KSW50ZWdyYXRlIGZyb3plbiBjbGFzc2lmaWVyIHdpdGggYWNjZXB0ZWQg
UGhhc2U0OgpgU291cmNlIGV2ZW50L0FwcCBVcGxvYWQvcmVwbGF5IOKGkiBzdGFiaWxpdHkvdmVyc2lvbiDihpIgU291cmNlIEludGFrZSDihpIgRG9jdW1l
bnRFdmlkZW5jZUVudmVsb3BlIOKGkiBmcm96ZW4gQ2xhc3NpZmllciB2MiDihpIgQ2xhc3NpZmljYXRpb25FbnZlbG9wZSDihpIgcmV2aWV3IGNvbXBhcmlz
b25gLgoKU0hBRE9XIG1lYW5zIGNsYXNzaWZpY2F0aW9uIGdlbmVyYXRlZCBhbmQgY29tcGFyaXNvbiByZWNvcmRlZCwgYnV0IE5PIGNsYXNzaWZpZXItb25s
eSBWZXJpZmllZEFzc2VydGlvbiBwcm9tb3Rpb24sIE5PIGNsYXNzaWZpZXItb25seSB0eXBlZCBwcm9qZWN0aW9uLCBOTyBTeW5vbG9neSB3cml0ZWJhY2su
IFZlcmlmaWVkQXNzZXJ0aW9uL3Byb2plY3Rpb24gbWF5IGJlIGV4ZXJjaXNlZCBvbmx5IHRocm91Z2ggZXhwbGljaXQgcmV2aWV3L3Rlc3QgYWN0aW9ucy4K
ClJldmlldyB0cmlnZ2VyczogY29udHJhZGljdGlvbnMsIEFNQklHVU9VU19SRVZJRVcsIGxvdy1jb25maWRlbmNlIG1hdGVyaWFsIG1vZHVsZS9mYW1pbHks
IHByb2plY3QtbGluayBhbWJpZ3VpdHksIE1hc3RlciBDb250ZW50IGFtYmlndWl0eSwgY2Fub25pY2FsIGNvbmZsaWN0LCBleHRlcm5hbCBjb25mbGljdCwg
cHJvdmVuYW5jZSBkZXBlbmRlbmN5LCB1bnN1cHBvcnRlZCBwYXJzZXIuIE9wdGlvbmFsIHVua25vd24gYXhpcyBhbG9uZSBuZWVkIG5vdCBmb3JjZSByZXZp
ZXcuCgpFdmVyeSBjb3JyZWN0aW9uIGlzIGltbXV0YWJsZSBDbGFzc2lmaWVyQ29ycmVjdGlvbkV2ZW50LiBJdCBjYW5ub3QgbXV0YXRlIHRoaXMgZnJvemVu
IHZlcnNpb247IGNoYW5nZXMgYmVsb25nIHRvIGEgZnV0dXJlIHZlcnNpb24uCgojIyBTaGFkb3cgZGF0YSBzb3VyY2VzIC8gYXV0aG9yaXR5Ck9mZmxpbmUv
cmVwbGF5IHNoYWRvdyBtYXkgdXNlIHZlcmlmaWVkIFN0YWdlMVIgZXZpZGVuY2UsIGdvbGRlbi92YWxpZGF0aW9uL2hvbGRvdXQgZml4dHVyZXMsIGFuZCBz
eW50aGV0aWMgYXBwIHVwbG9hZHMgd2l0aCBubyBuZXcgTkFTIHJlYWRzLgoKUmVhbCBjb250aW51b3VzIHNoYWRvdyBpcyBzZXBhcmF0ZWx5IGF1dGhvcml6
ZWQuIERlZmF1bHQ6Ci0gYFJFQUxfTElWRV9TSEFET1dfRU5BQkxFRD1mYWxzZWAKLSBgTkVXX1NNQl9DT05ORUNUSU9OUz0wYAotIGBORVdfQU1FQ19TT1VS
Q0VfUkVBRFM9MGAKLSBubyBOQVMgc2VjcmV0Ci0gbm8gd2F0Y2hlcgoKQSBmdXR1cmUgYEFNRUNfTElWRV9TSEFET1dfQUNUSVZBVElPTl9NQU5JRkVTVF92
MWAgaXMgYSBzZXBhcmF0ZSBnYXRlLgoKIyMgVmVyaWZpY2F0aW9uIHN0YXRlcwpQcm92ZSBzZXBhcmF0ZWx5OiBgVkVSSUZJRURfTE9DQUxgLCBgVkVSSUZJ
RURfUE9TVEdSRVNRTGAsIGBWRVJJRklFRF9CUk9XU0VSYC4gTmV2ZXIgaW5mZXIgYFZFUklGSUVEX0RFUExPWUVEYC4KCiMjIyBMT0NBTApGdWxsIGJhY2tl
bmQ7IGZ1bGwgZnJvbnRlbmQ7IHByb2R1Y3Rpb24gYnVpbGQ7IGdvbGRlbi92YWxpZGF0aW9uL2hvbGRvdXQ7IGNyb3NzLWZvcm1hdC9jb250ZXh0OyBwYXRo
IGNvdW50ZXJmYWN0dWFsOyB1bmtub3duLWZhbWlseSBhYnN0ZW50aW9uOyB1bnN1cHBvcnRlZC1jYXBhYmlsaXR5IHJldmlldzsgUGhhc2U0IGludGVncmF0
aW9uIHRhcmdldGVkIHN1aXRlLgoKIyMjIFBPU1RHUkVTUUwKRnJlc2ggZGlzcG9zYWJsZSBzdXBwb3J0ZWQtbWFqb3IgUG9zdGdyZVNRTDsgZnVsbCBtaWdy
YXRpb24gY2hhaW47IHNvdXJjZS1ldmVudCBpZGVtcG90ZW5jeTsgaW50YWtlIHJhY2UvbG9ja3M7IGltbXV0YWJsZSBDbGFzc2lmaWNhdGlvbkVudmVsb3Bl
OyByZXZpZXcgY29uY3VycmVuY3k7IGFwcGVuZC1vbmx5IGNvcnJlY3Rpb247IFZlcmlmaWVkQXNzZXJ0aW9uIHN1cGVyc2Vzc2lvbjsgcHJvamVjdGlvbiBp
ZGVtcG90ZW5jeTsgc2lkZS1lZmZlY3QgZGUtZHVwbGljYXRpb247IHJvbGxiYWNrLW9uLWZhaWx1cmU7IGNoZWNrcG9pbnQvcmVzdW1lIHdoZXJlIGFwcGxp
Y2FibGUuIFNRTGl0ZSBjYW5ub3Qgc3Vic3RpdHV0ZS4KCiMjIyBCUk9XU0VSClVzZSBleGlzdGluZyBQbGF5d3JpZ2h0IHJlYWwtc3RhY2sgaGFybmVzczog
cmVhbCBmcm9udGVuZOKGkmxvY2FsIGJhY2tlbmTihpJkaXNwb3NhYmxlIFBvc3RncmVTUUwuIFJlcXVpcmVkIHBhdGhzOgoxLiBORVcgc3ludGhldGljL2Fw
cC11cGxvYWTihpJpbnRha2XihpJjbGFzc2lmaWNhdGlvbuKGknJldmlld+KGkmFjY2VwdC9jb3JyZWN04oaSVmVyaWZpZWRBc3NlcnRpb27ihpJwcm9qZWN0
aW9u4oaSYXVkaXQvd29yay4KMi4gQU1CSUdVT1VT4oaScmVhc29uIHZpc2libGXihpJubyBhdXRvLXByb21vdGlvbi4KMy4gT1VUX09GX1NDT1BF4oaSbm8g
ZGVlcGVyIGNsYXNzaWZpZXIvcHJvamVjdGlvbi4KNC4gU0VDUkVUX0VYQ0xVREXihpJubyBwcmV2aWV3L21vZGVsIGNvbnRlbnQuCjUuIG1vZGlmaWVkIGtu
b3duIHNvdXJjZeKGkm5ldyB2ZXJzaW9uL2FmZmVjdGVkLWF4aXMgcmV2aWV3Lgo2LiBtb3ZlL3JlbmFtZeKGkm5vIGR1cGxpY2F0ZSBsb2dpY2FsIHJlY29y
ZC4KNy4gbWlzc2luZyBzb3VyY2XihpJJc3N1ZS9Ob3RpZmljYXRpb24vaGlzdG9yeSByZXRhaW5lZC4KOC4gY29ycmVjdGlvbuKGkm9yaWdpbmFsIGVudmVs
b3BlIHVuY2hhbmdlZCBhbmQgY29ycmVjdGlvbiBldmVudCB2aXNpYmxlLgo5LiBwcm90ZWN0ZWQgY29uc2VxdWVudGlhbCBhY3Rpb27ihpJzZXJ2ZXIgZGVu
aWFsLgoxMC4gcGVyc29uYXMgT3duZXIvQnVzaW5lc3MgRGV2ZWxvcG1lbnQvRW5naW5lZXJpbmcgc2VlIGFwcHJvcHJpYXRlIHJldmlldy93b3JrLgoKQnJv
d3NlciBxdWFsaXR5OiBubyBjb25zb2xlIGVycm9ycy91bmNhdWdodCBuZXR3b3JrIGZhaWx1cmVzIGluIGdvbGRlbiBwYXRoczsgbG9hZGluZy9lcnJvci9l
bXB0eSBzdGF0ZXM7IGtleWJvYXJkLWFjY2Vzc2libGUgYWN0aW9uczsgYmFzaWMgYXhlIHBhc3M7IGRlZXAgbGlua3MgcmVzb2x2ZTsgcm9vdC9jb3JyZWxh
dGlvbiBpbnNwZWN0YWJsZS4KCiMjIE9ic2VydmFiaWxpdHkgYW5kIGRyaWZ0CkVhY2ggY2hhaW4gcmVjb25zdHJ1Y3RzIHJvb3QgZXZlbnQsIHNvdXJjZS92
ZXJzaW9uL3Rva2VuLCBydW50aW1lL3BhcnNlciwgY2xhc3NpZmllci9ydWxlcy90YXhvbm9teS9Nb2R1bGVUcnV0aC9QaGFzZTQgaWRlbnRpdGllcywgcnVs
ZS9ldmlkZW5jZSBJRHMsIGNsYXNzaWZpY2F0aW9uLCByZXZpZXcsIG9wdGlvbmFsIHJldmlld2VkIHByb2plY3Rpb24sIGxhdGVuY3kvYnl0ZXMsIExMTSB1
c2FnZS9jb3N0LCBlcnJvcnMvcmV0cmllcy4gTm8gc2VjcmV0cy4KClRyYWNrIHVua25vd24vcmV2aWV3L2NvcnJlY3Rpb24gcmF0ZXMsIG1vZHVsZS9idXNp
bmVzcy1zY29wZS9mYW1pbHkvcHJvamVjdC9NYXN0ZXJDb250ZW50IGNvcnJlY3Rpb25zLCB1bnNlZW4gdGVybXMvZmFtaWxpZXMuIERyaWZ0IGNyZWF0ZXMg
cmV2aWV3L3ZlcnNpb24tY2FuZGlkYXRlIHdvcms7IG5ldmVyIG11dGF0ZXMgZnJvemVuIGNsYXNzaWZpZXIuCgojIyBQcm9kdWN0aW9uIGJvdW5kYXJ5IGFm
dGVyIFBoYXNlNQpFdmVuIGFmdGVyIHBhc3M6Ci0gYEFVVE9fUFJPTU9USU9OX0VOQUJMRUQ9ZmFsc2VgCi0gYFJFQUxfTElWRV9TSEFET1dfRU5BQkxFRD1m
YWxzZWAgdW5sZXNzIHNlcGFyYXRlbHkgYXV0aG9yaXplZAotIGBTWU5PTE9HWV9XUklURUJBQ0tfRU5BQkxFRD1mYWxzZWAKLSBgVkVSSUZJRURfREVQTE9Z
RUQ9ZmFsc2VgCgpBbGxvd2VkIGNsYWltIGFmdGVyIGFjdHVhbCBwYXNzOiBgUFJPRFVDVElPTl9DTEFTU0lGSUVSX0NBTkRJREFURT10cnVlYCBhbmQgYFBS
T0RVQ1RJT05fQVBQX0NMQVNTSUZJQ0FUSU9OX1JFQURZX0xPQ0FMX1BPU1RHUkVTUUxfQlJPV1NFUj10cnVlYCwgbm90IGRlcGxveWVkIHJlYWRpbmVzcy4K
CiMjIEFydGlmYWN0cyBhbmQgYWNjZXB0YW5jZQpDcmVhdGUgUGhhc2U1IGNsYXNzaWZpZXIgZnJlZXplL3J1bnRpbWUvaW5wdXQgbWFuaWZlc3RzIHBsdXMg
Y292ZXJhZ2UsIHJlZ3Jlc3Npb24sIHNoYWRvdywgbG9jYWwsIFBvc3RncmVTUUwsIGJyb3dzZXIsIGFuZCBhY2NlcHRhbmNlIHJlcG9ydHMuCgpDb2RleCBt
dXN0IHJ1biBhdCBsZWFzdCAxODAgYWN0dWFsIGFjY2VwdGFuY2UgY2hlY2tzIHdpdGggcGVyLWNoZWNrIElEL2NhdGVnb3J5L2Fzc2VydGlvbi9tZXRob2Qv
ZXZpZGVuY2UvcmVzdWx0IGNvdmVyaW5nIGVudHJ5L2FuY2VzdHJ5LCBjb3JwdXMgcHJvdmVuYW5jZSwgbm8gcmF3IGRhdGEsIGxlYWthZ2UsIG1vZHVsZSBj
b3ZlcmFnZSwgbmVnYXRpdmVzLCBzb3VyY2UtbW9kZS9oYXJkIGdhdGVzL3J1bGVzLCBvcHRpb25hbCBsZWFybmVkIGxhbmUsIExMTSBkaXNhYmxlZC1yZWFs
LWNvbnRlbnQsIGNyb3NzLWF4aXMgaW52YXJpYW50cywgY3JpdGljYWwgZmFsc2UgcHJvbW90aW9ucywgZnJlZXplIGlkZW50aXRpZXMsIHNoYWRvdyBib3Vu
ZGFyaWVzLCByZXZpZXcvY29ycmVjdGlvbnMsIFBoYXNlNCBpbnRlZ3JhdGlvbiwgTE9DQUwvUE9TVEdSRVNRTC9CUk9XU0VSLCBwZXJzb25hL1JCQUMvcHJv
dGVjdGVkIGFjdGlvbnMsIG9ic2VydmFiaWxpdHkvZHJpZnQsIG5vIE5BUy9TTUIsIG5vIGRlcGxveWVkIGNsYWltLCBkZXRlcm1pbmlzdGljIGZyZWV6ZS4K
ClRlcm1pbmFsIGlmIGFjdHVhbGx5IGdyZWVuOgotIGBQSEFTRTVfQ0FORElEQVRFX0NPTVBMRVRFPXRydWVgCi0gYENMQVNTSUZJRVJfVjJfRlJPWkVOPXRy
dWVgCi0gYFBST0RVQ1RJT05fQ0xBU1NJRklFUl9DQU5ESURBVEU9dHJ1ZWAKLSBgVkVSSUZJRURfTE9DQUw9dHJ1ZWAKLSBgVkVSSUZJRURfUE9TVEdSRVNR
TD10cnVlYAotIGBWRVJJRklFRF9CUk9XU0VSPXRydWVgCi0gYFZFUklGSUVEX0RFUExPWUVEPWZhbHNlYAotIGBBVVRPX1BST01PVElPTl9FTkFCTEVEPWZh
bHNlYAotIGBSRUFMX0xJVkVfU0hBRE9XX0VOQUJMRUQ9ZmFsc2VgCi0gYFNZTk9MT0dZX1dSSVRFQkFDS19FTkFCTEVEPWZhbHNlYAotIGBQSEFTRTVfQ09E
RVhfU0VMRl9BQ0NFUFRFRD1mYWxzZWAKLSBgUEhBU0U1X0lOREVQRU5ERU5UX0FDQ0VQVEFOQ0U9UEVORElOR2AKLSBgTkVYVD1JTkRFUEVOREVOVF9QSEFT
RTVfUkVWSUVXYAoKSWYgYW55IHN0YXRlIGZhaWxzLCByZXBvcnQgaXQgZmFsc2UgYW5kIFNUT1A7IG5ldmVyIHdlYWtlbiBnYXRlcy4KCgojIyBWYWxpZGF0
aW9uIGNsYXJpZmljYXRpb24g4oCUIGV4YWN0IGVudHJ5L2RvbWFpbi9vcGVyYXRpb25hbCBpbnZhcmlhbnRzClJlcXVpcmVkIGV4YWN0IGlucHV0IGlkZW50
aXR5IGZpZWxkczoKLSBgUEhBU0U0X0lOVEVHUkFUSU9OX0NPTlRSQUNUX1NIQTI1Nj08ZXhhY3Q+YAotIGBBTUVDX01PRFVMRV9UUlVUSF9DT05UUkFDVF9T
SEEyNTY9PGV4YWN0PmAKClJlcXVpcmVkIGRvbWFpbiBjb3ZlcmFnZSBpcyBleHBsaWNpdDoKYE0xYCwgYE0yYCwgYE0zYCwgYE00YCwgYE01YCwgYE02YCwg
YE03YCwgYEZJTkFOQ0VgLCBgTUFTVEVSX0NPTlRFTlRgLCBgUkVQT1JUU2AuCgpPcGVyYXRpb25hbCBib3VuZGFyeToKLSBgU0VDUkVUX1JFUVVJUkVEPWZh
bHNlYAotIGNsYXNzaWZpY2F0aW9uLCBldmVudCBpbnRha2UsIHJldmlldyBkZWNpc2lvbnMsIFZlcmlmaWVkQXNzZXJ0aW9uIHByb21vdGlvbiwgYW5kIHBy
b2plY3Rpb24gcmV0cmllcyBtdXN0IGJlIGlkZW1wb3RlbnQgd2hlcmUgdGhlIG9wZXJhdGlvbiBjb250cmFjdCByZXF1aXJlcyByZXRyeSBzYWZldHkuCg==
<<<END_BASE64_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_Classifier_Shadow_Validation_Master_Design.md>>>

<<<BEGIN_BASE64_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_190_Check_Design_Validation_Report.md::SHA256=61e57216ca5b8671df7337420bb7d116c94be138da62cde851dcab6236ecbe0f::BYTE_COUNT=16845>>>
IyBQcm9wb3NhbE9wcyBQaGFzZTUgMTkwIENoZWNrIERlc2lnbiBWYWxpZGF0aW9uCgpgYGB0ZXh0ClJFU1VMVD1QQVNTCkNIRUNLU19UT1RBTD0xOTAKQ0hF
Q0tTX1BBU1M9MTkwCkNIRUNLU19GQUlMPTAKVkFMSURBVEVEX0RFU0lHTl9TSEEyNTY9NzYxZGQ0ZTY0MmNlOGRjMzA1ODliYWIzOTM4MDhlOTY1YTRmOTMx
ZTllMmE5ZGRkYTk0Y2ZmNmYyMTdmYTgxYgpgYGAKCj4gUHJlLWV4ZWN1dGlvbiBkZXNpZ24gdmFsaWRhdGlvbiBvbmx5LiBUaGlzIGRvZXMgbm90IGNsYWlt
IGltcGxlbWVudGF0aW9uIG9yIHJ1bnRpbWUgdmVyaWZpY2F0aW9uLiBUaGUgZmluYWwgcmVwb3J0IHJlZmxlY3RzIHRoZSBzdXJnaWNhbGx5IGNvcnJlY3Rl
ZCBkZXNpZ24gYnl0ZXMgYWZ0ZXIgdGhlIGZpcnN0IHZhbGlkYXRpb24gZXhwb3NlZCBtaXNzaW5nIGV4cGxpY2l0IGludmFyaWFudHMuCgp8ICMgfCBDYXRl
Z29yeSB8IFJlc3VsdCB8IEFzc2VydGlvbiB8IEV2aWRlbmNlIHwKfC0tLTp8LS0tfDotLS06fC0tLXwtLS18CnwgMSB8IGVudHJ5IHwgKipQQVNTKiogfCBS
ZXF1aXJlcyBQaGFzZTQgaW5kZXBlbmRlbnQgYWNjZXB0YW5jZSB8IGBQSEFTRTRfSU5ERVBFTkRFTlRfQUNDRVBUQU5DRT1QQVNTYCB8CnwgMiB8IGVudHJ5
IHwgKipQQVNTKiogfCBSZXF1aXJlcyBQaGFzZTQgZXhhY3QgU0hBIHwgYFBIQVNFNF9BQ0NFUFRFRF9TSEFgIHwKfCAzIHwgZW50cnkgfCAqKlBBU1MqKiB8
IFJlcXVpcmVzIFBoYXNlNCBjb250cmFjdCB8IGBQSEFTRTRfSU5URUdSQVRJT05fQ09OVFJBQ1RfU0hBMjU2YCB8CnwgNCB8IGVudHJ5IHwgKipQQVNTKiog
fCBSZXF1aXJlcyBNb2R1bGUgVHJ1dGggfCBgQU1FQ19NT0RVTEVfVFJVVEhfQ09OVFJBQ1RfU0hBMjU2YCB8CnwgNSB8IGNvcnB1cyB8ICoqUEFTUyoqIHwg
Um9idXN0bmVzcyBjb3JwdXMgfCBgQU1FQ19DTEFTU0lGSUVSX1JPQlVTVE5FU1NfQ09SUFVTX1YyYCB8CnwgNiB8IGNvcnB1cyB8ICoqUEFTUyoqIHwgQ2Fs
aWJyYXRpb24gc3BsaXQgfCBgQ0FMSUJSQVRJT05fREVWRUxPUE1FTlRgIHwKfCA3IHwgY29ycHVzIHwgKipQQVNTKiogfCBWYWxpZGF0aW9uIHNwbGl0IHwg
YFZBTElEQVRJT05gIHwKfCA4IHwgY29ycHVzIHwgKipQQVNTKiogfCBIb2xkb3V0IHNwbGl0IHwgYEhPTERPVVRfQURWRVJTQVJJQUxgIHwKfCA5IHwgY292
ZXJhZ2UgfCAqKlBBU1MqKiB8IE0xIHwgYE0xYCB8CnwgMTAgfCBjb3ZlcmFnZSB8ICoqUEFTUyoqIHwgTTIgfCBgTTJgIHwKfCAxMSB8IGNvdmVyYWdlIHwg
KipQQVNTKiogfCBNMyB8IGBNM2AgfAp8IDEyIHwgY292ZXJhZ2UgfCAqKlBBU1MqKiB8IE00IHwgYE00YCB8CnwgMTMgfCBjb3ZlcmFnZSB8ICoqUEFTUyoq
IHwgTTUgfCBgTTVgIHwKfCAxNCB8IGNvdmVyYWdlIHwgKipQQVNTKiogfCBNNiB8IGBNNmAgfAp8IDE1IHwgY292ZXJhZ2UgfCAqKlBBU1MqKiB8IE03IHwg
YE03YCB8CnwgMTYgfCBjb3ZlcmFnZSB8ICoqUEFTUyoqIHwgRmluYW5jZSB8IGBGSU5BTkNFYCB8CnwgMTcgfCBjb3ZlcmFnZSB8ICoqUEFTUyoqIHwgTWFz
dGVyQ29udGVudCB8IGBNQVNURVJfQ09OVEVOVGAgfAp8IDE4IHwgY292ZXJhZ2UgfCAqKlBBU1MqKiB8IFJlcG9ydHMgfCBgUkVQT1JUU2AgfAp8IDE5IHwg
Y292ZXJhZ2UgfCAqKlBBU1MqKiB8IEFERVFVQVRFIHwgYEFERVFVQVRFYCB8CnwgMjAgfCBjb3ZlcmFnZSB8ICoqUEFTUyoqIHwgVEhJTiB8IGBUSElOYCB8
CnwgMjEgfCBjb3ZlcmFnZSB8ICoqUEFTUyoqIHwgTUlTU0lORyB8IGBNSVNTSU5HYCB8CnwgMjIgfCBjbGFzc2lmaWVyIHwgKipQQVNTKiogfCBMMCB8IGBM
MCBwcmlvci1zdGF0ZS9zb3VyY2UgbW9kZWAgfAp8IDIzIHwgY2xhc3NpZmllciB8ICoqUEFTUyoqIHwgTDEgfCBgTDEgaGFyZCBnYXRlc2AgfAp8IDI0IHwg
Y2xhc3NpZmllciB8ICoqUEFTUyoqIHwgTDIgfCBgTDIgdHlwZWQgcnVsZXMvcmVzb2x2ZXJzYCB8CnwgMjUgfCBjbGFzc2lmaWVyIHwgKipQQVNTKiogfCBM
MyB8IGBMMyBvcHRpb25hbCBsZWFybmVkIGxhbmVgIHwKfCAyNiB8IGNsYXNzaWZpZXIgfCAqKlBBU1MqKiB8IEw0IHwgYEw0IGJvdW5kZWQgTExNIHJlc29s
dmVyYCB8CnwgMjcgfCBjbGFzc2lmaWVyIHwgKipQQVNTKiogfCBMNSB8IGBMNSBjcm9zcy1heGlzIGNvbnNpc3RlbmN5YCB8CnwgMjggfCBzb3VyY2UtbW9k
ZSB8ICoqUEFTUyoqIHwgRXhpc3Rpbmcga25vd24gfCBgRVhJU1RJTkdfS05PV05fU09VUkNFYCB8CnwgMjkgfCBzb3VyY2UtbW9kZSB8ICoqUEFTUyoqIHwg
TmV3IHVua25vd24gfCBgTkVXX1VOS05PV05fU09VUkNFYCB8CnwgMzAgfCBzb3VyY2UtbW9kZSB8ICoqUEFTUyoqIHwgTW9kaWZpZWQga25vd24gfCBgTU9E
SUZJRURfS05PV05fU09VUkNFYCB8CnwgMzEgfCBzb3VyY2UtbW9kZSB8ICoqUEFTUyoqIHwgTW92ZSByZW5hbWUgfCBgTU9WRV9SRU5BTUVfQ0FORElEQVRF
YCB8CnwgMzIgfCBzY29wZSB8ICoqUEFTUyoqIHwgQ29yZSB8IGBDT1JFX0lOX1NDT1BFYCB8CnwgMzMgfCBzY29wZSB8ICoqUEFTUyoqIHwgQWRqYWNlbnQg
fCBgQURKQUNFTlRfUkVDT0dOSVpFRGAgfAp8IDM0IHwgc2NvcGUgfCAqKlBBU1MqKiB8IE91dCB8IGBPVVRfT0ZfU0NPUEVgIHwKfCAzNSB8IHNjb3BlIHwg
KipQQVNTKiogfCBBbWJpZ3VvdXMgfCBgQU1CSUdVT1VTX1JFVklFV2AgfAp8IDM2IHwgc2VjdXJpdHkgfCAqKlBBU1MqKiB8IFNlY3JldCBleGNsdWRlIHwg
YFNFQ1JFVF9FWENMVURFYCB8CnwgMzcgfCBzZWN1cml0eSB8ICoqUEFTUyoqIHwgUmVhbCBjb250ZW50IExMTSBkaXNhYmxlZCB8IGBMTE1fUkVBTF9DT05U
RU5UX01PREU9RElTQUJMRURgIHwKfCAzOCB8IHF1YWxpdHkgfCAqKlBBU1MqKiB8IENyaXRpY2FsIGZhbHNlIHByb21vdGlvbnMgemVybyB8IGBDUklUSUNB
TF9GQUxTRV9QUk9NT1RJT05TPTBgIHwKfCAzOSB8IHF1YWxpdHkgfCAqKlBBU1MqKiB8IFNhZmUgYWJzdGVudGlvbiB8IGBzYWZlIGFic3RlbnRpb25gIHwK
fCA0MCB8IHF1YWxpdHkgfCAqKlBBU1MqKiB8IENyb3NzLWZvcm1hdCB8IGBjcm9zcy1mb3JtYXRgIHwKfCA0MSB8IHF1YWxpdHkgfCAqKlBBU1MqKiB8IENy
b3NzLWNvbnRleHQgfCBgY3Jvc3MtY29udGV4dGAgfAp8IDQyIHwgbmVnYXRpdmUgfCAqKlBBU1MqKiB8IFBlcnNvbmFsIGZpbmFuY2UgY29uZnVzaW9uIHwg
YHBlcnNvbmFsIElCQU4vcGF5cm9sbCB2cyBBTUVDIEZpbmFuY2VgIHwKfCA0MyB8IG5lZ2F0aXZlIHwgKipQQVNTKiogfCBHdWFyYW50ZWUgY29uZnVzaW9u
IHwgYGV4ZWN1dGVkIGd1YXJhbnRlZSB2cyBibGFuayB0ZW1wbGF0ZWAgfAp8IDQ0IHwgbmVnYXRpdmUgfCAqKlBBU1MqKiB8IFBlcm1pdCByZWdpc3RyYXRp
b24gY29uZnVzaW9uIHwgYHByb2Zlc3Npb25hbCByZWdpc3RyYXRpb24gdnMgcHJvamVjdCBwZXJtaXRgIHwKfCA0NSB8IG5lZ2F0aXZlIHwgKipQQVNTKiog
fCBIYW5kb3ZlciBjb25mdXNpb24gfCBgZW1wbG95ZWUgdnMgcHJvamVjdCBoYW5kb3ZlcmAgfAp8IDQ2IHwgbmVnYXRpdmUgfCAqKlBBU1MqKiB8IFNob3Ag
ZHJhd2luZyBjb25mdXNpb24gfCBgU2hvcCBEcmF3aW5nIHZzIFN1Ym1pdHRhbGAgfAp8IDQ3IHwgbmVnYXRpdmUgfCAqKlBBU1MqKiB8IE1hdGVyaWFsIGNv
bmZ1c2lvbiB8IGBtYXRlcmlhbCB0ZWNobmljYWwgZGF0YSB2cyBzdWJtaXR0YWxgIHwKfCA0OCB8IG5lZ2F0aXZlIHwgKipQQVNTKiogfCBCbGFuay9leGVj
dXRlZCBmb3JtIHwgYGJsYW5rIHZzIGV4ZWN1dGVkIGZvcm1gIHwKfCA0OSB8IG5lZ2F0aXZlIHwgKipQQVNTKiogfCBSZXBvcnQgdGVtcGxhdGUvb3V0cHV0
IHwgYHJlcG9ydCB0ZW1wbGF0ZSB2cyBvdXRwdXRgIHwKfCA1MCB8IG5lZ2F0aXZlIHwgKipQQVNTKiogfCBEdXBsaWNhdGUvcmV2aXNpb24gfCBgZHVwbGlj
YXRlIHZzIHJldmlzaW9uYCB8CnwgNTEgfCBmcmVlemUgfCAqKlBBU1MqKiB8IFRheG9ub215IHJldmlzaW9uIHwgYHRheG9ub215IHJldmlzaW9uYCB8Cnwg
NTIgfCBmcmVlemUgfCAqKlBBU1MqKiB8IENsYXNzaWZpZXIgdmVyc2lvbiB8IGBjbGFzc2lmaWVyIHZlcnNpb25gIHwKfCA1MyB8IGZyZWV6ZSB8ICoqUEFT
UyoqIHwgUnVsZXMgdmVyc2lvbiB8IGBydWxlcyB2ZXJzaW9uYCB8CnwgNTQgfCBmcmVlemUgfCAqKlBBU1MqKiB8IFNjaGVtYSBTSEEgfCBgQ2xhc3NpZmll
ckVudmVsb3BlIHNjaGVtYSBTSEFgIHwKfCA1NSB8IGZyZWV6ZSB8ICoqUEFTUyoqIHwgR29sZGVuIHJlc3VsdCB8IGBnb2xkZW5gIHwKfCA1NiB8IHNoYWRv
dyB8ICoqUEFTUyoqIHwgU2hhZG93IGludGVncmF0aW9uIHwgYFNIQURPV2AgfAp8IDU3IHwgc2hhZG93IHwgKipQQVNTKiogfCBObyBjbGFzc2lmaWVyLW9u
bHkgYXNzZXJ0aW9uIHwgYE5PIGNsYXNzaWZpZXItb25seSBWZXJpZmllZEFzc2VydGlvbiBwcm9tb3Rpb25gIHwKfCA1OCB8IHNoYWRvdyB8ICoqUEFTUyoq
IHwgTm8gd3JpdGViYWNrIHwgYE5PIFN5bm9sb2d5IHdyaXRlYmFja2AgfAp8IDU5IHwgcmV2aWV3IHwgKipQQVNTKiogfCBSZXZpZXcgY29udHJhZGljdGlv
biB8IGBjb250cmFkaWN0aW9uc2AgfAp8IDYwIHwgcmV2aWV3IHwgKipQQVNTKiogfCBDb3JyZWN0aW9uIGltbXV0YWJsZSB8IGBDbGFzc2lmaWVyQ29ycmVj
dGlvbkV2ZW50YCB8CnwgNjEgfCBhdXRob3JpdHkgfCAqKlBBU1MqKiB8IFJlYWwgbGl2ZSBzaGFkb3cgZmFsc2UgfCBgUkVBTF9MSVZFX1NIQURPV19FTkFC
TEVEPWZhbHNlYCB8CnwgNjIgfCB2ZXJpZmljYXRpb24gfCAqKlBBU1MqKiB8IExvY2FsIHNlcGFyYXRlIHwgYFZFUklGSUVEX0xPQ0FMYCB8CnwgNjMgfCB2
ZXJpZmljYXRpb24gfCAqKlBBU1MqKiB8IFBvc3RncmVzIHNlcGFyYXRlIHwgYFZFUklGSUVEX1BPU1RHUkVTUUxgIHwKfCA2NCB8IHZlcmlmaWNhdGlvbiB8
ICoqUEFTUyoqIHwgQnJvd3NlciBzZXBhcmF0ZSB8IGBWRVJJRklFRF9CUk9XU0VSYCB8CnwgNjUgfCB2ZXJpZmljYXRpb24gfCAqKlBBU1MqKiB8IERlcGxv
eWVkIGZhbHNlIHwgYFZFUklGSUVEX0RFUExPWUVEPWZhbHNlYCB8CnwgNjYgfCBwb3N0Z3JlcyB8ICoqUEFTUyoqIHwgRXZlbnQgaWRlbXBvdGVuY3kgfCBg
c291cmNlLWV2ZW50IGlkZW1wb3RlbmN5YCB8CnwgNjcgfCBwb3N0Z3JlcyB8ICoqUEFTUyoqIHwgUm93IGxvY2tzIHwgYGxvY2tzYCB8CnwgNjggfCBwb3N0
Z3JlcyB8ICoqUEFTUyoqIHwgRW52ZWxvcGUgaW1tdXRhYmlsaXR5IHwgYGltbXV0YWJsZSBDbGFzc2lmaWNhdGlvbkVudmVsb3BlYCB8CnwgNjkgfCBwb3N0
Z3JlcyB8ICoqUEFTUyoqIHwgUmV2aWV3IGNvbmN1cnJlbmN5IHwgYHJldmlldyBjb25jdXJyZW5jeWAgfAp8IDcwIHwgcG9zdGdyZXMgfCAqKlBBU1MqKiB8
IENvcnJlY3Rpb24gYXBwZW5kLW9ubHkgfCBgYXBwZW5kLW9ubHkgY29ycmVjdGlvbmAgfAp8IDcxIHwgcG9zdGdyZXMgfCAqKlBBU1MqKiB8IEFzc2VydGlv
biBzdXBlcnNlc3Npb24gfCBgVmVyaWZpZWRBc3NlcnRpb24gc3VwZXJzZXNzaW9uYCB8CnwgNzIgfCBwb3N0Z3JlcyB8ICoqUEFTUyoqIHwgUHJvamVjdGlv
biBpZGVtcG90ZW5jeSB8IGBwcm9qZWN0aW9uIGlkZW1wb3RlbmN5YCB8CnwgNzMgfCBicm93c2VyIHwgKipQQVNTKiogfCBOZXcgcGF0aCB8IGBORVcgc3lu
dGhldGljL2FwcC11cGxvYWRgIHwKfCA3NCB8IGJyb3dzZXIgfCAqKlBBU1MqKiB8IEFtYmlndW91cyBwYXRoIHwgYEFNQklHVU9VU2AgfAp8IDc1IHwgYnJv
d3NlciB8ICoqUEFTUyoqIHwgT3V0LW9mLXNjb3BlIHBhdGggfCBgT1VUX09GX1NDT1BFYCB8CnwgNzYgfCBicm93c2VyIHwgKipQQVNTKiogfCBTZWNyZXQg
cGF0aCB8IGBTRUNSRVRfRVhDTFVERWAgfAp8IDc3IHwgYnJvd3NlciB8ICoqUEFTUyoqIHwgTW9kaWZpZWQgcGF0aCB8IGBtb2RpZmllZCBrbm93biBzb3Vy
Y2VgIHwKfCA3OCB8IGJyb3dzZXIgfCAqKlBBU1MqKiB8IE1vdmUgcGF0aCB8IGBtb3ZlL3JlbmFtZWAgfAp8IDc5IHwgYnJvd3NlciB8ICoqUEFTUyoqIHwg
TWlzc2luZyBwYXRoIHwgYG1pc3Npbmcgc291cmNlYCB8CnwgODAgfCBicm93c2VyIHwgKipQQVNTKiogfCBDb3JyZWN0aW9uIHBhdGggfCBgb3JpZ2luYWwg
ZW52ZWxvcGUgdW5jaGFuZ2VkYCB8CnwgODEgfCBicm93c2VyIHwgKipQQVNTKiogfCBQcm90ZWN0ZWQgYWN0aW9uIHBhdGggfCBgcHJvdGVjdGVkIGNvbnNl
cXVlbnRpYWwgYWN0aW9uYCB8CnwgODIgfCBicm93c2VyIHwgKipQQVNTKiogfCBQZXJzb25hIHBhdGggfCBgT3duZXIvQnVzaW5lc3MgRGV2ZWxvcG1lbnQv
RW5naW5lZXJpbmdgIHwKfCA4MyB8IGJyb3dzZXItcXVhbGl0eSB8ICoqUEFTUyoqIHwgQ29uc29sZSBlcnJvcnMgfCBgbm8gY29uc29sZSBlcnJvcnNgIHwK
fCA4NCB8IGJyb3dzZXItcXVhbGl0eSB8ICoqUEFTUyoqIHwgS2V5Ym9hcmQgYWNjZXNzaWJpbGl0eSB8IGBrZXlib2FyZC1hY2Nlc3NpYmxlYCB8CnwgODUg
fCBicm93c2VyLXF1YWxpdHkgfCAqKlBBU1MqKiB8IEF4ZSB8IGBheGVgIHwKfCA4NiB8IG9ic2VydmFiaWxpdHkgfCAqKlBBU1MqKiB8IFJvb3QgZXZlbnQg
fCBgcm9vdCBldmVudGAgfAp8IDg3IHwgb2JzZXJ2YWJpbGl0eSB8ICoqUEFTUyoqIHwgQ2xhc3NpZmllciBpZGVudGl0eSB8IGBjbGFzc2lmaWVyL3J1bGVz
L3RheG9ub215YCB8CnwgODggfCBvYnNlcnZhYmlsaXR5IHwgKipQQVNTKiogfCBFdmlkZW5jZSBJRHMgfCBgcnVsZS9ldmlkZW5jZSBJRHNgIHwKfCA4OSB8
IGRyaWZ0IHwgKipQQVNTKiogfCBVbmtub3duIHJhdGUgfCBgdW5rbm93bmAgfAp8IDkwIHwgZHJpZnQgfCAqKlBBU1MqKiB8IENvcnJlY3Rpb24gcmF0ZSB8
IGBjb3JyZWN0aW9uYCB8CnwgOTEgfCBib3VuZGFyeSB8ICoqUEFTUyoqIHwgTm8gU01CIHwgYE5FV19TTUJfQ09OTkVDVElPTlM9MGAgfAp8IDkyIHwgYm91
bmRhcnkgfCAqKlBBU1MqKiB8IE5vIHJlYWRzIHwgYE5FV19BTUVDX1NPVVJDRV9SRUFEUz0wYCB8CnwgOTMgfCBib3VuZGFyeSB8ICoqUEFTUyoqIHwgTm8g
YXV0byBwcm9tb3Rpb24gfCBgQVVUT19QUk9NT1RJT05fRU5BQkxFRD1mYWxzZWAgfAp8IDk0IHwgYm91bmRhcnkgfCAqKlBBU1MqKiB8IE5vIHdyaXRlYmFj
ayB8IGBTWU5PTE9HWV9XUklURUJBQ0tfRU5BQkxFRD1mYWxzZWAgfAp8IDk1IHwgY2xhaW0gfCAqKlBBU1MqKiB8IENsYXNzaWZpZXIgY2FuZGlkYXRlIHwg
YFBST0RVQ1RJT05fQ0xBU1NJRklFUl9DQU5ESURBVEU9dHJ1ZWAgfAp8IDk2IHwgY2xhaW0gfCAqKlBBU1MqKiB8IExvY2FsL1BHL2Jyb3dzZXIgcmVhZGlu
ZXNzIHwgYFBST0RVQ1RJT05fQVBQX0NMQVNTSUZJQ0FUSU9OX1JFQURZX0xPQ0FMX1BPU1RHUkVTUUxfQlJPV1NFUj10cnVlYCB8CnwgOTcgfCB0ZXJtaW5h
bCB8ICoqUEFTUyoqIHwgQ2FuZGlkYXRlIGNvbXBsZXRlIHwgYFBIQVNFNV9DQU5ESURBVEVfQ09NUExFVEU9dHJ1ZWAgfAp8IDk4IHwgdGVybWluYWwgfCAq
KlBBU1MqKiB8IEZyb3plbiB0cnVlIHwgYENMQVNTSUZJRVJfVjJfRlJPWkVOPXRydWVgIHwKfCA5OSB8IHRlcm1pbmFsIHwgKipQQVNTKiogfCBObyBzZWxm
IGFjY2VwdCB8IGBQSEFTRTVfQ09ERVhfU0VMRl9BQ0NFUFRFRD1mYWxzZWAgfAp8IDEwMCB8IHRlcm1pbmFsIHwgKipQQVNTKiogfCBJbmRlcGVuZGVudCBw
ZW5kaW5nIHwgYFBIQVNFNV9JTkRFUEVOREVOVF9BQ0NFUFRBTkNFPVBFTkRJTkdgIHwKfCAxMDEgfCBhdXRob3JpdHkgfCAqKlBBU1MqKiB8IENsYXNzaWZp
ZXIgb3V0cHV0IHJlbWFpbnMgcHJvcG9zYWwg4oCUIGNvbnNpc3RlbmN5IGxlbnMgMSB8IGBDbGFzc2lmaWNhdGlvbkVudmVsb3BlYCB8CnwgMTAyIHwgYXV0
aG9yaXR5IHwgKipQQVNTKiogfCBWZXJpZmllZCB0cnV0aCBib3VuZGFyeSBleHBsaWNpdCDigJQgY29uc2lzdGVuY3kgbGVucyAxIHwgYFZlcmlmaWVkQXNz
ZXJ0aW9uYCB8CnwgMTAzIHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBQcm9qZWN0aW9uIGJvdW5kYXJ5IGV4cGxpY2l0IOKAlCBjb25zaXN0ZW5jeSBsZW5z
IDEgfCBgdHlwZWQgcHJvamVjdGlvbmAgfAp8IDEwNCB8IGF1dGhvcml0eSB8ICoqUEFTUyoqIHwgTm8gYXV0by1wcm9tb3Rpb24g4oCUIGNvbnNpc3RlbmN5
IGxlbnMgMSB8IGBBVVRPX1BST01PVElPTl9FTkFCTEVEPWZhbHNlYCB8CnwgMTA1IHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBEZXBsb3llZCBzdGF0ZSBr
ZXB0IHNlcGFyYXRlIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDEgfCBgVkVSSUZJRURfREVQTE9ZRUQ9ZmFsc2VgIHwKfCAxMDYgfCBzb3VyY2UgfCAqKlBBU1Mq
KiB8IE5vIG5ldyBTTUIgcGF0aCDigJQgY29uc2lzdGVuY3kgbGVucyAxIHwgYE5FV19TTUJfQ09OTkVDVElPTlM9MGAgfAp8IDEwNyB8IHNvdXJjZSB8ICoq
UEFTUyoqIHwgTm8gbmV3IEFNRUMgc291cmNlIHJlYWRzIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDEgfCBgTkVXX0FNRUNfU09VUkNFX1JFQURTPTBgIHwKfCAx
MDggfCBzb3VyY2UgfCAqKlBBU1MqKiB8IE5vIHNlY3JldCByZXF1aXJlZCDigJQgY29uc2lzdGVuY3kgbGVucyAxIHwgYFNFQ1JFVF9SRVFVSVJFRD1mYWxz
ZWAgfAp8IDEwOSB8IHNlY3VyaXR5IHwgKipQQVNTKiogfCBTZWNyZXQgZXhjbHVzaW9uIGV4aXN0cyDigJQgY29uc2lzdGVuY3kgbGVucyAxIHwgYFNFQ1JF
VF9FWENMVURFYCB8CnwgMTEwIHwgZ292ZXJuYW5jZSB8ICoqUEFTUyoqIHwgSW5kZXBlbmRlbnQgcmV2aWV3IHJlcXVpcmVkIOKAlCBjb25zaXN0ZW5jeSBs
ZW5zIDEgfCBgSU5ERVBFTkRFTlRfQUNDRVBUQU5DRT1QRU5ESU5HYCB8CnwgMTExIHwgcXVhbGl0eSB8ICoqUEFTUyoqIHwgSWRlbXBvdGVuY3kgcmVxdWly
ZWQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgMSB8IGBpZGVtcG90ZW50YCB8CnwgMTEyIHwgcXVhbGl0eSB8ICoqUEFTUyoqIHwgQXVkaXRhYmlsaXR5IHJlcXVp
cmVkIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDEgfCBgYXVkaXRgIHwKfCAxMTMgfCBxdWFsaXR5IHwgKipQQVNTKiogfCBQcm90ZWN0ZWQgYWN0aW9ucyBwcmVz
ZXJ2ZWQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgMSB8IGBwcm90ZWN0ZWRgIHwKfCAxMTQgfCB0ZXN0aW5nIHwgKipQQVNTKiogfCBQb3N0Z3JlU1FMIHByb29m
IHByZXNlbnQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgMSB8IGBQb3N0Z3JlU1FMYCB8CnwgMTE1IHwgdGVzdGluZyB8ICoqUEFTUyoqIHwgRnJvbnRlbmQvYnJv
d3NlciBib3VuZGFyeSBwcmVzZW50IOKAlCBjb25zaXN0ZW5jeSBsZW5zIDEgfCBgZnJvbnRlbmRgIHwKfCAxMTYgfCBhdXRob3JpdHkgfCAqKlBBU1MqKiB8
IENsYXNzaWZpZXIgb3V0cHV0IHJlbWFpbnMgcHJvcG9zYWwg4oCUIGNvbnNpc3RlbmN5IGxlbnMgMiB8IGBDbGFzc2lmaWNhdGlvbkVudmVsb3BlYCB8Cnwg
MTE3IHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBWZXJpZmllZCB0cnV0aCBib3VuZGFyeSBleHBsaWNpdCDigJQgY29uc2lzdGVuY3kgbGVucyAyIHwgYFZl
cmlmaWVkQXNzZXJ0aW9uYCB8CnwgMTE4IHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBQcm9qZWN0aW9uIGJvdW5kYXJ5IGV4cGxpY2l0IOKAlCBjb25zaXN0
ZW5jeSBsZW5zIDIgfCBgdHlwZWQgcHJvamVjdGlvbmAgfAp8IDExOSB8IGF1dGhvcml0eSB8ICoqUEFTUyoqIHwgTm8gYXV0by1wcm9tb3Rpb24g4oCUIGNv
bnNpc3RlbmN5IGxlbnMgMiB8IGBBVVRPX1BST01PVElPTl9FTkFCTEVEPWZhbHNlYCB8CnwgMTIwIHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBEZXBsb3ll
ZCBzdGF0ZSBrZXB0IHNlcGFyYXRlIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDIgfCBgVkVSSUZJRURfREVQTE9ZRUQ9ZmFsc2VgIHwKfCAxMjEgfCBzb3VyY2Ug
fCAqKlBBU1MqKiB8IE5vIG5ldyBTTUIgcGF0aCDigJQgY29uc2lzdGVuY3kgbGVucyAyIHwgYE5FV19TTUJfQ09OTkVDVElPTlM9MGAgfAp8IDEyMiB8IHNv
dXJjZSB8ICoqUEFTUyoqIHwgTm8gbmV3IEFNRUMgc291cmNlIHJlYWRzIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDIgfCBgTkVXX0FNRUNfU09VUkNFX1JFQURT
PTBgIHwKfCAxMjMgfCBzb3VyY2UgfCAqKlBBU1MqKiB8IE5vIHNlY3JldCByZXF1aXJlZCDigJQgY29uc2lzdGVuY3kgbGVucyAyIHwgYFNFQ1JFVF9SRVFV
SVJFRD1mYWxzZWAgfAp8IDEyNCB8IHNlY3VyaXR5IHwgKipQQVNTKiogfCBTZWNyZXQgZXhjbHVzaW9uIGV4aXN0cyDigJQgY29uc2lzdGVuY3kgbGVucyAy
IHwgYFNFQ1JFVF9FWENMVURFYCB8CnwgMTI1IHwgZ292ZXJuYW5jZSB8ICoqUEFTUyoqIHwgSW5kZXBlbmRlbnQgcmV2aWV3IHJlcXVpcmVkIOKAlCBjb25z
aXN0ZW5jeSBsZW5zIDIgfCBgSU5ERVBFTkRFTlRfQUNDRVBUQU5DRT1QRU5ESU5HYCB8CnwgMTI2IHwgcXVhbGl0eSB8ICoqUEFTUyoqIHwgSWRlbXBvdGVu
Y3kgcmVxdWlyZWQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgMiB8IGBpZGVtcG90ZW50YCB8CnwgMTI3IHwgcXVhbGl0eSB8ICoqUEFTUyoqIHwgQXVkaXRhYmls
aXR5IHJlcXVpcmVkIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDIgfCBgYXVkaXRgIHwKfCAxMjggfCBxdWFsaXR5IHwgKipQQVNTKiogfCBQcm90ZWN0ZWQgYWN0
aW9ucyBwcmVzZXJ2ZWQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgMiB8IGBwcm90ZWN0ZWRgIHwKfCAxMjkgfCB0ZXN0aW5nIHwgKipQQVNTKiogfCBQb3N0Z3Jl
U1FMIHByb29mIHByZXNlbnQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgMiB8IGBQb3N0Z3JlU1FMYCB8CnwgMTMwIHwgdGVzdGluZyB8ICoqUEFTUyoqIHwgRnJv
bnRlbmQvYnJvd3NlciBib3VuZGFyeSBwcmVzZW50IOKAlCBjb25zaXN0ZW5jeSBsZW5zIDIgfCBgZnJvbnRlbmRgIHwKfCAxMzEgfCBhdXRob3JpdHkgfCAq
KlBBU1MqKiB8IENsYXNzaWZpZXIgb3V0cHV0IHJlbWFpbnMgcHJvcG9zYWwg4oCUIGNvbnNpc3RlbmN5IGxlbnMgMyB8IGBDbGFzc2lmaWNhdGlvbkVudmVs
b3BlYCB8CnwgMTMyIHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBWZXJpZmllZCB0cnV0aCBib3VuZGFyeSBleHBsaWNpdCDigJQgY29uc2lzdGVuY3kgbGVu
cyAzIHwgYFZlcmlmaWVkQXNzZXJ0aW9uYCB8CnwgMTMzIHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBQcm9qZWN0aW9uIGJvdW5kYXJ5IGV4cGxpY2l0IOKA
lCBjb25zaXN0ZW5jeSBsZW5zIDMgfCBgdHlwZWQgcHJvamVjdGlvbmAgfAp8IDEzNCB8IGF1dGhvcml0eSB8ICoqUEFTUyoqIHwgTm8gYXV0by1wcm9tb3Rp
b24g4oCUIGNvbnNpc3RlbmN5IGxlbnMgMyB8IGBBVVRPX1BST01PVElPTl9FTkFCTEVEPWZhbHNlYCB8CnwgMTM1IHwgYXV0aG9yaXR5IHwgKipQQVNTKiog
fCBEZXBsb3llZCBzdGF0ZSBrZXB0IHNlcGFyYXRlIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDMgfCBgVkVSSUZJRURfREVQTE9ZRUQ9ZmFsc2VgIHwKfCAxMzYg
fCBzb3VyY2UgfCAqKlBBU1MqKiB8IE5vIG5ldyBTTUIgcGF0aCDigJQgY29uc2lzdGVuY3kgbGVucyAzIHwgYE5FV19TTUJfQ09OTkVDVElPTlM9MGAgfAp8
IDEzNyB8IHNvdXJjZSB8ICoqUEFTUyoqIHwgTm8gbmV3IEFNRUMgc291cmNlIHJlYWRzIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDMgfCBgTkVXX0FNRUNfU09V
UkNFX1JFQURTPTBgIHwKfCAxMzggfCBzb3VyY2UgfCAqKlBBU1MqKiB8IE5vIHNlY3JldCByZXF1aXJlZCDigJQgY29uc2lzdGVuY3kgbGVucyAzIHwgYFNF
Q1JFVF9SRVFVSVJFRD1mYWxzZWAgfAp8IDEzOSB8IHNlY3VyaXR5IHwgKipQQVNTKiogfCBTZWNyZXQgZXhjbHVzaW9uIGV4aXN0cyDigJQgY29uc2lzdGVu
Y3kgbGVucyAzIHwgYFNFQ1JFVF9FWENMVURFYCB8CnwgMTQwIHwgZ292ZXJuYW5jZSB8ICoqUEFTUyoqIHwgSW5kZXBlbmRlbnQgcmV2aWV3IHJlcXVpcmVk
IOKAlCBjb25zaXN0ZW5jeSBsZW5zIDMgfCBgSU5ERVBFTkRFTlRfQUNDRVBUQU5DRT1QRU5ESU5HYCB8CnwgMTQxIHwgcXVhbGl0eSB8ICoqUEFTUyoqIHwg
SWRlbXBvdGVuY3kgcmVxdWlyZWQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgMyB8IGBpZGVtcG90ZW50YCB8CnwgMTQyIHwgcXVhbGl0eSB8ICoqUEFTUyoqIHwg
QXVkaXRhYmlsaXR5IHJlcXVpcmVkIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDMgfCBgYXVkaXRgIHwKfCAxNDMgfCBxdWFsaXR5IHwgKipQQVNTKiogfCBQcm90
ZWN0ZWQgYWN0aW9ucyBwcmVzZXJ2ZWQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgMyB8IGBwcm90ZWN0ZWRgIHwKfCAxNDQgfCB0ZXN0aW5nIHwgKipQQVNTKiog
fCBQb3N0Z3JlU1FMIHByb29mIHByZXNlbnQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgMyB8IGBQb3N0Z3JlU1FMYCB8CnwgMTQ1IHwgdGVzdGluZyB8ICoqUEFT
UyoqIHwgRnJvbnRlbmQvYnJvd3NlciBib3VuZGFyeSBwcmVzZW50IOKAlCBjb25zaXN0ZW5jeSBsZW5zIDMgfCBgZnJvbnRlbmRgIHwKfCAxNDYgfCBhdXRo
b3JpdHkgfCAqKlBBU1MqKiB8IENsYXNzaWZpZXIgb3V0cHV0IHJlbWFpbnMgcHJvcG9zYWwg4oCUIGNvbnNpc3RlbmN5IGxlbnMgNCB8IGBDbGFzc2lmaWNh
dGlvbkVudmVsb3BlYCB8CnwgMTQ3IHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBWZXJpZmllZCB0cnV0aCBib3VuZGFyeSBleHBsaWNpdCDigJQgY29uc2lz
dGVuY3kgbGVucyA0IHwgYFZlcmlmaWVkQXNzZXJ0aW9uYCB8CnwgMTQ4IHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBQcm9qZWN0aW9uIGJvdW5kYXJ5IGV4
cGxpY2l0IOKAlCBjb25zaXN0ZW5jeSBsZW5zIDQgfCBgdHlwZWQgcHJvamVjdGlvbmAgfAp8IDE0OSB8IGF1dGhvcml0eSB8ICoqUEFTUyoqIHwgTm8gYXV0
by1wcm9tb3Rpb24g4oCUIGNvbnNpc3RlbmN5IGxlbnMgNCB8IGBBVVRPX1BST01PVElPTl9FTkFCTEVEPWZhbHNlYCB8CnwgMTUwIHwgYXV0aG9yaXR5IHwg
KipQQVNTKiogfCBEZXBsb3llZCBzdGF0ZSBrZXB0IHNlcGFyYXRlIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDQgfCBgVkVSSUZJRURfREVQTE9ZRUQ9ZmFsc2Vg
IHwKfCAxNTEgfCBzb3VyY2UgfCAqKlBBU1MqKiB8IE5vIG5ldyBTTUIgcGF0aCDigJQgY29uc2lzdGVuY3kgbGVucyA0IHwgYE5FV19TTUJfQ09OTkVDVElP
TlM9MGAgfAp8IDE1MiB8IHNvdXJjZSB8ICoqUEFTUyoqIHwgTm8gbmV3IEFNRUMgc291cmNlIHJlYWRzIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDQgfCBgTkVX
X0FNRUNfU09VUkNFX1JFQURTPTBgIHwKfCAxNTMgfCBzb3VyY2UgfCAqKlBBU1MqKiB8IE5vIHNlY3JldCByZXF1aXJlZCDigJQgY29uc2lzdGVuY3kgbGVu
cyA0IHwgYFNFQ1JFVF9SRVFVSVJFRD1mYWxzZWAgfAp8IDE1NCB8IHNlY3VyaXR5IHwgKipQQVNTKiogfCBTZWNyZXQgZXhjbHVzaW9uIGV4aXN0cyDigJQg
Y29uc2lzdGVuY3kgbGVucyA0IHwgYFNFQ1JFVF9FWENMVURFYCB8CnwgMTU1IHwgZ292ZXJuYW5jZSB8ICoqUEFTUyoqIHwgSW5kZXBlbmRlbnQgcmV2aWV3
IHJlcXVpcmVkIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDQgfCBgSU5ERVBFTkRFTlRfQUNDRVBUQU5DRT1QRU5ESU5HYCB8CnwgMTU2IHwgcXVhbGl0eSB8ICoq
UEFTUyoqIHwgSWRlbXBvdGVuY3kgcmVxdWlyZWQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgNCB8IGBpZGVtcG90ZW50YCB8CnwgMTU3IHwgcXVhbGl0eSB8ICoq
UEFTUyoqIHwgQXVkaXRhYmlsaXR5IHJlcXVpcmVkIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDQgfCBgYXVkaXRgIHwKfCAxNTggfCBxdWFsaXR5IHwgKipQQVNT
KiogfCBQcm90ZWN0ZWQgYWN0aW9ucyBwcmVzZXJ2ZWQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgNCB8IGBwcm90ZWN0ZWRgIHwKfCAxNTkgfCB0ZXN0aW5nIHwg
KipQQVNTKiogfCBQb3N0Z3JlU1FMIHByb29mIHByZXNlbnQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgNCB8IGBQb3N0Z3JlU1FMYCB8CnwgMTYwIHwgdGVzdGlu
ZyB8ICoqUEFTUyoqIHwgRnJvbnRlbmQvYnJvd3NlciBib3VuZGFyeSBwcmVzZW50IOKAlCBjb25zaXN0ZW5jeSBsZW5zIDQgfCBgZnJvbnRlbmRgIHwKfCAx
NjEgfCBhdXRob3JpdHkgfCAqKlBBU1MqKiB8IENsYXNzaWZpZXIgb3V0cHV0IHJlbWFpbnMgcHJvcG9zYWwg4oCUIGNvbnNpc3RlbmN5IGxlbnMgNSB8IGBD
bGFzc2lmaWNhdGlvbkVudmVsb3BlYCB8CnwgMTYyIHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBWZXJpZmllZCB0cnV0aCBib3VuZGFyeSBleHBsaWNpdCDi
gJQgY29uc2lzdGVuY3kgbGVucyA1IHwgYFZlcmlmaWVkQXNzZXJ0aW9uYCB8CnwgMTYzIHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBQcm9qZWN0aW9uIGJv
dW5kYXJ5IGV4cGxpY2l0IOKAlCBjb25zaXN0ZW5jeSBsZW5zIDUgfCBgdHlwZWQgcHJvamVjdGlvbmAgfAp8IDE2NCB8IGF1dGhvcml0eSB8ICoqUEFTUyoq
IHwgTm8gYXV0by1wcm9tb3Rpb24g4oCUIGNvbnNpc3RlbmN5IGxlbnMgNSB8IGBBVVRPX1BST01PVElPTl9FTkFCTEVEPWZhbHNlYCB8CnwgMTY1IHwgYXV0
aG9yaXR5IHwgKipQQVNTKiogfCBEZXBsb3llZCBzdGF0ZSBrZXB0IHNlcGFyYXRlIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDUgfCBgVkVSSUZJRURfREVQTE9Z
RUQ9ZmFsc2VgIHwKfCAxNjYgfCBzb3VyY2UgfCAqKlBBU1MqKiB8IE5vIG5ldyBTTUIgcGF0aCDigJQgY29uc2lzdGVuY3kgbGVucyA1IHwgYE5FV19TTUJf
Q09OTkVDVElPTlM9MGAgfAp8IDE2NyB8IHNvdXJjZSB8ICoqUEFTUyoqIHwgTm8gbmV3IEFNRUMgc291cmNlIHJlYWRzIOKAlCBjb25zaXN0ZW5jeSBsZW5z
IDUgfCBgTkVXX0FNRUNfU09VUkNFX1JFQURTPTBgIHwKfCAxNjggfCBzb3VyY2UgfCAqKlBBU1MqKiB8IE5vIHNlY3JldCByZXF1aXJlZCDigJQgY29uc2lz
dGVuY3kgbGVucyA1IHwgYFNFQ1JFVF9SRVFVSVJFRD1mYWxzZWAgfAp8IDE2OSB8IHNlY3VyaXR5IHwgKipQQVNTKiogfCBTZWNyZXQgZXhjbHVzaW9uIGV4
aXN0cyDigJQgY29uc2lzdGVuY3kgbGVucyA1IHwgYFNFQ1JFVF9FWENMVURFYCB8CnwgMTcwIHwgZ292ZXJuYW5jZSB8ICoqUEFTUyoqIHwgSW5kZXBlbmRl
bnQgcmV2aWV3IHJlcXVpcmVkIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDUgfCBgSU5ERVBFTkRFTlRfQUNDRVBUQU5DRT1QRU5ESU5HYCB8CnwgMTcxIHwgcXVh
bGl0eSB8ICoqUEFTUyoqIHwgSWRlbXBvdGVuY3kgcmVxdWlyZWQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgNSB8IGBpZGVtcG90ZW50YCB8CnwgMTcyIHwgcXVh
bGl0eSB8ICoqUEFTUyoqIHwgQXVkaXRhYmlsaXR5IHJlcXVpcmVkIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDUgfCBgYXVkaXRgIHwKfCAxNzMgfCBxdWFsaXR5
IHwgKipQQVNTKiogfCBQcm90ZWN0ZWQgYWN0aW9ucyBwcmVzZXJ2ZWQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgNSB8IGBwcm90ZWN0ZWRgIHwKfCAxNzQgfCB0
ZXN0aW5nIHwgKipQQVNTKiogfCBQb3N0Z3JlU1FMIHByb29mIHByZXNlbnQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgNSB8IGBQb3N0Z3JlU1FMYCB8CnwgMTc1
IHwgdGVzdGluZyB8ICoqUEFTUyoqIHwgRnJvbnRlbmQvYnJvd3NlciBib3VuZGFyeSBwcmVzZW50IOKAlCBjb25zaXN0ZW5jeSBsZW5zIDUgfCBgZnJvbnRl
bmRgIHwKfCAxNzYgfCBhdXRob3JpdHkgfCAqKlBBU1MqKiB8IENsYXNzaWZpZXIgb3V0cHV0IHJlbWFpbnMgcHJvcG9zYWwg4oCUIGNvbnNpc3RlbmN5IGxl
bnMgNiB8IGBDbGFzc2lmaWNhdGlvbkVudmVsb3BlYCB8CnwgMTc3IHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBWZXJpZmllZCB0cnV0aCBib3VuZGFyeSBl
eHBsaWNpdCDigJQgY29uc2lzdGVuY3kgbGVucyA2IHwgYFZlcmlmaWVkQXNzZXJ0aW9uYCB8CnwgMTc4IHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBQcm9q
ZWN0aW9uIGJvdW5kYXJ5IGV4cGxpY2l0IOKAlCBjb25zaXN0ZW5jeSBsZW5zIDYgfCBgdHlwZWQgcHJvamVjdGlvbmAgfAp8IDE3OSB8IGF1dGhvcml0eSB8
ICoqUEFTUyoqIHwgTm8gYXV0by1wcm9tb3Rpb24g4oCUIGNvbnNpc3RlbmN5IGxlbnMgNiB8IGBBVVRPX1BST01PVElPTl9FTkFCTEVEPWZhbHNlYCB8Cnwg
MTgwIHwgYXV0aG9yaXR5IHwgKipQQVNTKiogfCBEZXBsb3llZCBzdGF0ZSBrZXB0IHNlcGFyYXRlIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDYgfCBgVkVSSUZJ
RURfREVQTE9ZRUQ9ZmFsc2VgIHwKfCAxODEgfCBzb3VyY2UgfCAqKlBBU1MqKiB8IE5vIG5ldyBTTUIgcGF0aCDigJQgY29uc2lzdGVuY3kgbGVucyA2IHwg
YE5FV19TTUJfQ09OTkVDVElPTlM9MGAgfAp8IDE4MiB8IHNvdXJjZSB8ICoqUEFTUyoqIHwgTm8gbmV3IEFNRUMgc291cmNlIHJlYWRzIOKAlCBjb25zaXN0
ZW5jeSBsZW5zIDYgfCBgTkVXX0FNRUNfU09VUkNFX1JFQURTPTBgIHwKfCAxODMgfCBzb3VyY2UgfCAqKlBBU1MqKiB8IE5vIHNlY3JldCByZXF1aXJlZCDi
gJQgY29uc2lzdGVuY3kgbGVucyA2IHwgYFNFQ1JFVF9SRVFVSVJFRD1mYWxzZWAgfAp8IDE4NCB8IHNlY3VyaXR5IHwgKipQQVNTKiogfCBTZWNyZXQgZXhj
bHVzaW9uIGV4aXN0cyDigJQgY29uc2lzdGVuY3kgbGVucyA2IHwgYFNFQ1JFVF9FWENMVURFYCB8CnwgMTg1IHwgZ292ZXJuYW5jZSB8ICoqUEFTUyoqIHwg
SW5kZXBlbmRlbnQgcmV2aWV3IHJlcXVpcmVkIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDYgfCBgSU5ERVBFTkRFTlRfQUNDRVBUQU5DRT1QRU5ESU5HYCB8Cnwg
MTg2IHwgcXVhbGl0eSB8ICoqUEFTUyoqIHwgSWRlbXBvdGVuY3kgcmVxdWlyZWQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgNiB8IGBpZGVtcG90ZW50YCB8Cnwg
MTg3IHwgcXVhbGl0eSB8ICoqUEFTUyoqIHwgQXVkaXRhYmlsaXR5IHJlcXVpcmVkIOKAlCBjb25zaXN0ZW5jeSBsZW5zIDYgfCBgYXVkaXRgIHwKfCAxODgg
fCBxdWFsaXR5IHwgKipQQVNTKiogfCBQcm90ZWN0ZWQgYWN0aW9ucyBwcmVzZXJ2ZWQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgNiB8IGBwcm90ZWN0ZWRgIHwK
fCAxODkgfCB0ZXN0aW5nIHwgKipQQVNTKiogfCBQb3N0Z3JlU1FMIHByb29mIHByZXNlbnQg4oCUIGNvbnNpc3RlbmN5IGxlbnMgNiB8IGBQb3N0Z3JlU1FM
YCB8CnwgMTkwIHwgdGVzdGluZyB8ICoqUEFTUyoqIHwgRnJvbnRlbmQvYnJvd3NlciBib3VuZGFyeSBwcmVzZW50IOKAlCBjb25zaXN0ZW5jeSBsZW5zIDYg
fCBgZnJvbnRlbmRgIHwK
<<<END_BASE64_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_190_Check_Design_Validation_Report.md>>>

<<<BEGIN_BASE64_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_Actions.md::SHA256=87a2376489a394806f9b11dadad5db710a0a0149ee895a449d1e4ea06823968e::BYTE_COUNT=801>>>
IyBQaGFzZSA1IEFjdGlvbnMKCkRlZmF1bHQgRFNNL2h1bWFuIGFjdGlvbnM6IG5vbmUuCgpgRFNNX0FDVElPTlNfUkVRVUlSRUQ9MGAsIGBOQVNfVEFTS19T
Q0hFRFVMRVJfUlVOUz0wYCwgYFNNQl9DT05ORUNUSU9OUz0wYCwgYE5FV19BTUVDX1NPVVJDRV9SRUFEUz0wYCwgYFNFQ1JFVF9SRVFVSVJFRD1mYWxzZWAu
CgpEbyBub3QgcmVjcmVhdGUgdGhlIE5BUyBzZWNyZXQgYW5kIGRvIG5vdCBydW4gYSBTeW5vbG9neSB3YXRjaGVyLiBQaGFzZTUgdXNlcyByZXBvc2l0b3J5
IGZpeHR1cmVzLCBzYW5pdGl6ZWQgU3RhZ2UxUi1kZXJpdmVkIGZpeHR1cmVzLCByZXN0cmljdGVkIGFjY2VwdGVkIGV2aWRlbmNlIHdoZXJlIHBvbGljeSBw
ZXJtaXRzLCBzeW50aGV0aWMgYXBwIHVwbG9hZHMsIGxvY2FsIGJhY2tlbmQvZnJvbnRlbmQsIFBsYXl3cmlnaHQsIGFuZCBkaXNwb3NhYmxlIFBvc3RncmVT
UUwuCgpEaXNwb3NhYmxlIFBvc3RncmVTUUwgcHJvdmVzIFBvc3RncmVTUUwgYmVoYXZpb3Igb25seTsgaXQgaXMgbm90IEF6dXJlIFBvc3RncmVTUUwgcHJv
b2YuIEJyb3dzZXIgdXNlcyBmcm9udGVuZOKGkmxvY2FsIGJhY2tlbmTihpJkaXNwb3NhYmxlIFBvc3RncmVTUUw7IGl0IGlzIG5vdCBWZXJjZWwvQXp1cmUg
ZGVwbG95ZWQgcHJvb2YuCgpSZWFsIGNvbnRpbnVvdXMgU3lub2xvZ3kgc2hhZG93IGlzIG5vdCBwYXJ0IG9mIFBoYXNlNSBieSBkZWZhdWx0LiBJdCBuZWVk
cyBhIHNlcGFyYXRlbHkgaW5kZXBlbmRlbnRseSBhY2NlcHRlZCBgQU1FQ19MSVZFX1NIQURPV19BQ1RJVkFUSU9OX01BTklGRVNUX3YxYC4K
<<<END_BASE64_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_Actions.md>>>

<<<BEGIN_BASE64_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_FINAL_R3_OneShot_EvidenceTruth_SQLServer_Browser_Closure_2026-08-24.md::SHA256=0fcb3efe875dff8b8d0c5cd939666ddcf37ea4d3d256e501d8c1927b288d34c5::BYTE_COUNT=46742>>>
IyBPTkUtU0hPVCBDT0RFWCBPV05FUiBBVVRIT1JJWkFUSU9OIOKAlCBQUk9QT1NBTE9QUyAvIEFNRUMgUEhBU0UgNSBGSU5BTCBSMwojIyBFdmlkZW5jZS10
cnV0aCByZXBhaXIgKyBkZXRlcm1pbmlzdGljIGZyZWV6ZSBwcm9vZiArIGFjdHVhbCBTSEFET1cgcmVwbGF5ICsgbmF0aXZlIFNRTCBTZXJ2ZXIgMjAyMiAr
IHJlYWwgYnJvd3NlcgoqKkRhdGU6KiogMjAyNi0wOC0yNCAvIDIwMjYtMDgtMjUgVVRDIGJvdW5kYXJ5CgotLS0KCiMgMC4gT1dORVIgQVVUSE9SSVpBVElP
TiAvIFNVUEVSU0VTU0lPTgoKVGhlIE93bmVyIGV4cGxpY2l0bHkgYXV0aG9yaXplcyBvbmUgbmV3IGJvdW5kZWQgUGhhc2U1IHJlcGFpci9yZXBsYWNlbWVu
dApyZXZpc2lvbiBhZnRlciB0aGUgZXhoYXVzdGVkIFIyIGF0dGVtcHQuCgpUaGlzIFIzIHByb21wdCBzdXBlcnNlZGVzIHRoZSBmYWlsZWQgUjIgZXhlY3V0
aW9uIHN0YXRlIGZvciAqKnJlcGFpciBhdXRob3JpdHkqKgpvbmx5LiBQcmVzZXJ2ZSBSMiBhcyBpbW11dGFibGUgaGlzdG9yaWNhbCBwcm92ZW5hbmNlLgoK
RG8gbm90IHJlcnVuIFIyIHVuY2hhbmdlZC4KClIzIG9iamVjdGl2ZToKCmBgYHRleHQKcmVwYWlyIGFsbCBpbmRlcGVuZGVudGx5IGNvbmZpcm1lZCBQaGFz
ZTUgZXZpZGVuY2UtaW50ZWdyaXR5IGRlZmVjdHMKKwpyZXBhaXIgYWxsIGN1cnJlbnRseSBrbm93biBkZXRlcm1pbmlzdGljIHZhbGlkYXRpb24td29ya2Zs
b3cgYmxvY2tlcnMKKwpwcmVzZXJ2ZSBjbGFzc2lmaWVyL2ZyZWV6ZSBidXNpbmVzcyBiZWhhdmlvcgorCmV4ZWN1dGUgb25lIGNvbXBsZXRlIGZyZXNoIG5h
dGl2ZSBTUUwgU2VydmVyICsgcmVhbCBicm93c2VyIHZhbGlkYXRpb24KKwpTVE9QIGZvciBpbmRlcGVuZGVudCBQaGFzZTUgYWNjZXB0YW5jZQpgYGAKClRo
aXMgaXMgbm90IGRlcGxveW1lbnQgYXV0aG9yaXphdGlvbi4KCk5vIEF6dXJlIG11dGF0aW9uLgpObyBFbnRyYSBtdXRhdGlvbi4KTm8gU3lub2xvZ3kvU01C
IGFjY2Vzcy4KTm8gcmVhbCBBTUVDIGRhdGEuCk5vIGNvbnRpbnVvdXMgbGl2ZSBzaGFkb3cuCk5vIHdyaXRlYmFjay4KTm8gUGhhc2U2LgoKLS0tCgojIDEu
IEdPVkVSTklORyBTT1VSQ0UgLyBTVEFURSBSVUxFCgpVc2U6CgpgYGB0ZXh0CmxhdGVzdCBleHBsaWNpdCBPd25lci9wcm9kdWN0IGRlY2lzaW9uCisgbGF0
ZXIgZXhlY3V0YWJsZSByZXBvc2l0b3J5L3J1bnRpbWUgZXZpZGVuY2UKKyBsYXRlciBpbmRlcGVuZGVudCBhY2NlcHRhbmNlIHdoZXJlIHJlcXVpcmVkCj0g
Z292ZXJuaW5nIGN1cnJlbnQgc3RhdGUKYGBgCgpFeGFjdCBydW4vYXJ0aWZhY3QgZXZpZGVuY2Ugb3V0cmFua3MgcHJvbXB0IGludGVudC4KCkRvIG5vdCBj
b2xsYXBzZToKCmBgYHRleHQKSU1QTEVNRU5URUQKVkVSSUZJRURfTE9DQUwKVkVSSUZJRURfU1FMU0VSVkVSX0NPTVBBVApWRVJJRklFRF9CUk9XU0VSClZF
UklGSUVEX0FaVVJFX1NRTApWRVJJRklFRF9ERVBMT1lFRApJTkRFUEVOREVOVExZX0FDQ0VQVEVECmBgYAoKaW50byBvbmUgc3RhdGUuCgotLS0KCiMgMi4g
RVhBQ1QgUEhBU0U0IEVOVFJZIOKAlCBNVVNUIFJFTUFJTiBJTU1VVEFCTEUKClJlcXVpcmUgbGl2ZToKCmBgYHRleHQKUEhBU0U0X0lOREVQRU5ERU5UX0FD
Q0VQVEFOQ0U9UEFTUwoKUEhBU0U0X0FDQ0VQVEVEX1NIQT0KNzA3MDAzZmMxNjc2N2ZiMjhiOWM5NjhmYmNmMTY4YWIwM2ViYWRjMQoKUEhBU0U0X0FDQ0VQ
VEVEX1RSRUU9CmFmNDczMTM0ZjZhOTJiOWRjOTkxOWVhZTcxZjFlMDJhM2VkODFlMWUKClBIQVNFNF9BQ0NFUFRBTkNFX1ZBTElEQVRJT05fU0hBPQpkNTY4
MTdkMjdhOWFhYWY2OWFhMDhiNWUzMTRmNzgyOTdlZDQ1Mzc2CgpQSEFTRTRfQUNDRVBUQU5DRV9SVU5fSUQ9CjMyNzc4Nzc1MDg1CgpQSEFTRTRfQUNDRVBU
QU5DRV9BUlRJRkFDVF9TSEEyNTY9Cjg3N2YxZTM5YzRiYjBlMTYxODdkY2Y0ZGU3NmJhNDdjZmY3ZGYzYmRmN2NiMDFhMmFlNjAyN2RhMWRmNGY0YTYKYGBg
CgpQcmVzZXJ2ZSBQaGFzZTQgYWNjZXB0ZWQgYnl0ZXMuCgpObyBQaGFzZTQgcmVpbXBsZW1lbnRhdGlvbi4KCi0tLQoKIyAzLiBFWEFDVCBGQUlMRUQgUEhB
U0U1IFIyIFNUQVRFIOKAlCBSRVBST1ZFIEZJUlNUCgpBcHBsaWNhdGlvbjoKCmBgYHRleHQKUEhBU0U1X1IyX0FQUExJQ0FUSU9OX0JSQU5DSD0KcGhhc2U1
LWNsYXNzaWZpZXItc2hhZG93LXZhbGlkYXRpb24tdjEKClBIQVNFNV9SMl9BUFBMSUNBVElPTl9TSEE9CmNhNjA0NTlmMjEwM2NiZjMwZTUyZTA1YzU5Yjhh
ZjZkNzcxNGJlMTIKClBIQVNFNV9SMl9BUFBMSUNBVElPTl9QQVJFTlQ9CjcwNzAwM2ZjMTY3NjdmYjI4YjljOTY4ZmJjZjE2OGFiMDNlYmFkYzEKClBIQVNF
NV9SMl9BUFBMSUNBVElPTl9UUkVFPQpmYjY2OTk2NTdhNTYyYjA3OWMxMWI5NmMwMzk2MWM4NTkzMWEwZTY2CmBgYAoKVmFsaWRhdGlvbjoKCmBgYHRleHQK
UEhBU0U1X1IyX1ZBTElEQVRJT05fQlJBTkNIPQpwaGFzZTUtY2xhc3NpZmllci1zaGFkb3ctdmFsaWRhdGlvbi1jaS12MQoKUEhBU0U1X1IyX1ZBTElEQVRJ
T05fU0hBPQozODQyZmMwZmFmNGM5NWJmOTMzZDBhNTZjZDg3NzMxNjJlOTdmODkzCgpQSEFTRTVfUjJfVkFMSURBVElPTl9QQVJFTlQ9CmNhNjA0NTlmMjEw
M2NiZjMwZTUyZTA1YzU5YjhhZjZkNzcxNGJlMTIKClBIQVNFNV9SMl9WQUxJREFUSU9OX1RSRUU9CmM0NWJjYWQ3ZTIyOWZhNzkwMjcxM2E5ZmFkMzFmYTUx
YWVhNjI2MTUKClBIQVNFNV9SMl9XT1JLRkxPV19QQVRIPQouZ2l0aHViL3dvcmtmbG93cy9waGFzZTUtY2xhc3NpZmllci1zaGFkb3ctdmFsaWRhdGlvbi1j
aS55bWwKClBIQVNFNV9SMl9XT1JLRkxPV19CTE9CX1NIQTE9CjAzZGZiZTE0NGU5YTBlNjFiN2RkYzY0OGViZTljYzhjZjcxMWY1NjAKYGBgCgpGYWlsZWQg
cmVtb3RlIHJ1bjoKCmBgYHRleHQKUlVOX0lEPTMyNzkyNjc2MjU3CkpPQl9JRD05NzYzNzMwMDMyNgpBUlRJRkFDVF9JRD05NTQzNjgxMzMyCgpBUlRJRkFD
VF9TSEEyNTY9CjY0MDYwNjQ3NTdmMzA4YzI1Yzk4M2I4OTVhY2IxOTkzZjZiODYyNjAxM2MxZDU3OWJlMmQ0YjM5YmU2MmI2YjMKCkZJUlNUX0ZBSUxFRF9H
QVRFPQpOQVRJVkVfU1FMX1NFUlZFUl8yMDIyX0RFVkVMT1BFUl9CT09UU1RSQVAKCkZJUlNUX0ZBSUxFRF9TVUJHQVRFPQpTUUxTRVJWRVJfQ09OVEFJTkVS
X0lNQUdFX01BTklGRVNUCgpGQUlMRURfSU1BR0U9Cm1jci5taWNyb3NvZnQuY29tL21zc3FsL3NlcnZlcjoyMDIyLUdBLXVidW50dS0yMC4wNApgYGAKClJl
cHJvdmUgdGhlIGV4YWN0IGZhaWxlZCBhcnRpZmFjdCAvIGpvYiBiZWZvcmUgbXV0YXRpb24uCgpSZXF1aXJlOgoKYGBgdGV4dApSMl9SVU5fUkVTVUxUPVZB
TElEX0ZBSUxfQ0xPU0VEClIyX1NRTFNFUlZFUl9DT05UQUlORVJfRVhJVF9DT0RFPTEyNQpSMl9ET1dOU1RSRUFNX1JVTlRJTUVfTk9UX0VYRUNVVEVEPXRy
dWUKUjJfQlJPV1NFUl9OT1RfRVhFQ1VURUQ9dHJ1ZQpSMl9GSU5BTElaRVJfTk9UX0VYRUNVVEVEPXRydWUKYGBgCgpJZiBtYXRlcmlhbGx5IGRpZmZlcmVu
dDoKCmBgYHRleHQKUkVTVUxUPVNUT1BfUEhBU0U1X1IzX0RJQUdOT1NJU19DSEFOR0VECmBgYAoKU1RPUC4KCi0tLQoKIyA0LiBORVcgUjMgQlJBTkNIRVMg
4oCUIExJVkUgQUJTRU5DRSBHQVRFCgpCZWZvcmUgbXV0YXRpb24gcmVxdWlyZSBib3RoIGFic2VudDoKCmBgYHRleHQKcGhhc2U1LWNsYXNzaWZpZXItc2hh
ZG93LXZhbGlkYXRpb24tcjMtdjEKcGhhc2U1LWNsYXNzaWZpZXItc2hhZG93LXZhbGlkYXRpb24tY2ktcjMtdjEKYGBgCgpJZiBlaXRoZXIgZXhpc3RzOgoK
YGBgdGV4dApSRVNVTFQ9U1RPUF9QSEFTRTVfUjNfQlJBTkNIX0NPTExJU0lPTgpgYGAKClNUT1AuCgotLS0KCiMgNS4gQ1VSUkVOVCBPV05FUiBEQVRBQkFT
RSBERUNJU0lPTgoKUHJlc2VydmUgY3VycmVudCBnb3Zlcm5pbmcgdGFyZ2V0OgoKYGBgdGV4dApEQVRBQkFTRV9UQVJHRVRfREVDSVNJT049T1dORVJfQ09O
RklSTUVECkRBVEFCQVNFX0VOR0lORV9UQVJHRVQ9QVpVUkVfU1FMX1NRTF9TRVJWRVJfRU5HSU5FCgpBWlVSRV9TUUxfU0VSVklDRV9WQVJJQU5UPUFaVVJF
X1NRTF9EQVRBQkFTRQpBWlVSRV9TUUxfREFUQUJBU0VfU0VMRUNURUQ9dHJ1ZQpBWlVSRV9TUUxfTUFOQUdFRF9JTlNUQU5DRV9TRUxFQ1RFRD1mYWxzZQoK
QVpVUkVfU1FMX0VYQUNUX1NLVT1PV05FUl9ERUNJU0lPTl9QRU5ESU5HCmBgYAoKUjMgdXNlcyBsb2NhbCBkaXNwb3NhYmxlIE1pY3Jvc29mdCBTUUwgU2Vy
dmVyIDIwMjIgZm9yIGVuZ2luZS1jb21wYXRpYmlsaXR5CnByb29mLgoKSXQgZG9lcyAqKm5vdCoqIGVzdGFibGlzaCBhY3R1YWwgQXp1cmUgU1FMIHNlcnZp
Y2UgdmVyaWZpY2F0aW9uLgoKLS0tCgojIDYuIFIzIElTIE5PVCBBIENMQVNTSUZJRVIgUkVERVNJR04KClIyIGNsYXNzaWZpZXIvZnJlZXplIGJlaGF2aW9y
IGlzIHByZXNlcnZlZC4KClIzIG11c3Qgbm90IG1vZGlmeToKCmBgYHRleHQKYmFja2VuZC9hcHAvc2VydmljZXMvY2xhc3NpZmllcl92Mi5weQpiYWNrZW5k
L2FwcC9zY2hlbWFzL2NsYXNzaWZpZXJfdjIucHkKYmFja2VuZC9hcHAvYXBpL3BoYXNlNS5weQoKY29udHJhY3RzL2FtZWMvcGhhc2U1L0FNRUNfQ0xBU1NJ
RklFUl9WMl9SVUxFU192MS5qc29uCmNvbnRyYWN0cy9hbWVjL3BoYXNlNS9BTUVDX0NMQVNTSUZJRVJfUk9CVVNUTkVTU19DT1JQVVNfVjIuanNvbgpjb250
cmFjdHMvYW1lYy9waGFzZTUvQU1FQ19DTEFTU0lGSUVSX0NBTElCUkFUSU9OX0RFVkVMT1BNRU5UX01BTklGRVNUX3YxLmpzb24KY29udHJhY3RzL2FtZWMv
cGhhc2U1L0FNRUNfQ0xBU1NJRklFUl9WQUxJREFUSU9OX01BTklGRVNUX3YxLmpzb24KY29udHJhY3RzL2FtZWMvcGhhc2U1L0FNRUNfQ0xBU1NJRklFUl9I
T0xET1VUX0FEVkVSU0FSSUFMX01BTklGRVNUX3YxLmpzb24KCmNvbnRyYWN0cy9hbWVjL3BoYXNlNS9BTUVDX0NMQVNTSUZJRVJfVjJfQ0FMSUJSQVRJT05f
UkVTVUxUU192MS5qc29uCmNvbnRyYWN0cy9hbWVjL3BoYXNlNS9BTUVDX0NMQVNTSUZJRVJfVjJfVkFMSURBVElPTl9SRVNVTFRTX3YxLmpzb24KY29udHJh
Y3RzL2FtZWMvcGhhc2U1L0FNRUNfQ0xBU1NJRklFUl9WMl9IT0xET1VUX1JFU1VMVFNfdjEuanNvbgpjb250cmFjdHMvYW1lYy9waGFzZTUvQU1FQ19DTEFT
U0lGSUVSX1YyX0NST1NTX0NPTlRFWFRfUkVTVUxUU192MS5qc29uCmNvbnRyYWN0cy9hbWVjL3BoYXNlNS9BTUVDX0NMQVNTSUZJRVJfVjJfUEFUSF9DT1VO
VEVSRkFDVFVBTF9SRVNVTFRTX3YxLmpzb24KCmNvbnRyYWN0cy9hbWVjL3BoYXNlNS9BTUVDX0NMQVNTSUZJRVJfVjJfRlJFRVpFX01BTklGRVNUX3YxLmpz
b24KY29udHJhY3RzL2FtZWMvcGhhc2U1L0FNRUNfUEhBU0U1X1NIQURPV19DT05UUkFDVF92MS5qc29uCmNvbnRyYWN0cy9hbWVjL3BoYXNlNS9BTUVDX1BI
QVNFNV9JTlBVVF9JREVOVElUWV9NQU5JRkVTVF92MS5qc29uCmBgYAoKUmVxdWlyZSBleGFjdCBieXRlIGVxdWFsaXR5IGFnYWluc3QgYGNhNjA0NTkuLi5g
IGZvciB0aG9zZSBwYXRocy4KCklmIGNsYXNzaWZpZXIvcnVsZS9jb3JwdXMvaG9sZG91dCBiZWhhdmlvciBtdXN0IGNoYW5nZToKCmBgYHRleHQKUkVTVUxU
PVNUT1BfUEhBU0U1X1IzX0NMQVNTSUZJRVJfQkVIQVZJT1JfU0NPUEVfRVhQQU5TSU9OX1JFUVVJUkVECmBgYAoKU1RPUC4gRG8gbm90IHNpbGVudGx5IGJ1
cm4vcmVidWlsZCBob2xkb3V0LgoKLS0tCgojIDcuIENSRUFURSBGUkVTSCBSMyBBUFBMSUNBVElPTiBCUkFOQ0gKCkNyZWF0ZToKCmBgYHRleHQKUEhBU0U1
X1IzX0FQUExJQ0FUSU9OX0JSQU5DSD0KcGhhc2U1LWNsYXNzaWZpZXItc2hhZG93LXZhbGlkYXRpb24tcjMtdjEKClBIQVNFNV9SM19BUFBMSUNBVElPTl9C
QVNFPQpjYTYwNDU5ZjIxMDNjYmYzMGU1MmUwNWM1OWI4YWY2ZDc3MTRiZTEyCmBgYAoKRGlyZWN0bHkgZnJvbSBleGFjdCBSMiBhcHBsaWNhdGlvbiBjYW5k
aWRhdGUuCgpObyBtZXJnZS4KTm8gcmViYXNlLgpObyBhbWVuZC4KTm8gZm9yY2UgcHVzaC4KCi0tLQoKIyA4LiBSMyBBUFBMSUNBVElPTiBNVVRBVElPTiBT
VVJGQUNFCgpSMyBtYXkgbW9kaWZ5IG9ubHkgdGhpcyBldmlkZW5jZS92YWxpZGF0aW9uIHN1cmZhY2U6CgpgYGB0ZXh0CnNjcmlwdHMvcGhhc2U1L2NvbW1v
bi5weQpzY3JpcHRzL3BoYXNlNS9yZWdpc3RyeS5weQpzY3JpcHRzL3BoYXNlNS9zb3VyY2VfcHJlZmxpZ2h0LnB5CnNjcmlwdHMvcGhhc2U1L2Jyb3dzZXJf
ZXZpZGVuY2UucHkKc2NyaXB0cy9waGFzZTUvc3Fsc2VydmVyX3RhcmdldGVkLnB5CnNjcmlwdHMvcGhhc2U1L3NoYWRvd19yZXBsYXkucHkKc2NyaXB0cy9w
aGFzZTUvYWNjZXB0YW5jZS5weQpzY3JpcHRzL3BoYXNlNS9ldmlkZW5jZV92YWxpZGF0ZS5weQpzY3JpcHRzL3BoYXNlNS9maW5hbGl6ZS5weQpzY3JpcHRz
L3BoYXNlNS9waGFzZTVfZmluYWxpemUucHkKc2NyaXB0cy9waGFzZTUvcmVwcm9kdWNpYmlsaXR5LnB5CnNjcmlwdHMvcGhhc2U1L3J1bnRpbWVfZXZpZGVu
Y2UucHkKCmJhY2tlbmQvdGVzdHMvdGVzdF9waGFzZTVfY29udHJhY3RzLnB5CmJhY2tlbmQvdGVzdHMvdGVzdF9waGFzZTVfZmluYWxpemVyX25lZ2F0aXZl
LnB5CmJhY2tlbmQvdGVzdHMvdGVzdF9waGFzZTVfZXZpZGVuY2VfaW50ZWdyaXR5LnB5CmJhY2tlbmQvdGVzdHMvdGVzdF9waGFzZTVfc3Fsc2VydmVyX3J1
bnRpbWUucHkKCmZyb250ZW5kL2Jyb3dzZXItcmVhbC1zdGFjay9waGFzZTUtY2xhc3NpZmllci1zaGFkb3cuc3BlYy50cwpmcm9udGVuZC90ZXN0cy9waGFz
ZTUtcmV2aWV3LWV2aWRlbmNlLnRlc3QudHN4CmBgYAoKTmV3IGZpbGVzIGZyb20gdGhhdCBleGFjdCBsaXN0IGFyZSBwZXJtaXR0ZWQuCgpBIHBhdGggbWF5
IHJlbWFpbiB1bmNoYW5nZWQgaWYgbm90IG5lZWRlZC4KCk5vIG90aGVyIGFwcGxpY2F0aW9uIHBhdGggaXMgYXV0aG9yaXplZC4KCklmIGFub3RoZXIgcGF0
aCBpcyB0cnVseSByZXF1aXJlZDoKCmBgYHRleHQKUkVTVUxUPVNUT1BfUEhBU0U1X1IzX0FQUExJQ0FUSU9OX1NDT1BFX0VYUEFOU0lPTl9SRVFVSVJFRApS
RVFVSVJFRF9QQVRIPTxleGFjdD4KUkVBU09OPTxleGFjdD4KYGBgCgpTVE9QIGJlZm9yZSBjb21taXQuCgotLS0KCiMgOS4gUjMgUkVQQUlSIExFREdFUiDi
gJQgQUxMIFJVTi0xMCBERUZFQ1RTIE1VU1QgQ0xPU0UKCkJlZm9yZSBhcHAgY29tbWl0IG1haW50YWluIGFuIGV4cGxpY2l0IG1hY2hpbmUtcmVhZGFibGUg
cmVwYWlyIGxlZGdlciB3aXRoIHRoZXNlCmV4YWN0IHJvd3M6CgpgYGB0ZXh0CkMwMV9TT1VSQ0VfUFJFRkxJR0hUX0hBUkRDT0RFRF9GSUVMRFMKQzAyX0ZJ
WEVEX1NIQV9ERVNDRU5EQU5UX0FVRElUX0lOQ09NUExFVEUKQzAzX0JST1dTRVJfRVZJREVOQ0VfSEFSRENPREVEX1BBU1MKQzA0X1NRTFNFUlZFUl9FVklE
RU5DRV9IQVJEQ09ERURfUEFTUwpDMDVfU0hBRE9XX1JFUExBWV9IQVJEQ09ERURfUEFTUwpDMDZfQUNDRVBUQU5DRV9HRU5FUkFUT1JfSEFSRENPREVEX1BB
U1MKQzA3X0FDQ0VQVEFOQ0VfRVZJREVOQ0VfU0VMRl9SRUZFUkVOVElBTApDMDhfRVZJREVOQ0VfVkFMSURBVE9SX1NFTUFOVElDX0dBUApDMDlfRklOQUxJ
WkVSX0RFRkFVTFRfUlVOVElNRV9QQVNTCkMxMF9GSU5BTElaRVJfQ0FORElEQVRFX1NIQV9OT1RfRVhBQ1QKQzExX0ZJTkFMSVpFUl9TVU1NQVJZX0hBUkRD
T0RFRF9SVU5USU1FCkMxMl9SRVBST0RVQ0lCSUxJVFlfTk9UX1JFR0VORVJBVEVECgpXMDFfSU5WQUxJRF9TUUxTRVJWRVJfSU1BR0VfVEFHClcwMl9TUUxT
RVJWRVJfUEFTU1dPUkRfTk9UX0VYUE9SVEVEClcwM19JTl9DT05UQUlORVJfU1FMQ01EX0JPT1RTVFJBUApXMDRfUExBWVdSSUdIVF9CUk9XU0VSX05PVF9F
WFBMSUNJVExZX0lOU1RBTExFRApgYGAKCkJlZm9yZSBjb21taXQgZXZlcnkgcm93IG11c3QgYmU6CgpgYGB0ZXh0CkNMT1NFRF9XSVRIX0VYRUNVVEFCTEVf
UkVHUkVTU0lPTgpgYGAKCm9yIFIzIG11c3QgU1RPUC4KCldyaXRlIGxvY2FsLW9ubHk6CgpgYGB0ZXh0CmFydGlmYWN0cy9waGFzZTUtcjMtcmVwYWlyLWxl
ZGdlci5qc29uCmBgYAoKRG8gbm90IGNvbW1pdCBnZW5lcmF0ZWQgbGVkZ2VyIG91dHB1dC4KCi0tLQoKIyAxMC4gQ0VOVFJBTCBFVklERU5DRSBSRUdJU1RS
WSDigJQgQUNUVUFMIFBST0RVQ0VSIENPTlRSQUNUUwoKVXBncmFkZSB0aGUgZXhpc3RpbmcgY2VudHJhbCByZWdpc3RyeSByYXRoZXIgdGhhbiBjcmVhdGlu
ZyBhZCBob2MgZXZpZGVuY2UKbmFtZXMgaW4gdGhlIHdvcmtmbG93LgoKRXZlcnkgcmVnaXN0ZXJlZCBwcm9kdWNlciBtdXN0IGRlZmluZSBhdCBtaW5pbXVt
OgoKYGBgdGV4dApwcm9kdWNlcl9pZApyYXdfbG9nX25hbWUKbWV0YV9uYW1lCnJlc3VsdF9uYW1lCnJ1bnRpbWVfcmVxdWlyZWQKYGBgCgpUaGUgcmVnaXN0
cnkgcmVtYWlucyB0aGUgc291cmNlIG9mIHRydXRoIGZvciBhY2NlcHRlZCBwcm9kdWNlciBJRHMuCgpSdW50aW1lLXJlcXVpcmVkIHByb2R1Y2VycyBtdXN0
IGluY2x1ZGUgYXQgbWluaW11bToKCmBgYHRleHQKc3Fsc2VydmVyLWJvb3RzdHJhcApzcWxzZXJ2ZXItdGFyZ2V0ZWQKc2hhZG93LXJlcGxheQpicm93c2Vy
LXJlcXVpcmVkLXBhdGhzCmJyb3dzZXItcXVhbGl0eQpiYWNrZW5kLXRhcmdldGVkCnBoYXNlNC1pbnRlZ3JhdGlvbi1yZWdyZXNzaW9uCmJhY2tlbmQtZnVs
bApmcm9udGVuZC10YXJnZXRlZApmcm9udGVuZC1mdWxsCmZyb250ZW5kLWJ1aWxkCmF1dGhvcml0eS1kZW5pYWwKb2JzZXJ2YWJpbGl0eQpzZWN1cml0eS1o
eWdpZW5lCmBgYAoKU291cmNlL2RldGVybWluaXN0aWMgcHJvZHVjZXJzIGluY2x1ZGUgYXQgbWluaW11bToKCmBgYHRleHQKZW50cnktaWRlbnRpdHkKaW5w
dXQtaWRlbnRpdHkKc291cmNlLXByZWZsaWdodApmcmVlemUtcmVwcm9kdWNpYmlsaXR5CmNsYXNzaWZpZXItY2FsaWJyYXRpb24KY2xhc3NpZmllci12YWxp
ZGF0aW9uCmNsYXNzaWZpZXItaG9sZG91dApjbGFzc2lmaWVyLWNyb3NzLWNvbnRleHQKY2xhc3NpZmllci1wYXRoLWNvdW50ZXJmYWN0dWFsCmFjY2VwdGFu
Y2UKZmluYWxpemVyCmBgYAoKTm8gcHJvZHVjZXIgbWF5IHJlcG9ydCBQQVNTIHNvbGVseSBiZWNhdXNlIGl0cyBzb3VyY2UgZmlsZSBleGlzdHMuCgotLS0K
CiMgMTEuIEMwMS9DMDIg4oCUIFNPVVJDRSBQUkVGTElHSFQgTVVTVCBBQ1RVQUxMWSBFWEVDVVRFIElUUyBDTEFJTVMKClJlcGFpciBgc291cmNlX3ByZWZs
aWdodC5weWAuCgpObyBvdXRwdXQgZmllbGQgcmVwcmVzZW50aW5nIGEgY2hlY2sgbWF5IGJlIGFzc2lnbmVkIHplcm8vdHJ1ZSB1bmxlc3MgY29tcHV0ZWQK
ZnJvbSBpbnNwZWN0ZWQgc291cmNlL3JlcG9zaXRvcnkgc3RhdGUuCgpBdCBtaW5pbXVtIG1lY2hhbmljYWxseSBpbnNwZWN0OgoKYGBgdGV4dAppbXBvcnRz
L21vZHVsZSBwYXRocwpBUEkgcmVnaXN0cmF0aW9uClBoYXNlNCBzZXJ2aWNlIHNpZ25hdHVyZXMKUHlkYW50aWMgY29uc3RydWN0b3JzClNRTEFsY2hlbXkg
Y29uc3RydWN0b3IgZmllbGRzClNRTEFsY2hlbXkgbWFwcGVkIGF0dHJpYnV0ZXMKU1FMIFNlcnZlci1zZW5zaXRpdmUgU1FMCnRleHQoKSBpbXBsaWNpdCBi
aW5kcwoKY2Fub25pY2FsIFBoYXNlNSBmaWxlbmFtZXMKcHJvZHVjZXIvY29uc3VtZXIgZXZpZGVuY2UgbmFtZXMKaW5wdXQtaWRlbnRpdHkgcmVmZXJlbmNl
cwpmcmVlemUgcmVmZXJlbmNlcwphY2NlcHRhbmNlIHByb2R1Y2VyIElEcwpmaW5hbGl6ZXIgcHJvZHVjZXIgcmVxdWlyZW1lbnRzCgpmaXhlZC1TSEEgcmVw
b3NpdG9yeSByZWZlcmVuY2VzCmZpeGVkIGFuY2VzdG9yIGdpdC1zaG93L3JlYWQgcGF0dGVybnMKY3VycmVudCBkZXNjZW5kYW50IHBhdGggZW51bWVyYXRp
b24KZGVzY2VuZGFudC1vbmx5IGFkZGl0aXZlIGZpbGVzCmZpeGVkIHBhdGgvY291bnQgYXNzdW1wdGlvbnMKClBsYXl3cmlnaHQgY29uZmlnL3NwZWMgcGF0
aHMKYWxsIHRlbiByZXF1aXJlZCBicm93c2VyIElEcwpidXNpbmVzcyBBUEkgbW9jay9pbnRlcmNlcHQgcGF0dGVybnMKcm9sZS9jYXBhYmlsaXR5IG5hbWVz
Cgp3b3JrZmxvdy1yZXF1aXJlZCBzY3JpcHQgcGF0aHMKYGBgCgojIyBGaXhlZC1TSEEgZGVzY2VuZGFudCBhdWRpdAoKRG8gbm90IHNwZWNpYWwtY2FzZSBv
bmx5IGBMRUdBQ1lfQk9PTEVBTl9CQVNFTElORV9TSEFgLgoKVGhlIGF1ZGl0IG11c3QgbWVjaGFuaWNhbGx5IGlkZW50aWZ5IHBhdHRlcm5zIGVxdWl2YWxl
bnQgdG86CgpgYGB0ZXh0CmVudW1lcmF0ZS9jdXJyZW50IEhFQUQgcGF0aHMK4oaSIHJlYWQgc2FtZSBwYXRoIGZyb20gZml4ZWQgYW5jZXN0b3IgU0hBCmBg
YAoKYW5kIHJlcG9ydCBhbnkgZGVzY2VuZGFudC1vbmx5IGFuY2VzdG9yIHJlYWQgdGhhdCB3b3VsZCBmYWlsLgoKUmVxdWlyZToKCmBgYHRleHQKUEhBU0U1
X1NPVVJDRV9QUkVGTElHSFRfVkVSU0lPTj0zClBIQVNFNV9TT1VSQ0VfUFJFRkxJR0hUX0RFRklOSVRFX0JMT0NLRVJfQ09VTlQ9MAoKUEhBU0U1X0lOSEVS
SVRFRF9GSVhFRF9TSEFfVEVTVF9DT1VOVD08YWN0dWFsPgpQSEFTRTVfSU5IRVJJVEVEX0ZJWEVEX1NIQV9ERVNDRU5EQU5UX0JMT0NLRVJfQ09VTlQ9MAoK
UEhBU0U1X0lOVkFMSURfTU9ERUxfQ09OU1RSVUNUT1JfS1dBUkdfQ09VTlQ9MApQSEFTRTVfSU5WQUxJRF9NQVBQRURfQVRUUklCVVRFX0NPVU5UPTAKUEhB
U0U1X0lNUExJQ0lUX1RFWFRfQklORF9DT1VOVD0wCgpQSEFTRTVfQ0FOT05JQ0FMX0ZJTEVOQU1FX1JFRkVSRU5DRV9NSVNNQVRDSF9DT1VOVD0wClBIQVNF
NV9PVVRQVVRfQ09OVFJBQ1RfTUlTTUFUQ0hfQ09VTlQ9MApQSEFTRTVfTUlTU0lOR19SVU5USU1FX1BBVEhfQ09VTlQ9MApQSEFTRTVfQUNDRVBUQU5DRV9V
TktOT1dOX0VWSURFTkNFX0lEX0NPVU5UPTAKUEhBU0U1X0ZSRUVaRV9SRUZFUkVOQ0VEX0ZJTEVfTUlTU0lOR19DT1VOVD0wClBIQVNFNV9CUk9XU0VSX1JF
UVVJUkVEX1BBVEhfU1BFQ19NSVNTSU5HPTAKUEhBU0U1X1dPUktGTE9XX0VWSURFTkNFX05BTUVfTUlTTUFUQ0hfQ09VTlQ9MApgYGAKCkFkZCBuZWdhdGl2
ZSB1bml0IGZpeHR1cmVzIHByb3ZpbmcgdGhlIHByZWZsaWdodCBkZXRlY3RzOgotIGRlc2NlbmRhbnQtb25seSBmaXhlZC1hbmNlc3RvciByZWFkOwotIHVu
a25vd24gcHJvZHVjZXI7Ci0gbWlzc2luZyBjYW5vbmljYWwgZmlsZTsKLSBpbXBsaWNpdCB0ZXh0dWFsIGJpbmQ7Ci0gbWlzc2luZyBicm93c2VyIElELgoK
SGFyZGNvZGVkLXplcm8gaW1wbGVtZW50YXRpb24gaXMgZm9yYmlkZGVuLgoKLS0tCgojIDEyLiBDMDMg4oCUIEJST1dTRVIgRVZJREVOQ0UgTVVTVCBQQVJT
RSBSRUFMIFBMQVlXUklHSFQgT1VUUFVUCgpSZXBhaXIgYGJyb3dzZXJfZXZpZGVuY2UucHlgLgoKUmVxdWlyZWQgQ0xJIHNoYXBlOgoKYGBgYmFzaApweXRo
b24gc2NyaXB0cy9waGFzZTUvYnJvd3Nlcl9ldmlkZW5jZS5weSBcCiAgLS1wbGF5d3JpZ2h0LWpzb24gPGFjdHVhbC1qc29uLXJlcG9ydD4gXAogIC0tc3Bl
YyBmcm9udGVuZC9icm93c2VyLXJlYWwtc3RhY2svcGhhc2U1LWNsYXNzaWZpZXItc2hhZG93LnNwZWMudHMgXAogIC0tb3V0cHV0IDxicm93c2VyLXF1YWxp
dHkucmVzdWx0Lmpzb24+CmBgYAoKSXQgbXVzdCBjb25zdW1lIGFjdHVhbCBQbGF5d3JpZ2h0IEpTT04uCgpJdCBtdXN0IGxvY2F0ZSB0aGUgZXhhY3QgcmVx
dWlyZWQgSURzOgoKYGBgdGV4dApQNS1CUk9XU0VSLU5FVwpQNS1CUk9XU0VSLUFNQklHVU9VU19SRVZJRVcKUDUtQlJPV1NFUi1PVVRfT0ZfU0NPUEUKUDUt
QlJPV1NFUi1TRUNSRVRfRVhDTFVERQpQNS1CUk9XU0VSLU1PRElGSUVEX0tOT1dOX1NPVVJDRQpQNS1CUk9XU0VSLU1PVkVfUkVOQU1FX0NBTkRJREFURQpQ
NS1CUk9XU0VSLU1JU1NJTkdfQ0FORElEQVRFClA1LUJST1dTRVItQ09SUkVDVElPTgpQNS1CUk9XU0VSLVBST1RFQ1RFRF9BQ1RJT04KUDUtQlJPV1NFUi1Q
RVJTT05BX1NDT1BFCmBgYAoKRGVyaXZlLCBuZXZlciBoYXJkY29kZToKCmBgYHRleHQKcmVxdWlyZWRfcGF0aF9jb3VudApyZXF1aXJlZF9wYXRoX3Bhc3MK
cmVxdWlyZWRfcGF0aF9mYWlsCnJlcXVpcmVkX3BhdGhfc2tpcApgYGAKClJlcXVpcmUgZXhhY3QgcmVtb3RlIHN1Y2Nlc3M6CgpgYGB0ZXh0ClBIQVNFNV9C
Uk9XU0VSX1JFUVVJUkVEX1BBVEhfQ09VTlQ9MTAKUEhBU0U1X0JST1dTRVJfUkVRVUlSRURfUEFUSF9QQVNTPTEwClBIQVNFNV9CUk9XU0VSX1JFUVVJUkVE
X1BBVEhfRkFJTD0wClBIQVNFNV9CUk9XU0VSX1JFUVVJUkVEX1BBVEhfU0tJUD0wCmBgYAoKQWxzbyBzb3VyY2UtaW5zcGVjdCB0aGUgcmVxdWlyZWQgc3Bl
YyBhbmQgcmVxdWlyZToKCmBgYHRleHQKUEhBU0U1X0JST1dTRVJfQVBJX01PQ0tfQ09VTlRfRk9SX1JFUVVJUkVEX1BBVEhTPTAKYGBgCgpEbyBub3QgdHJl
YXQgcm91dGUvcmVxdWVzdCBtb2NraW5nIG9mIFByb3Bvc2FsT3BzIGJ1c2luZXNzIEFQSSBhcyBwcm9vZi4KCiMjIEJyb3dzZXIgcXVhbGl0eSBldmlkZW5j
ZQoKVGhlIGN1cnJlbnQgVUkgYWxyZWFkeSBjb250YWlucyBsb2FkaW5nLCBlcnJvciBhbmQgZW1wdHkgc3RhdGVzLiBBZGQgZXhlY3V0YWJsZQp0ZXN0cy9l
dmlkZW5jZSByYXRoZXIgdGhhbiBib29sZWFucyBpbiBQeXRob24gc291cmNlLgoKQXQgbWluaW11bSBwcm92ZSB0aHJvdWdoIGJyb3dzZXIgYW5kL29yIGFj
dHVhbCBmcm9udGVuZCB0ZXN0IGV4ZWN1dGlvbjoKCmBgYHRleHQKTE9BRElOR19TVEFURV9QUk9WRU49dHJ1ZQpFUlJPUl9TVEFURV9QUk9WRU49dHJ1ZQpF
TVBUWV9TVEFURV9QUk9WRU49dHJ1ZQpLRVlCT0FSRF9BQ1RJT05fUEFUSFNfUEFTUz10cnVlCkJBU0lDX0FDQ0VTU0lCSUxJVFlfUEFTUz10cnVlCkRFRVBf
TElOS19SRVNPTFVUSU9OX1BBU1M9dHJ1ZQpDT1JSRUxBVElPTl9JRF9JTlNQRUNUQUJMRT10cnVlClJPT1RfRVZFTlRfSU5TUEVDVEFCTEU9dHJ1ZQpgYGAK
CklmIGV4dHJhIFBsYXl3cmlnaHQgcXVhbGl0eSB0ZXN0cyBhcmUgcmVxdWlyZWQsIGFkZCB0aGVtIHdpdGhvdXQgcmVuYW1pbmcgb3IKcmVtb3ZpbmcgdGhl
IHRlbiByZXF1aXJlZCBwYXRoIElEcy4KCk5vIHF1YWxpdHkgUEFTUyBtYXkgYmUgbWFudWZhY3R1cmVkIGluIGBicm93c2VyX2V2aWRlbmNlLnB5YC4KCi0t
LQoKIyAxMy4gQzA0IOKAlCBTUUwgU0VSVkVSIFRBUkdFVEVEIFBST0RVQ0VSIE1VU1QgQ09OU1VNRSBBQ1RVQUwgU1FMIFNFUlZFUiBQUk9PRgoKUmVwYWly
IGBzcWxzZXJ2ZXJfdGFyZ2V0ZWQucHlgLgoKSXQgbXVzdCBub3QgcmV0dXJuIFNRTCBTZXJ2ZXIgMTYgLyBtaWdyYXRpb24gUEFTUyAvIDE2IGdhdGVzIFBB
U1MgZnJvbSBjb25zdGFudHMuCgpSMyByZW1vdGUgZXhlY3V0aW9uIG11c3QgZmlyc3QgZ2VuZXJhdGUgcmVhbCBTUUwgU2VydmVyIGV2aWRlbmNlLgoKUmV1
c2UgdGhlIGluZGVwZW5kZW50bHkgYWNjZXB0ZWQgUGhhc2U0IFNRTCBTZXJ2ZXIgc2VhbSBhbmQgUGhhc2U1IHRhcmdldGVkCnRlc3RzIHJhdGhlciB0aGFu
IGR1cGxpY2F0aW5nIGJ1c2luZXNzIGxvZ2ljLgoKQXQgbWluaW11bSBhY3R1YWwgcnVudGltZSBtdXN0IHByb3ZlOgoKYGBgdGV4dAplbmdpbmU9bXNzcWwK
U1FMU0VSVkVSX01BSk9SPTE2CkFDVElWRV9NSUdSQVRJT05fSEVBRD1iYXNlbGluZV9waGFzZTRfdjM2X2F6dXJlX3NxbApgYGAKClRoZSBQaGFzZTUgcmVx
dWlyZWQgcnVudGltZSBnYXRlcyByZW1haW46CgpgYGB0ZXh0CnNvdXJjZV9ldmVudF9pZGVtcG90ZW5jeQpyZXBsYXlfc3RhYmxlX2Fjcm9zc190aW1lCmV2
aWRlbmNlX2ludGFrZV9pZGVtcG90ZW5jeQpjbGFzc2lmaWNhdGlvbl9lbnZlbG9wZV9pbW11dGFiaWxpdHkKcmV2aWV3X2xvY2tpbmdfY29uY3VycmVuY3kK
Y29ycmVjdGlvbl9hcHBlbmRfb25seQpyZXZpZXdlZF9hc3NlcnRpb25fcHJvbW90aW9uCmFzc2VydGlvbl9zdXBlcnNlc3Npb24KcHJvamVjdGlvbl9pZGVt
cG90ZW5jeQpkdXBsaWNhdGVfc2lkZV9lZmZlY3RfcHJvdGVjdGlvbgpyb2xsYmFjawpmcmVlemVfbWV0YWRhdGEKaGFyZF9nYXRlX3Nob3J0X2NpcmN1aXQK
b3V0X29mX3Njb3BlX25vX3Byb2plY3Rpb24Kc2VjcmV0X2V4Y2x1ZGVfbm9fcHJvamVjdGlvbgpwcm90ZWN0ZWRfYWN0aW9uX2RlbmlhbApgYGAKCkltcGxl
bWVudCBhY3R1YWwgU1FMIFNlcnZlci1iYWNrZWQgdGVzdHMgb3IgbWFwIHRoZW0gdG8gYWxyZWFkeS1leGVjdXRlZCBleGFjdApQaGFzZTQgU1FMIFNlcnZl
ciBnYXRlIGV2aWRlbmNlICsgUGhhc2U1LXNwZWNpZmljIHJ1bnRpbWUgdGVzdHMuCgpFdmVyeSBnYXRlIG11c3QgaGF2ZSBhIHJlYWwgZXZpZGVuY2UgcmVm
ZXJlbmNlLgoKUmVxdWlyZWQ6CgpgYGB0ZXh0ClBIQVNFNV9TUUxTRVJWRVJfVEFSR0VURURfR0FURV9DT1VOVD0xNgpQSEFTRTVfU1FMU0VSVkVSX1RBUkdF
VEVEX1BBU1M9MTYKUEhBU0U1X1NRTFNFUlZFUl9UQVJHRVRFRF9GQUlMPTAKUEhBU0U1X1NRTFNFUlZFUl9UQVJHRVRFRF9TS0lQPTAKUEhBU0U1X1NRTFNF
UlZFUl9UQVJHRVRFRF9TT1VSQ0VfT05MWV9QQVNTX0NPVU5UPTAKYGBgCgpgc3Fsc2VydmVyX3RhcmdldGVkLnB5YCBtdXN0IGNvbnN1bWUgdGhlIHByb2R1
Y2VkIFNRTCBTZXJ2ZXIgcnVudGltZS9KVW5pdC9nYXRlCmV2aWRlbmNlIGFuZCBkZXJpdmUgaXRzIHJlc3VsdC4KCi0tLQoKIyAxNC4gQzA1IOKAlCBTSEFE
T1cgUkVQTEFZIE1VU1QgRVhFQ1VURSBSRUFMIFNZTlRIRVRJQyBSRVBMQVkKClJlcGFpciBgc2hhZG93X3JlcGxheS5weWAuCgpXaGVuIHVzZWQgZm9yIHJl
bW90ZSBhY2NlcHRhbmNlIGl0IG11c3QgcmVxdWlyZSB0aGUgY3VycmVudCBTUUwgU2VydmVyLWJhY2tlZApgREFUQUJBU0VfVVJMYC4KCkV4ZWN1dGUgYSBj
b250cm9sbGVkIHN5bnRoZXRpYyByZXBsYXkgdGhyb3VnaCB0aGUgYWN0dWFsIFBoYXNlNSBjbGFzc2lmaWVyIGFuZAphY2NlcHRlZCBQaGFzZTQgcGVyc2lz
dGVuY2UvcmV2aWV3IHNlYW1zLgoKQXQgbWluaW11bToKMS4gY3JlYXRlIGEgZGV0ZXJtaW5pc3RpYyBzeW50aGV0aWMgY2xhc3NpZmljYXRpb24gcmVxdWVz
dDsKMi4gZXhlY3V0ZSBpdCBhbmQgcGVyc2lzdCBzb3VyY2UvZXZpZGVuY2UvY2xhc3NpZmljYXRpb24gZW52ZWxvcGU7CjMuIHJlcGxheSB0aGUgc2FtZSBs
b2dpY2FsIGlucHV0Owo0LiBwcm92ZSBzdGFibGUgbG9naWNhbCBldmVudCBpZGVudGl0eS9yZXN1bHQ7CjUuIHByb3ZlIG9yaWdpbmFsIENsYXNzaWZpY2F0
aW9uRW52ZWxvcGUgcmVtYWlucyBpbW11dGFibGU7CjYuIGV4ZWN1dGUgYW4gZXhwbGljaXQgcGVybWl0dGVkIGNvcnJlY3Rpb24vcmV2aWV3IGNhc2U7Cjcu
IHByb3ZlIGNvcnJlY3Rpb24gaXMgYXBwZW5kLW9ubHk7CjguIHF1ZXJ5IHN0YXRlIGJlZm9yZS9hZnRlcjsKOS4gcHJvdmUgbm8gY2xhc3NpZmllci1vbmx5
IFZlcmlmaWVkQXNzZXJ0aW9uOwoxMC4gcHJvdmUgbm8gY2xhc3NpZmllci1vbmx5IHR5cGVkIHByb2plY3Rpb247CjExLiBwcm92ZSBubyBwcm90ZWN0ZWQg
YWN0aW9uIGV4ZWN1dGlvbjsKMTIuIHByb3ZlIG5vIFN5bm9sb2d5L3dyaXRlYmFjay9leHRlcm5hbCBjYWxscy4KCkRlcml2ZToKCmBgYHRleHQKU0hBRE9X
X0NMQVNTSUZJQ0FUSU9OX0dFTkVSQVRFRD10cnVlClNIQURPV19DT01QQVJJU09OX1JFQ09SREVEPXRydWUKU0hBRE9XX0NMQVNTSUZJQ0FUSU9OX0VOVkVM
T1BFX0lNTVVUQUJMRT10cnVlClNIQURPV19DT1JSRUNUSU9OX0FQUEVORF9PTkxZPXRydWUKCkNMQVNTSUZJRVJfT05MWV9WRVJJRklFRF9BU1NFUlRJT05f
UFJPTU9USU9OX0NPVU5UPTAKQ0xBU1NJRklFUl9PTkxZX1RZUEVEX1BST0pFQ1RJT05fQ09VTlQ9MApDTEFTU0lGSUVSX1BST1RFQ1RFRF9BQ1RJT05fRVhF
Q1VUSU9OX0NPVU5UPTAKClJFUExBWV9FVkVOVF9JRF9TVEFCTEVfQUNST1NTX1RJTUU9dHJ1ZQpSRVBMQVlfUkVTVUxUX0hBU0hfU1RBQkxFX0FDUk9TU19U
SU1FPXRydWUKUkVQTEFZX1NJREVfRUZGRUNUX0RVUExJQ0FURV9DT1VOVD0wCgpTWU5PTE9HWV9XUklURUJBQ0tfQ09VTlQ9MApMTE1fRVhURVJOQUxfQ0FM
TF9DT1VOVD0wClJFQUxfQ09OVEVOVD1mYWxzZQpgYGAKCkRvIG5vdCBhc3NpZ24gdGhvc2UgdmFsdWVzIGJlZm9yZSBxdWVyeWluZy9leGVjdXRpbmcgdGhl
aXIgcHJvb2YuCgpQcm92aWRlIGEgYC0tb3V0cHV0YCByZXN1bHQgSlNPTi4KCi0tLQoKIyAxNS4gQzA2L0MwNyDigJQgQUNDRVBUQU5DRSBNQVkgTk9UIE1B
TlVGQUNUVVJFIDMwMCBQQVNTIENIRUNLUwoKUmVwYWlyIGBhY2NlcHRhbmNlLnB5YC4KClByZXNlcnZlIHRoZSA+PTMwMCB1bmlxdWUgcHJpbWFyeSByZXF1
aXJlbWVudHMuCgpEbyAqKm5vdCoqIHNldCBldmVyeSBwcmltYXJ5IHJlc3VsdCB0byBQQVNTIHVuY29uZGl0aW9uYWxseS4KCkRvICoqbm90KiogdXNlIGBz
Y3JpcHRzL3BoYXNlNS9hY2NlcHRhbmNlLnB5YCBpdHNlbGYgYXMgc3Vic3RhbnRpdmUgZXZpZGVuY2UKZm9yIGVhY2ggcmVxdWlyZW1lbnQuCgojIyBFdmlk
ZW5jZSBtYXBwaW5nCgpFYWNoIHJlcXVpcmVtZW50L2NhdGVnb3J5IG11c3QgbWFwIHRvIG9uZSBvciBtb3JlIGV4YWN0IHJlZ2lzdGVyZWQgcHJvZHVjZXIK
SURzIHdob3NlIHJlc3VsdC9yYXcvbWV0YSBldmlkZW5jZSBjYW4gcHJvdmUgaXQuCgpFeGFtcGxlczoKCmBgYHRleHQKU1FMU0VSVkVSCuKGkiBzcWxzZXJ2
ZXItYm9vdHN0cmFwICsgc3Fsc2VydmVyLXRhcmdldGVkCgpCUk9XU0VSXyoK4oaSIGJyb3dzZXItcmVxdWlyZWQtcGF0aHMgKyBicm93c2VyLXF1YWxpdHkK
ClJFR1JFU1NJT04K4oaSIGJhY2tlbmQtdGFyZ2V0ZWQgKyBwaGFzZTQtaW50ZWdyYXRpb24tcmVncmVzc2lvbiArIGJhY2tlbmQtZnVsbAogICsgZnJvbnRl
bmQtdGFyZ2V0ZWQgKyBmcm9udGVuZC1mdWxsICsgZnJvbnRlbmQtYnVpbGQKCkJPVU5EQVJZIC8gYXV0aG9yaXR5CuKGkiBzaGFkb3ctcmVwbGF5ICsgYXV0
aG9yaXR5LWRlbmlhbCArIHNlY3VyaXR5LWh5Z2llbmUKCkZSRUVaRQrihpIgaW5wdXQtaWRlbnRpdHkgKyBmcmVlemUtcmVwcm9kdWNpYmlsaXR5CiAgKyBj
bGFzc2lmaWVyLXZhbGlkYXRpb24gKyBjbGFzc2lmaWVyLWhvbGRvdXQKICArIGNsYXNzaWZpZXItY3Jvc3MtY29udGV4dCArIGNsYXNzaWZpZXItcGF0aC1j
b3VudGVyZmFjdHVhbAoKUkVWSUVXIC8gUFJPTU9USU9OIC8gQ09SUkVDVElPTgrihpIgc2hhZG93LXJlcGxheSArIHNxbHNlcnZlci10YXJnZXRlZCArIGF1
dGhvcml0eS1kZW5pYWwKYGBgCgpVc2Ugc3BlY2lmaWMgZXZpZGVuY2UgbWFwcGluZ3MgcmF0aGVyIHRoYW4gcm91bmQtcm9iaW4gcHJvZHVjZXIgSURzLgoK
IyMgUHJlY29tbWl0IGRyeS1ydW4gbW9kZQoKU3VwcG9ydCBhbiBleHBsaWNpdCBkcnktcnVuIGV2aWRlbmNlIHNldCB3aGVyZSBydW50aW1lIHByb2R1Y2Vy
cyBhcmU6CgpgYGB0ZXh0Ck5PVF9FWEVDVVRFRApgYGAKCkluIGRyeSBydW46Ci0gc291cmNlL2RldGVybWluaXN0aWMgY2hlY2tzIG1heSBiZSBldmFsdWF0
ZWQ7Ci0gcnVudGltZS1yZXF1aXJlZCBjaGVja3MgbXVzdCAqKm5vdCoqIGJlY29tZSBQQVNTOwotIG92ZXJhbGwgZHJ5LXJ1biBzdGF0ZSBpcyBub3QgUGhh
c2U1IFBBU1MuCgpSZXF1aXJlOgoKYGBgdGV4dApQSEFTRTVfQUNDRVBUQU5DRV9SRUZFUkVOQ0VfRFJZX1JVTj1QQVNTClBIQVNFNV9QUkVDT01NSVRfUlVO
VElNRV9GQUxTRV9BQ0NFUFRfQ09VTlQ9MApgYGAKCiMjIFJlbW90ZSBtb2RlCgpPbmx5IGFmdGVyIGFjdHVhbCBydW50aW1lIHJlc3VsdCBmaWxlcyBleGlz
dCBtYXkgYWNjZXB0YW5jZSBwcm9kdWNlOgoKYGBgdGV4dApyZXN1bHQ9UEFTUwpgYGAKClJlcXVpcmU6CgpgYGB0ZXh0ClBIQVNFNV9BQ0NFUFRBTkNFX0NI
RUNLX0NPVU5UPj0zMDAKUEhBU0U1X0FDQ0VQVEFOQ0VfQ0hFQ0tfUEFTUz1QSEFTRTVfQUNDRVBUQU5DRV9DSEVDS19DT1VOVApQSEFTRTVfQUNDRVBUQU5D
RV9DSEVDS19GQUlMPTAKClBIQVNFNV9BQ0NFUFRBTkNFX0NIRUNLX1dJVEhPVVRfUkVRVUlSRU1FTlRfSUQ9MApQSEFTRTVfQUNDRVBUQU5DRV9EVVBMSUNB
VEVfQ0hFQ0tfSURfQ09VTlQ9MApQSEFTRTVfQUNDRVBUQU5DRV9EVVBMSUNBVEVfUkVRVUlSRU1FTlRfUEFERElOR19DT1VOVD0wClBIQVNFNV9BQ0NFUFRB
TkNFX0RVUExJQ0FURV9BU1NFUlRJT05fQ09VTlQ9MAoKUEhBU0U1X0FDQ0VQVEFOQ0VfVU5LTk9XTl9FVklERU5DRV9JRF9DT1VOVD0wClBIQVNFNV9BQ0NF
UFRBTkNFX1VOUkVTT0xWRURfRVZJREVOQ0VfUkVGRVJFTkNFX0NPVU5UPTAKClBIQVNFNV9BQ0NFUFRBTkNFX1JVTlRJTUVfUkVRVUlSRURfU09VUkNFX09O
TFlfUEFTU19DT1VOVD0wCmBgYAoKLS0tCgojIDE2LiBDMDgg4oCUIEVWSURFTkNFIFZBTElEQVRPUiBNVVNUIERFVEVDVCBGQUxTRSBBQ0NFUFRTCgpSZXBh
aXIgYGV2aWRlbmNlX3ZhbGlkYXRlLnB5YC4KCkl0IG11c3Qgbm90IHRydXN0IGBjaGVja1sicmVzdWx0Il0gPT0gIlBBU1MiYCBieSBpdHNlbGYuCgpGb3Ig
ZXZlcnkgUEFTUyBwcmltYXJ5IGNoZWNrOgoxLiByZXNvbHZlIGFsbCBgZXZpZGVuY2VfaWRzYCB0aHJvdWdoIHRoZSBjZW50cmFsIHJlZ2lzdHJ5OwoyLiBy
ZXNvbHZlIHRoZSBhY3R1YWwgZXZpZGVuY2UgZmlsZXMgdW5kZXIgdGhlIHN1cHBsaWVkIGV2aWRlbmNlIGRpcmVjdG9yeTsKMy4gcHJvdmUgZXZlcnkgcmVx
dWlyZWQgcHJvZHVjZXIgZXhpc3RzOwo0LiBwcm92ZSBwcm9kdWNlciBpZGVudGl0eSBtYXRjaGVzIGNhbmRpZGF0ZS92YWxpZGF0aW9uL3J1biB3aGVuIHJ1
bnRpbWU7CjUuIHByb3ZlIHByb2R1Y2VyIHJlc3VsdCBpcyBQQVNTOwo2LiBwcm92ZSBydW50aW1lLXJlcXVpcmVkIGNoZWNrcyBjaXRlIGF0IGxlYXN0IG9u
ZSBydW50aW1lLXJlcXVpcmVkIHByb2R1Y2VyOwo3LiBwcm92ZSBydW50aW1lIHByb2R1Y2VyIHdhcyBhY3R1YWxseSBleGVjdXRlZDsKOC4gcmVqZWN0IGBO
T1RfRVhFQ1VURURgOwo5LiByZWplY3QgemVyby1ieXRlL21pc3NpbmcgcmVzdWx0IGV2aWRlbmNlOwoxMC4gcmVqZWN0IHNlbGYtcmVmZXJlbmNlIHRvIGFj
Y2VwdGFuY2UucHkgYXMgc29sZSBzdWJzdGFudGl2ZSBwcm9vZi4KCkNvbXB1dGUsIGRvIG5vdCBhc3NpZ246CgpgYGB0ZXh0CmZhbHNlX2FjY2VwdF9jb3Vu
dApydW50aW1lX3JlcXVpcmVkX3NvdXJjZV9vbmx5X3Bhc3NfY291bnQKdW5rbm93bl9ldmlkZW5jZV9pZF9jb3VudAp1bnJlc29sdmVkX2V2aWRlbmNlX3Jl
ZmVyZW5jZV9jb3VudApkdXBsaWNhdGVfYXNzZXJ0aW9uX2NvdW50CmBgYAoKUmVxdWlyZWQgcmVtb3RlOgoKYGBgdGV4dApmYWxzZV9hY2NlcHRfY291bnQ9
MApydW50aW1lX3JlcXVpcmVkX3NvdXJjZV9vbmx5X3Bhc3NfY291bnQ9MApgYGAKCkFkZCBuZWdhdGl2ZSB0ZXN0cyBzaG93aW5nIGVhY2ggYmVjb21lcyBu
b256ZXJvL2ZhaWwgd2hlbiBldmlkZW5jZSBpcyBjb3JydXB0ZWQuCgotLS0KCiMgMTcuIEMwOS9DMTAg4oCUIEZJTkFMSVpFUiBNVVNUIEZBSUwgQ0xPU0VE
IEFORCBCSU5EIEVYQUNUIFBIQVNFNSBDQU5ESURBVEUKClJlcGFpciBgZmluYWxpemUucHlgIC8gYHBoYXNlNV9maW5hbGl6ZS5weWAuCgojIyBObyBkZWZh
dWx0IHJ1bnRpbWUgUEFTUwoKVGhlIGFjY2VwdGFuY2UgZmluYWxpemVyIG11c3QgbmV2ZXIgaW5mZXIgU1FMIFNlcnZlci9icm93c2VyL3JlZ3Jlc3Npb24g
UEFTUwpmcm9tIGBldmlkZW5jZV9kaXI9Tm9uZWAuCgpGb3IgYWNjZXB0YW5jZSBtb2RlOgoKYGBgdGV4dApldmlkZW5jZV9kaXIgbWlzc2luZyA9PiBGQUlM
CnJlcXVpcmVkIHByb2R1Y2VyIG1pc3NpbmcgPT4gRkFJTApydW50aW1lIHJlc3VsdCBtaXNzaW5nID0+IEZBSUwKYGBgCgpBIGhlbHBlciB1c2VkIGZvciBu
b24tYWNjZXB0YW5jZSBhcnRpZmFjdCBjb25zdHJ1Y3Rpb24gbWF5IGV4aXN0IG9ubHkgaWYgaXQgaXMKY2xlYXJseSBuYW1lZC9ub24tYWNjZXB0YW5jZSBh
bmQgY2Fubm90IG91dHB1dCBgQ09NUExFVEVfUEFTU2AuCgojIyBFeGFjdCBleHRlcm5hbGx5IHN1cHBsaWVkIGNhbmRpZGF0ZSBpZGVudGl0eQoKQWRkIENM
SToKCmBgYGJhc2gKLS1leHBlY3RlZC1jYW5kaWRhdGUtc2hhIDw0MC1oZXggUGhhc2U1IFNIQT4KYGBgCgpSZW1vdGUgaW52b2NhdGlvbiBtdXN0IHN1cHBs
eToKCmBgYGJhc2gKLS1leHBlY3RlZC1jYW5kaWRhdGUtc2hhICIkQ0FORElEQVRFX1NIQSIKYGBgCgpUaGUgZmluYWxpemVyIG11c3QgcmVxdWlyZToKCmBg
YHRleHQKcnVudGltZSBjYW5kaWRhdGVfc2hhID09IGV4cGVjdGVkX2NhbmRpZGF0ZV9zaGEKYGBgCgpleGFjdGx5LgoKRG8gbm90IGFjY2VwdCBhcmJpdHJh
cnkgNDAtaGV4IFNIQSBtZXJlbHkgYmVjYXVzZSBpdCBpcyB3ZWxsIGZvcm1lZC4KCkRvIG5vdCB1c2UgYWNjZXB0ZWQgUGhhc2U0IFNIQSBhcyB0aGUgUGhh
c2U1IHJ1bnRpbWUgY2FuZGlkYXRlIGlkZW50aXR5LgoKYExPQ0FMX1BSRUNPTU1JVGAgbWF5IGJlIGFjY2VwdGVkIG9ubHkgaW4gYW4gZXhwbGljaXQgbG9j
YWwtdGVzdCBtb2RlLgoKQWRkIGFjdHVhbC1maW5hbGl6ZXIgdGVzdHMgZm9yOgotIGV4YWN0IG1hdGNoaW5nIHJlbW90ZS1zaGFwZWQgNDAtaGV4IGNhbmRp
ZGF0ZSA9PiBhbGxvd2VkIHdoZW4gYWxsIG90aGVyCiAgZml4dHVyZSBldmlkZW5jZSB2YWxpZDsKLSBkaWZmZXJlbnQgdmFsaWQgNDAtaGV4IGNhbmRpZGF0
ZSA9PiByZWplY3RlZDsKLSBibGFuayBleHBlY3RlZCBjYW5kaWRhdGUgPT4gcmVqZWN0ZWQ7Ci0gbWFsZm9ybWVkIGV4cGVjdGVkIGNhbmRpZGF0ZSA9PiBy
ZWplY3RlZDsKLSBtaXNzaW5nIENMSSBleHBlY3RlZCBjYW5kaWRhdGUgPT4gcmVqZWN0ZWQuCgotLS0KCiMgMTguIEMxMSDigJQgRklOQUwgU1VNTUFSWSBN
VVNUIEJFIERFUklWRUQsIE5PVCBIQVJEQ09ERUQKCkZpbmFsaXplciBtdXN0IHBhcnNlIGFjdHVhbCBldmlkZW5jZSByZXN1bHRzIGFuZCBkZXJpdmU6Cgpg
YGB0ZXh0CmJyb3dzZXJfcmVxdWlyZWRfcGF0aF9jb3VudApicm93c2VyX3JlcXVpcmVkX3BhdGhfcGFzcwpicm93c2VyX3JlcXVpcmVkX3BhdGhfZmFpbAoK
c3Fsc2VydmVyX3ZhbGlkYXRpb25fcmVzdWx0CnNxbHNlcnZlcl9tYWpvcgptaWdyYXRpb25faGVhZAoKY3JpdGljYWxfZmFsc2VfcHJvbW90aW9ucwoKc2hh
ZG93X3N0YXRlCnByb21vdGlvbl9yZXF1aXJlc19odW1hbl9yZXZpZXcKcHJvamVjdGlvbl9yZXF1aXJlc19leGlzdGluZ192ZXJpZmllZF9hc3NlcnRpb24K
CmJhY2tlbmRfcmVncmVzc2lvbgpmcm9udGVuZF9yZWdyZXNzaW9uCmZyb250ZW5kX2J1aWxkCgpuZXdfc291cmNlX3JlYWRzCmF1dG9fcHJvbW90aW9uX2Vu
YWJsZWQKbGxtX3JlYWxfY29udGVudF9tb2RlCmxsbV9leHRlcm5hbF9jYWxsX2NvdW50CmBgYAoKRG8gbm90IGVtaXQ6CgpgYGB0ZXh0CmJyb3dzZXJfcmVx
dWlyZWRfcGF0aF9wYXNzPTEwCnNxbHNlcnZlcl92YWxpZGF0aW9uX3Jlc3VsdD1QQVNTCmNyaXRpY2FsX2ZhbHNlX3Byb21vdGlvbnM9MApgYGAKCnVubGVz
cyB0aG9zZSBleGFjdCB2YWx1ZXMgd2VyZSByZWFkL3ZhbGlkYXRlZCBmcm9tIGFjdHVhbCBldmlkZW5jZS4KCmBoYW5kb2ZmX3N0YXRlPVJFQURZX0ZPUl9J
TkRFUEVOREVOVF9QSEFTRTVfQUNDRVBUQU5DRWAgaXMgcGVybWl0dGVkIG9ubHkgYWZ0ZXIKYWxsIHJlcXVpcmVkIGV2aWRlbmNlIGlzIGNvbXBsZXRlIGFu
ZCBhY2NlcHRhbmNlIHZhbGlkYXRvciByZXBvcnRzIHplcm8gZmFsc2UKYWNjZXB0cy4KCi0tLQoKIyAxOS4gQzEyIOKAlCBSRVBST0RVQ0lCSUxJVFkgTVVT
VCBSRUdFTkVSQVRFCgpSZXBhaXIgYHJlcHJvZHVjaWJpbGl0eS5weWAuCgpJdCBtdXN0IG5vdCBoYXNoIHRoZSBzYW1lIGFscmVhZHktd3JpdHRlbiBmaWxl
cyB0d2ljZS4KCkNyZWF0ZSB0d28gaW5kZXBlbmRlbnQgdGVtcG9yYXJ5IHJlZ2VuZXJhdGlvbiByb290cyBmcm9tIHRoZSBzYW1lIGV4YWN0IHNvdXJjZQpi
eXRlcyBhbmQgcmVydW4gZGV0ZXJtaW5pc3RpYyBQaGFzZTUgZ2VuZXJhdG9ycyBmb3IgdGhlIGNsYXNzaWZpZXIvZnJlZXplCmFydGlmYWN0IGZhbWlsaWVz
IHRoYXQgYXJlIGludGVuZGVkIHRvIGJlIHJlcHJvZHVjaWJsZS4KCkF0IG1pbmltdW0gaW5kZXBlbmRlbnRseSByZWdlbmVyYXRlIGFuZCBjb21wYXJlOgoK
YGBgdGV4dAppbnB1dCBpZGVudGl0eQpyb2J1c3RuZXNzIGNvcnB1cwpjYWxpYnJhdGlvbiBtYW5pZmVzdAp2YWxpZGF0aW9uIG1hbmlmZXN0CmhvbGRvdXQv
YWR2ZXJzYXJpYWwgbWFuaWZlc3QKY2FsaWJyYXRpb24gcmVzdWx0cwp2YWxpZGF0aW9uIHJlc3VsdHMKaG9sZG91dCByZXN1bHRzCmNyb3NzLWNvbnRleHQg
cmVzdWx0cwpwYXRoLWNvdW50ZXJmYWN0dWFsIHJlc3VsdHMKYGBgCgpBbHNvIHJlY29tcHV0ZSBhbmQgdmVyaWZ5IGV2ZXJ5IGZyZWV6ZS1tYW5pZmVzdCBy
ZWZlcmVuY2VkIFNIQSB3aGljaCBkZXBlbmRzIG9uCnRob3NlIGRldGVybWluaXN0aWMgZmlsZXMvY2xhc3NpZmllci9ydWxlcy4KClJlcXVpcmU6Ci0gcmVn
ZW5lcmF0aW9uIEEgPT0gcmVnZW5lcmF0aW9uIEI7Ci0gcmVnZW5lcmF0aW9uIEEgPT0gY29tbWl0dGVkIGNhbm9uaWNhbCBieXRlczsKLSBldmVyeSByZWZl
cmVuY2VkIFNIQSBtYXRjaGVzOwotIG5vIHdhbGwtY2xvY2svdGVtcG9yYXJ5IHBhdGggbGVha3M7Ci0gbm8gcmVjdXJzaXZlIHNlbGYtaGFzaC4KCk91dHB1
dCBhY3R1YWwgbWlzbWF0Y2ggbGlzdHMuCgpSZXF1aXJlIHJlbW90ZToKCmBgYHRleHQKUkVNT1RFX0NMQVNTSUZJRVJfRlJFRVpFX1JFUFJPRFVDSUJJTElU
WT1QQVNTClJFTU9URV9DTEFTU0lGSUVSX1JFU1VMVF9IQVNIX01JU01BVENIX0NPVU5UPTAKUkVNT1RFX0NBTk9OSUNBTF9BUlRJRkFDVF9NSVNTSU5HX0NP
VU5UPTAKUkVNT1RFX0ZSRUVaRV9SRUZFUkVOQ0VfTUlTTUFUQ0hfQ09VTlQ9MApgYGAKClRoZSBjbGFzc2lmaWVyL3J1bGVzL2NvcnB1cyBjb21taXR0ZWQg
Ynl0ZXMgcmVtYWluIHVuY2hhbmdlZCBmcm9tIFIyLgoKLS0tCgojIDIwLiBGSU5BTElaRVIgTkVHQVRJVkUgU1VJVEUg4oCUIEVYUEFORCwgRE8gTk9UIFdF
QUtFTgoKUmV0YWluIHRoZSBleGlzdGluZyBhY3R1YWwtZmluYWxpemVyIG5lZ2F0aXZlIHRlc3RzIGFuZCBhZGQgY292ZXJhZ2UgZm9yIHRoZQpuZXcgZXZp
ZGVuY2UgdHJ1dGggY29udHJhY3QuCgpBdCBtaW5pbXVtIGFjdHVhbCBDTEkgZmluYWxpemVyIG11c3QgcmVqZWN0OgoKYGBgdGV4dAptaXNzaW5nIGV2aWRl
bmNlIGRpcmVjdG9yeQptaXNzaW5nIHJlcXVpcmVkIHByb2R1Y2VyCmZhaWxlZCBwcm9kdWNlcgpwcm9kdWNlciBOT1RfRVhFQ1VURUQKcHJvZHVjZXIgY2Fu
ZGlkYXRlIFNIQSBtaXNtYXRjaApwcm9kdWNlciB2YWxpZGF0aW9uIFNIQSBtaXNtYXRjaApwcm9kdWNlciBydW4gSUQgbWlzbWF0Y2gKYmxhbmsvbm9uaW50
ZWdlciBleGl0IGNvZGUKemVyby1ieXRlIHJlcXVpcmVkIHJhdyBsb2cKZmFpbGVkIGFjY2VwdGFuY2UKZHVwbGljYXRlIGNoZWNrIElECmR1cGxpY2F0ZSBu
b3JtYWxpemVkIGFzc2VydGlvbgptaXNzaW5nIHJlcXVpcmVtZW50IElECnJ1bnRpbWUtcmVxdWlyZWQgc291cmNlLW9ubHkgUEFTUwpmYWxzZS1hY2NlcHQg
ZXZpZGVuY2UgbWFwcGluZwpjcml0aWNhbCBmYWxzZSBwcm9tb3Rpb24KbmV3IHNvdXJjZSByZWFkcyA+IDAKYXV0byBwcm9tb3Rpb24gZW5hYmxlZApMTE0g
cmVhbCBjb250ZW50IGVuYWJsZWQKYnJvd3NlciBldmlkZW5jZSBtaXNzaW5nL2ZhaWwvc2tpcApTUUwgU2VydmVyIGV2aWRlbmNlIG1pc3NpbmcvZmFpbApm
cmVlemUgZGlnZXN0IG1pc21hdGNoCnVucmVzb2x2ZWQgZXZpZGVuY2UKc2VjcmV0IGh5Z2llbmUgZmFpbHVyZQpjYW5kaWRhdGUgU0hBIG1pc21hdGNoCm1h
bGZvcm1lZCBleHBlY3RlZCBjYW5kaWRhdGUgU0hBCmBgYAoKUmVxdWlyZToKCmBgYHRleHQKUEhBU0U1X0ZJTkFMSVpFUl9ORUdBVElWRV9GSVhUVVJFX0NP
VU5UPj0yNQpQSEFTRTVfRklOQUxJWkVSX05FR0FUSVZFX0ZBTFNFX0FDQ0VQVF9DT1VOVD0wClBIQVNFNV9GSU5BTElaRVJfTkVHQVRJVkVfVEVTVFNfSU5W
T0tFX0FDVFVBTF9GSU5BTElaRVI9dHJ1ZQpQSEFTRTVfRklOQUxJWkVSX0hFTFBFUl9PTkxZX05FR0FUSVZFX1RFU1RfQ09VTlQ9MApgYGAKCi0tLQoKIyAy
MS4gQlJPV1NFUiBTUEVDIFFVQUxJVFkg4oCUIEFDVFVBTCBURVNUUywgTk9UIFBZVEhPTiBGTEFHUwoKUHJlc2VydmUgdGhlIHRlbiByZXF1aXJlZCBidXNp
bmVzcyBwYXRoIElEcy4KCkFkZCBhY3R1YWwgY2hlY2tzLCB1c2luZyB0aGUgcmVhbCBmcm9udGVuZC9iYWNrZW5kIHdoZXJlIGFwcHJvcHJpYXRlLCBmb3I6
Ci0gaW5pdGlhbCBsb2FkaW5nIHN0YXRlOwotIGVtcHR5IHN0YXRlIGFnYWluc3QgZnJlc2ggcHJlLVBoYXNlNSBxdWV1ZSB3aGVuIGRldGVybWluaXN0aWNh
bGx5IGF2YWlsYWJsZTsKLSBlcnJvciBzdGF0ZSB2aWEgYSB0ZXN0LW9ubHkvbm9uLWJ1c2luZXNzIHRyYW5zcG9ydCBmYWlsdXJlIG1lY2hhbmlzbSB0aGF0
CiAgZG9lcyBub3QgbW9jayBhIHN1Y2Nlc3NmdWwgUHJvcG9zYWxPcHMgYnVzaW5lc3MgcmVzcG9uc2U7Ci0ga2V5Ym9hcmQtYWNjZXNzaWJsZSByZXZpZXcg
YWN0aW9uczsKLSBiYXNpYyBhY2Nlc3NpYmxlIHJvbGVzL25hbWVzOwotIGRlZXAtbGluayByb3V0ZSByZXNvbHV0aW9uOwotIHZpc2libGUgY29ycmVsYXRp
b24gSUQ7Ci0gdmlzaWJsZSByb290IGV2ZW50LgoKSWYgYSBxdWFsaXR5IHRlc3QgdXNlcyBuZXR3b3JrIGludGVyY2VwdGlvbiBvbmx5IHRvIGluZHVjZSBh
biBlcnJvciwgaXQgbXVzdApub3QgZmFicmljYXRlIGEgc3VjY2Vzc2Z1bCBidXNpbmVzcyByZXNwb25zZSBhbmQgbXVzdCBiZSBleGNsdWRlZCBmcm9tIHRo
ZQpyZXF1aXJlZC1wYXRoIEFQSSBtb2NrIGNvdW50LgoKTm8gYXBwbGljYXRpb24gdHJ1dGggbWF5IGJlIG1vY2tlZC4KCi0tLQoKIyAyMi4gUFJFU0VSVkUg
WkVSTy1TQ0hFTUEtREVMVEEKClIzIG11c3QgcmV0YWluOgoKYGBgdGV4dApQSEFTRTVfTUlHUkFUSU9OX1JFUVVJUkVEPWZhbHNlCkRBVEFCQVNFX1NDSEVN
QV9ERUxUQT0wCgpBQ1RJVkVfTUlHUkFUSU9OX0hFQUQ9CmJhc2VsaW5lX3BoYXNlNF92MzZfYXp1cmVfc3FsCmBgYAoKTm8gbW9kZWwvbWlncmF0aW9uIGNo
YW5nZXMuCgotLS0KCiMgMjMuIExPQ0FMIFBSRUNPTU1JVCBFVklERU5DRSBDT05UUkFDVAoKQmVmb3JlIGFwcGxpY2F0aW9uIGNvbW1pdCBjcmVhdGUgdGVt
cG9yYXJ5IHByZWNvbW1pdCBldmlkZW5jZS4KClJ1bnRpbWUgcHJvZHVjZXJzIG11c3QgYmUgZXhwbGljaXRseToKCmBgYHRleHQKTk9UX0VYRUNVVEVECmBg
YAoKUnVuOgotIHNvdXJjZSBwcmVmbGlnaHQgVjM7Ci0gZGV0ZXJtaW5pc3RpYyByZWdlbmVyYXRpb247Ci0gZXZpZGVuY2UtcmVnaXN0cnkvcmVmZXJlbmNl
IGRyeSBydW47Ci0gYWNjZXB0YW5jZSBkcnkgcnVuOwotIGZpbmFsaXplciBwb3NpdGl2ZSBsb2NhbCBmaXh0dXJlOwotID49MjUgYWN0dWFsLWZpbmFsaXpl
ciBuZWdhdGl2ZSBmaXh0dXJlcy4KClJlcXVpcmU6CgpgYGB0ZXh0ClBIQVNFNV9QUkVDT01NSVRfUlVOVElNRV9GQUxTRV9BQ0NFUFRfQ09VTlQ9MApQSEFT
RTVfQUNDRVBUQU5DRV9SRUZFUkVOQ0VfRFJZX1JVTj1QQVNTClBIQVNFNV9GSU5BTElaRVJfTkVHQVRJVkVfRkFMU0VfQUNDRVBUX0NPVU5UPTAKYGBgCgpE
ZWxldGUgdGVtcG9yYXJ5IGV2aWRlbmNlIGJlZm9yZSBzdGFnaW5nLgoKLS0tCgojIDI0LiBXSE9MRS1TVVJGQUNFIFIzIE5PLUxPT1AgQVVESVQKCkJlZm9y
ZSB0aGUgb25lIGFwcGxpY2F0aW9uIGNvbW1pdCwgcGVyZm9ybSBhIGZyZXNoIGluZGVwZW5kZW50IHNvdXJjZSBhdWRpdCBvdmVyCnRoZSBlbnRpcmUgUGhh
c2U1IGNhbmRpZGF0ZSBzdXJmYWNlIGFuZCBpbmhlcml0ZWQgY29uc3VtZXJzLgoKUmUtYWRqdWRpY2F0ZSBldmVyeSBSdW4tMTAgZGVmZWN0IGFuZCB3b3Jr
ZmxvdyBkZWZlY3QuCgpSZXF1aXJlOgoKYGBgdGV4dApDMDFfU09VUkNFX1BSRUZMSUdIVF9IQVJEQ09ERURfRklFTERTPUNMT1NFRApDMDJfRklYRURfU0hB
X0RFU0NFTkRBTlRfQVVESVRfSU5DT01QTEVURT1DTE9TRUQKQzAzX0JST1dTRVJfRVZJREVOQ0VfSEFSRENPREVEX1BBU1M9Q0xPU0VECkMwNF9TUUxTRVJW
RVJfRVZJREVOQ0VfSEFSRENPREVEX1BBU1M9Q0xPU0VECkMwNV9TSEFET1dfUkVQTEFZX0hBUkRDT0RFRF9QQVNTPUNMT1NFRApDMDZfQUNDRVBUQU5DRV9H
RU5FUkFUT1JfSEFSRENPREVEX1BBU1M9Q0xPU0VECkMwN19BQ0NFUFRBTkNFX0VWSURFTkNFX1NFTEZfUkVGRVJFTlRJQUw9Q0xPU0VECkMwOF9FVklERU5D
RV9WQUxJREFUT1JfU0VNQU5USUNfR0FQPUNMT1NFRApDMDlfRklOQUxJWkVSX0RFRkFVTFRfUlVOVElNRV9QQVNTPUNMT1NFRApDMTBfRklOQUxJWkVSX0NB
TkRJREFURV9TSEFfTk9UX0VYQUNUPUNMT1NFRApDMTFfRklOQUxJWkVSX1NVTU1BUllfSEFSRENPREVEX1JVTlRJTUU9Q0xPU0VECkMxMl9SRVBST0RVQ0lC
SUxJVFlfTk9UX1JFR0VORVJBVEVEPUNMT1NFRAoKVzAxX0lOVkFMSURfU1FMU0VSVkVSX0lNQUdFX1RBRz1DTE9TRUQKVzAyX1NRTFNFUlZFUl9QQVNTV09S
RF9OT1RfRVhQT1JURUQ9Q0xPU0VEClcwM19JTl9DT05UQUlORVJfU1FMQ01EX0JPT1RTVFJBUD1DTE9TRUQKVzA0X1BMQVlXUklHSFRfQlJPV1NFUl9OT1Rf
RVhQTElDSVRMWV9JTlNUQUxMRUQ9Q0xPU0VECgpLTk9XTl9ORVhUX0RFVEVSTUlOSVNUSUNfQkxPQ0tFUl9DT1VOVD0wCmBgYAoKVGhlIGF1ZGl0IG11c3Qg
aW5zcGVjdCBleGVjdXRhYmxlIGNvZGUsIG5vdCBtZXJlbHkgc2VhcmNoIGZvciB0aGVzZSBvdXRwdXQKc3RyaW5ncy4KCklmIGEgZGVmaW5pdGUgYmxvY2tl
ciByZW1haW5zIGluc2lkZSB0aGUgYXV0aG9yaXplZCBzdXJmYWNlLCByZXBhaXIgaXQgYmVmb3JlCnRoZSBmaXJzdCBhcHBsaWNhdGlvbiBjb21taXQuCgpJ
ZiBpdCByZXF1aXJlcyBhbiB1bmF1dGhvcml6ZWQgcGF0aDoKCmBgYHRleHQKUkVTVUxUPVNUT1BfUEhBU0U1X1IzX0FERElUSU9OQUxfU0NPUEVfUkVRVUlS
RUQKYGBgCgpTVE9QIGJlZm9yZSBjb21taXQuCgotLS0KCiMgMjUuIExPQ0FMIEFQUExJQ0FUSU9OIFZBTElEQVRJT04KClJ1biBhbGwgaW1wYWN0ZWQgdGVz
dHMgYW5kIGZ1bGwgcmVncmVzc2lvbnMuCgpBdCBtaW5pbXVtOgoKYGBgYmFzaApweXRlc3QgLXEgXAogIGJhY2tlbmQvdGVzdHMvdGVzdF9waGFzZTVfY29u
dHJhY3RzLnB5IFwKICBiYWNrZW5kL3Rlc3RzL3Rlc3RfcGhhc2U1X2ZpbmFsaXplcl9uZWdhdGl2ZS5weSBcCiAgYmFja2VuZC90ZXN0cy90ZXN0X3BoYXNl
NV9ldmlkZW5jZV9pbnRlZ3JpdHkucHkgXAogIGJhY2tlbmQvdGVzdHMvdGVzdF9waGFzZTVfc3Fsc2VydmVyX3J1bnRpbWUucHkgXAogIGJhY2tlbmQvdGVz
dHMvdGVzdF9waGFzZTVfY2xhc3NpZmllci5weSBcCiAgYmFja2VuZC90ZXN0cy90ZXN0X3BoYXNlNV9wb3J0YWJpbGl0eS5weQoKcHl0ZXN0IC1xIGJhY2tl
bmQvdGVzdHMvdGVzdF9waGFzZTRfY29ycHVzX2FwcF9pbnRlZ3JhdGlvbi5weQoKcHl0ZXN0IC1xCgpweXRob24gLW0gY29tcGlsZWFsbCAtcSBiYWNrZW5k
IHNjcmlwdHMKCnB5dGhvbiBzY3JpcHRzL3BoYXNlNS9zb3VyY2VfcHJlZmxpZ2h0LnB5CnB5dGhvbiBzY3JpcHRzL3BoYXNlNS9yZXByb2R1Y2liaWxpdHku
cHkKCmdpdCBkaWZmIC0tY2hlY2sKYGBgCgpGcm9udGVuZDoKCmBgYGJhc2gKY2QgZnJvbnRlbmQKbnBtIGNpCm5wbSB0ZXN0IC0tIC0tcnVuCm5weCB0c2Mg
LWIKbnB4IHZpdGUgYnVpbGQKbnB4IHBsYXl3cmlnaHQgdGVzdCBcCiAgYnJvd3Nlci1yZWFsLXN0YWNrL3BoYXNlNS1jbGFzc2lmaWVyLXNoYWRvdy5zcGVj
LnRzIFwKICAtLWNvbmZpZz1wbGF5d3JpZ2h0LnJlYWwtc3RhY2suY29uZmlnLnRzIFwKICAtLWxpc3QKYGBgCgpSZXF1aXJlIGFsbCBmYWlsdXJlcyB6ZXJv
LgoKRG8gbm90IGNsYWltIFNRTCBTZXJ2ZXIvYnJvd3NlciBydW50aW1lIHByb29mIGZyb20gdGhlc2UgbG9jYWwgdGVzdHMuCgotLS0KCiMgMjYuIEFQUExJ
Q0FUSU9OIERJRkYgR0FURQoKQmVmb3JlIGNvbW1pdDoKCmBgYHRleHQKUEhBU0U1X1IzX0FQUExJQ0FUSU9OX1BBUkVOVD0KY2E2MDQ1OWYyMTAzY2JmMzBl
NTJlMDVjNTliOGFmNmQ3NzE0YmUxMgpgYGAKCkNoYW5nZWQgcGF0aHMgbXVzdCBiZSBhIHN1YnNldCBvZiBTZWN0aW9uIDggb25seS4KClJlcXVpcmUgY2xh
c3NpZmllci9mcmVlemUgcHJvdGVjdGVkIGJ5dGVzIHVuY2hhbmdlZCBmcm9tIFIyLgoKUmVxdWlyZToKCmBgYHRleHQKUEhBU0U1X1IzX0NMQVNTSUZJRVJf
QkVIQVZJT1JfUEFUSF9DSEFOR0VfQ09VTlQ9MApQSEFTRTVfUjNfUEhBU0U0X1BBVEhfQ0hBTkdFX0NPVU5UPTAKUEhBU0U1X1IzX01JR1JBVElPTl9NT0RF
TF9DSEFOR0VfQ09VTlQ9MApQSEFTRTVfUjNfVU5BVVRIT1JJWkVEX1BBVEhfQ09VTlQ9MApgYGAKCk5vIGdlbmVyYXRlZCBgYXJ0aWZhY3RzLyoqYCBmaWxl
cyBzdGFnZWQuCgotLS0KCiMgMjcuIENSRUFURSBFWEFDVExZIE9ORSBSMyBBUFBMSUNBVElPTiBDT01NSVQKCkNyZWF0ZSBvbmUgY29tbWl0IG9uOgoKYGBg
dGV4dApwaGFzZTUtY2xhc3NpZmllci1zaGFkb3ctdmFsaWRhdGlvbi1yMy12MQpgYGAKClBhcmVudCBleGFjdGx5OgoKYGBgdGV4dApjYTYwNDU5ZjIxMDNj
YmYzMGU1MmUwNWM1OWI4YWY2ZDc3MTRiZTEyCmBgYAoKUmVjb21tZW5kZWQgbWVzc2FnZToKCmBgYHRleHQKZml4KHBoYXNlNSk6IGJpbmQgYWNjZXB0YW5j
ZSB0byBhY3R1YWwgcnVudGltZSBldmlkZW5jZQpgYGAKClJlY29yZDoKCmBgYHRleHQKUEhBU0U1X1IzX0NBTkRJREFURV9TSEE9PGV4YWN0PgpQSEFTRTVf
UjNfQ0FORElEQVRFX1RSRUU9PGV4YWN0PgpgYGAKClB1c2ggb25seSB0aGlzIGFwcGxpY2F0aW9uIGJyYW5jaC4KCkFmdGVyIHB1c2g6CgpgYGB0ZXh0ClNF
Q09ORF9BUFBMSUNBVElPTl9DT01NSVRfQVVUSE9SSVpFRD1mYWxzZQpgYGAKCi0tLQoKIyAyOC4gQ1JFQVRFIEZSRVNIIFZBTElEQVRJT04gQlJBTkNIIERJ
UkVDVExZIEZST00gUjMgQ0FORElEQVRFCgpDcmVhdGU6CgpgYGB0ZXh0ClBIQVNFNV9SM19WQUxJREFUSU9OX0JSQU5DSD0KcGhhc2U1LWNsYXNzaWZpZXIt
c2hhZG93LXZhbGlkYXRpb24tY2ktcjMtdjEKYGBgCgpkaXJlY3RseSBmcm9tIGV4YWN0OgoKYGBgdGV4dApQSEFTRTVfUjNfQ0FORElEQVRFX1NIQQpgYGAK
CkRvIG5vdCBicmFuY2ggZnJvbSBgMzg0MmZjMC4uLmAuCgpDcmVhdGUgZXhhY3RseSBvbmUgd29ya2Zsb3ctb25seSBjaGlsZCBjb21taXQuCgotLS0KCiMg
MjkuIFdPUktGTE9XIFNPVVJDRSBBVVRIT1JJVFkKClVzZSB0aGUgZXhhY3QgZmFpbGVkIFIyIHdvcmtmbG93IGFzIHN0cnVjdHVyYWwgc291cmNlOgoKYGBg
dGV4dApTT1VSQ0VfVkFMSURBVElPTl9TSEE9CjM4NDJmYzBmYWY0Yzk1YmY5MzNkMGE1NmNkODc3MzE2MmU5N2Y4OTMKClNPVVJDRV9XT1JLRkxPV19QQVRI
PQouZ2l0aHViL3dvcmtmbG93cy9waGFzZTUtY2xhc3NpZmllci1zaGFkb3ctdmFsaWRhdGlvbi1jaS55bWwKClNPVVJDRV9XT1JLRkxPV19CTE9CX1NIQTE9
CjAzZGZiZTE0NGU5YTBlNjFiN2RkYzY0OGViZTljYzhjZjcxMWY1NjAKYGBgCgpDcmVhdGUgZnJlc2ggd29ya2Zsb3cgcGF0aDoKCmBgYHRleHQKLmdpdGh1
Yi93b3JrZmxvd3MvcGhhc2U1LWNsYXNzaWZpZXItc2hhZG93LXZhbGlkYXRpb24tY2ktcjMueW1sCmBgYAoKUHJlc2VydmU6Ci0gZXhhY3QgY2FuZGlkYXRl
L3BhcmVudC9icmFuY2ggYmluZGluZyBwYXR0ZXJuOwotIFVidW50dSB4NjQgcHJvb2Y7Ci0gT0RCQyBpbnN0YWxsIGFwcHJvYWNoIHRoYXQgYWxyZWFkeSBw
YXNzZWQ7Ci0gZGVwZW5kZW5jeSBpbnN0YWxsYXRpb247Ci0gcmF3L21ldGEgZXZpZGVuY2Ugd3JhcHBlcjsKLSBhbHdheXMtb24gY2xlYW51cDsKLSBjcmVk
ZW50aWFsLWZyZWUgYXJ0aWZhY3QgdXBsb2FkLgoKQXBwbHkgYWxsIFIzIHJlcGFpcnMgYmVsb3cuCgotLS0KCiMgMzAuIFdPUktGTE9XIEJJTkRJTkcKClNl
dCBleGFjdDoKCmBgYHRleHQKQ0FORElEQVRFX1NIQT08UEhBU0U1X1IzX0NBTkRJREFURV9TSEE+CgpDQU5ESURBVEVfQlJBTkNIPQpwaGFzZTUtY2xhc3Np
Zmllci1zaGFkb3ctdmFsaWRhdGlvbi1yMy12MQoKVkFMSURBVElPTl9CUkFOQ0g9CnBoYXNlNS1jbGFzc2lmaWVyLXNoYWRvdy12YWxpZGF0aW9uLWNpLXIz
LXYxCmBgYAoKUmVxdWlyZSByZW1vdGUgYnJhbmNo4oaSY2FuZGlkYXRlIFNIQSBhbmQgdmFsaWRhdGlvbiBwYXJlbnTihpJjYW5kaWRhdGUgU0hBLgoKVmFs
aWRhdGlvbiBkaWZmIG11c3QgZXF1YWwgZXhhY3RseToKCmBgYHRleHQKLmdpdGh1Yi93b3JrZmxvd3MvcGhhc2U1LWNsYXNzaWZpZXItc2hhZG93LXZhbGlk
YXRpb24tY2ktcjMueW1sCmBgYAoKTm8gb3RoZXIgdmFsaWRhdGlvbi1jaGlsZCBwYXRoLgoKLS0tCgojIDMxLiBTUUwgU0VSVkVSIElNQUdFIOKAlCBDVVJS
RU5UIFNVUFBPUlRFRCBUQUcgKyBXSVRISU4tUlVOIERJR0VTVCBGUkVFWkUKClVzZToKCmBgYHRleHQKU1FMU0VSVkVSX0lNQUdFX1RBRz0KbWNyLm1pY3Jv
c29mdC5jb20vbXNzcWwvc2VydmVyOjIwMjItbGF0ZXN0CmBgYAoKRXhwbGljaXRseToKCmBgYGJhc2gKZG9ja2VyIHB1bGwgLS1wbGF0Zm9ybSBsaW51eC9h
bWQ2NCAiJFNRTFNFUlZFUl9JTUFHRV9UQUciCmBgYAoKUmVzb2x2ZSB0aGUgcHVsbGVkIHJlcG8gZGlnZXN0OgoKYGBgYmFzaApTUUxTRVJWRVJfSU1BR0Vf
UkVQT0RJR0VTVD0iJCgKICBkb2NrZXIgaW1hZ2UgaW5zcGVjdCAiJFNRTFNFUlZFUl9JTUFHRV9UQUciIFwKICAgIC0tZm9ybWF0ICd7e2luZGV4IC5SZXBv
RGlnZXN0cyAwfX0nCikiCmBgYAoKUmVxdWlyZToKCmBgYHRleHQKbWNyLm1pY3Jvc29mdC5jb20vbXNzcWwvc2VydmVyQHNoYTI1Njo8NjQgaGV4PgpgYGAK
ClRoZW4gcnVuIHRoZSBTUUwgU2VydmVyIGNvbnRhaW5lciB1c2luZyB0aGUgZXhhY3QgcmVzb2x2ZWQgUmVwb0RpZ2VzdCwgbm90IHRoZQptdXRhYmxlIHRh
Zy4KClJlY29yZCBib3RoIHRhZyBhbmQgUmVwb0RpZ2VzdCBpbiBjcmVkZW50aWFsLWZyZWUgZXZpZGVuY2UuCgpXb3JrZmxvdyBzb3VyY2UgbXVzdCBjb250
YWluIHplcm8gYWN0aXZlIG9jY3VycmVuY2VzIG9mOgoKYGBgdGV4dAptY3IubWljcm9zb2Z0LmNvbS9tc3NxbC9zZXJ2ZXI6MjAyMi1HQS11YnVudHUtMjAu
MDQKYGBgCgotLS0KCiMgMzIuIFNRTCBTRVJWRVIgUEFTU1dPUkQg4oCUIE1BU0sgKyBFWFBPUlQgKyBGVVRVUkUtU1RFUCBQRVJTSVNURU5DRQoKR2VuZXJh
dGUgYSBzdHJvbmcgcmFuZG9tIHBhc3N3b3JkLgoKUmVxdWlyZWQgb3JkZXIgaW4gc2FtZSBzdGVwOgoKYGBgdGV4dApnZW5lcmF0ZQrihpIgbWFzawrihpIg
ZXhwb3J0IFNRTFNFUlZFUl9QQVNTV09SRArihpIgd3JpdGUgU1FMU0VSVkVSX1BBU1NXT1JEIHRvIEdJVEhVQl9FTlYK4oaSIGhvc3QgcHlvZGJjIGJvb3Rz
dHJhcArihpIgREFUQUJBU0VfVVJMIGNvbnN0cnVjdGlvbgpgYGAKClJlcXVpcmU6CgpgYGB0ZXh0ClNRTFNFUlZFUl9QQVNTV09SRF9FWFBPUlRfQ09VTlQ9
MQpTUUxTRVJWRVJfUEFTU1dPUkRfR0lUSFVCX0VOVl9XUklURV9DT1VOVD0xClNRTFNFUlZFUl9QQVNTV09SRF9QTEFJTlRFWFRfRVZJREVOQ0VfTUFUQ0hf
Q09VTlQ9MApgYGAKCi0tLQoKIyAzMy4gU1FMIFNFUlZFUiBCT09UU1RSQVAg4oCUIEhPU1QgUFlPREJDLCBOT1QgQ09OVEFJTkVSIFNRTENNRAoKRG8gbm90
IHVzZSBjb250YWluZXItaW50ZXJuYWwgYHNxbGNtZGAgZm9yIHRoZSBib290c3RyYXAvcmVhZGluZXNzIGNvbnRyYWN0LgoKVXNlIHRoZSBhbHJlYWR5LWlu
c3RhbGxlZCBob3N0OgoKYGBgdGV4dApPREJDIERyaXZlciAxOCBmb3IgU1FMIFNlcnZlcgpweW9kYmMKYGBgCgpSdW4gYSBib3VuZGVkIHJldHJ5IHByb2Jl
IGFnYWluc3QgbWFzdGVyLgoKUmVxdWlyZSBhY3R1YWwgcXVlcmllczoKCmBgYHRleHQKU0VMRUNUIDEKU0VMRUNUIFNFUlZFUlBST1BFUlRZKCdQcm9kdWN0
TWFqb3JWZXJzaW9uJykKYGBgCgpSZXF1aXJlOgoKYGBgdGV4dApTUUxTRVJWRVJfTUFKT1I9MTYKYGBgCgpXaXRoIHB5b2RiYyBgYXV0b2NvbW1pdD1UcnVl
YCwgY3JlYXRlOgoKYGBgdGV4dApwaGFzZTVkYgpgYGAKCmlmIGFic2VudC4KClRoZW4gYnVpbGQ6CgpgYGB0ZXh0Cm1zc3FsK3B5b2RiYzovLy4uLgpgYGAK
CmBEQVRBQkFTRV9VUkxgIGZvciBgcGhhc2U1ZGJgIGFuZCBwZXJzaXN0IHRvIGBHSVRIVUJfRU5WYC4KClJlcXVpcmUgc291cmNlIHByZWZsaWdodDoKCmBg
YHRleHQKSU5fQ09OVEFJTkVSX1NRTENNRF9CT09UU1RSQVBfQ09VTlQ9MApIT1NUX1BZT0RCQ19TUUxTRVJWRVJfQk9PVFNUUkFQX0NPVU5UPTEKYGBgCgot
LS0KCiMgMzQuIFBMQVlXUklHSFQgQlJPV1NFUiBJTlNUQUxMIOKAlCBFWFBMSUNJVAoKQWZ0ZXIgYG5wbSBjaWAgcnVuOgoKYGBgYmFzaApjZCBmcm9udGVu
ZApucHggcGxheXdyaWdodCBpbnN0YWxsIC0td2l0aC1kZXBzIGNocm9taXVtCmBgYAoKQ2FwdHVyZSByYXcvbWV0YSBldmlkZW5jZS4KClJlcXVpcmU6Cgpg
YGB0ZXh0ClBMQVlXUklHSFRfQ0hST01JVU1fSU5TVEFMTD1QQVNTCmBgYAoKRG8gbm90IGFzc3VtZSBicm93c2VyIGJpbmFyaWVzIGZyb20gbnBtIHBhY2th
Z2UgaW5zdGFsbGF0aW9uLgoKLS0tCgojIDM1LiBSMyBSRU1PVEUgRVhFQ1VUSU9OIE9SREVSCgpVc2UgYSBzaW5nbGUgZnJlc2ggcnVuLgoKUmVxdWlyZWQg
aGlnaC1sZXZlbCBvcmRlcjoKCmBgYHRleHQKMSBjYW5kaWRhdGUvd29ya2Zsb3cgaWRlbnRpdHkKMiBVYnVudHUgeDY0ICsgRG9ja2VyCjMgUHl0aG9uL05v
ZGUvZGVwZW5kZW5jaWVzL09EQkMKNCBleHBsaWNpdCBQbGF5d3JpZ2h0IENocm9taXVtIGluc3RhbGwKNSBTUUwgU2VydmVyIGltYWdlIHB1bGwgKyBkaWdl
c3QgZnJlZXplCjYgU1FMIFNlcnZlciBob3N0LXB5b2RiYyByZWFkaW5lc3MvdmVyc2lvbiArIGZyZXNoIERCCjcgQWxlbWJpYyBtaWdyYXRpb24gKyBzeW50
aGV0aWMgc2VlZCArIGhlYWQgY2hlY2sKOCBzb3VyY2UgcHJlZmxpZ2h0IFYzCjkgZGV0ZXJtaW5pc3RpYyBjb3JwdXMvZXZhbHVhdGlvbi9mcmVlemUgcmVn
ZW5lcmF0aW9uIHByb29mCjEwIGFjdHVhbCBTUUwgU2VydmVyIHRhcmdldGVkIGV2aWRlbmNlCjExIGFjdHVhbCBTSEFET1cgcmVwbGF5IGV2aWRlbmNlCjEy
IHRhcmdldGVkICsgUGhhc2U0IGludGVncmF0aW9uICsgZnVsbCBiYWNrZW5kIHJlZ3Jlc3Npb24KMTMgc3RhcnQgcmVhbCBTUUwgU2VydmVyLWJhY2tlZCBB
UEkKMTQgc3RhcnQgcmVhbCBmcm9udGVuZAoxNSB0ZW4gcmVxdWlyZWQgcmVhbCBicm93c2VyIHBhdGhzICsgcXVhbGl0eSBldmlkZW5jZQoxNiBmcm9udGVu
ZCB0YXJnZXRlZC9mdWxsL2J1aWxkCjE3IGF1dGhvcml0eSAvIG9ic2VydmFiaWxpdHkgLyBzZWN1cml0eSBldmlkZW5jZQoxOCBnZW5lcmF0ZSA+PTMwMCBl
dmlkZW5jZS1ib3VuZCBhY2NlcHRhbmNlIGNoZWNrcwoxOSBzZW1hbnRpYyBldmlkZW5jZSB2YWxpZGF0aW9uCjIwIGFjdHVhbCBmYWlsLWNsb3NlZCBmaW5h
bGl6ZXIgd2l0aCBleGFjdCBjYW5kaWRhdGUgU0hBCjIxIGV2aWRlbmNlIG1hbmlmZXN0CjIyIGFydGlmYWN0IHVwbG9hZAoyMyBjbGVhbnVwCjI0IGluZGVw
ZW5kZW50IGFydGlmYWN0IHJlY2hlY2svaGFuZG9mZgpgYGAKCkRvIG5vdCBydW4gZmluYWwgYWNjZXB0YW5jZSBiZWZvcmUgcnVudGltZSBldmlkZW5jZSBl
eGlzdHMuCgotLS0KCiMgMzYuIFJFTU9URSBGUkVFWkUgUkVQUk9EVUNUSU9OCgpSZXF1aXJlIGZyZXNoOgoKYGBgdGV4dApSRU1PVEVfUEhBU0U1X0lOUFVU
X0lERU5USVRZPVBBU1MKUkVNT1RFX0NMQVNTSUZJRVJfRlJFRVpFX1JFUFJPRFVDSUJJTElUWT1QQVNTClJFTU9URV9DTEFTU0lGSUVSX1JFU1VMVF9IQVNI
X01JU01BVENIX0NPVU5UPTAKUkVNT1RFX0NBTk9OSUNBTF9BUlRJRkFDVF9NSVNTSU5HX0NPVU5UPTAKUkVNT1RFX0ZSRUVaRV9SRUZFUkVOQ0VfTUlTTUFU
Q0hfQ09VTlQ9MApgYGAKClIzIG11c3QgcHJvdmUgdGhlIHByZXNlcnZlZCBSMiBjbGFzc2lmaWVyL2ZyZWV6ZSBieXRlcyBhcmUgcmVwcm9kdWNpYmxlLgoK
LS0tCgojIDM3LiBSRU1PVEUgU1FMIFNFUlZFUiBUQVJHRVRFRCBQUk9PRgoKVXNlIHRoZSBmcmVzaCBgcGhhc2U1ZGJgLgoKUmVxdWlyZToKCmBgYHRleHQK
U1FMU0VSVkVSX01BSk9SPTE2Ck1JR1JBVElPTl9QQVNTPXRydWUKQUNUSVZFX01JR1JBVElPTl9IRUFEPWJhc2VsaW5lX3BoYXNlNF92MzZfYXp1cmVfc3Fs
CgpQSEFTRTVfU1FMU0VSVkVSX1RBUkdFVEVEX0dBVEVfQ09VTlQ9MTYKUEhBU0U1X1NRTFNFUlZFUl9UQVJHRVRFRF9QQVNTPTE2ClBIQVNFNV9TUUxTRVJW
RVJfVEFSR0VURURfRkFJTD0wClBIQVNFNV9TUUxTRVJWRVJfVEFSR0VURURfU0tJUD0wCmBgYAoKTm8gaGFyZGNvZGVkIHByb2R1Y2VyIFBBU1MuCgotLS0K
CiMgMzguIFJFTU9URSBTSEFET1cgUFJPT0YKClJlcXVpcmUgZXZpZGVuY2UtZGVyaXZlZDoKCmBgYHRleHQKU0hBRE9XX0NMQVNTSUZJQ0FUSU9OX0dFTkVS
QVRFRD10cnVlClNIQURPV19DT01QQVJJU09OX1JFQ09SREVEPXRydWUKU0hBRE9XX0NMQVNTSUZJQ0FUSU9OX0VOVkVMT1BFX0lNTVVUQUJMRT10cnVlClNI
QURPV19DT1JSRUNUSU9OX0FQUEVORF9PTkxZPXRydWUKCkNMQVNTSUZJRVJfT05MWV9WRVJJRklFRF9BU1NFUlRJT05fUFJPTU9USU9OX0NPVU5UPTAKQ0xB
U1NJRklFUl9PTkxZX1RZUEVEX1BST0pFQ1RJT05fQ09VTlQ9MApDTEFTU0lGSUVSX1BST1RFQ1RFRF9BQ1RJT05fRVhFQ1VUSU9OX0NPVU5UPTAKClJFUExB
WV9FVkVOVF9JRF9TVEFCTEVfQUNST1NTX1RJTUU9dHJ1ZQpSRVBMQVlfUkVTVUxUX0hBU0hfU1RBQkxFX0FDUk9TU19USU1FPXRydWUKUkVQTEFZX1NJREVf
RUZGRUNUX0RVUExJQ0FURV9DT1VOVD0wCgpTWU5PTE9HWV9XUklURUJBQ0tfQ09VTlQ9MApMTE1fRVhURVJOQUxfQ0FMTF9DT1VOVD0wClJFQUxfQ09OVEVO
VD1mYWxzZQpgYGAKCi0tLQoKIyAzOS4gUkVBTCBCUk9XU0VSIOKAlCBTQU1FIFNRTCBTRVJWRVIgQkFDS0VORAoKVG9wb2xvZ3kgbXVzdCBiZToKCmBgYHRl
eHQKcmVhbCBQcm9wb3NhbE9wcyBmcm9udGVuZArihpIgbG9jYWwgUHJvcG9zYWxPcHMgYmFja2VuZArihpIgZnJlc2ggUjMgU1FMIFNlcnZlciAyMDIyIHg2
NCBkYXRhYmFzZQpgYGAKCk5vIG1vY2tlZCBQcm9wb3NhbE9wcyBidXNpbmVzcyBBUEkgZm9yIHRoZSByZXF1aXJlZCB0ZW4gcGF0aHMuCgpSZXF1aXJlOgoK
YGBgdGV4dApQSEFTRTVfQlJPV1NFUl9SRVFVSVJFRF9QQVRIX0NPVU5UPTEwClBIQVNFNV9CUk9XU0VSX1JFUVVJUkVEX1BBVEhfUEFTUz0xMApQSEFTRTVf
QlJPV1NFUl9SRVFVSVJFRF9QQVRIX0ZBSUw9MApQSEFTRTVfQlJPV1NFUl9SRVFVSVJFRF9QQVRIX1NLSVA9MAoKUEhBU0U1X0JST1dTRVJfQVBJX01PQ0tf
Q09VTlRfRk9SX1JFUVVJUkVEX1BBVEhTPTAKYGBgCgpCcm93c2VyIGV2aWRlbmNlIHNjcmlwdCBtdXN0IHBhcnNlIHRoZSBhY3R1YWwgUGxheXdyaWdodCBK
U09OLgoKLS0tCgojIDQwLiBGVUxMIFJFR1JFU1NJT05TCgpTYW1lIHJ1biByZXF1aXJlOgoKYGBgdGV4dApQSEFTRTVfVEFSR0VURURfQkFDS0VORF9GQUlM
PTAKUEhBU0U1X1RBUkdFVEVEX0JBQ0tFTkRfU0tJUD0wCgpQSEFTRTRfSU5URUdSQVRJT05fUkVHUkVTU0lPTl9GQUlMPTAKQkFDS0VORF9GVUxMX0ZBSUw9
MAoKUEhBU0U1X1RBUkdFVEVEX0ZST05URU5EX0ZBSUw9MApGUk9OVEVORF9GVUxMX0ZBSUw9MApGUk9OVEVORF9CVUlMRD1QQVNTCgpQSEFTRTVfQlJPV1NF
Ul9GQUlMPTAKYGBgCgotLS0KCiMgNDEuIEFVVEhPUklUWSAvIE9CU0VSVkFCSUxJVFkgLyBTRUNVUklUWSBQUk9EVUNFUlMKCkRvIG5vdCBjcmVhdGUgUEFT
UyB2YWx1ZXMgaW4gcnVudGltZS1nYXRlcy5qc29uIG1lcmVseSBiZWNhdXNlIGVhcmxpZXIgc3RlcHMgZGlkCm5vdCBmYWlsLgoKRWFjaCBtdXN0IGhhdmUg
YWN0dWFsIHByb2R1Y2VyIGV2aWRlbmNlLgoKIyMgQXV0aG9yaXR5CgpQcm92ZSBhdCBtaW5pbXVtOgotIHByb3RlY3RlZCBhY3Rpb24gZGVuaWFsOwotIGNs
YXNzaWZpZXItb25seSBwcm9tb3Rpb24gY291bnQgemVybzsKLSBjbGFzc2lmaWVyLW9ubHkgcHJvamVjdGlvbiBjb3VudCB6ZXJvOwotIGNsaWVudCBhY3Rv
ciBkb2VzIG5vdCBvdmVycmlkZSBzZXJ2ZXIgYXV0aG9yaXR5OwotIGh1bWFuIHJldmlldyByZW1haW5zIHJlcXVpcmVkLgoKIyMgT2JzZXJ2YWJpbGl0eQoK
UHJvdmUgcmVjb25zdHJ1Y3RlZCBjaGFpbiBpbmNsdWRlczoKLSByb290IGV2ZW50OwotIHNvdXJjZSBhcnRpZmFjdC92ZXJzaW9uOwotIGV2aWRlbmNlIGVu
dmVsb3BlOwotIGNsYXNzaWZpZXIvcnVsZXMvdGF4b25vbXk7Ci0gY29ycmVsYXRpb24gSUQ7Ci0gcmV2aWV3L2NvcnJlY3Rpb247Ci0gcmVzdWx0IGlkZW50
aXR5LgoKIyMgU2VjdXJpdHkvc291cmNlIGh5Z2llbmUKClByb3ZlOgotIG5ldyBzb3VyY2UgcmVhZHMgPSAwOwotIHJlYWwgZGF0YSA9IGZhbHNlOwotIGV4
dGVybmFsIExMTSBjYWxscyA9IDA7Ci0gc2VjcmV0IHBhdHRlcm4gbWF0Y2hlcyBpbiBldmlkZW5jZSA9IDA7Ci0gbm8gU3lub2xvZ3kvU01CL0F6dXJlL0Vu
dHJhIGFjY2Vzcy4KClJlcXVpcmUgYWN0dWFsIHJlc3VsdCBmaWxlcyBmcm9tIGFsbCB0aHJlZSBwcm9kdWNlcnMuCgotLS0KCiMgNDIuIFJFTU9URSBBQ0NF
UFRBTkNFIOKAlCBBRlRFUiBSVU5USU1FCgpSdW4gYWNjZXB0YW5jZSBvbmx5IGFmdGVyIFNlY3Rpb25zIDM24oCTNDEgZXZpZGVuY2UgZXhpc3RzLgoKUmVx
dWlyZToKCmBgYHRleHQKUEhBU0U1X0FDQ0VQVEFOQ0VfQ0hFQ0tfQ09VTlQ+PTMwMApQSEFTRTVfQUNDRVBUQU5DRV9DSEVDS19QQVNTPVBIQVNFNV9BQ0NF
UFRBTkNFX0NIRUNLX0NPVU5UClBIQVNFNV9BQ0NFUFRBTkNFX0NIRUNLX0ZBSUw9MAoKUEhBU0U1X0FDQ0VQVEFOQ0VfQ0hFQ0tfV0lUSE9VVF9SRVFVSVJF
TUVOVF9JRD0wClBIQVNFNV9BQ0NFUFRBTkNFX0RVUExJQ0FURV9DSEVDS19JRF9DT1VOVD0wClBIQVNFNV9BQ0NFUFRBTkNFX0RVUExJQ0FURV9SRVFVSVJF
TUVOVF9QQURESU5HX0NPVU5UPTAKUEhBU0U1X0FDQ0VQVEFOQ0VfRFVQTElDQVRFX0FTU0VSVElPTl9DT1VOVD0wCgpQSEFTRTVfQUNDRVBUQU5DRV9VTktO
T1dOX0VWSURFTkNFX0lEX0NPVU5UPTAKUEhBU0U1X0FDQ0VQVEFOQ0VfVU5SRVNPTFZFRF9FVklERU5DRV9SRUZFUkVOQ0VfQ09VTlQ9MAoKUEhBU0U1X0FD
Q0VQVEFOQ0VfUlVOVElNRV9SRVFVSVJFRF9TT1VSQ0VfT05MWV9QQVNTX0NPVU5UPTAKUEhBU0U1X0FDQ0VQVEFOQ0VfRkFMU0VfQUNDRVBUX0NPVU5UPTAK
CkNSSVRJQ0FMX0ZBTFNFX1BST01PVElPTlM9MApgYGAKCi0tLQoKIyA0My4gQUNUVUFMIEZJTkFMSVpFUiDigJQgRVhBQ1QgUjMgQ0FORElEQVRFCgpJbnZv
a2U6CgpgYGBiYXNoCnB5dGhvbiBzY3JpcHRzL3BoYXNlNS9waGFzZTVfZmluYWxpemUucHkgXAogIC0tZXZpZGVuY2UtZGlyICIkRVZJREVOQ0VfRElSIiBc
CiAgLS1hY2NlcHRhbmNlLXJlc3VsdCAiJEVWSURFTkNFX0RJUi9hY2NlcHRhbmNlLXJlc3VsdC5qc29uIiBcCiAgLS1jb250cmFjdHMtZGlyIGNvbnRyYWN0
cy9hbWVjL3BoYXNlNSBcCiAgLS1leHBlY3RlZC1jYW5kaWRhdGUtc2hhICIkQ0FORElEQVRFX1NIQSIgXAogIC0tb3V0cHV0ICIkRVZJREVOQ0VfRElSL3Bo
YXNlNS1maW5hbC1zdW1tYXJ5Lmpzb24iCmBgYAoKRmluYWxpemVyIG11c3QgZGVyaXZlIHJhdGhlciB0aGFuIG1hbnVmYWN0dXJlIHRoZSBzdW1tYXJ5LgoK
UmVxdWlyZToKCmBgYHRleHQKUlVOX0VWSURFTkNFX1NUQVRFPUNPTVBMRVRFX1BBU1MKYGBgCgpBbnl0aGluZyByZXF1aXJlZCBtaXNzaW5nL2ZhaWxpbmcv
Tk9UX0VYRUNVVEVEOgoKYGBgdGV4dApSVU5fRVZJREVOQ0VfU1RBVEU9UEFSVElBTF9GQUlMRUQKYGBgCgpuZXZlciBQQVNTLgoKLS0tCgojIDQ0LiBFVklE
RU5DRSBJTlRFR1JJVFkKCkV2ZXJ5IG1hbmRhdG9yeSBwcm9kdWNlciBtdXN0IGhhdmU6CgpgYGB0ZXh0CnJhdyBsb2cgb3IgZXhwbGljaXQgc3VjY2VzcyBt
YXJrZXIKbWV0YSBKU09OCnJlc3VsdCBKU09OCmludGVnZXIgZXhpdCBjb2RlCmNhbmRpZGF0ZSBTSEEKdmFsaWRhdGlvbiBTSEEKcnVuIElECmBgYAoKUmVx
dWlyZToKCmBgYHRleHQKVU5SRVNPTFZFRF9FVklERU5DRV9SRUZFUkVOQ0VfQ09VTlQ9MApCTEFOS19FWElUX0NPREVfQ09VTlQ9MApNSVNTSU5HX0VWSURF
TkNFX0ZJTEVfQ09VTlQ9MApaRVJPX0JZVEVfUkVRVUlSRURfUkFXX0xPR19DT1VOVD0wCgpEVVBMSUNBVEVfQUNDRVBUQU5DRV9JRF9DT1VOVD0wClNFTEZf
Q0VSVElGWUlOR19QQVNTX0NPVU5UPTAKU0VDUkVUX0VWSURFTkNFX01BVENIX0NPVU5UPTAKClJVTlRJTUVfUkVRVUlSRURfU09VUkNFX09OTFlfUEFTU19D
T1VOVD0wCkZBTFNFX0FDQ0VQVF9DT1VOVD0wCmBgYAoKLS0tCgojIDQ1LiBXT1JLRkxPVyBTVEFUSUMgTk8tTE9PUCBQUkVGTElHSFQgQkVGT1JFIEZJUlNU
IENPTU1JVAoKQmVmb3JlIHZhbGlkYXRpb24gd29ya2Zsb3cgY29tbWl0IGluc3BlY3QgdGhlIGFjdHVhbCBZQU1ML3NoZWxsLgoKUmVxdWlyZToKCmBgYHRl
eHQKV09SS0ZMT1dfU1RBTEVfMjAyMl9HQV9VQlVOVFVfMjBfMDRfQ09VTlQ9MAoKV09SS0ZMT1dfU1FMU0VSVkVSXzIwMjJfTEFURVNUX1BVTExfQ09VTlQ9
MQpXT1JLRkxPV19TUUxTRVJWRVJfUlVOX0JZX1JFU09MVkVEX0RJR0VTVD10cnVlCldPUktGTE9XX1NRTFNFUlZFUl9QTEFURk9STV9BTUQ2ND10cnVlCgpX
T1JLRkxPV19TUUxTRVJWRVJfUEFTU1dPUkRfRVhQT1JUX0NPVU5UPTEKV09SS0ZMT1dfU1FMU0VSVkVSX1BBU1NXT1JEX0dJVEhVQl9FTlZfQ09VTlQ9MQoK
V09SS0ZMT1dfSU5fQ09OVEFJTkVSX1NRTENNRF9CT09UU1RSQVBfQ09VTlQ9MApXT1JLRkxPV19IT1NUX1BZT0RCQ19CT09UU1RSQVBfQ09VTlQ9MQoKV09S
S0ZMT1dfUExBWVdSSUdIVF9DSFJPTUlVTV9JTlNUQUxMX0NPVU5UPTEKCldPUktGTE9XX0FDQ0VQVEFOQ0VfQUZURVJfQlJPV1NFUl9TUUxTRVJWRVJfUkVH
UkVTU0lPTlM9dHJ1ZQpXT1JLRkxPV19GSU5BTElaRVJfRVhQRUNURURfQ0FORElEQVRFX1NIQV9CSU5ESU5HPXRydWUKCldPUktGTE9XX1BIQVNFNV9TQ1JJ
UFRfUEFUSF9NSVNTSU5HX0NPVU5UPTAKV09SS0ZMT1dfRVZJREVOQ0VfUFJPRFVDRVJfVU5LTk9XTl9DT1VOVD0wCldPUktGTE9XX1JFUVVJUkVEX0VWSURF
TkNFX05BTUVfTUlTTUFUQ0hfQ09VTlQ9MAoKV09SS0ZMT1dfRFVQTElDQVRFX01JQ1JPU09GVF9BUFRfU09VUkNFX0NPVU5UPTAKV09SS0ZMT1dfTE9DQUxf
TUFDX0RPQ0tFUl9SRUZFUkVOQ0VfQ09VTlQ9MApgYGAKCkRvIG5vdCBjb21taXQgd29ya2Zsb3cgdW50aWwgYWxsIGFyZSBncmVlbi4KCi0tLQoKIyA0Ni4g
Q1JFQVRFIEVYQUNUTFkgT05FIFZBTElEQVRJT04gV09SS0ZMT1cgQ09NTUlUCgpPbjoKCmBgYHRleHQKcGhhc2U1LWNsYXNzaWZpZXItc2hhZG93LXZhbGlk
YXRpb24tY2ktcjMtdjEKYGBgCgpjb21taXQgb25seToKCmBgYHRleHQKLmdpdGh1Yi93b3JrZmxvd3MvcGhhc2U1LWNsYXNzaWZpZXItc2hhZG93LXZhbGlk
YXRpb24tY2ktcjMueW1sCmBgYAoKUGFyZW50IG11c3QgYmUgZXhhY3QgUjMgYXBwbGljYXRpb24gU0hBLgoKUmVjb21tZW5kZWQgbWVzc2FnZToKCmBgYHRl
eHQKY2kocGhhc2U1KTogdmFsaWRhdGUgZXZpZGVuY2UtYm91bmQgc2hhZG93IG9uIFNRTCBTZXJ2ZXIKYGBgCgpQdXNoIG9ubHkgdmFsaWRhdGlvbiBicmFu
Y2guCgpBZnRlciBwdXNoOgoKYGBgdGV4dApTRUNPTkRfV09SS0ZMT1dfQ09NTUlUX0FVVEhPUklaRUQ9ZmFsc2UKYGBgCgotLS0KCiMgNDcuIEZBSUxVUkUg
UE9MSUNZIOKAlCBOTyBSMyBQQVRDSCBMT09QCgpJZiBwcmVjb21taXQgY2Fubm90IGNsb3NlIGFsbCBkZXRlcm1pbmlzdGljIGRlZmVjdHM6CgpgYGB0ZXh0
ClJFU1VMVD1TVE9QX1BIQVNFNV9SM19QUkVDT01NSVRfTk9fR08KRklSU1RfRkFJTEVEX0dBVEU9PGV4YWN0PgpgYGAKClNUT1AgYmVmb3JlIGFwcCBjb21t
aXQuCgpJZiByZW1vdGUgcnVuIGZhaWxzOgoKYGBgdGV4dApSRVNVTFQ9U1RPUF9QSEFTRTVfUjNfUkVNT1RFX1ZBTElEQVRJT05fRkFJTEVECgpGSVJTVF9G
QUlMRURfR0FURT08ZXhhY3Q+CkZJUlNUX0ZBSUxFRF9TVUJHQVRFPTxleGFjdCBpZiBrbm93bj4KRkFJTFVSRV9FVklERU5DRT08ZXhhY3Qgc2FuaXRpemVk
PgoKUEhBU0U1X1IzX0NBTkRJREFURV9TSEE9PGV4YWN0PgpQSEFTRTVfUjNfVkFMSURBVElPTl9TSEE9PGV4YWN0PgoKUlVOX0lEPTxleGFjdD4KSk9CX0lE
PTxleGFjdD4KQVJUSUZBQ1RfSUQ9PGV4YWN0PgpBUlRJRkFDVF9TSEEyNTY9PGV4YWN0PgoKU0VDT05EX0FQUExJQ0FUSU9OX0NPTU1JVF9DUkVBVEVEPWZh
bHNlClNFQ09ORF9XT1JLRkxPV19DT01NSVRfQ1JFQVRFRD1mYWxzZQoKTUFJTl9DSEFOR0VEPWZhbHNlCkFaVVJFX0FDQ0VTU0VEPWZhbHNlCkVOVFJBX0FD
Q0VTU0VEPWZhbHNlClNZTk9MT0dZX0FDQ0VTU0VEPWZhbHNlClNNQl9BQ0NFU1NFRD1mYWxzZQpSRUFMX0RBVEFfVVNFRD1mYWxzZQoKTkVYVD1TVE9QCmBg
YAoKRG8gbm90IGNyZWF0ZSBSM1IxL1I0IGF1dG9tYXRpY2FsbHkuCgotLS0KCiMgNDguIElOREVQRU5ERU5UIEFSVElGQUNUIFJFQ0hFQ0sgQUZURVIgUkVN
T1RFIENPTVBMRVRFIFBBU1MKCk9ubHkgYWZ0ZXIgdGhlIHJlbW90ZSB3b3JrZmxvdyBpdHNlbGYgcGFzc2VzOgoKMS4gZG93bmxvYWQgZXhhY3QgYXJ0aWZh
Y3Q7CjIuIGhhc2ggYXJ0aWZhY3Q7CjMuIHJlLWV4dHJhY3Q7CjQuIHZlcmlmeSBhcHBsaWNhdGlvbi92YWxpZGF0aW9uL3J1biBiaW5kaW5nOwo1LiB2ZXJp
ZnkgZXZlcnkgcmVnaXN0ZXJlZCBwcm9kdWNlciByYXcvbWV0YS9yZXN1bHQ7CjYuIHZlcmlmeSBubyBtaXNzaW5nL3VubWFuaWZlc3RlZC9oYXNoLW1pc21h
dGNoZWQgZXZpZGVuY2U7CjcuIGluZGVwZW5kZW50bHkgcmVjYWxjdWxhdGUgYWNjZXB0YW5jZSBjb3VudHM7CjguIGluZGVwZW5kZW50bHkgcmVjYWxjdWxh
dGUgZmFsc2UtYWNjZXB0L3J1bnRpbWUtc291cmNlLW9ubHkgY291bnRzOwo5LiB2ZXJpZnkgU1FMIFNlcnZlciBpbWFnZSBSZXBvRGlnZXN0ICsgbWFqb3Ig
MTY7CjEwLiB2ZXJpZnkgbWlncmF0aW9uIGhlYWQ7CjExLiB2ZXJpZnkgMTYgU1FMIFNlcnZlciB0YXJnZXRlZCBnYXRlczsKMTIuIHZlcmlmeSBTSEFET1cg
cmVwbGF5IHN0YXRlOwoxMy4gcGFyc2UgUGxheXdyaWdodCBKU09OIGluZGVwZW5kZW50bHkgZm9yIHRlbiBwYXRoczsKMTQuIHZlcmlmeSByZWdyZXNzaW9u
cy9idWlsZDsKMTUuIHZlcmlmeSBmaW5hbGl6ZXIgcmVzdWx0OwoxNi4gc2VjcmV0L3Jhdy1jb250ZW50IHNjYW47CjE3LiB2ZXJpZnkgbm8gZXh0ZXJuYWwg
YWNjZXNzLgoKQ3JlYXRlOgoKYGBgdGV4dApQcm9wb3NhbE9wc19QaGFzZTVfUjNfSW5kZXBlbmRlbnRfUmV2aWV3X0hhbmRvZmZfPGNhbmRpZGF0ZV9zaG9y
dD5fPHRpbWVzdGFtcD4vClByb3Bvc2FsT3BzX1BoYXNlNV9SM19JbmRlcGVuZGVudF9SZXZpZXdfSGFuZG9mZl88Y2FuZGlkYXRlX3Nob3J0Pl88dGltZXN0
YW1wPi50YXIuZ3oKYGBgCgpNYW5pZmVzdCBldmVyeSBmaWxlIGFuZCByZS1leHRyYWN0IGFyY2hpdmUuCgpEbyBub3QgaW5kZXBlbmRlbnRseSBhY2NlcHQg
UGhhc2U1IGluc2lkZSBDb2RleC4KCi0tLQoKIyA0OS4gU0FGRVRZIEJPVU5EQVJZCgpUaHJvdWdob3V0OgoKYGBgdGV4dApBWlVSRV9BQ0NFU1NFRD1mYWxz
ZQpFTlRSQV9BQ0NFU1NFRD1mYWxzZQpTWU5PTE9HWV9BQ0NFU1NFRD1mYWxzZQpTTUJfQUNDRVNTRUQ9ZmFsc2UKUkVBTF9EQVRBX1VTRUQ9ZmFsc2UKCk5F
V19TTUJfQ09OTkVDVElPTlM9MApORVdfQU1FQ19TT1VSQ0VfUkVBRFM9MApORVdfQU1FQ19TT1VSQ0VfQllURVM9MAoKQVVUT19QUk9NT1RJT05fRU5BQkxF
RD1mYWxzZQpSRUFMX0xJVkVfU0hBRE9XX0VOQUJMRUQ9ZmFsc2UKTElWRV9TWU5PTE9HWV9NT05JVE9SX0VOQUJMRUQ9ZmFsc2UKU1lOT0xPR1lfV1JJVEVC
QUNLX0VOQUJMRUQ9ZmFsc2UKCkxMTV9SRUFMX0NPTlRFTlRfTU9ERT1ESVNBQkxFRApMTE1fRVhURVJOQUxfQ0FMTF9DT1VOVD0wCgpNQUlOX0NIQU5HRUQ9
ZmFsc2UKTUFJTl9QVVNIRUQ9ZmFsc2UKVEFHX0NSRUFURUQ9ZmFsc2UKUkVMRUFTRV9DUkVBVEVEPWZhbHNlCkRFUExPWU1FTlRfU1RBUlRFRD1mYWxzZQoK
UEhBU0U2X1NUQVJURUQ9ZmFsc2UKYGBgCgotLS0KCiMgNTAuIFRSVVRIRlVMIFNVQ0NFU1MgQ0xBU1NJRklDQVRJT04KCkEgc3VjY2Vzc2Z1bCBleGFjdCBS
MyBydW4gbWF5IGVzdGFibGlzaCBmb3IgUGhhc2U1OgoKYGBgdGV4dApQSEFTRTVfQ0FORElEQVRFX0NPTVBMRVRFPXRydWUKQ0xBU1NJRklFUl9WMl9GUk9a
RU49dHJ1ZQpQUk9EVUNUSU9OX0NMQVNTSUZJRVJfQ0FORElEQVRFPXRydWUKClZFUklGSUVEX0xPQ0FMPXRydWUKVkVSSUZJRURfU1FMU0VSVkVSX0NPTVBB
VD10cnVlClZFUklGSUVEX0JST1dTRVI9dHJ1ZQoKVkVSSUZJRURfQVpVUkVfU1FMPWZhbHNlClZFUklGSUVEX0RFUExPWUVEPWZhbHNlCgpBVVRPX1BST01P
VElPTl9FTkFCTEVEPWZhbHNlClJFQUxfTElWRV9TSEFET1dfRU5BQkxFRD1mYWxzZQpTWU5PTE9HWV9XUklURUJBQ0tfRU5BQkxFRD1mYWxzZQpMTE1fUkVB
TF9DT05URU5UX01PREU9RElTQUJMRUQKClBIQVNFNV9DT0RFWF9TRUxGX0FDQ0VQVEVEPWZhbHNlClBIQVNFNV9JTkRFUEVOREVOVF9BQ0NFUFRBTkNFPVBF
TkRJTkcKYGBgCgpEbyBub3QgY2xhaW0gQXp1cmUgU1FMIHZlcmlmaWNhdGlvbiBmcm9tIGxvY2FsIFNRTCBTZXJ2ZXIuCgotLS0KCiMgNTEuIEZJTkFMIFNV
Q0NFU1MgUkVUVVJOCgpPbmx5IGlmOgotIGFwcGxpY2F0aW9uIHByZWNvbW1pdCBhbGwgZ3JlZW47Ci0gb25lIFIzIGFwcGxpY2F0aW9uIGNvbW1pdDsKLSBv
bmUgd29ya2Zsb3ctb25seSB2YWxpZGF0aW9uIGNoaWxkOwotIHJlbW90ZSB3b3JrZmxvdyBjb21wbGV0ZSBQQVNTOwotIGluZGVwZW5kZW50IGFydGlmYWN0
IHJlY2hlY2sgY29tcGxldGUgUEFTUzsKLSBldmlkZW5jZSBmYWxzZS1hY2NlcHQgY291bnQgemVybzsKLSBhbGwgUnVuLTEwIGRlZmVjdHMgY2xvc2VkOwoK
cmV0dXJuOgoKYGBgdGV4dApSRVNVTFQ9UEhBU0U1X1IzX0NBTkRJREFURV9SRUFEWV9GT1JfSU5ERVBFTkRFTlRfQUNDRVBUQU5DRQoKUEhBU0U1X1IzX0FQ
UExJQ0FUSU9OX0JSQU5DSD0KcGhhc2U1LWNsYXNzaWZpZXItc2hhZG93LXZhbGlkYXRpb24tcjMtdjEKClBIQVNFNV9SM19DQU5ESURBVEVfU0hBPTxleGFj
dD4KUEhBU0U1X1IzX0NBTkRJREFURV9QQVJFTlQ9CmNhNjA0NTlmMjEwM2NiZjMwZTUyZTA1YzU5YjhhZjZkNzcxNGJlMTIKUEhBU0U1X1IzX0NBTkRJREFU
RV9UUkVFPTxleGFjdD4KClBIQVNFNV9SM19WQUxJREFUSU9OX0JSQU5DSD0KcGhhc2U1LWNsYXNzaWZpZXItc2hhZG93LXZhbGlkYXRpb24tY2ktcjMtdjEK
ClBIQVNFNV9SM19WQUxJREFUSU9OX1NIQT08ZXhhY3Q+ClBIQVNFNV9SM19WQUxJREFUSU9OX1BBUkVOVD08UEhBU0U1X1IzX0NBTkRJREFURV9TSEE+CgpS
VU5fSUQ9PGV4YWN0PgpKT0JfSUQ9PGV4YWN0PgpBUlRJRkFDVF9JRD08ZXhhY3Q+CkFSVElGQUNUX1NIQTI1Nj08ZXhhY3Q+CgpTUUxTRVJWRVJfSU1BR0Vf
VEFHPQptY3IubWljcm9zb2Z0LmNvbS9tc3NxbC9zZXJ2ZXI6MjAyMi1sYXRlc3QKClNRTFNFUlZFUl9JTUFHRV9SRVBPRElHRVNUPTxleGFjdD4KClNRTFNF
UlZFUl9NQUpPUj0xNgpNSUdSQVRJT05fUEFTUz10cnVlCkFDVElWRV9NSUdSQVRJT05fSEVBRD1iYXNlbGluZV9waGFzZTRfdjM2X2F6dXJlX3NxbAoKUEhB
U0U1X1NRTFNFUlZFUl9UQVJHRVRFRF9HQVRFX0NPVU5UPTE2ClBIQVNFNV9TUUxTRVJWRVJfVEFSR0VURURfUEFTUz0xNgpQSEFTRTVfU1FMU0VSVkVSX1RB
UkdFVEVEX0ZBSUw9MApQSEFTRTVfU1FMU0VSVkVSX1RBUkdFVEVEX1NLSVA9MAoKU0hBRE9XX0NMQVNTSUZJQ0FUSU9OX0dFTkVSQVRFRD10cnVlClNIQURP
V19DT01QQVJJU09OX1JFQ09SREVEPXRydWUKU0hBRE9XX0NMQVNTSUZJQ0FUSU9OX0VOVkVMT1BFX0lNTVVUQUJMRT10cnVlClNIQURPV19DT1JSRUNUSU9O
X0FQUEVORF9PTkxZPXRydWUKCkNMQVNTSUZJRVJfT05MWV9WRVJJRklFRF9BU1NFUlRJT05fUFJPTU9USU9OX0NPVU5UPTAKQ0xBU1NJRklFUl9PTkxZX1RZ
UEVEX1BST0pFQ1RJT05fQ09VTlQ9MApDTEFTU0lGSUVSX1BST1RFQ1RFRF9BQ1RJT05fRVhFQ1VUSU9OX0NPVU5UPTAKClJFUExBWV9FVkVOVF9JRF9TVEFC
TEVfQUNST1NTX1RJTUU9dHJ1ZQpSRVBMQVlfUkVTVUxUX0hBU0hfU1RBQkxFX0FDUk9TU19USU1FPXRydWUKUkVQTEFZX1NJREVfRUZGRUNUX0RVUExJQ0FU
RV9DT1VOVD0wCgpQSEFTRTVfQlJPV1NFUl9SRVFVSVJFRF9QQVRIX0NPVU5UPTEwClBIQVNFNV9CUk9XU0VSX1JFUVVJUkVEX1BBVEhfUEFTUz0xMApQSEFT
RTVfQlJPV1NFUl9SRVFVSVJFRF9QQVRIX0ZBSUw9MApQSEFTRTVfQlJPV1NFUl9SRVFVSVJFRF9QQVRIX1NLSVA9MAoKUEhBU0U1X1RBUkdFVEVEX0JBQ0tF
TkRfRkFJTD0wClBIQVNFNF9JTlRFR1JBVElPTl9SRUdSRVNTSU9OX0ZBSUw9MApCQUNLRU5EX0ZVTExfRkFJTD0wCgpQSEFTRTVfVEFSR0VURURfRlJPTlRF
TkRfRkFJTD0wCkZST05URU5EX0ZVTExfRkFJTD0wCkZST05URU5EX0JVSUxEPVBBU1MKClJFTU9URV9DTEFTU0lGSUVSX0ZSRUVaRV9SRVBST0RVQ0lCSUxJ
VFk9UEFTUwpSRU1PVEVfQ0xBU1NJRklFUl9SRVNVTFRfSEFTSF9NSVNNQVRDSF9DT1VOVD0wClJFTU9URV9GUkVFWkVfUkVGRVJFTkNFX01JU01BVENIX0NP
VU5UPTAKClBIQVNFNV9BQ0NFUFRBTkNFX0NIRUNLX0NPVU5UPTxhY3R1YWwgPj0zMDA+ClBIQVNFNV9BQ0NFUFRBTkNFX0NIRUNLX1BBU1M9PHNhbWU+ClBI
QVNFNV9BQ0NFUFRBTkNFX0NIRUNLX0ZBSUw9MAoKUEhBU0U1X0FDQ0VQVEFOQ0VfUlVOVElNRV9SRVFVSVJFRF9TT1VSQ0VfT05MWV9QQVNTX0NPVU5UPTAK
UEhBU0U1X0FDQ0VQVEFOQ0VfRkFMU0VfQUNDRVBUX0NPVU5UPTAKClJVTl9FVklERU5DRV9TVEFURT1DT01QTEVURV9QQVNTCgpVTlJFU09MVkVEX0VWSURF
TkNFX1JFRkVSRU5DRV9DT1VOVD0wCkJMQU5LX0VYSVRfQ09ERV9DT1VOVD0wCk1JU1NJTkdfRVZJREVOQ0VfRklMRV9DT1VOVD0wClpFUk9fQllURV9SRVFV
SVJFRF9SQVdfTE9HX0NPVU5UPTAKRFVQTElDQVRFX0FDQ0VQVEFOQ0VfSURfQ09VTlQ9MApTRUxGX0NFUlRJRllJTkdfUEFTU19DT1VOVD0wClNFQ1JFVF9F
VklERU5DRV9NQVRDSF9DT1VOVD0wCgpDMDFfU09VUkNFX1BSRUZMSUdIVF9IQVJEQ09ERURfRklFTERTPUNMT1NFRApDMDJfRklYRURfU0hBX0RFU0NFTkRB
TlRfQVVESVRfSU5DT01QTEVURT1DTE9TRUQKQzAzX0JST1dTRVJfRVZJREVOQ0VfSEFSRENPREVEX1BBU1M9Q0xPU0VECkMwNF9TUUxTRVJWRVJfRVZJREVO
Q0VfSEFSRENPREVEX1BBU1M9Q0xPU0VECkMwNV9TSEFET1dfUkVQTEFZX0hBUkRDT0RFRF9QQVNTPUNMT1NFRApDMDZfQUNDRVBUQU5DRV9HRU5FUkFUT1Jf
SEFSRENPREVEX1BBU1M9Q0xPU0VECkMwN19BQ0NFUFRBTkNFX0VWSURFTkNFX1NFTEZfUkVGRVJFTlRJQUw9Q0xPU0VECkMwOF9FVklERU5DRV9WQUxJREFU
T1JfU0VNQU5USUNfR0FQPUNMT1NFRApDMDlfRklOQUxJWkVSX0RFRkFVTFRfUlVOVElNRV9QQVNTPUNMT1NFRApDMTBfRklOQUxJWkVSX0NBTkRJREFURV9T
SEFfTk9UX0VYQUNUPUNMT1NFRApDMTFfRklOQUxJWkVSX1NVTU1BUllfSEFSRENPREVEX1JVTlRJTUU9Q0xPU0VECkMxMl9SRVBST0RVQ0lCSUxJVFlfTk9U
X1JFR0VORVJBVEVEPUNMT1NFRAoKVzAxX0lOVkFMSURfU1FMU0VSVkVSX0lNQUdFX1RBRz1DTE9TRUQKVzAyX1NRTFNFUlZFUl9QQVNTV09SRF9OT1RfRVhQ
T1JURUQ9Q0xPU0VEClcwM19JTl9DT05UQUlORVJfU1FMQ01EX0JPT1RTVFJBUD1DTE9TRUQKVzA0X1BMQVlXUklHSFRfQlJPV1NFUl9OT1RfRVhQTElDSVRM
WV9JTlNUQUxMRUQ9Q0xPU0VECgpQSEFTRTVfSEFORE9GRl9BUkNISVZFPTxleGFjdD4KUEhBU0U1X0hBTkRPRkZfQVJDSElWRV9TSEEyNTY9PGV4YWN0PgpI
QU5ET0ZGX1JFRVhUUkFDVElPTl9QQVNTPXRydWUKClBIQVNFNV9DQU5ESURBVEVfQ09NUExFVEU9dHJ1ZQpDTEFTU0lGSUVSX1YyX0ZST1pFTj10cnVlClBS
T0RVQ1RJT05fQ0xBU1NJRklFUl9DQU5ESURBVEU9dHJ1ZQoKVkVSSUZJRURfTE9DQUw9dHJ1ZQpWRVJJRklFRF9TUUxTRVJWRVJfQ09NUEFUPXRydWUKVkVS
SUZJRURfQlJPV1NFUj10cnVlClZFUklGSUVEX0FaVVJFX1NRTD1mYWxzZQpWRVJJRklFRF9ERVBMT1lFRD1mYWxzZQoKREFUQUJBU0VfVEFSR0VUX0RFQ0lT
SU9OPU9XTkVSX0NPTkZJUk1FRApEQVRBQkFTRV9FTkdJTkVfVEFSR0VUPUFaVVJFX1NRTF9TUUxfU0VSVkVSX0VOR0lORQpBWlVSRV9TUUxfU0VSVklDRV9W
QVJJQU5UPUFaVVJFX1NRTF9EQVRBQkFTRQpBWlVSRV9TUUxfRVhBQ1RfU0tVPU9XTkVSX0RFQ0lTSU9OX1BFTkRJTkcKCkFVVE9fUFJPTU9USU9OX0VOQUJM
RUQ9ZmFsc2UKUkVBTF9MSVZFX1NIQURPV19FTkFCTEVEPWZhbHNlClNZTk9MT0dZX1dSSVRFQkFDS19FTkFCTEVEPWZhbHNlCkxMTV9SRUFMX0NPTlRFTlRf
TU9ERT1ESVNBQkxFRApMTE1fRVhURVJOQUxfQ0FMTF9DT1VOVD0wCgpNQUlOX0NIQU5HRUQ9ZmFsc2UKTUFJTl9QVVNIRUQ9ZmFsc2UKQVpVUkVfQUNDRVNT
RUQ9ZmFsc2UKRU5UUkFfQUNDRVNTRUQ9ZmFsc2UKU1lOT0xPR1lfQUNDRVNTRUQ9ZmFsc2UKU01CX0FDQ0VTU0VEPWZhbHNlClJFQUxfREFUQV9VU0VEPWZh
bHNlCgpQSEFTRTVfQ09ERVhfU0VMRl9BQ0NFUFRFRD1mYWxzZQpQSEFTRTVfSU5ERVBFTkRFTlRfQUNDRVBUQU5DRT1QRU5ESU5HClBIQVNFNl9TVEFSVEVE
PWZhbHNlCgpORVhUPUlOREVQRU5ERU5UX1BIQVNFNV9BQ0NFUFRBTkNFX1JFVklFVwpgYGAKClRoZW4gU1RPUC4KCk5vIHBvc3Qtc3VjY2VzcyBpbXBsZW1l
bnRhdGlvbiBtdXRhdGlvbiBpcyBhdXRob3JpemVkLgo=
<<<END_BASE64_PHASE5_SOURCE::docs/phase5/governing/ProposalOps_Phase5_FINAL_R3_OneShot_EvidenceTruth_SQLServer_Browser_Closure_2026-08-24.md>>>

