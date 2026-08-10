# Reference Numbering

Forms, Reports, Engineering Works, and Definitions use durable PostgreSQL-backed sequences with default `F`, `R`, `E`, and `D` prefixes and four-digit padding. Explicit references remain supported. Allocation locks the sequence row, reconciles existing numeric suffixes, and checks idempotency before allocation. S/N is a presentation ordinal only. See `reference-tests.json`.
