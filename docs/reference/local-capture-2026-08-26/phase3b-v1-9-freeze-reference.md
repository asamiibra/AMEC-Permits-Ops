# CODEX MASTER EXECUTION PROMPT
# ProposalOps / AMEC — Phase 3B v1.9
# Stage 0.3 FINAL ACCEPTANCE, v1.8 CONFORMANCE, REPAIR-IF-NEEDED, FREEZE
# + Module-Coverage Closure
# + Exact Stage1R-A Budget Freeze
# + Phase 3B.0.4 Transport-Certification Handoff
#
# THIS IS THE FINAL METADATA-ONLY ACCEPTANCE GATE FOR STAGE 0.3.
#
# ZERO BUSINESS-SOURCE READS.
# ZERO SOURCE HASHES.
# ZERO SYNOLOGY CONNECTIONS.
# ZERO SOURCE MUTATIONS.
# ZERO OCR.
# ZERO ARCHIVE EXTRACTION.
# ZERO PRODUCT / DB / DEPLOYMENT CHANGES.
#
# DO NOT RE-RUN PHASE 2.
# DO NOT RE-RUN PHASE 3A / 3A.1.
# DO NOT RE-RUN STAGE 0 / 0.1 / 0.2.
# DO NOT RECLASSIFY THE 251,211-ROW CORPUS.
#
# The purpose is to:
#   1) accept or narrowly repair the completed Stage 0.3 v1.7 output,
#   2) prove conformance with the governing v1.8 taxonomy-first contract,
#   3) freeze the exact Stage1R-A candidate and physical-I/O budget,
#   4) prove module coverage,
#   5) produce the immutable handoff for Phase 3B.0.4.
#
# A successful run closes Stage 0.3.
# No additional metadata-planning phase should be invented afterward unless
# this audit proves a genuine unreconciled defect.

---

# 0. CURRENT EXECUTION STATE

The latest Stage 0.3 run reported:

```text
STAGE0_3_RESULT=PASS
RESULT=PREAUTHORIZATION_READY

post-object-closure FILE actions
1,468

Stage1R-A
273 operations

Stage1R-B
343 operations

Stage1R-DEFER
579 operations

Stage1R-SKIP
273 operations

273 + 343 + 579 + 273
=
1,468

Stage1R-A >=100 MB
0

Stage1R-A >=1 GB
0

business-source bytes read
0

source hashes
0

source connections
0

source mutations
0

transport contract
READY / DESIGN ONLY

transport certification
NOT EXECUTED
```

Expected evidence directory:

```text
<local ProposalOps-Control>/
proposalops-amec-corpus-phase3b-stage0-3-evidence-20260817/
```

Key reported artifacts include:

```text
summary.json

17_AMEC_Phase3B_Stage1R_A_Immediate_High_Value_Plan_CANDIDATE_v1.json

18_AMEC_Phase3B_Stage1R_A_Immediate_High_Value_Allowlist_CANDIDATE_v1.jsonl

08_AMEC_Phase3B_Stage0_3_Product_Relevance_Audit_v1.json

32_AMEC_Phase3B_Stage0_3_Source_Access_Transport_Contract_v1.json

34_AMEC_Phase3B_Stage0_3_Transport_Certification_Plan_v1.json

37_AMEC_Phase3B_Stage0_3_Owner_PreAuthorization_Pack_v1.md

38_PHASE3B_STAGE0_3_INVARIANT_AUDIT.json

summary.json
```

Locate the actual semantic equivalents if filenames differ.

---

# 1. WHY THIS FINAL ACCEPTANCE GATE EXISTS

The Stage 0.3 run was executed from v1.7 logic.

The later governing correction is v1.8:

> **For historical corpus records, reuse frozen taxonomy before deriving new
> ProposalOps relevance. `business_scope=OUT_OF_SCOPE` must short-circuit
> before relevance, handling, content-read planning, or product-discovery hash
> planning.**

Therefore:

```text
Stage 0.3 v1.7
PASS at its own contract
```

is not sufficient by itself to declare:

```text
Stage 0.3 FINAL / FROZEN
```

until v1.8 conformance is proven.

This phase performs that proof.

---

# 2. GOVERNING TAXONOMY RULE

Canonical business-scope values:

```text
CORE_IN_SCOPE
ADJACENT_RECOGNIZED
OUT_OF_SCOPE
AMBIGUOUS_REVIEW
```

For existing historical corpus records:

```text
frozen Phase-2 business_scope
        ↓
must be consulted first
```

Required routing:

```text
OUT_OF_SCOPE
        ↓
STAGE1R_SKIP
reason = OUT_OF_SCOPE_FROZEN_TAXONOMY
        ↓
STOP
```

For those records:

```text
relevance re-derivation = false

handling re-derivation = false

content-read candidate generation = false

product-discovery hash candidate generation = false

module mapping re-derivation = false

Master Content relevance re-derivation = false
```

This is the highest-priority conformance check.

---

# 3. PRESERVE THE TWO DISTINCT "54" POPULATIONS

There are two independent findings with the same numeric value.

Do NOT merge them.

## 3.1 Object-kind population

```text
54 historical Stage-1 DIRECTORY operations
```

Meaning:

```text
not valid source-file actions
```

They were removed before the 1,468 FILE-action universe.

Required:

```text
HISTORICAL_STAGE1_DIRECTORY_ACTIONS_EXCLUDED=54
```

## 3.2 Frozen business-scope / PII regression population

Independent prior review found:

```text
97 PII-keyword-matched Stage-3 hash-comparison groups

54
business_scope=OUT_OF_SCOPE

24
CORE_IN_SCOPE

14
ADJACENT_RECOGNIZED

remaining
derive exact actual state from source evidence
```

Required:

```text
PII_KEYWORD_GROUPS_WITH_FROZEN_OUT_OF_SCOPE=<actual, expected 54>
```

Never use one value to reconcile the other.

---

# 4. FREEZE ALL INPUT IDENTITIES BEFORE ANALYSIS

Create:

```text
AMEC_Phase3B_Stage0_3_Final_Acceptance_Input_Identity_Manifest_v1.json
```

Compute SHA-256 for every consumed artifact from:

```text
Stage 0.3 output

Phase 2 registry / canonical record source

Phase 2 run contract

Stage 0.1 object-kind closure artifacts

Stage 0.3 v1.8 prompt/contract if locally available

taxonomy v1.0.1
```

Do not hardcode unknown artifact SHAs.

If any consumed artifact changes during the run:

```text
RESULT=BLOCKED

BLOCKER=INPUT_IDENTITY_DRIFT
```

---

# 5. ABSOLUTE SAFETY BOUNDARY

All must remain zero:

```text
BUSINESS_SOURCE_BYTES_READ

BUSINESS_SOURCE_FILE_HASHES

CONTENT_ACTIONS_EXECUTED

SOURCE_CONNECTIONS

SYNOLOGY_CONNECTIONS

NETWORK_DISCOVERY

SOURCE_MUTATIONS

SOURCE_RENAMES

SOURCE_MOVES

SOURCE_DELETES

OCR_RUNS

ARCHIVE_EXTRACTIONS

OPERATIONAL_DB_WRITES

PRODUCT_CODE_CHANGES

DEPLOYMENTS

OWNER_DECISIONS_INVENTED

TAXONOMY_CHANGES

CLASSIFIER_RUNTIME_RULE_CHANGES
```

---

# 6. PRIMARY ACTION UNIVERSE

The final acceptance universe is:

```text
1,468 logical FILE actions
```

from Stage 0.1 object-kind closure.

Do not:

```text
re-add the 54 directories

add Stage 2 actions

add Stage 3 actions

add new files from Synology

expand the source universe
```

Every one of the 1,468 FILE actions must be joined to its immutable Phase-2 record.

---

# 7. IDENTIFIER JOIN — REUSE THE ALREADY CLOSED CONTRACT

Do not recreate the old identifier ambiguity.

Use the Stage 0.1 proven identifier-role closure.

For every Stage0.3 FILE action prove:

```text
action
→ correct Phase-2 immutable record
```

Required:

```text
STAGE0_3_ACTIONS_WITH_MISSING_PHASE2_JOIN=0

STAGE0_3_ACTIONS_WITH_AMBIGUOUS_PHASE2_JOIN=0

STAGE0_3_ACTIONS_JOINED_VIA_WRONG_IDENTIFIER_ROLE=0
```

If the old plan field label remains misleading, use the proven semantic identifier role.

Do not modify Phase 2.

---

# 8. RECONSTRUCT FROZEN BUSINESS_SCOPE FOR ALL 1,468 FILE ACTIONS

Produce exact counts:

```text
FROZEN_BUSINESS_SCOPE_CORE_IN_SCOPE=<n>

FROZEN_BUSINESS_SCOPE_ADJACENT_RECOGNIZED=<n>

FROZEN_BUSINESS_SCOPE_OUT_OF_SCOPE=<n>

FROZEN_BUSINESS_SCOPE_AMBIGUOUS_REVIEW=<n>
```

Require:

```text
sum
=
1,468 logical FILE actions
```

If one physical source supports multiple logical actions, report both:

```text
logical action counts

unique Phase-2 source record counts
```

Do not mix the units.

---

# 9. OUT_OF_SCOPE CONFORMANCE AUDIT

For every logical FILE action whose frozen Phase-2:

```text
business_scope=OUT_OF_SCOPE
```

prove its Stage0.3 handling.

Required final state:

```text
STAGE1R_SKIP
```

with:

```text
reason=OUT_OF_SCOPE_FROZEN_TAXONOMY
```

or a semantic equivalent that explicitly reflects frozen scope authority.

Required zero:

```text
OUT_OF_SCOPE_RECORDS_IN_STAGE1R_A

OUT_OF_SCOPE_RECORDS_IN_STAGE1R_B

OUT_OF_SCOPE_RECORDS_IN_STAGE1R_DEFER

OUT_OF_SCOPE_RELEVANCE_CLASSIFIER_INVOCATIONS

OUT_OF_SCOPE_HANDLING_CLASSIFIER_INVOCATIONS

OUT_OF_SCOPE_CONTENT_READ_CANDIDATES

OUT_OF_SCOPE_STRUCTURE_READ_CANDIDATES

OUT_OF_SCOPE_HASH_CANDIDATES_FOR_PRODUCT_DISCOVERY

OUT_OF_SCOPE_MODULE_REDERIVATIONS

OUT_OF_SCOPE_MASTER_CONTENT_REDERIVATIONS
```

---

# 10. HOW TO PROVE "NO RELEVANCE INVOCATION"

Historical Stage0.3 artifacts may not contain an explicit function-call log.

Do not fabricate one.

Use the strongest available evidence in this order:

```text
1.
actual execution trace / planner trace

2.
per-record audit state showing frozen-scope short-circuit

3.
planner source/control-flow evidence + output disposition

4.
derived forensic reconstruction from recorded Stage0.3 intermediate artifacts
```

Report:

```text
INVOCATION_PROOF_METHOD=<state>
```

If Stage0.3 actually re-derived relevance for an OUT_OF_SCOPE record:

```text
this is a v1.8 conformance defect
```

Repair the derived Stage0.3 layer as specified below.

---

# 11. DO NOT CONFUSE "RELEVANCE RESULT = SKIP" WITH SHORT-CIRCUIT CONFORMANCE

This is critical.

The following is **not** sufficient:

```text
OUT_OF_SCOPE source
→ relevance classifier runs
→ result eventually SKIP
```

v1.8 requires:

```text
OUT_OF_SCOPE source
→ SKIP before relevance invocation
```

This matters for:

```text
cost
unnecessary PII exposure
frozen-decision integrity
determinism
runtime classifier architecture
```

---

# 12. V1.8 CONFORMANCE RESULTS

Classify Stage0.3 into exactly one:

```text
CONFORMANT_NO_REPAIR

CONFORMANT_AFTER_DERIVED_REPAIR

BLOCKED_UNRECOVERABLE_STAGE0_3_DEFECT
```

---

# 13. IF CONFORMANT_NO_REPAIR

Do not regenerate the Stage0.3 plans merely to produce new timestamps.

Preserve the existing:

```text
273 A
343 B
579 DEFER
273 SKIP
```

if they remain exactly correct.

Create only:

```text
acceptance
freeze
manifest
module-coverage closure
budget freeze
handoff
```

artifacts.

---

# 14. IF DERIVED REPAIR IS REQUIRED

Do NOT:

```text
rerun Phase 2

rerun classifier on 251,211 rows

rerun source inventories

touch source files

reclassify frozen business scope
```

Repair only affected Stage0.3 derived artifacts.

At minimum potentially affected:

```text
Product Relevance Audit

Module Evidence Map

Handling / Minimization Audit

Stage1R-A plan/allowlist

Stage1R-B plan/allowlist

Deferred plan

Skipped plan

Relevance Budget

Physical I/O Plan

Stage1R-A Authorization Budget Candidate

Owner Decision Pack

Owner Preauthorization Pack

Invariant Audit

summary.json
```

Write repaired versions with:

```text
FINAL_v1
```

or:

```text
v2
```

suffixes.

Never overwrite the historical v1.7-generated files in place.

---

# 15. REPAIR CONSERVATION

After any derived repair:

```text
STAGE1R_A
+
STAGE1R_B
+
STAGE1R_DEFER
+
STAGE1R_SKIP
=
1,468
```

Required:

```text
STAGE1R_LOGICAL_CONSERVATION_PASS=true
```

Also report unique source-version accounting separately.

---

# 16. TECHNICAL ARTIFACT CARRYFORWARD

Preserve prior technical/system suppression.

Required zero:

```text
CLEAR_SOFTWARE_SYSTEM_SUPPORT_ACTIONS_IN_STAGE1R_A

KNOWN_INSTALLER_ICON_GROUP_IN_STAGE1R_A

CLEAR_TECHNICAL_NOISE_CONTENT_READS

CLEAR_TECHNICAL_NOISE_RELEVANCE_REDERIVATIONS
```

For a business-lineage `.bak`, preserve the previously proven exception behavior.

Do not blanket-exclude all backup artifacts if a concrete duplicate/version question remains.

---

# 17. PII / PERSONAL-DATA BACKSTOP — ONLY AFTER BUSINESS_SCOPE

Required order:

```text
FILE
→ technical gate
→ frozen business_scope
→ OUT_OF_SCOPE? stop
→ relevance
→ handling
→ independent PII path/name backstop
```

Never:

```text
PII keyword
→ override business_scope
```

Run the independent case-insensitive path/name scan against surviving A/B candidates using at minimum:

```text
PASSPORT
QID
IBAN
SALARY
PAYROLL
BANK ACCOUNT
CV
RESUME
NATIONAL ID
DATE OF BIRTH
```

plus established Arabic equivalents if already present in prior rules/evidence.

Required:

```text
PII_KEYWORD_PATH_MATCHES_WITH_HANDLING_CLASS_NORMAL_IN_STAGE1R_A=0

PII_KEYWORD_PATH_MATCHES_WITH_HANDLING_CLASS_NORMAL_IN_STAGE1R_B=0
```

If any mismatch:

```text
repair that derived handling state
→ MINIMIZE_VALUES
or
→ SKIP
```

Do not reclassify business_scope.

---

# 18. SECRET / CREDENTIAL EXCLUSION

Required:

```text
STAGE1R_A_SECRET_EXCLUDE_ACTIONS=0

STAGE1R_B_SECRET_EXCLUDE_ACTIONS=0

CREDENTIAL_OR_SECRET_SOURCE_ACTIONS=0
```

Secrets stay SKIP.

---

# 19. PROVENANCE / AUTHORITY CARRYFORWARD

Keep independent:

```text
Art Mark

ART MEC

United Construction
```

Unresolved provenance may support:

```text
generic product/workflow discovery
```

if Stage0.3 policy allows it.

But it may never support:

```text
AMEC canonical authority
```

Required:

```text
UNRESOLVED_PROVENANCE_USED_AS_AMEC_CANONICAL_AUTHORITY=0

ART_MARK_UNRESOLVED_USED_AS_CANONICAL_AUTHORITY=0

ART_MEC_UNRESOLVED_USED_AS_CANONICAL_AUTHORITY=0

UNITED_CONSTRUCTION_UNRESOLVED_USED_AS_CANONICAL_AUTHORITY=0
```

---

# 20. TRUE OWNER DECISION COMPRESSION

Do not emit hundreds of file-level Owner questions.

At minimum keep independent decision units:

```text
ART_MARK_ORGANIZATIONAL_RELATIONSHIP

ART_MEC_ORGANIZATIONAL_RELATIONSHIP

UNITED_CONSTRUCTION_RELATIONSHIP
```

Any >=1 GB actions that survive later stages must also be explicit Owner decisions.

Stage1R-A currently reports zero >=1 GB actions.

---

# 21. DUPLICATE PROOF-SCOPE CARRYFORWARD

Preserve Stage 0.1 closure.

Required:

```text
FULL_GROUP_EXACT_DUPLICATE_CLAIMS_FROM_PARTIAL_REPRESENTATIVES=0

HASH_ACTIONS_WITH_UNKNOWN_DUPLICATE_GROUP_SCOPE_IN_STAGE1R_A=0

PAIRWISE_REHASH_PLAN_COUNT=0
```

Every Stage1R-A hash action must state:

```text
exactness_business_question

decision_unit_id

original group cardinality

selected members

proof scope

downstream state that can change

stop condition
```

---

# 22. MINIMUM ACCESS CONTRACT

Every Stage1R-A action must be exactly one:

```text
HASH_ONLY

STRUCTURE_READ

BOUNDED_CONTENT_READ
```

Required zero:

```text
STAGE1R_A_ACTIONS_WITH_UNKNOWN_ACCESS_TYPE

STAGE1R_A_OPEN_ENDED_CONTENT_READS

STAGE1R_A_OCR_ACTIONS

STAGE1R_A_ARCHIVE_EXTRACTION_ACTIONS
```

---

# 23. EVERY STAGE1R-A ACTION MUST ANSWER A PRODUCT QUESTION

Required fields:

```text
why_this_informs_proposalops

proposalops_modules[]

relevance_categories[]

product_questions[]

minimum_required_access

retention_policy

stop_condition

priority

provenance_status

canonical_authority_allowed
```

Required zero:

```text
STAGE1R_A_ACTIONS_WITHOUT_PRODUCT_RELEVANCE

STAGE1R_A_ACTIONS_WITHOUT_MODULE_OR_CROSSCUTTING_MAPPING

STAGE1R_A_ACTIONS_WITHOUT_PRODUCT_QUESTION

STAGE1R_A_ACTIONS_WITHOUT_RETENTION_POLICY

STAGE1R_A_ACTIONS_WITHOUT_STOP_CONDITION
```

---

# 24. MODULE-COVERAGE CLOSURE — REQUIRED BEFORE TRANSPORT CERTIFICATION HANDOFF

Stage1R-A is not accepted merely because it is small.

Create a canonical module-evidence closure matrix for:

```text
M1
Intake & Opportunity / BD / Proposal

M2
Contract & Mobilization

M3
Design & Technical Delivery

M4
Regulatory & Submissions

M5
Construction & Post-Approval

M6
Completion & As-Built

M7
Handover & Closeout

FINANCE
Invoices / receivables / payment evidence

MASTER_CONTENT
FORM
REPORT
ENGINEERING_WORK
DEFINITION

REPORTING
report definitions / report instances / report sources

CROSS_CUTTING
Home / Dashboard
My Work
Issues
Notifications
Admin
Audit
Operating Guide implications
```

---

# 25. ALLOWED MODULE-COVERAGE STATES

For each required module/domain use exactly one:

```text
STAGE1R_A_EVIDENCE_IDENTIFIED

STAGE1R_B_EVIDENCE_REQUIRED

METADATA_ALREADY_SUFFICIENT

NO_RELEVANT_CORPUS_EVIDENCE_PRESENT

OWNER_DECISION_REQUIRED

UNRESOLVED_PRODUCT_GAP
```

Do not force Stage1R-A source reads solely to make every row green.

But no module may be silently omitted.

---

# 26. MODULE COVERAGE DETAILS

For each domain report:

```text
module/domain

taxonomy operational bucket

key product questions

metadata evidence already known

Stage1R-A action IDs

Stage1R-B action IDs if required

expected document families

expected app entities/features

Master Content dependencies

workflow implications

source-of-truth questions

remaining unresolved questions

coverage state
```

---

# 27. M1 ACCEPTANCE QUESTIONS

At minimum determine whether planned evidence can inform:

```text
RFQ / tender intake

opportunity identity

proposal / quotation

proposal revision

proposal template

proposal checklist / Form

client/project link

proposal status

award / rejection / approval

handoff to M2
```

---

# 28. M2 ACCEPTANCE QUESTIONS

At minimum:

```text
contract

award / LOA

parties

contract/project relationship

commercial terms

mobilization

contract deliverables

contract-tied guarantees

blank reusable guarantee forms/templates
```

---

# 29. M3 ACCEPTANCE QUESTIONS

At minimum:

```text
engineering deliverable families

discipline

drawing/document number

revision

issue purpose

technical report/specification/calculation

Shop Drawing vs Shop Drawing Submittal

technical data vs submittal workflow
```

---

# 30. M4 ACCEPTANCE QUESTIONS

At minimum distinguish:

```text
PROJECT_APPROVAL

PROFESSIONAL_REGISTRATION

CONSULTANT_OFFICE_REGISTRATION

CORPORATE_CLASSIFICATION

CORPORATE_LICENSE_COMPLIANCE
```

and identify evidence for:

```text
authority

forms

requirements

attachments

application refs

approval/comments/findings

resubmission
```

---

# 31. M5 ACCEPTANCE QUESTIONS

At minimum:

```text
shop drawing submittal

material submittal

contractor submission

site report

review/approval cycle

construction correspondence

inspection/post-approval workflow
```

---

# 32. M6 ACCEPTANCE QUESTIONS

At minimum:

```text
as-built

completion certificate

final inspection

record drawing

completion package

final report

authority closeout
```

---

# 33. M7 ACCEPTANCE QUESTIONS

At minimum distinguish:

```text
PROJECT_TO_CLIENT

PROJECT_TO_OTHER_CONSULTANT

DOCUMENT_CONTROL_HANDOVER

INTERNAL_EMPLOYEE_HANDOVER

DEPARTMENTAL_HANDOVER

FINANCE_HANDOVER
```

Only appropriate project-closeout evidence should support M7 product truth.

---

# 34. FINANCE / INVOICE CLOSURE

This is a mandatory explicit domain.

Confirm planned evidence can inform or explicitly state a gap for:

```text
Invoice

InvoiceRef

invoice issue

due state

payment terms

receivable

PaymentReceipt

outstanding amount

settlement

follow-up

financial account reference

project/contract relationship
```

Preserve:

```text
Paid != Financially Settled

unverified PaymentReceipt != reduce receivable

follow-up note != payment

regulatory payment requirement != AMEC receivable

personal employee IBAN/payroll != Finance truth
```

If Stage1R-A has no Finance evidence and metadata is not sufficient:

```text
coverage state cannot be silently COMPLETE
```

Use:

```text
STAGE1R_B_EVIDENCE_REQUIRED
or
UNRESOLVED_PRODUCT_GAP
```

---

# 35. MASTER CONTENT CLOSURE

Exactly:

```text
FORM

REPORT

ENGINEERING_WORK

DEFINITION
```

Checklist remains a Form.

For each type report evidence for:

```text
blank/reusable vs executed/project instance

source provenance

usage

module applicability

current/version family

Current / Needs Review / Inactive implications

resolver eligibility

canonical-source questions
```

Do not invent a fifth content type.

---

# 36. REPORTING CLOSURE

Distinguish:

```text
report definition/template

executed report instance/output

report source data

report cadence/audience
```

A report definition may support:

```text
Master Content REPORT
```

The executed report/service belongs to reporting/domain behavior.

Home/Dashboard remains a projection.

---

# 37. WORK / ISSUES / NOTIFICATIONS ARE DERIVED

The corpus evidence should identify rules/events.

It must not directly manufacture operational truth from filenames.

Preserve:

```text
Work
= DO

Issues
= BLOCKING / WRONG / CONFLICTING / STALE / RISK

Notifications
= CHANGED / KNOW

Audit
= HAPPENED
```

The module matrix should identify likely triggers, not create live records.

---

# 38. MODULE COVERAGE FINAL GATE

Stage 0.3 can be fully frozen only if:

```text
UNRESOLVED_PRODUCT_GAP
```

is either:

```text
0
```

or every remaining gap is explicitly listed and shown to be:

```text
nonblocking for Stage1R-A transport/evidence run
```

If a missing Finance/Master Content/M1-M7 question is fundamental to deciding what Stage1R-A should read:

```text
repair Stage1R-A candidate before freeze
```

Do not postpone a known critical coverage hole into real-source execution.

---

# 39. RECOMPUTE EXACT STAGE1R-A ACTION MIX

Report:

```text
STAGE1R_A_OPERATIONS=<n>

STAGE1R_A_UNIQUE_FILES=<n>

STAGE1R_A_HASH_ONLY=<n>

STAGE1R_A_STRUCTURE_READ=<n>

STAGE1R_A_BOUNDED_CONTENT_READ=<n>

STAGE1R_A_NORMAL_HANDLING=<n>

STAGE1R_A_MINIMIZE_VALUES=<n>
```

Current expected operations:

```text
273
```

Do not hardcode if repair changes it.

---

# 40. RECOMPUTE EXACT STAGE1R-A BYTE BUDGET

Separately calculate:

```text
LOGICAL_ACTION_BYTES

UNIQUE_SOURCE_VERSION_BYTES

PLANNED_PHYSICAL_FILE_OPENS

PLANNED_PHYSICAL_READ_BYTES_UPPER_BOUND
```

Do not equate them.

---

# 41. PHYSICAL READ PLAN

For every unique Stage1R-A source version produce:

```text
physical_read_plan_id

logical_action_ids[]

planned_physical_open_count

planned_physical_bytes_upper_bound

coalescing_candidate

coalescing_assumption

stop_condition
```

Until transport certification proves coalescing:

```text
do not assume it
```

---

# 42. SIZE-BAND BUDGET

Report:

```text
<1 MB

1–10 MB

10–100 MB

100 MB–1 GB

>=1 GB
```

For each:

```text
logical actions

unique files

unique bytes

physical read bytes upper bound
```

Current Stage1R-A reported:

```text
>=100 MB
0

>=1 GB
0
```

Verify.

---

# 43. BUDGET BY DIMENSION

Report exact Stage1R-A budget by:

```text
share

module

action type

handling class

size band

priority

decision family
```

Use:

```text
record counts
```

and:

```text
bytes
```

as separate dimensions.

Do not repeat the historical mislabeled `source_bytes_by_share` defect.

---

# 44. NON-FUNGIBLE AUTHORIZATION CONTRACT

The future Owner/ChatGPT authorization must pin:

```text
exact action IDs
```

Unused budget is not transferable.

If action A is skipped:

```text
its bytes do not authorize action D
```

---

# 45. FREEZE STAGE1R-A CANDIDATE IDENTITIES

Create:

```text
STAGE1R_A_PLAN_SHA256

STAGE1R_A_ALLOWLIST_SHA256

STAGE1R_A_ACTION_IDS_SHA256

STAGE1R_A_PHYSICAL_IO_PLAN_SHA256

STAGE1R_A_BUDGET_SHA256

MODULE_COVERAGE_MATRIX_SHA256
```

These become the exact candidate inputs for transport certification review and later authorization.

---

# 46. TRANSPORT CONTRACT ACCEPTANCE — DESIGN ONLY

Review the Stage0.3 transport contract.

Do not execute it.

Require design support for:

```text
exact share/path source selection

FILE only

no fuzzy fallback

no latest-file substitution

no symlink/shortcut following

source-version precondition

pre-read metadata

bounded reads

post-read metadata

SHA-256 streaming

safe parser handoff

checkpoint/resume

audit

zero source mutation
```

---

# 47. TRANSPORT CAPABILITY MATRIX

Report theoretical support separately:

```text
HASH_ONLY

STRUCTURE_READ

BOUNDED_CONTENT_READ
```

Use states:

```text
DESIGN_SUPPORTED

DESIGN_UNRESOLVED

NOT_SUPPORTED
```

Do not claim:

```text
VERIFIED_AVAILABLE
```

before Phase 3B.0.4.

---

# 48. FORMAT / PARSER CARRYFORWARD

For planned Stage1R-A content actions report format.

Candidate future handling:

```text
PDF
text layer only

DOCX
safe package text/structure

XLSX
specific sheets/cells; no macro/external-link execution

PPTX
bounded text/structure

EML/MSG
no remote content; attachments separately controlled

image/scan
OCR_REQUIRED_NOT_AUTHORIZED

archive
ARCHIVE_EXTRACTION_NOT_AUTHORIZED

CAD/binary
no content parse unless specifically certified
```

If a Stage1R-A `STRUCTURE_READ` or `BOUNDED_CONTENT_READ` action has no safe theoretical parser:

```text
move to Stage1R-B or DEFER
```

Do not leave an impossible action in A.

---

# 49. PHASE 3B.0.4 HANDOFF BUNDLE

Create an immutable handoff artifact:

```text
AMEC_Phase3B_Stage0_3_to_0_4_Transport_Certification_Handoff_v1.json
AMEC_Phase3B_Stage0_3_to_0_4_Transport_Certification_Handoff_v1.md
```

Pin:

```text
Stage0.3 Final Freeze Manifest SHA

Stage1R-A Plan SHA

Stage1R-A Allowlist SHA

Stage1R-A Action IDs SHA

Physical I/O Plan SHA

Budget SHA

Module Coverage Matrix SHA

Transport Contract SHA

Transport Certification Plan SHA

taxonomy revision

classifier/rules authority used for historical corpus
```

---

# 50. TRANSPORT CERTIFICATION REMAINS NON-BUSINESS

Handoff must state:

```text
PHASE3B_0_4_BUSINESS_SOURCE_ACCESS_AUTHORIZED=false
```

Certification input must be:

```text
synthetic
or
explicitly non-business
```

No real AMEC source reads in 0.4.

---

# 51. NO STAGE1R-A AUTHORIZATION YET

This phase freezes the candidate.

It does NOT authorize it.

Required:

```text
STAGE1R_A_EXECUTION_AUTHORIZED=false

STAGE1R_B_EXECUTION_AUTHORIZED=false

STAGE2_EXECUTION_AUTHORIZED=false

STAGE3_EXECUTION_AUTHORIZED=false
```

After transport certification, an exact Stage1R-A authorization can be issued using the frozen hashes.

---

# 52. FINAL STAGE 0.3 FREEZE MANIFEST

Create:

```text
AMEC_Phase3B_Stage0_3_FINAL_Freeze_Manifest_v1.json
AMEC_Phase3B_Stage0_3_FINAL_Freeze_Manifest_v1.md
```

It must identify:

```text
historical v1.7 result

v1.8 conformance result

whether derived repair occurred

exact final artifact filenames

exact SHA-256s

final lane counts

final Stage1R-A budget

module coverage state

known unresolved Owner decisions

known deferred/nonblocking product gaps

transport design state

source-access state
```

---

# 53. HISTORICAL ARTIFACT PRESERVATION

Do not delete/replace:

```text
v1.7 Stage0.3 artifacts
```

If repair occurs:

```text
historical_v1
→ provenance only

FINAL/v2
→ current Stage0.3 authority
```

---

# 54. REQUIRED EVIDENCE DIRECTORY

Create outside Git:

```text
<local ProposalOps-Control>/
proposalops-amec-corpus-phase3b-stage0-3-final-acceptance-evidence-<run-id>/
```

---

# 55. REQUIRED ARTIFACTS

At minimum:

```text
01_PHASE3B_STAGE0_3_FINAL_ACCEPTANCE_PROVENANCE.md

02_AMEC_Phase3B_Stage0_3_Final_Acceptance_Input_Identity_Manifest_v1.json

03_AMEC_Phase3B_Stage0_3_v1_8_Business_Scope_Conformance_Audit_v1.csv
04_AMEC_Phase3B_Stage0_3_v1_8_Business_Scope_Conformance_Audit_v1.json
05_AMEC_Phase3B_Stage0_3_v1_8_Business_Scope_Conformance_Audit_v1.md

06_AMEC_Phase3B_Stage0_3_Two_54_Populations_Reconciliation_v1.json
07_AMEC_Phase3B_Stage0_3_Two_54_Populations_Reconciliation_v1.md

08_AMEC_Phase3B_Stage0_3_PII_Backstop_Final_Audit_v1.json
09_AMEC_Phase3B_Stage0_3_PII_Backstop_Final_Audit_v1.md

10_AMEC_Phase3B_Stage0_3_Module_Coverage_Closure_v1.csv
11_AMEC_Phase3B_Stage0_3_Module_Coverage_Closure_v1.json
12_AMEC_Phase3B_Stage0_3_Module_Coverage_Closure_v1.md

13_AMEC_Phase3B_Stage0_3_Stage1R_A_Final_Action_Audit_v1.json
14_AMEC_Phase3B_Stage0_3_Stage1R_A_Final_Action_Audit_v1.md

15_AMEC_Phase3B_Stage0_3_Stage1R_A_Final_Budget_v1.json
16_AMEC_Phase3B_Stage0_3_Stage1R_A_Final_Budget_v1.md

17_AMEC_Phase3B_Stage0_3_Stage1R_A_Final_Physical_IO_Plan_v1.json
18_AMEC_Phase3B_Stage0_3_Stage1R_A_Final_Physical_IO_Plan_v1.md

19_AMEC_Phase3B_Stage0_3_Transport_Design_Acceptance_v1.json
20_AMEC_Phase3B_Stage0_3_Transport_Design_Acceptance_v1.md

21_AMEC_Phase3B_Stage0_3_to_0_4_Transport_Certification_Handoff_v1.json
22_AMEC_Phase3B_Stage0_3_to_0_4_Transport_Certification_Handoff_v1.md

23_AMEC_Phase3B_Stage0_3_FINAL_Freeze_Manifest_v1.json
24_AMEC_Phase3B_Stage0_3_FINAL_Freeze_Manifest_v1.md

25_AMEC_Phase3B_Stage0_3_FINAL_Owner_PreAuthorization_Pack_v1.md

26_PHASE3B_STAGE0_3_FINAL_INVARIANT_AUDIT.json
27_PHASE3B_STAGE0_3_FINAL_INVARIANT_AUDIT.md

summary.json
```

If a derived repair is required, include repaired plan/budget artifacts in this directory and list them in the freeze manifest.

---

# 56. REQUIRED SUMMARY CONTRACT

Create:

```json
{
  "phase": "AMEC_PHASE3B_STAGE0_3_FINAL_ACCEPTANCE_AND_FREEZE",
  "revision": "v1.9",

  "result": "PASS|PASS_WITH_DERIVED_REPAIR|BLOCKED",

  "stage0_3_final_state": "FROZEN|NOT_FROZEN",

  "v1_8_conformance": {
    "state": "CONFORMANT_NO_REPAIR|CONFORMANT_AFTER_DERIVED_REPAIR|BLOCKED_UNRECOVERABLE_STAGE0_3_DEFECT",

    "frozen_business_scope_core_in_scope": 0,
    "frozen_business_scope_adjacent_recognized": 0,
    "frozen_business_scope_out_of_scope": 0,
    "frozen_business_scope_ambiguous_review": 0,

    "out_of_scope_relevance_classifier_invocations": 0,
    "out_of_scope_handling_classifier_invocations": 0,
    "out_of_scope_content_read_candidates": 0,
    "out_of_scope_structure_read_candidates": 0,
    "out_of_scope_hash_candidates_for_product_discovery": 0,
    "out_of_scope_records_in_stage1r_a": 0,
    "out_of_scope_records_in_stage1r_b": 0,
    "out_of_scope_records_in_stage1r_defer": 0
  },

  "population_reconciliation": {
    "historical_stage1_directory_actions_excluded": 54,
    "stage1_file_actions": 1468,
    "pii_keyword_groups_with_frozen_out_of_scope": 0,
    "two_54_populations_conflated": false
  },

  "final_lanes": {
    "stage1r_a_operations": 0,
    "stage1r_b_operations": 0,
    "stage1r_defer_operations": 0,
    "stage1r_skip_operations": 0,
    "logical_conservation_pass": false
  },

  "stage1r_a": {
    "unique_files": 0,

    "hash_only": 0,
    "structure_read": 0,
    "bounded_content_read": 0,

    "logical_action_bytes": 0,
    "unique_source_version_bytes": 0,
    "planned_physical_file_opens": 0,
    "planned_physical_read_bytes_upper_bound": 0,

    "normal_handling": 0,
    "minimize_values_handling": 0,

    "ge_100mb_actions": 0,
    "ge_1gb_actions": 0
  },

  "module_coverage": {
    "M1": "",
    "M2": "",
    "M3": "",
    "M4": "",
    "M5": "",
    "M6": "",
    "M7": "",
    "FINANCE": "",
    "MASTER_CONTENT_FORM": "",
    "MASTER_CONTENT_REPORT": "",
    "MASTER_CONTENT_ENGINEERING_WORK": "",
    "MASTER_CONTENT_DEFINITION": "",
    "REPORTING": "",
    "CROSS_CUTTING": ""
  },

  "owner_decisions": {
    "art_mark_relationship": "PENDING|RESOLVED|NOT_APPLICABLE",
    "art_mec_relationship": "PENDING|RESOLVED|NOT_APPLICABLE",
    "united_construction_relationship": "PENDING|RESOLVED|NOT_APPLICABLE"
  },

  "transport": {
    "design_accepted": false,
    "hash_only_design_supported": false,
    "structure_read_design_supported": false,
    "bounded_content_read_design_supported": false,
    "verified_available": false,
    "certification_executed": false
  },

  "freeze": {
    "stage1r_a_plan_sha256": "",
    "stage1r_a_allowlist_sha256": "",
    "stage1r_a_action_ids_sha256": "",
    "stage1r_a_budget_sha256": "",
    "stage1r_a_physical_io_plan_sha256": "",
    "module_coverage_sha256": "",
    "freeze_manifest_sha256": ""
  },

  "safety": {
    "business_source_bytes_read": 0,
    "business_source_file_hashes": 0,
    "content_actions_executed": 0,
    "source_connections": 0,
    "source_mutations": 0
  },

  "authorization": {
    "phase3b_0_4_business_source_access_authorized": false,
    "stage1r_a_execution_authorized": false,
    "stage1r_b_execution_authorized": false,
    "stage2_execution_authorized": false,
    "stage3_execution_authorized": false
  },

  "ready_for_phase3b_0_4_transport_certification": false,

  "next": ""
}
```

---

# 57. FINAL HARD INVARIANTS

All required zero:

```text
STAGE0_3_ACTIONS_WITH_MISSING_PHASE2_JOIN

STAGE0_3_ACTIONS_WITH_AMBIGUOUS_PHASE2_JOIN

STAGE0_3_ACTIONS_JOINED_VIA_WRONG_IDENTIFIER_ROLE

OUT_OF_SCOPE_RELEVANCE_CLASSIFIER_INVOCATIONS

OUT_OF_SCOPE_HANDLING_CLASSIFIER_INVOCATIONS

OUT_OF_SCOPE_CONTENT_READ_CANDIDATES

OUT_OF_SCOPE_STRUCTURE_READ_CANDIDATES

OUT_OF_SCOPE_HASH_CANDIDATES_FOR_PRODUCT_DISCOVERY

OUT_OF_SCOPE_RECORDS_IN_STAGE1R_A

OUT_OF_SCOPE_RECORDS_IN_STAGE1R_B

OUT_OF_SCOPE_RECORDS_IN_STAGE1R_DEFER

CLEAR_SOFTWARE_SYSTEM_SUPPORT_ACTIONS_IN_STAGE1R_A

KNOWN_INSTALLER_ICON_GROUP_IN_STAGE1R_A

PII_KEYWORD_PATH_MATCHES_WITH_HANDLING_CLASS_NORMAL_IN_STAGE1R_A

PII_KEYWORD_PATH_MATCHES_WITH_HANDLING_CLASS_NORMAL_IN_STAGE1R_B

STAGE1R_A_SECRET_EXCLUDE_ACTIONS

CREDENTIAL_OR_SECRET_SOURCE_ACTIONS

UNRESOLVED_PROVENANCE_USED_AS_AMEC_CANONICAL_AUTHORITY

FULL_GROUP_EXACT_DUPLICATE_CLAIMS_FROM_PARTIAL_REPRESENTATIVES

HASH_ACTIONS_WITH_UNKNOWN_DUPLICATE_GROUP_SCOPE_IN_STAGE1R_A

PAIRWISE_REHASH_PLAN_COUNT

STAGE1R_A_ACTIONS_WITH_UNKNOWN_ACCESS_TYPE

STAGE1R_A_OPEN_ENDED_CONTENT_READS

STAGE1R_A_OCR_ACTIONS

STAGE1R_A_ARCHIVE_EXTRACTION_ACTIONS

STAGE1R_A_ACTIONS_WITHOUT_PRODUCT_RELEVANCE

STAGE1R_A_ACTIONS_WITHOUT_MODULE_OR_CROSSCUTTING_MAPPING

STAGE1R_A_ACTIONS_WITHOUT_PRODUCT_QUESTION

STAGE1R_A_ACTIONS_WITHOUT_RETENTION_POLICY

STAGE1R_A_ACTIONS_WITHOUT_STOP_CONDITION

MINIMIZE_VALUES_ACTIONS_WITH_UNBOUNDED_RETENTION

SOURCE_CONNECTIONS

BUSINESS_SOURCE_BYTES_READ

BUSINESS_SOURCE_FILE_HASHES

SOURCE_MUTATIONS
```

---

# 58. PASS GATE — FINAL STAGE 0.3 FREEZE

Stage0.3 may be frozen only if:

```text
[ ] exact Stage0.3 input identities pinned

[ ] 1,468 FILE-action universe reconciled

[ ] 54 directory operations remain independently excluded

[ ] frozen Phase-2 business_scope joined before relevance

[ ] every OUT_OF_SCOPE action short-circuits before relevance

[ ] two independent "54" populations explicitly reconciled

[ ] PII backstop operates after business_scope, not instead of it

[ ] technical noise remains suppressed

[ ] secrets remain excluded

[ ] provenance authority rules preserved

[ ] duplicate proof-scope rules preserved

[ ] all Stage1R-A actions have complete minimum-access/product-question contracts

[ ] module coverage explicitly assessed for M1-M7

[ ] Finance/Invoices explicitly assessed

[ ] Master Content FORM/REPORT/ENGINEERING_WORK/DEFINITION explicitly assessed

[ ] Reporting explicitly assessed

[ ] cross-cutting Home/My Work/Issues/Notifications/Admin/Audit implications assessed

[ ] no blocking module coverage hole remains hidden

[ ] exact Stage1R-A action mix recomputed

[ ] exact logical/unique/physical I/O budget recomputed

[ ] size-band budget recomputed

[ ] Stage1R-A >=100MB and >=1GB state verified

[ ] candidate artifact SHAs frozen

[ ] transport design accepted

[ ] transport not executed

[ ] Phase3B.0.4 handoff produced

[ ] zero business-source access
```

---

# 59. RESULT = PASS

Use when:

```text
v1.7 output already satisfies v1.8
```

and no derived plan changes are required.

Expected final lane counts may remain:

```text
A=273
B=343
DEFER=579
SKIP=273
```

but derive, do not assume.

---

# 60. RESULT = PASS_WITH_DERIVED_REPAIR

Use when:

```text
v1.7 violated v1.8 only in derived Stage0.3 planning
```

and the issue is repaired without changing upstream frozen truth.

Report:

```text
what changed

which actions changed lanes

why

old lane counts

new lane counts

budget delta

module-coverage delta

new artifact SHAs
```

Historical v1.7 remains preserved.

---

# 61. RESULT = BLOCKED

Only if a genuine unrecoverable defect exists, such as:

```text
cannot join Stage0.3 actions to Phase2 authority

input artifacts drift

Stage0.3 population cannot conserve

source record identity ambiguity unresolved

critical module coverage cannot be planned from available metadata and requires a new Owner decision before transport certification

transport design cannot theoretically support the frozen Stage1R-A action mix
```

Do not return BLOCKED merely because:

```text
Art Mark is unresolved

Stage1R-B exists

deferred actions exist

Stage2/Stage3 are incomplete

sensitivity contract is imperfect for production
```

unless one actually contaminates Stage1R-A acceptance.

---

# 62. FINAL HANDOFF FORMAT

On PASS:

```text
PROPOSALOPS_AMEC_PHASE3B_STAGE0_3_FINAL_ACCEPTANCE_COMPLETE

RESULT=<PASS|PASS_WITH_DERIVED_REPAIR>

STAGE0_3_FINAL_STATE=FROZEN

V1_8_CONFORMANCE=<state>

HISTORICAL_STAGE1_DIRECTORY_ACTIONS_EXCLUDED=54

STAGE1_FILE_ACTIONS=1468

FROZEN_BUSINESS_SCOPE_CORE_IN_SCOPE=<n>
FROZEN_BUSINESS_SCOPE_ADJACENT_RECOGNIZED=<n>
FROZEN_BUSINESS_SCOPE_OUT_OF_SCOPE=<n>
FROZEN_BUSINESS_SCOPE_AMBIGUOUS_REVIEW=<n>

OUT_OF_SCOPE_RELEVANCE_CLASSIFIER_INVOCATIONS=0
OUT_OF_SCOPE_HANDLING_CLASSIFIER_INVOCATIONS=0
OUT_OF_SCOPE_CONTENT_READ_CANDIDATES=0
OUT_OF_SCOPE_HASH_CANDIDATES_FOR_PRODUCT_DISCOVERY=0

PII_KEYWORD_GROUPS_WITH_FROZEN_OUT_OF_SCOPE=<n>
TWO_54_POPULATIONS_CONFLATED=false

STAGE1R_A_OPERATIONS=<n>
STAGE1R_B_OPERATIONS=<n>
STAGE1R_DEFER_OPERATIONS=<n>
STAGE1R_SKIP_OPERATIONS=<n>

STAGE1R_CONSERVATION_PASS=true

STAGE1R_A_UNIQUE_FILES=<n>

STAGE1R_A_HASH_ONLY=<n>
STAGE1R_A_STRUCTURE_READ=<n>
STAGE1R_A_BOUNDED_CONTENT_READ=<n>

STAGE1R_A_LOGICAL_ACTION_BYTES=<bytes>
STAGE1R_A_UNIQUE_SOURCE_VERSION_BYTES=<bytes>
STAGE1R_A_PHYSICAL_FILE_OPENS=<n>
STAGE1R_A_PHYSICAL_READ_BYTES_UPPER_BOUND=<bytes>

STAGE1R_A_GE_100MB=<n>
STAGE1R_A_GE_1GB=<n>

MODULE_COVERAGE_M1=<state>
MODULE_COVERAGE_M2=<state>
MODULE_COVERAGE_M3=<state>
MODULE_COVERAGE_M4=<state>
MODULE_COVERAGE_M5=<state>
MODULE_COVERAGE_M6=<state>
MODULE_COVERAGE_M7=<state>

MODULE_COVERAGE_FINANCE=<state>

MODULE_COVERAGE_MASTER_CONTENT_FORM=<state>
MODULE_COVERAGE_MASTER_CONTENT_REPORT=<state>
MODULE_COVERAGE_MASTER_CONTENT_ENGINEERING_WORK=<state>
MODULE_COVERAGE_MASTER_CONTENT_DEFINITION=<state>

MODULE_COVERAGE_REPORTING=<state>
MODULE_COVERAGE_CROSS_CUTTING=<state>

ART_MARK_OWNER_DECISION=<state>
ART_MEC_OWNER_DECISION=<state>
UNITED_CONSTRUCTION_OWNER_DECISION=<state>

UNRESOLVED_PROVENANCE_USED_AS_AMEC_CANONICAL_AUTHORITY=0

FULL_GROUP_EXACT_DUPLICATE_CLAIMS_FROM_PARTIAL_REPRESENTATIVES=0

STAGE1R_A_PLAN_SHA256=<sha>
STAGE1R_A_ALLOWLIST_SHA256=<sha>
STAGE1R_A_ACTION_IDS_SHA256=<sha>
STAGE1R_A_BUDGET_SHA256=<sha>
STAGE1R_A_PHYSICAL_IO_PLAN_SHA256=<sha>
MODULE_COVERAGE_MATRIX_SHA256=<sha>
STAGE0_3_FINAL_FREEZE_MANIFEST_SHA256=<sha>

TRANSPORT_DESIGN_ACCEPTED=true
TRANSPORT_VERIFIED_AVAILABLE=false
TRANSPORT_CERTIFICATION_EXECUTED=false

BUSINESS_SOURCE_BYTES_READ=0
BUSINESS_SOURCE_FILE_HASHES=0
SOURCE_CONNECTIONS=0
SOURCE_MUTATIONS=0

PHASE3B_0_4_BUSINESS_SOURCE_ACCESS_AUTHORIZED=false

STAGE1R_A_EXECUTION_AUTHORIZED=false
STAGE1R_B_EXECUTION_AUTHORIZED=false
STAGE2_EXECUTION_AUTHORIZED=false
STAGE3_EXECUTION_AUTHORIZED=false

READY_FOR_PHASE3B_0_4_TRANSPORT_CERTIFICATION=true

EVIDENCE_DIR=<path>

NEXT=Phase 3B.0.4 synthetic/non-business read-only transport certification using the exact frozen handoff bundle; no real AMEC source access.
```

---

# 63. WHAT HAPPENS AFTER THIS PASSES

The sequence is frozen:

```text
Stage0.3 FINAL
        ↓
Phase 3B.0.4
synthetic/non-business transport certification
        ↓
review exact certification evidence
        ↓
exact Stage1R-A authorization
        ↓
Stage1R-A real AMEC evidence execution
        ↓
STOP
        ↓
evidence sufficiency / module-gap review
        ↓
only necessary Stage1R-B subset, if any
        ↓
Phase 3C canonical Module Truth Contract
        ↓
Phase 4 Corpus → App Integration Contract freeze
```

Do not start Phase 5 continuous trigger/writeback work yet.

Finish this historical corpus truth chain first.

---

# 64. NO MORE METADATA-PLANNING LOOP

If this phase returns PASS:

```text
Stage0.3 metadata planning is CLOSED.
```

Do not create:

```text
Stage0.3.1
Stage0.3.2
another sensitivity pass
another relevance pass
another generic duplicate pass
```

unless new executable evidence proves a material defect.

The next technical step is transport certification.

# END
