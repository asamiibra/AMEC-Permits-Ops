# Browser E2E evidence

Status: `PASS` — 14 Chromium scenarios passed.

Evidence class: `SYNTHETIC_IMPLEMENTATION_EVIDENCE`.

The suite uses the active canonical fixture authority in its route fixtures: `PermitOps_Synthetic_MVP_Dataset_v1`, version `1.1.0`, hash `f5eaaf110015e50c5bd8349658e42b3afbc07500199a47b05d45b206c08be08d`. No authority website, client credential, or production data is contacted.

| Test | Canonical project/application | Control proven | Result | Failure artifact |
|---|---|---|---|---|
| E2E-01 | `GHCE-2026-0142` / `GHCE-APP-0142` | Bootstrap/project/application identity | PASS | none |
| E2E-02 | canonical dashboard | Package `BLOCKED` and exact blocker | PASS | none |
| E2E-03 | `GHCE-2026-0142` | Assisted municipality mismatch visible | PASS | none |
| E2E-04 | `GHCE-APP-0142` | Finding → task → notification state | PASS | none |
| E2E-05 | canonical revision | Stale package/preparation denial | PASS | none |
| E2E-06 | canonical Arabic synthetic evidence | RTL and LTR identifier preservation | PASS | none |
| E2E-07 | canonical operator surface | No final-submit capability | PASS | none |
| E2E-08 | `GHCE-APP-0142` | Monitoring `NO_CHANGE` evidence | PASS | none |
| E2E-09 | `GHCE-APP-0142` | Drift fail-closed/manual fallback | PASS | none |
| E2E-10 | canonical revision | MFA metadata and human handoff boundary | PASS | none |
| E2E-11 | returned synthetic finding | Deterministic recurrence-after-closure | PASS | none |
| E2E-12 | canonical acceptance surface | Week 14 acceptance/G10 separation | PASS | none |
| Existing canonical controls | `GHCE-2026-0142` | Project and safety boundary | PASS | none |
| Existing control boundary | synthetic operator surface | Human-only final action | PASS | none |

Command: `make pre-g10-reconcile` or `cd frontend && npm run browser-e2e`.
