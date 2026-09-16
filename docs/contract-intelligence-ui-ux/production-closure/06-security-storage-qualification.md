# Security and storage qualification

`CANDIDATE_SHA=c10e3aac0c47d9d158fffe65b89b5b3ce7fe1cc9`
`CANDIDATE_TREE=d0e4ad97b95fa85cfa7e8149c4640bc07f7f0051`
`MAIN_SHA=594b313a15cc6ade3f0505de395a5817c6337268`
`COMMAND=compileall; focused storage/security tests; read-only code inspection`
`ENVIRONMENT=local synthetic test harness`
`DB_ENGINE=SQLite focused harness; PostgreSQL storage proof retained for predecessor`
`RESULT=PARTIAL`
`REAL_AMEC_DATA_USED=false`

The upload boundary is implemented before `DocumentVersion` persistence: bounded read, safe basename, MIME allowlist, magic validation, and production fail-closed scanner requirement. Existing storage-focused tests had passed on the predecessor candidate, but the scanner integration, Samba round-trip, and current-head full matrix are not proven here.
