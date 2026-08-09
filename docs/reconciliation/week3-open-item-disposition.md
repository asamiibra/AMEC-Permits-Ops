# Week 3 Open-Item Disposition

> Evidence class: `SYNTHETIC_IMPLEMENTATION_EVIDENCE` unless marked external.

## Historical adjudication items

| item_id | source_artifact | original_status | original_blocking_scope | disposition | evidence | resolved_by | resolved_at | synthetic_track_effect | formal_build_effect | remaining_action |
|---|---|---|---|---|---|---|---|---|---|---|
| ADJ-004 | `docs/week-3/adjudication-summary.md` | DISPUTED | Could affect a non-required document classification | `DEFERRED_PER_APPROVED_PLAN` | Canonical Week 6 contract does not use this disputed optional classification as golden truth; raw label remains in historical corpus | Requirement Steward | Reconciliation run | No synthetic Golden Path blocker | Not evidence of client truth | Adjudicate in expanded corpus before formal/real use |
| ADJ-012 | `docs/week-3/adjudication-summary.md` | IN_REVIEW | Poor/degraded document case outside required clean path | `DEFERRED_PER_APPROVED_PLAN` | Degraded keyed path is exercised separately; unresolved source label is not promoted to canonical verified truth | Document Steward | Reconciliation run | No synthetic Golden Path blocker | Real evidence remains blocked | Expand/adjudicate corpus later |

## Tier 1 conditions

| item_id | source_artifact | original_status | original_blocking_scope | disposition | evidence | resolved_by | resolved_at | synthetic_track_effect | formal_build_effect | remaining_action |
|---|---|---|---|---|---|---|---|---|---|---|
| T1-ATTACHMENT-APPLICABILITY | `docs/week-3/tier1-resolution-log.md` | OPEN | Formal attachment applicability | `BLOCKED_EXTERNAL_FORMAL_BUILD` | Synthetic category/checklist rules and Week 6 attachment path exist; no client/authority applicability approval | — | — | Synthetic path continues with explicit synthetic rules | Blocks approved-real/formal build | Obtain signed applicability decision |
| T1-DATA-ACCESS | `docs/week-3/tier1-resolution-log.md` | OPEN | Real data path/security | `BLOCKED_EXTERNAL_FORMAL_BUILD` | Stage 2 baseline says real data false; privacy/security records remain unknown | — | — | No effect on synthetic data | Blocks real-data spike/formal build | Approve location, roles and raw-data route |
| T1-PROFESSIONAL-RESPONSIBILITY | `docs/week-3/tier1-resolution-log.md` | OPEN | Client professional accountability | `BLOCKED_EXTERNAL_FORMAL_BUILD` | Synthetic Responsible Engineer/Final Submitter role separation is tested; no client acceptance | — | — | Synthetic role model remains usable | Blocks formal/live responsibility claim | Obtain signed responsibility and submission policy |

## Historical Week 6 blockers

| item_id | source_artifact | original_status | original_blocking_scope | disposition | evidence | resolved_by | resolved_at | synthetic_track_effect | formal_build_effect | remaining_action |
|---|---|---|---|---|---|---|---|---|---|---|
| W6-T2-REPEATING-GRID | `docs/week-3/tier2-backlog.md` | BLOCKING_WEEK6 | Grid identity/persistence | `RESOLVED_WITH_EVIDENCE` | `backend/scripts/golden_path_v1.py`, Week 6 report, stable grid rows and save/reopen reconciliation | Synthetic Product/Engineer | Reconciliation run | Resolved for synthetic Golden Path | No formal/live claim | W9/W12 hardening remains scheduled |
| W6-T2-FINDING-TAXONOMY | `docs/week-3/tier2-backlog.md` | BLOCKING_WEEK6 | Finding/task route | `SUPERSEDED` | Week 7 controlled FindingCode → Finding → Task → Notification mechanism; Week 6 core does not require closure | Synthetic Product | Week 7 implementation | No Week 6 blocker remains | No client approval created | Closure/resubmission remains W10 |

No historical open item is represented as generic `CLOSED`. Synthetic blockers remaining: none for the accepted Golden Path v1. Formal-build blockers remain the three external Tier 1 conditions plus unsigned Stage 2/Sign-off C and absent real-data/G10 evidence.

