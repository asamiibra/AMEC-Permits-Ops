# Cross-Module Regression

Focused Content Library acceptance: `44 passed, 1 skipped`.

Fresh isolated seam checks:

- BD Forms v2 acceptance: `1 passed` using `/tmp/cl-cross-bd-fresh-20260911-a.db`.
- Permit transition/manual-source/lineage: `1 passed` using `/tmp/cl-cross-contract-isolated.db`.
- BD final hardening: `1 passed` using `/tmp/cl-cross-bd-hardening-isolated.db`.

An earlier rerun against a reused SQLite file failed because stale `F-0003/F-0004` rows had dangling current-version pointers. That was confirmed as test-database contamination; the fresh isolated rerun passed. The full broad suite result was `79 passed, 7 skipped, 2 failed` only when that reused contaminated fixture was included. This condition is recorded for test hygiene and is not a Content Library product gap.

No cross-module implementation was committed to `next/module-integration`.
