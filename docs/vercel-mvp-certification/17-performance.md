# Performance

The effective backend region observed in deployment inspection was `iad1`. Thirty-two-request probes produced zero errors. Representative p50/p95 latencies in milliseconds were: `/health` 230/239, `/api/dashboard` 264/1,723, current Master Content 229/3,148, and version history 341/390. All stayed below the configured function/proxy budgets.

The higher p95 values reflect serverless/database cold or concurrent startup behavior, not a timeout or error. No production SLO is asserted from this synthetic sample.
