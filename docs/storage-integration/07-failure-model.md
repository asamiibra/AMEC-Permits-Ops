# Failure model and recovery

`StorageOperation` records PLANNED, WRITING, READBACK_VERIFYING, FINALIZING,
STORAGE_VERIFIED, DB_PUBLISHING, PUBLISHED and terminal/recovery states.
Temporary objects live in `.proposalops/tmp` and are eligible for cleanup
only after the durable operation is terminal or its lease has safely expired.

PostgreSQL and SMB are not one ACID transaction. A final orphan is never
shown as business content; it is reconciled under controlled operator policy.
