# Integrity and immutability

SHA-256 and byte count are evidence of exact bytes, not business identity.
Every upload is streamed and verified through a fresh read. Final targets use
exclusive/no-replace semantics. Existing equal bytes are reusable only when
the durable operation identity proves idempotent recovery; otherwise the
operation fails with `STORAGE_CONFLICT`.

DocumentVersion history is append-only. An external change produces drift or
missing-object evidence and requires an explicit reconciliation action.
