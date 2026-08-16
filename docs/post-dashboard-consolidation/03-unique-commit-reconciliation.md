# Unique Commit Reconciliation

The common base is `07ea0478`. The four main-only commits are verification/evidence records and must remain in the integrated main history. The feature commits are retained by normal merges, not cherry-picks or rebases.

| Ref | Unique commits | Classification |
|---|---|---|
| owner integration branch | `c2a7551`, `d670a2b`, `7250b52` | `REQUIRED_CURRENT` for source closure plus `EVIDENCE_ONLY_CURRENT` for certification records |
| home navigation branch | `c2a7551`, `eccdfe8` | shared closure plus `REQUIRED_CURRENT` navigation work |
| UI productionization branch | `c2a7551`, `d670a2b`, `7250b52`, `aefb541` | shared closure/evidence plus `REQUIRED_CURRENT` visual-system work |
| main | `30a0396`, `2878c5d`, `ff4d45d`, `c31e6fb` | `MAIN_ONLY_CURRENT`; preserve all |

No unique commit is unknown, abandoned, obsolete, or silently discarded. The `git cherry` checks mark all branch candidates `+` relative to current main because their patch IDs are not yet contained in main; normal merge containment is the selected strategy.

`UNKNOWN_UNIQUE_COMMIT_COUNT=0` and `UNRECONCILED_MAIN_ONLY_COMMIT_COUNT=0`.
