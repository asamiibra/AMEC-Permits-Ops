# Dashboard V1 / V2 Split — Final Result

## Overall

The current codebase now exposes two intentionally different Dashboard experiences over one canonical master-content foundation. `/dashboard` is the restored legacy V1 surface; `/dashboard-v2` is the Wave A governance surface and the future destination for B/C.

## Repository

- Starting SHA: `f694a145dc927426d022e50f7e86348fa9ef879d`
- Final SHA: `5e5fb43b57c8d0fb92f5e7fe9c3124b1ad341512`
- Remote SHA: `5e5fb43b57c8d0fb92f5e7fe9c3124b1ad341512`
- Alembic head: `0036_dashboard_forms_governance_wave_a`
- Working tree: required clean at close

## Dashboard V1

V1 remains `/dashboard`, with the Forms, Reports, Engineering Works, and Definitions libraries; baseline filters, Version column, legacy detail presentation, shared New/Edit/History actions, and legacy Inputs behavior. Wave A governance filters, badges, and detail sections are absent from normal V1 UX. Shared security, restricted-reference controls, immutable history, and backend RBAC remain active.

## Dashboard V2

V2 is `/dashboard-v2`, linked from `/work` for Owner roles. It contains the same four libraries and the existing Wave A governance UX: ownership, artifact kind, source/provenance metadata, currentness, sensitivity/restricted-reference state, quality flags, source sections, readiness, advanced filters, versions/history, and governance Inputs & Go-Live. V2 route access and governance writes use the existing Owner policy and shared audit/security services.

## Shared canonical data

Both surfaces use the same `MasterContentItem`, `Document`, `DocumentVersion`, bindings, resolver, audit, and material-propagation truth. No duplicate records, version models, Dashboard-version column, or data-copy migration was introduced. Migration 0036 remains the head.

## Downstream and deferred scope

Proposal Template, Proposal Checklist, and Contract Template resolver regression passed. Wave B and Wave C remain explicitly deferred until `ExternalBody`, `ServiceType`, `Jurisdiction`, `RequirementPolicyVersion`, `TechnicalRuleSetVersion`, and a canonical Form Automation execution foundation exist. No Dashboard-local substitutes were created.

## Tests and external status

Backend: 150 passed, 1 skipped. Frontend: 32 passed. Build: passed. Focused real-stack browser: 3 passed. Disposable data and generated fixtures were cleaned. Exact production deployment SHA provenance is external and unavailable. Real Synology verification is external and unavailable.

Final tokens:

`DASHBOARD_V1_RESTORED_V2_WAVE_A_CODE_FROZEN`

`DASHBOARD_V1_V2_DEPLOYMENT_PROVENANCE_BLOCKED_EXTERNAL`

`REAL_SYNOLOGY_VERIFICATION_BLOCKED_EXTERNAL`
