# Source connector boundary

Implemented, isolated and not API-wired: `MountedProposalSource` is a POSIX mounted-volume source adapter. It has no write, rename, delete, mkdir or cleanup operation. All opens use read-only flags. Child resolution uses dirfd plus O_NOFOLLOW, including the final file, to avoid symlink check/open races. No credentials or source-system calls were made.

It consumes a server-configured physical root corresponding to `Tenders/1- Proposal/2026`. This is not arbitrary NAS browsing. Destination capture must use existing DocumentStorageService; this adapter does not create a competing byte store.

Live connector configuration, existing SMB integration, sync job persistence, storage publication and HTTP authorization remain unimplemented. Capability absence and fixture file hashes/mtime were tested; no live NAS was available for independent server audit.

SYNOLOGY_WRITE_COUNT=0
LIVE_SYNOLOGY_SYNC=false
