# Production cutover

Cutover requires `STORAGE_PROVIDER=smb`, a private TCP/445 route, approved
service identity/share/root, explicit SMB security and direct-edit policy,
cross-system restore runbook, bounded reconciliation, load baseline and
Owner-controlled write evidence. Rollback is application/config rollback;
there is no mock or local-disk durable fallback.
