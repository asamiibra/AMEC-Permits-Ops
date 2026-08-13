# Engineering / Approved Design Baseline — Entry Baseline

Date: 2026-08-13
Execution mode: IMPLEMENT + RECONCILE + VERIFY + REPAIR CLOSURE DEFECTS + FREEZE

## Entry authority

The BD / Proposal Forms-Driven v2 handoff is accepted from the repository evidence at `docs/bd-proposal-forms-driven-v2/17-final-result.md`:

- `BD_PROPOSAL_FORMS_DRIVEN_V2_CODE_FROZEN`
- `BD_PROPOSAL_FORMS_DRIVEN_V2_DEPLOYMENT_PROVENANCE_BLOCKED_EXTERNAL`
- `REAL_SYNOLOGY_VERIFICATION_BLOCKED_EXTERNAL`

The actual starting SHA is `bcc5061a2dea388ce5a2ec6b2432e27fc3b3b9ac`, verified equal to `origin/main` at entry. This is the post-BD SHA and is the only engineering starting point.

## Working tree

The worktree contains one pre-existing, unrelated untracked user artifact:

`mock-systems/excel/permit_tracker 2.xlsx`

It is preserved and is outside the Engineering / Approved Design Baseline change surface. No overlapping uncommitted changes were found in Project, Engineering, DocumentVersion, TechnicalRule, Requirement, Party, Property, Admin Contract, Dashboard Engineering Works, or migrations.

## Migration entry

- Repository Alembic head: `0042_bd_proposal_forms_driven_v2`
- The default local SQLite database was at revision `0021_e7_unified_task_context` and is not used as the PostgreSQL verification database. Fresh and disposable PostgreSQL environments must be upgraded to the repository head before claims are made.

## Existing baseline evidence

The BD closure records the post-BD verification baseline: PostgreSQL full suite `155 passed`; SQLite full suite `154 passed, 1 skipped`; frontend `32 passed`; frontend build passed; and serial real-stack browser verification passed. Those checks are re-run after Engineering implementation, with any skip explicitly adjudicated.

## Scope gate

This work attaches Project Engineering to the canonical activated `Project`, reuses canonical `DocumentVersion`, Party, Property, Requirement, and TechnicalRule foundations, and leaves AuthorityCase, SubmissionPackage, ExternalApproval, and Construction Start outside this implementation.
