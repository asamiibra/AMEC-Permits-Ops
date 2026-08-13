# Revision UX

Revision allocation locks the deliverable row where supported and enforces a unique `(deliverable_id, sequence)` database index. The configured display policy is `R{sequence}` starting at 1, but caller-provided business codes remain supported. Approved revisions remain immutable and require a new revision. DocumentVersion is explicitly separate from business revision.
