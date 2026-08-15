# Local Samba lab

`dev/storage-lab` builds a pinned Debian/Samba endpoint with guest access
disabled, SMB2+ only, signing required, authenticated synthetic users, the
canonical `ProposalOpsLab` share and legacy-shaped compatibility shares.

The lab is an SMB contract endpoint, not a Synology emulator. It may emit
`SMB_STORAGE_CONTRACT_VERIFIED` after the complete protocol suite passes; it
cannot emit any DSM or Owner verification token.
