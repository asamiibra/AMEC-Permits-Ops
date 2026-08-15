# Provider contract tests

`backend/tests/test_binary_store_contract.py` is the reusable provider seam.
The full Level 1 suite must run against Samba, then the same suite against a
Synology mirror and Owner test share. It covers health, Unicode names,
streamed write/read, immutable conflicts, fresh read-back and provider
capabilities. The complete finalization protocol is covered by
`test_document_storage_service.py`.
