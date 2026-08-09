# PermitOps current-state entry audit

Date: 2026-08-08  
Environment: synthetic development/prototype only

## Executive finding

The normal landing page is the workflow-first **My Work** surface in `frontend/src/WorkflowFirst.tsx`. The application is a React/Vite frontend over a FastAPI/SQLAlchemy modular monolith. Permit core capabilities are present as synthetic runtime paths and executable tests, but no production authority connection or machine final submission is authorized.

The explainer therefore uses `IMPLEMENTED` only for the deterministic My Work projection and `IMPLEMENTED_PROTOTYPE` for synthetic/runtime-backed permit capabilities. Stage 1 v2.6 expansion entities and assistant queue runtime are shown as bounded prototype/foundation scope, not as a complete ERP/CRM/finance system.

## Current UI inventory

| Surface | Runtime evidence | Current classification |
|---|---|---|
| Application shell / role selector / environment banner | `frontend/src/App.tsx`, `frontend/src/styles.css` | Implemented |
| My Work | `frontend/src/WorkflowFirst.tsx`, `frontend/tests/workflow-first.test.tsx` | Implemented |
| Permits / permit workspace | `frontend/src/WorkflowFirst.tsx` | Implemented in synthetic prototype |
| Reviews / Issues / Notifications | `frontend/src/WorkflowFirst.tsx` | Implemented in synthetic prototype |
| Project & Sources / Verify Data | `frontend/src/WorkflowFirst.tsx`, Week 2 APIs | Implemented in synthetic prototype |
| Prepare Package / Municipality Preparation | `frontend/src/Week45.tsx` | Implemented in synthetic prototype |
| Attachments & grids | `frontend/src/Week9.tsx` | Implemented in synthetic prototype |
| Final Review / Handoff | `frontend/src/WorkflowFirst.tsx`, Week 10–12 APIs | Implemented in synthetic prototype; human submit only |
| Authority Review / Comments & Corrections | `frontend/src/WorkflowFirst.tsx`, `frontend/src/Week7.tsx` | Implemented in synthetic prototype |
| History / Lineage / Validity | `frontend/src/Week8.tsx` and audit projections | Implemented in synthetic prototype |
| Administration / control diagnostics | `frontend/src/WorkflowFirst.tsx`, `frontend/src/ReconciliationControls.tsx` | Admin-only prototype |
| About / Help entry | New `/about` route, sidebar affordance, My Work onboarding card | Implemented |
| i18n / RTL | No global i18n framework found; reusable `LtrTerm` and page-local `lang`/`dir` added | Implemented for explainer; broader app remains mixed |

## Current backend/domain inventory

Evidence was verified from the model, service, router, and acceptance-test layers. The permit core includes Project, Document/DocumentVersion, FieldObservation, VerifiedAssertion, Conflict, field authority/configuration, requirements/dependencies, validity, drawing controls, Package/manifest, rendered forms, Excel projection, approvals, preparation revisions, portal snapshots/reconciliation, precheck capture, Findings, WorkflowTask, NotificationEvent, SubmissionHandoff, SubmissionCycle/SubmittedSnapshot, MonitoringRun, ExternalMutation, LineageEdge, MaterialChangeEvent, and audit records.

Primary evidence locations:

- `backend/app/models/entities.py`
- `backend/app/models/week2_entities.py` through `backend/app/models/week14_entities.py`
- `backend/app/models/expansion_entities.py`
- `backend/app/api/week2_routers.py`, `week45_routers.py`, `week7_routers.py`, `week8_routers.py`, `week9_routers.py`, `week10_routers.py`, `week11_routers.py`, `week12_routers.py`, `week13_routers.py`, `week14_routers.py`
- `backend/app/api/expansion_routers.py`, `backend/app/expansion/unified.py`
- `backend/app/services/document_intelligence.py`, `week45.py`, `week7.py`, `week8.py`, `week10.py`, `week11.py`, `week12.py`, `week13.py`, `week14.py`

## Expansion runtime

Opportunity/RFQ, quotation, client acceptance, contract, checklist, reference/project administration, project-status Excel, communication drafts, engineering/finance/handover entities, and four-assistant shared context are present in the expansion foundation/runtime. The repository README and expansion evidence explicitly stop before complete quotation release, contract execution, engineering AI approval, invoice workflow, handover release, real communication, accounting writes, authority writes, and machine final submission. These are therefore not counted as current permit-MVP implementations.

## Evidence state

- Migration head: `0021_e7_unified_task_context.py` (migration directory; verify with the target database before release).
- Canonical synthetic fixture: `PermitOps_Synthetic_MVP_Dataset_v1`, successor `1.1.0`, manifest hash documented in `README.md` and exposed by `/api/reconciliation/fixture`.
- PostgreSQL target validation: documented as PASS for the reconciled synthetic track; Docker is convenience infrastructure, not the product gate.
- SQLite regression path: present in `backend/tests` and Makefile workflows.
- Golden Path v1/v2, reconciliation, expansion, monitoring, recovery, and acceptance rehearsal scripts are present under `backend/scripts` and `Makefile`.
- Frontend build: `npm run build` PASS on 2026-08-08.
- Safety counters: `artifacts/production/g10-zero-tolerance-counters.json` all zero for the synthetic repository run; `g10-formal-decision.json` says G10 not run and production mode is not authorized.

## Candidate feature status rule

The page catalog in `frontend/src/AboutPermitOps.tsx` is the user-facing status source. Only `IMPLEMENTED` and `IMPLEMENTED_PROTOTYPE` contribute to the displayed capability count. Every visible feature has an evidence list; FOUNDATION_ONLY, PLANNED_PENDING_SCOPE, and EXCLUDED entries are never counted as current MVP capabilities.

