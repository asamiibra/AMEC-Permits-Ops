# Domain model

- `MasterContentItem`: stable `ref`, content type, title, category, description, lifecycle status, document pointer, current version pointer.
- `ContentCategory`: governed code/label, allowed content types, active flag, sort order.
- `Document`/`DocumentVersion`: reused for immutable binary/version metadata and current pointer; SOR locator, SHA-256, size, MIME, snapshots, change reason, and status are retained in the existing fields plus metadata.
- `DefinitionEntry`/`DefinitionRevision`: structured semantic registry with immutable revision history and current revision pointer.
- `MasterContentChangeEvent`: global material-change hook for later downstream lineage/revalidation consumers.

No Definition binary is created.
