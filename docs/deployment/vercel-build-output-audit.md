# Vercel build output audit

The final audit was run from `backend/` with Vercel CLI 58.9.0 and `uv` 0.12.3:

```text
npx vercel build --yes --output .vercel-output-audit-3
status: ok
message: Build completed successfully.
```

The build detected FastAPI, used Python 3.14 from `pyproject.toml`, and
installed the declared runtime dependencies successfully.

The Build Output API emitted:

```text
.vercel-output-audit-3/functions/fastapi.func/.vc-config.json
.vercel-output-audit-3/functions/fastapi.func/vc__handler__python.py
```

The function configuration resolved to:

```json
{
  "handler": "vc__handler__python.vc_handler",
  "runtime": "python3.14",
  "filePathMap": {
    "app/main.py": "backend/app/main.py"
  }
}
```

The generated handler identifies `app.main` and the `app` variable. No `.py`
files were emitted under `.vercel-output-audit-3/static/`; the only generated
Python handler is inside the Python function bundle.

The pre-fix build is also documented by its generated `builds.json`: framework
detection was skipped and only `@vercel/static` was selected. After adding the
backend-local framework pin, the build selects `@vercel/python` with
`framework: "fastapi"` and emits `fastapi.func`.

`VERCEL_BUILD_PYTHON_FUNCTION_EMITTED`

`PYTHON_STATIC_DOWNLOAD_BUG_FIXED`
