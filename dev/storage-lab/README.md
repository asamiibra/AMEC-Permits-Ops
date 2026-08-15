# ProposalOps local SMB integration lab

This is a reproducible, synthetic Samba endpoint for Level 1 SMB contract
certification. It is not a Synology emulator and it does not establish DSM or
Owner-Synology parity.

Start it with:

```sh
docker compose -f dev/storage-lab/docker-compose.storage.yml up --build -d
```

The host endpoint is `127.0.0.1:1445`; the service endpoint from another
container on `proposalops-storage-net` is `samba:445`. The canonical test
share is `ProposalOpsLab`. Legacy-shaped shares are included only to test
spaces and mapping behavior: `Marketing`, `pro`, `Tenders`, `Supervision`,
and `Services Provider`.

Synthetic credentials are defined in the compose file and must never be used
for Owner environments. Guest access is disabled. The provider must use SMB2
or SMB3, authenticated access, explicit timeout settings, and the same
write→fresh read-back→hash→no-replace finalize protocol used for Synology.

Required certification evidence is `SMB_STORAGE_CONTRACT_VERIFIED` and
`LOCAL_SAMBA_STORAGE_LAB_FROZEN`. This lab cannot emit
`SYNOLOGY_DSM_STORAGE_PARITY_VERIFIED` or any Owner/production token.
