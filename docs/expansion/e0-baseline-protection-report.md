# E0 baseline protection report

The pre-E1 permit regression was executed before schema changes: backend SQLite regression was 57 passed; PostgreSQL 16 was available with the accepted pre-G10 database at migration `0015_week14_acceptance`; canonical fixture validation and prior Golden Path/acceptance evidence were already recorded as passing in the repository artifacts.

The repository has no `.git` metadata, so commit or working-tree state cannot be claimed. The runtime `permitops.db` was at migration `0006_confirmation_binding`, while repository migration head was `0015_week14_acceptance`; this discrepancy is recorded, not hidden. E1 adds migration `0016_stage1_v2_6_expansion_foundation` and preserves the historical migration chain.

E0 registry validation is executable in `backend/app/expansion/governance.py` and `backend/tests/test_expansion_e0_e1.py`. The original A12 file remains separate at exactly 20 rows; A12B has exactly 40 owner-session IDs; A15 has exactly 18 controlled clarifications.
