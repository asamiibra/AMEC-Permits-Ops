# Pre-G10 pre-change audit

Audit date: 2026-08-08
Audit class: `SYNTHETIC_IMPLEMENTATION_EVIDENCE`
Purpose: establish repository state before the pre-G10 reconciliation changes. This is an inventory, not a delivery report and not formal G10 evidence.

## Repository inventory

| Item | Observed state | Evidence |
|---|---|---|
| Migration head | `0015_week14_acceptance` | `alembic heads` |
| Canonical fixture | `PermitOps_Synthetic_MVP_Dataset_v1` | `backend/app/fixtures/canonical.py` |
| Fixture version/hash | `1.1.0` / `f5eaaf110015e50c5bd8349658e42b3afbc07500199a47b05d45b206c08be08d` | canonical manifest and existing reconciliation reports |
| Canonical projects | `GHCE-2026-0142`, `GHCE-2026-0187`, `GHCE-2026-0210`, `GHCE-2026-0244` | canonical manifest |
| Canonical applications | Corresponding `GHCE-APP-*` identities | canonical manifest |
| Golden Path v1 | Present; artifact reports PASS | `backend/scripts/golden_path_v1.py`, `artifacts/golden-path-v1-result.json` |
| Golden Path v2 | Present; artifact reports PASS | `backend/scripts/golden_path_v2.py`, `artifacts/golden-path-v2-result.json` |
| Week 9 report | Present; historical report says `READY_FOR_WEEK10` | `docs/week-9/week9-delivery-report.md` |
| Week 11 report | Present; historical report says `READY_FOR_WEEK12` | `docs/week-11/week11-delivery-report.md` |
| Week 12 report | Present; historical report says `READY_FOR_WEEK13` | `docs/week-12/week12-delivery-report.md` |
| Week 13 report | Present; historical report says `READY_FOR_WEEK14` | `docs/week-13/week13-delivery-report.md` |
| Week 14 report | Present; historical report says Wave 3 assisted review ready | `docs/week-14/week14-delivery-report.md` |
| Acceptance runner/result | Present; latest result PASS | `backend/scripts/acceptance_rehearsal.py`, `artifacts/week13-14-acceptance-result.json` |
| G10 evidence pack | Present; five indexed items | `docs/week-14/g10-evidence-pack/` |
| Browser E2E | 2 spec files / 2 scenarios before change | `frontend/browser-e2e/` |
| Component tests | 2 test files | `frontend/tests/` |
| Backend tests | 9 test modules; 56 passed in the pre-change SQLite run | `backend/tests/` |
| PostgreSQL test count | Existing Week 10–14 reports record 56 passed on clean PostgreSQL 16 | historical delivery reports |
| Current safety evidence | Acceptance artifact records no machine final submit and no live Ministry write | acceptance artifact |
| Stage 2 | `DRAFT` / reviewed where recorded, not approved | `docs/reconciliation/governance-status-reconciliation.md` |
| Sign-off C | `DRAFT`, unsigned | `docs/reconciliation/governance-status-reconciliation.md` |
| Formal build | `NOT_AUTHORIZED` / external | governance reconciliation |
| Live production | `NOT_AUTHORIZED` / external | governance reconciliation |
| Formal G10 | Absent; Week 14 explicitly did not run it | Week 14 evidence pack |
| Open P1/P2 | Synthetic defect ledger seeded closed with zero open P1/P2 | Week 14 seed and shadow defect evidence |
| Open control states | `NEEDS_REVIEW` exists as a legitimate engine outcome and is not yet dispositioned in a dedicated pre-G10 artifact | `backend/app/services/week10.py` |
| Supported fields | 14 active `FieldDefinition` records in the synthetic scenario seed | `backend/app/seed/cli.py` |
| Supported grids | 2 configured municipality grids: `buildings`, `floors` | `backend/app/seed/cli.py` |
| 20-requirement registry | YAML registry present with unique numbers 1–20 | `config/recording_fidelity_requirements_v2_5.yaml` |

## Pre-change findings

1. Browser evidence is below the requested minimum of seven meaningful browser scenarios.
2. Week 9–14 reports exist, but no independent pre-G10 execution package ties the historical reports to rerunnable commands and artifacts.
3. Week 10 matrix reports do not explicitly distinguish synthetic supported-scenario completeness from client-approved Stage 2 completeness.
4. The `NEEDS_REVIEW` control outcome has no dedicated actor/evidence/disposition record.
5. `field_coverage()` checks active database fields but hardcodes the grid count and does not prove bidirectional field/grid inventory equality.
6. The default `permitops.db` is an older SQLite schema; the raw script invocation without the repository runtime database setup fails on the missing `source_manifest_path` column. The final command must use a clean, migrated, seeded isolated database.
7. The canonical fixture check, coverage checks, safety search, independent week gates, browser suite, and final matrix need one native orchestration command.

## Evidence boundary

The active track remains `SYNTHETIC_DEVELOPMENT_PROTOTYPE`. `FORMAL_CLIENT_BUILD`, `LIVE_PRODUCTION`, approved real-data evidence, client workflow approval, and formal G10 remain external and are not changed by this reconciliation.
