# Performance and Scale

The synthetic scale probe used 200 projects, 200 ConstructionExecutions, 4,000 obligations, 2,000 inspections, 4,000 issues, and 800 work-control events.

| Operation | Result | Queries | Returned |
|---|---:|---:|---:|
| Construction list | p50 10.11 ms / p95 10.24 ms | 1 | 201 |
| Detail | p50 8.54 ms / p95 8.54 ms | 10 | 20/10/20 child rows |
| Readiness | p50 7.14 ms / p95 7.14 ms | 9 | bounded response |
| Completion context | p50 4.06 ms / p95 4.06 ms | 4 | bounded response |
| History | p50 2.87 ms / p95 2.87 ms | 2 | 4 |

No N+1 pattern was observed in detail. The endpoint has no explicit offset/limit metadata, so the list result is a bounded synthetic benchmark and not a production pagination SLO claim.
