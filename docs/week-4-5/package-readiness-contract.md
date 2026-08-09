# Package Readiness Contract

`POST /api/projects/{id}/readiness/evaluate` returns `READY`, `READY_WITH_NONBLOCKING_WARNINGS`, or `BLOCKED` with explicit category, severity, reason, evidence refs, and related entity refs. Current VerifiedAssertions, approved non-expired versions, current dependencies/credentials, multi-owner shares, and drawing controls are evaluated deterministically.
