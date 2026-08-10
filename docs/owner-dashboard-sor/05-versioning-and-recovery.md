# Versioning and recovery

Create starts a pending `DocumentVersion`; a successful read-back promotes it to `CURRENT`. Modify creates the next version and only then marks the previous version `SUPERSEDED`. The previous bytes are not overwritten. `expected_current_version` is checked with a row lock where supported and stale clients receive `VERSION_CONFLICT` (409). Idempotency records prevent a repeated key from creating another logical version. SOR failures leave the prior current version unchanged and return typed errors.

The synthetic adapter supports read-back and exact historical download. A reconciliation endpoint detects an external hash/size mutation without rewriting the registered historical version.
