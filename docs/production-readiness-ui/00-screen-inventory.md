# PermitOps production-readiness screen inventory

The authoritative inventory is `frontend/src/ProductionReadiness.tsx`. `screenReadinessRegistry` is the single screen-level source of truth; `SCREEN_ROUTE_INVENTORY` is its export for audits and tooling.

Coverage includes the seven business navigation screens, About, the eight permit workspace stages S07–S14, Administration, the implemented admin/legacy evidence routes, and the bounded expansion screens. Every rendered route is assigned a `screenId`, purpose, runtime inputs, runtime outputs, customer requirement IDs, implementation status, and role context.

The current UI exposes the shared `ReadinessDrawer` in the application top bar. `/admin/go-live-readiness` exposes the consolidated requirement view and CSV export.

## Canonical stage map

| Screen IDs | Stage | Route pattern |
|---|---|---|
| S07–S14 | Project & Sources → Verify Data → Prepare Package → Municipality Preparation → Final Review & Human Submit → Authority Review → Comments & Corrections → History | `/permits/:projectId/<stage>` |

## Safety boundary

The inventory describes what the current prototype uses and produces; it does not grant authority. Municipality submission, professional engineering decisions, finance, contract, and production communication remain human-controlled or explicitly bounded while their setup items are configured and tested.
