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

- One forward migration was added from `billing_finance_experience_v1`:
  `billing_finance_experience_closure_v1`.
- It adds milestone attribution to allocations and versioned FX / Expected EXP
  persistence. It does not rewrite V10 or PR #46 historical migrations.
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
- Exact-head qualification at implementation SHA
  `69e57cd0d47e8c6f192e34be6fa0a4e52a1dc809` (tree
  `d7a7daf19d33b880bf7ea553c71ff2c41e6a33c9`) completed with focused backend
  finance/authority tests `51 passed, 1 warning`; frontend Vitest `117/117`
  passed; frontend production build passed; Python compile passed; and Alembic
  reported one head. The universal UI crawl completed all `312/312` cases over
  66 routes and ended `PROPOSALOPS_UI_CONFORMANCE_READY` with all 28 checks
  true. A prior single `NOT_READY` replay was not reproducible on the repeat
  exact-head crawl and is recorded as a harness flake, not a product repair.
- Required exact-head GitHub Actions passed: `backend-regression`,
  `frontend-regression`, `migration-head`, `policy-and-security`, and both
  `samba-contract` contexts. The backend Vercel preview remains
  environment-blocked because `DATABASE_URL` is unavailable to
  `scripts/vercel_data_bootstrap.py`; no credentials were added.

## Terminal closure audit disposition

`FINAL_RESULT=PR46_BILLING_FINANCE_EXPERIENCE_CLOSURE_BLOCKED`

The remaining blocker is the live Billing mutation authorization seam. The
Billing router gates mutations through global `Role` sets and `_role(...)`;
`AuthenticatedPrincipal` carries the global role but no capability-assignment,
project-scope, or client-scope authority; and the tested `ScopedCapability`
helper in `source12_finance_controls.py` is side-effect-free and is not wired
into the Billing dependency or a persisted assignment/resolver. The repository
does not define a fourth global Finance/Secretary persona, and that invariant
is preserved. Therefore scoped Finance capability authorization is not proven
for live mutations and role-only privilege escalation remains unresolved.

The helper-level negative tests still pass for wrong project, job-title-only,
Finance/Secretary persona, and engineering billable-stage boundaries. They do
not prove live route enforcement, so this is a real closure blocker rather than
a failed UI or arithmetic result. Payment recorded/verified/allocated/reversed
and cross-project/client checks remain distinct and passing.

No Billing V10 reopening, Billing V11 work, merge, deployment, production or
preproduction access, Azure/Entra/DNS change, real financial-data use, or
protected-human finance action occurred.

## Explicit non-goals

- No new branch, replacement PR, Billing V11, or merge to `main`.
- No accounting ERP/journal integration in this release.
- No Billing-specific AI runtime or fake AI work product.
- No production numbering reservation or public preview credential changes.
