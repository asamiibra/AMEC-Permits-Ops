# Local validation

Focused affected run after closure changes: `31 passed, 1 warning in 127.06s`.
Frontend Node 22 Vitest: `21 files, 113 tests passed`; production build passed
with TypeScript compilation; focused browser E2E: `1 passed`.

`git diff --check` and `git fsck --full` passed. The full backend suite was not
treated as locally authoritative after the host terminated the resource-
intensive run; governed CI is required.
