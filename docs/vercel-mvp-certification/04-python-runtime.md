# Python runtime

Build logs selected Python 3.12, installed dependencies from `uv.lock`, imported the FastAPI application, and completed the build-time schema bootstrap. The backend health endpoint returned HTTP 200 from production.

The local post-change Python compile check passed for all changed Python files. The full isolated PostgreSQL regression passed: 236 passed, 6 skipped.
