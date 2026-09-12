# SQL proof

SQL Server 2022 was used as the canonical validation database through the disposable local SQL ladder. SQLite was used only for supporting tests.

- SQL Server version: `16.0.4265.3`; ODBC Driver 18.
- Clean database migrated baseline → current Alembic head successfully.
- Repository head: `opportunity_proposal_idempotency_v1`.
- Database head: `opportunity_proposal_idempotency_v1`.
- `SELECT 1`: PASS.
- Independent reconnect: PASS.
- Transaction commit/read-back: PASS.
- Final browser Proposal `AMEC-SYN-PROP-0002` has two accepted revisions (R1/R2), four source evidence rows, one technical assessment, one current scope confirmation, one eligible service decision, one authorized release, one `CLIENT_PORTAL` distribution, two client responses, one verified acceptance, one `PASS` LPO reconciliation with `variances=[]`, and one `ELIGIBLE` handoff row.
- The final R2 content hash is `3afff2ff7312eae21f8f6a7744f2d3bb2422552c9a8b2c73c4b43a94e67a14b`; release, acceptance, LPO, and handoff rows all point to the same accepted R2 revision.
- Independent-connection read-back of the final browser proposal and its ten audit events: PASS.
- Contract rows for the Proposal: `0`; Project Activation rows for the accepted revisions: `0`.

No production or pre-production database was touched.
