# CODEX MASTER EXECUTION PROMPT
# ProposalOps / AMEC — Phase 3B.0.5 v1.0
# Exact Stage1R-A Execution Authorization
# + Frozen Action/Source/Reader/Io Contract
# + Owner Authorization Attestation
# + Non-Fungible Budget
# + Stop-Condition Execution Schedule
# + First Real AMEC Evidence-Run Handoff
#
# THIS IS AN AUTHORIZATION GATE.
# IT IS NOT A SOURCE-READ PHASE.
#
# ZERO REAL AMEC BUSINESS-SOURCE BYTES MAY BE READ IN PHASE 0.5.
# ZERO REAL AMEC SOURCE HASHES.
# ZERO REAL AMEC CONTENT PARSING.
# ZERO SYNOLOGY SOURCE CONNECTIONS FOR BUSINESS FILES.
# ZERO SOURCE MUTATIONS.
#
# The first real AMEC source read occurs ONLY in the later:
#
#   Phase 3B Stage1R-A — Real Evidence Execution
#
# and only after this Phase 0.5 has produced a valid, explicit, immutable
# authorization whose hashes exactly match the frozen Stage0.3 plan and the
# certified Phase0.4 execution substrate.
#
# PHASE 0.5 MUST NOT:
# - perform new relevance analysis
# - change taxonomy
# - change Stage1R-A membership
# - change product questions
# - change action types
# - enlarge source I/O budgets
# - substitute source paths
# - authorize Stage1R-B / Stage2 / Stage3
# - authorize OCR or general archive extraction
# - send source content to cloud LLMs
# - index source content into a vector DB
# - ingest source content into ProposalOps
#
# A successful 0.5 transforms:
#
#   FROZEN + CERTIFIED + CANDIDATE
#
# into:
#
#   FROZEN + CERTIFIED + EXACTLY AUTHORIZED
#
# for a specific immutable Stage1R-A execution envelope.

---

# 0. ENTRY GATE

Phase 0.5 may begin only when Phase 3B.0.4 reports:

```text
RESULT=PASS

READY_FOR_PHASE3B_0_5_EXACT_EXECUTION_AUTHORIZATION=true
```

and the Stage0.3 final state remains:

```text
STAGE0_3_FINAL_STATE=FROZEN
```

Expected historical baseline, verify rather than assume:

```text
Stage1R-A logical actions
273

Stage1R-A unique source files
272

Stage1R-A physical-read upper bound
940,387,450 bytes

Stage1R-A >=100 MB actions
0

Stage1R-A >=1 GB actions
0
```

If Phase0.4 has not passed:

```text
RESULT=BLOCKED
BLOCKER=PHASE3B_0_4_NOT_CERTIFIED
```

Do not manufacture authorization.

---

# 1. PURPOSE

Create one immutable execution authorization tying together:

```text
WHAT
exact Stage1R-A action IDs

WHERE
exact frozen source selectors

WHICH VERSION
exact source-version preconditions

HOW
exact certified read operation + reader

HOW MUCH
exact logical + physical I/O ceilings

WHAT MAY BE RETAINED
exact evidence/minimization contract

WHEN TO STOP
exact decision-unit stop conditions

WHO APPROVED
explicit Owner authorization evidence

WHAT REMAINS PROHIBITED
everything outside the envelope
```

The authorization must be machine-checkable.

A human saying:

```text
"go ahead with Stage1R-A"
```

without the exact immutable authorization manifest is insufficient.

---

# 2. GOVERNING PREDECESSOR AUTHORITIES

Consume and pin the exact final artifacts from:

```text
Phase 3B Stage0.3 FINAL Acceptance / Freeze

Phase 3B.0.4 Transport + Evidence Reader Certification
```

At minimum consume:

```text
Stage0.3 FINAL Freeze Manifest

Stage1R-A Final Plan

Stage1R-A Final Allowlist

Stage1R-A Action-ID set

Stage1R-A Final Budget

Stage1R-A Final Physical I/O Plan

Stage0.3 Module Coverage Matrix

Stage0.3 Owner Preauthorization Pack

Stage0.3 → 0.4 handoff

Phase0.4 Certification Freeze Manifest

Phase0.4 Capability Matrix

Phase0.4 Stage1R-A Compatibility Audit

Phase0.4 Runtime I/O Meter Certification

Phase0.4 Failure Injection Results

Phase0.4 Production Network Path Proof

Phase0.4 → 0.5 Authorization Handoff
```

Locate actual semantic equivalents if filenames differ.

---

# 3. IMMUTABLE INPUT IDENTITY

Create:

```text
AMEC_Phase3B_0_5_Frozen_Input_Identity_Manifest_v1.json
AMEC_Phase3B_0_5_Frozen_Input_Identity_Manifest_v1.md
```

For every consumed predecessor artifact record:

```text
path

role

sha256

source phase

authoritative status
```

Compare to predecessor freeze/handoff manifests.

Required:

```text
STAGE0_3_FROZEN_SHA_MISMATCHES=0

PHASE0_4_CERTIFICATION_SHA_MISMATCHES=0
```

If any mismatch:

```text
RESULT=BLOCKED
BLOCKER=PREDECESSOR_IDENTITY_DRIFT
```

---

# 4. NO REAL SOURCE ACCESS IN 0.5

Required zero:

```text
REAL_AMEC_BUSINESS_SOURCE_FILES_OPENED

REAL_AMEC_BUSINESS_SOURCE_BYTES_READ

REAL_AMEC_BUSINESS_SOURCE_HASHES

REAL_AMEC_BUSINESS_CONTENT_PARSED

SYNOLOGY_BUSINESS_SOURCE_CONNECTIONS

SOURCE_MUTATIONS
```

Do not:

```text
refresh mtime
test one path
re-stat a real file
test ACL with a business source
```

Phase0.4 certified the execution substrate.

Stage1R-A execution performs fresh source-version preconditions immediately
before each future real source read.

---

# 5. AUTHORIZATION IS NOT RELEVANCE RE-ANALYSIS

Stage0.3 already decided:

```text
why each action informs ProposalOps

module mapping

product questions

minimum access type

handling/minimization

stop condition
```

Phase0.5 may validate completeness.

It may not decide relevance again.

Required:

```text
NEW_RELEVANCE_CLASSIFICATIONS=0

TAXONOMY_CHANGES=0

STAGE1R_A_ACTION_TYPE_CHANGES=0

STAGE1R_A_PRODUCT_QUESTION_CHANGES=0
```

---

# 6. EXACT ACTION-SET RECONCILIATION

Reconstruct the canonical ordered Stage1R-A action set.

Canonicalization:

```text
extract exact action_id values

validate uniqueness

sort lexicographically by exact UTF-8 action_id

join using LF (`\n`)

final trailing LF = yes

SHA-256 exact bytes
```

Produce:

```text
STAGE1R_A_ACTION_IDS_SHA256
```

Compare with the frozen Stage0.3 / Phase0.4 value.

Required:

```text
STAGE1R_A_ACTION_ID_COUNT=<actual>

STAGE1R_A_DUPLICATE_ACTION_IDS=0

STAGE1R_A_ACTION_ID_SET_DRIFT=0
```

Expected action count:

```text
273
```

derive, do not hardcode.

---

# 7. EXACT UNIQUE SOURCE-SET RECONCILIATION

For each action resolve the exact frozen:

```text
phase2_corpus_record_id

registry_record_id where present

share

relative_path

record_type=FILE

expected_size

expected_mtime / observation

source_version_precondition
```

Create a canonical unique source-selector set.

Required:

```text
SOURCE_SELECTORS_WITH_MISSING_IDENTITY=0

SOURCE_SELECTORS_WITH_AMBIGUOUS_IDENTITY=0

SOURCE_SELECTORS_WITH_NON_FILE_OBJECT=0
```

Expected unique source count:

```text
272
```

derive, do not hardcode.

---

# 8. AUTHORIZATION BINDS TO SOURCE VERSION — NOT "WHATEVER IS LATEST"

Every authorized action is bound to its frozen source-version precondition.

Never authorize:

```text
latest

newest

current-looking

nearest path

same filename elsewhere

future replacement version
```

If the source changes before Stage1R-A executes:

```text
SOURCE_VERSION_PRECONDITION_FAILED
```

That action's authorization is invalid for the changed bytes.

Required future result:

```text
NOT_EXECUTED_SOURCE_VERSION_DRIFT
```

Do not automatically substitute the new version.

---

# 9. SOURCE-DRIFT REAUTHORIZATION RULE

A changed source version is a new evidence candidate.

If still needed:

```text
reconcile changed source
→ prove relevance remains applicable
→ create a new versioned action/authorization amendment
```

Do not reuse the old action authorization against different bytes.

Required:

```text
AUTHORIZED_ACTIONS_ALLOWING_LATEST_SUBSTITUTION=0
```

---

# 10. CERTIFIED CAPABILITY JOIN

Join every Stage1R-A action to Phase0.4:

```text
certified transport

certified format × action capability

certified reader implementation/version

certified parser implementation/version if applicable

certified source-version semantics

certified budget meter

certified checkpoint/restart

certified audit contract
```

Required:

```text
AUTHORIZED_ACTIONS_WITH_UNCERTIFIED_CAPABILITY=0
```

Any uncertified required capability blocks authorization.

Do not downgrade the operation.

---

# 11. READER / TRANSPORT VERSION PINNING

Authorization must pin:

```text
transport_implementation_id

transport_implementation_sha256

reader_id

reader_version

reader_sha256 / code SHA where available

parser_security_contract_sha256

runtime_io_meter_version / SHA

audit_envelope_version
```

If Stage1R-A execution later uses a different material implementation:

```text
AUTHORIZATION_IMPLEMENTATION_MISMATCH
```

and the action does not execute until compatibility/reauthorization is proven.

---

# 12. PRODUCTION NETWORK PATH PINNING

Authorization must reference the exact certified Phase0.4 production network
boundary.

Pin:

```text
Azure region

execution network equivalence class

private connectivity mode

Synology endpoint

production read principal / certified equivalent identity

source-share transport-equivalence classes
```

No Stage1R-A execution through:

```text
developer laptop

office LAN shortcut

public Internet path

different Azure region

uncertified VPN/tunnel
```

Required:

```text
AUTHORIZED_PRODUCTION_NETWORK_PATH_SHA256=<sha>
```

---

# 13. AUTHORIZED OPERATION TYPES

Only:

```text
HASH_ONLY

STRUCTURE_READ

BOUNDED_CONTENT_READ
```

as already frozen per action.

Required:

```text
AUTHORIZED_OCR_ACTIONS=0

AUTHORIZED_GENERAL_ARCHIVE_EXTRACTION_ACTIONS=0

AUTHORIZED_UNBOUNDED_CONTENT_READ_ACTIONS=0
```

---

# 14. CLOUD LLM / VECTOR DB / RAG ARE NOT AUTHORIZED IN STAGE1R-A

Stage1R-A is the first real-source evidence acquisition phase.

Keep its boundary narrow.

Required:

```text
EXTERNAL_CLOUD_LLM_SOURCE_CONTENT_UPLOAD_AUTHORIZED=false

VECTOR_DB_INDEXING_AUTHORIZED=false

PRODUCTION_SEARCH_INDEXING_AUTHORIZED=false

PRODUCTION_RAG_INDEXING_AUTHORIZED=false

PRODUCTION_AI_RETRIEVAL_AUTHORIZED=false
```

This does not decide the future Classifier v2 architecture.

It only keeps this first real evidence run controlled and evidence-oriented.

---

# 15. PRODUCT INGESTION IS NOT AUTHORIZED

Required:

```text
DOCUMENTVERSION_CREATION_AUTHORIZED=false

MASTERCONTENT_CREATION_AUTHORIZED=false

BUSINESS_DB_PROJECTION_AUTHORIZED=false

VERIFIEDASSERTION_PRODUCT_WRITE_AUTHORIZED=false

PRODUCTION_STORAGE_PROMOTION_AUTHORIZED=false

DEPLOYMENT_AUTHORIZED=false
```

Stage1R-A evidence remains external/restricted.

---

# 16. RAW SOURCE COPYING IS NOT AUTHORIZED

Do not build a local shadow copy of the AMEC corpus.

Required:

```text
RAW_SOURCE_FULL_FILE_RETENTION_AUTHORIZED=false
```

For HASH_ONLY:

```text
retain source identity + digest + audit
```

For structure/bounded reads:

```text
retain only authorized structured evidence / bounded excerpt
```

according to the action contract.

---

# 17. RETENTION CONTRACT PER ACTION

Every action must include:

```text
retention_policy

allowed_retained_fields

max_retained_evidence_bytes or equivalent bounded output

minimal_excerpt_allowed
true/false

raw_source_retention
false
```

For `MINIMIZE_VALUES`:

```text
retain document structure/business semantics

do not retain unnecessary personal identifiers
```

Required:

```text
AUTHORIZED_ACTIONS_WITHOUT_RETENTION_CONTRACT=0

MINIMIZE_VALUES_ACTIONS_WITH_UNBOUNDED_RETENTION=0
```

---

# 18. HANDLING CLASSES

Preserve Stage0.3:

```text
NORMAL

MINIMIZE_VALUES
```

No `SECRET_EXCLUDE` action may be authorized.

Required:

```text
AUTHORIZED_SECRET_EXCLUDE_ACTIONS=0
```

---

# 19. PROVENANCE / AUTHORITY LIMITS SURVIVE AUTHORIZATION

If an action has:

```text
canonical_authority_allowed=false
```

authorization does not change it.

For unresolved:

```text
Art Mark

ART MEC

United Construction
```

generic product discovery may be authorized if already frozen as valid.

But evidence cannot be used to assert:

```text
AMEC current canonical source

AMEC authoritative legal identity

AMEC canonical template

AMEC canonical business rule
```

until separately resolved.

Required:

```text
AUTHORIZATION_PROMOTING_UNRESOLVED_PROVENANCE_TO_CANONICAL=0
```

---

# 20. AUTHORIZATION IS ACTION-SPECIFIC AND NON-FUNGIBLE

For every authorized action:

```text
action_id
```

is explicit.

No authorization by:

```text
share

directory

module

file type

budget only
```

Required:

```text
CLASS_WIDE_SOURCE_AUTHORIZATION=0
```

---

# 21. UNUSED BUDGET IS NOT FUNGIBLE

If authorized action A is not executed:

```text
its source bytes
its physical open
its parser allowance
```

do not become permission for another action D.

Required:

```text
BUDGET_REALLOCATION_TO_UNAUTHORIZED_ACTIONS_ALLOWED=false
```

---

# 22. LOGICAL ACTIONS VS UNIQUE PHYSICAL SOURCES

Preserve:

```text
logical actions
!=
unique source versions
```

One source may support multiple logical product decisions.

Authorization must allow evidence reuse where the frozen/certified plan permits it.

Do not:

```text
re-read same source separately
```

merely because two decision units reference it.

---

# 23. PHYSICAL I/O PLAN IS THE EXECUTION CEILING

Pin exact final values:

```text
AUTHORIZED_MAX_LOGICAL_ACTIONS

AUTHORIZED_MAX_UNIQUE_SOURCE_FILES

AUTHORIZED_MAX_PHYSICAL_FILE_OPENS

AUTHORIZED_MAX_PHYSICAL_SOURCE_BYTES
```

Expected historical upper bound:

```text
940,387,450 bytes
```

but derive from frozen artifacts.

Required:

```text
AUTHORIZED_MAX_PHYSICAL_SOURCE_BYTES
<=
FROZEN_STAGE1R_A_PHYSICAL_READ_BYTES_UPPER_BOUND
```

Never enlarge in 0.5.

---

# 24. FOUR BUDGET DIMENSIONS REMAIN DISTINCT

Pin separately:

```text
LOGICAL_ACTION_BYTES

UNIQUE_SOURCE_VERSION_BYTES

PLANNED_PHYSICAL_FILE_OPENS

PLANNED_PHYSICAL_READ_BYTES_UPPER_BOUND
```

Do not collapse them into one "budget."

---

# 25. BUDGET BY DIMENSION

Freeze authorization ceilings by:

```text
share

module/domain

action type

handling class

size band

priority

decision unit
```

If the frozen plan has no trustworthy per-dimension byte figure:

```text
do not invent one
```

Use exact action-level bounds and aggregate from them.

---

# 26. LARGE OBJECT POLICY

Verify:

```text
Stage1R-A >=100 MB actions

Stage1R-A >=1 GB actions
```

Expected:

```text
0
0
```

If any appear unexpectedly:

```text
RESULT=BLOCKED
BLOCKER=STAGE1R_A_LARGE_OBJECT_DRIFT
```

unless the frozen predecessor explicitly authorized the changed state.

No new large-object exception is invented in 0.5.

---

# 27. EXECUTION IS MAXIMUM-AUTHORIZED, NOT "MUST READ ALL"

The Stage1R-A set is:

```text
maximum authorized evidence work
```

not:

```text
mandatory source-read count
```

The future executor must stop when an already-frozen stop condition makes later
evidence unnecessary.

---

# 28. DECISION-UNIT EXECUTION SCHEDULE

Build:

```text
AMEC_Phase3B_0_5_Stage1R_A_Execution_Schedule_v1.json
AMEC_Phase3B_0_5_Stage1R_A_Execution_Schedule_v1.md
```

Group by:

```text
decision_unit_id
```

Within each unit preserve/freeze:

```text
priority

authority/source-role ordering

representative-first ordering

action dependencies

stop condition

fallback action IDs

module/product questions
```

Do not invent new product priority scores.

Use existing:

```text
P0
P1
P2
P3
```

and frozen evidence hierarchy.

---

# 29. DEFAULT EXECUTION ORDER PRINCIPLE

Prefer:

```text
P0 before P1 before P2 before P3

higher-authority representative before lower-authority copy

smaller sufficient evidence before larger redundant evidence

structure/bounded read before extra duplicate work when it can answer the
business question more cheaply

one source-version hash reused across dependent decisions
```

Only where consistent with the frozen plan.

---

# 30. STOP CONDITIONS MUST BE MACHINE-READABLE WHERE POSSIBLE

For each decision unit capture:

```text
stop_condition_id

condition_type

human_or_deterministic

condition_description

actions_cancelled_if_met[]
```

Examples:

```text
AUTHORITATIVE_REPRESENTATIVE_ANSWERS_STRUCTURE

FIRST_HASH_MISMATCH_BREAKS_ALL_IDENTICAL_HYPOTHESIS

CANONICAL_SOURCE_IDENTIFIED

DOCUMENT_CONFIRMED_NO_PRODUCT_VALUE

REQUIRED_FIELD_SCHEMA_CONFIRMED
```

Do not rewrite the underlying business condition.

---

# 31. HUMAN STOP CONDITIONS

Some sufficiency questions require judgment.

For those:

```text
stop_condition_mode=HUMAN_REVIEW
```

The executor pauses the decision unit after the triggering evidence.

It must not continue consuming all remaining actions automatically.

---

# 32. STOP-CONDITION OUTCOMES

Future allowed action outcomes:

```text
EXECUTED_SUCCESS

SKIPPED_STOP_CONDITION

SKIPPED_SOURCE_VERSION_DRIFT

BLOCKED_PRECONDITION

BLOCKED_TRANSPORT

BLOCKED_PARSER

BLOCKED_BUDGET

NEEDS_HUMAN_EVIDENCE_REVIEW

FAILED
```

Do not count skipped-by-stop-condition actions as failures.

---

# 33. SOURCE-VERSION DRIFT DOES NOT CONSUME BUDGET AS SUBSTITUTE AUTHORITY

If an action is blocked before source read because its source version changed:

```text
no replacement source may consume the unused action budget
```

The action becomes:

```text
SKIPPED_SOURCE_VERSION_DRIFT
```

or equivalent.

---

# 34. FUTURE EXECUTION CONCURRENCY

Use the Phase0.4-certified concurrency.

If Phase0.4 certified only sequential source reads:

```text
AUTHORIZED_MAX_CONCURRENT_SOURCE_READS=1
```

Do not increase it.

If Phase0.4 certified a higher value explicitly, pin it.

---

# 35. RETRY POLICY

Pin the certified Phase0.4 retry contract.

Every retry must:

```text
revalidate source-version precondition

revalidate remaining action authorization

respect max attempts

reuse idempotency/action identity
```

No retry may read a changed version silently.

---

# 36. CHECKPOINT / RESUME

Future Stage1R-A execution must checkpoint at:

```text
action
decision unit
physical source result
```

On restart:

```text
completed action
→ do not repeat unnecessarily

skipped by stop condition
→ remains skipped

interrupted action
→ fresh source-version precondition before retry
```

---

# 37. EVIDENCE RESULT CONTRACT

Freeze the Stage1R-A result envelope:

```text
SourceEvidenceResult

run_id

action_id

decision_unit_id

source identity

source-version precondition

pre-read source state

operation type

transport version

reader version

physical_file_opens

physical_source_bytes_read

hash_bytes

parser_input_bytes

extracted_output_bytes

retained_evidence_bytes

evidence payload

evidence payload hash

post-read source state

handling class

retention outcome

stop-condition evaluation

status

error/blocker

audit event id
```

---

# 38. EVIDENCE PAYLOAD IS NOT PRODUCT TRUTH

Stage1R-A produces:

```text
evidence
```

not:

```text
canonical app state
```

Allowed conclusions include:

```text
document appears to use fields X/Y/Z

form structure contains repeating grid

invoice evidence contains these labels

authority form identifies requirement pattern

two selected files are byte-identical
```

Not automatically:

```text
this is AMEC canonical forever

invoice is financially settled

permit is approved

Master Content is Current
```

Those require later canonical resolution.

---

# 39. STRUCTURED PRODUCT-FINDING CONTRACT

Alongside raw evidence, allow a restricted:

```text
ProductLearningObservation
```

linked to source evidence.

Fields may include:

```text
module implications

workflow implications

document family evidence

required fields

required statuses

roles

business identifiers

business-rule observations

Master Content implications

source-of-truth observations

duplicate/version observations

AI-assist opportunity

human authority boundary

unresolved questions
```

State:

```text
OBSERVATION_ONLY
```

not VerifiedAssertion.

---

# 40. MODULE EVIDENCE ACCUMULATION

Every future successful action must link its observation to one or more frozen
coverage targets:

```text
M1

M2

M3

M4

M5

M6

M7

FINANCE

MASTER_CONTENT_FORM

MASTER_CONTENT_REPORT

MASTER_CONTENT_ENGINEERING_WORK

MASTER_CONTENT_DEFINITION

REPORTING

CROSS_CUTTING
```

No untraceable generic summary.

---

# 41. FINANCE SAFEGUARDS

Stage1R-A may learn:

```text
invoice fields

invoice references

payment terms

project/contract links

payment-receipt document structure

financial-account reference structure
```

It may not conclude from document text alone:

```text
Paid = Financially Settled

unverified PaymentReceipt reduces receivable

follow-up note = payment

regulatory fee = AMEC receivable
```

Preserve those as later truth-resolution rules.

---

# 42. MASTER CONTENT SAFEGUARDS

Stage1R-A may learn evidence for:

```text
FORM

REPORT

ENGINEERING_WORK

DEFINITION
```

Checklist remains FORM.

An executed project record may not become reusable Master Content automatically.

---

# 43. REGULATORY SAFEGUARDS

Preserve distinction:

```text
PROJECT_APPROVAL

PROFESSIONAL_REGISTRATION

CONSULTANT_OFFICE_REGISTRATION

CORPORATE_CLASSIFICATION

CORPORATE_LICENSE_COMPLIANCE
```

Evidence may inform classification.

It does not expand AI/human submission authority.

---

# 44. ENGINEERING / CONSTRUCTION SAFEGUARDS

Preserve:

```text
Shop Drawing
→ M3

Shop Drawing Submittal
→ M5

Authority submission of drawing
→ M4
```

and:

```text
material technical data
→ M3

material submittal
→ M5

authority-facing material approval
→ M4 where applicable
```

---

# 45. HANDOVER SAFEGUARDS

Preserve:

```text
PROJECT_TO_CLIENT

PROJECT_TO_OTHER_CONSULTANT

INTERNAL_EMPLOYEE_HANDOVER

DEPARTMENTAL_HANDOVER

DOCUMENT_CONTROL_HANDOVER

FINANCE_HANDOVER
```

Employee/depart­ment handover is not silently M7 project closeout.

---

# 46. OWNER AUTHORIZATION IS A DISTINCT BUSINESS DECISION

Technical certification does not authorize business-source reading.

Phase0.5 must create an explicit Owner authorization request referencing the
exact immutable authorization manifest.

Required:

```text
AMEC_Phase3B_0_5_Exact_Stage1R_A_Owner_Authorization_Request_v1.md
```

---

# 47. OWNER AUTHORIZATION REQUEST — REQUIRED CONTENT

Keep concise and decision-oriented.

Show:

```text
purpose:
ProposalOps product discovery / corpus intelligence

exact logical actions

exact unique source files

maximum physical source bytes

maximum physical opens

operation counts:
HASH_ONLY
STRUCTURE_READ
BOUNDED_CONTENT_READ

handling:
NORMAL
MINIMIZE_VALUES

module coverage:
M1-M7
Finance
Master Content
Reporting
Cross-cutting

large objects:
>=100MB
>=1GB

transport:
certified

network:
certified production-equivalent path

source mutation:
0

raw source retention:
not authorized

cloud LLM upload:
not authorized

vector indexing:
not authorized

product ingestion:
not authorized

Stage1R-B / Stage2 / Stage3:
not authorized
```

No unnecessary personal filenames/values.

---

# 48. OWNER AUTHORIZATION ATTESTATION

Create:

```text
AMEC_Phase3B_0_5_Exact_Stage1R_A_Owner_Authorization_Attestation_TEMPLATE_v1.md
AMEC_Phase3B_0_5_Exact_Stage1R_A_Owner_Authorization_Attestation_TEMPLATE_v1.json
```

The authorization is valid only when an actual Owner statement is present.

Do not invent:

```text
Owner approved
```

from:

```text
access credentials

prior general Synology access

technical feasibility

this Codex run
```

---

# 49. OWNER AUTHORIZATION MUST PIN THE MANIFEST HASH

Required authorization language must reference:

```text
authorization_manifest_sha256
```

and state whether approval is:

```text
FULL_EXACT_STAGE1R_A

or

PARTIAL_EXACT_ACTION_SUBSET
```

No vague class-wide approval.

---

# 50. FULL AUTHORIZATION

For:

```text
FULL_EXACT_STAGE1R_A
```

the Owner attestation approves:

```text
every exact action_id in the frozen manifest

subject to:
source-version preconditions
certified transport/readers
physical budget
retention rules
stop conditions
```

It does not require every action to execute.

---

# 51. PARTIAL AUTHORIZATION

If the Owner approves only a subset:

```text
list exact action IDs
```

or provide a canonical subset manifest SHA.

Do not let Codex choose a partial subset on the Owner's behalf unless an
explicit Owner instruction defines that subset.

---

# 52. AUTHORIZATION MANIFEST

Create:

```text
AMEC_Phase3B_0_5_Stage1R_A_Exact_Execution_Authorization_Manifest_v1.json
AMEC_Phase3B_0_5_Stage1R_A_Exact_Execution_Authorization_Manifest_v1.md
```

This is the central artifact.

Every action entry must include at minimum:

```text
action_id

action_group_id

decision_unit_id

authorization_state

phase2_corpus_record_id

registry_record_id if applicable

record_type=FILE

share

relative_path

expected_size

expected_mtime / source observation

source_version_precondition

operation_type

format

certified_transport_id

certified_transport_sha256

certified_reader_id

certified_reader_version

certified_reader_sha256

certified_capability_id

proposalops_modules[]

relevance_categories[]

product_questions[]

priority

handling_class

retention_policy

allowed_retained_fields

max_retained_evidence_bytes / bounded output

minimum_required_access

max_physical_source_bytes_for_action

max_physical_file_opens_for_action

physical_read_plan_id

canonical_authority_allowed

provenance_status

duplicate_group_id if applicable

proof_scope if applicable

stop_condition_id

idempotency_identity

authorization_manifest_version
```

Missing required field:

```text
action cannot be authorized
```

---

# 53. AUTHORIZATION STATE

Before actual Owner approval:

```text
CANDIDATE_AWAITING_OWNER_AUTHORIZATION
```

After a valid attestation matching the exact manifest SHA:

```text
AUTHORIZED
```

Never infer state from file presence alone.

---

# 54. AUTHORIZATION IDENTITY

Canonicalize the final authorization manifest.

Create:

```text
AUTHORIZATION_MANIFEST_SHA256
```

Also create:

```text
AUTHORIZED_ACTION_IDS_SHA256

AUTHORIZED_SOURCE_SELECTORS_SHA256

AUTHORIZED_READER_BINDINGS_SHA256

AUTHORIZED_PHYSICAL_IO_BUDGET_SHA256

AUTHORIZED_RETENTION_CONTRACT_SHA256

AUTHORIZED_EXECUTION_SCHEDULE_SHA256
```

These are pinned into the Stage1R-A execution handoff.

---

# 55. DO NOT CALL A HASH A DIGITAL SIGNATURE

Unless an actual cryptographic signing mechanism is used:

```text
SHA-256 = identity/integrity hash
```

not:

```text
digital signature
```

The Owner attestation is the authorization evidence.

---

# 56. AUTHORIZATION REVOCATION / EXPIRY

Create fields:

```text
authorization_effective_at

authorization_valid_until
optional

authorization_revoked
false

revocation_reference
null
```

Do not invent an expiry date.

If none is explicitly set:

```text
authorization_valid_until=null
```

Source-version preconditions still protect against stale execution.

---

# 57. OWNER AUTHORIZATION EVIDENCE

Record:

```text
owner_authorization_evidence_reference

owner_authorization_date

owner_identity / role as available

authorized_scope

authorization_manifest_sha256
```

Do not store unnecessary personal details.

---

# 58. TRUE OWNER BUSINESS DECISIONS REMAIN SEPARATE

Art Mark / ART MEC / United Construction relationship questions remain:

```text
PENDING
```

unless separately resolved.

Authorizing a generic discovery read does not resolve provenance.

---

# 59. AUTHORIZATION PACK MUST SURFACE UNRESOLVED PROVENANCE COUNTS

Report:

```text
authorized actions with canonical_authority_allowed=false

authorized actions dependent on Art Mark context

authorized actions dependent on ART MEC context

authorized actions dependent on United Construction context
```

Do not expose unnecessary sensitive names/values.

---

# 60. EXECUTION HANDOFF

Create:

```text
AMEC_Phase3B_0_5_to_Stage1R_A_Execution_Handoff_v1.json
AMEC_Phase3B_0_5_to_Stage1R_A_Execution_Handoff_v1.md
```

It must pin:

```text
Stage0.3 Freeze Manifest SHA

Phase0.4 Certification Freeze SHA

Authorization Manifest SHA

Owner Attestation SHA / evidence reference

Authorized Action-ID SHA

Authorized Source Selector SHA

Authorized Reader Binding SHA

Authorized I/O Budget SHA

Authorized Retention Contract SHA

Execution Schedule SHA

production network-path proof SHA

module coverage SHA
```

---

# 61. STAGE1R-A EXECUTION MAY START ONLY IF AUTHORIZED

Handoff:

```text
READY_FOR_STAGE1R_A_REAL_EVIDENCE_EXECUTION=true
```

only when:

```text
technical predecessor identity pass

Phase0.4 certification pass

exact authorization manifest complete

explicit Owner authorization present

Owner approval references exact manifest SHA

all authorized actions map to certified capabilities

physical budget <= frozen budget

zero prohibited capabilities authorized
```

---

# 62. IF OWNER AUTHORIZATION IS NOT PRESENT

Do not return `AUTHORIZED`.

Return:

```text
RESULT=READY_FOR_OWNER_AUTHORIZATION

STAGE1R_A_EXECUTION_AUTHORIZED=false

READY_FOR_STAGE1R_A_REAL_EVIDENCE_EXECUTION=false
```

with:

```text
NEXT=Owner reviews and explicitly approves the exact authorization manifest
SHA (full Stage1R-A or exact subset); then rerun only the attestation/finalization
step. No new analysis is required.
```

This is not another planning loop.

---

# 63. IF OWNER AUTHORIZATION IS PRESENT AND VALID

Return:

```text
RESULT=AUTHORIZED

STAGE1R_A_EXECUTION_AUTHORIZED=true

READY_FOR_STAGE1R_A_REAL_EVIDENCE_EXECUTION=true
```

No source read occurs inside 0.5.

---

# 64. AUTHORIZATION CANNOT BE SELF-EXPANDING

After authorization:

```text
new action IDs
new source paths
new source versions
new readers
new formats
new modules
```

are NOT automatically authorized.

Required:

```text
AUTHORIZATION_AUTO_EXPANSION_ALLOWED=false
```

---

# 65. EXECUTION-TIME HARD PRECONDITIONS

The Stage1R-A executor must check before every action:

```text
action ID authorized

authorization not revoked

source selector exact match

source-version precondition match

transport version authorized

reader version authorized

capability certified

remaining non-fungible action budget

production network path valid

no stop condition has already cancelled action
```

If any fail:

```text
do not read
```

---

# 66. EXECUTION-TIME PHYSICAL BUDGET PRECHECK

Before source open:

```text
planned action physical bytes
+
already consumed authorized physical bytes
<=
authorized ceiling
```

But because budget is non-fungible:

```text
global spare bytes
```

do not authorize an otherwise unauthorized action.

---

# 67. EXECUTION-TIME SOURCE VERSION PRECHECK

Fresh stat immediately before read.

If mismatch:

```text
NOT_EXECUTED_SOURCE_VERSION_DRIFT
```

No fuzzy or latest substitution.

---

# 68. EXECUTION-TIME POST-READ CHECK

Fresh source state after read.

If changed during read:

```text
reject evidence

do not count as successful
```

Follow Phase0.4 certified behavior.

---

# 69. EXECUTION-TIME EVIDENCE MINIMIZATION

For `MINIMIZE_VALUES`:

```text
retained sensitive values
expected 0
```

unless the action contract explicitly states a business-semantic value is
required.

Every exception must be action-specific.

---

# 70. NO CLOUD / VECTOR SIDE EFFECT AT EXECUTION

The Stage1R-A executor must not:

```text
send real source content to cloud LLM

create embeddings

write vectors

index into search

upload raw files into product storage
```

Required future counters:

```text
CLOUD_LLM_SOURCE_UPLOADS=0

VECTOR_EMBEDDINGS_CREATED=0

PRODUCTION_SEARCH_INDEX_WRITES=0

PRODUCT_DOCUMENT_UPLOADS=0
```

---

# 71. STAGE1R-A RUN SHOULD BE PAUSABLE

The future executor must support:

```text
pause

resume

stop
```

without losing completed evidence.

Do not require the whole authorized tranche to run in one session.

---

# 72. STAGE1R-A SHOULD EXECUTE REPRESENTATIVE-FIRST

The schedule should maximize:

```text
product questions resolved
per
physical source I/O
```

without inventing fake numeric value scores.

---

# 73. EVIDENCE SUFFICIENCY STOP IS MANDATORY AFTER STAGE1R-A

The authorization handoff must state:

```text
AFTER_STAGE1R_A
STOP
```

Then perform:

```text
Evidence Sufficiency Review
```

Do not automatically authorize:

```text
Stage1R-B
```

after A completes.

---

# 74. STAGE1R-B REMAINS COMPLETELY UNAUTHORIZED

Required:

```text
STAGE1R_B_EXECUTION_AUTHORIZED=false

STAGE2_EXECUTION_AUTHORIZED=false

STAGE3_EXECUTION_AUTHORIZED=false
```

Unused A budget cannot flow into B.

---

# 75. OCR / ARCHIVES / SPECIAL PARSERS REMAIN UNAUTHORIZED

Required:

```text
OCR_AUTHORIZED=false

GENERAL_ARCHIVE_EXTRACTION_AUTHORIZED=false

UNSUPPORTED_CAD_CONTENT_PARSING_AUTHORIZED=false
```

HASH_ONLY on supported binary formats remains allowed only where the exact
frozen action says so.

---

# 76. REQUIRED EVIDENCE DIRECTORY

Create outside Git:

```text
<local ProposalOps-Control>/
proposalops-amec-phase3b-0-5-exact-stage1r-a-authorization-<run-id>/
```

---

# 77. REQUIRED ARTIFACTS

At minimum:

```text
01_PHASE3B_0_5_PROVENANCE.md

02_AMEC_Phase3B_0_5_Frozen_Input_Identity_Manifest_v1.json
03_AMEC_Phase3B_0_5_Frozen_Input_Identity_Manifest_v1.md

04_AMEC_Phase3B_0_5_Stage1R_A_Action_Set_Reconciliation_v1.json
05_AMEC_Phase3B_0_5_Stage1R_A_Action_Set_Reconciliation_v1.md

06_AMEC_Phase3B_0_5_Unique_Source_Set_Reconciliation_v1.json
07_AMEC_Phase3B_0_5_Unique_Source_Set_Reconciliation_v1.md

08_AMEC_Phase3B_0_5_Certified_Capability_Binding_v1.csv
09_AMEC_Phase3B_0_5_Certified_Capability_Binding_v1.json
10_AMEC_Phase3B_0_5_Certified_Capability_Binding_v1.md

11_AMEC_Phase3B_0_5_Stage1R_A_Authorization_Budget_v1.json
12_AMEC_Phase3B_0_5_Stage1R_A_Authorization_Budget_v1.md

13_AMEC_Phase3B_0_5_Stage1R_A_Retention_and_Minimization_Contract_v1.json
14_AMEC_Phase3B_0_5_Stage1R_A_Retention_and_Minimization_Contract_v1.md

15_AMEC_Phase3B_0_5_Stage1R_A_Execution_Schedule_v1.json
16_AMEC_Phase3B_0_5_Stage1R_A_Execution_Schedule_v1.md

17_AMEC_Phase3B_0_5_Stage1R_A_Exact_Execution_Authorization_Manifest_v1.json
18_AMEC_Phase3B_0_5_Stage1R_A_Exact_Execution_Authorization_Manifest_v1.md

19_AMEC_Phase3B_0_5_Exact_Stage1R_A_Owner_Authorization_Request_v1.md

20_AMEC_Phase3B_0_5_Exact_Stage1R_A_Owner_Authorization_Attestation_TEMPLATE_v1.json
21_AMEC_Phase3B_0_5_Exact_Stage1R_A_Owner_Authorization_Attestation_TEMPLATE_v1.md

22_AMEC_Phase3B_0_5_Provenance_Authority_Limits_v1.json
23_AMEC_Phase3B_0_5_Provenance_Authority_Limits_v1.md

24_AMEC_Phase3B_0_5_Module_Evidence_Targets_v1.json
25_AMEC_Phase3B_0_5_Module_Evidence_Targets_v1.md

26_AMEC_Phase3B_0_5_Stage1R_A_Execution_Result_Contract_v1.json
27_AMEC_Phase3B_0_5_Stage1R_A_Execution_Result_Contract_v1.md

28_AMEC_Phase3B_0_5_to_Stage1R_A_Execution_Handoff_v1.json
29_AMEC_Phase3B_0_5_to_Stage1R_A_Execution_Handoff_v1.md

30_AMEC_Phase3B_0_5_Authorization_Freeze_Manifest_v1.json
31_AMEC_Phase3B_0_5_Authorization_Freeze_Manifest_v1.md

32_PHASE3B_0_5_INVARIANT_AUDIT.json
33_PHASE3B_0_5_INVARIANT_AUDIT.md

summary.json
```

If actual Owner authorization evidence already exists, also create:

```text
34_AMEC_Phase3B_0_5_Exact_Stage1R_A_Owner_Authorization_Attestation_FINAL_v1.json
35_AMEC_Phase3B_0_5_Exact_Stage1R_A_Owner_Authorization_Attestation_FINAL_v1.md
```

and pin their hashes.

---

# 78. AUTHORIZATION FREEZE MANIFEST

Create:

```text
AMEC_Phase3B_0_5_Authorization_Freeze_Manifest_v1.json
```

Pin:

```text
Stage0.3 Freeze Manifest SHA

Phase0.4 Certification Freeze SHA

Stage1R-A Plan SHA

Stage1R-A Allowlist SHA

Stage1R-A Action-ID SHA

Stage1R-A Source-Selector SHA

Stage1R-A Reader-Binding SHA

Stage1R-A Budget SHA

Retention Contract SHA

Execution Schedule SHA

Authorization Manifest SHA

Owner Authorization Attestation SHA if present

Production Network Path Proof SHA

Module Evidence Targets SHA

Invariant Audit SHA
```

---

# 79. REQUIRED HARD INVARIANTS

All zero:

```text
STAGE0_3_FROZEN_SHA_MISMATCHES

PHASE0_4_CERTIFICATION_SHA_MISMATCHES

REAL_AMEC_BUSINESS_SOURCE_FILES_OPENED

REAL_AMEC_BUSINESS_SOURCE_BYTES_READ

REAL_AMEC_BUSINESS_SOURCE_HASHES

REAL_AMEC_BUSINESS_CONTENT_PARSED

SYNOLOGY_BUSINESS_SOURCE_CONNECTIONS

SOURCE_MUTATIONS

NEW_RELEVANCE_CLASSIFICATIONS

TAXONOMY_CHANGES

STAGE1R_A_ACTION_TYPE_CHANGES

STAGE1R_A_PRODUCT_QUESTION_CHANGES

STAGE1R_A_DUPLICATE_ACTION_IDS

STAGE1R_A_ACTION_ID_SET_DRIFT

SOURCE_SELECTORS_WITH_MISSING_IDENTITY

SOURCE_SELECTORS_WITH_AMBIGUOUS_IDENTITY

SOURCE_SELECTORS_WITH_NON_FILE_OBJECT

AUTHORIZED_ACTIONS_ALLOWING_LATEST_SUBSTITUTION

AUTHORIZED_ACTIONS_WITH_UNCERTIFIED_CAPABILITY

AUTHORIZED_OCR_ACTIONS

AUTHORIZED_GENERAL_ARCHIVE_EXTRACTION_ACTIONS

AUTHORIZED_UNBOUNDED_CONTENT_READ_ACTIONS

AUTHORIZED_ACTIONS_WITHOUT_RETENTION_CONTRACT

MINIMIZE_VALUES_ACTIONS_WITH_UNBOUNDED_RETENTION

AUTHORIZED_SECRET_EXCLUDE_ACTIONS

AUTHORIZATION_PROMOTING_UNRESOLVED_PROVENANCE_TO_CANONICAL

CLASS_WIDE_SOURCE_AUTHORIZATION

CLOUD_LLM_SOURCE_UPLOADS

VECTOR_EMBEDDINGS_CREATED

PRODUCTION_SEARCH_INDEX_WRITES

PRODUCT_DOCUMENT_UPLOADS
```

---

# 80. REQUIRED BOOLEAN INVARIANTS

Required:

```text
BUDGET_REALLOCATION_TO_UNAUTHORIZED_ACTIONS_ALLOWED=false

EXTERNAL_CLOUD_LLM_SOURCE_CONTENT_UPLOAD_AUTHORIZED=false

VECTOR_DB_INDEXING_AUTHORIZED=false

PRODUCTION_SEARCH_INDEXING_AUTHORIZED=false

PRODUCTION_RAG_INDEXING_AUTHORIZED=false

PRODUCTION_AI_RETRIEVAL_AUTHORIZED=false

DOCUMENTVERSION_CREATION_AUTHORIZED=false

MASTERCONTENT_CREATION_AUTHORIZED=false

BUSINESS_DB_PROJECTION_AUTHORIZED=false

VERIFIEDASSERTION_PRODUCT_WRITE_AUTHORIZED=false

PRODUCTION_STORAGE_PROMOTION_AUTHORIZED=false

RAW_SOURCE_FULL_FILE_RETENTION_AUTHORIZED=false

AUTHORIZATION_AUTO_EXPANSION_ALLOWED=false

STAGE1R_B_EXECUTION_AUTHORIZED=false

STAGE2_EXECUTION_AUTHORIZED=false

STAGE3_EXECUTION_AUTHORIZED=false

OCR_AUTHORIZED=false

GENERAL_ARCHIVE_EXTRACTION_AUTHORIZED=false
```

---

# 81. POSITIVE TECHNICAL GATES

Required true before an Owner authorization may be finalized:

```text
FROZEN_INPUT_IDENTITY_PASS

STAGE1R_A_ACTION_SET_PASS

UNIQUE_SOURCE_SET_PASS

PHASE0_4_CERTIFICATION_IDENTITY_PASS

ALL_STAGE1R_A_ACTIONS_BOUND_TO_CERTIFIED_CAPABILITIES

PRODUCTION_NETWORK_PATH_BINDING_PASS

AUTHORIZATION_BUDGET_WITHIN_FROZEN_CEILING

RETENTION_CONTRACT_COMPLETE

EXECUTION_SCHEDULE_COMPLETE

STOP_CONDITION_COVERAGE_COMPLETE

AUTHORIZATION_MANIFEST_COMPLETE

OWNER_AUTHORIZATION_REQUEST_COMPLETE

EXECUTION_RESULT_CONTRACT_COMPLETE
```

---

# 82. REQUIRED SUMMARY CONTRACT

Create:

```json
{
  "phase": "AMEC_PHASE3B_0_5_EXACT_STAGE1R_A_EXECUTION_AUTHORIZATION",
  "revision": "v1.0",

  "result": "AUTHORIZED|READY_FOR_OWNER_AUTHORIZATION|BLOCKED",

  "predecessor_identity": {
    "stage0_3_frozen_identity_pass": false,
    "phase0_4_certification_identity_pass": false,
    "stage0_3_freeze_manifest_sha256": "",
    "phase0_4_certification_freeze_sha256": ""
  },

  "stage1r_a": {
    "logical_actions": 0,
    "unique_source_files": 0,

    "hash_only_actions": 0,
    "structure_read_actions": 0,
    "bounded_content_read_actions": 0,

    "normal_handling_actions": 0,
    "minimize_values_actions": 0,

    "ge_100mb_actions": 0,
    "ge_1gb_actions": 0
  },

  "budget": {
    "logical_action_bytes": 0,
    "unique_source_version_bytes": 0,
    "authorized_max_physical_file_opens": 0,
    "authorized_max_physical_source_bytes": 0,
    "frozen_stage1r_a_physical_read_upper_bound": 0,
    "within_frozen_ceiling": false,
    "budget_non_fungible": true
  },

  "bindings": {
    "actions_bound_to_certified_transport": 0,
    "actions_bound_to_certified_reader": 0,
    "actions_with_uncertified_capability": 0,
    "production_network_path_bound": false
  },

  "authorization_identity": {
    "stage1r_a_action_ids_sha256": "",
    "authorized_source_selectors_sha256": "",
    "authorized_reader_bindings_sha256": "",
    "authorized_physical_io_budget_sha256": "",
    "authorized_retention_contract_sha256": "",
    "authorized_execution_schedule_sha256": "",
    "authorization_manifest_sha256": ""
  },

  "owner_authorization": {
    "request_created": false,
    "explicit_owner_authorization_present": false,
    "authorization_mode": "NONE|FULL_EXACT_STAGE1R_A|PARTIAL_EXACT_ACTION_SUBSET",
    "owner_authorization_evidence_reference": "",
    "owner_authorization_manifest_sha_matches": false
  },

  "prohibited": {
    "external_cloud_llm_source_upload_authorized": false,
    "vector_db_indexing_authorized": false,
    "product_ingestion_authorized": false,
    "source_mutation_authorized": false,
    "ocr_authorized": false,
    "general_archive_extraction_authorized": false,
    "stage1r_b_authorized": false,
    "stage2_authorized": false,
    "stage3_authorized": false
  },

  "safety": {
    "real_amec_business_source_files_opened": 0,
    "real_amec_business_source_bytes_read": 0,
    "real_amec_business_source_hashes": 0,
    "real_amec_business_content_parsed": 0,
    "synology_business_source_connections": 0,
    "source_mutations": 0
  },

  "stage1r_a_execution_authorized": false,
  "ready_for_stage1r_a_real_evidence_execution": false,

  "authorization_freeze_manifest_sha256": "",

  "next": ""
}
```

---

# 83. RESULT = READY_FOR_OWNER_AUTHORIZATION

Use when:

```text
all technical authorization artifacts are complete
```

but explicit Owner approval referencing the exact final:

```text
AUTHORIZATION_MANIFEST_SHA256
```

is absent.

Required:

```text
STAGE1R_A_EXECUTION_AUTHORIZED=false

READY_FOR_STAGE1R_A_REAL_EVIDENCE_EXECUTION=false
```

The next action is one human decision.

No more analysis.

---

# 84. RESULT = AUTHORIZED

Use only when:

```text
Owner authorization evidence is explicit

approval scope is exact

approval references the exact final authorization manifest SHA

all technical positive gates pass
```

Then:

```text
STAGE1R_A_EXECUTION_AUTHORIZED=true

READY_FOR_STAGE1R_A_REAL_EVIDENCE_EXECUTION=true
```

Still:

```text
REAL_AMEC_BUSINESS_SOURCE_BYTES_READ=0
```

inside Phase0.5.

---

# 85. RESULT = BLOCKED

Only for an actual authorization-integrity defect such as:

```text
predecessor SHA drift

Phase0.4 not PASS

Stage1R-A action set drift

source-selector ambiguity

uncertified action capability

budget exceeds frozen ceiling

required retention contract missing

authorization manifest incomplete

Owner attestation references wrong manifest SHA
```

Do not block merely because:

```text
Art Mark relationship remains unresolved

Stage1R-B exists

Stage2/Stage3 remain deferred

Owner authorization has not yet been given
```

The latter is:

```text
READY_FOR_OWNER_AUTHORIZATION
```

not `BLOCKED`.

---

# 86. AUTHORIZED HANDOFF FORMAT

On valid authorization:

```text
PROPOSALOPS_AMEC_PHASE3B_0_5_COMPLETE

RESULT=AUTHORIZED

STAGE0_3_FROZEN_IDENTITY_PASS=true
PHASE0_4_CERTIFICATION_IDENTITY_PASS=true

STAGE1R_A_LOGICAL_ACTIONS=<n>
STAGE1R_A_UNIQUE_SOURCE_FILES=<n>

STAGE1R_A_HASH_ONLY=<n>
STAGE1R_A_STRUCTURE_READ=<n>
STAGE1R_A_BOUNDED_CONTENT_READ=<n>

STAGE1R_A_NORMAL=<n>
STAGE1R_A_MINIMIZE_VALUES=<n>

STAGE1R_A_GE_100MB=<n>
STAGE1R_A_GE_1GB=<n>

AUTHORIZED_MAX_PHYSICAL_FILE_OPENS=<n>
AUTHORIZED_MAX_PHYSICAL_SOURCE_BYTES=<bytes>

FROZEN_PHYSICAL_READ_UPPER_BOUND=<bytes>
AUTHORIZATION_WITHIN_FROZEN_BUDGET=true

ALL_ACTIONS_BOUND_TO_CERTIFIED_CAPABILITIES=true
PRODUCTION_NETWORK_PATH_BOUND=true

STAGE1R_A_ACTION_IDS_SHA256=<sha>
AUTHORIZED_SOURCE_SELECTORS_SHA256=<sha>
AUTHORIZED_READER_BINDINGS_SHA256=<sha>
AUTHORIZED_PHYSICAL_IO_BUDGET_SHA256=<sha>
AUTHORIZED_RETENTION_CONTRACT_SHA256=<sha>
AUTHORIZED_EXECUTION_SCHEDULE_SHA256=<sha>

AUTHORIZATION_MANIFEST_SHA256=<sha>

OWNER_AUTHORIZATION_PRESENT=true
OWNER_AUTHORIZATION_MODE=<FULL_EXACT_STAGE1R_A|PARTIAL_EXACT_ACTION_SUBSET>
OWNER_AUTHORIZATION_MANIFEST_SHA_MATCH=true

EXTERNAL_CLOUD_LLM_SOURCE_CONTENT_UPLOAD_AUTHORIZED=false
VECTOR_DB_INDEXING_AUTHORIZED=false
PRODUCT_INGESTION_AUTHORIZED=false

OCR_AUTHORIZED=false
GENERAL_ARCHIVE_EXTRACTION_AUTHORIZED=false

STAGE1R_B_EXECUTION_AUTHORIZED=false
STAGE2_EXECUTION_AUTHORIZED=false
STAGE3_EXECUTION_AUTHORIZED=false

REAL_AMEC_BUSINESS_SOURCE_FILES_OPENED=0
REAL_AMEC_BUSINESS_SOURCE_BYTES_READ=0
REAL_AMEC_BUSINESS_SOURCE_HASHES=0
REAL_AMEC_BUSINESS_CONTENT_PARSED=0
SYNOLOGY_BUSINESS_SOURCE_CONNECTIONS=0
SOURCE_MUTATIONS=0

STAGE1R_A_EXECUTION_AUTHORIZED=true
READY_FOR_STAGE1R_A_REAL_EVIDENCE_EXECUTION=true

AUTHORIZATION_FREEZE_MANIFEST_SHA256=<sha>

EVIDENCE_DIR=<path>

NEXT=Phase 3B Stage1R-A real AMEC evidence execution using ONLY this exact authorization envelope. Stop after Stage1R-A for evidence sufficiency review; do not automatically run Stage1R-B.
```

---

# 87. READY-FOR-OWNER HANDOFF FORMAT

If technical preparation passes but Owner approval is absent:

```text
PROPOSALOPS_AMEC_PHASE3B_0_5_COMPLETE

RESULT=READY_FOR_OWNER_AUTHORIZATION

AUTHORIZATION_MANIFEST_SHA256=<sha>

STAGE1R_A_LOGICAL_ACTIONS=<n>
STAGE1R_A_UNIQUE_SOURCE_FILES=<n>

AUTHORIZED_MAX_PHYSICAL_FILE_OPENS=<n>
AUTHORIZED_MAX_PHYSICAL_SOURCE_BYTES=<bytes>

STAGE1R_A_GE_100MB=<n>
STAGE1R_A_GE_1GB=<n>

ALL_ACTIONS_BOUND_TO_CERTIFIED_CAPABILITIES=true

SOURCE_MUTATIONS_AUTHORIZED=false
CLOUD_LLM_SOURCE_UPLOAD_AUTHORIZED=false
VECTOR_DB_INDEXING_AUTHORIZED=false
PRODUCT_INGESTION_AUTHORIZED=false

STAGE1R_A_EXECUTION_AUTHORIZED=false
READY_FOR_STAGE1R_A_REAL_EVIDENCE_EXECUTION=false

OWNER_AUTHORIZATION_REQUEST=<path>
OWNER_AUTHORIZATION_ATTESTATION_TEMPLATE=<path>

NEXT=Owner explicitly approves the exact Authorization Manifest SHA, either FULL_EXACT_STAGE1R_A or an exact action subset. Then finalize attestation only; do not rerun relevance, transport certification, or planning.
```

---

# 88. FUTURE STAGE1R-A EXECUTION PHASE — DO NOT IMPLEMENT HERE

The next execution phase should:

```text
consume authorization freeze

validate authorization identity

connect through certified production network path

process authorized decision units representative-first

fresh source-version precondition per action

perform minimum certified source operation

meter physical I/O

retain bounded evidence

apply stop conditions

checkpoint

produce module-organized evidence findings
```

That is the FIRST real AMEC content-reading phase.

---

# 89. AFTER STAGE1R-A — MANDATORY STOP

After the real A run:

```text
STOP
```

Perform:

```text
Evidence Sufficiency Review
```

Question:

```text
Which material ProposalOps module/product questions remain unresolved?
```

Only then may an exact subset of Stage1R-B be considered.

Do not mechanically proceed from:

```text
A
→ all B
```

---

# 90. COMPLETE REMAINING HISTORICAL-CORPUS PATH

The intended chain remains:

```text
Stage0.3 FINAL / FROZEN
        ↓
Phase0.4 transport/reader certification
        ↓
Phase0.5 exact execution authorization
        ↓
Stage1R-A real evidence execution
        ↓
STOP
        ↓
Evidence Sufficiency Review
        ↓
only necessary Stage1R-B subset if any
        ↓
Phase3C canonical AMEC Module Truth
        ↓
Phase4 Corpus → ProposalOps Integration Contract
        ↓
historical corpus discovery CLOSED
```

Do not start the continuous Synology trigger/write-back architecture before
this truth chain is complete.

# END
