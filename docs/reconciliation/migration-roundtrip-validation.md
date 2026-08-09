# Migration Roundtrip Validation

Validation command sequence:

```text
drop/recreate isolated permitops_test
alembic downgrade base
alembic upgrade 0001_week1_skeleton
alembic upgrade 0002_week2_document_intelligence
alembic upgrade 0003_phase0_week3_decision_layer
alembic upgrade head
alembic downgrade 0002_week2_document_intelligence
verify Week 3 tables and phase0 column are absent
alembic upgrade head
canonical seed
backend regression
```

The Week 3 boundary downgrade is responsible for all Week 3 objects introduced by the decision-layer metadata path while preserving shared Week 1/2 objects. The reconciliation migration `0010_week1_8_integrity_reconciliation` is reversible for its own tables/columns. Native PostgreSQL 16 is the target runtime; Docker Desktop is not a product gate.

Recorded PostgreSQL result: clean `0001 → head` passed; `head → 0002_week2_document_intelligence` passed with the Week 3 tables and `raid_items.phase0_close_impact` absent; `0002 → head` passed; canonical seed, 54-test regression, and Golden Path v1 then passed.
