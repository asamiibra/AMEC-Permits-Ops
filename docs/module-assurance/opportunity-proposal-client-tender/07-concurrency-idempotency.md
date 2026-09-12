# Concurrency and idempotency

Protected transitions use accepted-revision identity and durable unique keys. Proposal creation now persists a filtered unique idempotency key; a repeated create request returns the same Proposal context with `IDEMPOTENT`. Commercial release, distribution, LPO reconciliation, client response, acceptance verification, and handoff eligibility likewise use stable idempotency keys or revision-scoped uniqueness. The focused suite verifies all six duplicate replay paths, and the dedicated concurrent replay test submits those committed duplicates in parallel and asserts `IDEMPOTENT` with one row per transition.

The API uses row locking for human Proposal Accept and rejects stale revision releases. Sustained multi-process load testing across multiple API workers remains a later operational gate; this closure claims only the deterministic concurrent replay proof above.
