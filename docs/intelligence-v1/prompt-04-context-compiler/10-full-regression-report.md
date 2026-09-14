# Prompt 04 full regression report

```text
IMPLEMENTATION_SHA=fb5702f97daa2d1c6f5cc875b7aca0ab76d4f25d
IMPLEMENTATION_TREE=78c5555387a70722712e3f872fe7d24128a154fa

BACKEND_COMMAND=PYTHONPATH=. pytest -q backend/tests
BACKEND_RESULT=946 passed, 33 skipped, 4 warnings in 1186.29s (0:19:46)
BACKEND_BASELINE=919 passed, 33 skipped, 4 warnings at Prompt 03 seal; no previously passing test failed

FRONTEND_COMMAND=npm run build && npm test -- --run
FRONTEND_RESULT=PASS from a clean temporary checkout of implementation commit A
FRONTEND_BUILD=PASS
FRONTEND_TESTS=21 files passed, 114 tests passed

POLICY_SECURITY=PASS
STATIC_DIFF_CHECK=PASS: Python compileall and git diff --check
BICEP_VALIDATION=PASS: four accepted templates; only pre-existing linter/update warnings
PIP_AUDIT=PASS: no known vulnerabilities
NPM_HIGH_CRITICAL_AUDIT=PASS: two unchanged moderate @vitest/mocker advisories remain
STORAGE_CONTRACT=8 passed, 1 warning
ALEMBIC_HEAD_COUNT=1
ALEMBIC_HEAD=intelligence_v1_shared_contracts
MIGRATION_ADDED=false
MIGRATION_DIFF_FROM_P03=NONE

REAL_DATA_USED=false
REAL_AMEC_BUSINESS_CONTENT_USED=false
REAL_DSM_BUSINESS_CONTENT_USED=false
PRODUCTION_MUTATED=false
DEPLOYMENT_PERFORMED=false
```

The working checkout also contains unrelated untracked proposal UX files from another workstream. They were not staged, edited, or removed; the clean frontend checkout was used to isolate the P04 regression result without discarding those artifacts.
