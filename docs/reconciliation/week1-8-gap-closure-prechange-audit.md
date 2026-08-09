# Weeks 1–8 Integrity Reconciliation — Pre-change Audit

> Audit type: read-only repository inventory before reconciliation changes.
> Evidence class: `SYNTHETIC_IMPLEMENTATION_EVIDENCE`.
> This document records the state that existed before the gap-closure work. It
> is not a replacement for the historical Week 1–8 reports.

## Audit scope

Inspected the repository tree, Week 1–9 reports and contracts, reconciliation
artifacts, Stage 2 and Sign-off C records, fixture/seed sources, backend models,
services, routes, tests, Alembic revisions, frontend routes/tests, README and
the native PostgreSQL validation path. Week 9 implementation was inventoried
but is not used as evidence for missing Week 6 acceptance.

## Repository baseline

| Area | Pre-change evidence | Finding |
|---|---|---|
| Backend | `backend/app`, `backend/tests`, Alembic revisions `0001`–`0009` | Modular monolith with Week 1–9 domain surfaces present |
| Frontend | `frontend/src`, `frontend/tests/app.test.tsx` | Operator console present; only one frontend smoke test existed |
| Database target | Native PostgreSQL 16.14 at localhost:5432, database `permitops_test` | PostgreSQL is available and is the target validation runtime |
| Fast test database | SQLite test fixture in `backend/tests/conftest.py` | Useful for unit/regression feedback; not the target integrity proof |
| Migration head | `0009_week9_attachment_grid_hardening` | Week 9 is already present and must remain intact |
| Existing backend baseline | Historical Week 8 report: SQLite 45 passed; PostgreSQL 45 passed | Re-run required after reconciliation |
| Existing frontend baseline | `frontend/tests/app.test.tsx`: one test; production build reported passing | Evidence is materially too thin for the control-heavy workflow |

## Fixture identity inventory

| Source | Identifiers observed | Pre-change classification |
|---|---|---|
| `backend/app/fixtures/canonical.py` | `PermitOps_Synthetic_MVP_Dataset_v1`, version `1.0.0`, hash `1a4a125708a6ffb983910b7860135cd0a6eba64d360d16d62920cd44966b00fe` | Intended canonical authority, but its project/application universe still used legacy `PRJ-2026-*` / `REQ-DEMO-*` identities |
| `backend/app/seed/cli.py` | `PRJ-2026-001`…`004`; `REQ-DEMO-1001`…`1004` | Legacy seed used by package, Week 5, Week 7 and Week 8 flows; split-brain risk |
| `backend/app/services/canonical_workbook.py` and `mock-systems/excel/permit_tracker.xlsx` | `PRJ-2026-001`…`004`; project names Al Noor Villa, West Bay Residence, Lusail Office Annex, Pearl Community Clinic | Legacy workbook/project rows |
| `mock-systems/synology/2026/PRJ-2026-*` | Four legacy project roots and sample PDFs | Legacy mock Synology corpus; not safe as the sole canonical E2E authority |
| `tmp/permitops-sheet-builder.mjs` | `PRJ-2026-*`, `REQ-DEMO-*` | Legacy/demo artifact; not a valid E2E authority |
| `synthetic-data/documents/week2` | Scoped document corpus including West Bay and Arabic/degraded cases | Scoped unit/spike corpus; requires explicit unit-only or canonical mapping |
| `GHCE-2026-*` | No authoritative active manifest/seed universe found | Required canonical successor identity was absent pre-change |
| `N/2026/` | No active source found in the repository inventory | No canonical authority found |

The canonical target required by this reconciliation is the existing fixture
set name with a controlled manifest successor containing primary identities
`GHCE-2026-0142`, `GHCE-2026-0187`, and `GHCE-2026-0210` (plus any explicitly
manifested supporting case). Legacy identifiers may remain only in tagged
unit/scoped fixtures or in an explicit migration map.

## E2E and Golden Path evidence

| Required evidence | Pre-change state |
|---|---|
| Week 4 package/readiness | `backend/tests/test_week45.py`; helper selected `PRJ-2026-001` |
| Week 5 assisted municipality | Same test; package → revision → simulator save/reopen → mismatch → match → precheck → session → handoff |
| Standalone Week 6 Golden Path v1 | Missing. Week 5 report said `READY_FOR_WEEK6_GOLDEN_PATH`; Week 7 entry gate explicitly carried that evidence forward |
| Week 7 finding/task/notification | `backend/tests/test_week7.py`; helpers selected `REQ-DEMO-1001/1002` |
| Week 8 staleness/lineage | `backend/tests/test_week8.py`; helper selected `PRJ-2026-001` |
| Fixture authority enforcement | `SyntheticFixtureSet` existed, but no repository-wide E2E inventory/check command or uniqueness invariant was present |
| Machine-readable Golden Path report | Missing |

## Week 3, Stage 2 and Sign-off C status

- `docs/week-3/stage2/stage2-baseline.json`: version `1.0`, status `DRAFT`,
  synthetic-only, `real_data: false`, municipality submission excluded.
- `docs/week-3/signoff-c-draft.md`: draft only; no executed contract, payment,
  client acceptance, production credentials or external integration.
- `docs/week-3/phase0-close-report.md`: recommendation is `PAUSE` for
  real-data progression; client approval is absent.
- `docs/week-3/adjudication-summary.md`: 15 cases, 13 adjudicated, one
  disputed and one in review in the historical report.
- `docs/week-3/tier1-resolution-log.md`: attachment applicability, data access
  and professional-responsibility boundaries remain open in the historical
  record.
- `docs/week-3/stage2/open-conditions.md`: data access, responsible engineer,
  attachment applicability, real-document evidence, hosting/security and
  municipality behavior remain open.
- A `Stage2ReviewAcknowledgement` model existed, but no reviewer
  acknowledgement endpoint/UI was found in the pre-change route inventory.

Resulting governance truth before changes: synthetic development could be
active; formal client build and live production were not evidenced as
authorized. No signed approval, approved real-data path, accepted client
responsibilities or G10 live authorization was found.

## Traceability inventory

Existing Week 4–5, Week 7 and Week 8 matrices used abbreviated/reassigned
requirement descriptions and statuses. The older
`docs/reconciliation/twenty-requirement-traceability.md` also treated several
requirements scheduled for Weeks 4–8 as later work. An authoritative exact
20-row A12 registry and corrected Week 1–8 matrix were therefore missing.

## Configuration and lineage inventory

Week 8 already contained `LineageEdge`, `MaterialChangeEvent`, stale reasons,
validity records and bounded impact services. Configuration models exposed
versions in places such as `ScenarioConfig`, `TargetRenderingRule` and
`ConfigurationChangeImpactPolicy`, but consequential configuration identity was
not a consistent stable-id/version/checksum contract. `PreparationRevision`,
readiness/package records, render outputs, municipality intended state,
precheck context and `FindingCode` did not all retain one reconstructable
configuration bundle identity.

## Migration and warning inventory

- Revision `0003_phase0_week3_decision_layer` downgrade removed only the
  `raid_items.phase0_close_impact` column; it did not remove the Week 3 tables
  created by the model metadata path.
- Revision `0004` had an explicit downgrade for its own tables, but the Week 3
  boundary roundtrip had not been validated as a complete upgrade → downgrade
  → re-upgrade path.
- The backend baseline had a pytest-asyncio deprecation warning in the test
  output. Its exact source/configuration needed confirmation rather than broad
  suppression.

## Safety and capability inventory

The pre-change routes and UI explicitly represented assisted/mock authority
operations, attended MFA/session state, confirmation evidence and human
handoff. Existing tests asserted that `/api/findings/{finding_id}/close` and a
machine final-submit operation were absent. The reconciliation must re-run the
search/audit and must not introduce submit, payment, signature, stamp,
certification, autonomous professional approval, unrestricted browser-agent or
real Ministry write capability.

## Required repairs identified

1. Establish one canonical fixture manifest/registry and migrate all
   integration/golden-path references to it while retaining only explicitly
   tagged legacy unit fixtures.
2. Execute and accept a standalone Week 6 Golden Path v1 with machine-readable
   identifiers and shadow/agreement evidence.
3. Publish the synthetic/formal/live governance boundary and visible status.
4. Create the exact A12 20-requirement registry, corrected notice and Week 1–8
   matrix.
5. Disposition every historical Week 3 open item and Week 6 blocker without
   treating external conditions as synthetic resolution.
6. Add stable configuration bundle/checksum/version bindings and bounded
   material-change lineage.
7. Expand frontend control evidence and focused browser-like flow coverage.
8. Resolve/supersede the Week 1 project-start finding, add Stage 2 reviewer
   acknowledgement if still absent, repair migration roundtrip integrity, and
   address the pytest warning without broad suppression.

No implementation or historical report was modified in producing this audit.
