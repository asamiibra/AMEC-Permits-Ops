# Deployment verification

The Vercel production aliases are live and aligned with this implementation. Backend health reports durable PostgreSQL, no SQLite fallback, a valid connection, and Alembic `0028_master_content_propagation`; OpenAPI exposes the master-content/definition paths. The deployed Owner-only Administration Forms check passes.

The deployed `TEST` runtime uses an explicitly ephemeral synthetic `/tmp` SOR because the Vercel bundle filesystem is read-only. This proves the deployed software path only; a later serverless invocation cannot be used to claim durable historical-download parity from that ephemeral store. It is not a real Synology or durable production SOR claim.
