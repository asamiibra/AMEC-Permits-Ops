# v1.4 entry baseline

Scope is the attached v1.4 reconciliation prompt, the supplied disposition manifest, and `/Users/ahmedsami/Downloads/FORME.zip`. The Owner Dashboard remains the existing simplified Forms / Reports / Engineering Works / Definitions surface; no Source Intake UI was added.

- Branch: `branch/owner-form-simple-dashboard`
- Entry commit: `076d834d8ab41049081b3f0481aaaadad4e30e75`
- Existing remote: `origin/branch/owner-form-simple-dashboard`
- Existing main reference: `origin/main` at `7a923fb875de8a46d94699280ef90eb012fedcf1`
- Existing v1.3 foundation: provider-neutral binary store, real SMB contract, verified document storage journal/outbox, Master Content integration, needs-review overlay and resolver exclusion.
- Existing pre-task worktree changes preserved: the tracked Excel fixture modification and the previously present fixture deletions/operating-guide image change were not reset or included in this implementation.
- Docker Samba lab was available on `127.0.0.1:1445`; PostgreSQL 16 was available through Docker Compose.
- Migration target after this work: `0058_source_intake_ledger`.

The v1.4 delta is hidden/durable source intake: batch and item identity, bounded ZIP observation, exact manifest reconciliation, explicit source-gap rows, separated managed/external SMB roles, and copy-only promotion through the existing verified storage path.
