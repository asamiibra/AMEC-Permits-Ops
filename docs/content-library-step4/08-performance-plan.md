# Future deployed performance plan

Step 3’s local synthetic result (`57` records, `61` SQL statements across five
reads, p50 about `7.8ms`, p95 about `8.2ms`) is only a regression guard. It is
not an Azure SQL or production SLA.

The future deployed run records, without arbitrary thresholds:

- request count and endpoint latency for health, discovery, and retrieval;
- SQL statement count and candidate/result counts;
- retrieval latency separately from network latency;
- bounded result size and memory where available;
- query-plan evidence where the deployed operator permits safe read-only
  inspection;
- N+1 indicators across increasing bounded fixture counts.

Baseline first, then compare candidate behavior. Any later index decision must
name the exact query class and evidence; no index, cache, embedding store,
Azure AI Search, or vector database is created as preparation.
