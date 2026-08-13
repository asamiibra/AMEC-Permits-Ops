# Full Regression

| Gate | Result |
|---|---|
| Backend | `150 passed, 1 skipped, 2 warnings` |
| Frontend | `12 test files, 32 tests passed` |
| Production build | Passed (`tsc -b` and Vite build) |
| Focused real-stack browser | `3 passed` |
| Alembic heads | One head: `0036_dashboard_forms_governance_wave_a` |
| Migration downgrade | Not run; no downgrade was required or performed |
| Wave B implementation | Zero |
| Wave C implementation | Zero |

The build emitted only the existing large-chunk advisory; it did not fail.
