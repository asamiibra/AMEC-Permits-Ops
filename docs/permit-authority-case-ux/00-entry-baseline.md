# Permit / Authority Case UX — Entry Baseline

Date: 2026-08-13
Prompt: Permit / Authority Case UX v1.0

## Repository

- Branch: `main`
- HEAD: `3bac43e65bdff3eba71f8d9963e3d9238d30c8b4`
- `origin/main`: `3bac43e65bdff3eba71f8d9963e3d9238d30c8b4`
- Working tree: clean at entry
- Alembic head: `0044_preparation_submission_loop`

## Required dependency evidence

- Preparation + Submission: `PREPARATION_SUBMISSION_LOOP_CODE_FROZEN`
- Preparation deployment provenance: `PREPARATION_SUBMISSION_LOOP_DEPLOYMENT_PROVENANCE_BLOCKED_EXTERNAL`
- Engineering: `ENGINEERING_APPROVED_DESIGN_BASELINE_CODE_FROZEN`
- Engineering dependencies: `PREPARATION_SUBMISSION_ENGINEERING_DEPENDENCIES_READY`
- UX dependency status: locally proven from the executable API, migration, test, and frontend evidence; exact deployment provenance remains externally blocked.

## Baseline evidence inspected

- Preparation + Submission closure: `docs/preparation-submission-loop/27-final-result.md`
- Preparation + Submission regression: `docs/preparation-submission-loop/24-regression-proof.md`
- Engineering closure: `docs/engineering-approved-design-baseline/23-post-implementation-closure.md`
- BD v2 and Dashboard V2 evidence directories are present and previously closed.

## Existing UX inventory

- Existing Permit navigation resolves `/permit`, `/permits`, and `/proposals-contracts` to the legacy Proposal/Contract surface.
- Existing `PermitWorkspacePage` is a stage-based legacy workspace over Project/Application records.
- Existing Authority Case workspace is available at `/authority-cases` and is the bounded Preparation + Submission read model.
- Existing canonical APIs already expose Project, Regulatory Core, Requirement Engine, Form Automation, Engineering baseline, findings, history, My Work, Issues, Notifications, Audit, and Lineage seams.

## Boundary

This work adds Owner-facing Permit / Authority Case projections and query seams over the existing canonical engine. It does not create Permit-local truth tables, rebuild the regulatory engine, mutate approved Engineering revisions, automate portals, add billing, or create construction/completion workflows.
