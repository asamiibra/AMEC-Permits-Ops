# Concurrency

An explicit eight-thread PostgreSQL probe was run for keyed authority notifications and keyed inspections. Each command group returned eight successful responses with one unique persisted record. Matching idempotency keys return the existing project-scoped record; cross-project reuse remains rejected.

The inspection path now has a nullable idempotency key, a project-execution unique constraint, and an IntegrityError recovery/refetch path. Migration `0051_construction_inspection_idempotency` carries the constraint forward.
