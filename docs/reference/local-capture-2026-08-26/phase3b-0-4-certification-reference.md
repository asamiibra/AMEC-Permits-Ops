# CODEX MASTER EXECUTION PROMPT
# ProposalOps / AMEC — Phase 3B.0.4 v1.0
# Synthetic / Non-Business Exact-Source Read Transport
# + Evidence Reader Certification
# + Source-Version Integrity
# + Runtime I/O Budget Enforcement
# + Failure Injection
# + Immutable Stage1R-A Compatibility Handoff
#
# THIS PHASE MAY RUN ONLY AFTER:
#
#   Phase 3B Stage 0.3 FINAL Acceptance / v1.8 Conformance / Freeze
#   RESULT = PASS or PASS_WITH_DERIVED_REPAIR
#   STAGE0_3_FINAL_STATE = FROZEN
#   READY_FOR_PHASE3B_0_4_TRANSPORT_CERTIFICATION = true
#
# THIS PHASE DOES NOT AUTHORIZE ANY REAL AMEC BUSINESS-SOURCE CONTENT READ.
#
# ALLOWED SOURCE CONTENT:
#   SYNTHETIC
#   or
#   EXPLICITLY NON-BUSINESS CERTIFICATION FIXTURES
#
# PROHIBITED:
#   REAL AMEC BUSINESS FILE CONTENT
#   REAL AMEC SOURCE HASHING
#   STAGE1R-A EXECUTION
#   STAGE1R-B EXECUTION
#   OCR
#   GENERAL ARCHIVE EXTRACTION
#   SOURCE MUTATION OF BUSINESS SHARES
#   PRODUCT / DB / DEPLOYMENT CHANGES
#
# PURPOSE:
# Prove that the exact frozen Stage1R-A execution contract can later be run
# safely, deterministically, read-only, with correct source-version semantics,
# bounded evidence extraction, physical-I/O metering, failure behavior,
# checkpoint/restart behavior, and zero silent fallback.
#
# A successful 0.4 result does NOT authorize Stage1R-A.
# It creates the evidence required for Phase 3B.0.5 exact execution
# authorization.

---

# 0. EXECUTIVE OBJECTIVE

Certify the real execution substrate for the frozen Stage1R-A candidate:

```text
Frozen Stage1R-A Action
        ↓
Exact Source Selector
        ↓
Read-Only Transport
        ↓
Source-Version Precondition
        ↓
Physical Source Read
        ↓
one exact operation:

HASH_ONLY
STRUCTURE_READ
BOUNDED_CONTENT_READ

        ↓
Bounded / Typed Evidence Result
        ↓
Post-Read Source-Version Check
        ↓
Audit + Budget Metering
        ↓
Checkpoint / Restart
```

The certification must be representative of the actual Stage1R-A:

```text
operation types
file formats/extensions
source-size bands
parser requirements
transport semantics
```

Do not certify only a `.txt` happy path and call the system ready.

---

# 1. GOVERNING INPUT — STAGE 0.3 IS FROZEN

Locate the Stage 0.3 FINAL evidence directory produced by Phase 3B v1.9.

Consume the exact:

```text
Stage0.3 FINAL Freeze Manifest

Stage1R-A Final Plan

Stage1R-A Final Allowlist

Stage1R-A Action-ID set

Stage1R-A Final Budget

Stage1R-A Final Physical I/O Plan

Module Coverage Matrix

Transport Design Acceptance

Stage0.3 → 0.4 Transport Certification Handoff
```

Compute SHA-256 for every input.

Do not trust filenames alone.

---

# 2. HARD INPUT IDENTITY GATE

Compare every consumed SHA with the frozen Stage0.3 handoff.

Required:

```text
FROZEN_INPUT_SHA_MISMATCH_COUNT=0
```

If any mismatch:

```text
RESULT=BLOCKED
BLOCKER=FROZEN_STAGE0_3_INPUT_DRIFT
```

Do not continue.

---

# 3. DO NOT MODIFY THE FROZEN STAGE1R-A PLAN

0.4 is an execution-capability certification phase.

It must not silently change:

```text
which Stage1R-A actions exist

which source files Stage1R-A targets

which product questions they answer

which action type each uses

which module each informs
```

If certification proves a frozen action cannot be safely executed:

```text
record exact incompatibility
```

Do NOT edit Stage1R-A in place.

A later explicit execution-contract amendment, if necessary, must be separately versioned.

---

# 4. ABSOLUTE BUSINESS-SOURCE SAFETY BOUNDARY

All required:

```text
REAL_AMEC_BUSINESS_SOURCE_FILES_OPENED=0

REAL_AMEC_BUSINESS_SOURCE_BYTES_READ=0

REAL_AMEC_BUSINESS_SOURCE_HASHES=0

REAL_AMEC_BUSINESS_CONTENT_PARSED=0

REAL_AMEC_BUSINESS_SOURCE_MUTATIONS=0
```

A real business file must not be used:

```text
"just to test permissions"

"just to hash one file"

"just to see if the path works"
```

If no suitable synthetic/non-business fixture exists on the actual transport surface:

```text
do not weaken the rule
```

Follow the fixture-staging gate below.

---

# 5. SOURCE MUTATION BOUNDARY

Business source shares remain read-only.

Required:

```text
BUSINESS_SHARE_FILE_CREATES=0
BUSINESS_SHARE_FILE_RENAMES=0
BUSINESS_SHARE_FILE_MOVES=0
BUSINESS_SHARE_FILE_DELETES=0
BUSINESS_SHARE_FILE_WRITES=0
```

This phase is not write-back certification.

Phase 5 write-back remains future work.

---

# 6. CERTIFICATION FIXTURE POLICY

Certification may use only a fixture whose status is proven:

```text
SYNTHETIC_CERTIFICATION_FIXTURE

or

EXPLICIT_NON_BUSINESS_CERTIFICATION_FIXTURE
```

Each fixture must have:

```text
fixture_id

fixture_purpose

fixture_owner

fixture_origin

synthetic_or_non_business_proof

transport_location

share/path

expected_size

expected_sha256

format

expected structure/content assertions

allowed operation types

created_at / provenance
```

---

# 7. DO NOT ASSUME `ProposalOps-Inventory` IS AUTOMATICALLY TRANSPORT-EQUIVALENT

`ProposalOps-Inventory` remains never-source for business corpus purposes.

It may be used as a certification fixture location only if:

```text
the frozen Stage0.3 transport design permits it
and
the actual read mechanism exercised there is materially equivalent
to the intended source-read mechanism
```

If:

```text
share ACL
mount semantics
resolver path
transport route
filesystem behavior
```

could differ materially from authorized business source shares:

```text
SOURCE_SHARE_TRANSPORT_EQUIVALENCE=false
```

and do not claim full source-share certification from that fixture alone.

---

# 8. FIXTURE-STAGING GATE

First inspect whether suitable fixtures are already available on the intended transport surface.

If YES:

```text
verify their non-business/synthetic provenance
verify exact expected hashes
proceed
```

If NO:

Do not read a business file as a substitute.

Create locally:

```text
Synthetic_Transport_Certification_Fixture_Pack_v1/
```

plus:

```text
Fixture_Staging_Instructions_v1.md
Fixture_Manifest_v1.json
```

Then:

```text
RESULT=NOT_READY
BLOCKER=SYNTHETIC_FIXTURE_STAGING_REQUIRED
```

unless the already-authorized transport/output mechanism explicitly permits
placing fixtures into a designated non-business certification area without
modifying business source shares.

Do not invent new Synology write authority in Phase 0.4.

---

# 9. TRANSPORT TARGET MUST COME FROM THE FROZEN DESIGN

Read the Stage0.3 transport contract.

Allowed examples may include:

```text
READ_ONLY_SMB_DIRECT

DSM_TASK_SCHEDULER_BOUNDED_RESOLVER

OWNER_APPROVED_READ_ONLY_SOURCE_RESOLVER
```

Do not choose a convenient new transport merely because the designed one is difficult.

If the frozen design has multiple candidates:

```text
select the designated preferred candidate
```

or:

```text
RESULT=NOT_READY
BLOCKER=TRANSPORT_TARGET_NOT_FROZEN
```

if no candidate was actually selected.

---

# 10. INVENTORY TRANSPORT IS NOT SOURCE-READ TRANSPORT

Do not confuse:

```text
full / bounded metadata inventory scanner
```

with:

```text
exact-source content reader
```

0.4 certifies the latter.

A metadata scanner proving that a path exists does not prove:

```text
source bytes can be safely opened
source-version checks work
parser handoff works
```

---

# 11. NO NETWORK DISCOVERY

The certification harness may use only:

```text
predeclared endpoint
predeclared share
predeclared exact fixture path
```

Required:

```text
NETWORK_DISCOVERY_COUNT=0

SHARE_ENUMERATION_FOR_SOURCE_SELECTION=0

FUZZY_PATH_LOOKUPS=0

LATEST_FILE_SUBSTITUTIONS=0

NEAREST_NAME_SUBSTITUTIONS=0
```

---

# 12. EXACT PATH RESOLUTION

The exact resolver must reject:

```text
../ traversal

absolute-path escape

symlink escape

shortcut target following

.url target following

.lnk target following

directory target

path normalization that changes semantic target

fuzzy/case-insensitive substitution not guaranteed by actual filesystem contract
```

Create explicit negative tests.

---

# 13. REGULAR FILE ENFORCEMENT

Before source-byte access:

```text
record_type must be FILE
```

Reject:

```text
directory
symlink
special file
socket/device if surfaced
```

Required:

```text
NON_FILE_CONTENT_READS=0
```

---

# 14. READ-ONLY PROOF

Certification must prove the transport does not:

```text
write
rename
move
delete
chmod
touch mtime
create sidecars next to source
```

Capture pre/post fixture metadata.

Required:

```text
SOURCE_MUTATIONS_DURING_READ_CERT=0
```

---

# 15. SOURCE-VERSION PRECONDITION MODEL

Every test action has:

```text
expected_share
expected_relative_path
expected_size
expected_mtime_or_observation
expected_sha256 where applicable/available
```

Immediately before physical read:

```text
fresh stat
```

Compare against precondition.

If mismatch:

```text
SOURCE_VERSION_PRECONDITION_FAILED
```

and:

```text
bytes_read=0
```

unless a specific operation requires reading to establish the hash and the
frozen contract explicitly permits that state.

Do not silently read a newer file.

---

# 16. PRECONDITION PRIORITY

A metadata-only frozen plan may not yet contain source SHA.

Therefore distinguish:

```text
METADATA_VERSION_PRECONDITION
size + mtime / source observation

CONTENT_VERSION_PRECONDITION
sha256
```

The certification must prove the metadata precondition path because Stage1R-A
will encounter un-hashed files.

Once a hash is obtained, later operations can strengthen identity.

---

# 17. CHANGE-DURING-READ DETECTION

After physical read:

```text
fresh post-stat
```

Compare to pre-stat.

If material source metadata changed while reading:

```text
SOURCE_CHANGED_DURING_READ
```

The evidence result is invalid.

Required:

```text
CHANGED_DURING_READ_RESULTS_ACCEPTED=0
```

---

# 18. IMPORTANT LIMIT — STAT EQUALITY IS NOT PERFECT CONTENT IMMUTABILITY

Do not claim:

```text
same size + same mtime
→ mathematically proves bytes unchanged
```

It does not.

For HASH_ONLY:

```text
digest is the byte-identity evidence
```

For bounded/structure reads on un-hashed sources:

```text
pre/post metadata stability
+
read audit
```

supports execution consistency but is not an exact duplicate proof.

Represent this distinction explicitly.

---

# 19. ACTION TYPE 1 — HASH_ONLY

Certify:

```text
exact file stream
→ SHA-256
```

Required result fields:

```text
fixture/source identity

bytes_read

expected_size

actual_size

sha256

pre_stat

post_stat

duration

status
```

No content parser invoked.

Required:

```text
HASH_ONLY_PARSER_INVOCATIONS=0
```

---

# 20. HASH STREAMING

Hash must be incremental/streaming.

Do not load arbitrarily large file fully into memory merely to calculate SHA-256.

Record:

```text
chunk_size

peak memory if measurable

bytes_streamed
```

No specific chunk size is mandated unless the frozen design already defines one.

---

# 21. HASH CHECKPOINT / RESTART — DO NOT FAKE BYTE-LEVEL RESUME

Standard SHA-256 continuation state is not assumed serializable by the runtime.

Therefore Phase 0.4 only requires:

```text
ACTION-LEVEL checkpoint/restart
```

Meaning:

```text
completed action
→ not rerun unnecessarily

interrupted hash action
→ on retry, revalidate source precondition
→ restart hash safely from byte 0
```

Do not claim mid-file hash resume unless explicitly implemented and proven.

---

# 22. ACTION TYPE 2 — STRUCTURE_READ

Goal:

```text
understand document structure
without unnecessary business values
```

Possible outputs:

```text
document type

page/section count

headings

field labels

table/grid shape

sheet names if allowed

content-control names

form labels

attachment structure

basic metadata
```

The exact structure contract depends on format.

---

# 23. ACTION TYPE 3 — BOUNDED_CONTENT_READ

Goal:

```text
answer an explicit frozen product question
```

Output must be bounded by:

```text
allowed page/section/sheet/range

allowed output fields

max extracted characters/bytes

retention policy
```

No open-ended document dump.

---

# 24. PHYSICAL SOURCE BYTES VS EXTRACTED OUTPUT BYTES

This is a mandatory accounting distinction.

A bounded logical content request may still require a parser to physically read
the whole file/container.

Therefore separately meter:

```text
PHYSICAL_SOURCE_BYTES_READ

EXTRACTED_OUTPUT_BYTES

RETAINED_EVIDENCE_BYTES
```

Do not report:

```text
"read pages 1–2"
```

as though only those page bytes crossed the transport unless that is actually
proven.

---

# 25. PHYSICAL I/O BUDGET COMPATIBILITY

Compare measured parser/transport behavior to the frozen Stage1R-A Physical I/O
Plan.

If a reader requires more physical source bytes than the frozen execution
budget assumed:

```text
PHYSICAL_IO_BUDGET_MODEL_MISMATCH
```

Do not silently enlarge the Stage1R-A budget.

0.4 may still characterize the required budget, but cannot return full PASS
until every frozen A action has a compatible certified execution model.

---

# 26. DERIVE REQUIRED FORMAT × ACTION MATRIX FROM STAGE1R-A

Do not hardcode formats.

Build:

```text
extension / MIME / format family
×
HASH_ONLY
STRUCTURE_READ
BOUNDED_CONTENT_READ
```

from the final frozen Stage1R-A allowlist.

Example only:

```text
PDF × HASH_ONLY
PDF × STRUCTURE_READ
PDF × BOUNDED_CONTENT_READ

DOCX × STRUCTURE_READ

XLSX × BOUNDED_CONTENT_READ

DWG × HASH_ONLY
```

Certify every combination actually required by Stage1R-A.

---

# 27. UNKNOWN / AMBIGUOUS FORMAT

If a Stage1R-A content action has:

```text
unknown format
unsupported format
ambiguous parser
```

then:

```text
STAGE1R_A_COMPATIBILITY=false
```

Do not guess parser behavior.

---

# 28. PDF READER CONTRACT

For PDF structure/content reads:

```text
text layer only
```

Do NOT:

```text
OCR
execute JavaScript
execute embedded actions
open remote URLs
extract embedded files automatically
```

Handle:

```text
encrypted/password protected
malformed
image-only
```

as explicit unsupported/error states unless a safe reader capability is
separately certified.

---

# 29. DOCX READER CONTRACT

Allowed:

```text
safe OOXML package parsing

paragraph/headings

tables

content-control / field structure when safely available

bounded text extraction
```

Prohibited:

```text
macro execution

external relationship fetch

remote template fetch

OLE execution
```

---

# 30. XLSX READER CONTRACT

Allowed:

```text
sheet names

defined bounded cells/ranges

table structure

stored formula text/value where appropriate
```

Prohibited:

```text
formula recalculation

external-link refresh

macro execution

data connection refresh
```

Hidden sheets/cells must not be included unless the frozen action explicitly
requires them.

---

# 31. PPTX READER CONTRACT

Allowed:

```text
slide titles

bounded text

basic structure
```

Prohibited:

```text
macro execution

external fetch

embedded-object execution
```

---

# 32. OFFICE OPEN XML IS A ZIP CONTAINER — HANDLE SAFELY

DOCX/XLSX/PPTX internal ZIP package parsing is not the same as authorizing
general archive extraction.

The safe OOXML reader must enforce:

```text
member count bound

total uncompressed byte bound

compression-ratio / zip-bomb guard

no `../` package path traversal

no external relationship fetch

no executable payload launch
```

Required:

```text
OOXML_ZIP_BOMB_GUARD_CERTIFIED=true
```

if Stage1R-A requires OOXML content/structure reads.

---

# 33. MACRO-ENABLED OFFICE FILES

If Stage1R-A includes:

```text
DOCM
XLSM
PPTM
```

content/structure reads:

Do not execute macros.

Either:

```text
certify safe non-macro OOXML structure/content parsing
```

or:

```text
mark required combination NOT_CERTIFIED
```

Do not silently treat macro-enabled files as ordinary Office documents.

---

# 34. CSV / TXT / XML / JSON

If required by Stage1R-A:

Certify:

```text
encoding handling

bounded line/record reads

size limits

no entity expansion attacks for XML

no external entity fetch
```

For XML:

```text
XXE disabled
```

---

# 35. EML / MSG

If required:

```text
no remote-image fetch

no URL fetch

no automatic attachment execution

attachments separately authorized
```

Return only the exact fields required by frozen product question.

---

# 36. IMAGE / SCAN

If Stage1R-A requires content from:

```text
JPG
PNG
TIFF
image-only PDF
```

and that requires OCR:

```text
OCR_NOT_AUTHORIZED
```

0.4 cannot certify that action.

Do not silently invoke OCR.

---

# 37. ARBITRARY ARCHIVES

For:

```text
ZIP
RAR
7Z
other archive
```

general extraction remains:

```text
NOT_AUTHORIZED
```

unless the frozen A action is HASH_ONLY.

---

# 38. CAD / BINARY ENGINEERING FORMATS

For:

```text
DWG
DXF
DWF
other engineering binary
```

HASH_ONLY may be certified generically.

Content/structure parsing requires a specific safe parser contract.

Do not invent one.

---

# 39. RAW SOURCE RETENTION

For HASH_ONLY:

```text
retain digest + source identity + audit
```

not full raw copied bytes.

For STRUCTURE_READ / BOUNDED_CONTENT_READ:

retain only the allowed evidence output.

Do not create a shadow corpus of raw source copies.

---

# 40. TEMP FILE POLICY

Prefer streaming.

If a parser requires a temporary local file:

```text
restricted per-run temp directory

random/non-user-controlled temp name

no executable permission if controllable

not in product storage

not indexed

deleted after action

deletion verified at path level
```

Do not claim secure physical erasure.

Report:

```text
TEMP_RAW_SOURCE_FILES_RETAINED_AFTER_ACTION=0
```

---

# 41. SYNTHETIC MINIMIZATION CANARIES

Create synthetic fixtures containing clearly fake canary values such as:

```text
SYNTHETIC_PASSPORT_CANARY_001

SYNTHETIC_QID_CANARY_002

SYNTHETIC_IBAN_CANARY_003

SYNTHETIC_SALARY_CANARY_004

SYNTHETIC_SECRET_CANARY_005
```

Use them to prove:

```text
STRUCTURE_READ
does not emit unrequested values

BOUNDED_CONTENT_READ
does not emit values outside allowed scope

MINIMIZE_VALUES retention
does not preserve irrelevant canary values
```

These are synthetic test strings only.

---

# 42. BOUNDED-READ NEGATIVE CANARY

For each bounded reader fixture, place a unique canary outside the authorized
scope.

Examples:

```text
PDF:
canary on page 5
request pages 1–2

XLSX:
canary on hidden/unrequested sheet
request one named range

DOCX:
canary under an unrequested heading/section
```

Required:

```text
OUT_OF_SCOPE_CANARY_LEAK_COUNT=0
```

---

# 43. EXTERNAL-RESOURCE CANARY

Where safe/feasible, include a synthetic document relationship pointing to a
non-routable or test URL.

Required:

```text
EXTERNAL_RESOURCE_FETCH_ATTEMPTS=0
```

Do not make real external network calls.

---

# 44. CERTIFICATION FIXTURE SET

The fixture suite must cover:

```text
every Stage1R-A-required format × action combination

small file

medium streaming file

zero-byte file where relevant

malformed file

encrypted/protected file where format supports it

precondition mismatch

change during read

directory target

symlink/shortcut target

path traversal request

unsupported format/action

bounded-output canary

minimization canary
```

Do not generate huge fixtures merely to imitate large objects if final
Stage1R-A has no large objects.

---

# 45. SIZE REPRESENTATIVENESS

Use Stage1R-A final size-band distribution.

Certification should exercise:

```text
the largest actually required Stage1R-A size band
```

without needlessly reproducing every large real byte count.

The goal is:

```text
streaming correctness
metering correctness
memory safety
```

not synthetic storage waste.

---

# 46. RUNTIME I/O METER

Every certification action records:

```text
physical_file_opens

physical_source_bytes_read

hash_bytes

parser_input_bytes

extracted_output_bytes

retained_evidence_bytes

duration

retry_count
```

No counter may be inferred from file size when actual measurement is possible.

---

# 47. ENFORCE PER-ACTION MAXIMUMS

The executor must reject or stop requests exceeding frozen/action-level:

```text
max bytes

allowed operation

allowed page/range/section

allowed extracted output

timeout

retry policy
```

Required:

```text
BUDGET_OVERRUN_ACCEPTED_COUNT=0
```

---

# 48. GLOBAL CERTIFICATION BUDGET

Create a small certification-only budget.

It is not the Stage1R-A real execution budget.

Track:

```text
max fixture opens

max fixture bytes

max retries

max parser actions

max concurrent reads
```

Initial certification concurrency:

```text
1
```

unless frozen infrastructure already requires another value.

---

# 49. NO CONCURRENCY OPTIMIZATION IN CERTIFICATION

Run sequentially first.

Do not introduce parallel source reads merely to improve wall-clock time.

The objective is correctness and evidence.

---

# 50. CHECKPOINT / RESTART CONTRACT

Checkpoint at action granularity.

Persist:

```text
action_id

fixture_id

attempt

precondition state

status

evidence result hash

completed_at
```

On process restart:

```text
completed actions
→ do not repeat

failed/interrupted actions
→ revalidate fixture/source version
→ restart deterministically
```

No stale continuation.

---

# 51. IDEMPOTENT CERTIFICATION RESULT

Running the same certification against unchanged fixtures and same code/config
must produce equivalent semantic results.

Record:

```text
determinism_run_1
determinism_run_2
```

Expected:

```text
same status

same hash outputs

same evidence payload semantics

same capability state
```

Timing may differ.

---

# 52. FAILURE INJECTION — PRECONDITION CHANGED BEFORE READ

Synthetic test:

```text
plan fixture version A
modify synthetic fixture to version B
attempt action pinned to A
```

Expected:

```text
SOURCE_VERSION_PRECONDITION_FAILED
bytes_read=0
```

---

# 53. FAILURE INJECTION — CHANGE DURING READ

Use a controlled synthetic fixture/process.

Modify fixture during an intentionally slowed streaming read.

Expected:

```text
SOURCE_CHANGED_DURING_READ
result rejected
```

Do not use a real AMEC file.

---

# 54. FAILURE INJECTION — CONNECTION / READ INTERRUPTION

Use a harness-level injected read failure unless it is safe to reproduce a real
transport interruption.

Label:

```text
FAULT_INJECTION_METHOD=
REAL_TRANSPORT
or
HARNESS_SIMULATED
```

Never imply a simulated failure proves an infrastructure behavior it does not.

Expected:

```text
action incomplete
checkpoint written
no false success
retry requires fresh precondition
```

---

# 55. FAILURE INJECTION — PARSER ERROR

Malformed synthetic file.

Expected:

```text
PARSER_FAILED
```

No fallback to:

```text
full-file AI upload

OCR

alternate unsafe parser

silent raw-text dump
```

---

# 56. FAILURE INJECTION — PERMISSION DENIAL

If safe to test on certification fixture:

```text
permission denied
→ explicit ACCESS_DENIED
```

If actual transport permissions cannot be safely manipulated:

use harness simulation and label it.

Do not change business-share ACLs.

---

# 57. FAILURE INJECTION — PATH TRAVERSAL

Requests like:

```text
../
../../
absolute path outside allowed root
```

must be rejected before source open.

Required:

```text
PATH_ESCAPE_OPENS=0
```

---

# 58. FAILURE INJECTION — SYMLINK / LINK

Synthetic link fixture if supported.

Expected:

```text
LINK_TARGET_NOT_FOLLOWED
```

No source bytes from target.

---

# 59. FAILURE INJECTION — DIRECTORY

Exact selector targets directory.

Expected:

```text
NOT_A_REGULAR_FILE
```

No content read.

---

# 60. FAILURE INJECTION — BUDGET LIMIT

Request content beyond allowed output or source-byte ceiling.

Expected:

```text
BUDGET_LIMIT_ENFORCED
```

No silent continuation.

---

# 61. FAILURE INJECTION — DUPLICATE RETRY

Re-submit same certification action after completed success.

Expected:

```text
existing completed result reused
```

or deterministic no-op according to harness contract.

Do not duplicate retained evidence.

---

# 62. AUDIT CONTRACT

Every action attempt emits:

```text
root_run_id

cert_action_id

fixture_id

transport implementation/version

reader implementation/version

operation

precondition

pre_stat

physical bytes

result

post_stat

evidence hash

budget outcome

retry state

fault injection state if applicable

timestamps
```

---

# 63. NO SECRET OUTPUT IN LOGS

Even synthetic canaries should be handled according to the same logging rules.

Logs should not dump arbitrary document content.

Required:

```text
RAW_DOCUMENT_CONTENT_IN_OPERATIONAL_LOGS=0
```

---

# 64. CERTIFICATION CODE / HARNESS LOCATION

Any certification-only implementation must be isolated from the live
application unless the frozen repository already contains the exact adapter.

Preferred:

```text
dedicated isolated worktree / control tooling
```

Do not modify the primary workspace.

Do not touch:

```text
main
release deployment
production DB
```

unless this prompt explicitly authorizes it.

It does not.

---

# 65. PRIMARY WORKSPACE PRESERVATION

Before and after:

```text
record git status

record HEAD

record known pre-existing modifications
```

Do not clean/reset/delete unrelated user changes.

Required:

```text
PRIMARY_WORKSPACE_NEW_UNRELATED_CHANGES=0
```

---

# 66. IMPLEMENTATION ALLOWED IN 0.4

0.4 may implement the minimum certification harness required to test the frozen
transport design and evidence readers.

Allowed:

```text
test-only resolver adapter

synthetic fixture generator

safe format reader adapters

budget meter

audit/result envelope

fault injection harness

checkpoint state
```

Not allowed:

```text
wire live ProposalOps UI

write operational DB records

enable production source reads

deploy

create continuous trigger

create write-back
```

---

# 67. READER LIBRARY / DEPENDENCY RULE

Prefer already-approved / installed libraries.

Do not fetch or install arbitrary new packages silently.

If a required Stage1R-A format needs a new dependency:

```text
record dependency

license/source if locally known

security implications

exact capability needed
```

and:

```text
RESULT=NOT_READY
```

unless repository policy explicitly permits adding it within this isolated
certification scope.

Do not use an online service to parse source files.

---

# 68. LLM / AI USE IN 0.4

This phase is transport/reader certification.

The source evidence reader itself should be deterministic where possible.

Do not send certification fixtures to an external model merely to prove
transport.

If the final Stage1R-A later requires model-assisted semantic interpretation,
that is a separate evidence-interpretation layer.

0.4 certifies:

```text
source acquisition
safe parsing
bounded extraction
```

not model reasoning quality.

---

# 69. CAPABILITY MATRIX

Produce exact states for every required capability.

Allowed:

```text
CERTIFIED

NOT_CERTIFIED

NOT_REQUIRED_BY_STAGE1R_A

BLOCKED_BY_FIXTURE

BLOCKED_BY_DEPENDENCY
```

At minimum:

```text
EXACT_PATH_RESOLUTION

REGULAR_FILE_ENFORCEMENT

READ_ONLY_BEHAVIOR

SOURCE_VERSION_PRECONDITION

CHANGE_DURING_READ_DETECTION

HASH_SHA256

CHECKPOINT_RESTART

BUDGET_METERING

AUDIT

TEMP_FILE_CLEANUP

per format/action combination
```

---

# 70. STAGE1R-A COMPATIBILITY JOIN

Join every frozen Stage1R-A action to the certification capability matrix.

For each action:

```text
action_id

format

operation

required capability IDs

certification state

compatible
true/false

blocker
```

Required for PASS:

```text
STAGE1R_A_ACTIONS_WITH_UNCERTIFIED_REQUIRED_CAPABILITY=0
```

---

# 71. DO NOT "DOWNGRADE" A FROZEN ACTION SILENTLY

Example:

```text
frozen action = PDF BOUNDED_CONTENT_READ
```

If only PDF HASH_ONLY is certified:

```text
compatible=false
```

Do not silently turn the frozen action into a hash.

---

# 72. TRANSPORT CERTIFICATION MUST BE INTEGRATED, NOT ONLY LOCAL-PARSER TESTS

A local synthetic parser test proves reader behavior.

It does not prove actual source transport.

PASS requires:

```text
actual intended read transport
+
certification fixture
+
reader
+
budget
+
audit
```

integrated for every required operation class.

---

# 73. SOURCE-SHARE ACL / TRANSPORT EQUIVALENCE

If synthetic fixture runs on a test/output share:

Assess whether intended business-source shares differ in:

```text
read ACL

mount options

SMB protocol/path semantics

filesystem behavior

resolver privilege
```

If differences remain unproven:

```text
SOURCE_SHARE_PERMISSION_EQUIVALENCE=UNVERIFIED
```

This must not be disguised as full certification.

A PASS may require an explicitly non-business fixture on the same authorized
source transport boundary.

If no such fixture exists:

```text
NOT_READY
```

rather than reading business bytes.

---

# 74. WHAT COUNTS AS PASS

`RESULT=PASS` only if all are true:

```text
Stage0.3 frozen inputs match

actual intended read transport exercised

only synthetic/non-business bytes read

no business bytes opened/read/hashed

exact resolver certified

regular-file gate certified

read-only behavior certified

source-version precondition certified

change-during-read detection certified

hash streaming certified

checkpoint/restart certified

budget metering certified

audit certified

all Stage1R-A-required format × action combinations certified

every Stage1R-A action maps to certified capabilities

zero parser/source-operation safety invariant failures

zero source mutations
```

---

# 75. WHAT COUNTS AS NOT_READY

Use `NOT_READY` when:

```text
fixture staging required

transport target not frozen

source-share transport equivalence unproven

required reader dependency missing

required format/action not certified

physical-I/O model exceeds frozen budget

required parser cannot safely bound output

actual integrated transport cannot be exercised without touching business bytes
```

This is not failure.

It is an exact prerequisite.

---

# 76. WHAT COUNTS AS BLOCKED

Use `BLOCKED` for:

```text
frozen input identity mismatch

source mutation occurred

business source bytes were accessed

path escape occurred

silent fallback occurred

certification result cannot be reproduced

critical safety invariant failure
```

---

# 77. SILENT FALLBACK = ZERO TOLERANCE

Required:

```text
TRANSPORT_FAILURE_TO_MOCK_FALLBACK=0

TRANSPORT_FAILURE_TO_LOCAL_STALE_COPY=0

PARSER_FAILURE_TO_OCR_FALLBACK=0

PARSER_FAILURE_TO_FULL_BINARY_AI_FALLBACK=0

PATH_FAILURE_TO_FUZZY_SUBSTITUTION=0
```

If the certified route fails:

```text
fail explicitly
```

---

# 78. REQUIRED EVIDENCE DIRECTORY

Create outside Git:

```text
<local ProposalOps-Control>/
proposalops-amec-phase3b-0-4-transport-reader-certification-<run-id>/
```

---

# 79. REQUIRED ARTIFACTS

At minimum:

```text
01_PHASE3B_0_4_PROVENANCE.md

02_AMEC_Phase3B_0_4_Frozen_Input_Identity_Manifest_v1.json
03_AMEC_Phase3B_0_4_Frozen_Input_Identity_Manifest_v1.md

04_AMEC_Phase3B_0_4_Required_Format_Action_Matrix_v1.csv
05_AMEC_Phase3B_0_4_Required_Format_Action_Matrix_v1.json
06_AMEC_Phase3B_0_4_Required_Format_Action_Matrix_v1.md

07_AMEC_Phase3B_0_4_Certification_Fixture_Manifest_v1.json
08_AMEC_Phase3B_0_4_Certification_Fixture_Manifest_v1.md

09_AMEC_Phase3B_0_4_Fixture_Staging_Audit_v1.json
10_AMEC_Phase3B_0_4_Fixture_Staging_Audit_v1.md

11_AMEC_Phase3B_0_4_Exact_Source_Resolver_Certification_v1.json
12_AMEC_Phase3B_0_4_Exact_Source_Resolver_Certification_v1.md

13_AMEC_Phase3B_0_4_Source_Version_Integrity_Certification_v1.json
14_AMEC_Phase3B_0_4_Source_Version_Integrity_Certification_v1.md

15_AMEC_Phase3B_0_4_Hash_Reader_Certification_v1.json
16_AMEC_Phase3B_0_4_Hash_Reader_Certification_v1.md

17_AMEC_Phase3B_0_4_Structure_Read_Certification_v1.json
18_AMEC_Phase3B_0_4_Structure_Read_Certification_v1.md

19_AMEC_Phase3B_0_4_Bounded_Content_Read_Certification_v1.json
20_AMEC_Phase3B_0_4_Bounded_Content_Read_Certification_v1.md

21_AMEC_Phase3B_0_4_Parser_Security_Audit_v1.json
22_AMEC_Phase3B_0_4_Parser_Security_Audit_v1.md

23_AMEC_Phase3B_0_4_Minimization_Canary_Audit_v1.json
24_AMEC_Phase3B_0_4_Minimization_Canary_Audit_v1.md

25_AMEC_Phase3B_0_4_Runtime_IO_Meter_Certification_v1.json
26_AMEC_Phase3B_0_4_Runtime_IO_Meter_Certification_v1.md

27_AMEC_Phase3B_0_4_Checkpoint_Restart_Certification_v1.json
28_AMEC_Phase3B_0_4_Checkpoint_Restart_Certification_v1.md

29_AMEC_Phase3B_0_4_Failure_Injection_Results_v1.json
30_AMEC_Phase3B_0_4_Failure_Injection_Results_v1.md

31_AMEC_Phase3B_0_4_Capability_Matrix_v1.csv
32_AMEC_Phase3B_0_4_Capability_Matrix_v1.json
33_AMEC_Phase3B_0_4_Capability_Matrix_v1.md

34_AMEC_Phase3B_0_4_Stage1R_A_Compatibility_Audit_v1.csv
35_AMEC_Phase3B_0_4_Stage1R_A_Compatibility_Audit_v1.json
36_AMEC_Phase3B_0_4_Stage1R_A_Compatibility_Audit_v1.md

37_AMEC_Phase3B_0_4_Transport_Certification_Freeze_Manifest_v1.json
38_AMEC_Phase3B_0_4_Transport_Certification_Freeze_Manifest_v1.md

39_AMEC_Phase3B_0_4_to_0_5_Execution_Authorization_Handoff_v1.json
40_AMEC_Phase3B_0_4_to_0_5_Execution_Authorization_Handoff_v1.md

41_PHASE3B_0_4_INVARIANT_AUDIT.json
42_PHASE3B_0_4_INVARIANT_AUDIT.md

summary.json
```

If fixture staging is not yet possible, still create:

```text
Synthetic_Transport_Certification_Fixture_Pack_v1/
Fixture_Staging_Instructions_v1.md
```

and return NOT_READY precisely.

---

# 80. CERTIFICATION FREEZE MANIFEST

Pin:

```text
Stage0.3 Freeze Manifest SHA

Stage1R-A Plan SHA

Stage1R-A Allowlist SHA

Stage1R-A Action IDs SHA

Stage1R-A Budget SHA

Stage1R-A Physical I/O Plan SHA

Module Coverage SHA

transport implementation source SHA / script SHA

reader implementation SHA(s)

fixture manifest SHA

capability matrix SHA

compatibility audit SHA

invariant audit SHA
```

---

# 81. 0.4 → 0.5 HANDOFF

On PASS create immutable handoff for:

```text
Phase 3B.0.5
Exact Stage1R-A Execution Authorization
```

It must pin:

```text
frozen Stage1R-A artifact SHAs

certified transport SHA/version

certified reader versions

capability matrix SHA

compatibility audit SHA

certification fixture manifest SHA

physical-I/O meter certification SHA

failure-injection audit SHA

zero-business-source-access proof
```

---

# 82. DO NOT AUTHORIZE STAGE1R-A IN 0.4

Required:

```text
STAGE1R_A_EXECUTION_AUTHORIZED=false

STAGE1R_B_EXECUTION_AUTHORIZED=false

STAGE2_EXECUTION_AUTHORIZED=false

STAGE3_EXECUTION_AUTHORIZED=false

REAL_AMEC_SOURCE_READ_AUTHORIZED=false
```

0.5 is the authorization gate.

---

# 83. PHASE 0.5 SHOULD BE SMALL

The 0.4 handoff should make 0.5 mechanical:

```text
these exact action IDs

these exact source selectors

these exact operation types

these exact certified readers

these exact physical I/O ceilings

these exact retention rules

these exact stop conditions
```

No new relevance analysis.

---

# 84. HARD INVARIANTS

Required zero:

```text
FROZEN_INPUT_SHA_MISMATCH_COUNT

REAL_AMEC_BUSINESS_SOURCE_FILES_OPENED

REAL_AMEC_BUSINESS_SOURCE_BYTES_READ

REAL_AMEC_BUSINESS_SOURCE_HASHES

REAL_AMEC_BUSINESS_CONTENT_PARSED

REAL_AMEC_BUSINESS_SOURCE_MUTATIONS

BUSINESS_SHARE_FILE_CREATES

BUSINESS_SHARE_FILE_RENAMES

BUSINESS_SHARE_FILE_MOVES

BUSINESS_SHARE_FILE_DELETES

BUSINESS_SHARE_FILE_WRITES

NETWORK_DISCOVERY_COUNT

SHARE_ENUMERATION_FOR_SOURCE_SELECTION

FUZZY_PATH_LOOKUPS

LATEST_FILE_SUBSTITUTIONS

NEAREST_NAME_SUBSTITUTIONS

NON_FILE_CONTENT_READS

SOURCE_MUTATIONS_DURING_READ_CERT

CHANGED_DURING_READ_RESULTS_ACCEPTED

HASH_ONLY_PARSER_INVOCATIONS

OUT_OF_SCOPE_CANARY_LEAK_COUNT

EXTERNAL_RESOURCE_FETCH_ATTEMPTS

TEMP_RAW_SOURCE_FILES_RETAINED_AFTER_ACTION

BUDGET_OVERRUN_ACCEPTED_COUNT

PATH_ESCAPE_OPENS

RAW_DOCUMENT_CONTENT_IN_OPERATIONAL_LOGS

TRANSPORT_FAILURE_TO_MOCK_FALLBACK

TRANSPORT_FAILURE_TO_LOCAL_STALE_COPY

PARSER_FAILURE_TO_OCR_FALLBACK

PARSER_FAILURE_TO_FULL_BINARY_AI_FALLBACK

PATH_FAILURE_TO_FUZZY_SUBSTITUTION

PRIMARY_WORKSPACE_NEW_UNRELATED_CHANGES

STAGE1R_A_ACTIONS_WITH_UNCERTIFIED_REQUIRED_CAPABILITY
```

---

# 85. REQUIRED POSITIVE GATES FOR PASS

Required true where applicable:

```text
FROZEN_INPUT_IDENTITY_PASS

ACTUAL_INTENDED_TRANSPORT_EXERCISED

CERT_FIXTURE_PROVEN_SYNTHETIC_OR_NON_BUSINESS

EXACT_PATH_RESOLUTION_CERTIFIED

REGULAR_FILE_ENFORCEMENT_CERTIFIED

READ_ONLY_BEHAVIOR_CERTIFIED

SOURCE_VERSION_PRECONDITION_CERTIFIED

CHANGE_DURING_READ_DETECTION_CERTIFIED

SHA256_STREAMING_CERTIFIED

ACTION_LEVEL_CHECKPOINT_RESTART_CERTIFIED

RUNTIME_IO_METERING_CERTIFIED

AUDIT_CERTIFIED

FAILURE_INJECTION_SUITE_PASS

STAGE1R_A_FORMAT_ACTION_MATRIX_COMPLETE

STAGE1R_A_COMPATIBILITY_PASS

ZERO_BUSINESS_SOURCE_ACCESS_PASS
```

---

# 86. REQUIRED SUMMARY CONTRACT

Create:

```json
{
  "phase": "AMEC_PHASE3B_0_4_TRANSPORT_AND_EVIDENCE_READER_CERTIFICATION",
  "revision": "v1.0",

  "result": "PASS|NOT_READY|BLOCKED",

  "frozen_stage0_3_inputs": {
    "identity_pass": false,
    "stage0_3_freeze_manifest_sha256": "",
    "stage1r_a_plan_sha256": "",
    "stage1r_a_allowlist_sha256": "",
    "stage1r_a_action_ids_sha256": "",
    "stage1r_a_budget_sha256": "",
    "stage1r_a_physical_io_plan_sha256": "",
    "module_coverage_sha256": ""
  },

  "fixture": {
    "fixture_ready": false,
    "fixture_type": "SYNTHETIC|EXPLICIT_NON_BUSINESS|NONE",
    "actual_transport_surface_exercised": false,
    "source_share_transport_equivalence": "PROVEN|UNVERIFIED|NOT_APPLICABLE",
    "fixture_manifest_sha256": ""
  },

  "transport": {
    "target": "",
    "implementation_sha256": "",
    "actual_intended_transport_exercised": false,
    "exact_path_resolution_certified": false,
    "regular_file_enforcement_certified": false,
    "read_only_behavior_certified": false,
    "source_version_precondition_certified": false,
    "change_during_read_detection_certified": false,
    "checkpoint_restart_certified": false,
    "audit_certified": false
  },

  "readers": {
    "hash_sha256_streaming_certified": false,
    "required_format_action_combinations": 0,
    "certified_format_action_combinations": 0,
    "uncertified_required_combinations": 0,
    "ooxml_zip_bomb_guard_required": false,
    "ooxml_zip_bomb_guard_certified": false,
    "ocr_authorized": false,
    "general_archive_extraction_authorized": false
  },

  "budget": {
    "runtime_io_metering_certified": false,
    "budget_overrun_accepted_count": 0,
    "certification_physical_file_opens": 0,
    "certification_physical_source_bytes_read": 0,
    "certification_extracted_output_bytes": 0,
    "certification_retained_evidence_bytes": 0,
    "stage1r_a_physical_io_budget_compatible": false
  },

  "compatibility": {
    "stage1r_a_actions_total": 0,
    "stage1r_a_actions_compatible": 0,
    "stage1r_a_actions_with_uncertified_required_capability": 0,
    "compatibility_pass": false
  },

  "failure_injection": {
    "precondition_mismatch_pass": false,
    "changed_during_read_pass": false,
    "read_interruption_pass": false,
    "parser_failure_pass": false,
    "path_traversal_pass": false,
    "link_following_rejected_pass": false,
    "directory_rejected_pass": false,
    "budget_limit_pass": false,
    "duplicate_retry_pass": false
  },

  "safety": {
    "real_amec_business_source_files_opened": 0,
    "real_amec_business_source_bytes_read": 0,
    "real_amec_business_source_hashes": 0,
    "real_amec_business_content_parsed": 0,
    "real_amec_business_source_mutations": 0,
    "silent_fallback_count": 0,
    "raw_document_content_in_operational_logs": 0
  },

  "authorization": {
    "real_amec_source_read_authorized": false,
    "stage1r_a_execution_authorized": false,
    "stage1r_b_execution_authorized": false,
    "stage2_execution_authorized": false,
    "stage3_execution_authorized": false
  },

  "ready_for_phase3b_0_5_exact_execution_authorization": false,

  "next": ""
}
```

---

# 87. PASS HANDOFF FORMAT

On PASS:

```text
PROPOSALOPS_AMEC_PHASE3B_0_4_COMPLETE

RESULT=PASS

FROZEN_STAGE0_3_INPUT_IDENTITY_PASS=true

ACTUAL_INTENDED_TRANSPORT_EXERCISED=true

CERT_FIXTURE_TYPE=<SYNTHETIC|EXPLICIT_NON_BUSINESS>

EXACT_PATH_RESOLUTION_CERTIFIED=true
REGULAR_FILE_ENFORCEMENT_CERTIFIED=true
READ_ONLY_BEHAVIOR_CERTIFIED=true

SOURCE_VERSION_PRECONDITION_CERTIFIED=true
CHANGE_DURING_READ_DETECTION_CERTIFIED=true

HASH_SHA256_STREAMING_CERTIFIED=true

REQUIRED_FORMAT_ACTION_COMBINATIONS=<n>
CERTIFIED_FORMAT_ACTION_COMBINATIONS=<n>
UNCERTIFIED_REQUIRED_FORMAT_ACTION_COMBINATIONS=0

ACTION_LEVEL_CHECKPOINT_RESTART_CERTIFIED=true
RUNTIME_IO_METERING_CERTIFIED=true
AUDIT_CERTIFIED=true
FAILURE_INJECTION_SUITE_PASS=true

STAGE1R_A_ACTIONS_TOTAL=<n>
STAGE1R_A_ACTIONS_COMPATIBLE=<n>
STAGE1R_A_ACTIONS_WITH_UNCERTIFIED_REQUIRED_CAPABILITY=0

STAGE1R_A_PHYSICAL_IO_BUDGET_COMPATIBLE=true

REAL_AMEC_BUSINESS_SOURCE_FILES_OPENED=0
REAL_AMEC_BUSINESS_SOURCE_BYTES_READ=0
REAL_AMEC_BUSINESS_SOURCE_HASHES=0
REAL_AMEC_BUSINESS_CONTENT_PARSED=0
REAL_AMEC_BUSINESS_SOURCE_MUTATIONS=0

SOURCE_MUTATIONS_DURING_READ_CERT=0
SILENT_FALLBACK_COUNT=0

STAGE1R_A_EXECUTION_AUTHORIZED=false
STAGE1R_B_EXECUTION_AUTHORIZED=false
STAGE2_EXECUTION_AUTHORIZED=false
STAGE3_EXECUTION_AUTHORIZED=false

READY_FOR_PHASE3B_0_5_EXACT_EXECUTION_AUTHORIZATION=true

TRANSPORT_CERTIFICATION_FREEZE_MANIFEST_SHA256=<sha>

EVIDENCE_DIR=<path>

NEXT=Phase 3B.0.5 exact Stage1R-A execution authorization using the frozen Stage0.3 candidate plus this certification freeze; no new relevance analysis.
```

---

# 88. NOT_READY HANDOFF FORMAT

If prerequisites remain:

```text
PROPOSALOPS_AMEC_PHASE3B_0_4_COMPLETE

RESULT=NOT_READY

COMPLETED_SUBGATES=<...>

BLOCKER=<single precise blocker>

REAL_AMEC_BUSINESS_SOURCE_BYTES_READ=0
REAL_AMEC_BUSINESS_SOURCE_HASHES=0
REAL_AMEC_BUSINESS_SOURCE_MUTATIONS=0

READY_FOR_PHASE3B_0_5_EXACT_EXECUTION_AUTHORIZATION=false

NEXT=<exact smallest remediation>
```

Examples:

```text
SYNTHETIC_FIXTURE_STAGING_REQUIRED

TRANSPORT_TARGET_NOT_FROZEN

SOURCE_SHARE_TRANSPORT_EQUIVALENCE_UNPROVEN

REQUIRED_PDF_BOUNDED_READER_NOT_CERTIFIED

PHYSICAL_IO_BUDGET_MODEL_MISMATCH
```

Do not invent another generic planning phase.

---

# 89. AFTER 0.4 PASSES

The next phase is deliberately small:

```text
Phase 3B.0.5
Exact Stage1R-A Execution Authorization
```

It must authorize:

```text
exact action IDs

exact source selectors

exact operation types

exact certified reader versions

exact physical opens

exact physical-byte ceilings

exact retention/minimization rules

exact stop conditions
```

Then and only then:

```text
Phase 3B Stage1R-A
FIRST REAL AMEC SOURCE EVIDENCE RUN
```

---

# 90. DO NOT START PHASE 5

Do not implement:

```text
continuous trigger

Source Change Monitor

live classifier v2

write-back

Synology mutation
```

in this phase.

Complete the historical corpus truth chain first:

```text
0.4 certification
→ 0.5 authorization
→ Stage1R-A real evidence
→ evidence sufficiency review
→ only necessary Stage1R-B subset
→ Phase 3C Module Truth
→ Phase 4 corpus→app contract
```

Then build the stronger production classifier and continuous integration loop.

# END
