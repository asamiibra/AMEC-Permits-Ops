# Storage contract

Managed Content Library writes use `DocumentStorageService(create_binary_store())`. The service performs temporary write, read-back size/hash verification, finalization, final read-back verification, and only then marks the DocumentVersion storage verified.

The provider is selected by the configured factory (`mock`, `smb`, or `azure_blob`); application code does not bind managed writes to SMB or a local filesystem. Production settings continue to require the managed Azure Blob provider where a managed store is required. The closure run did not mutate Azure, SMB, production, preproduction, or real AMEC data.

Synthetic TEST storage remains explicitly DB-backed where the runtime is deployed synthetic-only.
