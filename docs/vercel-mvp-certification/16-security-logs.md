# Security and logs

No secret values were emitted. Frontend production assets contained no `.env`, database, archive, document, or SQLite files. Backend logs and API responses used masked/configuration-only storage health and did not expose raw document bytes; download probes measured bytes and hashes only.

The frontend sends a development role header in synthetic mode. This is a deliberate TEST-only behavior and is not a production authentication claim. Real Synology credentials, real Owner documents, and production authority credentials are absent.
