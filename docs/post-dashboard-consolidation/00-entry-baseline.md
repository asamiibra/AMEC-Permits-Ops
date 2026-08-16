# ProposalOps — Post-Dashboard Consolidation Entry Baseline

Captured 2026-08-15 after `git fetch --all --prune`, before integration edits.

- Starting branch: `branch/owner-form-simple-dashboard`
- Starting HEAD / remote feature: `7250b5264cf586e15adf185e8947e60399cf00aa`
- `main` / `origin/main`: `c31e6fb04265999bbd85b4974095a9246156734a`
- Common branch base: `07ea0478dd71f37c84995936c057acadf3e939a0`
- Other remote feature heads: home `eccdfe87aa67615a0153a41e9012bb011faa5092`; UI `aefb541a3c186cfd6aca00ff14f602e06e5b4aaa`.
- Alembic head: `0058_source_intake_ledger`; current local command environment is SQLite. PostgreSQL migration proof is a candidate gate.
- Working tree: only pre-existing `mock-systems/excel/permit_tracker.xlsx` is modified.
- Excel preservation stash: `stash@{0}` / `2f072fce8eb6f31851a8233e054a88a0f17eca6c`; binary diff `8143 -> 8129` bytes. It remains untouched.
- Existing detached reference worktree: `/private/tmp/proposalops-wave-a-v1-reference` at `0ccb61a2b7ac483a17590c27eca594b16b505bb7`.

The task integration worktree is intentionally separate from this dirty primary worktree.
