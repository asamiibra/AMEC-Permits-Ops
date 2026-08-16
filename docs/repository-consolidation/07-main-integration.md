# Main Integration

Pre-integration proof: `origin/main` was `7a923fb875de8a46d94699280ef90eb012fedcf1`; the tested feature descendant was `cfc5374b6183aba5c6522963789652ecc022763a`. The intended operation is `git merge --ff-only` in a clean temporary worktree. The protected Excel change in the primary worktree is excluded.

The clean worktree fast-forward completed with no conflicts; final evidence and regression are on `30a0396eb740c6c0a84ca54aa47b9920c9022e12`. All 13 required feature commits are ancestors of this SHA, all current module paths are reachable, Alembic reports one head, final-main regression passed, and `origin/main` has exact SHA parity. Vercel deployments sourced from this clean main tree were blocked/not promotable, so the final-main Vercel parity gate remains open and the feature branch is not retired.
