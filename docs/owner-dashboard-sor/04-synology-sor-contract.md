# SOR contract

The API accepts business metadata and a file. The server resolves the configured semantic destination (`MASTER_FORM`, `MASTER_REPORT`, or `MASTER_ENGINEERING_WORK`), normalizes the stored filename, writes through the server-side adapter, reads metadata back, and verifies size and SHA-256 before promotion. Browser responses never include raw SOR locators, share names, credentials, hashes, or adapter names.

The current implementation is proven with `MockSynologyAdapter` only. It does not claim a real Synology connection.
