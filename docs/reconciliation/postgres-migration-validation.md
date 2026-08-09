# PostgreSQL Migration Validation

Native PostgreSQL 16 is the target integrity runtime. The validation target is the isolated `permitops_test` database on localhost, not Docker Desktop.

Required sequence:

```text
drop/recreate permitops_test
alembic upgrade 0001
alembic upgrade head
canonical seed
Week 1–8 regression
golden-path-v1
```

The recorded validation result is maintained with the final reconciliation run. The Week 3 downgrade boundary is separately checked by `docs/reconciliation/migration-roundtrip-validation.md`; after downgrade, the database is re-upgraded and reseeded before regression.

Final recorded result: PostgreSQL 16.14, Alembic head `0010_week1_8_integrity_reconciliation`, canonical seed PASS, backend regression `54 passed / 1 documented warning`, and Golden Path v1 PASS.
