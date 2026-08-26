# Local capture reference set — 2026-08-26

This directory contains historical ProposalOps/AMEC repository captures,
synthetic validation evidence, and execution-prompt references copied from the
owner's local Desktop/Downloads review. It is reference material only.

Nothing in this directory is imported by the backend, frontend, migration
runner, Vercel configuration, Make targets, or CI workflows. The files are not
runtime fixtures and must not be treated as current application authority.

## Included

- Repository branch/SHA capture and update reports.
- Stage1R-A DSM package validation evidence.
- Phase 3B synthetic certification, authorization, freeze, fixture-manifest,
  and canary-integrity references.
- Phase 5 R3R1/R3R1R2 execution-boundary references, including their recorded
  stop/fail-closed states.

## Deliberately excluded

- Real NAS/network discovery output, subscription/build details, secret
  handling instructions, and personal files.
- Executable operator scripts, parser binaries, wheelhouses, and archives.
- The 1.6 GB AMEC corpus evidence and other local-only evidence bundles.
- v16/v17/v18 rescue worktrees and fixture-exclusion code, because those can
  change application behavior and require a separate engineering evaluation.

## Runtime-impact evaluation set

At capture time, the local branch `branch/owner-form-simple-dashboard` was six
commits ahead of its GitHub remote. The final contents of the first three
documentation/evidence-only commits were preserved in the separate
`docs(reference): preserve local release evidence` commit. The three later
runtime-capable commits were deliberately excluded:

| Local commit | Classification | Why it can affect execution |
|---|---|---|
| `b1b3cb9` | Documentation-only; preserved | Release evidence only. |
| `13ab799` | Documentation/evidence-only; preserved | Release evidence and verification artifact only. |
| `1699416` | Documentation/evidence-only; preserved | Release evidence updates only. |
| `45cadfd` | Runtime/deployment-impacting | Changes backend and frontend Vercel configuration. |
| `89ac5d2` | Runtime/build/UI-impacting | Changes frontend dependencies, Vite configuration, UI code, and browser tests. |
| `fde6eb9` | Runtime/database-impacting | Changes migrations and adds migration schema-fingerprint tests. |

The rescue worktrees and their fixture-exclusion layer are also in this
evaluation set. They must not be merged or pushed as reference material until
their import boundaries, source classification behavior, regression coverage,
and production/deployment effects are reviewed on the current branch.
