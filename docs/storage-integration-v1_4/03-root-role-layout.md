# root and role layout

The lab now contains:

- `ProposalOpsManaged`: application-managed binary destination, writable only by `proposalops_rw`.
- `OwnerExternal`: owner/external source observation share, read-only to `external_ro`.
- `ProposalOpsLab`: retained for the v1.3 contract and compatibility checks.

The external settings are separate from the managed settings (`SMB_EXTERNAL_*`). The external helper only reads a stable source and compares stat metadata before and after the read; it never promotes by moving or renaming the source.
