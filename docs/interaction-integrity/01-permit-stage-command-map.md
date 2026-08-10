# Permit stage command map

| Stage | Persisted source of state | Next action | Current disposition |
|---|---|---|---|
| 1 Project & Sources | `PermitApplication.workflow_stage`, confirmation evidence, `WorkflowTask` | Confirm project & sources | PASS: domain command and refresh persistence verified. |
| 2 Verify Data | `PermitApplication.workflow_stage`, documents/conflicts/readiness | Verify project data | Projection exists; command-level completion is not implemented in this change. |
| 3 Prepare Package | Package/readiness/revision records | Prepare package | Existing bounded workflow endpoints exist; whole-app browser command coverage remains incomplete. |
| 4 Municipality Preparation | assisted preparation and reconciliation records | Prepare municipality draft | Existing bounded workflow; no machine submission. |
| 5 Final Review & Human Submit | readiness, precheck, approval and handoff evidence | Record human confirmation | Human-only boundary is intentional; static checklist controls require audit. |
| 6 Authority Review | application status and monitoring history | Review returned comments | Read-only monitoring; returned-state routing exists. |
| 7 Comments & Corrections | findings, tasks and closure records | Resolve findings | Existing finding commands exist; cross-stage browser coverage remains incomplete. |
| 8 History / Close | audit, lineage, submission cycle | View history | Read-only timeline; closure automation is disabled by policy. |

Only Stage 1 is marked complete by this implementation. The UI must not infer completion of stages 2–8 from a click without a persisted command result.
