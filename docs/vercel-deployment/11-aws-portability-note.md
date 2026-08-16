# AWS portability note

This release adds no Vercel-specific business identity, table, workflow, or storage semantics. The frontend deployment uses the existing static Vite build and API rewrite. The backend remains the existing FastAPI/PostgreSQL application with existing `DocumentStorageService`, `BinaryStorePort`, `StorageOperation`, `StorageOutboxEvent`, RBAC, audit, and Home read-model boundaries.

Classification: current Vercel source deployment is `PORTABLE`; the Vercel alias/rewrites are `REPLACE_ON_AWS` transport configuration; synthetic/mock document storage is `REMOVE_ON_AWS` when the later approved AWS/Owner storage target is available.
