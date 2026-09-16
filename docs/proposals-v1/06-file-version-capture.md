# Capture primitive

The adapter stats the opened file, reads and hashes bounded chunks, stats it again, and reopens the path to compare inode/device/size/mtime/ctime. Replacement or modification is detected. Retry is limited to 1–3 attempts. Source-changed and size-limit tests pass.

Durable sync, version deduplication, missing-at-source history and canonical DocumentStorageService publication are NOT_IMPLEMENTED. No persisted versioning pass is claimed. Returned bytes/hash are an input to canonical storage, not proof of durable capture.
