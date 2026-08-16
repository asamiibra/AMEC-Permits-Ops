# Deployment execution

Deployment target: intended MVP Production aliases. Supported path: authenticated Vercel CLI source deployment from the `frontend` project root with `--prod --project amec-permits-ops`, using the committed exact SHA as the source worktree and a deployment metadata field carrying that SHA. The backend was not redeployed because this wave changed no backend files; the existing PostgreSQL-backed backend remains the API target.

The final deployment ID, URL, READY state, alias inspection, and command output are recorded in `04-sha-parity.md` and `artifacts/vercel-deployment/verification.json` after execution. No deployment success token is emitted before those checks pass.
