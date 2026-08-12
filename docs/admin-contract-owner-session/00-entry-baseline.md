# Administration + Contract Owner Session — Entry Re-baseline

Date: 2026-08-12
Required result token: `ADMIN_CONTRACT_ENTRY_BASELINE_PASS`

## Repository and deployment baseline

| Check | Result |
|---|---|
| Branch | `main` |
| Local HEAD | `f07a46ccd065e9a51c9aac0b3905cc3c6fd400b9` |
| `origin/main` HEAD | `f07a46ccd065e9a51c9aac0b3905cc3c6fd400b9` |
| Entry working tree | Clean |
| Final working tree | Clean except the intentional Step 4/5 evidence and PostgreSQL test-isolation cleanup changes listed below |
| Deployed frontend | `https://amec-permits-ops.vercel.app` — HTTP 200 shell response |
| Deployed backend | `https://amec-permits-ops-backend.vercel.app` — `/health` HTTP 200 |
| Deployment health | `TEST`, synthetic-only, durable PostgreSQL, SQLite fallback inactive |
| Deployed Alembic state | `0034_admin_contract_owner_session` present |

The local baseline used a disposable PostgreSQL target at
`postgresql+psycopg://ahmedsami@localhost:5432/admin_contract_baseline_20260812`.
It was PostgreSQL 16.14, migrated to Alembic head
`0034_admin_contract_owner_session`, and dropped after verification.

Runtime versions recorded at entry:

- Python 3.14.2
- Node.js v24.13.0
- npm 11.6.2

## Source-of-record status

The test SOR is the repository’s explicit synthetic boundary: `MockSynologyAdapter`
over `mock-systems/synology`, with the canonical synthetic fixture and PostgreSQL
database. The deployed adapter health confirms synthetic Synology and
`real_synology: NOT_CONFIGURED`.

Real Synology connection details and production health verification were not
supplied. This remains an external AMEC IT go-live dependency and is not claimed
as passed by this baseline.

## Required inspection coverage

The entry inspection covered the following existing surfaces and seams:

- Administration routes/pages and owner readiness: `frontend/src/App.tsx`,
  `frontend/src/AdministrationOwner.tsx`, `backend/app/api/admin_owner_ready.py`.
- Contract list/detail and owner actions: `backend/app/api/contract_workspace_routers.py`,
  `backend/app/services/contract_workspace.py`, and the Contract routes in the
  frontend shell.
- Proposal → Contract handoff: accepted Proposal revision identity, immutable
  content hash, Contract creation, and lineage in `contract_workspace.py`.
- Contract → Project activation: explicit Owner activation, Project Code,
  Start Date, idempotency, audit, notification, and lineage behavior.
- Canonical Client/Contact, Project, Proposal, Contract, Document/DocumentVersion,
  Evidence, and template resolver seams, including Dashboard
  `ADMIN / CONTRACT_TEMPLATE` resolution.
- Definitions, tasks/My Work, issues, notifications, audit, lineage, and RBAC
  through the existing projection and persona APIs.
- Inputs & Go-Live and deployed runtime health, including the explicit real
  Synology exception.
- Current browser E2E suite and deployed frontend/backend shell/health probes.

The architecture protection record is in
`docs/admin-contract-owner-session/00-architecture-to-protect.md` and records
the no-duplicate-truth-store rule plus the distinct boundaries:
`Proposal Accept` ≠ `Contract authority/execution` ≠ `Project activation`.

## Verification results

| Verification | Result |
|---|---|
| Full backend suite against PostgreSQL | **PASS — 143 passed, 2 warnings** |
| Frontend tests | **PASS — 11 test files, 29 tests** |
| Frontend production build | **PASS**; Vite emitted only the existing large-chunk warning |
| Current browser E2E suite | **BASELINE RECORDED — 57 passed, 12 failed** |

The browser failures were recorded without widening this entry baseline into a
repair sprint. They cluster in existing proposal/issue browser checks: API
responses received as empty/non-JSON in several checks, a strict-text locator
collision in the Operating Guide check, and navigation/register checks that did
not reach their expected route or controls. The full UI-conformance crawl still
completed its 312-route/persona/viewport checks and wrote its conformance result.

During the PostgreSQL run, the existing Contract fixture cleanup was corrected to
delete dependent `NotificationEvent` and `AssistantHandoff` rows before shared
`WorkflowTask` rows. This is a test-isolation/FK-ordering repair exposed by
PostgreSQL; it does not create a new product primitive or alter runtime behavior.

## Entry decision

Step 4 architecture protection is recorded and Step 5 entry re-baseline is
complete. No Section 6 planning or later implementation/deployment scope is
claimed by this record.

Result: `ADMIN_CONTRACT_ENTRY_BASELINE_PASS`
