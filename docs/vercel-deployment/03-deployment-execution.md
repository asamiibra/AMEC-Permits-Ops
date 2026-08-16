# Deployment execution

Deployment target: intended MVP Production aliases. The exact release SHA was `e5b916d5a81dfdd72a93a769d49d015cf2c71866`, and it matched `origin/branch/ui-productionization` before deployment attempts. The supported authenticated Vercel CLI path was exercised. Direct source attempts were blocked by the project Root Directory being applied twice; a reversible project-setting correction followed by `vercel build` successfully produced the exact prebuilt artifact.

The final `vercel deploy --prebuilt --prod` was rejected before creating a deployment by the platform quota gate: `api-deployments-free-per-day` / `more than 100` / retry in 24 hours. The project Root Directory was restored to its original `frontend` value. The backend was not redeployed because this wave changed no backend files; the existing PostgreSQL-backed backend remains the API target.

No READY deployment ID exists for this release. The two prebuilt/source attempts that reached Vercel were `dpl_72VMhwP4JTaENTxeBaGcuwW4n2uk` and `dpl_EB9VWHYtucCQVPE27kJbE2aSJs3E`, both `BLOCKED` with empty build output due the root-directory mismatch; the final prebuilt upload was rejected by quota before deployment creation. No deployment success token is emitted.
