# Prompt 1 source-workspace closure

The closure slice is implemented on `feature/proposals-v1-synology-454`.

The source workspace uses `MountedProposalSource` with a configured absolute
root and server-side path-bound IDs. Six authenticated routes provide project
discovery, recursive tree metadata, file metadata, inline content, download,
and idempotent sync. Capture performs stat/read/hash/stat through the existing
read-only adapter and persists immutable `DocumentVersion` records using the
existing Document/DocumentVersion tables; unchanged hashes are skipped.

The committed deterministic fixture includes the exact expected 454 folder
names, representative root files, nested content, and a `520 - Future Draft`
source project. The fixture is source-only: sync creates no Proposal and runs
no AI. There is no route that writes to the source root.

The browser source workspace is reachable from the Proposals register. It
shows project state badges, the exact breadcrumb and names, folder selection,
View/Download actions, native image/PDF previews when bytes are valid, and a
truthful download path for other file types.

Qualification completed: 60 focused backend tests and OpenAPI route checks pass;
fixture discovery reports 454 and 520 with 20 recursive 454 entries. Native
PostgreSQL, real Synology, and full browser E2E were unavailable in this
executor, so those gates remain explicitly unqualified. No migration was added.
