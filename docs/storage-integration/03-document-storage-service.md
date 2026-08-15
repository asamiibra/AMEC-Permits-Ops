# Document storage service

`DocumentStorageService.store_version` allocates a candidate version ID but
does not create a normal visible DocumentVersion until storage verification
has completed. It persists a `StorageOperation` state progression and creates
one `DocumentVersionStored` outbox event in the same database transaction as
publication.

The service preserves the original filename as metadata, uses a normalized
physical filename, creates an immutable version-specific path, and returns a
safe `StoredVersion` result. `read_verified` detects external mutation as
`STORAGE_INTEGRITY_DRIFT` without rewriting the canonical hash.
