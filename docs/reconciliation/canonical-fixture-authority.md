# Canonical Fixture Authority

| Field | Authority |
|---|---|
| Fixture name | `PermitOps_Synthetic_MVP_Dataset_v1` |
| Version | `1.1.1` controlled patch successor |
| Manifest source | `backend/app/fixtures/canonical.py` |
| Manifest hash | `b3a5fbee1a968e3740801b0b696b31a39a3a907437f2377fcdfdfad3bb3546cb` |
| Import/seed method | `backend.app.seed.cli.seed`; `make canonical-fixture-check` |
| Primary projects | `GHCE-2026-0142`, `GHCE-2026-0187`, `GHCE-2026-0210`, `GHCE-2026-0244` |
| Applications | `GHCE-APP-0142`, `GHCE-APP-0187`, `GHCE-APP-0210`, `GHCE-APP-0244` |
| Workbook | `mock-systems/excel/permit_tracker.xlsx` |
| Synology mock root | `mock-systems/synology/2026/GHCE-2026-*` |
| Document corpus | `synthetic-data/documents/week2` plus canonical Synology sample roots |
| Users/roles | Synthetic owner, champion, steward, engineer, preparer, Final Submitter, admin |
| Portal simulator | `Permit Authority Simulator`; draft/save/reopen/precheck state only |

The database registry enforces one `golden_path_authority = true`. Legacy identifiers have explicit `LegacyFixtureAlias` rows and are not used by canonical E2E/golden-path reports. Every Golden Path report prints this fixture identity and hash.
