# Full regression report

The Prompt 02 exit gates completed on the isolated feature worktree. Results do not represent synthetic fixtures as real AMEC or DSM/Synology data.

```text
BACKEND=912 passed, 33 skipped, 4 warnings
FRONTEND_BUILD=PASS
FRONTEND_TESTS=21 files, 114 tests passed
STATIC_COMPILE_AND_DIFF_CHECK=PASS
BICEP_BUILD=PASS (pre-existing no-hardcoded-env-urls warnings)
PIP_AUDIT=PASS (no known vulnerabilities)
NPM_AUDIT=PASS at high/critical threshold; 2 moderate @vitest/mocker advisories remain
STORAGE_LAB=8 passed, 1 warning
```

The storage suite ran against the repository's synthetic Samba lab through a uniquely named isolated Docker invocation because the host lacks a working Compose plugin. It was torn down afterward. No real Synology/DSM endpoint, production traffic, production database, or real AMEC content was accessed.
