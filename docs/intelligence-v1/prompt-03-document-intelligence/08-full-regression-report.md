# Prompt 03 full regression report

```text
BACKEND_COMMAND=PYTHONPATH=. pytest -q backend/tests
BACKEND_RESULT=919 passed, 33 skipped, 4 warnings in 419.43s
BACKEND_BASELINE=912 passed, 33 skipped, 4 warnings at Prompt 02 seal; delta is the 7 focused P03 tests

FRONTEND_COMMAND=npm run build && npm test -- --run
FRONTEND_BUILD=PASS
FRONTEND_TESTS=21 files passed, 114 tests passed

STATIC_COMMAND=python3 -m compileall ... && git diff --check
STATIC_RESULT=PASS
BICEP_RESULT=PASS for the four infrastructure templates; only pre-existing no-hardcoded-env-urls warnings and Bicep update notices
PIP_AUDIT_RESULT=PASS; no known vulnerabilities
NPM_AUDIT_RESULT=PASS for high/critical threshold; 2 moderate @vitest/mocker advisories remain unchanged from P02

STORAGE_COMMAND=STORAGE_CONTRACT_PROVIDER=smb ... pytest -q backend/tests/test_binary_store_contract.py backend/tests/test_smb_integration.py
STORAGE_RESULT=8 passed, 1 warning in 10.82s
STORAGE_FIXTURE=isolated synthetic Samba container; no real DSM/Synology data used

ALEMBIC_COMMAND=PYTHONPATH=. alembic heads
ALEMBIC_RESULT=intelligence_v1_shared_contracts (one head)
MIGRATION_RESULT=no migration added; active migration inventory unchanged
REGRESSION_RESULT=PASS; no unexplained backend regression
```

The first storage launch attempt was a disposable harness startup conflict and was cleaned up by exact container/network name. The successful retry above is the storage gate result.
