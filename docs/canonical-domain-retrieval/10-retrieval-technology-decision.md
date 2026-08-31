# Phase 5 — Retrieval technology decision

| Use case | Current mechanism | Measured result | Recommendation |
|---|---|---|---|
| Exact ID/version lookup | SQL primary keys and version pointers | Synthetic proof resolves exact IDs and historical V1 | `EXISTING_SQL_SUFFICIENT` |
| Metadata/authority filtering | SQL projections and governance joins | Existing master projections preserve status, bindings, currentness, and provenance | `EXISTING_SQL_SUFFICIENT` |
| Relationship traversal | Foreign keys and relationship IDs | Synthetic envelope preserves master→document→version and evidence links | `EXISTING_SQL_SUFFICIENT` |
| Structured project facts | SQL document/project/evidence queries | Wrong-project isolation is proven by explicit membership | `EXISTING_SQL_SUFFICIENT` |
| Full-text / Arabic-English lexical search | No dedicated search implementation found | Corpus size, language quality, and latency are not yet measured | `FURTHER_EVIDENCE_REQUIRED` |
| Semantic similarity / embeddings | Not present | No demonstrated requirement in this proof | `FURTHER_EVIDENCE_REQUIRED` |
| Citation reconstruction | Canonical IDs, versions, hashes, and locators | Exact version citations pass | `EXISTING_SQL_SUFFICIENT` |
| AI context assembly | Read-only envelope plus deterministic synthetic answer seam | No canonical write; citations retained | `EXISTING_SQL_SUFFICIENT` |

The smallest justified current solution is SQL-backed governed retrieval over
canonical records. No vector, full-text, cache, materialized read store, or
external search service is provisioned. A production-scale decision requires
measured corpus/query/latency evidence; if it demonstrates a new service is
needed, owner authorization is required before provisioning.

`RETRIEVAL_TECHNOLOGY_DECISION=EXISTING_SQL_SUFFICIENT_FOR_PROVEN_USE_CASES; FURTHER_EVIDENCE_REQUIRED_FOR_SEMANTIC_OR_SCALE_REQUIREMENTS`

`NEW_EXTERNAL_RETRIEVAL_INFRASTRUCTURE_REQUIRED=0`
