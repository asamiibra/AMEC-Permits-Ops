# P04 regression report

| Check | Result |
| --- | --- |
| Frontend build | PASS (`npm run build`) |
| Frontend unit suite | PASS: 22 files, 126 tests |
| P04 focused unit suite | PASS: 12 tests |
| P04 browser suite | PASS: 3 tests |
| Exhaustive UI conformance crawl | PASS: 66 material routes, 312 route/persona/viewport results, all runtime gates green |
| Backend suite from repository root | PASS: 946 passed, 33 skipped, 4 warnings (`pytest -q backend/tests`, 22m50.97s) |
| Real-data path | not used |
| Production mutation | none |
| New provider / queue / UI database | none |

The first backend invocation from `backend/` was invalid for this repository because path-based integrity tests resolve paths from the repository root. The authoritative rerun from the repository root completed successfully: `pytest -q backend/tests` — 946 passed, 33 skipped, 4 warnings in 22m50.97s. The warnings were existing deprecation/SQLAlchemy seed integrity warnings; no test failures were reported.
