# Concurrency and idempotency

Existing unique constraints, proposal row locks, and scope-checked idempotency now cover accepted output/release/distribution/response/LPO replay paths. The repository regression suite passes the available committed replay and concurrency checks; external multi-worker/provider-restart qualification remains `NOT_RUN`/`BLOCKED_EXTERNAL` where it requires deployed infrastructure.
