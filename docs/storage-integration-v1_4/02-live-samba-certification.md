# live Samba certification

The real SMB contract ran against the Docker Samba server over TCP port 1445 with SMB signing required. `make storage-contract` completed with 12 passing tests. Coverage includes authentication, read/write/readback, temporary cleanup, range read, missing object/share, read-only and denied credentials, deletion detection, and concurrent provider instances.

The added role test verified `ProposalOpsManaged` is writable by `proposalops_rw` and `OwnerExternal` is healthy but write-denied for `external_ro`. This is a local Samba lab result only; it is not Synology certification.
