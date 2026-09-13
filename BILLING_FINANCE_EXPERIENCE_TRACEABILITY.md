# Billing & Finance Experience v1 — Traceability

This feature branch implements the requested Billing / Invoice / Receivables /
Collection operating experience as a bounded layer over the accepted Billing
V10 canonical events. It does not reopen Billing V10, change financial
arithmetic, or merge to `main`.

Source authority: the user-provided request attachment
`/Users/ahmedsami/.codex/attachments/a31fdd56-38a5-45d4-985f-1e2f412b879d/pasted-text.txt`.
The request was supplied as one consolidated product and qualification brief;
the locators below use its numbered requirement sections and named contracts.

| Request locator | Acceptance intent | Implementation / evidence | Authority boundary |
| --- | --- | --- | --- |
| §§8–9, 87 | Three visible personas; Billing & Finance replaces four old lanes | `frontend/src/App.tsx`, `frontend/src/billing/BillingShell.tsx`, `frontend/src/billing/billing-experience.css` | Navigation is a server capability projection; hidden UI is not authority |
| §§10, 29–31 | Command Center with work-first queue and deterministic insights | `GET /api/billing/capabilities`, `GET /api/billing/command-center`, `frontend/src/billing/BillingCommandCenter.tsx` | `source_of_truth=CANONICAL_BILLING_EVENTS`; `system_insights_only=true`; no model call |
| §§12–18 | Billing Plans, milestones, invoice register, receivables, payments/credits, controls/reports | `GET /api/billing/plans`, `/milestones`, `/invoices`, `/receivables`, `/payments`, `/controls`, `/reports`; `frontend/src/billing/BillingRegisters.tsx` | Read models only; protected mutations remain canonical router policy |
| §§19–24 | Invoice detail preserves project/client/contract context and distinct status dimensions | `frontend/src/billing/InvoiceWorkspace.tsx`; enhanced `GET /api/billing/invoices/{id}` | Issue and accept remain separate human actions; communication, receivable, verification, and allocation do not collapse |
| §§25–28 | Project Finance, payment history, evidence, allocation and explicit reversal | `GET /api/billing/projects/{id}/payment-history`; payment projection and invoice workspace panels | Observed ≠ verified ≠ allocated; reversal is append-only and explicit |
| §§32–35 | Billing mode and service period are structured; monthly supervision fails closed without timezone policy | `billing_mode` fields, structured InvoiceRevision period fields, `GET /api/billing/supervision-queue` | No autonomous invoice creation, issuing, verification, allocation, or settlement |
| §§36–39 | Engineering / PM may request billable-stage review without invoice authority | `BillingReadinessRequest`, `POST /api/billing/readiness-requests`, `GET /api/billing/readiness-requests` | Append-only request; response explicitly reports `invoice_issue_authority=false` |
| §§40–42 | Safe invoice clone creates a separate draft and excludes lifecycle/payment state | `POST /api/billing/invoices/{id}/clone`; `Invoice.source_clone_id`; clone idempotency key | Draft-only clone; no silent issue, payment, allocation, or resolution copy |
| §§43–47 | Owner decisions are visible and unresolved values are not fabricated | Capability, command-center, controls and workspace policy cards | Five unresolved policies remain `OWNER_DECISION_REQUIRED`; no fabricated QAR conversion, EXP%, YTD, timezone, or numbering policy |
| §§48–55 | Content Library remains the evidence foundation | Existing `DocumentVersion` validation and Billing evidence references | No second evidence store introduced |
| §§56–63 | Typed frontend contracts and bounded failure states | `frontend/src/billing/billing-types.ts`, `billing-api.ts`, loading/error/empty states | New Billing surface contains no `any`; capability resolution fails closed |
| §§64–73 | Backend/schema qualification and one forward migration | `backend/migrations/versions/billing_finance_experience_v1.py`; model/router tests | One new migration from `17c6ebd99c4a`; canonical Billing authority/arithmetic unchanged |
| §§74–86 | Browser, frontend, accessibility and regression qualification | `frontend/tests/billing-experience.test.tsx`; package scripts; backend selected suite | Qualification evidence is recorded in the PR and final task report |

## Explicit non-goals

- No Billing V11, reclosure, or new Billing loop.
- No AI Billing skill, model invocation, canonical write authority, or protected
  action authority.
- No production deployment, real financial data, or public demo URL.
- No merge to `main` in this execution.

## Qualification commands

```text
PYTHONPATH=. APP_ENV=TEST SYNTHETIC_ONLY=true python -m pytest <selected backend qualification>
cd frontend && npm test -- --run
cd frontend && npm run build
cd frontend && npm run ui-conformance
```

The final task report records the exact command results, branch SHA, remote
parity, PR URL, migration head count, and any environment-gated browser result.

## Qualification recorded for this branch

- Backend selected Billing / contract / controls suite: **114 passed**.
- Frontend Vitest suite: **22 files, 116 tests passed**.
- Frontend TypeScript/Vite production build: **PASS**.
- Focused real-stack Billing browser rehearsal against the feature server and
  synthetic FastAPI/SQLite data: **1 passed**.
- Repository UI conformance crawl against the feature server: **312/312
  cases passed; final decision READY**. The existing universal route inventory
  contains 66 non-Billing material routes; the focused Billing rehearsal is the
  direct evidence for the new Billing route surface.
