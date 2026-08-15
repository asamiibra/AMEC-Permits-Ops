# v1.4 reconciliation

| Requirement | Existing state | v1.4 disposition |
|---|---|---|
| Durable batch/item ledger | Existing ProposalIntakeArtifact was opportunity-scoped and not a complete archive ledger | Added `SourceIntakeBatch` and `SourceIntakeItem`; identity is batch + ordinal + original path |
| Safe archive handling | No bounded non-extracting reader | Added `BoundedZipReader` with path, count, size, ratio, encryption, symlink, collision and nested-archive guards |
| Exact disposition | No generic one-row-per-observation disposition path | Manifest application rejects count, path, or hash omissions/mismatches |
| Managed promotion | Existing Master Content SMB protocol | Reused `create_master_content` and `DocumentStorageService` for verified temp/write/readback/finalize/readback |
| Needs Review | Existing owner overlay and consumer exclusion | Intake sets `needs_review=true`; normal resolver behavior remains unchanged |
| External source | One configured SMB provider | Added separate external source configuration and mutation-detecting stable read helper |
| Root roles | Existing lab had one ProposalOpsLab share | Added `ProposalOpsManaged` RW and `OwnerExternal` RO identities/shares |
| Owner surface | Simplified dashboard already present | Preserved; no source-intake UI or extra navigation was added |

No Synology, Owner production, or production authority claim is made by local evidence.
