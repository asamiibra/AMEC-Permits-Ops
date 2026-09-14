# Proposal production-hardening baseline

Audit timestamp: 2026-09-13T20:59:25Z (repository evidence refreshed before source edits).

## Branch and immutable provenance

- Canonical continuation branch: `module/opportunity-proposal-client-tender`.
- Remote accepted PR41 head: `dbd54c8e208e7347c959364b0bffd0f513eb81c7`, tree `c3b91ecd87d525a3e5f4332cedb09811354c18f3`.
- Immutable PR41 merge: `e3af5e8d5c8abc996f1039aaae394bb734cc0193`, tree `c3b91ecd87d525a3e5f4332cedb09811354c18f3`.
- Protected `origin/main`: `594b313a15cc6ade3f0505de395a5817c6337268`, tree `73d6781640bc774b577a6eb8e938868ef3fb83c3`.
- GitHub compare `main...module/opportunity-proposal-client-tender`: `status=behind`, `ahead_by=0`, `behind_by=17`, merge base PR41 head.
- The isolated working copy was unshallowed, fetched with `origin main module/opportunity-proposal-client-tender`, and fast-forwarded to `594b313a15cc6ade3f0505de395a5817c6337268` without conflict. It remains on the existing branch name; no hardening branch was created.
- Branch census found `feature/proposalops-intelligence-v1` at `bdfa445de3351d49fb44b324e01928f2a4adfa76`, but no open Proposal PR or repository designation superseding the canonical branch. Other Proposal-named branches are release-integration/SQL compatibility lines. This is not treated as a superseding continuation.

## Workspace preservation

The user worktree is `/Users/ahmedsami/Desktop/Qatar Permitting Tool/Dev`, branch `azure-p0-v25-preauthorization-repair-v1`. It was not modified. Status/diff inspection was blocked by pre-existing shared-worktree Git lock/process activity (`.git/worktrees/amec-billing-experience-20260913/HEAD.lock` and long-running status processes); this is recorded as an environment constraint rather than bypassed destructively.

## Current code findings

At the protected-main baseline, Proposal routes still expose synthetic-only response markers, create a synthetic ClientAccount from `client_name`, accept actor parameters/defaults, create accepted output through `output_bytes()` with `synthetic://` references, accept eligibility based on caller payload, accept client evidence references without exact DocumentVersion/hash validation, and derive LPO `PASS` from caller-provided empty variances. Active staleness review clears events without recording a revalidation revision/result. These are implementation gaps, not proof of production readiness.

Repository Alembic head is `17c6ebd99c4a` (read from the repository migration graph). No database migration or external production gate was run during baseline capture.

## Final branch position

- Hardening implementation commit: `b47263a9ef86e472f34d218c2f255cf6d0dd73f1`, tree `fc4c3bd05436c7ac5559ed8bfc814fb9eaaca93b`.
- Evidence-seal commit: `63fb1a94358f6710cb1ef538328c94abd8679d37`, tree `28ae5f89baa1aaa9c1c14372938013319180eeae`.
- Final branch remains `module/opportunity-proposal-client-tender`, 2 commits ahead of protected `main` and 19 commits ahead of the remote PR41 head; merge base with `main` is `594b313a15cc6ade3f0505de395a5817c6337268`.
- PR41 accepted SHA `dbd54c8e208e7347c959364b0bffd0f513eb81c7` and merge `e3af5e8d5c8abc996f1039aaae394bb734cc0193` remain immutable ancestors/provenance; no new Proposal branch was created.
