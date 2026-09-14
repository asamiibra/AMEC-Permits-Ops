# Proposal production closure — final exact-state record

This is the final closure record for the Proposal / Opportunity / Client Tender
production-hardening epoch. It supersedes same-scope draft readiness claims; it
does not rewrite the historical PR41 evidence or the earlier Proposal seal.

## Governing identity

| Field | Exact value |
|---|---|
| Branch | `module/opportunity-proposal-client-tender` |
| PR | [#48](https://github.com/asamiibra/AMEC-Permits-Ops/pull/48) |
| Final source candidate | `ae9e736f62bcd5a06f4eccc3be3450c9570deca8` |
| Final source tree | `f1b1e555d7b3c138785dd90e28707e8b1e75b5c5` |
| Main at baseline | `594b313a15cc6ade3f0505de395a5817c6337268` |
| Main tree at baseline | `73d6781640bc774b577a6eb8e938868ef3fb83c3` |
| Merge-base | `594b313a15cc6ade3f0505de395a5817c6337268` |
| Branch relation before closure docs | `10 ahead / 0 behind` |
| PR41 accepted SHA | `dbd54c8e208e7347c959364b0bffd0f513eb81c7` — ancestor preserved |
| PR41 merge SHA | `e3af5e8d5c8abc996f1039aaae394bb734cc0193` — ancestor preserved |
| Alembic head | `proposal_production_hardening_v1` |
| Merge SHA | `NOT_MERGED` |
| Merge tree | `NOT_MERGED` |
| Final main SHA/tree | `NOT_MERGED` |

The source correction in the final candidate binds Proposal creation and
idempotency to the canonical current Client row and rejects a caller-supplied
or synthetic substitute. The exact negative/positive coverage is recorded in
`backend/tests/test_proposal_production_guards.py`.

## Gate record at the exact source candidate

| Gate | Result | Evidence / disposition |
|---|---|---|
| Canonical current Client truth | `PASS` | Source correction plus focused guard suite |
| Proposal P0 decisions unresolved | `PASS` — `0` | No Proposal-specific P0 unresolved decision found |
| Proposal P1 decisions unresolved | `FAIL` — `3` | `PROPOSAL_ACCEPT_REQUIRED_FIELDS`, `PROPOSAL_ACCEPT_AUTHORITY`, and `PROPOSAL_TO_CONTRACT_POLICY` remain proposed defaults and unapplied |
| Output format policy | `FAIL` | `PROPOSAL_OUTPUT_FORMAT_POLICY` remains an unapplied proposed default; PDF/DOCX owner decision is required |
| Checklist output policy | `FAIL` | `PROPOSAL_CHECKLIST_OUTPUT_POLICY` remains an unapplied proposed default |
| Canonical Proposal renderer | `FAIL` | Current implementation does not prove the governed canonical PDF/DOCX renderer |
| Proposal/checklist download and lineage | `FAIL` | Same-candidate managed-artifact write/readback and genuine final-format download were not executed |
| Service-specific eligibility authority | `FAIL` | Repository guards exist, but authoritative service-specific party/capability evidence was not executed in the target runtime |
| Commercial chain and adversarial boundaries | `FAIL` | Target-runtime commercial-chain, stale-revalidation, replay, and cross-service evidence were not executed as a production acceptance run |
| Protected negative-boundary suite | `PASS` | Exact-head repository regression and focused Proposal guard coverage passed |
| Backend regression | `PASS` | Exact-head PR #48 required check passed in release-critical-gates run `34841406152`, job `103967008804` |
| Frontend regression | `PASS` | Exact-head PR #48 required check passed in run `34841406152`, job `103967009075` |
| Migration head | `PASS` | Exact-head PR #48 required check passed in run `34841406152`, job `103967009015` |
| Policy/security | `PASS` | Exact-head PR #48 required check passed in run `34841406152`, job `103967009078` |
| Storage contract | `PASS` | Both exact-head Samba checks passed: runs `34841406193` / job `103967008937` and `34841401534` / job `103966993225` |
| Heavy source preflight | `PASS` | Canonical standalone `python3 scripts/phase5/source_preflight.py` rerun after the source correction: zero definite blockers; semantic mutation matrix `300/300` primary and independent rejects |
| Azure SQL migration/behavior/recovery | `FAIL` | Not executed against an approved isolated Azure SQL target with managed-identity access token and `DATABASE_MIGRATION_URL` |
| Entra authentication and authorization | `FAIL` | Required target-tenant, separate API/web IDs, scope, and real-user acceptance not supplied/executed |
| Managed artifact storage | `FAIL` | Canonical Azure Blob graph exists in source; real managed write/readback/retention was not executed |
| Qatar Source Intake Bridge / Synology | `FAIL` | Real bridge readback and source-of-record authority were not executed |
| Real production browser flow | `FAIL` | No authoritative Azure-backed browser acceptance run was executed |
| Multi-worker / multi-instance behavior | `FAIL` | No target-runtime concurrency acceptance run was executed |
| Independent exact-head review | `FAIL` | Clean review process was run, but no separate independent reviewer was available; therefore not proven |
| Owner UAT | `FAIL` | Owner decision closure and UAT were not supplied |
| Vercel backend deployment | `FAIL` — `NON_AUTHORITATIVE_PREVIEW_RUNTIME` | Deployment `4NDtKZ5noX4j4DnDgXQy94Bzojk7` failed, but repository configuration and deployment records identify Vercel as the PostgreSQL/synthetic preview path, not the Azure SQL production authority; it does not gate the Azure launch decision |

## 320-cell ledger

`docs/module-assurance/proposal-production-hardening-v1/17-320-verification-ledger.md`
contains exactly 320 records bound to the final source SHA/tree:

`PASS=194`, `FAIL=0`, `BLOCKED_EXTERNAL=126`, `NOT_APPLICABLE=0`.

The 126 external records remain blocked because the required external gates
were not executed. They are not promoted to PASS. Consequently this candidate
is not production-ready.

## Final production state

```text
FINAL_SOURCE_SHA=ae9e736f62bcd5a06f4eccc3be3450c9570deca8
FINAL_SOURCE_TREE=f1b1e555d7b3c138785dd90e28707e8b1e75b5c5
FINAL_BRANCH=module/opportunity-proposal-client-tender
PR_NUMBER=48
ALEMBIC_HEAD=proposal_production_hardening_v1
MERGE_SHA=NOT_MERGED
MERGE_TREE=NOT_MERGED
FINAL_MAIN_SHA=NOT_MERGED
FINAL_MAIN_TREE=NOT_MERGED
PRODUCTION_DEPLOYED=false
REAL_AMEC_DATA_AUTHORITY=false
PROTECTED_HUMAN_AUTHORITY_ASSUMED=false
PROPOSAL_PRODUCTION_READY=false
```

`FINAL_OPEN_BLOCKERS` is non-empty: three unapplied P1 Owner decisions; output
format and checklist policy decisions; canonical PDF/DOCX rendering and
managed-artifact lineage; Azure SQL managed-identity migration/behavior/
recovery; Entra; managed Blob; real Source Intake Bridge/Synology authority;
authoritative browser and multi-worker acceptance; independent exact-head
review; and Owner UAT.

No merge, deployment, real-data import, or human-authority assumption was made.

The optional workflow-aware preflight auditor was also attempted. Its single
failure is the repository auditor’s stale CLI-argument allowlist against the
existing Azure hardening workflow; it does not alter the standalone preflight
result or the production gate disposition above.
