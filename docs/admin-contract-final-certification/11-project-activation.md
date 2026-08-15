# Project Activation

Contract existence does not activate a Project. Owner-only Project Activation requires explicit project code, start date, current Contract readiness, and an idempotency key. The canonical Project is linked once; repeat activation returns the existing activation rather than creating duplicates. Project code/start-date semantics remain policy decisions, not inferred facts.

The owner-session, billing, handover, and browser suites prove the separation on PostgreSQL.

