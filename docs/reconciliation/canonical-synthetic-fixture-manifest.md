# Canonical Synthetic Fixture Manifest

This is the machine-readable manifest companion to `backend/app/fixtures/canonical.py`.

| Property | Value |
|---|---|
| Fixture set | `PermitOps_Synthetic_MVP_Dataset_v1` |
| Controlled successor version | `1.1.1` |
| Manifest hash | `b3a5fbee1a968e3740801b0b696b31a39a3a907437f2377fcdfdfad3bb3546cb` |
| Source path | `backend/app/fixtures/canonical.py` |
| Import method | deterministic `seed_reconciliation()` / isolated database seed |
| Workbook | `mock-systems/excel/permit_tracker.xlsx` |
| Synology root | `mock-systems/synology` |
| Portal simulator | Permit Authority Simulator |
| Evidence class | `SYNTHETIC_IMPLEMENTATION_EVIDENCE` |

Canonical projects are `GHCE-2026-0142`, `GHCE-2026-0187`, `GHCE-2026-0210`, and `GHCE-2026-0244`; applications are the corresponding `GHCE-APP-*` identities. The manifest also contains the controlled document corpus, workbook human-owned sheets and projection sheet, portal fixture categories, forms, synthetic user/role identities, and explicit legacy aliases.

The invariant is one active `golden_path_authority`; legacy IDs are compatibility/unit-only references and are not Golden Path identities.
