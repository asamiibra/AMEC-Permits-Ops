# Vercel Main Deployment

Final main code SHA before blocker evidence: `202728cb176d9ef561391531729b3d580a7837f0`.

The backend project was linked as `amec-permits-ops-backend`, and the production `RELEASE_SHA` variable was updated to that full SHA. Clean-root production deployments were attempted from an exact-main detached worktree. Vercel accepted upload but marked each deployment `BLOCKED` before a ready runtime/build output:

- `dpl_JgrUoSYChPrpuc44sGC38Dadz99Y`
- `dpl_E4TnjMH1KWxdghKGiS65gMoHxT2e`
- `dpl_x6AQyq133FVKWzLiqu7dZjNh95nj`
- `dpl_7WHvuiVotSFQ9GMfcu4Vx7rMb8QW`

No exact-main production health, Alembic, or runtime `RELEASE_SHA` proof is claimed. The frontend exact-main deployment was not promoted because the required backend exact-main runtime gate was blocked. `VERCEL_FINAL_MAIN_DEPLOYMENT_BLOCKED=1`.
