# Billing & Finance Experience — PR #46 closure traceability

This document records the implementation against the governing Owner Sources
12–16, later same-scope Owner-resolved G0.13 / G0.14 / G0.16 decisions, cross-
source Sources 6 / 7 / 9 / 11 where applicable, and the locked ProposalOps
Intelligence Architecture v1. The original product brief is treated as an
execution prompt, not as the governing authority.

The feature remains a bounded operating layer over accepted Billing V10
canonical events. It does not reopen V10, create Billing V11, change accepted
financial arithmetic, introduce ERP journal integration, or merge to `main`.

| Governing evidence / family | Requirement | Implementation path / API | Positive and negative evidence | Authority boundary |
| --- | --- | --- | --- | --- |
| Owner Sources 12 / 16; G0.13 / G0.14 / G0.16 | Billing policies are resolved within existing persona and scoped-capability governance | `backend/app/services/owner_decisions.py`; `RESOLVED_OWNER_POLICIES`; `/api/billing/capabilities`; `/api/billing/controls` | Resolved policy projection; runtime readiness remains separate; job-title-only and missing-scope paths remain denied | No Finance or Secretary persona; mutations remain server-enforced |
| Source 13 standard Invoice policy | Accepted Contract authority, one office-wide sequence, rollover without reset, `INV-AMEC-{year}-{project}-{sequence}`, governed `INV-Form.docx`, human signer | `_allocate_invoice_ref`, Issue precheck, `InvoiceIssueEvent`, `RenderedArtifact` | Issue derives reference server-side; duplicate/idempotency constraints; no client-side next reference | No production numbering readiness is claimed until reconciliation gate passes |
| Sources 12 / 16 | Payment observed, verified, allocated, and reversed are distinct | `InvoicePaymentAllocation.billing_milestone_id`; payment verify/allocate/reverse routes; Payment Workspace | Unverified allocation denied; multi-milestone allocation without explicit milestone denied; reversal preserves events | AI cannot verify, allocate, reverse, or settle |
| Source 12 milestone arithmetic | Actual Collected is only the sum of active allocations explicitly attributed to the milestone | `_milestone_projection`; allocation validation; closure migration | Historical unlinked allocations remain `UNATTRIBUTED_HISTORICAL_ALLOCATION` and are excluded from milestone Actual Collected | No invoice-level inference or proportional split |
| Sources 12 / 13 | Plan, revision, milestone, evidence, readiness, supervision, and contractual-term lineage | `BillingPlanWorkspace`; `/api/billing/plans/{id}`; readiness and eligibility routes; supervision queue | Requester boundary is explicit; contract payment-term lineage is validated | Readiness never grants Issue or payment authority; monthly recurrence creates work only |
| Source 16 artifact/evidence family | Issued PDF, references, approvals, delivery, acknowledgment, and Content Library DocumentVersion lineage | `InvoiceWorkspace`; invoice detail/precheck/download routes; existing evidence validation | Accept/Issue precheck gates; issued artifact metadata shown; delivery ≠ acknowledgment ≠ approval | No external send is claimed; canonical artifact is PDF |
| Sources 12 / 16 | Payment entry, evidence completeness, allocation splits, unallocated credit, reversal, follow-up, non-cash resolution | `PaymentWorkspace`; payment routes and projections | Method-specific evidence gates; resolution is not Paid; follow-up does not change financial state | Protected actions require scoped human capability |
| Sources 12 / 16 | Project Finance and calendar-year YTD projections | `ProjectFinanceWorkspace`; `/api/billing/projects/{id}/financial-projection`; versioned FX/Expected EXP records | QAR is direct; non-QAR without approved FX is `FX_RATE_RECORD_REQUIRED`; YTD is `CONFIGURATION_REQUIRED` without governed business-local timezone | No guessed FX, EXP formula, timezone, or YTD amount |
| Locked Intelligence Architecture v1 | Shared intelligence, module review, human authority, canonical truth | Typed `WorkItem.target`; deterministic `SYSTEM_INSIGHT` queue; Billing UI contract fields reserved for future `AI_WORK_PRODUCT` | No Billing model invocation; no Billing-local AI table/gateway/queue | `AI_CANONICAL_WRITE_AUTHORITY=ZERO`; `AI_PROTECTED_ACTION_AUTHORITY=ZERO` |
| Sources 6 / 7 / 9 / 11; route contract | Every visible Billing destination is a functioning context workspace | `/billing/plans/:id`, `/billing/payments/:id`, `/billing/projects/:id`; typed shell routing | Detail routes no longer fall back to registers; technical IDs remain metadata | UI visibility never replaces backend authorization |

## Policy truth versus runtime facts

The following policies are resolved and no longer appear as Owner decisions
required:

- Finance/Secretary mapping: `SCOPED_CAPABILITY_ASSIGNMENT_WITHIN_EXISTING_PERSONA_MODEL`
- Invoice numbering: `CONTINUE_RECONCILED_HISTORICAL_AMEC_SEQUENCE_AND_FORMAT`
- Non-QAR conversion: `GOVERNED_OWNER_EDITABLE_FX_RATE_RECORD`
- Expected EXP%: `OWNER_APPROVED_EDITABLE_PROJECT_FINANCE_FIELD`
- YTD boundary: `CALENDAR_YEAR`

Runtime data may still be unavailable. The UI reports this explicitly, for
example `PRODUCTION_NUMBERING_READY=false`, `FX_RATE_RECORD_REQUIRED`,
`NOT_SET`, or `CONFIGURATION_REQUIRED`; these states do not relabel an
approved policy as unresolved.

## Schema and qualification

- The accepted closure migration `billing_finance_experience_closure_v1` remains
  intact, followed by the persisted assignment migration
  `scoped_finance_capability_assignment_v1` and the forward production-
  hardening migration `billing_finance_production_hardening_v1`, followed by
  reusable governed signatory authority migrations
  `governed_signatory_authority_v1` and
  `governed_signatory_authority_governance_v2`. These migrations bind financial-account
  and signer evidence to canonical scope; none rewrites V10 or PR #46
  historical migrations.
- Synthetic data only; no production database, credentials, bank account,
  client payment, cheque, receipt, or external AI invocation.
- Full qualification must be rerun after closure changes; prior PR #46 counts
  are historical evidence and are not reused as closure results.

Residual implementation evidence from this run:

- `PaymentWorkspace` now carries an explicit selected invoice target and the
  regression test proves the second eligible invoice is sent in the allocation
  request; it no longer posts the first eligible invoice unconditionally.
- Billing Plan review carries an explicit selected milestone, and Billing
  evidence selectors resolve Content Library current `DocumentVersion` records
  with an evidence-open route instead of asking operators to type UUIDs.
- Payment record, delivery, acknowledgment, approval, follow-up, and non-cash
  resolution controls are exposed as separate human actions in the Billing UI;
  backend method-specific evidence gates remain authoritative.
- Business-local timezone is deployment configuration. Reports fail closed when
  it is blank or invalid and expose `CONFIGURATION_REQUIRED`; no guessed
  timezone or YTD value is emitted.
- Historical exact-head qualification at implementation SHA
  `69e57cd0d47e8c6f192e34be6fa0a4e52a1dc809` (tree
  `d7a7daf19d33b880bf7ea553c71ff2c41e6a33c9`) completed with focused backend
  finance/authority tests `51 passed, 1 warning`; frontend Vitest `117/117`
  passed; frontend production build passed; Python compile passed; and Alembic
  reported one head. The universal UI crawl completed all `312/312` cases over
  66 routes and ended `PROPOSALOPS_UI_CONFORMANCE_READY` with all 28 checks
  true. This remains historical evidence only.
- Required exact-head GitHub Actions passed: `backend-regression`,
  `frontend-regression`, `migration-head`, `policy-and-security`, and both
  `samba-contract` contexts. The backend Vercel preview remains
  environment-blocked because `DATABASE_URL` is unavailable to
  `scripts/vercel_data_bootstrap.py`; no credentials were added.

## Terminal closure audit disposition

## Production-hardening closure pass

The adversarial pre-implementation ledger is
`artifacts/production/pr46_production_hardening_validation_ledger.json`.
It contains 24 closure propositions × 8 evidence lenses = 192 falsifiable
checks and 30 hostile shortcut attacks, for an exact analytical total of 222
(the brief's stated minimum of 208 is arithmetically lower than its own
192 + 30 components).

The code closure pass adds the following controls on this existing PR branch:

- Billing GET/HEAD/direct artifact paths require the existing global role,
  active persisted `BILLING_VIEW`, and canonical Project/Client/Contract scope;
  list, report, command-center, evidence, and aggregate queries are filtered
  in SQL from the effective assignment scope.
- Target office scope is derived from canonical Project/Contract lineage;
  actor office is not substituted for a target resource. Assignment rows have
  database checks for non-empty scope, valid effective intervals, and allowed
  status values, with service validation for project/client consistency and
  duplicate active grants.
- Production header authentication is rejected outside DEV/TEST, payload and
  `X-Dev-Actor` values are not authoritative in production, and Issue stores
  Source 13 signer identity/capacity/authority evidence in its immutable source
  snapshot. Issue and Controls consume the same canonical Source 12 numbering
  decision-key contract.
- Read scope algebra is explicit: persisted assignment rows are OR-ed, while
  office/client/project dimensions inside one row are AND-ed. Client scope is
  never expanded through every project or contract for that client, preventing
  same-project cross-client leakage.
- Source 13 production Issue resolves an active effective-dated governed
  signatory authority record, canonical office/legal entity, required authority
  evidence, and a project-linked signed/stamped invoice `DocumentVersion`;
  caller-supplied signer strings cannot create authority.

The earlier exact-head browser rehearsal remains classified as 53/64 passed,
10 failed, and 1 not run; its failures are environment/legacy-contract cases
(SQLite-vs-Postgres assertions, historical dashboard/contract expectations,
Administration cleanup timeout, and one strict duplicate-text assertion).
After the current repairs, a fresh isolated synthetic database containing an
issued Invoice passed the three applicable Billing real-stack checks: both
Billing detail-route checks and the project-safe Invoice/communication-history
journey. The prior 312/312 crawl remains historical only.

Post-hardening qualification at code head
`d33d7b95a7604ef3ca46e898da2ac4455019c776` (tree
`fdca32d8222835025df6263a42fc0de70ca289e0`) completed the exact Billing,
authorization, migration, and SQL-port contract set with `71 passed, 1
skipped, 1 warning`, frontend Vitest with `117/117`, frontend production
build, Python compile, and the single Alembic head check. The committed
Alembic sole head is `governed_signatory_authority_governance_v2`.
Deterministic synthetic real-stack Billing acceptance passed `3/3` with an
issued Invoice, project-safe context, communication history, and route-
isolation negative checks. The broad repository run was not promoted to a
pass: it was interrupted during the unrelated 300-case Phase 5 mutation
subprocess after `599 passed, 11 skipped`; no failure had surfaced. SQL
Server/Azure runtime evidence was not available in this isolated synthetic
environment and remains external.

The final governed signatory provisioning lifecycle is Owner-authenticated and
history-retaining: create enters `PENDING_APPROVAL`, a distinct Owner approves,
and Owner-only revoke/supersede operations retain server-owned actor/timestamp
audit fields. Forged lifecycle fields are rejected, self-approval is denied,
and canonical active User, office/entity, and authority evidence are required.
The exact lifecycle evidence token is
`SIGNATORY_AUTHORITY_PROVISIONING_GOVERNANCE=PASS`.

The scoped Finance authorization seam is implemented on the existing accepted
branch. `ScopedCapabilityAssignment` is a persisted generic assignment bound to
the actual User, exact capability code, and one or more explicit office/client/
Project scopes, with effective dates, provenance, and revocation state. The
server resolver requires an active persisted assignment, exact context match,
the existing global Role constraint, and returns the assignment ID used for
mutation audit. No authority is inferred from job title, display name, or
global persona; Finance and Secretary remain operational functions rather than
new global personas.

All protected Billing POST mutation routes now resolve authorization from the
canonical loaded Contract, Client, Project, Payment, or office context before
writing. `/api/billing/capabilities` projects only effective scoped grants for
the requested canonical context. Owner Administration exposes assignment list,
create, and explicit revoke operations; revocation retains history. Synthetic
seed data contains explicit office-scoped grants solely for the seeded demo
users. Live route tests prove no-grant denial, wrong-capability denial,
wrong-project denial, exact project-scope success, and auditable revoke.

The migrations `scoped_finance_capability_assignment_v1`,
`billing_finance_production_hardening_v1`, and
`governed_signatory_authority_v1` and
`governed_signatory_authority_governance_v2` follow
`billing_finance_experience_closure_v1`; `governed_signatory_authority_governance_v2`
is the sole repository head. The existing universal UI closure was not
reopened, and no Vercel repair or merge to `main` was performed.

`PR46_BILLING_PRODUCTION_HARDENING_CODE_CLOSED`
`SIGNATORY_AUTHORITY_PROVISIONING_GOVERNANCE=PASS`
`BILLING_READ_SCOPE_ALGEBRA=PASS`
`SOURCE13_SIGNER_USE_TIME_AUTHORITY=PASS`
`BILLING_BROWSER_ACCEPTANCE=PASS`
`BILLING_PRODUCTION_READY=false`
`BILLING_SQLSERVER_RUNTIME=EXTERNAL_EVIDENCE_REQUIRED`
`BILLING_INDEPENDENT_COLD_REVIEW=NOT_PROVEN`
`EXACT_HEAD_REQUIRED_CI=PASS`
`POST_IMPLEMENTATION_LEDGER=PASS`
`PR46_EVIDENCE_CURRENTNESS=PASS`
`PR46_BILLING_BRANCH_ACCEPTED=false`
`PR46_MERGE_AUTHORITY=NOT_GRANTED`
`REAL_DATA_ACCEPTANCE=EXTERNAL_REQUIRED`
`UAT=EXTERNAL_REQUIRED`
`G9=EXTERNAL_REQUIRED`

No Billing V10 reopening, Billing V11 work, merge, deployment, production or
preproduction access, Azure/Entra/DNS change, real financial-data use, or
protected-human finance action occurred.

## Explicit non-goals

- No new branch, replacement PR, Billing V11, or merge to `main`.
- No accounting ERP/journal integration in this release.
- No Billing-specific AI runtime or fake AI work product.
- No production numbering reservation or public preview credential changes.
