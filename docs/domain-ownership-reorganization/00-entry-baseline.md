# Entry baseline

Date: 2026-08-15

Repository: `/private/tmp/proposalops-ui-productionization`

This run is an information-architecture and presentation-ownership reconciliation. The entry inspection found that the canonical business APIs, entities, audit records, lineage, and RBAC already exist; the defect is that `AdministrationOwner.tsx` renders business work under `/admin`.

## Existing presentation surfaces

| Surface | Current route | Current implementation | Canonical data/API | Defect observed |
| --- | --- | --- | --- | --- |
| Admin landing | `/admin` | `AdministrationOwnerPage` → `Landing` | `/api/admin/summary`, `/api/admin/contracts`, `/api/billing/invoices` | Presents Contract and Invoice registers as Admin work |
| Admin Contract register | `/admin/contracts` | `OperationalContracts` | `/api/admin/contracts` | Business register is owned by Admin presentation |
| Admin Contract workspace | `/admin/contracts/:id` | `ContractWorkbench` | `/api/admin/contracts/:id` and existing contract workspace actions | Commercial terms, client inputs, deliverables, activation, and billing context are under Admin |
| Admin Invoice register | `/admin/invoices` | `BillingInvoicePage` | `/api/billing/invoices` | Finance work is reachable through an Admin presentation |
| Contract/Proposal register | `/proposals-contracts?view=contracts` | `ProposalsContractsPage` | `/api/proposals-main` | Existing business-facing Contract register and Proposal lineage |
| Finance | `/billing` | `BillingInvoicePage` | `/api/billing/*` | Existing canonical billing/invoice workspace |
| Home finance panel | `/home` | `HomeCommandCenter` | `/api/billing/summary`, `/api/billing/invoices` | Existing contextual Finance entry |
| Admin setup | `/admin/*` | `SetupControls` and configuration sections | `/api/admin/*` | Legitimate system configuration mixed with business work |

## Canonical protections observed

- Contract creation is controlled by the existing accepted-Proposal prerequisite and backend capability checks.
- Contract acceptance does not automatically activate a Project.
- Project Activation is an explicit audited action at `/api/admin/contracts/{contract_id}/activate-project`.
- Billing Plan, Billing Milestone, Invoice, Receivable, payment verification, allocation, and follow-up are served by `/api/billing/*`.
- Proposal → Contract and Contract → Project/Permit context are already represented by canonical IDs and read models.
- Existing frontend and backend tests exercise the legacy `/api/admin/contracts/*` paths; those API paths remain unchanged in this run.

## Entry change boundary

Expected changes: frontend route mapping, page composition, user-facing copy, contextual deep-link normalization, browser tests, and documentation.

Expected unchanged: domain models, services, database schema, Alembic migrations, API mutation semantics, audit events, IDs, predicates, and role capability guards.
