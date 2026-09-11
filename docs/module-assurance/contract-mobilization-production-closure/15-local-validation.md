# Local validation

Focused affected run after CM-G16 hardening: `33 passed, 1 warning in 86.12s`.
SQL portability/runtime suite: `77 passed, 17 skipped, 1 warning in 58.43s`.
Frontend Vitest: `21 files, 113 tests passed`; production build passed with
TypeScript compilation; focused Contract browser E2E: `1 passed`.

`git diff --check` and Python compilation passed. Reachable refs and trees are
intact. `git fsck --full --no-reflogs --unreachable` reported two dangling blobs
that are recognizable prior source/test content; no reachable corruption was
found. The full backend suite remains governed by CI.
