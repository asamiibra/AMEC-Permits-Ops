# Main Integration Plan

The safe topology is a clean detached worktree from `origin/main`, followed by normal non-destructive merges in dependency order:

1. merge `origin/branch/owner-form-simple-dashboard` (Dashboard closure and storage/source-intake baseline);
2. merge `origin/branch/home-navigation-reorganization` (home/navigation shell);
3. merge `origin/branch/ui-productionization` (visual system and responsive evidence);
4. verify the resulting candidate before moving local `main` or pushing.

A rehearsal in `/private/tmp/proposalops-consolidation-test.rWzDDK` completed all three merges with the `ort` strategy and no conflicts. The real candidate must still run the full regression and browser gates. Main-only commits are preserved by using `origin/main` as the candidate base. No force push, reset, rebase, cherry-pick, data migration, or destructive cleanup is authorized.
