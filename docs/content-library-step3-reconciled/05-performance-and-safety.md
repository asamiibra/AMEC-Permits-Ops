# Synthetic performance and safety evidence

The isolated quality fixture uses a bounded canonical corpus and records SQL
statement count, candidate count, and SQLite `EXPLAIN QUERY PLAN` output. The
retrieval implementation batches profiles, provenance, bindings, observations,
assertions, and classifications for broad queries; explicit ID queries remain
scoped and authorization-filtered.

The test gate is fewer than 100 SQL statements for the bounded query and a
successful searchable/indexable query plan; the current quality run passes
that gate. This is a proof of bounded query shape, not a production latency
promise. No new retrieval technology or external infrastructure is required.
