# AWS Portability

Deployment-specific evidence is classified as follows:

- `PORTABLE`: source tree, FastAPI/React application, PostgreSQL contract, migration history, synthetic disclosure, and canonical domain/workflow identifiers.
- `REPLACE_ON_AWS`: Vercel project/deployment IDs, Vercel Git integration settings, Vercel environment-variable bindings, and platform-specific build/runtime configuration.
- `REMOVE_ON_AWS`: any Vercel-only deployment URL, deployment ID, or Vercel filesystem assumption.

No business identity is bound to a Vercel deployment ID, Vercel instance, Vercel Blob URL, Vercel cron ID, or local ephemeral filesystem.
