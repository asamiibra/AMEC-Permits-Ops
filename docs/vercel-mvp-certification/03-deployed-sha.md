# Deployed source parity

The final frontend and backend production deployments were uploaded with the same frozen local worktree SHA. The Vercel CLI deployment path does not expose a Git SHA in `vercel inspect`; parity is therefore established by exact local-source CLI upload and the backend `RELEASE_SHA` provenance value configured for the final deployment.

The final SHA and both deployment IDs are recorded in the certification handoff. No Git-triggered preview SHA is treated as the production deployment SHA.
