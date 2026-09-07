# PostgreSQL R13 0001–0059 rebaseline

The active Alembic lineage is now one explicit root revision:

```text
baseline_r13_0059 (down_revision=None)
```

The exact R13 chain remains byte-for-byte under
`backend/migrations/history/postgresql_r13_0001_0059/` as historical
provenance. That directory is not an Alembic version location and must not be
executed against future application models.

## Authority

The reference package was captured in GitHub Actions using
`postgres:16@sha256:e17e86066e5ef83e0952a9347f5c792b7ece00972e2aa787a6986f471b3dd3d5`.
It used two independent exact-R13 databases and froze the schema and
migration-owned control-data contracts before candidate generation.

Reference schema contract: `1f75d13fbac7b42585504df2da7c48a2bf6c22def49fedff64a13954dfa540e1`

Reference control-data contract: `b423173037fb3b16a4d0a158faa8321397e926c2721b6a4c5b12c501b2b0f27f`

The only preserved control row is the deterministic Proposal reference
sequence owned by legacy revision `0055_bd_proposal_final_hardening`.

## Runtime and release contract

Application readiness delegates to `verify_database_migration_head()`, which
resolves the single active Alembic head dynamically. The redundant literal
head assertion was removed from `backend/app/main.py`; the database runtime
authority in `backend/app/db.py` remains byte-identical to exact R13.

The A1 release schema and verifier require `baseline_r13_0059`. An old database
reporting `0059_entra_user_identity` is rejected fail-closed.

Root downgrade is intentionally unsupported and raises a `RuntimeError`.
