# Manual source ingestion

Client List, Proposal Form, Contract Form, and Permit initiation require a manually selected file. The server validates Project identity and Project Reference, resolves the configured project SOR root, writes to the semantic destination, reads back hash and size, and only then updates workflow state. No screen invents a source file or silently creates a document type.

Permit initiation uses `PERMIT_INITIATION` / `PERMIT_SOURCE`. It is controlled synthetic initiation-source behavior for this environment and remains distinct from municipality submission.
