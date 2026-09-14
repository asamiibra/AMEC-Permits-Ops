# Database migration proof

Migration added: `backend/migrations/versions/p07_intelligence_foundation_closure.py`.

Executed command: `PYTHONPATH=. python3 -m alembic -c alembic.ini heads`.

Observed head: `p07_intelligence_foundation_closure (head)`; head count is one. The migration has an additive upgrade and a downgrade for all P07 tables, columns, and indexes.

A disposable SQLite `upgrade head` attempt reached the repository baseline and stopped at its pre-existing `ALTER` foreign-key operation (`NotImplementedError` on SQLite); SQLite roundtrip remains recorded separately as skipped for that repository limitation.

PostgreSQL 16 proof was then run against a fresh disposable container with `APP_ENV=TEST`, `SYNTHETIC_ONLY=true`, and `DATABASE_URL=postgresql+psycopg://p07:p07@127.0.0.1:15432/p07`. The first run exposed and the second run verified two genuine PostgreSQL portability repairs: explicit `VARCHAR(80)` casts for reused baseline seed parameters, and a shortened 63-byte-safe Source-18 index identifier. The authoritative result reached `p07_intelligence_foundation_closure`; `alembic_version` contains exactly that head and the database contains 475 public tables.

Migration contract result: PASS for the PostgreSQL upgrade-head proof; SQLite full roundtrip remains skipped only for the established SQLite ALTER limitation.
