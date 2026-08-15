# Architecture

Business modules depend on `DocumentStorageService`, which depends on the
provider-neutral `BinaryStorePort`. The available implementations are
`MockBinaryStore` for isolated tests and `SMBBinaryStore` for SMB2/SMB3.

PostgreSQL remains authoritative for Document, DocumentVersion, lineage,
workflow and audit. The approved SMB store owns durable binary bytes. A
locator is opaque (`storage://provider/share/relative-path`) and never a raw
UNC path in normal UI data.

The provider cannot select currentness, business identity, or authority
state.
