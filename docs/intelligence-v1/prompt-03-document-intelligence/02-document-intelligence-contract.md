# Document Intelligence contract

P03 establishes one bounded machine-intelligence path:

```text
governed source
  → source identity / integrity / stability
  → DocumentVersion where applicable
  → existing Phase4 evidence, classification, and FieldObservation
  → CandidateAssertion
  → STOP
```

The adapter uses the P02 `CandidateAssertion` contract. Candidate identity is a SHA-256 of canonical scope, subject, assertion, producer, exact source/evidence identity, and value identity. The resulting bounded key is `di:<sha256>`.

Candidate lifecycle is limited to `CURRENT`, `SUPERSEDED`, and `STALE` for P03 machine writes. P03 never writes `PROMOTED` or `REJECTED`. A newer source identity in the same producer family preserves the old candidate, marks it `SUPERSEDED`, creates a new `CURRENT` candidate, and binds `supersedes_candidate_assertion_id`.

The field-observation adapter preserves field definition, project scope, DocumentVersion, FieldObservation, extractor version/hash, confidence, value hash, and correlation. The classifier adapter preserves the complete Phase5 classification/evidence envelope and adds normalized classification and relationship candidates alongside it. The bridge adapter preserves all allowlist, bounds, declared-size, SHA-256, Ed25519, replay, scope, DocumentVersion, evidence, classification, observation, and audit controls.

No adapter creates `VerifiedAssertion`, typed business projections, workflow tasks, notifications, review queues, model calls, embeddings, vector stores, or protected domain transitions.

