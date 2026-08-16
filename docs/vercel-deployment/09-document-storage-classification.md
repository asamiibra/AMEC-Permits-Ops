# Document-storage classification

Classification: `SYNTHETIC_DOCUMENT_STORAGE`.

The deployed backend health reports synthetic test mode, a synthetic/mock storage provider, and `real_synology=NOT_CONFIGURED`. The MVP’s durable application state is PostgreSQL-backed, but this is not evidence of real Owner Synology or durable production document-binary storage.

Counters: `VERCEL_REAL_DURABLE_DOCUMENT_STORAGE=0`, `VERCEL_SYNTHETIC_DOCUMENT_STORAGE=1`, `VERCEL_DOCUMENT_STORAGE_BLOCKED=0`, `OWNER_SYNOLOGY_INTEGRATION_VERIFIED=0`, `SYNOLOGY_DSM_STORAGE_PARITY_VERIFIED=0`.
