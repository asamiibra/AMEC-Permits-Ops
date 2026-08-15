# Real process crash results

Fresh PostgreSQL plus the live Samba lab passed all five storage crash boundaries, source promotion retry, post-commit outbox recovery, and idempotent redelivery. The result was zero visible unverified versions, duplicate versions, lost outbox events, source mutations, and untracked orphans.

See `artifacts/integrated-local-closure/process-crash-results.json`.
