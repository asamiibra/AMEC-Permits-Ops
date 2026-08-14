# Concurrency

Status: IMPLEMENTED_AND_VERIFIED.

Four concurrent explicit starts using one idempotency key converge to one Completion case and one Completion context. Unique constraints plus flush/commit recovery protect context and case-link creation.
