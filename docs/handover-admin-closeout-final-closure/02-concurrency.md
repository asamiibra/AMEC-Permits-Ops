# Concurrency certification

Real PostgreSQL thread-pool checks completed with zero unexpected failures. Same-key distribution and receipt requests converged to one durable record with idempotent responses; acceptance produced one terminal acceptance and conflict responses for later races; service-close was idempotent; eight concurrent lock attempts produced one winner; eight concurrent revision attempts produced one new revision with numbers `[1, 2]`.

