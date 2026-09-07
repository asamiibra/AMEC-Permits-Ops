# Step 4 regression results

Final repository acceptance on the Step 4 source tree:

| Gate | Result |
| --- | --- |
| Backend full suite | `264 passed, 15 skipped, 2 warnings` |
| Governed prefill/apply and adversarial suites | passed |
| Consumer convergence and retrieval-quality suites | passed |
| Frontend unit suite | `39 passed` |
| Frontend production build | passed; existing large-chunk advisory only |
| Owner Dashboard E2E | desktop and mobile passed |
| Governed prefill/apply E2E | passed |
| SQLite migration upgrade/downgrade/upgrade | passed at `0059_governed_form_draft_apply` |
| Test-order isolation | passed in focused forward/reverse waves |
| `git diff --check` | passed |

No external retrieval/vector infrastructure was introduced. Existing SQL
retrieval remains sufficient.
