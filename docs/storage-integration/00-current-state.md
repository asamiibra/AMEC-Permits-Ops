# Storage integration current state

The repository previously used `MockSynologyAdapter` as a local filesystem
test seam. Proposal intake, master content, contract evidence and several
synthetic fixtures still use that legacy seam. It is retained only for
fixture compatibility and is blocked when `STORAGE_PROVIDER=smb` or the app
is production.

The permanent seam is now `BinaryStorePort` → `DocumentStorageService` →
provider. `StorageOperation` is the durable journal and
`StorageOutboxEvent` is the post-commit delivery boundary. No Owner Synology
endpoint has been connected or verified by this repository change.

See `artifacts/storage-integration/storage-callsite-matrix.json` for the
machine-readable call-site inventory.
