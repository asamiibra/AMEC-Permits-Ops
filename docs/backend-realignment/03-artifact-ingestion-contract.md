# Artifact ingestion contract

`ArtifactIngestionService` is the bounded dispatch seam for Tender Email,
Tender Document, Tender Image, Client, Proposal, Contract and Permit
initiation sources. It validates context, filename, non-empty content and size,
computes a SHA-256, delegates to the configured provisional or canonical
Synology adapter, performs read-back verification, and then registers
DocumentVersion, EvidenceArtifact, LineageEdge and AuditEvent.

The database is an operational index. The configured AMEC repository remains
the document SOR. Hash/idempotency keys are context- and artifact-class-aware;
different hashes create a new version and preserve supersession.
