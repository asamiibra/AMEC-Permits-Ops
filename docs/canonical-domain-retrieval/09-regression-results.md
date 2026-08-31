# Regression results

Focused implementation proof:

```text
pytest -q backend/tests/test_canonical_domain_retrieval.py
3 passed, 1 warning
```

The complete backend regression is run after this artifact is staged; this
file records the result without weakening or removing existing tests.

Complete backend regression:

```text
pytest -q backend/tests
231 passed, 15 skipped, 2 warnings
```

Frontend consumer regression:

```text
npm test -- --run
13 test files passed; 37 tests passed
```

Frontend dependencies were installed from the committed lockfile only; no
source or lockfile changes were made.

Touched consumer families remain covered by the existing suite, including
Dashboard/master content, Dashboard V2 governance, Administration contract
projections, source intake, week-2 evidence verification, storage abstraction,
RBAC, and shared-domain workflows.
