# Downstream Permit Stages

## ROUTE / PERSONAS

Eight stage families under `/permits/:projectId/*` and `/proposals-contracts/:projectId/*`; Owner, Business Development, Engineering.

## DESIGN CONTRACT

Project & Sources → Verify Data → Prepare Package → Municipality Preparation → Final Review & Human Submit → Authority Review → Comments & Corrections → History / Close.

## DESIGN PASS / FUNCTION PASS

PASS locally. The workspace explicitly shows `Current stage` and `Viewing`; source rows use semantic labels; all three personas pass role-matrix checks.

## DATA / ROLE / INTEGRATION

Current stage and next action are backend-derived. Engineering owns technical actions; non-Engineering personas receive context-only controls. Municipality remains simulated/read-only and final submission remains human.

## ERROR / LOADING / EMPTY / MOBILE / ACCESSIBILITY

API failure states are covered by the universal harness; local overflow is zero. The old Arabic/global-language real-stack assertions are outside current product behavior.

## CROSS-PAGE / DEFECTS / EVIDENCE

Permit language is classified as legitimate downstream terminology. Evidence: `screenshots/S07-*` through `S14-*`, `role-matrix-result.json`, and `field-authority-map.json`.
