# Focused tests

Against implementation SHA `b21ab2fe5e30e306a9bc40149ba10324f0bebd9b`:

- P07 control plane: 5 passed.
- P05/document/intelligence contracts: 19 passed in SQLite and 24 passed in PostgreSQL 16.15 qualification.
- Frontend: 22 files and 126 tests passed; production build passed.
- Storage/Samba: 17 passed in the accepted unchanged storage proof; no storage paths changed in the candidate.
- Full backend: 957 passed, 19 governed skips, 0 failures with exact 976-node coverage.

The full machine-readable regression evidence is in `21`–`26` of this
directory.
