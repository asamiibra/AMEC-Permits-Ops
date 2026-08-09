# Fixture Universe Inventory

| Source | Examples | Classification | Rule |
|---|---|---|---|
| Canonical manifest/seed | `PermitOps_Synthetic_MVP_Dataset_v1` v1.1.1; `GHCE-2026-*` | `CANONICAL_E2E` | Sole E2E/golden-path authority |
| Canonical workbook | `mock-systems/excel/permit_tracker.xlsx` with GHCE rows | `CANONICAL_E2E` | Workbook row identity is linked through `ExcelProjectRow` |
| Canonical Synology roots | `mock-systems/synology/2026/GHCE-2026-*` | `CANONICAL_E2E` | Synthetic folder/template evidence only |
| `synthetic-data/documents/week2` | Arabic, degraded OCR, wrong-project and expired-NOC cases | `LEGACY_UNIT_TEST_ONLY` / scoped spike corpus | Not a package/golden-path authority unless explicitly named by the manifest |
| `mock-systems/synology/2026/PRJ-*` | Al Noor, West Bay, Lusail, Pearl legacy roots | `DEPRECATED` | Retained for historical inspection only |
| `tmp/permitops-sheet-builder.mjs` | PRJ/REQ demo rows | `DEPRECATED` | Not executable E2E evidence |
| Legacy IDs | `PRJ-2026-*`, `REQ-DEMO-*` | `LEGACY_MUST_MIGRATE` | Explicit mapping exists in `LegacyFixtureAlias`; no canonical E2E use |
| `N/2026/` | No active source found | `UNKNOWN_REVIEW_REQUIRED` | No E2E or Golden Path depends on it |

The migration map is explicit, not a hidden alias: old project/application identifiers map to their GHCE successors for historical unit-test interpretation only.
