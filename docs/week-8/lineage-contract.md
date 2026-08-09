# Lineage Contract

`LineageEdge` records project-scoped upstream/downstream type, ID, version/hash, dependency kind, timestamp, and correlation ID. Required chains include DocumentVersion → Observation → VerifiedAssertion → Package → PreparationRevision → AuthorityPrecheckRun. Edges are deduplicated and historical edges are retained.
