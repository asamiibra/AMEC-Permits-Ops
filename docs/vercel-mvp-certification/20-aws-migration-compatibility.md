# AWS migration compatibility

Portable components remain the domain models, services, `DocumentStorageService`, `BinaryStorePort`, SMB adapter, PostgreSQL persistence, source-intake ledger, outbox, RBAC, audit, and resolver rules.

Vercel-only changes are runtime entrypoint/configuration, build-time schema compatibility, explicit synthetic DB-backed document mode, serverless filesystem guards, and the request-size transport boundary. AWS replacements are the compute runtime, deployment secret manager, worker scheduler, and durable object/SMB endpoint. No business identity or correctness depends on a Vercel deployment ID, cron ID, Blob URL, or instance memory.
