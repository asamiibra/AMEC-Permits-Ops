# Supported field and grid coverage

Status: `PASS` for the active synthetic supported scenario.

Evidence class: `SYNTHETIC_IMPLEMENTATION_EVIDENCE`.

Client-approved baseline: `NO`.

The deterministic check is `PYTHONPATH=. DATABASE_URL=<clean-seeded-db> python3 backend/scripts/supported_coverage_check.py`. It derives the active field inventory from `FieldDefinition` and the active municipality grid inventory from `MunicipalityConfig`; it does not maintain a second hand-written field list.

Required invariants:

```text
ACTIVE_SUPPORTED_FIELDS - FIELD_MATRIX_ROWS = 0
FIELD_MATRIX_ROWS - ACTIVE_SUPPORTED_FIELDS = 0
ACTIVE_SUPPORTED_GRIDS - GRID_MATRIX_ROWS = 0
GRID_MATRIX_ROWS - ACTIVE_SUPPORTED_GRIDS = 0
```

The check also verifies active Form, Excel, and Municipality `TargetRenderingRule` coverage for every active field. Allowed source distinctions remain explicit (`PORTAL_DERIVED` and `HUMAN_DECISION` are not silently treated as office truth).

The latest clean-seeded result is stored at `artifacts/pre-g10-supported-coverage.json` and records the scenario/config version, configuration checksum, field and grid counts, critical/form/Excel/municipality/dropdown/portal-derived/human-decision counts, missing/extra sets, rendering coverage, and fixture identity.
