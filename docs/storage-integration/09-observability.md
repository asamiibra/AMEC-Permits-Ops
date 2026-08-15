# Observability

The operation journal, audit event and outbox payload carry operation ID,
provider, DocumentVersion, size/hash result and normalized error class.
Infrastructure metrics must use low-cardinality labels only: provider,
operation, result, error class, document class and environment. Filenames,
client names, raw paths, credentials and content are excluded.
