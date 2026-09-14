# Database migration proof

Candidate: `b21ab2fe5e30e306a9bc40149ba10324f0bebd9b`.

Fresh disposable PostgreSQL 16.15 database `p07_final_20260914` completed
zero-to-head migration. `alembic_version` contains exactly one row with
`p07_intelligence_foundation_closure`; 475 public tables and zero identifiers
over PostgreSQL's 63-byte limit were verified. All eight P07 tables and all
five reservation-fence ledger columns are present.

A separate committed transaction followed by a new connection read back the
synthetic marker `P07_POSTGRES_REOPEN_MARKER`. The database and container were
destroyed after evidence capture. The PostgreSQL-focused P07/P05/document set
passed `24` tests against this database.

Machine-readable proof: `25-postgres16-proof.json`.

`P07_POSTGRES16_GATE=PASS`.
