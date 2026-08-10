# Whole-app control inventory

Audit date: 2026-08-09. Scope: the current React/Vite client, FastAPI API, SQLite/PostgreSQL model layer, and the seeded real-stack rehearsal.

| Surface | Material controls | Classification | Runtime disposition |
|---|---|---|---|
| `/work` | Work cards, reviews, issue links, notification links | `NAVIGATION` | Routes are live; the destination commands are owned by their target screens. |
| `/proposals-contracts` | New Proposal, source drawers, KPI filters, Proceed, Contract, Permit | `FILE_INGESTION`, `QUERY_FILTER`, `DOMAIN_COMMAND`, `NAVIGATION` | Existing proposal/contract tests pass; source upload is read-back verified. |
| Proposal/Contract detail | Promote, Proceed, Ready for BD, Proposal → Contract, Contract → Permit | `DOMAIN_COMMAND` | Existing backend and browser coverage pass locally. |
| `/permits/:id/project-and-sources` | Confirm project & sources | `DOMAIN_COMMAND` | Implemented and verified end-to-end in this task. |
| Permit stage stepper | Select stages and deep links | `NAVIGATION` | Local navigation only; it does not mutate business state. |
| Verify / package / municipality / review stages | Evidence, readiness, assisted preparation, human handoff buttons | `BACKEND_READ`, `NAVIGATION`, `ACKNOWLEDGEMENT` | Read/navigation surfaces are wired, but several stage summaries still need command-level audit. |
| `/issues` and `/notifications` | Persona filter, open record, notification history | `BACKEND_READ`, `QUERY_FILTER`, `NAVIGATION` | Persona visibility tests pass; hidden-error and empty-state audit remains open. |
| Administration | Configuration, diagnostics, evidence and setup links | `NAVIGATION`, `DISABLED_BY_POLICY` | Safe boundaries are visible; no portal-write action is exposed. |

The inventory is deliberately classification-first. A button is not considered a domain command merely because it changes route or local React state. The machine-readable inventory is [control-inventory.json](../../artifacts/interaction-integrity/control-inventory.json). The complete unwired/no-op proof scan is still open.

## Stage 1 control contract

`Confirm project & sources` is now a real command:

`NextActionCard → POST /api/projects/{project_id}/confirm-project-sources → confirm_project_sources() → PermitApplication.workflow_stage + confirmation evidence → WorkflowTask completion + VERIFY_PROJECT_DATA task + audit + notification → refreshed project projection → Verify stage`.

The command validates the project reference, role capability, application ownership, and active Synology/Excel/Municipality links. A repeat call is idempotent and does not duplicate the verification task.
