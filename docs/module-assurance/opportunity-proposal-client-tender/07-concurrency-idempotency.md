# Concurrency and idempotency

Protected transitions use accepted-revision identity and durable unique keys. Proposal creation now persists a filtered unique idempotency key; a repeated create request returns the same Proposal context with `IDEMPOTENT`. Commercial release, distribution, LPO reconciliation, client response, and handoff eligibility likewise use stable idempotency keys or revision-scoped uniqueness. The focused suite verifies duplicate release and Proposal creation behavior.

The API uses row locking for human Proposal Accept and rejects stale revision releases. Parallel multi-process load testing remains a later governed CI gate rather than a claim made by this local synthetic run.
