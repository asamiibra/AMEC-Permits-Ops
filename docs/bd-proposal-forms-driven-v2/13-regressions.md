# Regression matrix

Status: `PROTECTED_AND_REGRESSION_VERIFIED`

| Gate | Result |
|---|---|
| Fresh SQLite migration round-trip 0041 → 0042 → 0041 → 0042 | pass; final head 0042 |
| Full SQLite backend suite | 154 passed, 1 skipped, 2 warnings |
| Full PostgreSQL backend suite | 155 passed, 2 warnings |
| Focused BD Forms-driven v2 PostgreSQL suite | 2 passed, 1 warning |
| Frontend unit suite | 12 files, 32 tests passed |
| Production build | passed; existing chunk-size advisory only |
| Real-stack current browser checks | 5 passed, serial workers=1 |
| Dashboard V1/V2 seam | passed |
| Admin Contract / shared-domain regressions | included in full PostgreSQL suite; passed |

SQLite skip adjudication: `test_dashboard_master_content_v2.py:91` is a PostgreSQL row-locking concurrency proof and is `NOT_APPLICABLE_PROVEN` for SQLite; the same full suite on PostgreSQL passed with no skip.
