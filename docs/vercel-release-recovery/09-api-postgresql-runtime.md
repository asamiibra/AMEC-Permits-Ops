# API and PostgreSQL Runtime

Not executed against a new release because quota blocked deployment before a deployment ID existed.

The backend regression gate passed locally: `228 passed, 14 skipped, 2 warnings`. The local API/database test process used its existing isolated test setup; it is not deployed-runtime evidence.

Historical repository evidence and current code classify the intended Vercel MVP runtime as PostgreSQL-backed and synthetic-only when configured with the required backend environment variables. This is not new deployment proof.

```text
VERCEL_API_HEALTH_PASS=0
VERCEL_PERSISTENT_DB_POSTGRESQL=0
VERCEL_POSTGRES_CONNECTIVITY_PASS=0
VERCEL_COLD_WARM_SMOKE_PASS=0
VERCEL_POSTGRES_RECONNECT_PASS=0
VERCEL_BOUNDED_CONCURRENCY_PASS=0
VERCEL_DURABLE_SQLITE_USAGE_COUNT=UNSET
VERCEL_DURABLE_TMP_USAGE_COUNT=UNSET
LOCAL_BACKEND_REGRESSION_PASS=1
```
