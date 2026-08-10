# Manual upload and SOR contract

`POST /api/proposals-main/intake` is the bounded intake service used by all four orange actions. It requires an action, project, manually selected multipart file, and actor/persona.

Flow:

`SELECTED → VALIDATING → PUSHING_TO_SYSTEM_OF_RECORD → VERIFYING → REGISTERED`

The service validates project identity, resolves the configured bootstrap root and folder template, hashes the source, checks idempotency/deduplication, writes through the adapter, reads back metadata, verifies SHA-256 and size, then creates the `DocumentVersion`, `EvidenceArtifact`, `ProjectArtifactRecord`, `LineageEdge`, and audit event. A retry with the same idempotency key or exact hash reuses the registered record. A same-name different-hash source receives a versioned stored filename and preserves the previous version.

The database stores workflow/index metadata and lineage pointers. It does not store the source bytes as a hidden repository.
