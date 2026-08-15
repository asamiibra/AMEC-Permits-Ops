# Integration Plan

The topology is Case A: `origin/main` is an ancestor of the tested feature SHA. The plan is a non-destructive fast-forward, not a merge commit, cherry-pick, rebase, or force push.

1. Preserve the dirty primary worktree and protected Excel file.
2. Validate the feature SHA and existing Dashboard/Vercel evidence.
3. Use a clean temporary worktree from `origin/main` for `git merge --ff-only origin/branch/owner-form-simple-dashboard`.
4. Run the full final-main regression on the resulting SHA.
5. Push `main` with a normal non-force push and verify remote SHA parity.
6. Deploy both Vercel projects from that exact final `main` SHA and rerun smoke checks.
7. Only then evaluate the named feature branch for deletion. No other branch is eligible for automatic deletion.

No merge conflicts are expected. Migrations 0056–0058 and current Dashboard/storage/Source Intake/Vercel work are the integration payload.
