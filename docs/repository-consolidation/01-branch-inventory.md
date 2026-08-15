# Branch Inventory

There are two local branches and two corresponding remote-tracking branches. No branch is unknown, orphaned, stale, or diverged from the relevant remote. `main` and `origin/main` point to `7a923fb`; the current feature branch and its remote point to `cfc5374`.

`branch/owner-form-simple-dashboard` is a strict descendant of `origin/main`: ahead 13, behind 0, merge base equal to `origin/main`, and `git log origin/main..branch` lists all 13 commits. `git log branch..origin/main` is empty. The detached temporary worktree is not a branch ref and was not modified.

`UNCLASSIFIED_BRANCH_COUNT=0`.
