# Contract Revisions and Authority

Contract revisions are append-only, current-revision pinned, and audit-backed. Authority review is explicit and role-controlled; Accept Contract is a separate owner action with current-revision/readiness checks and idempotent replay. Acceptance does not create a Project or Invoice.

The revision/authority, readiness, and acceptance paths passed the PostgreSQL targeted suite and the Contract browser detail checks. Official authority thresholds and signing policy are still Owner Input Required.

