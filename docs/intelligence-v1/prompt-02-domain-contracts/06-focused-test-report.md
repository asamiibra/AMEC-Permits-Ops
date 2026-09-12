# Focused test report

```text
COMMAND=PYTHONPATH=. pytest -q backend/tests/test_intelligence_contracts.py
RESULT=5 passed, 1 warning

COMMAND=PYTHONPATH=. pytest -q backend/tests/test_migration_runner.py backend/tests/test_db_rebaseline.py backend/tests/test_database_startup_contract.py backend/tests/test_azure_sql_port.py
RESULT=62 passed, 1 warning
```

Coverage includes schema columns/constraints/indexes, candidate-only semantics, state/output-class rejection, exact idempotency, stable hashing, dependency metadata hygiene and counting, citation ordinal uniqueness, manifest hashing/authority rejection, and legacy-writer compatibility.
