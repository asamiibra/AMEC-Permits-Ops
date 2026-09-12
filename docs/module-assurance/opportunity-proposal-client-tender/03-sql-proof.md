# SQL proof

SQL Server 2022 was used as the canonical validation database through the disposable local SQL ladder. SQLite was used only for supporting tests.

- SQL Server version: `16.0.4265.3`; ODBC Driver 18.
- Clean database migrated baseline → current Alembic head successfully.
- Repository head: `opportunity_proposal_idempotency_v1`.
- Database head: `opportunity_proposal_idempotency_v1`.
- `SELECT 1`: PASS.
- Independent reconnect: PASS.
- Transaction commit/read-back: PASS.
- Current SQL database control rows: technical assessments 2, scope confirmations 2, service eligibility 2, commercial releases 3, distribution events 3, acceptance verifications 3, LPO reconciliations 3, handoff eligibility 1.
- Independent-connection read-back of the browser proposal handoff row: PASS.

No production or pre-production database was touched.
