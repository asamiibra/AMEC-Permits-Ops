# source intake design

`SourceIntakeBatch` records archive identity, source location reference, receipt actor, discovery counts, manifest version and lifecycle. `SourceIntakeItem` records the batch-scoped ordinal, original path, normalized path, size, hash, media type, source locator, disposition, duplicate grouping, promotion state and target IDs.

Hashes are evidence, not identity. The uniqueness constraint is `(batch_id, source_ordinal, original_relative_path)`, and the same hash can therefore occur on multiple observations. Empty folders are represented as `SOURCE_GAP` rows and do not create Documents or Master Content.

The service is hidden from the Owner UI. It accepts a bounded archive, applies the controlling manifest, and promotes only `PROMOTE_MASTER_CURRENT` and `PROMOTE_MASTER_NEEDS_REVIEW` rows. Transactional/historical, reference-only and blocked rows remain ledger-only.
